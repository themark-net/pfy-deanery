#!/usr/bin/env python3
"""Report-only shadow of codebase-memory-mcp detect_changes next to test_select.

Not a gate. A missing binary, a non-zero tool exit, and a timeout are one
JSONL record. This process exits 0. PFY_CBM_SHADOW=0 skips without a record.

Host CLI (binary 0.9.0; catalog pin ee68144). Scope tests is passed through.
On that binary, scope other than "symbols" or "impact" returns changed files
and does not walk callers (upstream handle_detect_changes). A later binary
that returns a tests array is recorded too.

  CBM_CACHE_DIR=$HOME/.cache/pfy/cbm-shadow/db \\
  CBM_MEM_BUDGET_MB=8192 CBM_WORKERS=2 \\
  codebase-memory-mcp cli index_repository \\
      --repo-path $HOME/.cache/pfy/cbm-shadow/wt \\
      --name pfy-mentat-cbm-shadow --mode fast
  codebase-memory-mcp cli detect_changes \\
      --project pfy-mentat-cbm-shadow --scope tests \\
      --since <base-sha> --depth 2

The index lives under the cache and is reused. The compared tree is a
detached worktree in that cache, not the caller's checkout.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import signal
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

PROJECT = "pfy-mentat-cbm-shadow"
DEPTH = "2"
DEFAULT_TIMEOUT = 120.0
INVOCATION = (
    "codebase-memory-mcp cli detect_changes "
    "--project pfy-mentat-cbm-shadow --scope tests --since <base-sha> --depth 2"
)


def script_repo() -> Path:
    return Path(__file__).resolve().parent.parent


def cache_dir() -> Path:
    raw = os.environ.get("PFY_CBM_SHADOW_CACHE", "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".cache" / "pfy" / "cbm-shadow"


def log_path(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser()
    raw = os.environ.get("PFY_CBM_SHADOW_LOG", "").strip()
    if raw:
        return Path(raw).expanduser()
    return cache_dir() / "selections.jsonl"


def timeout_s(arg: float | None) -> float:
    if arg is not None:
        return arg
    raw = os.environ.get("PFY_CBM_SHADOW_TIMEOUT", "").strip()
    if not raw:
        return DEFAULT_TIMEOUT
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_TIMEOUT


def find_binary() -> str | None:
    forced = os.environ.get("PFY_CBM_SHADOW_BIN", "").strip()
    if forced:
        path = Path(forced)
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
        return None
    # scripts/tool_cache.sh: ${PFY_TOOL_CACHE:-$HOME/.cache/pfy}/bin
    tool_cache = os.environ.get("PFY_TOOL_CACHE", "").strip()
    if tool_cache:
        cache_bin = Path(tool_cache).expanduser() / "bin" / "codebase-memory-mcp"
    else:
        cache_bin = Path.home() / ".cache" / "pfy" / "bin" / "codebase-memory-mcp"
    candidates = [
        Path.home() / ".local" / "bin" / "codebase-memory-mcp",
        cache_bin,
    ]
    for cand in candidates:
        if cand.is_file() and os.access(cand, os.X_OK):
            return str(cand)
    return None


def is_test_path(rel: str) -> bool:
    # Same rule as scripts/test_select.py is_test_path.
    name = rel.replace("\\", "/").rsplit("/", 1)[-1]
    rel = rel.replace("\\", "/")
    return (
        rel.startswith("tests/")
        and name.startswith("test_")
        and rel.endswith(".py")
        and "/fixtures/" not in rel
    )


def module_to_rel(module: str) -> str:
    return module.replace(".", "/") + ".py"


def cbm_env(cache: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["CBM_CACHE_DIR"] = str(cache / "db")
    env.setdefault("CBM_MEM_BUDGET_MB", os.environ.get("PFY_CBM_MEM_BUDGET_MB", "8192"))
    env.setdefault("CBM_WORKERS", os.environ.get("PFY_CBM_WORKERS", "2"))
    env.setdefault("CBM_LOG_LEVEL", "error")
    return env


def run_cmd(cmd: list[str], timeout: float, env: dict[str, str] | None, cwd: Path | None) -> tuple[int, str, str, bool]:
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(timeout=max(0.05, timeout))
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, err = proc.communicate()
        return proc.returncode or -9, out or "", err or "", True
    return proc.returncode, out or "", err or "", False


def git_ok(source: Path, *args: str, timeout: float = 30.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(source), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def rev(source: Path, ref: str) -> str:
    proc = git_ok(source, "rev-parse", "--verify", f"{ref}^{{commit}}")
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or f"unknown ref {ref}").strip())
    return proc.stdout.strip()


def ensure_checkout(source: Path, head: str, cache: Path) -> Path:
    """Detach cache/wt at head. Never cleans or checks out source."""
    cache.mkdir(parents=True, exist_ok=True)
    wt = (cache / "wt").resolve()
    cache_r = cache.resolve()
    if wt != cache_r and cache_r not in wt.parents:
        raise RuntimeError("refusing checkout outside the shadow cache")
    source_r = source.resolve()
    if source_r != wt:
        git_marker = wt / ".git"
        if not git_marker.exists():
            if wt.exists():
                raise RuntimeError(f"{wt} exists and is not a git worktree")
            proc = git_ok(source, "worktree", "add", "--detach", str(wt), head, timeout=120)
            if proc.returncode != 0:
                raise RuntimeError((proc.stderr or proc.stdout or "worktree add failed").strip())
    current = git_ok(wt, "rev-parse", "HEAD")
    dirty = git_ok(wt, "status", "--porcelain")
    if current.stdout.strip() == head and not (dirty.stdout or "").strip():
        return wt
    jumped = git_ok(wt, "checkout", "--detach", "--force", head, timeout=120)
    if jumped.returncode != 0:
        raise RuntimeError((jumped.stderr or jumped.stdout or "checkout failed").strip())
    cleaned = git_ok(wt, "clean", "-ffd", timeout=60)
    if cleaned.returncode != 0:
        raise RuntimeError((cleaned.stderr or "git clean failed").strip())
    return wt


def parse_payload(text: str) -> dict:
    raw = text.strip()
    start = raw.find("{")
    if start < 0:
        raise ValueError("no JSON object in tool output")
    # The CLI may prefix a log line. Take the last object-looking span.
    decoder = json.JSONDecoder()
    obj, _end = decoder.raw_decode(raw[start:])
    if not isinstance(obj, dict):
        raise ValueError("tool JSON is not an object")
    return obj


def short_err(text: str, limit: int = 300) -> str:
    flat = " ".join((text or "").split())
    if len(flat) > limit:
        return flat[:limit]
    return flat


def tests_from_cbm(payload: dict) -> tuple[set[str], bool]:
    found: set[str] = set()
    run_all = False
    if payload.get("run_all") is True:
        run_all = True
    decision = str(payload.get("decision") or payload.get("mode") or "").lower()
    if decision in {"all", "run_all", "full", "run-everything", "run_everything"}:
        run_all = True
    for key in ("tests", "test_files", "selected_tests"):
        value = payload.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and is_test_path(item):
                    found.add(item)
                elif isinstance(item, dict):
                    rel = str(item.get("file") or item.get("path") or item.get("file_path") or "")
                    if is_test_path(rel):
                        found.add(rel)
    for item in payload.get("impacted_symbols") or []:
        if not isinstance(item, dict):
            continue
        rel = str(item.get("file") or item.get("file_path") or "")
        if item.get("is_test") is True or is_test_path(rel):
            if is_test_path(rel):
                found.add(rel)
    for rel in payload.get("changed_files") or []:
        if isinstance(rel, str) and is_test_path(rel):
            found.add(rel)
    return found, run_all


def selector_tests(root: Path, base: str, head: str, budget: float) -> tuple[dict, float, str]:
    select = script_repo() / "scripts" / "test_select.py"
    started = time.monotonic()
    rc, out, err, timed = run_cmd(
        [sys.executable, str(select), "--base", base, "--head", head, "--root", str(root)],
        budget,
        None,
        root,
    )
    elapsed = time.monotonic() - started
    if timed:
        return {}, elapsed, "test_select timeout"
    if rc != 0:
        return {}, elapsed, short_err(err or out) or f"test_select exit {rc}"
    try:
        data = json.loads(out)
    except json.JSONDecodeError as exc:
        return {}, elapsed, f"test_select JSON: {exc}"
    if not isinstance(data, dict):
        return {}, elapsed, "test_select JSON is not an object"
    return data, elapsed, ""


def project_indexed(binary: str, env: dict[str, str], budget: float) -> tuple[bool, bool]:
    rc, out, err, timed = run_cmd([binary, "cli", "list_projects"], budget, env, None)
    if timed:
        return False, True
    if rc != 0:
        return False, False
    return PROJECT in out, False


def call_detect(binary: str, env: dict[str, str], base: str, budget: float) -> tuple[dict, str, bool]:
    rc, out, err, timed = run_cmd(
        [
            binary,
            "cli",
            "detect_changes",
            "--project",
            PROJECT,
            "--scope",
            "tests",
            "--since",
            base,
            "--depth",
            DEPTH,
        ],
        budget,
        env,
        None,
    )
    if timed:
        return {}, "timeout", True
    if rc != 0:
        return {}, short_err(err or out) or f"detect_changes exit {rc}", False
    try:
        payload = parse_payload(out)
    except ValueError as exc:
        return {}, short_err(f"{exc}: {err or out}"), False
    if payload.get("error"):
        return payload, short_err(str(payload.get("error"))), False
    return payload, "", False


def run_cbm(binary: str, env: dict[str, str], wt: Path, base: str, deadline: float) -> tuple[set[str], bool, str, bool, float, float]:
    """Returns tests, cbm_run_all, error, timed_out, detect_s, index_s."""
    started = time.monotonic()
    index_s = 0.0

    def left() -> float:
        return deadline - time.monotonic()

    ready, listed_timeout = project_indexed(binary, env, left())
    if listed_timeout:
        return set(), False, "timeout", True, time.monotonic() - started, index_s
    if not ready:
        if left() <= 0.05:
            return set(), False, "timeout", True, time.monotonic() - started, index_s
        index_started = time.monotonic()
        rc, out, err, timed = run_cmd(
            [
                binary,
                "cli",
                "index_repository",
                "--repo-path",
                str(wt),
                "--name",
                PROJECT,
                "--mode",
                "fast",
            ],
            left(),
            env,
            wt,
        )
        index_s = time.monotonic() - index_started
        if timed:
            return set(), False, "timeout", True, time.monotonic() - started, index_s
        if rc != 0 or '"status":"indexed"' not in out and "indexed" not in out.lower():
            return set(), False, short_err(err or out) or f"index exit {rc}", False, time.monotonic() - started, index_s
    if left() <= 0.05:
        return set(), False, "timeout", True, time.monotonic() - started, index_s
    payload, error, timed = call_detect(binary, env, base, left())
    elapsed = time.monotonic() - started
    if timed or error == "timeout":
        return set(), False, "timeout", True, elapsed, index_s
    if error and "not indexed" in error:
        # The list lied or the db was wiped. One index retry inside the budget.
        if left() <= 0.05:
            return set(), False, "timeout", True, elapsed, index_s
        index_started = time.monotonic()
        rc, out, err, timed = run_cmd(
            [binary, "cli", "index_repository", "--repo-path", str(wt), "--name", PROJECT, "--mode", "fast"],
            left(),
            env,
            wt,
        )
        index_s += time.monotonic() - index_started
        if timed:
            return set(), False, "timeout", True, time.monotonic() - started, index_s
        if rc != 0:
            return set(), False, short_err(err or out) or error, False, time.monotonic() - started, index_s
        payload, error, timed = call_detect(binary, env, base, left())
        elapsed = time.monotonic() - started
        if timed:
            return set(), False, "timeout", True, elapsed, index_s
    if error:
        return set(), False, error, False, elapsed, index_s
    tests, run_all = tests_from_cbm(payload)
    return tests, run_all, "", False, elapsed, index_s


def append_record(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.write(line)
        handle.flush()
        fcntl.flock(handle, fcntl.LOCK_UN)


def with_lock(cache: Path):
    cache.mkdir(parents=True, exist_ok=True)
    handle = (cache / "lock").open("a+")
    fcntl.flock(handle, fcntl.LOCK_EX)
    return handle


def shadow(base_ref: str, head_ref: str, source: Path, cache: Path, dest: Path, budget: float) -> dict:
    record: dict = {
        "sha": head_ref,
        "base": base_ref,
        "changed": [],
        "test_select": [],
        "cbm": [],
        "run_all": False,
        "run_all_reason": "",
        "cbm_error": "",
        "cbm_timeout": False,
        "only_in_test_select": [],
        "only_in_cbm": [],
        "test_select_s": 0.0,
        "cbm_s": 0.0,
        "index_s": 0.0,
        "invocation": INVOCATION,
    }
    binary = find_binary()
    if not binary:
        record["cbm_error"] = "binary missing"
        append_record(dest, record)
        return record
    env = cbm_env(cache)
    ver_rc, ver_out, _ver_err, ver_timed = run_cmd([binary, "--version"], min(5.0, budget), env, None)
    if not ver_timed and ver_rc == 0:
        record["binary_version"] = ver_out.strip().splitlines()[-1] if ver_out.strip() else ""
    deadline = time.monotonic() + budget
    lock = with_lock(cache)
    try:
        try:
            head = rev(source, head_ref)
            base = rev(source, base_ref)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            record["cbm_error"] = short_err(str(exc))
            append_record(dest, record)
            return record
        record["sha"] = head
        record["base"] = base
        record["invocation"] = (
            "codebase-memory-mcp cli detect_changes "
            f"--project {PROJECT} --scope tests --since {base} --depth {DEPTH}"
        )
        try:
            wt = ensure_checkout(source, head, cache)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            record["cbm_error"] = short_err(str(exc))
            append_record(dest, record)
            return record
        data, select_s, select_err = selector_tests(wt, base, head, max(0.05, deadline - time.monotonic()))
        record["test_select_s"] = round(select_s, 3)
        if select_err:
            record["test_select_error"] = select_err
        else:
            changed = [str(item) for item in (data.get("changed") or [])]
            record["changed"] = changed
            modules = [str(item) for item in (data.get("modules") or [])]
            selected = sorted({module_to_rel(item) for item in modules})
            record["test_select"] = selected
            record["mode"] = data.get("mode") or ""
            reason = str(data.get("reason") or "")
            record["run_all"] = data.get("mode") == "full"
            record["run_all_reason"] = reason if record["run_all"] else ""
        cbm_tests, cbm_run_all, cbm_error, cbm_timeout, cbm_s, index_s = run_cbm(
            binary, env, wt, base, deadline
        )
        record["cbm_s"] = round(cbm_s, 3)
        record["index_s"] = round(index_s, 3)
        record["cbm_timeout"] = cbm_timeout
        record["cbm_run_all"] = cbm_run_all
        if cbm_error and cbm_error != "timeout":
            record["cbm_error"] = cbm_error
        elif cbm_timeout:
            record["cbm_error"] = "timeout"
        record["cbm"] = sorted(cbm_tests)
        selected_set = set(record["test_select"])
        record["only_in_test_select"] = sorted(selected_set - cbm_tests)
        record["only_in_cbm"] = sorted(cbm_tests - selected_set)
        if cbm_run_all and not record["run_all"]:
            record["only_in_cbm"] = ["*"]
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
    append_record(dest, record)
    return record


def load_records(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_SH)
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
        fcntl.flock(handle, fcntl.LOCK_UN)
    return rows


def report(path: Path) -> str:
    rows = load_records(path)
    lines = [
        f"log: {path}",
        f"invocation: {INVOCATION}",
        f"records: {len(rows)}",
    ]
    if not rows:
        lines.append("no shadow records")
        lines.append("later full-run failures: no data in the log")
        return "\n".join(lines)
    clean = [
        row for row in rows
        if not row.get("cbm_error") and not row.get("cbm_timeout")
    ]
    agreed = [
        row for row in clean
        if not row.get("only_in_test_select") and not row.get("only_in_cbm")
    ]
    run_all = [row for row in rows if row.get("run_all")]
    lines.append(
        f"agreement: {len(agreed)}/{len(rows)} records"
        f" ({len(agreed)}/{len(clean)} with a cbm answer)"
    )
    lines.append(f"run_all: {len(run_all)}/{len(rows)}")
    errors = [row for row in rows if row.get("cbm_error") or row.get("cbm_timeout")]
    lines.append(f"cbm errors or timeouts: {len(errors)}/{len(rows)}")
    only_cbm: Counter[str] = Counter()
    only_sel: Counter[str] = Counter()
    for row in rows:
        for rel in row.get("only_in_cbm") or []:
            only_cbm[str(rel)] += 1
        for rel in row.get("only_in_test_select") or []:
            only_sel[str(rel)] += 1
    lines.append("top only-in-cbm:")
    if not only_cbm:
        lines.append("  (none)")
    for rel, count in only_cbm.most_common(10):
        lines.append(f"  {count} {rel}")
    lines.append("top only-in-test_select:")
    if not only_sel:
        lines.append("  (none)")
    for rel, count in only_sel.most_common(10):
        lines.append(f"  {count} {rel}")
    missed = []
    for row in rows:
        later = {str(item) for item in (row.get("later_failed") or [])}
        picked = {str(item) for item in (row.get("only_in_cbm") or [])}
        hit = sorted(later & picked)
        if hit:
            missed.append(f"  {row.get('sha', '')[:12]} {', '.join(hit)}")
    lines.append("cbm-only tests that later failed a full run:")
    if missed:
        lines.extend(missed)
    else:
        lines.append("  no data in the log")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default=None)
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--root", type=Path, default=None)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--log", default=None)
    ap.add_argument("--timeout", type=float, default=None)
    args = ap.parse_args(argv)
    dest = log_path(args.log)
    if args.report:
        print(report(dest))
        return 0
    if os.environ.get("PFY_CBM_SHADOW", "1") == "0":
        return 0
    if not args.base:
        # A gate calls this best-effort. Missing args are a log line, not an exit 2.
        append_record(
            dest,
            {
                "sha": "",
                "base": "",
                "changed": [],
                "test_select": [],
                "cbm": [],
                "run_all": False,
                "run_all_reason": "",
                "cbm_error": "missing --base",
                "cbm_timeout": False,
                "only_in_test_select": [],
                "only_in_cbm": [],
                "test_select_s": 0.0,
                "cbm_s": 0.0,
            },
        )
        return 0
    root_env = os.environ.get("PFY_CBM_SHADOW_ROOT", "").strip()
    source = (args.root or (Path(root_env) if root_env else script_repo())).resolve()
    try:
        shadow(args.base, args.head, source, cache_dir(), dest, timeout_s(args.timeout))
    except Exception as exc:  # noqa: BLE001 - shadow must not escape into the gate
        try:
            append_record(
                dest,
                {
                    "sha": args.head,
                    "base": args.base,
                    "changed": [],
                    "test_select": [],
                    "cbm": [],
                    "run_all": False,
                    "run_all_reason": "",
                    "cbm_error": short_err(f"shadow failed: {exc}"),
                    "cbm_timeout": False,
                    "only_in_test_select": [],
                    "only_in_cbm": [],
                    "test_select_s": 0.0,
                    "cbm_s": 0.0,
                },
            )
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
