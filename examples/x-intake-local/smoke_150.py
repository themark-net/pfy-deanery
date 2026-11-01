#!/usr/bin/env python3
"""Static operate-or-FAIL smoke for X intake Entry 150 (dsh-superagent, DeepSeek's proactive repo agent prototype).
Stdlib only, self-contained.

Usage: python3 examples/x-intake-local/smoke_150.py

Exit 0 = PASS, 1 = the checks ran and one failed, 2 = can't run here (prereq missing; reason recorded).
Receipt: $PFY_SMOKE_RECEIPT_DIR/latest.json, else pipelines/smoke/dsh-superagent/latest.json. Never installs or
downloads anything, never starts DeepSeek Harness, never talks to GitHub or Feishu, needs no model key.

This is the upstream `pnpm check` (typecheck, vitest, tsdown build) run straight from the clone's node_modules/.bin,
so neither pnpm nor corepack (which would fetch pnpm 11.7.0) is needed at smoke time.
Clone: $DSH_SUPERAGENT_DIR, else ~/DEVELOP/pfy-mentat/tmp/dsh-superagent, checked out at DSH_SUPERAGENT_COMMIT
(default the pinned commit below) with `pnpm install --frozen-lockfile` already done; otherwise exit 2.
Node: $NODE_BIN, else `node` on PATH; must be ^22.19 or >=24 (upstream engines), else exit 2.
Steps run with a temp HOME/TMPDIR, a clean env and a timeout ($PFY_XINTAKE_TIMEOUT, default 600 s per step), under
bwrap --unshare-net when it works. Checks: typecheck and build exit 0, the build writes lib/index.js, the vitest JSON
report has at least MIN_TESTS passing and no failures other than the known timing-dependent upstream test below
(recorded as a warning), tracked sources (src/, tests/, package.json, pnpm-lock.yaml) are byte-identical afterwards,
and the real-HOME paths ~/.dsh, ~/.config/gh-agent, ~/.lark-cli-dsh-superagent are unchanged.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIN = os.environ.get("DSH_SUPERAGENT_COMMIT", "6337fc823ce20251c8de8085948165c81aaa701e")
SYS_PATH = "/usr/local/bin:/usr/bin:/bin"
WATCHED = [".dsh", ".config/gh-agent", ".lark-cli-dsh-superagent"]
SOURCES = ["src", "tests", "package.json", "pnpm-lock.yaml"]
MIN_TESTS = 1100  # 1197 tests at the pinned commit
# Fails on the Grok Bot box in most runs (health flips back to "ready" before the assertion reads "error").
KNOWN_FLAKY = {"feishu event consumer takes in the event lines it reads, records each chat as direct or not, "
               "and reports a malformed line without stopping"}


def receipt_dir() -> Path:
    env = os.environ.get("PFY_SMOKE_RECEIPT_DIR")
    return Path(env) if env else ROOT / "pipelines/smoke/dsh-superagent"


def finish(code: int, rec: dict) -> int:
    rec["status"] = {0: "PASS", 1: "FAIL", 2: "SKIP"}[code]
    rec["exit"] = code
    rec["at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    d = receipt_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "latest.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": rec["status"], "reason": rec.get("reason"), "failed": rec.get("failed", []),
                      "warnings": rec.get("warnings", [])}))
    return code


def read_head(repo: Path) -> str | None:
    """Commit at HEAD from .git without running git (handles detached HEAD, loose and packed refs)."""
    git = repo / ".git"
    try:
        head = (git / "HEAD").read_text().strip()
    except OSError:
        return None
    if not head.startswith("ref: "):
        return head or None
    ref = head[5:]
    try:
        return (git / ref).read_text().strip()
    except OSError:
        pass
    try:
        for line in (git / "packed-refs").read_text().splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1] == ref:
                return parts[0]
    except OSError:
        pass
    return None


def node_ok(version: str) -> bool:
    m = re.match(r"v?(\d+)\.(\d+)", version.strip())
    if not m:
        return False
    major, minor = int(m.group(1)), int(m.group(2))
    return major >= 24 or (major == 22 and minor >= 19)


def bwrap_ok() -> bool:
    if not shutil.which("bwrap"):
        return False
    # Probe with the same mounts the run uses (/dev/shm tmpfs, /proc), so a host that can't make them falls back.
    p = subprocess.run(["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--tmpfs", "/dev/shm", "--proc", "/proc",
                        "--unshare-net", "true"], capture_output=True)
    return p.returncode == 0


def home_sig(home: Path) -> dict:
    sig = {}
    for rel in WATCHED:
        p = home / rel
        if p.is_dir():
            sig[rel] = sorted((str(q.relative_to(p)), q.stat().st_size, q.stat().st_mtime_ns) for q in p.rglob("*"))
        elif p.exists():
            sig[rel] = [p.stat().st_size, p.stat().st_mtime_ns]
        else:
            sig[rel] = None
    return sig


def tree_hash(repo: Path) -> str:
    h = hashlib.sha256()
    for rel in SOURCES:
        p = repo / rel
        files = sorted(q for q in p.rglob("*") if q.is_file()) if p.is_dir() else ([p] if p.is_file() else [])
        for f in files:
            h.update(str(f.relative_to(repo)).encode() + b"\0" + f.read_bytes() + b"\0")
    return h.hexdigest()


def kill_group(p: subprocess.Popen) -> None:
    """SIGKILL the child's whole process group (start_new_session=True), so a sandboxed grandchild can't outlive us."""
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def run_group(cmd: list[str], env: dict, cwd: str, timeout: float) -> subprocess.CompletedProcess:
    """subprocess.run, but the process group is killed on timeout and after exit (no orphans under bwrap)."""
    p = subprocess.Popen(cmd, env=env, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_group(p)
        p.communicate()
        raise
    finally:
        kill_group(p)
    return subprocess.CompletedProcess(cmd, p.returncode, out, err)


def run(cmd: list[str], repo: Path, tmp: Path, node_dir: str, sandbox: bool, timeout: float):
    env = {"PATH": f"{node_dir}:{SYS_PATH}", "HOME": str(tmp / "home"), "TMPDIR": str(tmp / "t"), "LANG": "C.UTF-8",
           "NO_COLOR": "1", "TERM": "dumb", "CI": "1"}
    if sandbox:
        cmd = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--tmpfs", "/dev/shm", "--proc", "/proc",
               "--bind", str(tmp), str(tmp), "--bind", str(repo), str(repo), "--unshare-net", "--die-with-parent", *cmd]
    return run_group(cmd, env, str(repo), timeout)


def body(rec: dict, repo: Path, node: str, tmp: Path, timeout: float) -> int:
    def check(name: str, ok: bool) -> None:
        rec["checks"][name] = bool(ok)
        if not ok:
            rec["failed"].append(name)

    (tmp / "t").mkdir()
    (tmp / "home").mkdir()
    sandbox = bwrap_ok()
    rec["sandbox"] = "bwrap --unshare-net" if sandbox else "none (network reachable)"
    node_dir = str(Path(node).resolve().parent)
    bins = repo / "node_modules/.bin"
    src_before = tree_hash(repo)
    lib = repo / "lib/index.js"
    lib_before = lib.stat().st_mtime_ns if lib.exists() else None
    report = tmp / "vitest.json"
    outs = {}
    try:
        p = run([str(bins / "tsc"), "--noEmit"], repo, tmp, node_dir, sandbox, timeout)
        outs["typecheck"] = p.stdout + p.stderr
        check("typecheck_ok", p.returncode == 0)
        p = run([str(bins / "vitest"), "run", "--reporter=json", f"--outputFile={report}"], repo, tmp, node_dir,
                sandbox, timeout)
        outs["test"] = p.stdout + p.stderr
        rec["checks"]["test_exit"] = p.returncode
        p = run([str(bins / "tsdown")], repo, tmp, node_dir, sandbox, timeout)
        outs["build"] = p.stdout + p.stderr
        check("build_ok", p.returncode == 0)
    except subprocess.TimeoutExpired as e:
        rec["failed"].append(f"timed out: {e.cmd[-2:] if e.cmd else ''}")
        return 1
    try:
        rep = json.loads(report.read_text())
        failed = sorted(a.get("fullName", "?") for f in rep.get("testResults", [])
                        for a in f.get("assertionResults", []) if a.get("status") == "failed")
        rec["tests_passed"] = int(rep.get("numPassedTests", 0))
        rec["tests_failed"] = failed[:20]
        suite_errors = [f.get("name") for f in rep.get("testResults", [])
                        if f.get("status") == "failed" and not f.get("assertionResults")]
    except (OSError, ValueError, AttributeError, TypeError):
        rec["tests_passed"], failed, suite_errors = 0, ["no vitest JSON report"], []
    unexpected = [n for n in failed if n not in KNOWN_FLAKY]
    rec["warnings"] = [f"known flaky upstream test failed: {n[:80]}" for n in failed if n in KNOWN_FLAKY]
    check("tests_no_unexpected_failures", not unexpected and not suite_errors)
    check(f"tests_at_least_{MIN_TESTS}_pass", rec["tests_passed"] >= MIN_TESTS)
    check("build_wrote_lib", lib.exists() and lib.stat().st_mtime_ns != lib_before)
    check("sources_unchanged", tree_hash(repo) == src_before)
    if rec["failed"]:
        rec["tail"] = {k: v[-400:] for k, v in outs.items()}
    return 1 if rec["failed"] else 0


def main() -> int:
    rec: dict = {"entry": "150-dsh-superagent", "pin": PIN, "failed": [], "checks": {}, "warnings": []}
    try:
        timeout = float(os.environ.get("PFY_XINTAKE_TIMEOUT", "600"))
        if timeout <= 0:
            raise ValueError
    except ValueError:
        rec["reason"] = "bad PFY_XINTAKE_TIMEOUT"
        return finish(2, rec)
    repo = Path(os.environ.get("DSH_SUPERAGENT_DIR") or Path.home() / "DEVELOP/pfy-mentat/tmp/dsh-superagent")
    rec["clone"] = str(repo)
    if not (repo / "package.json").is_file():
        rec["reason"] = f"dsh-superagent clone not staged at {repo}"
        return finish(2, rec)
    head = read_head(repo)
    rec["head"] = head
    if head != PIN:
        rec["reason"] = f"clone HEAD {head} is not the pinned commit {PIN}"
        return finish(2, rec)
    missing = [b for b in ("tsc", "vitest", "tsdown") if not os.access(repo / "node_modules/.bin" / b, os.X_OK)]
    if missing:
        rec["reason"] = f"dependencies not installed in the clone (missing node_modules/.bin/{', '.join(missing)})"
        return finish(2, rec)
    node = os.environ.get("NODE_BIN") or shutil.which("node")
    if not node or not os.access(node, os.X_OK):
        rec["reason"] = "node not found (set NODE_BIN)"
        return finish(2, rec)
    try:
        v = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=30,
                           stdin=subprocess.DEVNULL).stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        rec["reason"] = f"node --version failed: {e}"
        return finish(2, rec)
    rec["node"] = v
    if not node_ok(v):
        rec["reason"] = f"node {v!r} does not satisfy ^22.19.0 || >=24"
        return finish(2, rec)
    real_home = Path.home()
    before = home_sig(real_home)
    code = 1
    try:
        with tempfile.TemporaryDirectory(prefix="pfy-smoke-150-") as td:
            code = body(rec, repo, node, Path(td), timeout)
    except Exception as e:  # any crash is a FAIL with a receipt
        rec["failed"].append(f"exception: {e!r}")
        code = 1
    finally:
        after = home_sig(real_home)
        rec["real_home_changed"] = [k for k in WATCHED if before[k] != after[k]]
        rec["checks"]["real_home_unchanged"] = not rec["real_home_changed"]
    if rec["real_home_changed"]:
        rec["failed"].append("real_home_unchanged")
        code = 1
    return finish(code, rec)


if __name__ == "__main__":
    sys.exit(main())
