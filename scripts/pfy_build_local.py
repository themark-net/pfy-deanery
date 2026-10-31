#!/usr/bin/env python3
"""pfy build --local: one headless local-model task to a tested branch.

The checkout this process was started from is never switched, reset, stashed,
or committed. Work happens in a detached git worktree under ``<repo>/tmp/``.
Nothing is pushed and no PR is opened.

Exit codes:
  0  PASS, or a clean --dry-run, or --reap
  1  FAIL, or PASS-REJECTED (the gate was green and the review rejected the patch)
  2  usage, or opencode is missing
  3  TIMEOUT (agent)
  4  BLOCKED (memory, busy host, ps error, model size, cloud tag, lock, no-model,
           no-sandbox, no-runtime-dir, runtime-dir-in-tmp, socket-path)

A SIGKILL of this process cannot write a receipt. The pid file under
<repo>/tmp/local-build.pids.json is the recovery handle: the next run, and
`pfy build --local --reap`, signal that process group and write ABORTED for
any build-local directory that has no receipt, and for the pid file's receipt
dir when that receipt is missing.

Receipt schema: pfy-local-build/1
"""

from __future__ import annotations

import argparse
import fcntl
import fnmatch
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib.bot_interface import _scrub, _which_opencode, opencode_config  # noqa: E402

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_TIMEOUT = 3
EXIT_BLOCKED = 4

SCHEMA = "pfy-local-build/1"
DEFAULT_MODEL = "qwen3.6:35b"
DEFAULT_ENDPOINT = "http://127.0.0.1:11434/v1"
DEFAULT_TEST_CMD = "python3 -m unittest discover -s tests -t ."
DEFAULT_TIMEOUT = 1200
DEFAULT_TEST_TIMEOUT = 600
DEFAULT_MIN_FREE_GB = 32.0
DEFAULT_RETRIES = 2
DEFAULT_MAX_FILES = 3
DEFAULT_MAX_LINES = 250
REVIEW_MARKER = "pfy-review-v1"
DIFF_PROMPT_CAP = 8000
_RETRYABLE = {
    "no-change",
    "protected-path-changed",
    "tests-failed",
    "tests-regressed",
    "tests-tampered",
    "tests-flaky",
}
_FILES_LINE = re.compile(r"(?m)^files:\s*(.*)$")
_REQUIRE_LINE = re.compile(r"(?m)^require:\s*(\S+)\s+in\s+(.+)$")
# examples/local-bench/bench.py DEFAULT_MIN_MEM_GB (Entry 091). Watchdog only.
MEM_EDGE_GIB = 16.0
MAX_MODEL_BYTES = 30 * 1024 * 1024 * 1024
AUTHOR_NAME = "pfy-local-build"
AUTHOR_EMAIL = "pfy-local-build@localhost"
WATCH_SECONDS = 10.0
KILL_GRACE_SECONDS = 5.0

_SECRET_EQ = re.compile(
    r"(?i)\b([A-Za-z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD|PASSWD)[A-Za-z0-9_]*)\s*([:=])\s*(\S+)"
)
_BEARER = re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._\-]{8,})")
_BASIC = re.compile(r"(?i)(authorization\s*:\s*basic\s+)(\S+)")
_SK = re.compile(r"\b((?:sk|ghp)_[A-Za-z0-9]{8,})\b")
_AKIA = re.compile(r"\b(AKIA[0-9A-Z]{16})\b")
_PEM = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.DOTALL,
)


class UsageError(Exception):
    pass


class State:
    def __init__(self) -> None:
        self.interrupted = False
        self.mem_edge = False
        self.proc: subprocess.Popen | None = None
        self.pgid: int | None = None
        self.pid_path: Path | None = None
        self.min_avail: float | None = None
        self.lock_fd = None


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _mask(val: str) -> str:
    val = val.strip().strip('"').strip("'")
    if len(val) <= 4:
        return "***"
    return val[:4] + "***"


def redact(text: str) -> str:
    if not text:
        return ""

    def _eq(match: re.Match) -> str:
        return match.group(1) + match.group(2) + _mask(match.group(3))

    text = _PEM.sub("[redacted-private-key]", text)
    text = _SECRET_EQ.sub(_eq, text)
    text = _BEARER.sub(lambda m: m.group(1) + _mask(m.group(2)), text)
    text = _BASIC.sub(lambda m: m.group(1) + _mask(m.group(2)), text)
    text = _SK.sub(lambda m: _mask(m.group(1)), text)
    text = _AKIA.sub(lambda m: _mask(m.group(1)), text)
    return text


def _kb(info: dict, key: str) -> float:
    raw = info.get(key) or ""
    if not raw:
        return 0.0
    try:
        return float(str(raw).split()[0])
    except (TypeError, ValueError, IndexError):
        return 0.0


def read_meminfo() -> dict:
    path = Path(os.environ.get("PFY_MEMINFO_FILE") or "/proc/meminfo")
    out: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return out
    for line in lines:
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        out[key.strip()] = val.strip()
    return out


def gib(kb: float) -> float:
    return kb / (1024.0 * 1024.0)


def free_ram_plus_swap_gib(info: dict) -> float:
    """MemAvailable + SwapFree. SwapTotal is capacity, not free headroom."""
    return gib(_kb(info, "MemAvailable") + _kb(info, "SwapFree"))


def mem_available_gib(info: dict) -> float:
    return gib(_kb(info, "MemAvailable"))


def _alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _http_json(method: str, url: str, body=None, timeout: float = 5):
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Accept": "application/json", "User-Agent": "pfy-local-build/1"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", "replace")
        return resp.status, json.loads(raw) if raw else {}


def _slug(text: str) -> str:
    raw = re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return (raw[:40] or "task").strip("-") or "task"


def _endpoint_pair(raw: str) -> tuple[str, str]:
    ep = (raw or "").strip().rstrip("/") or DEFAULT_ENDPOINT
    if ep.endswith("/v1"):
        return ep[: -len("/v1")], ep
    return ep, ep + "/v1"


def _host_only(openai_base: str) -> str:
    root, _base = _endpoint_pair(openai_base)
    no_scheme = root.split("://", 1)[-1]
    return no_scheme.split("/", 1)[0]


def _is_cloud_tag(name: str) -> bool:
    return ":cloud" in (name or "").lower()


def _same_model(left: str, right: str) -> bool:
    def norm(name: str) -> str:
        name = (name or "").strip()
        if name.endswith(":latest"):
            name = name[: -len(":latest")]
        return name

    return norm(left) == norm(right)


def _pick_str(flag: str | None, env_name: str, default: str) -> str:
    if flag is not None and str(flag).strip() != "":
        return str(flag).strip()
    raw = os.environ.get(env_name)
    if raw is not None and raw.strip() != "":
        return raw.strip()
    return default


def _pick_float(flag: float | None, env_name: str, default: float) -> float:
    if flag is not None:
        return float(flag)
    raw = os.environ.get(env_name)
    if raw is not None and raw.strip() != "":
        return float(raw.strip())
    return default


def _parse_require_flag(text: str) -> tuple[str, list[str]]:
    match = re.fullmatch(r"(\S+)\s+in\s+(\S.*)", (text or "").strip())
    if not match:
        raise UsageError("--require-wiring must look like 'NAME in path, path'")
    modules = [part.strip() for part in match.group(2).split(",") if part.strip()]
    if not modules:
        raise UsageError("--require-wiring must look like 'NAME in path, path'")
    return match.group(1), modules


def _apply_review_flags(args: argparse.Namespace) -> None:
    if args.review and args.no_review_flag:
        raise UsageError("pass only one of --review and --no-review")
    args.review = not args.no_review_flag
    if args.retries is None:
        args.retries_n = DEFAULT_RETRIES
    else:
        args.retries_n = int(args.retries)
    args.max_files_n = DEFAULT_MAX_FILES if args.max_files is None else int(args.max_files)
    args.max_lines_n = DEFAULT_MAX_LINES if args.max_lines is None else int(args.max_lines)
    if args.retries_n < 0 or args.max_files_n < 0 or args.max_lines_n < 0:
        raise UsageError("retries, max-files, and max-lines must be zero or greater")
    if not args.review:
        args.retries_n = 0
    for item in list(args.require_wiring or []):
        _parse_require_flag(item)


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pfy build --local",
        description="Headless local-model build. One task, one tested branch, no push.",
    )
    parser.add_argument("task", nargs="?", help="task text")
    parser.add_argument("--local", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--repo", default=None, help="git repo (default: repo that contains the cwd)")
    parser.add_argument("--base", default=None, help="base ref (default: origin/main, else HEAD)")
    parser.add_argument("--model", default=None, help="Ollama tag (env PFY_LOCAL_BUILD_MODEL)")
    parser.add_argument("--endpoint", default=None, help="OpenAI base URL (env LOCAL_OPENAI_BASE_URL)")
    parser.add_argument("--test-cmd", default=None, help="gate command (env PFY_LOCAL_BUILD_TEST_CMD)")
    parser.add_argument("--timeout", type=float, default=None, help="agent seconds (env PFY_LOCAL_BUILD_TIMEOUT)")
    parser.add_argument("--test-timeout", type=float, default=None, help="test command seconds")
    parser.add_argument("--min-free-gb", type=float, default=None, help="MemAvailable+SwapFree floor")
    parser.add_argument("--protect", action="append", default=[], help="glob the agent must not change")
    parser.add_argument(
        "--writable-test",
        action="append",
        default=[],
        help="test path the task may change (repeatable). Other test files stay hashed",
    )
    parser.add_argument("--prompt-file", default=None, help="read the task from this file")
    parser.add_argument("--receipt-dir", default=None, help="directory for receipt.json")
    parser.add_argument("--keep-worktree", action="store_true", help="keep the worktree after PASS")
    parser.add_argument("--dry-run", action="store_true", help="pre-flight only: start nothing, load nothing")
    parser.add_argument("--run-tests-on-timeout", action="store_true", help="run the gate after TIMEOUT")
    parser.add_argument("--keep-model", action="store_true", help="do not unload at the end")
    parser.add_argument(
        "--unload-at-end",
        action="store_true",
        help="unload the requested model at the end if the agent started",
    )
    parser.add_argument(
        "--reap",
        action="store_true",
        help="kill stale local-build process groups, unload a model this runner loaded, write ABORTED receipts",
    )
    parser.add_argument(
        "--unsafe-no-sandbox",
        action="store_true",
        help="run the agent without bwrap when bwrap is unavailable (recorded on the receipt)",
    )
    parser.add_argument("--review", action="store_true", help="review a green gate before PASS (default)")
    parser.add_argument(
        "--no-review",
        action="store_true",
        dest="no_review_flag",
        help="one attempt and no review (MVP-1 behavior)",
    )
    parser.add_argument("--retries", type=int, default=None, help="extra attempts after the first (default 2)")
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="changed files allowed, not counting a test file the test command names (default 3)",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=None,
        help="added plus removed lines allowed (default 250)",
    )
    parser.add_argument("--allow-path", action="append", default=[], help="glob the patch may change (repeatable)")
    parser.add_argument(
        "--require-wiring",
        action="append",
        default=[],
        help="NAME in path, path: the symbol must be added in every path (repeatable)",
    )
    args = parser.parse_args(argv)
    if args.task and args.prompt_file:
        raise UsageError("PASS one task string or --prompt-file, not both")
    task = args.task
    if args.prompt_file:
        path = Path(args.prompt_file)
        if not path.is_file():
            raise UsageError("prompt file not found: %s" % path)
        task = path.read_text(encoding="utf-8")
    if args.reap and (not task or not str(task).strip()):
        args.task_text = ""
        args.model_name = _pick_str(args.model, "PFY_LOCAL_BUILD_MODEL", DEFAULT_MODEL)
        args.endpoint_raw = _pick_str(args.endpoint, "LOCAL_OPENAI_BASE_URL", DEFAULT_ENDPOINT)
        args.test_cmd_s = _pick_str(args.test_cmd, "PFY_LOCAL_BUILD_TEST_CMD", DEFAULT_TEST_CMD)
        args.timeout_s = _pick_float(args.timeout, "PFY_LOCAL_BUILD_TIMEOUT", DEFAULT_TIMEOUT)
        args.test_timeout_s = _pick_float(args.test_timeout, "PFY_LOCAL_BUILD_TEST_TIMEOUT", DEFAULT_TEST_TIMEOUT)
        args.min_free = _pick_float(args.min_free_gb, "PFY_LOCAL_BUILD_MIN_FREE_GB", DEFAULT_MIN_FREE_GB)
        _apply_review_flags(args)
        return args
    if not task or not str(task).strip():
        raise UsageError("a task string or --prompt-file is required")
    args.task_text = str(task)
    try:
        args.model_name = _pick_str(args.model, "PFY_LOCAL_BUILD_MODEL", DEFAULT_MODEL)
        args.endpoint_raw = _pick_str(args.endpoint, "LOCAL_OPENAI_BASE_URL", DEFAULT_ENDPOINT)
        args.test_cmd_s = _pick_str(args.test_cmd, "PFY_LOCAL_BUILD_TEST_CMD", DEFAULT_TEST_CMD)
        args.timeout_s = _pick_float(args.timeout, "PFY_LOCAL_BUILD_TIMEOUT", DEFAULT_TIMEOUT)
        args.test_timeout_s = _pick_float(args.test_timeout, "PFY_LOCAL_BUILD_TEST_TIMEOUT", DEFAULT_TEST_TIMEOUT)
        args.min_free = _pick_float(args.min_free_gb, "PFY_LOCAL_BUILD_MIN_FREE_GB", DEFAULT_MIN_FREE_GB)
    except ValueError as exc:
        raise UsageError("a numeric flag or env value is not a number") from exc
    if args.timeout_s <= 0 or args.test_timeout_s <= 0 or args.min_free < 0:
        raise UsageError("timeout and min-free-gb must be positive (min-free-gb may be 0)")
    _apply_review_flags(args)
    return args


def _git(repo: Path, args: list[str], env: dict | None = None, timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def resolve_repo(raw: str | None) -> Path:
    start = Path(raw).resolve() if raw else Path.cwd()
    if not start.exists():
        raise UsageError("repo path does not exist: %s" % start)
    proc = _git(start if start.is_dir() else start.parent, ["rev-parse", "--show-toplevel"])
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        raise UsageError("not a git repo: %s" % start)
    return Path(proc.stdout.strip()).resolve()


def resolve_base(repo: Path, requested: str | None) -> str:
    if requested and requested.strip():
        ref = requested.strip()
    else:
        probe = _git(repo, ["rev-parse", "--verify", "--quiet", "origin/main"])
        ref = "origin/main" if probe.returncode == 0 else "HEAD"
    sha = _git(repo, ["rev-parse", ref])
    if sha.returncode != 0 or not (sha.stdout or "").strip():
        raise UsageError("base ref not found: %s" % ref)
    return ref


def _child_env(extra: dict[str, str]) -> dict[str, str]:
    forwarded = {}
    for key, val in os.environ.items():
        if key == "PFY_LOCAL_BUILD_SCENARIO" or key.startswith("PFY_STUB_"):
            forwarded[key] = val
    forwarded.update(extra)
    return _scrub(os.environ, **forwarded)


def _group_alive(pgid: int) -> bool:
    if not pgid or pgid <= 0:
        return False
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _signal_pgid(pgid: int, sig: int) -> None:
    if not pgid or pgid <= 0 or pgid == os.getpgrp():
        return
    try:
        os.killpg(pgid, sig)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def _kill_pgid(pgid: int | None) -> None:
    """TERM the whole group, then SIGKILL. Leader state does not matter."""
    if not pgid or pgid <= 0 or pgid == os.getpgrp():
        return
    if not _group_alive(pgid):
        return
    _signal_pgid(pgid, signal.SIGTERM)
    deadline = time.monotonic() + KILL_GRACE_SECONDS
    while time.monotonic() < deadline:
        if not _group_alive(pgid):
            return
        time.sleep(0.05)
    if _group_alive(pgid):
        _signal_pgid(pgid, signal.SIGKILL)


def _remember_pgid(state: State, pgid: int) -> None:
    state.pgid = pgid
    path = state.pid_path
    if path is None:
        return
    try:
        current = {}
        if path.is_file():
            current = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(current, dict):
            current = {}
        current["pid"] = os.getpid()
        current["pgid"] = os.getpgrp()
        current["agent_pgid"] = pgid
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(current), encoding="utf-8")
        os.replace(tmp, path)
    except (OSError, json.JSONDecodeError):
        pass


def _drain(proc: subprocess.Popen, box: dict) -> None:
    try:
        out, err = proc.communicate()
    except Exception as exc:  # noqa: BLE001
        box["error"] = str(exc)
        out, err = "", ""
    box["out"] = out or ""
    box["err"] = err or ""
    box["code"] = proc.returncode


def run_bounded(cmd: list[str], env: dict, cwd: Path, timeout: float, state: State) -> tuple[str, int | None, str, str]:
    """Run cmd in its own session. Returns (status, code, stdout, stderr).

    status is done, timeout, interrupted, or mem-edge.
    """
    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        pgid = os.getpgid(proc.pid)
    except (ProcessLookupError, PermissionError, OSError):
        pgid = proc.pid
    state.proc = proc
    _remember_pgid(state, pgid)
    box: dict = {}
    reader = threading.Thread(target=_drain, args=(proc, box), daemon=True)
    reader.start()
    deadline = time.monotonic() + timeout
    status = "done"
    while True:
        if state.interrupted:
            status = "interrupted"
            _kill_pgid(pgid)
            break
        if state.mem_edge:
            status = "mem-edge"
            _kill_pgid(pgid)
            break
        if time.monotonic() >= deadline:
            status = "timeout"
            _kill_pgid(pgid)
            break
        # The leader can exit and leave children holding the pipes.
        # Reap the group now so a background child cannot sit out the timeout.
        if proc.poll() is not None:
            _kill_pgid(pgid)
            status = "done"
            break
        if not reader.is_alive():
            status = "done"
            break
        time.sleep(0.05)
    if reader.is_alive():
        reader.join(timeout=2)
    if reader.is_alive():
        _kill_pgid(pgid)
        try:
            proc.kill()
        except OSError:
            pass
        reader.join(timeout=2)
    state.proc = None
    state.pgid = None
    return status, box.get("code"), box.get("out") or "", box.get("err") or ""


def _tail(text: str, lines: int = 40) -> str:
    parts = (text or "").splitlines()
    return "\n".join(parts[-lines:])


def parse_unittest_counts(text: str) -> dict | None:
    match = re.search(r"^Ran (\d+) tests?\b", text or "", re.M)
    if not match:
        return None
    ran = int(match.group(1))
    failed_m = re.search(r"failures=(\d+)", text)
    errors_m = re.search(r"errors=(\d+)", text)
    skipped_m = re.search(r"skipped=(\d+)", text)
    if not skipped_m:
        skipped_m = re.search(r"(\d+)\s+skipped\b", text or "")
    xfail_m = re.search(r"xfailed=(\d+)", text or "")
    if not xfail_m:
        xfail_m = re.search(r"(\d+)\s+xfailed\b", text or "")
    failed = int(failed_m.group(1)) if failed_m else 0
    errors = int(errors_m.group(1)) if errors_m else 0
    skipped = int(skipped_m.group(1)) if skipped_m else 0
    xfailed = int(xfail_m.group(1)) if xfail_m else 0
    passed = max(0, ran - failed - errors - skipped - xfailed)
    sec_m = re.search(r"Ran \d+ tests? in ([0-9.]+)s", text)
    seconds = float(sec_m.group(1)) if sec_m else None
    return {
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "xfailed": xfailed,
        "deselected": 0,
        "ran": ran,
        "seconds": seconds,
    }


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text or "")


def _count_record(passed: int, failed: int, errors: int, skipped: int, xfailed: int, deselected: int, seconds: float | None) -> dict:
    ran = passed + failed + errors + skipped + xfailed
    return {
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "xfailed": xfailed,
        "deselected": deselected,
        "ran": ran,
        "seconds": seconds,
    }


def _parse_pytest_summary(text: str) -> dict | None:
    chosen = None
    chosen_line = ""
    for line in text.splitlines():
        if not re.search(r"\bin\s+[0-9.]+\s*s\b", line):
            continue
        found = list(
            re.finditer(
                r"(\d+)\s+(passed|failed|errors|error|skipped|xfailed|xpassed|deselected)\b",
                line,
                re.I,
            )
        )
        if found:
            chosen = found
            chosen_line = line
    if not chosen:
        return None
    counts = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0, "xfailed": 0, "deselected": 0}
    for match in chosen:
        num = int(match.group(1))
        word = match.group(2).lower()
        if word in ("error", "errors"):
            counts["errors"] = num
        elif word == "xpassed":
            continue
        elif word in counts:
            counts[word] = num
    sec_m = re.search(r"\bin\s+([0-9.]+)\s*s", chosen_line)
    seconds = float(sec_m.group(1)) if sec_m else None
    return _count_record(
        counts["passed"],
        counts["failed"],
        counts["errors"],
        counts["skipped"],
        counts["xfailed"],
        counts["deselected"],
        seconds,
    )


def _parse_junit(text: str) -> dict | None:
    chunks = re.findall(r"<testsuite\b([^>]*)>", text, re.I)
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    saw = False
    for chunk in chunks:
        # <testsuites> does not match <testsuite\b because the next char is a word.
        attrs = dict(re.findall(r'([A-Za-z]+)="(\d+)"', chunk))
        if "tests" not in attrs:
            continue
        saw = True
        for key in totals:
            totals[key] += int(attrs.get(key) or 0)
    if not saw:
        return None
    ran = totals["tests"]
    failed = totals["failures"]
    errors = totals["errors"]
    skipped = totals["skipped"]
    passed = max(0, ran - failed - errors - skipped)
    return _count_record(passed, failed, errors, skipped, 0, 0, None)


def parse_test_counts(text: str) -> dict | None:
    """Unittest, a pytest summary line, or junit xml. None if nothing parseable."""
    clean = _strip_ansi(text)
    uni = parse_unittest_counts(clean)
    if uni is not None:
        return uni
    pytest_counts = _parse_pytest_summary(clean)
    if pytest_counts is not None:
        return pytest_counts
    return _parse_junit(clean)


def _total(counts: dict | None) -> int | None:
    if not counts:
        return None
    return int(counts["ran"])


def judge_tests(before: dict, after: dict) -> str | None:
    """None means the gate passed. Otherwise a FAIL reason.

    A new skip, xfail, deselect, or error is a failure even when the process
    exit is 0. Exit 0 with no parseable summary is a failure, so a runner
    that calls os._exit(0) does not pass. Passed count must not fall.
    """
    if not after.get("started"):
        return "test-cmd-failed-to-start"
    if after.get("exit") != 0:
        return "tests-failed"
    after_counts = after.get("counts")
    before_counts = before.get("counts")
    if not after_counts or not before_counts:
        return "tests-failed"
    for key in ("skipped", "xfailed", "deselected", "errors", "failed"):
        if int(after_counts.get(key) or 0) > int(before_counts.get(key) or 0):
            return "tests-failed"
    if int(after_counts.get("passed") or 0) < int(before_counts.get("passed") or 0):
        return "tests-regressed"
    if _total(after_counts) < _total(before_counts):
        return "tests-regressed"
    return None


def _test_record(cmd: str, started: bool, exit_code: int | None, text: str, seconds: float) -> dict:
    counts = parse_test_counts(text) if started else None
    return {
        "cmd": cmd,
        "exit": exit_code,
        "passed": None if not counts else counts["passed"],
        "failed": None if not counts else counts["failed"],
        "errors": None if not counts else counts["errors"],
        "seconds": round(seconds, 3),
        "tail": redact(_tail(text)),
        "started": started,
        "counts": counts,
    }


def run_tests(
    cmd_s: str,
    cwd: Path,
    env: dict,
    timeout: float,
    state: State,
    *,
    repo: Path | None = None,
    unsafe: bool = False,
) -> dict:
    """Run the gate command. With a repo, use the agent bwrap profile.

    The profile is --unshare-net with no Ollama bridge, the main checkout not
    writable, and no push credentials. --unsafe-no-sandbox leaves the command
    unsandboxed only when bwrap itself is missing.
    """
    argv = shlex.split(cmd_s)
    if not argv:
        return _test_record(cmd_s, False, None, "empty test command", 0.0)
    if not _command_resolves(argv, cwd, env):
        return _test_record(cmd_s, False, None, "command not found", 0.0)
    prepared = None
    run_argv = argv
    run_env = dict(env)
    if repo is not None:
        prepared = prepare_sandbox(
            argv,
            cwd,
            hide=hide_paths(repo, cwd),
            endpoint=None,
            unsafe=unsafe,
        )
        run_argv = prepared.argv
        run_env.update(lockdown_env(cwd))
        run_env["GIT_TERMINAL_PROMPT"] = "0"
    started = time.monotonic()
    try:
        try:
            status, code, out, err = run_bounded(run_argv, run_env, cwd, timeout, state)
        except FileNotFoundError:
            return _test_record(cmd_s, False, None, "command not found", 0.0)
        except OSError as exc:
            if getattr(exc, "errno", None) == 2:
                return _test_record(cmd_s, False, None, "command not found", 0.0)
            return _test_record(cmd_s, False, None, str(exc), 0.0)
    finally:
        if prepared is not None:
            prepared.close()
    elapsed = time.monotonic() - started
    text = (out or "") + ("\n" + err if err else "")
    if status == "timeout":
        rec = _test_record(cmd_s, True, code if code is not None else 124, text + "\ntest-timeout", elapsed)
        rec["exit"] = 124
        return rec
    if status in ("interrupted", "mem-edge"):
        rec = _test_record(cmd_s, True, code, text, elapsed)
        rec["aborted"] = status
        return rec
    return _test_record(cmd_s, True, code if code is not None else 1, text, elapsed)


def _command_resolves(argv: list[str], cwd: Path, env: dict) -> bool:
    """True when argv[0] exists on the host. bwrap hides a missing exec."""
    program = argv[0]
    if os.path.sep in program:
        candidate = Path(program)
        if not candidate.is_absolute():
            candidate = cwd / candidate
        return candidate.is_file() and os.access(candidate, os.X_OK)
    return shutil.which(program, path=env.get("PATH")) is not None


def _norm_rel(path: str) -> str:
    """Normalise a repo-relative path. Does not strip leading dots."""
    text = (path or "").replace("\\", "/").strip()
    while text.startswith("./"):
        text = text.removeprefix("./")
    if not text:
        return ""
    normalized = os.path.normpath(text).replace("\\", "/")
    if normalized == ".":
        return ""
    return normalized


def _protected(path: str, patterns: list[str]) -> bool:
    rel = _norm_rel(path)
    if not rel:
        return False
    name = Path(rel).name
    for pattern in patterns:
        pat = _norm_rel(pattern)
        if not pat:
            continue
        if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(name, pat):
            return True
        if pat.endswith("/**"):
            prefix = pat[:-3].rstrip("/")
            if rel == prefix or rel.startswith(prefix + "/"):
                return True
        if "**" in pat and fnmatch.fnmatch(rel, pat.replace("**", "*")):
            return True
    return False


def files_changed(worktree: Path, env: dict) -> list[str]:
    proc = _git(worktree, ["status", "--porcelain", "-uall"], env=env)
    found = []
    for line in (proc.stdout or "").splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        path = path.replace("\\", "/")
        if path == "tmp" or path.startswith("tmp/"):
            continue
        if path.startswith("__pycache__/") or path.endswith(".pyc") or "/__pycache__/" in path:
            continue
        found.append(path)
    return found


def _ensure_tmp_excluded(worktree: Path, env: dict) -> None:
    """Append tmp ignores to this worktree's git dir only, never the common dir."""
    (worktree / "tmp").mkdir(parents=True, exist_ok=True)
    raw = _git(worktree, ["rev-parse", "--path-format=absolute", "--git-dir"], env=env)
    if raw.returncode != 0 or not (raw.stdout or "").strip():
        return
    path = Path((raw.stdout or "").strip()) / "info" / "exclude"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = [ln.strip() for ln in text.splitlines()]
    extra = ["tmp/", "__pycache__/", "*.pyc"]
    missing = [item for item in extra if item not in lines]
    if not missing:
        return
    with path.open("a", encoding="utf-8") as handle:
        if text and not text.endswith("\n"):
            handle.write("\n")
        for item in missing:
            handle.write(item + "\n")


def _acquire_lock(path: Path) -> object | None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = open(path, "a+", encoding="utf-8")
    try:
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        fd.seek(0)
        raw = fd.read().strip()
        fd.close()
        pid = int(raw) if raw.isdigit() else None
        if pid and not _alive(pid):
            fd = open(path, "a+", encoding="utf-8")
            try:
                fcntl.flock(fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                fd.close()
                return None
        else:
            return None
    fd.seek(0)
    fd.truncate()
    fd.write(str(os.getpid()))
    fd.flush()
    return fd


def _release_lock(fd) -> None:
    if fd is None:
        return
    try:
        fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass
    try:
        fd.close()
    except OSError:
        pass


def _ollama_tags(root: str) -> tuple[list[dict] | None, str | None]:
    try:
        status, data = _http_json("GET", root.rstrip("/") + "/api/tags", timeout=3)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return None, "unreachable"
    if status != 200 or not isinstance(data, dict):
        return None, "unreachable"
    models = data.get("models")
    if not isinstance(models, list):
        return [], None
    return models, None


def _tag_of(model: str, tags: list[dict]) -> dict | None:
    for item in tags:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("model") or ""
        if _same_model(str(name), model):
            return item
    return None


def _ps_names(root: str) -> list[str] | None:
    """Loaded model names, or None when /api/ps cannot be trusted.

    None is fail-closed. A 500, a network error, or a non-JSON body is not
    an empty host. There is no `ollama ps` fallback.
    """
    try:
        status, data = _http_json("GET", root.rstrip("/") + "/api/ps", timeout=3)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return None
    if status != 200 or not isinstance(data, dict):
        return None
    names = []
    for item in data.get("models") or []:
        if isinstance(item, str) and item.strip():
            names.append(item.strip())
        elif isinstance(item, dict):
            name = item.get("name") or item.get("model") or ""
            if str(name).strip():
                names.append(str(name).strip())
    return names


def _model_size(tag: dict) -> int | None:
    raw = tag.get("size")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def unload_model(root: str, model: str) -> bool:
    body = {
        "model": model,
        "prompt": "",
        "stream": False,
        "keep_alive": 0,
        "options": {"num_ctx": 512, "num_predict": 1},
    }
    try:
        status, _data = _http_json("POST", root.rstrip("/") + "/api/generate", body, timeout=30)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
        return False
    return status == 200


def _write_config(home: Path, base: str, model: str) -> Path:
    cfg = opencode_config(base, model)
    cfg["permission"] = {
        "read": "allow",
        "edit": "allow",
        "bash": {
            "*": "allow",
            # Last match wins. A slash after a space or a redirect, or "..",
            # is a path outside this worktree or an absolute path. In-tree
            # commands such as `python3 -m unittest discover -s tests -t .`
            # do not match these. opencode 1.18 does not treat a shell
            # redirect as external_directory, so the pattern is the backstop.
            "* /*": "deny",
            "*>/*": "deny",
            "*..*": "deny",
            "git commit*": "deny",
            "git push*": "deny",
            "git reset*": "deny",
            "git checkout*": "deny",
            "git switch*": "deny",
            "git clean*": "deny",
        },
        "external_directory": "deny",
        "webfetch": "deny",
        "websearch": "deny",
        "question": "deny",
    }
    path = home / "config" / "opencode" / "opencode.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return path


def _agent_prompt(task: str, test_cmd: str, feedback: str = "", previous_diff: str = "") -> str:
    base = (
        "Work only in this directory. Edit files. Run the tests yourself. "
        "Do not commit. Do not touch anything outside this directory.\n\n"
        "Test command: %s\n\n"
        "Task:\n%s" % (test_cmd, task)
    )
    if not feedback and not previous_diff:
        return base
    shown = redact(previous_diff or "")
    if len(shown) > DIFF_PROMPT_CAP:
        shown = shown[:DIFF_PROMPT_CAP] + "\n...[diff truncated]\n"
    return (
        base
        + "\n\nThe previous attempt was rejected.\nReasons:\n%s\n\nPrevious diff:\n%s\n"
        % (redact(feedback or ""), shown)
    )


def _opencode_env(home: Path, worktree: Path, base: str, config: Path) -> dict[str, str]:
    return _child_env(
        {
            "OPENAI_BASE_URL": base,
            "HOME": str(home / "home"),
            "XDG_CONFIG_HOME": str(home / "config"),
            "XDG_DATA_HOME": str(home / "data"),
            "XDG_CACHE_HOME": str(home / "cache"),
            "XDG_STATE_HOME": str(home / "state"),
            "OPENCODE_CONFIG": str(config),
            "OPENCODE_DISABLE_PROJECT_CONFIG": "1",
            "OPENCODE_DISABLE_AUTOUPDATE": "1",
            "OPENCODE_DISABLE_MODELS_FETCH": "1",
            "OPENCODE_DISABLE_SHARE": "1",
            "OPENCODE_DISABLE_CLAUDE_CODE": "1",
            "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
            "OPENCODE_DISABLE_LSP_DOWNLOAD": "1",
            "TMPDIR": str(worktree / "tmp"),
        }
    )


def _prepare_home(home: Path) -> None:
    for name in ("home", "config", "data", "cache", "state"):
        (home / name).mkdir(parents=True, exist_ok=True)


def _public_test(rec: dict | None) -> dict | None:
    if rec is None:
        return None
    return {
        "cmd": rec.get("cmd"),
        "exit": rec.get("exit"),
        "passed": rec.get("passed"),
        "failed": rec.get("failed"),
        "errors": rec.get("errors"),
        "seconds": rec.get("seconds"),
        "tail": rec.get("tail"),
    }


def _write_receipt(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _summary(status: str, reason: str, branch: str | None, receipt: Path) -> str:
    label = status
    if status == "BLOCKED":
        label = "BLOCKED:"
    if status == "PASS-REJECTED":
        label = "PASS-REJECTED"
    shown = reason or ""
    return "%s %s branch=%s receipt=%s" % (label, shown, branch or "none", receipt)


def _install_signals(state: State) -> None:
    def _handle(signum, _frame):
        state.interrupted = True
        if state.pgid:
            _signal_pgid(state.pgid, signal.SIGTERM)

    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)


def _watchdog(stop: threading.Event, state: State) -> None:
    while not stop.wait(WATCH_SECONDS):
        avail = mem_available_gib(read_meminfo())
        if state.min_avail is None:
            state.min_avail = avail
        else:
            state.min_avail = min(state.min_avail, avail)
        if avail < MEM_EDGE_GIB:
            state.mem_edge = True
            if state.pgid:
                _signal_pgid(state.pgid, signal.SIGTERM)
            return


def _git_env(base_env: dict[str, str]) -> dict[str, str]:
    env = dict(base_env)
    env["GIT_AUTHOR_NAME"] = AUTHOR_NAME
    env["GIT_AUTHOR_EMAIL"] = AUTHOR_EMAIL
    env["GIT_COMMITTER_NAME"] = AUTHOR_NAME
    env["GIT_COMMITTER_EMAIL"] = AUTHOR_EMAIL
    return env


PUSH_BLOCKED_URL = "file:///pfy-local-build-push-blocked"
_CONFIG_BASENAMES = {
    "conftest.py",
    "pytest.ini",
    "tox.ini",
    "phpunit.xml",
    "phpunit.xml.dist",
    "unittest.cfg",
    "jest.config.js",
    "jest.config.ts",
    "vitest.config.ts",
}
# Always hashed, including files the agent creates. A new conftest or a
# rewritten .gitignore must not be able to change the gate.
_GATE_BASENAMES = {
    "conftest.py",
    "pytest.ini",
    "tox.ini",
    "setup.cfg",
    "pyproject.toml",
    "sitecustomize.py",
    "usercustomize.py",
    ".gitignore",
    ".gitattributes",
}
_ENTRY = """\
import os
import socket
import subprocess
import sys
import threading
import time

sock_path = sys.argv[1]
port = int(sys.argv[2])
cmd = sys.argv[4:]


def splice(left, right):
    def pump(src, dst):
        try:
            while True:
                data = src.recv(65536)
                if not data:
                    break
                dst.sendall(data)
        except OSError:
            pass
        finally:
            try:
                dst.shutdown(socket.SHUT_WR)
            except OSError:
                pass

    left_to_right = threading.Thread(target=pump, args=(left, right), daemon=True)
    right_to_left = threading.Thread(target=pump, args=(right, left), daemon=True)
    left_to_right.start()
    right_to_left.start()


def serve(ready):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind(("127.0.0.1", port))
        srv.listen(16)
    except OSError:
        ready.set()
        return
    srv.settimeout(0.3)
    ready.set()
    while True:
        try:
            conn, _addr = srv.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        unix = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            unix.connect(sock_path)
        except OSError:
            conn.close()
            continue
        threading.Thread(target=splice, args=(conn, unix), daemon=True).start()


ready = threading.Event()
threading.Thread(target=serve, args=(ready,), daemon=True).start()
ready.wait(2)
raise SystemExit(subprocess.call(cmd))
"""


class SandboxUnavailable(Exception):
    def __init__(self, message: str, reason: str = "no-sandbox") -> None:
        super().__init__(message)
        self.reason = reason


class PreparedSandbox:
    def __init__(self, argv: list[str], mode: str, bridge, link: Path | None = None) -> None:
        self.argv = argv
        self.mode = mode
        self.bridge = bridge
        self.link = link

    def close(self) -> None:
        if self.bridge is not None:
            self.bridge.close()
            self.bridge = None
        if self.link is not None:
            try:
                if self.link.is_symlink() or self.link.exists():
                    self.link.unlink()
            except OSError:
                pass
            self.link = None


class _Bridge:
    def __init__(self) -> None:
        self.stop = threading.Event()
        self.sock_path: Path | None = None
        self._srv = None

    def start(self, sock_path: Path, port: int) -> None:
        self.sock_path = sock_path
        if sock_path.exists():
            sock_path.unlink()
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(str(sock_path))
        os.chmod(sock_path, 0o600)
        srv.listen(32)
        srv.settimeout(0.2)
        self._srv = srv

        def loop() -> None:
            while not self.stop.is_set():
                try:
                    conn, _addr = srv.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                try:
                    tcp = socket.create_connection(("127.0.0.1", port), timeout=3)
                except OSError:
                    conn.close()
                    continue
                # The 3s cap is only the handshake. A model load is silent
                # longer than that, and a leftover timeout aborts the response.
                tcp.settimeout(None)
                threading.Thread(target=_splice_sockets, args=(conn, tcp), daemon=True).start()
            try:
                srv.close()
            except OSError:
                pass

        threading.Thread(target=loop, daemon=True).start()

    def close(self) -> None:
        self.stop.set()
        if self._srv is not None:
            try:
                self._srv.close()
            except OSError:
                pass
        if self.sock_path is not None and self.sock_path.exists():
            try:
                self.sock_path.unlink()
            except OSError:
                pass


def _splice_sockets(left: socket.socket, right: socket.socket) -> None:
    def pump(src: socket.socket, dst: socket.socket) -> None:
        try:
            while True:
                data = src.recv(65536)
                if not data:
                    break
                dst.sendall(data)
        except OSError:
            pass
        finally:
            try:
                dst.shutdown(socket.SHUT_WR)
            except OSError:
                pass

    left_to_right = threading.Thread(target=pump, args=(left, right), daemon=True)
    right_to_left = threading.Thread(target=pump, args=(right, left), daemon=True)
    left_to_right.start()
    right_to_left.start()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_test_path(rel: str) -> bool:
    parts = [part for part in _norm_rel(rel).split("/") if part]
    if not parts:
        return False
    name = parts[-1]
    if name.startswith("test_") or name.endswith("_test.py") or name.endswith("_test.go"):
        return True
    dirs = parts[:-1]
    return any(part in ("tests", "test") for part in dirs)


def _is_gate_file(rel: str) -> bool:
    return Path(rel).name in _GATE_BASENAMES


def _is_test_config(rel: str, full: Path, test_cmd: str) -> bool:
    name = Path(rel).name
    if name in _CONFIG_BASENAMES:
        return True
    cmd = (test_cmd or "").lower()
    if name in ("pyproject.toml", "setup.cfg"):
        try:
            text = full.read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            return False
        if "pytest" in cmd and "pytest" in text:
            return True
        if "unittest" in cmd and "unittest" in text:
            return True
    try:
        tokens = shlex.split(test_cmd or "")
    except ValueError:
        tokens = []
    for token in tokens:
        if _norm_rel(token) == _norm_rel(rel):
            return True
    return False


def snapshot_tests(worktree: Path, test_cmd: str) -> dict[str, str]:
    """Hash test files and the test command's config at the base tree."""
    found: dict[str, str] = {}
    if not worktree.is_dir():
        return found
    for dirpath, dirnames, filenames in os.walk(worktree):
        dirnames[:] = [
            name
            for name in dirnames
            if name not in {".git", "tmp", "__pycache__"} and not name.endswith(".home")
        ]
        for name in filenames:
            if name.endswith(".pyc"):
                continue
            full = Path(dirpath) / name
            try:
                rel = _norm_rel(str(full.relative_to(worktree)))
            except ValueError:
                continue
            if not rel or rel.startswith("tmp/"):
                continue
            if not (_is_test_path(rel) or _is_test_config(rel, full, test_cmd) or _is_gate_file(rel)):
                continue
            try:
                found[rel] = _sha256_file(full)
            except OSError:
                continue
    return found


def tests_tampered(worktree: Path, snapshot: dict[str, str], writable: list[str]) -> list[str]:
    bad = []
    for rel, digest in snapshot.items():
        if writable and _protected(rel, writable):
            continue
        path = worktree / rel
        if not path.is_file():
            bad.append(rel)
            continue
        try:
            if _sha256_file(path) != digest:
                bad.append(rel)
        except OSError:
            bad.append(rel)
    current = snapshot_tests(worktree, "")
    for rel in current:
        if rel in snapshot or rel in bad:
            continue
        if not _is_gate_file(rel):
            continue
        if writable and _protected(rel, writable):
            continue
        bad.append(rel)
    return bad


def _under_system_tmp(path: Path) -> bool:
    """True when path is /tmp or a child of it. The sandbox tmpfs hides /tmp."""
    raw = str(path)
    if raw == "/tmp" or raw.startswith("/tmp/"):
        return True
    try:
        resolved = path.resolve()
    except OSError:
        return False
    system = Path("/tmp").resolve()
    return resolved == system or system in resolved.parents


def _runtime_dir() -> Path:
    """A short writable directory for the Ollama socket.

    AF_UNIX paths are limited to 108 bytes. A worktree under this repo is
    already longer than that, so the socket cannot live at the worktree path.
    A dir under /tmp is refused: the sandbox mounts a fresh tmpfs there and
    the agent would lose the socket. When XDG_RUNTIME_DIR is set and unusable,
    this does not fall back, so the receipt can name the runtime dir.
    """
    env_dir = (os.environ.get("XDG_RUNTIME_DIR") or "").strip()
    if env_dir:
        cand = Path(env_dir)
        if _under_system_tmp(cand):
            raise SandboxUnavailable("runtime dir is under /tmp", reason="runtime-dir-in-tmp")
        if cand.is_dir() and os.access(cand, os.W_OK):
            return cand
        raise SandboxUnavailable("runtime dir is missing", reason="no-runtime-dir")
    fallback = Path("/run/user") / str(os.getuid())
    if _under_system_tmp(fallback):
        raise SandboxUnavailable("runtime dir is under /tmp", reason="runtime-dir-in-tmp")
    if fallback.is_dir() and os.access(fallback, os.W_OK):
        return fallback
    raise SandboxUnavailable("runtime dir is missing", reason="no-runtime-dir")


def _refuse_explicit_runtime_dir() -> None:
    """Raise before a sandbox starts when XDG_RUNTIME_DIR is set and unusable.

    A missing or /tmp runtime dir must not be reported as a missing bwrap.
    An unset XDG is left to _socket_link, which may bind a short worktree
    socket. That keeps "bwrap is not usable" for a caller that did not point
    at a bad runtime dir.
    """
    if not (os.environ.get("XDG_RUNTIME_DIR") or "").strip():
        return
    _runtime_dir()


def _socket_link(worktree: Path) -> tuple[Path | None, Path]:
    """Symlink a short runtime name at the worktree and return (link, socket).

    The socket inode stays in the worktree tmp. The name used for bind() is
    the short link, which also fits inside the sandbox via the host /run mount.
    When no runtime dir exists and the worktree path itself fits in 108 bytes,
    bind the socket in the worktree tmp. An explicit XDG_RUNTIME_DIR does not
    fall back.
    """
    direct = worktree / "tmp" / "ollama.sock"
    try:
        runtime = _runtime_dir()
    except SandboxUnavailable as exc:
        xdg = (os.environ.get("XDG_RUNTIME_DIR") or "").strip()
        if exc.reason == "no-runtime-dir" and not xdg and len(str(direct)) < 108:
            return None, direct
        raise
    for old in runtime.glob("pfy-lb-*"):
        if old.is_symlink() and not old.exists():
            try:
                old.unlink()
            except OSError:
                pass
    link = runtime / ("pfy-lb-%s-%s" % (os.getpid(), _stamp()[-6:]))
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(worktree.resolve())
    sock = link / "tmp" / "ollama.sock"
    if len(str(sock)) >= 108:
        link.unlink()
        raise SandboxUnavailable("ollama socket path is too long", reason="socket-path")
    return link, sock


def bwrap_works() -> bool:
    cached = getattr(bwrap_works, "_cached", None)
    if cached is not None:
        return bool(cached)
    ok = False
    if shutil.which("bwrap"):
        try:
            proc = subprocess.run(
                [
                    "bwrap",
                    "--ro-bind",
                    "/",
                    "/",
                    "--dev",
                    "/dev",
                    "--proc",
                    "/proc",
                    "--tmpfs",
                    "/tmp",
                    "--unshare-net",
                    "--unshare-pid",
                    "--unshare-ipc",
                    "--unshare-uts",
                    "--die-with-parent",
                    "--",
                    "true",
                ],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            ok = proc.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            ok = False
    setattr(bwrap_works, "_cached", ok)
    return ok


def _loopback_port(endpoint: str | None) -> int | None:
    if not endpoint:
        return None
    host = endpoint.strip().split("://", 1)[-1].split("/", 1)[0]
    name = host
    port: int | None = None
    if host.startswith("["):
        name = host[1:].split("]", 1)[0]
        rest = host.split("]", 1)[-1]
        if rest.startswith(":"):
            try:
                port = int(rest[1:])
            except ValueError:
                return None
    elif ":" in host:
        name, port_s = host.rsplit(":", 1)
        try:
            port = int(port_s)
        except ValueError:
            return None
    if name not in ("127.0.0.1", "localhost", "::1"):
        return None
    return port or 80


def _abs_git_path(repo: Path, flag: str) -> Path | None:
    proc = _git(repo, ["rev-parse", "--path-format=absolute", flag])
    text = (proc.stdout or "").strip() if proc.returncode == 0 else ""
    if not text:
        proc = _git(repo, ["rev-parse", flag])
        text = (proc.stdout or "").strip() if proc.returncode == 0 else ""
    if not text:
        return None
    path = Path(text)
    if not path.is_absolute():
        path = (repo / path).resolve()
    return path


def hide_paths(repo: Path, worktree: Path, extra: list[str] | None = None) -> list[str]:
    """Directories the sandbox must not see. The worktree is bound back afterwards."""
    candidates: list[Path] = []
    home = Path.home()
    for rel in (".ssh", Path(".config") / "gh", ".grok", Path(".config") / "git"):
        candidates.append(home / rel)
    for flag in ("--git-common-dir", "--git-dir"):
        found = _abs_git_path(repo, flag)
        if found is not None:
            candidates.append(found)
            if found.name == ".git":
                candidates.append(found.parent)
    for item in extra or []:
        candidates.append(Path(item))
    wt = worktree.resolve()
    seen: set[str] = set()
    out: list[str] = []
    for cand in candidates:
        try:
            if not cand.exists() or not cand.is_dir():
                continue
            resolved = cand.resolve()
        except OSError:
            continue
        if resolved == Path("/") or resolved == wt or wt in resolved.parents:
            continue
        text = str(resolved)
        if text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _sandbox_hides(hide: list[str], worktree: Path) -> list[str]:
    """tmpfs the hidden dirs. Recreate the worktree path if a parent was covered.

    bwrap will not bind onto a path that a parent tmpfs removed. --dir puts
    the mountpoint back, then the caller bind-mounts the worktree.
    """
    wt = worktree.resolve()
    dirs: list[Path] = []
    for raw in hide:
        path = Path(raw)
        try:
            if path.is_dir():
                dirs.append(path.resolve())
        except OSError:
            continue
    dirs.sort(key=lambda path: len(path.parts))
    kept: list[Path] = []
    for path in dirs:
        if any(earlier == path or earlier in path.parents for earlier in kept):
            continue
        kept.append(path)
    argv: list[str] = []
    for path in kept:
        argv.extend(["--tmpfs", str(path)])
    covered = [path for path in kept if path in wt.parents]
    if covered:
        ancestor = min(covered, key=lambda path: len(path.parts))
        current = ancestor
        for part in wt.relative_to(ancestor).parts:
            current = current / part
            argv.extend(["--dir", str(current)])
    return argv


def _gitconfig_binds(worktree: Path) -> list[tuple[str, str]]:
    target = Path.home() / ".gitconfig"
    if not target.is_file():
        return []
    empty = worktree / "tmp" / "empty-gitconfig"
    empty.parent.mkdir(parents=True, exist_ok=True)
    empty.write_text("", encoding="utf-8")
    return [(str(empty), str(target))]


def prepare_sandbox(
    cmd: list[str],
    worktree: Path,
    *,
    hide: list[str],
    endpoint: str | None,
    extra_rw: list[Path] | None = None,
    unsafe: bool = False,
) -> PreparedSandbox:
    """Build the agent argv. Loopback Ollama is proxied over a unix socket.

    --unshare-net has no route to the host's 127.0.0.1. A socket under the
    worktree tmp bridges that one port. A non-loopback endpoint cannot use
    that bridge, so the sandbox shares the net namespace and the git lockdown
    still applies. bwrap missing raises SandboxUnavailable unless unsafe.
    """
    worktree = Path(worktree)
    (worktree / "tmp").mkdir(parents=True, exist_ok=True)
    port = _loopback_port(endpoint)
    share_net = bool(endpoint) and port is None
    # Before the missing-bwrap return. Unsafe mode does not open the bridge.
    if port is not None and not share_net and (bwrap_works() or not unsafe):
        _refuse_explicit_runtime_dir()
    if not bwrap_works():
        if not unsafe:
            raise SandboxUnavailable("bwrap is not usable", reason="no-sandbox")
        if not getattr(prepare_sandbox, "_warned_unsafe", False):
            print(
                "WARN: --unsafe-no-sandbox is on and bwrap is not usable, so this run is not sandboxed",
                file=sys.stderr,
            )
            setattr(prepare_sandbox, "_warned_unsafe", True)
        return PreparedSandbox(list(cmd), "unsafe-no-sandbox", None, None)
    bridge = None
    link = None
    run_cmd = list(cmd)
    if port is not None and not share_net:
        link, sock = _socket_link(worktree)
        bridge = _Bridge()
        try:
            bridge.start(sock, port)
        except OSError:
            try:
                if link is not None:
                    link.unlink()
            except OSError:
                pass
            raise
        entry = worktree / "tmp" / "pfy-sandbox-entry.py"
        entry.write_text(_ENTRY, encoding="utf-8")
        run_cmd = ["python3", str(entry), str(sock), str(port), "--", *run_cmd]
    argv = [
        shutil.which("bwrap") or "bwrap",
        "--die-with-parent",
        "--ro-bind",
        "/",
        "/",
        "--dev",
        "/dev",
        "--proc",
        "/proc",
        "--tmpfs",
        "/tmp",
    ]
    argv.extend(_sandbox_hides(hide, worktree))
    for src, dest in _gitconfig_binds(worktree):
        argv.extend(["--ro-bind", src, dest])
    argv.extend(["--bind", str(worktree), str(worktree)])
    for extra in extra_rw or []:
        extra_path = Path(extra)
        try:
            if extra_path.is_dir() and extra_path.resolve() != worktree.resolve():
                argv.extend(["--bind", str(extra_path), str(extra_path)])
        except OSError:
            continue
    if share_net:
        argv.append("--share-net")
        mode = "bwrap-share-net"
    else:
        argv.append("--unshare-net")
        mode = "bwrap-unshare-net"
    # Pid namespace so a setsid or double-fork child dies with bwrap, and so
    # the agent cannot see or signal host pids. ipc and uts go with it.
    argv.extend(["--unshare-pid", "--unshare-ipc", "--unshare-uts"])
    argv.extend(["--chdir", str(worktree), "--"])
    argv.extend(run_cmd)
    return PreparedSandbox(argv, mode, bridge, link)


def run_sandboxed(
    cmd: list[str],
    worktree: Path,
    hide: list[str] | None = None,
    *,
    endpoint: str | None = None,
    timeout: float = 30,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    """Run cmd in the agent sandbox. Tests use this. The runner uses prepare_sandbox."""
    prepared = prepare_sandbox(
        cmd,
        Path(worktree),
        hide=list(hide or []),
        endpoint=endpoint,
        unsafe=False,
    )
    try:
        return subprocess.run(
            prepared.argv,
            cwd=str(worktree),
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    finally:
        prepared.close()


def _git_config_file(cfg: Path, key: str, value: str) -> None:
    subprocess.run(
        ["git", "config", "--file", str(cfg), key, value],
        capture_output=True,
        text=True,
        check=False,
    )


def lockdown_env(worktree: Path) -> dict[str, str]:
    hooks = worktree / "tmp" / "empty-hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    empty = worktree / "tmp" / "empty-gitconfig"
    if not empty.exists():
        empty.write_text("", encoding="utf-8")
    return {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": str(empty),
        "GIT_CONFIG_COUNT": "3",
        "GIT_CONFIG_KEY_0": "remote.origin.pushurl",
        "GIT_CONFIG_VALUE_0": PUSH_BLOCKED_URL,
        "GIT_CONFIG_KEY_1": "core.hooksPath",
        "GIT_CONFIG_VALUE_1": str(hooks),
        "GIT_CONFIG_KEY_2": "credential.helper",
        "GIT_CONFIG_VALUE_2": "",
    }


def isolate_worktree_git(worktree: Path) -> bytes | None:
    """Point a linked worktree at a sandbox git dir for the agent.

    The common config of the repo that owns the worktree is not edited.
    The sandbox has this worktree's files and no remotes, so git apply and
    git status work. pushurl is invalid, hooks are an empty directory, and
    there is no credential helper. The caller restores the saved bytes.
    That restore drops the sandbox commit. It is not the product commit.
    """
    link = worktree / ".git"
    if not link.is_file():
        return None
    saved = link.read_bytes()
    sandbox = worktree / "tmp" / "git-sandbox"
    if sandbox.exists():
        shutil.rmtree(sandbox, ignore_errors=True)
    subprocess.run(
        ["git", "init", "-q", "-b", "main", str(sandbox)],
        capture_output=True,
        text=True,
        check=False,
    )
    git_dir = sandbox / ".git"
    hooks = worktree / "tmp" / "empty-hooks"
    hooks.mkdir(parents=True, exist_ok=True)
    cfg = git_dir / "config"
    _git_config_file(cfg, "user.email", AUTHOR_EMAIL)
    _git_config_file(cfg, "user.name", AUTHOR_NAME)
    _git_config_file(cfg, "remote.origin.pushurl", PUSH_BLOCKED_URL)
    _git_config_file(cfg, "core.hooksPath", str(hooks))
    _git_config_file(cfg, "credential.helper", "")
    link.write_text("gitdir: %s\n" % git_dir.resolve(), encoding="utf-8")
    # Seed only when the gitfile really points at the sandbox. A failed swap
    # must not stage files into the caller's common git dir.
    shown = subprocess.run(
        ["git", "-C", str(worktree), "rev-parse", "--absolute-git-dir"],
        capture_output=True,
        text=True,
        check=False,
    )
    if (shown.stdout or "").strip() != str(git_dir.resolve()):
        return saved
    subprocess.run(
        ["git", "-C", str(worktree), "add", "-A", "--", ".", ":!tmp"],
        capture_output=True,
        text=True,
        check=False,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(worktree),
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "sandbox base",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return saved


def restore_worktree_git(worktree: Path, saved: bytes | None) -> None:
    if not saved:
        return
    link = worktree / ".git"
    if link.is_dir() and not link.is_symlink():
        shutil.rmtree(link, ignore_errors=True)
    elif link.exists() or link.is_symlink():
        try:
            link.unlink()
        except OSError:
            pass
    link.write_bytes(saved)


def _write_aborted(repo: Path) -> list[str]:
    notes = []
    base = repo / "pipelines" / "dogfood" / "build-local"
    if not base.is_dir():
        return notes
    for entry in sorted(base.iterdir()):
        if not entry.is_dir() or (entry / "receipt.json").is_file():
            continue
        _write_receipt(
            entry / "receipt.json",
            {
                "schema": SCHEMA,
                "id": entry.name,
                "status": "ABORTED",
                "reason": "no-receipt",
                "exit_code": EXIT_FAIL,
                "finished_at": _now(),
            },
        )
        notes.append(entry.name)
    return notes


def reap_stale(repo: Path) -> list[str]:
    """Kill groups left by a SIGKILL'd runner and write missing receipts.

    A live pid is left alone: the lock means it is not one of our runs, and
    the pid may have been recycled. A dead pid's recorded group is signalled.
    """
    notes: list[str] = []
    pid_path = repo / "tmp" / "local-build.pids.json"
    if pid_path.is_file():
        try:
            data = json.loads(pid_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        try:
            pid = int(data.get("pid") or 0)
        except (TypeError, ValueError):
            pid = 0
        if pid and pid != os.getpid() and not _alive(pid):
            for key in ("agent_pgid", "pgid"):
                try:
                    pg = int(data.get(key) or 0)
                except (TypeError, ValueError):
                    pg = 0
                _kill_pgid(pg)
            if data.get("loaded_by_run") and data.get("ollama_root") and data.get("model"):
                unload_model(str(data["ollama_root"]), str(data["model"]))
            notes.append("reaped %s" % pid)
            receipt_dir = str(data.get("receipt_dir") or "").strip()
            if receipt_dir:
                dest = Path(receipt_dir) / "receipt.json"
                if not dest.is_file():
                    try:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                    except OSError:
                        pass
                    if dest.parent.is_dir():
                        _write_receipt(
                            dest,
                            {
                                "schema": SCHEMA,
                                "id": dest.parent.name,
                                "status": "ABORTED",
                                "reason": "no-receipt",
                                "exit_code": EXIT_FAIL,
                                "finished_at": _now(),
                            },
                        )
                        notes.append("aborted %s" % dest.parent.name)
        if pid != os.getpid():
            try:
                pid_path.unlink()
            except OSError:
                pass
    for name in _write_aborted(repo):
        notes.append("aborted %s" % name)
    return notes


def _reap_only(args) -> int:
    try:
        repo = resolve_repo(args.repo)
    except UsageError as exc:
        print("FAIL: %s" % exc, file=sys.stderr)
        return EXIT_USAGE
    lock_path = repo / "tmp" / "local-build.lock"
    fd = _acquire_lock(lock_path)
    if fd is None:
        print("BLOCKED: another run", file=sys.stderr)
        return EXIT_BLOCKED
    try:
        notes = reap_stale(repo)
        print("reaped: %s" % (", ".join(notes) or "none"))
        return EXIT_OK
    finally:
        try:
            lock_path.unlink()
        except OSError:
            pass
        _release_lock(fd)


def tree_digest(worktree: Path) -> str:
    """Hash the worktree the gate just accepted. tmp and bytecode are excluded."""
    digest = hashlib.sha256()
    files: list[tuple[str, Path]] = []
    skip_dirs = {".git", "tmp", "__pycache__", ".pytest_cache"}
    if not worktree.is_dir():
        return digest.hexdigest()
    for dirpath, dirnames, filenames in os.walk(worktree):
        dirnames[:] = [name for name in dirnames if name not in skip_dirs and not name.endswith(".home")]
        for name in filenames:
            if name.endswith(".pyc") or name.endswith(".pyo"):
                continue
            full = Path(dirpath) / name
            try:
                rel = _norm_rel(str(full.relative_to(worktree)))
            except ValueError:
                continue
            if not rel or rel.startswith("tmp/"):
                continue
            files.append((rel, full))
    for rel, full in sorted(files):
        digest.update(rel.encode())
        digest.update(b"\0")
        try:
            digest.update(full.read_bytes())
        except OSError:
            digest.update(b"")
        digest.update(b"\0")
    return digest.hexdigest()


def _materialize_commit(worktree: Path, sha: str, dest: Path) -> bool:
    """Extract the commit into dest. This is the tree git will serve, not the worktree."""
    dest.mkdir(parents=True, exist_ok=True)
    archived = subprocess.run(
        ["git", "-C", str(worktree), "archive", sha],
        capture_output=True,
        check=False,
    )
    if archived.returncode != 0 or not archived.stdout:
        return False
    extracted = subprocess.run(
        ["tar", "-x", "-C", str(dest)],
        input=archived.stdout,
        capture_output=True,
        check=False,
    )
    return extracted.returncode == 0


def _rollback_head(worktree: Path, env: dict) -> None:
    _git(worktree, ["reset", "--hard", "HEAD~1"], env=env)


def _recheck_commit(
    repo: Path,
    worktree: Path,
    sha: str,
    cmd: str,
    env: dict,
    timeout: float,
    state: State,
    before: dict,
    unsafe: bool,
) -> str | None:
    """Run the gate on a fresh extract of sha. None means it passed."""
    if not sha:
        return "fail"
    dest = repo / "tmp" / ("recheck-" + sha[:12])
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    try:
        if not _materialize_commit(worktree, sha, dest):
            return "fail"
        rec = run_tests(cmd, dest, env, timeout, state, repo=repo, unsafe=unsafe)
        if rec.get("aborted") == "interrupted" or state.interrupted:
            return "interrupted"
        if rec.get("aborted") == "mem-edge" or state.mem_edge:
            return "fail"
        if judge_tests(before, rec):
            return "fail"
        return None
    finally:
        shutil.rmtree(dest, ignore_errors=True)


def _write_pidfile(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(tmp, path)


def _mark_loaded(state: State, loaded_by_run: bool) -> None:
    path = state.pid_path
    if path is None or not path.is_file():
        return
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(current, dict):
            return
        current["loaded_by_run"] = loaded_by_run
        _write_pidfile(path, current)
    except (OSError, json.JSONDecodeError):
        pass


def _cleanup_runtime(home: Path | None, lock_path: Path | None, pid_path: Path | None) -> None:
    if home is not None and home.exists():
        shutil.rmtree(home, ignore_errors=True)
    if pid_path is not None and pid_path.exists():
        try:
            pid_path.unlink()
        except OSError:
            pass
    if lock_path is not None and lock_path.exists():
        try:
            lock_path.unlink()
        except OSError:
            pass


def _can_retry(review: bool, used: int, maximum: int, why: str) -> bool:
    return bool(review) and used < maximum and why in _RETRYABLE


def _task_allow(task: str, extra: list[str] | None) -> tuple[list[str], bool]:
    declared = False
    patterns: list[str] = []
    for item in extra or []:
        text = (item or "").strip()
        if text:
            patterns.append(text)
            declared = True
    for match in _FILES_LINE.finditer(task or ""):
        declared = True
        for part in match.group(1).split(","):
            part = part.strip()
            if part:
                patterns.append(part)
    return patterns, declared


def _wiring_rules(task: str, flags: list[str] | None) -> list[tuple[str, list[str]]]:
    rules: list[tuple[str, list[str]]] = []
    for match in _REQUIRE_LINE.finditer(task or ""):
        symbol = match.group(1).strip()
        modules = [part.strip() for part in match.group(2).split(",") if part.strip()]
        if symbol and modules:
            rules.append((symbol, modules))
    for item in flags or []:
        rules.append(_parse_require_flag(item))
    return rules


def _named_by_test_cmd(rel: str, test_cmd: str) -> bool:
    rel_n = _norm_rel(rel)
    if not rel_n:
        return False
    try:
        tokens = shlex.split(test_cmd or "")
    except ValueError:
        tokens = (test_cmd or "").split()
    for token in tokens:
        if _norm_rel(token) == rel_n:
            return True
        if "." not in token or token.endswith(".py"):
            continue
        parts = token.split(".")
        if len(parts) >= 2 and parts[0] in ("tests", "test"):
            if _norm_rel("%s/%s.py" % (parts[0], parts[1])) == rel_n:
                return True
    return False


def _synthetic_new_diff(rel: str, lines: list[str]) -> str:
    body = "".join("+%s\n" % line for line in lines)
    return (
        "diff --git a/%s b/%s\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        "+++ b/%s\n"
        "@@ -0,0 +1,%d @@\n%s" % (rel, rel, rel, len(lines), body)
    )


def _collect_diff(worktree: Path, env: dict, paths: list[str]) -> tuple[str, dict]:
    proc = _git(worktree, ["diff", "HEAD", "--"], env=env)
    text = proc.stdout or ""
    num = _git(worktree, ["diff", "HEAD", "--numstat"], env=env)
    added = 0
    removed = 0
    seen: set[str] = set()
    for line in (num.stdout or "").splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        if parts[0] != "-":
            try:
                added += int(parts[0])
            except ValueError:
                pass
        if parts[1] != "-":
            try:
                removed += int(parts[1])
            except ValueError:
                pass
        seen.add(parts[2].replace("\\", "/"))
    for rel in paths:
        norm = _norm_rel(rel)
        if not norm or norm in seen:
            continue
        full = worktree / norm
        if not full.is_file():
            continue
        try:
            content = full.read_text(encoding="utf-8", errors="replace")
        except OSError:
            content = ""
        lines = content.splitlines()
        added += len(lines)
        text += _synthetic_new_diff(norm, lines)
    stats = {
        "files": len(paths),
        "added": added,
        "removed": removed,
        "lines": added + removed,
        "paths": list(paths),
    }
    return text, stats


def _added_text_for(diff_text: str, rel: str) -> str:
    target = _norm_rel(rel)
    if not target:
        return ""
    blobs: list[str] = []
    for part in re.split(r"(?m)^diff --git ", diff_text or ""):
        lines = part.splitlines()
        if not lines:
            continue
        head = lines[0]
        path = head.split(" b/")[-1].strip()
        if path != target:
            continue
        for line in lines[1:]:
            if line.startswith("+") and not line.startswith("+++"):
                blobs.append(line[1:])
    return "\n".join(blobs)


def _check_scope(paths: list[str], patterns: list[str], declared: bool) -> dict:
    if not declared:
        return {"ok": True, "outside": [], "skipped": "no-allow-list", "patterns": []}
    outside = [path for path in paths if not _protected(path, patterns)]
    return {"ok": not outside, "outside": outside, "skipped": None, "patterns": list(patterns)}


def _check_size(paths: list[str], diff_stats: dict, test_cmd: str, max_files: int, max_lines: int) -> dict:
    counted = [path for path in paths if not _named_by_test_cmd(path, test_cmd)]
    files_n = len(counted)
    lines_n = int(diff_stats.get("lines") or 0)
    return {
        "ok": files_n <= max_files and lines_n <= max_lines,
        "files": files_n,
        "lines": lines_n,
        "max_files": max_files,
        "max_lines": max_lines,
        "counted_paths": counted,
    }


def _check_wiring(diff_text: str, rules: list[tuple[str, list[str]]]) -> dict:
    missing: list[str] = []
    for symbol, modules in rules:
        for module in modules:
            if symbol not in _added_text_for(diff_text, module):
                missing.append("missing wiring for %s in %s" % (symbol, module))
    return {
        "ok": not missing,
        "missing": missing,
        "rules": [{"symbol": symbol, "modules": modules} for symbol, modules in rules],
    }


def _reject_reasons(scope: dict, size: dict, wiring: dict) -> list[str]:
    reasons: list[str] = []
    for path in scope.get("outside") or []:
        reasons.append("path outside allowed set: %s" % path)
    if not size.get("ok"):
        reasons.append(
            "changed files %d (max %d), changed lines %d (max %d)"
            % (size.get("files"), size.get("max_files"), size.get("lines"), size.get("max_lines"))
        )
    reasons.extend(wiring.get("missing") or [])
    return reasons


def _gate_feedback(why: str, record: dict | None) -> str:
    tail = ""
    if isinstance(record, dict):
        tail = str(record.get("tail") or "")
    return "gate failed: %s\n%s" % (why, tail)


def _review_prompt(task: str, diff_text: str, gate_tail: str) -> str:
    return (
        "%s\n"
        "Reply with JSON only, no markdown: "
        '{"verdict": "accept" or "reject", "reasons": ["..."]}\n'
        "Accept only when the change does exactly what the task says, at the place the task names, "
        "without widening behavior. A green test can still be wrong if the change applies to a "
        "broader block than the task names.\n\n"
        "Task:\n%s\n\nDiff:\n%s\n\nGate:\n%s\n"
        % (REVIEW_MARKER, (task or "")[:4000], (diff_text or "")[:DIFF_PROMPT_CAP], (gate_tail or "")[:2000])
    )


def _parse_verdict(text: str) -> tuple[str, list[str], str]:
    raw = (text or "").strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
    blob = fenced.group(1) if fenced else raw
    start = blob.find("{")
    end = blob.rfind("}")
    if start < 0 or end <= start:
        return "reject", ["review-unparseable"], raw[:500]
    try:
        data = json.loads(blob[start : end + 1])
    except json.JSONDecodeError:
        return "reject", ["review-unparseable"], raw[:500]
    if not isinstance(data, dict):
        return "reject", ["review-unparseable"], raw[:500]
    verdict = data.get("verdict")
    reasons = data.get("reasons")
    if verdict not in ("accept", "reject") or not isinstance(reasons, list):
        return "reject", ["review-unparseable"], raw[:500]
    if not all(isinstance(item, str) for item in reasons):
        return "reject", ["review-unparseable"], raw[:500]
    return verdict, reasons, raw[:500]


def _content_from_model_body(raw: str) -> str:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw or ""
    if not isinstance(data, dict):
        return raw or ""
    if data.get("error"):
        return ""
    choices = data.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        message = choices[0].get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                bits = []
                for part in content:
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        bits.append(part["text"])
                if bits:
                    return "\n".join(bits)
    response = data.get("response")
    if isinstance(response, str):
        return response
    return raw or ""


_REVIEW_POSTER = """\
import json
import os
import urllib.request

url = os.environ["OPENAI_BASE_URL"].rstrip("/") + "/chat/completions"
body = json.loads(open(os.environ["PFY_REVIEW_BODY"], encoding="utf-8").read())
data = json.dumps(body).encode("utf-8")
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
timeout = float(os.environ.get("PFY_REVIEW_HTTP_TIMEOUT") or "60")
out = os.environ["PFY_REVIEW_OUT"]
try:
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", "replace")
except Exception as exc:
    raw = json.dumps({"error": "%s" % exc})
open(out, "w", encoding="utf-8").write(raw)
"""


def _mem_sample() -> float | None:
    info = read_meminfo()
    if not info:
        return None
    return mem_available_gib(info)


def _attempt_low(state: State, snap: float | None) -> float | None:
    values = []
    now = _mem_sample()
    for item in (snap, now):
        if isinstance(item, (int, float)):
            values.append(float(item))
    if isinstance(state.min_avail, (int, float)) and (snap is None or state.min_avail < snap):
        values.append(float(state.min_avail))
    if not values:
        return None
    return round(min(values), 3)


def _stub_extra_rw() -> list[Path]:
    """Parents of the test stub's plan files. A normal run sets none of these.

    The sandbox root is read-only, so the stub cannot record the prompt or the
    attempt counter unless those files' directory is bound read-write. The
    agent cannot add binds of its own: this list is fixed before it starts.
    """
    found: list[Path] = []
    seen: set[str] = set()
    for key in ("PFY_STUB_PLAN", "PFY_STUB_COUNT", "PFY_STUB_PROMPTS"):
        raw = os.environ.get(key) or ""
        if not raw:
            continue
        path = Path(raw)
        parent = path if path.is_dir() else path.parent
        try:
            if not parent.is_dir():
                continue
            resolved = parent.resolve()
        except OSError:
            continue
        text = str(resolved)
        if text in seen or resolved == Path("/"):
            continue
        seen.add(text)
        found.append(resolved)
    return found


def _drop_worktree(repo: Path, worktree: Path | None) -> None:
    if worktree is None:
        return
    _git(repo, ["worktree", "remove", "--force", str(worktree)])
    if worktree.exists():
        shutil.rmtree(worktree, ignore_errors=True)
    _git(repo, ["worktree", "prune"])


def _run_model_review(
    args,
    worktree: Path,
    openai_base: str,
    task: str,
    diff_text: str,
    gate_tail: str,
    state: State,
    repo: Path,
) -> tuple[str, dict | None]:
    """Return (status, review). status is accept, reject, timeout, interrupted, mem-edge, blocked, sandbox."""
    port = _loopback_port(openai_base)
    if port is None:
        return "blocked", {
            "verdict": "reject",
            "reasons": ["review-endpoint-not-local"],
            "raw_tail": "",
        }
    prompt = _review_prompt(task, redact(diff_text), redact(gate_tail or ""))
    body = {
        "model": args.model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "stream": False,
    }
    tmp = worktree / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "review-home").mkdir(parents=True, exist_ok=True)
    body_path = tmp / "pfy-review-body.json"
    out_path = tmp / "pfy-review-out.json"
    script_path = tmp / "pfy-review-post.py"
    if out_path.exists():
        out_path.unlink()
    body_path.write_text(json.dumps(body), encoding="utf-8")
    script_path.write_text(_REVIEW_POSTER, encoding="utf-8")
    child = _child_env(
        {
            "TMPDIR": str(tmp),
            "HOME": str(tmp / "review-home"),
            "PYTHONDONTWRITEBYTECODE": "1",
            "OPENAI_BASE_URL": openai_base,
            "PFY_REVIEW_BODY": str(body_path),
            "PFY_REVIEW_OUT": str(out_path),
            "PFY_REVIEW_HTTP_TIMEOUT": str(float(args.timeout_s) + 30.0),
        }
    )
    try:
        prepared = prepare_sandbox(
            ["python3", str(script_path)],
            worktree,
            hide=hide_paths(repo, worktree),
            endpoint=openai_base,
            unsafe=bool(args.unsafe_no_sandbox),
        )
    except SandboxUnavailable as exc:
        return "sandbox", {"verdict": "reject", "reasons": [exc.reason], "raw_tail": str(exc)}
    if prepared.mode == "bwrap-unshare-net":
        child["OPENAI_BASE_URL"] = "http://127.0.0.1:%d/v1" % port
    child.update(lockdown_env(worktree))
    try:
        run_status, _code, out, err = run_bounded(
            prepared.argv, child, worktree, float(args.timeout_s), state
        )
    finally:
        prepared.close()
    if run_status == "timeout":
        return "timeout", None
    if run_status == "interrupted":
        return "interrupted", None
    if run_status == "mem-edge":
        return "mem-edge", None
    raw = ""
    try:
        raw = out_path.read_text(encoding="utf-8")
    except OSError:
        raw = (out or "") + (err or "")
    content = _content_from_model_body(raw)
    verdict, reasons, raw_tail = _parse_verdict(content)
    return verdict, {"verdict": verdict, "reasons": reasons, "raw_tail": redact(raw_tail)[:500]}


def build_local(argv: list[str] | None = None) -> int:
    state = State()
    _install_signals(state)
    try:
        args = parse_args(argv)
    except UsageError as exc:
        print("FAIL: %s" % exc, file=sys.stderr)
        return EXIT_USAGE

    if args.reap and not args.task_text:
        return _reap_only(args)

    started = time.monotonic()
    started_at = _now()
    stamp = _stamp()
    slug = _slug(args.task_text)
    receipt_path: Path | None = None
    home: Path | None = None
    worktree: Path | None = None
    branch: str | None = None
    commit: str | None = None
    status = "FAIL"
    reason = "runner-crash"
    exit_code = EXIT_FAIL
    tests_before = None
    tests_after = None
    changed: list[str] = []
    agent_log: Path | None = None
    agent_seconds = 0.0
    attempts_used = 0
    attempt_receipts: list[str] = []
    model_was_loaded = False
    unloaded = False
    agent_started = False
    opencode_version = None
    base_ref = None
    base_sha = None
    repo = None
    ollama_root = None
    sandbox_mode = None
    lock_path: Path | None = None
    pid_path: Path | None = None
    git_saved: bytes | None = None
    prepared: PreparedSandbox | None = None
    test_snapshot: dict[str, str] = {}
    mem_start = read_meminfo()
    state.min_avail = mem_available_gib(mem_start)
    stop_watch = threading.Event()
    watcher = None

    def finish() -> int:
        nonlocal unloaded, git_saved, prepared
        if git_saved is not None and worktree is not None:
            restore_worktree_git(worktree, git_saved)
            git_saved = None
        if prepared is not None:
            prepared.close()
            prepared = None
        finished_at = _now()
        if receipt_path is not None:
            payload = {
                "schema": SCHEMA,
                "id": stamp + "-" + slug,
                "task": redact(args.task_text)[:500],
                "repo": None if repo is None else str(repo),
                "base_sha": base_sha,
                "model": args.model_name,
                "endpoint": _host_only(args.endpoint_raw),
                "status": status,
                "reason": reason,
                "exit_code": exit_code,
                "wall_seconds": round(time.monotonic() - started, 3),
                "agent_seconds": round(agent_seconds, 3),
                "tests_before": _public_test(tests_before),
                "tests_after": _public_test(tests_after),
                "files_changed": changed,
                "attempts": attempts_used,
                "review": {
                    "enabled": bool(args.review),
                    "retries": int(args.retries_n),
                    "max_files": int(args.max_files_n),
                    "max_lines": int(args.max_lines_n),
                    "allow_path": list(args.allow_path or []),
                    "require_wiring": list(args.require_wiring or []),
                },
                "attempt_receipts": list(attempt_receipts),
                "branch": branch,
                "commit": commit,
                "worktree": None if worktree is None else str(worktree),
                "model_was_loaded": model_was_loaded,
                "unloaded": unloaded,
                "mem": {
                    "mem_available_gb": round(mem_available_gib(mem_start), 3),
                    "swap_free_gb": round(gib(_kb(mem_start, "SwapFree")), 3),
                    "min_available_gb": None if state.min_avail is None else round(state.min_avail, 3),
                },
                "opencode_version": opencode_version,
                "agent_log": None if agent_log is None else str(agent_log),
                "sandbox": sandbox_mode,
                "started_at": started_at,
                "finished_at": finished_at,
            }
            _write_receipt(receipt_path, payload)
            print(_summary(status, reason, branch, receipt_path))
        stop_watch.set()
        if watcher is not None:
            watcher.join(timeout=1)
        if ollama_root and _should_unload():
            unloaded = unload_model(ollama_root, args.model_name)
            if receipt_path is not None and receipt_path.is_file():
                try:
                    current = json.loads(receipt_path.read_text(encoding="utf-8"))
                    current["unloaded"] = unloaded
                    _write_receipt(receipt_path, current)
                except (OSError, json.JSONDecodeError):
                    pass
        _cleanup_runtime(home, lock_path, pid_path)
        _release_lock(state.lock_fd)
        state.lock_fd = None
        return exit_code

    def _should_unload() -> bool:
        if not agent_started:
            return False
        if args.unload_at_end:
            return True
        if args.keep_model:
            return False
        return not model_was_loaded

    try:
        repo = resolve_repo(args.repo)
        base_ref = resolve_base(repo, args.base)
        sha_proc = _git(repo, ["rev-parse", base_ref])
        base_sha = (sha_proc.stdout or "").strip() or None
        ollama_root, openai_base = _endpoint_pair(args.endpoint_raw)
        if args.receipt_dir:
            receipt_dir = Path(args.receipt_dir).resolve()
        else:
            receipt_dir = repo / "pipelines" / "dogfood" / "build-local" / stamp
        receipt_path = receipt_dir / "receipt.json"

        lock_path = repo / "tmp" / "local-build.lock"
        state.lock_fd = _acquire_lock(lock_path)
        if state.lock_fd is None:
            receipt_dir.mkdir(parents=True, exist_ok=True)
            status, reason, exit_code = "BLOCKED", "another run", EXIT_BLOCKED
            return finish()
        # The previous runner may have been SIGKILL'd. Reap before this dir exists
        # so an empty directory from that run becomes ABORTED, not this one.
        reap_stale(repo)
        receipt_dir.mkdir(parents=True, exist_ok=True)

        if state.interrupted:
            status, reason, exit_code = "FAIL", "interrupted", EXIT_FAIL
            return finish()

        free = free_ram_plus_swap_gib(mem_start)
        if free < args.min_free:
            status, reason, exit_code = "BLOCKED", "mem", EXIT_BLOCKED
            return finish()

        binary = _which_opencode(os.environ)
        if not binary:
            print("BLOCKED: no-opencode", file=sys.stderr)
            print("  next: ./pfy attach opencode", file=sys.stderr)
            status, reason, exit_code = "BLOCKED", "no-opencode", EXIT_USAGE
            return finish()

        if _is_cloud_tag(args.model_name):
            status, reason, exit_code = "BLOCKED", "cloud-tag", EXIT_BLOCKED
            return finish()

        tags, tag_err = _ollama_tags(ollama_root)
        if tag_err or tags is None:
            status, reason, exit_code = "BLOCKED", "no-model", EXIT_BLOCKED
            return finish()
        tag = _tag_of(args.model_name, tags)
        if tag is None:
            status, reason, exit_code = "BLOCKED", "no-model", EXIT_BLOCKED
            return finish()
        size = _model_size(tag)
        if size is not None and size > MAX_MODEL_BYTES:
            status, reason, exit_code = "BLOCKED", "model-too-big", EXIT_BLOCKED
            return finish()

        loaded = _ps_names(ollama_root)
        if loaded is None:
            status, reason, exit_code = "BLOCKED", "busy-host", EXIT_BLOCKED
            return finish()
        others = [name for name in loaded if not _same_model(name, args.model_name)]
        if others:
            status, reason, exit_code = "BLOCKED", "busy-host", EXIT_BLOCKED
            return finish()
        model_was_loaded = any(_same_model(name, args.model_name) for name in loaded)

        if args.dry_run:
            print("dry-run: repo=%s" % repo)
            print("dry-run: base=%s sha=%s" % (base_ref, base_sha))
            print("dry-run: model=%s endpoint=%s" % (args.model_name, _host_only(args.endpoint_raw)))
            print("dry-run: test_cmd=%s" % args.test_cmd_s)
            print("dry-run: min_free_gb=%s free_gib=%.3f" % (args.min_free, free))
            print("dry-run: worktree would be %s" % (repo / "tmp" / ("local-build-%s-%s" % (stamp, slug))))
            print("dry-run: start nothing, load nothing")
            status, reason, exit_code = "PASS", "dry-run", EXIT_OK
            return finish()

        (repo / "tmp").mkdir(parents=True, exist_ok=True)
        (receipt_dir / "version-home").mkdir(parents=True, exist_ok=True)
        ver = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
            stdin=subprocess.DEVNULL,
            env=_scrub(os.environ, HOME=str(receipt_dir / "version-home"), TMPDIR=str(repo / "tmp")),
        )
        opencode_version = redact(((ver.stdout or "") + (ver.stderr or "")).strip().splitlines()[0] if (ver.stdout or ver.stderr) else "") or None

        wt_path = repo / "tmp" / ("local-build-%s-%s" % (stamp, slug))
        if wt_path.exists():
            status, reason, exit_code = "FAIL", "worktree-exists", EXIT_FAIL
            return finish()
        (repo / "tmp").mkdir(parents=True, exist_ok=True)

        max_attempts = 1 if not args.review else 1 + int(args.retries_n)
        feedback = ""
        previous_diff = ""
        commit_ready = False
        pid_written = False
        watcher_started = False
        allow_patterns, allow_declared = _task_allow(args.task_text, list(args.allow_path or []))
        wiring_rules = _wiring_rules(args.task_text, list(args.require_wiring or []))

        def _record_attempt(number, t0, mem_snap, attempt_status, attempt_reason, checks, model_review, diff_stats, diff_text):
            if not args.review:
                return
            payload = {
                "schema": SCHEMA,
                "attempt": number,
                "status": attempt_status,
                "reason": attempt_reason,
                "tests_before": _public_test(tests_before),
                "tests_after": _public_test(tests_after),
                "diff_stats": diff_stats,
                "checks": checks,
                "model_review": model_review,
                "wall_seconds": round(time.monotonic() - t0, 3),
                "mem_min_available_gb": _attempt_low(state, mem_snap),
            }
            dest = receipt_dir / ("attempt-%d" % number) / "receipt.json"
            _write_receipt(dest, payload)
            attempt_receipts.append(str(dest))
            if diff_text:
                try:
                    (dest.parent / "patch.diff").write_text(redact(diff_text), encoding="utf-8")
                except OSError:
                    pass

        while attempts_used < max_attempts:
            attempts_used += 1
            attempt_t0 = time.monotonic()
            mem_snap = state.min_avail
            sample = _mem_sample()
            if isinstance(sample, (int, float)) and (mem_snap is None or sample < mem_snap):
                mem_snap = sample
            tests_before = None
            tests_after = None
            changed = []
            diff_text = ""
            diff_stats = {"files": 0, "added": 0, "removed": 0, "lines": 0, "paths": []}
            checks = None
            model_review = None

            if worktree is not None:
                if git_saved is not None:
                    restore_worktree_git(worktree, git_saved)
                    git_saved = None
                if prepared is not None:
                    prepared.close()
                    prepared = None
                _drop_worktree(repo, worktree)
                worktree = None

            added = _git(repo, ["worktree", "add", "--detach", str(wt_path), base_ref])
            if added.returncode != 0:
                status, reason, exit_code = "FAIL", "worktree-failed", EXIT_FAIL
                _record_attempt(attempts_used, attempt_t0, mem_snap, "FAIL", "worktree-failed", None, None, diff_stats, "")
                return finish()
            worktree = wt_path
            home = worktree / "tmp" / "opencode.home"
            _ensure_tmp_excluded(worktree, _child_env({"TMPDIR": str(worktree / "tmp")}))
            (worktree / "tmp").mkdir(parents=True, exist_ok=True)
            if not pid_written:
                pid_path = repo / "tmp" / "local-build.pids.json"
                state.pid_path = pid_path
                _write_pidfile(
                    pid_path,
                    {
                        "pid": os.getpid(),
                        "pgid": os.getpgrp(),
                        "agent_pgid": None,
                        "model": args.model_name,
                        "ollama_root": ollama_root,
                        "loaded_by_run": False,
                        "receipt_dir": str(receipt_dir),
                    },
                )
                pid_written = True
            test_env = _child_env(
                {
                    "TMPDIR": str(worktree / "tmp"),
                    "HOME": str(home / "home"),
                    "PYTHONDONTWRITEBYTECODE": "1",
                }
            )
            home.mkdir(parents=True, exist_ok=True)
            _prepare_home(home)
            try:
                if _loopback_port(openai_base) is not None and not args.unsafe_no_sandbox:
                    _refuse_explicit_runtime_dir()
            except SandboxUnavailable as exc:
                print("BLOCKED: %s" % exc, file=sys.stderr)
                status, reason, exit_code = "BLOCKED", exc.reason, EXIT_BLOCKED
                _record_attempt(attempts_used, attempt_t0, mem_snap, "BLOCKED", exc.reason, None, None, diff_stats, "")
                return finish()
            if not watcher_started:
                watcher = threading.Thread(target=_watchdog, args=(stop_watch, state), daemon=True)
                watcher.start()
                watcher_started = True

            tests_before = run_tests(
                args.test_cmd_s,
                worktree,
                test_env,
                args.test_timeout_s,
                state,
                repo=repo,
                unsafe=bool(args.unsafe_no_sandbox),
            )
            if tests_before.get("aborted") == "interrupted" or state.interrupted:
                status, reason, exit_code = "FAIL", "interrupted", EXIT_FAIL
                _record_attempt(attempts_used, attempt_t0, mem_snap, "FAIL", "interrupted", None, None, diff_stats, "")
                return finish()
            if tests_before.get("aborted") == "mem-edge" or state.mem_edge:
                status, reason, exit_code = "FAIL", "mem-edge", EXIT_FAIL
                _record_attempt(attempts_used, attempt_t0, mem_snap, "FAIL", "mem-edge", None, None, diff_stats, "")
                return finish()
            if not tests_before.get("started"):
                status, reason, exit_code = "FAIL", "test-cmd-failed-to-start", EXIT_FAIL
                _record_attempt(
                    attempts_used, attempt_t0, mem_snap, "FAIL", "test-cmd-failed-to-start", None, None, diff_stats, ""
                )
                return finish()

            test_snapshot = snapshot_tests(worktree, args.test_cmd_s)
            config = _write_config(home, openai_base, args.model_name)
            try:
                shutil.copy(config, receipt_dir / "opencode.json")
            except OSError:
                pass
            child = _opencode_env(home, worktree, openai_base, config)
            child.update(lockdown_env(worktree))
            prompt = _agent_prompt(args.task_text, args.test_cmd_s, feedback, previous_diff)
            cmd = [binary, "run", "--pure", "--model", "ollama/%s" % args.model_name, "--variant", "none", prompt]
            git_saved = isolate_worktree_git(worktree)
            try:
                prepared = prepare_sandbox(
                    cmd,
                    worktree,
                    hide=hide_paths(repo, worktree),
                    endpoint=openai_base,
                    extra_rw=_stub_extra_rw(),
                    unsafe=bool(args.unsafe_no_sandbox),
                )
            except SandboxUnavailable as exc:
                print("BLOCKED: %s" % exc, file=sys.stderr)
                status, reason, exit_code = "BLOCKED", exc.reason, EXIT_BLOCKED
                _record_attempt(attempts_used, attempt_t0, mem_snap, "BLOCKED", exc.reason, None, None, diff_stats, "")
                return finish()
            sandbox_mode = prepared.mode
            if sandbox_mode == "bwrap-unshare-net":
                port = _loopback_port(openai_base)
                if port:
                    child["OPENAI_BASE_URL"] = "http://127.0.0.1:%d/v1" % port
            agent_started = True
            _mark_loaded(state, not model_was_loaded)
            agent_t0 = time.monotonic()
            run_status, _code, out, err = run_bounded(prepared.argv, child, worktree, args.timeout_s, state)
            agent_seconds += time.monotonic() - agent_t0
            prepared.close()
            prepared = None
            if git_saved is not None:
                restore_worktree_git(worktree, git_saved)
                git_saved = None
            blob = "----- attempt %d stdout -----\n%s\n----- stderr -----\n%s\n" % (
                attempts_used,
                redact(out),
                redact(err),
            )
            agent_log = receipt_dir / "agent.log"
            if agent_log.is_file():
                with agent_log.open("a", encoding="utf-8") as handle:
                    handle.write(blob)
            else:
                agent_log.write_text(blob, encoding="utf-8")

            if os.environ.get("PFY_LOCAL_BUILD_INJECT_CRASH") == "post" and run_status == "done":
                raise RuntimeError("injected post crash")

            if run_status == "interrupted" or state.interrupted:
                status, reason, exit_code = "FAIL", "interrupted", EXIT_FAIL
                _record_attempt(attempts_used, attempt_t0, mem_snap, "FAIL", "interrupted", None, None, diff_stats, "")
                return finish()
            if run_status == "mem-edge" or state.mem_edge:
                status, reason, exit_code = "FAIL", "mem-edge", EXIT_FAIL
                _record_attempt(attempts_used, attempt_t0, mem_snap, "FAIL", "mem-edge", None, None, diff_stats, "")
                return finish()
            if run_status == "timeout" and not args.run_tests_on_timeout:
                status, reason, exit_code = "TIMEOUT", "timeout", EXIT_TIMEOUT
                _record_attempt(attempts_used, attempt_t0, mem_snap, "TIMEOUT", "timeout", None, None, diff_stats, "")
                return finish()

            changed = files_changed(worktree, test_env)
            diff_text, diff_stats = _collect_diff(worktree, test_env, changed)
            if not changed:
                if _can_retry(args.review, attempts_used, max_attempts, "no-change"):
                    _record_attempt(attempts_used, attempt_t0, mem_snap, "FAIL", "no-change", None, None, diff_stats, diff_text)
                    feedback = "no-change"
                    previous_diff = diff_text
                    continue
                status, reason, exit_code = "FAIL", "no-change", EXIT_FAIL
                _record_attempt(attempts_used, attempt_t0, mem_snap, "FAIL", "no-change", None, None, diff_stats, diff_text)
                return finish()
            protected_hits = [path for path in changed if _protected(path, args.protect or [])]
            if protected_hits:
                feedback = "protected-path-changed: %s" % ", ".join(protected_hits)
                if _can_retry(args.review, attempts_used, max_attempts, "protected-path-changed"):
                    _record_attempt(
                        attempts_used, attempt_t0, mem_snap, "FAIL", "protected-path-changed", None, None, diff_stats, diff_text
                    )
                    previous_diff = diff_text
                    continue
                status, reason, exit_code = "FAIL", "protected-path-changed", EXIT_FAIL
                _record_attempt(
                    attempts_used, attempt_t0, mem_snap, "FAIL", "protected-path-changed", None, None, diff_stats, diff_text
                )
                return finish()

            tests_after = run_tests(
                args.test_cmd_s,
                worktree,
                test_env,
                args.test_timeout_s,
                state,
                repo=repo,
                unsafe=bool(args.unsafe_no_sandbox),
            )
            if tests_after.get("aborted") == "interrupted" or state.interrupted:
                status, reason, exit_code = "FAIL", "interrupted", EXIT_FAIL
                _record_attempt(attempts_used, attempt_t0, mem_snap, "FAIL", "interrupted", None, None, diff_stats, diff_text)
                return finish()
            gate = judge_tests(tests_before, tests_after)
            if gate:
                feedback = _gate_feedback(gate, tests_after)
                if _can_retry(args.review, attempts_used, max_attempts, gate):
                    _record_attempt(attempts_used, attempt_t0, mem_snap, "FAIL", gate, None, None, diff_stats, diff_text)
                    previous_diff = diff_text
                    continue
                status, reason, exit_code = "FAIL", gate, EXIT_FAIL
                _record_attempt(attempts_used, attempt_t0, mem_snap, "FAIL", gate, None, None, diff_stats, diff_text)
                return finish()
            tampered = tests_tampered(worktree, test_snapshot, list(args.writable_test or []))
            if tampered:
                feedback = "gate failed: tests-tampered\n%s" % "\n".join(tampered)
                if _can_retry(args.review, attempts_used, max_attempts, "tests-tampered"):
                    _record_attempt(
                        attempts_used, attempt_t0, mem_snap, "FAIL", "tests-tampered", None, None, diff_stats, diff_text
                    )
                    previous_diff = diff_text
                    continue
                status, reason, exit_code = "FAIL", "tests-tampered", EXIT_FAIL
                _record_attempt(
                    attempts_used, attempt_t0, mem_snap, "FAIL", "tests-tampered", None, None, diff_stats, diff_text
                )
                return finish()
            again = run_tests(
                args.test_cmd_s,
                worktree,
                test_env,
                args.test_timeout_s,
                state,
                repo=repo,
                unsafe=bool(args.unsafe_no_sandbox),
            )
            if again.get("aborted") == "interrupted" or state.interrupted:
                status, reason, exit_code = "FAIL", "interrupted", EXIT_FAIL
                _record_attempt(attempts_used, attempt_t0, mem_snap, "FAIL", "interrupted", None, None, diff_stats, diff_text)
                return finish()
            if again.get("aborted") == "mem-edge" or state.mem_edge:
                status, reason, exit_code = "FAIL", "mem-edge", EXIT_FAIL
                _record_attempt(attempts_used, attempt_t0, mem_snap, "FAIL", "mem-edge", None, None, diff_stats, diff_text)
                return finish()
            flaky = judge_tests(tests_before, again)
            if flaky:
                feedback = _gate_feedback("tests-flaky", again)
                if _can_retry(args.review, attempts_used, max_attempts, "tests-flaky"):
                    _record_attempt(attempts_used, attempt_t0, mem_snap, "FAIL", "tests-flaky", None, None, diff_stats, diff_text)
                    previous_diff = diff_text
                    continue
                status, reason, exit_code = "FAIL", "tests-flaky", EXIT_FAIL
                _record_attempt(attempts_used, attempt_t0, mem_snap, "FAIL", "tests-flaky", None, None, diff_stats, diff_text)
                return finish()
            gated_tree = tree_digest(worktree)
            if run_status == "timeout":
                status, reason, exit_code = "TIMEOUT", "timeout", EXIT_TIMEOUT
                _record_attempt(attempts_used, attempt_t0, mem_snap, "TIMEOUT", "timeout", None, None, diff_stats, diff_text)
                return finish()
            if tree_digest(worktree) != gated_tree:
                status, reason, exit_code = "FAIL", "worktree-changed-after-gate", EXIT_FAIL
                _record_attempt(
                    attempts_used,
                    attempt_t0,
                    mem_snap,
                    "FAIL",
                    "worktree-changed-after-gate",
                    None,
                    None,
                    diff_stats,
                    diff_text,
                )
                return finish()

            if not args.review:
                commit_ready = True
                break

            scope = _check_scope(changed, allow_patterns, allow_declared)
            size = _check_size(changed, diff_stats, args.test_cmd_s, args.max_files_n, args.max_lines_n)
            wire = _check_wiring(diff_text, wiring_rules)
            checks = {"scope": scope, "size": size, "wiring": wire}
            reasons = _reject_reasons(scope, size, wire)
            if reasons:
                feedback = "\n".join(reasons)
                previous_diff = diff_text
                if attempts_used >= max_attempts:
                    status, reason, exit_code = "PASS-REJECTED", "review-rejected", EXIT_FAIL
                    _record_attempt(
                        attempts_used, attempt_t0, mem_snap, "PASS-REJECTED", "review-rejected", checks, None, diff_stats, diff_text
                    )
                    return finish()
                _record_attempt(
                    attempts_used, attempt_t0, mem_snap, "PASS-REJECTED", "review-rejected", checks, None, diff_stats, diff_text
                )
                continue

            gate_tail = str(tests_after.get("tail") or "") if isinstance(tests_after, dict) else ""
            review_status, model_review = _run_model_review(
                args,
                worktree,
                openai_base,
                args.task_text,
                diff_text,
                gate_tail,
                state,
                repo,
            )
            if review_status == "timeout":
                status, reason, exit_code = "TIMEOUT", "timeout", EXIT_TIMEOUT
                _record_attempt(attempts_used, attempt_t0, mem_snap, "TIMEOUT", "timeout", checks, model_review, diff_stats, diff_text)
                return finish()
            if review_status == "interrupted" or state.interrupted:
                status, reason, exit_code = "FAIL", "interrupted", EXIT_FAIL
                _record_attempt(attempts_used, attempt_t0, mem_snap, "FAIL", "interrupted", checks, model_review, diff_stats, diff_text)
                return finish()
            if review_status == "mem-edge" or state.mem_edge:
                status, reason, exit_code = "FAIL", "mem-edge", EXIT_FAIL
                _record_attempt(attempts_used, attempt_t0, mem_snap, "FAIL", "mem-edge", checks, model_review, diff_stats, diff_text)
                return finish()
            if review_status == "blocked":
                status, reason, exit_code = "BLOCKED", "review-endpoint-not-local", EXIT_BLOCKED
                _record_attempt(
                    attempts_used,
                    attempt_t0,
                    mem_snap,
                    "BLOCKED",
                    "review-endpoint-not-local",
                    checks,
                    model_review,
                    diff_stats,
                    diff_text,
                )
                return finish()
            if review_status == "sandbox":
                why = "no-sandbox"
                if isinstance(model_review, dict) and model_review.get("reasons"):
                    why = str(model_review["reasons"][0])
                print("BLOCKED: %s" % why, file=sys.stderr)
                status, reason, exit_code = "BLOCKED", why, EXIT_BLOCKED
                _record_attempt(attempts_used, attempt_t0, mem_snap, "BLOCKED", why, checks, model_review, diff_stats, diff_text)
                return finish()
            if review_status != "accept":
                feedback = "\n".join((model_review or {}).get("reasons") or ["review-unparseable"])
                previous_diff = diff_text
                if attempts_used >= max_attempts:
                    status, reason, exit_code = "PASS-REJECTED", "review-rejected", EXIT_FAIL
                    _record_attempt(
                        attempts_used,
                        attempt_t0,
                        mem_snap,
                        "PASS-REJECTED",
                        "review-rejected",
                        checks,
                        model_review,
                        diff_stats,
                        diff_text,
                    )
                    return finish()
                _record_attempt(
                    attempts_used, attempt_t0, mem_snap, "PASS-REJECTED", "review-rejected", checks, model_review, diff_stats, diff_text
                )
                continue
            if tree_digest(worktree) != gated_tree:
                status, reason, exit_code = "FAIL", "worktree-changed-after-gate", EXIT_FAIL
                _record_attempt(
                    attempts_used,
                    attempt_t0,
                    mem_snap,
                    "FAIL",
                    "worktree-changed-after-gate",
                    checks,
                    model_review,
                    diff_stats,
                    diff_text,
                )
                return finish()
            _record_attempt(attempts_used, attempt_t0, mem_snap, "PASS", "ok", checks, model_review, diff_stats, diff_text)
            commit_ready = True
            break

        if not commit_ready:
            return finish()

        commit_env = _git_env(test_env)
        title = " ".join(args.task_text.split())[:80] or "task"
        message = "%s\n\nreceipt: %s\n" % (title, stamp + "-" + slug)
        # -f so a gitignore cannot drop a file the tests imported. tmp and
        # bytecode stay out. .gitignore itself is a gate file and is hashed.
        committed = _git(
            worktree,
            [
                "add",
                "-A",
                "-f",
                "--",
                ".",
                ":!tmp",
                ":!**/__pycache__",
                ":!**/*.pyc",
                ":!.pytest_cache",
                ":!**/.pytest_cache",
            ],
            env=commit_env,
        )
        if committed.returncode != 0:
            status, reason, exit_code = "FAIL", "commit-failed", EXIT_FAIL
            return finish()
        committed = _git(worktree, ["commit", "-m", message], env=commit_env)
        if committed.returncode != 0:
            status, reason, exit_code = "FAIL", "commit-failed", EXIT_FAIL
            return finish()
        sha_now = _git(worktree, ["rev-parse", "HEAD"], env=commit_env)
        commit_sha = (sha_now.stdout or "").strip()
        recheck_status = _recheck_commit(
            repo,
            worktree,
            commit_sha,
            args.test_cmd_s,
            test_env,
            args.test_timeout_s,
            state,
            tests_before,
            bool(args.unsafe_no_sandbox),
        )
        if recheck_status == "interrupted" or state.interrupted:
            _rollback_head(worktree, commit_env)
            status, reason, exit_code = "FAIL", "interrupted", EXIT_FAIL
            return finish()
        if recheck_status:
            _rollback_head(worktree, commit_env)
            status, reason, exit_code = "FAIL", "commit-recheck-failed", EXIT_FAIL
            return finish()
        branch_name = "local/%s-%s" % (slug, stamp)
        made = _git(worktree, ["branch", branch_name, "HEAD"], env=commit_env)
        if made.returncode != 0:
            status, reason, exit_code = "FAIL", "commit-failed", EXIT_FAIL
            return finish()
        _git(worktree, ["switch", branch_name], env=commit_env)
        sha = _git(worktree, ["rev-parse", "HEAD"], env=commit_env)
        branch = branch_name
        commit = (sha.stdout or "").strip() or None
        status, reason, exit_code = "PASS", "ok", EXIT_OK
        if not args.keep_worktree:
            _git(repo, ["worktree", "remove", str(worktree)])
        return finish()
    except SandboxUnavailable as exc:
        print("BLOCKED: %s" % exc, file=sys.stderr)
        status, reason, exit_code = "BLOCKED", exc.reason, EXIT_BLOCKED
        return finish()
    except UsageError as exc:
        print("FAIL: %s" % exc, file=sys.stderr)
        status, reason, exit_code = "BLOCKED", "usage", EXIT_USAGE
        return finish()
    except Exception:
        traceback.print_exc()
        status, reason, exit_code = "FAIL", "runner-crash", EXIT_FAIL
        return finish()
    finally:
        stop_watch.set()


def main(argv: list[str] | None = None) -> int:
    return build_local(argv)


if __name__ == "__main__":
    sys.exit(main())
