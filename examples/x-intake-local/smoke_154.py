#!/usr/bin/env python3
"""Operate-or-FAIL smoke for X intake Entry 154 (RoBrain, shared decision memory with veto warnings).
Stdlib only, self-contained.

Usage: python3 examples/x-intake-local/smoke_154.py

Exit 0 = PASS, 1 = the bench ran but a check failed, 2 = can't run here (prereq missing; reason recorded).
Receipt: $PFY_SMOKE_RECEIPT_DIR/latest.json, else pipelines/smoke/robrain/latest.json. Never installs or downloads
anything, never starts Docker/Postgres/Perception, never calls an LLM (no --live, no keys in the child env).

Runs VetoBench's offline retrieval layer (packages/vetobench, deterministic hash embedder, no API key) from a
pre-built clone: $ROBRAIN_DIR, else ~/DEVELOP/pfy-mentat/tmp/robrain, checked out at ROBRAIN_COMMIT (default the
pinned commit below) with `pnpm install --filter "@robrain/vetobench..."` and the shared + vetobench builds done
(packages/vetobench/dist/run.js and packages/shared/dist present); otherwise exit 2.
Node: $NODE_BIN, else `node` on PATH, major >= 20, else exit 2.
Steps (temp HOME/TMPDIR, clean env, timeout $PFY_XINTAKE_TIMEOUT default 120 s, bwrap --unshare-net when it works):
`node dist/run.js` (default suite), `node dist/run.js --suite lifecycle`, and the package's node:test files.
Checks: each exits 0 with "PASS", veto recall@5 with files known meets the upstream gate (>= 0.80) and both recall
numbers match the values pinned for this commit (deterministic, so drift means the bench changed), every scenario
row is present, the run says it is offline, node:test reports 0 failures, packages/vetobench/results is unchanged
(no archive written), and the real-HOME paths ~/.robrain and ~/.mem0 are unchanged.
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
PIN = os.environ.get("ROBRAIN_COMMIT", "ac53011016e5f7dd42bae9c00c1a9b7d207a68b8")
SYS_PATH = "/usr/local/bin:/usr/bin:/bin"
WATCHED = [".robrain", ".mem0"]
GATE = 0.80
# suite -> (scenario count, recall@5 files known, recall@5 without files) at the pinned commit
EXPECT = {"default": (10, 1.00, 0.70), "lifecycle": (4, 1.00, 1.00)}
TEST_FILES = ["dist/score.test.js", "dist/adapters.test.js", "dist/mem0-adapter.test.js"]
MIN_NODE_TESTS = 20  # 22 at the pinned commit
RECALL_RE = re.compile(r"veto recall@5:\s*([0-9.]+)\s+with files known.*?([0-9.]+)\s+without")
ROW_RE = re.compile(r"^(s\w+)\s+\S+\s+\d+\s+[✓✗]\s+\d+\s+[✓✗]\s*$", re.M)


def receipt_dir() -> Path:
    env = os.environ.get("PFY_SMOKE_RECEIPT_DIR")
    return Path(env) if env else ROOT / "pipelines/smoke/robrain"


def finish(code: int, rec: dict) -> int:
    rec["status"] = {0: "PASS", 1: "FAIL", 2: "SKIP"}[code]
    rec["exit"] = code
    rec["at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    d = receipt_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "latest.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": rec["status"], "reason": rec.get("reason"), "failed": rec.get("failed", [])}))
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


def bwrap_ok() -> bool:
    if not shutil.which("bwrap"):
        return False
    p = subprocess.run(["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--unshare-net", "true"],
                       capture_output=True)
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


def dir_hash(p: Path) -> str:
    h = hashlib.sha256()
    if p.is_dir():
        for f in sorted(q for q in p.rglob("*") if q.is_file()):
            h.update(str(f.relative_to(p)).encode() + b"\0" + f.read_bytes() + b"\0")
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


def run(node: str, args: list[str], cwd: Path, tmp: Path, sandbox: bool, timeout: float):
    env = {"PATH": f"{Path(node).resolve().parent}:{SYS_PATH}", "HOME": str(tmp / "home"), "TMPDIR": str(tmp / "t"),
           "LANG": "C.UTF-8", "NO_COLOR": "1", "TERM": "dumb"}
    cmd = [node, *args]
    if sandbox:
        cmd = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--bind", str(tmp), str(tmp),
               "--unshare-net", "--die-with-parent", *cmd]
    return run_group(cmd, env, str(cwd), timeout)


def body(rec: dict, repo: Path, node: str, tmp: Path, timeout: float) -> int:
    def check(name: str, ok: bool) -> None:
        rec["checks"][name] = bool(ok)
        if not ok:
            rec["failed"].append(name)

    (tmp / "t").mkdir()
    (tmp / "home").mkdir()
    sandbox = bwrap_ok()
    rec["sandbox"] = "bwrap --unshare-net" if sandbox else "none (network reachable)"
    vb = repo / "packages/vetobench"
    results_before = dir_hash(vb / "results")
    outs = {}
    try:
        for suite, (rows, want_files, want_nofiles) in EXPECT.items():
            args = ["dist/run.js"] + ([] if suite == "default" else ["--suite", suite])
            p = run(node, args, vb, tmp, sandbox, timeout)
            out = p.stdout + p.stderr
            outs[suite] = out
            check(f"{suite}_exit_0", p.returncode == 0)
            check(f"{suite}_says_pass", "✓ PASS" in out and "✗ FAIL" not in out)
            check(f"{suite}_offline", "offline run" in out)
            m = RECALL_RE.search(out)
            got = (float(m.group(1)), float(m.group(2))) if m else None
            rec[f"{suite}_recall_files_known_nofiles"] = got
            check(f"{suite}_recall_meets_gate", got is not None and got[0] >= GATE)
            check(f"{suite}_recall_matches_pin", got is not None and abs(got[0] - want_files) < 1e-9
                  and abs(got[1] - want_nofiles) < 1e-9)
            n_rows = len(ROW_RE.findall(out))
            rec[f"{suite}_rows"] = n_rows
            check(f"{suite}_rows_{rows}", n_rows == rows)
        p = run(node, ["--test", *TEST_FILES], vb, tmp, sandbox, timeout)
        out = p.stdout + p.stderr
        outs["node_test"] = out
        passed = re.search(r"^\D*pass (\d+)\s*$", out, re.M)
        failed = re.search(r"^\D*fail (\d+)\s*$", out, re.M)
        rec["node_test_pass"] = int(passed.group(1)) if passed else None
        rec["node_test_fail"] = int(failed.group(1)) if failed else None
        check("node_test_exit_0", p.returncode == 0)
        check("node_test_no_failures", rec["node_test_fail"] == 0)
        check(f"node_test_at_least_{MIN_NODE_TESTS}", (rec["node_test_pass"] or 0) >= MIN_NODE_TESTS)
    except subprocess.TimeoutExpired as e:
        rec["failed"].append(f"timed out: {e.cmd[-2:] if e.cmd else ''}")
        return 1
    check("results_dir_unchanged", dir_hash(vb / "results") == results_before)
    if rec["failed"]:
        rec["tail"] = {k: v[-400:] for k, v in outs.items()}
    return 1 if rec["failed"] else 0


def main() -> int:
    rec: dict = {"entry": "154-robrain", "pin": PIN, "failed": [], "checks": {}}
    try:
        timeout = float(os.environ.get("PFY_XINTAKE_TIMEOUT", "120"))
        if timeout <= 0:
            raise ValueError
    except ValueError:
        rec["reason"] = "bad PFY_XINTAKE_TIMEOUT"
        return finish(2, rec)
    repo = Path(os.environ.get("ROBRAIN_DIR") or Path.home() / "DEVELOP/pfy-mentat/tmp/robrain")
    rec["clone"] = str(repo)
    if not (repo / "packages/vetobench/package.json").is_file():
        rec["reason"] = f"robrain clone not staged at {repo}"
        return finish(2, rec)
    head = read_head(repo)
    rec["head"] = head
    if head != PIN:
        rec["reason"] = f"clone HEAD {head} is not the pinned commit {PIN}"
        return finish(2, rec)
    vb = repo / "packages/vetobench"
    need = [vb / "dist/run.js", *(vb / t for t in TEST_FILES), repo / "packages/shared/dist",
            vb / "node_modules/@robrain/shared"]
    missing = [str(p.relative_to(repo)) for p in need if not p.exists()]
    if missing:
        rec["reason"] = f"clone not built (missing {', '.join(missing)})"
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
    m = re.match(r"v?(\d+)\.", v)
    if not m or int(m.group(1)) < 20:
        rec["reason"] = f"node {v!r} is older than 20"
        return finish(2, rec)
    real_home = Path.home()
    before = home_sig(real_home)
    code = 1
    try:
        with tempfile.TemporaryDirectory(prefix="pfy-smoke-154-") as td:
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
