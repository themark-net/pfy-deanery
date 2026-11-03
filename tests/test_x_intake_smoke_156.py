"""Entry 156 smoke (SysKnife): a missing binary exits 2, a hang and a forked grandchild are killed,
a dry-run that cannot plan exits 2, a real-HOME write fails, and a stub plan passes without --yes."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples/x-intake-local/smoke_156.py"

STUB = r'''
import os, sys, time
a = sys.argv[1:]
if K.get("orphan"):
    if os.fork() == 0:
        for fd in (1, 2):
            try:
                os.close(fd)
            except OSError:
                pass
        time.sleep(30)
        os._exit(0)
    os._exit(0)
if K.get("hang"):
    time.sleep(60)
if K.get("touch_real"):
    os.makedirs(os.path.join(K["touch_real"], ".sysknife"), exist_ok=True)
if "--version" in a:
    print(K.get("version", "0.30.0"))
    raise SystemExit(0)
if "--help" in a or "-h" in a:
    print("Usage: sysknife\n--dry-run  print the plan and do not execute")
    raise SystemExit(0)
if "--dry-run" in a:
    if "--yes" in a or "--dangerously-skip-approval" in a:
        print("armed")
        raise SystemExit(1)
    print('{"dry_run":true,"plan":{"steps":[{"action":"GetDiskUsage","risk":"low"}]}}')
    raise SystemExit(K.get("dry_exit", 0))
print("usage")
raise SystemExit(2)
'''

# Enough of bwrap for the probe and for argv stripping. Ubuntu-parity hides the real
# binary; the dry-run checks still need shutil.which("bwrap") to succeed. This shim
# does not isolate. It only lets the stub run.
BWRAP_SHIM = """
import os, sys
args = sys.argv[1:]
two = {"--ro-bind", "--bind"}
one = {"--dev", "--proc", "--chdir", "--uid", "--gid", "--setenv"}
i = 0
while i < len(args):
    flag = args[i]
    if flag in two:
        i += 3
        continue
    if flag in one:
        i += 2
        continue
    if flag.startswith("--"):
        i += 1
        continue
    break
if i >= len(args):
    raise SystemExit(1)
os.execv(args[i], args[i:])
"""


def _path_bwrap(td: Path, path: str) -> str:
    if shutil.which("bwrap", path=path):
        return path
    bindir = td / "bin"
    bindir.mkdir()
    shim = bindir / "bwrap"
    shim.write_text("#!" + sys.executable + "\n" + BWRAP_SHIM, encoding="utf-8")
    shim.chmod(0o755)
    return str(bindir) + os.pathsep + path


def survivors_of(path: str) -> list[int]:
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            argv = (entry / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        if path.encode() in argv:
            found.append(int(entry.name))
            try:
                os.kill(int(entry.name), 9)
            except OSError:
                pass
    return found


class Smoke156(unittest.TestCase):
    def run_smoke(self, knobs=None, env=None):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            real = td / "realhome"
            real.mkdir()
            env2 = {
                "PATH": os.environ.get("PATH", ""),
                "HOME": str(real),
                "PFY_SMOKE_RECEIPT_DIR": str(td / "r"),
            }
            stub_path = td / "sysknife"
            if knobs is not None:
                k = dict(knobs)
                if k.get("touch_real"):
                    k["touch_real"] = str(real)
                stub_path.write_text(f"#!{sys.executable}\nK = {k!r}\n" + STUB, encoding="utf-8")
                stub_path.chmod(0o755)
                env2["SYSKNIFE_BIN"] = str(stub_path)
            else:
                env2["SYSKNIFE_BIN"] = str(td / "missing")
            env2.update(env or {})
            if not env or "PATH" not in env:
                env2["PATH"] = _path_bwrap(td, env2.get("PATH", ""))
            proc = subprocess.run(
                [sys.executable, str(SCRIPT)], env=env2, capture_output=True, text=True, timeout=60,
            )
            receipt = json.loads((td / "r" / "sysknife" / "latest.json").read_text())
            survivors = survivors_of(str(stub_path))
            self.assertEqual(survivors, [], "stub sysknife outlived the smoke")
            return proc.returncode, receipt

    def test_missing_binary_exits_2(self):
        code, rec = self.run_smoke(None)
        self.assertEqual(code, 2)
        self.assertIn("not an executable", rec["reason"])

    def test_hang_is_killed(self):
        code, rec = self.run_smoke({"hang": True}, {"PFY_XINTAKE_TIMEOUT": "2"})
        self.assertEqual(code, 2)
        self.assertIn("timeout after 2s", rec["reason"])

    def test_grandchild_does_not_survive(self):
        code, rec = self.run_smoke({"orphan": True}, {"PFY_XINTAKE_TIMEOUT": "5"})
        self.assertEqual(code, 2, rec)
        self.assertIn("version pin", rec["reason"])

    def test_plan_passes_without_execution_flags(self):
        code, rec = self.run_smoke({})
        self.assertEqual(code, 0, rec)
        argv = rec["dry_run_argv"]
        self.assertIn("--dry-run", argv)
        self.assertNotIn("--yes", argv)
        self.assertNotIn("--dangerously-skip-approval", argv)

    def test_planner_unavailable_exits_2(self):
        code, rec = self.run_smoke({"dry_exit": 4})
        self.assertEqual(code, 2, rec)
        self.assertIn("did not return a plan", rec["reason"])

    def test_real_home_write_fails(self):
        code, rec = self.run_smoke({"touch_real": True}, {"PATH": "/nonexistent"})
        self.assertEqual(code, 1, rec)
        self.assertIn("real_home_unchanged", rec["failed"])

    def test_bad_timeout_exits_2(self):
        self.assertEqual(self.run_smoke({}, {"PFY_XINTAKE_TIMEOUT": "soon"})[0], 2)

    def test_receipt_dir_is_gitignored(self):
        proc = subprocess.run(
            ["git", "check-ignore", "-q", "pipelines/smoke/sysknife/latest.json"],
            cwd=ROOT,
        )
        self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
