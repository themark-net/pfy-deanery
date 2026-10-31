#!/usr/bin/env python3
"""Operate-or-FAIL smoke for X intake Entry 149 (MemPalace, local-first agent memory). Stdlib only, self-contained.

Usage: python3 examples/x-intake-local/smoke_149.py

Exit 0 = PASS, 1 = the tool ran but a check failed, 2 = can't run here (prereq missing; reason recorded).
Receipt: $PFY_SMOKE_RECEIPT_DIR/latest.json, else pipelines/smoke/mempalace/latest.json. Never installs anything,
never downloads a model, never calls an LLM.

Binary: $MEMPALACE_BIN, else ~/DEVELOP/pfy-mentat/tmp/mempalace/.venv/bin/mempalace, else `mempalace` on PATH.
`--version` must report exactly MEMPALACE_VERSION (default 3.12.0) or the smoke exits 2.
Model cache: the default embedder (ChromaDB's all-MiniLM-L6-v2 ONNX) must already sit in
$MEMPALACE_HOME/.cache/chroma/onnx_models/all-MiniLM-L6-v2 (MEMPALACE_HOME default
~/DEVELOP/pfy-mentat/tmp/mempalace/home); without it the smoke exits 2 rather than fetch ~80 MB.
The smoke copies that HOME into a temp dir, writes a two-note fixture project, then runs `init --yes`, `mine` and two
`search` queries against a temp palace with a clean env and a timeout ($PFY_XINTAKE_TIMEOUT, default 180 s). Every
step runs under bwrap with no network and a read-only root. If bwrap is missing or unusable, or a required
`/proc` or `/dev/shm` mount cannot be made, the smoke exits 2 and never runs MemPalace unsandboxed (same rule as
Entry 148). Checks: each step exits 0, mine files 2 drawers, each query ranks
the right note first, and real-HOME paths ~/.mempalace, ~/.config/mempalace and ~/.cache/chroma are unchanged.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIN = os.environ.get("MEMPALACE_VERSION", "3.12.0")
SYS_PATH = "/usr/local/bin:/usr/bin:/bin"
PROC_PATH = "/proc"
SHM_PATH = "/dev/shm"
WATCHED = [".mempalace", ".config/mempalace", ".cache/chroma"]
MODEL_REL = ".cache/chroma/onnx_models/all-MiniLM-L6-v2"
NOTES = {
    "auth.md": "# Auth decision\nWe switched auth to Clerk because Auth0 pricing jumped and token refresh kept failing.\n",
    "ci.md": "# CI\nThe CI pipeline runs ruff then pytest on ubuntu-24.04.\n",
}
QUERIES = {"why did we switch auth provider": "auth.md", "which test runner does CI use": "ci.md"}


def receipt_dir() -> Path:
    env = os.environ.get("PFY_SMOKE_RECEIPT_DIR")
    return Path(env) if env else ROOT / "pipelines/smoke/mempalace"


def finish(code: int, rec: dict) -> int:
    rec["status"] = {0: "PASS", 1: "FAIL", 2: "SKIP"}[code]
    rec["exit"] = code
    rec["at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    d = receipt_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "latest.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": rec["status"], "reason": rec.get("reason"), "failed": rec.get("failed", [])}))
    return code


def find_bin() -> str | None:
    env = os.environ.get("MEMPALACE_BIN")
    if env:
        return env if os.access(env, os.X_OK) else None
    local = Path.home() / "DEVELOP/pfy-mentat/tmp/mempalace/.venv/bin/mempalace"
    if os.access(local, os.X_OK):
        return str(local)
    return shutil.which("mempalace")


def bwrap_ok() -> bool:
    if not shutil.which("bwrap"):
        return False
    p = subprocess.run(["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--unshare-net", "true"],
                       capture_output=True)
    return p.returncode == 0


def dir_usable(path: str, *, writable: bool) -> bool:
    try:
        if not os.path.isdir(path):
            return False
        need = os.X_OK | (os.W_OK if writable else os.R_OK)
        return os.access(path, need)
    except OSError:
        return False


def sandbox_mount_args() -> tuple[list[str], str | None]:
    """Bind args for the required mounts, or a fail-closed reason. Never a signal to run unsandboxed."""
    if not dir_usable(PROC_PATH, writable=False):
        return [], f"required bind {PROC_PATH} is not usable; refusing to run unsandboxed"
    if not dir_usable(SHM_PATH, writable=True):
        return [], f"required bind {SHM_PATH} is not usable; refusing to run unsandboxed"
    return ["--tmpfs", SHM_PATH, "--proc", PROC_PATH], None


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


def run(binary: str, args: list[str], tmp: Path, timeout: float,
        extra_binds: list[str] | None = None) -> subprocess.CompletedProcess:
    # extra_binds is a test seam. main() never passes it. No env var opens a writable real HOME.
    env = {"PATH": SYS_PATH, "HOME": str(tmp / "home"), "TMPDIR": str(tmp / "t"), "LANG": "C.UTF-8",
           "NO_COLOR": "1", "TERM": "dumb", "HF_HUB_OFFLINE": "1", "ANONYMIZED_TELEMETRY": "False"}
    mounts, why = sandbox_mount_args()
    if why:
        raise OSError(why)
    # Same PATH lookup as bwrap_ok. The child env's PATH is the stripped one and must not pick a different bwrap.
    bwrap = shutil.which("bwrap")
    if not bwrap:
        raise OSError("bwrap is not usable here; MemPalace must run with no network")
    cmd = [bwrap, "--ro-bind", "/", "/", "--dev", "/dev", *mounts,
           "--bind", str(tmp), str(tmp), *(extra_binds or []), "--unshare-net", "--die-with-parent",
           binary, *args]
    return subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout, start_new_session=True,
                          stdin=subprocess.DEVNULL)


def version_of(out: str) -> str | None:
    m = re.search(r"\b(\d+\.\d+\.\d+[0-9A-Za-z.+-]*)", out)
    return m.group(1) if m else None


def top_source(out: str) -> str | None:
    m = re.search(r"Source:\s*(\S+)", out)
    return m.group(1) if m else None


def main() -> int:
    rec: dict = {"entry": "149-mempalace", "pin": PIN, "failed": [], "checks": {}}
    try:
        timeout = float(os.environ.get("PFY_XINTAKE_TIMEOUT", "180"))
        if timeout <= 0:
            raise ValueError
    except ValueError:
        rec["reason"] = "bad PFY_XINTAKE_TIMEOUT"
        return finish(2, rec)
    binary = find_bin()
    if not binary:
        rec["reason"] = "mempalace not staged (set MEMPALACE_BIN or stage ~/DEVELOP/pfy-mentat/tmp/mempalace/.venv)"
        return finish(2, rec)
    rec["binary"] = binary
    src_home = Path(os.environ.get("MEMPALACE_HOME") or Path.home() / "DEVELOP/pfy-mentat/tmp/mempalace/home")
    if not (src_home / MODEL_REL).is_dir():
        rec["reason"] = f"embedding model not cached at {src_home / MODEL_REL} (warm it once inside DEVELOP)"
        return finish(2, rec)
    _mounts, mount_reason = sandbox_mount_args()
    if mount_reason:
        rec["reason"] = mount_reason
        return finish(2, rec)
    if not bwrap_ok():
        rec["reason"] = "bwrap is not usable here; MemPalace must run with no network"
        return finish(2, rec)
    rec["sandbox"] = "bwrap --unshare-net"
    real_home = Path.home()
    before = home_sig(real_home)
    with tempfile.TemporaryDirectory(prefix="pfy-smoke-149-") as td:
        tmp = Path(td)
        (tmp / "t").mkdir()
        shutil.copytree(src_home, tmp / "home", symlinks=True)
        proj = tmp / "proj" / "notes"
        proj.mkdir(parents=True)
        for name, text in NOTES.items():
            (proj / name).write_text(text, encoding="utf-8")
        palace = str(tmp / "palace")
        try:
            v = run(binary, ["--version"], tmp, timeout)
        except (OSError, subprocess.TimeoutExpired) as e:
            rec["reason"] = f"--version failed: {e}"
            return finish(2, rec)
        rec["version_output"] = (v.stdout + v.stderr).strip()[:200]
        rec["version"] = version_of(rec["version_output"])
        if rec["version"] != PIN:
            rec["reason"] = f"version pin {PIN} != --version {rec['version']}"
            return finish(2, rec)
        outs = {}
        try:
            for step, args in (("init", ["--palace", palace, "init", str(tmp / "proj"), "--yes"]),
                               ("mine", ["--palace", palace, "mine", str(tmp / "proj")])):
                p = run(binary, args, tmp, timeout)
                rec["checks"][f"{step}_exit"] = p.returncode
                outs[step] = p.stdout + p.stderr
            for i, q in enumerate(QUERIES):
                p = run(binary, ["--palace", palace, "search", q, "--results", "2"], tmp, timeout)
                rec["checks"][f"q{i}_exit"] = p.returncode
                outs[f"q{i}"] = p.stdout + p.stderr
        except subprocess.TimeoutExpired as e:
            rec["failed"].append(f"timed out: {e.cmd[-3:] if e.cmd else ''}")
            return finish(1, rec)
        finally:
            after = home_sig(real_home)
            rec["real_home_changed"] = [k for k in WATCHED if before[k] != after[k]]

    def check(name: str, ok: bool) -> None:
        rec["checks"][name] = bool(ok)
        if not ok:
            rec["failed"].append(name)

    check("init_ok", rec["checks"].get("init_exit") == 0)
    check("mine_ok", rec["checks"].get("mine_exit") == 0)
    m = re.search(r"Drawers filed:\s*(\d+)", outs.get("mine", ""))
    rec["drawers_filed"] = int(m.group(1)) if m else None
    check("mine_filed_2", rec["drawers_filed"] == 2)
    for i, (q, want) in enumerate(QUERIES.items()):
        got = top_source(outs.get(f"q{i}", ""))
        rec[f"q{i}_top"] = got
        check(f"q{i}_ok", rec["checks"].get(f"q{i}_exit") == 0)
        check(f"q{i}_ranks_{want}", got == want)
    check("real_home_unchanged", not rec["real_home_changed"])
    if rec["failed"]:
        rec["tail"] = {k: v[-400:] for k, v in outs.items()}
    return finish(1 if rec["failed"] else 0, rec)


if __name__ == "__main__":
    sys.exit(main())
