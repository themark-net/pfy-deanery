"""Entry 160 smoke (agentplay): a missing interpreter exits 2, a hang and a
grandchild are killed, import of a synthetic map does not open the viewer, a
real-HOME write fails, and the receipt is gitignored."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples/x-intake-local/smoke_160.py"
SESSION = "local:claude-code:pfy-smoke-160"

CLI = r'''
import os, sys, time
from pathlib import Path
a = sys.argv[1:]
mark = K.get("mark")
if mark:
    Path(mark).open("a").write(
        (os.environ.get("AGENTPLAY_NO_NETWORK") or "") + "\t" + os.environ.get("HOME", "") + "\t"
        + " ".join(a) + "\n"
    )
if K.get("orphan"):
    if os.fork() == 0:
        time.sleep(30)
        os._exit(0)
    os._exit(0)
if K.get("hang"):
    time.sleep(60)
if K.get("touch_real"):
    os.makedirs(os.path.join(K["touch_real"], ".agentplay"), exist_ok=True)
if "--version" in a:
    print(K.get("version", "0.2.6"))
    raise SystemExit(0)
if "--help" in a:
    print("usage: agentplay\nimport  add map files\nlist  list sessions\nview  open the viewer")
    raise SystemExit(0)
if a and a[0] == "view":
    raise SystemExit(99)
if a and a[0] == "import":
    print("Imported 1 map(s).")
    raise SystemExit(0)
if a and a[0] == "list":
    print(K.get("session", "local:claude-code:pfy-smoke-160"))
    raise SystemExit(0)
raise SystemExit(2)
'''

PYTHON = r'''
import os, pathlib, sys
argv = sys.argv[1:]
if argv[:1] == ["-c"]:
    print("3.14")
    raise SystemExit(0)
if argv[:2] == ["-m", "venv"]:
    dest = pathlib.Path(argv[2])
    bindir = dest / "bin"
    bindir.mkdir(parents=True)
    pip = bindir / "pip"
    cli = bindir / "agentplay"
    cli.write_text("#!" + sys.executable + "\n" + K["cli"], encoding="utf-8")
    cli.chmod(0o755)
    pip.write_text(
        "#!" + sys.executable + "\n"
        "import os, pathlib, sys\n"
        "pathlib.Path(" + repr(K["mark"]) + ").write_text(os.environ.get('HOME','') + '\\n' + os.environ.get('PIP_CACHE_DIR','') + '\\n' + ' '.join(sys.argv[1:]))\n"
        "raise SystemExit(0)\n",
        encoding="utf-8",
    )
    pip.chmod(0o755)
    raise SystemExit(0)
raise SystemExit(2)
'''


def survivors_of(path: str) -> list[int]:
    found = []
    needle = path.encode()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            argv = (entry / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        if needle in argv or any(needle in part for part in argv):
            found.append(int(entry.name))
            try:
                os.kill(int(entry.name), 9)
            except OSError:
                pass
    return found


class Smoke160(unittest.TestCase):
    def run_smoke(self, knobs=None, env=None, python=False):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            real = td / "realhome"
            real.mkdir()
            env2 = {
                "PATH": os.environ.get("PATH", ""),
                "HOME": str(real),
                "PFY_SMOKE_RECEIPT_DIR": str(td / "r"),
            }
            stub_path = td / "agentplay"
            mark = td / "mark"
            if python:
                cli_body = "K = {'version': '0.2.6', 'session': %r}\n" % SESSION + CLI
                py = td / "python3"
                py.write_text(
                    f"#!{sys.executable}\nK = {{'mark': {str(mark)!r}, 'cli': {cli_body!r}}}\n" + PYTHON,
                    encoding="utf-8",
                )
                py.chmod(0o755)
                env2["AGENTPLAY_PYTHON"] = str(py)
            elif knobs is not None:
                k = dict(knobs)
                k["mark"] = str(mark)
                if k.get("touch_real"):
                    k["touch_real"] = str(real)
                stub_path.write_text(f"#!{sys.executable}\nK = {k!r}\n" + CLI, encoding="utf-8")
                stub_path.chmod(0o755)
                env2["AGENTPLAY_BIN"] = str(stub_path)
            else:
                env2["AGENTPLAY_PYTHON"] = str(td / "missing-python")
            env2.update(env or {})
            proc = subprocess.run(
                [sys.executable, str(SCRIPT)], env=env2, capture_output=True, text=True, timeout=60,
            )
            receipt = json.loads((td / "r" / "agentplay" / "latest.json").read_text())
            survivors = survivors_of(str(stub_path))
            self.assertEqual(survivors, [], "agentplay outlived the smoke")
            mark_text = mark.read_text() if mark.exists() else ""
            return proc.returncode, receipt, mark_text, real

    def test_missing_python_exits_2(self):
        code, rec, _mark, _real = self.run_smoke(None)
        self.assertEqual(code, 2)
        self.assertIn("python3 is not available", rec["reason"])

    def test_hang_is_killed(self):
        code, rec, _mark, _real = self.run_smoke({"hang": True}, {"PFY_XINTAKE_TIMEOUT": "2"})
        self.assertEqual(code, 2, rec)
        self.assertIn("timeout after 2s", rec["reason"])

    def test_grandchild_does_not_survive(self):
        code, rec, _mark, _real = self.run_smoke({"orphan": True}, {"PFY_XINTAKE_TIMEOUT": "5"})
        self.assertEqual(code, 2, rec)

    def test_import_does_not_open_the_viewer(self):
        code, rec, mark, real = self.run_smoke({"version": "0.2.6", "session": SESSION})
        self.assertEqual(code, 0, rec)
        self.assertEqual(rec["checks"]["parse"], "imported")
        self.assertEqual(rec["checks"]["browser"], "not_opened")
        lines = mark.splitlines()
        self.assertTrue(lines)
        for line in lines:
            flag, home, _argv = line.split("\t", 2)
            self.assertEqual(flag, "1")
            self.assertFalse(home.startswith(str(real)))
            self.assertNotIn(" view", " " + line)
            self.assertFalse(line.endswith("\tview") or "\tview " in line)

    def test_venv_scratch_stays_in_the_worktree(self):
        code, rec, mark, real = self.run_smoke(python=True)
        self.assertEqual(code, 0, rec)
        home, cache, argv = mark.split("\n", 2)
        root = str((ROOT / "tmp").resolve())
        self.assertTrue(home.startswith(root + "/"), home)
        self.assertTrue(cache.startswith(root + "/"), cache)
        self.assertNotIn(str(real), home)
        self.assertIn("agentplay==0.2.6", argv)
        self.assertTrue(str(rec["checks"]["pip_cache"]).startswith(root + "/"))

    def test_real_home_write_fails(self):
        code, rec, _mark, _real = self.run_smoke({"touch_real": True})
        self.assertEqual(code, 1, rec)
        self.assertIn("real_home_unchanged", rec["failed"])

    def test_bad_timeout_exits_2(self):
        self.assertEqual(self.run_smoke({}, {"PFY_XINTAKE_TIMEOUT": "soon"})[0], 2)

    def test_receipt_dir_is_gitignored(self):
        proc = subprocess.run(
            ["git", "check-ignore", "-q", "pipelines/smoke/agentplay/latest.json"],
            cwd=ROOT,
        )
        self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
