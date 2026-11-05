"""Entry 159 smoke (Skills Manager): missing node exits 2, a hang and a grandchild are killed,
npm is pointed at a worktree scratch, list may refuse with no skill home, and a real-HOME write fails."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples/x-intake-local/smoke_159.py"

CLI = r'''
import os, sys, time
a = sys.argv[1:]
if K.get("orphan"):
    if os.fork() == 0:
        time.sleep(30)
        os._exit(0)
    os._exit(0)
if K.get("hang"):
    time.sleep(60)
if K.get("touch_real"):
    os.makedirs(os.path.join(K["touch_real"], ".skills-manager"), exist_ok=True)
if "--version" in a:
    print(K.get("version", "2026.10.27-1"))
    raise SystemExit(0)
if "--help" in a:
    print("Usage: skills-manager")
    raise SystemExit(0)
if "list" in a:
    print("No skill home at " + (a[a.index("--home") + 1] if "--home" in a else "missing"), file=sys.stderr)
    raise SystemExit(1)
raise SystemExit(2)
'''

NPM = r'''
import os, pathlib, sys
argv = sys.argv[1:]
prefix = pathlib.Path(argv[argv.index("--prefix") + 1])
home = pathlib.Path(os.environ["HOME"])
cache = pathlib.Path(os.environ["npm_config_cache"])
pathlib.Path(K["mark"]).write_text(str(home) + "\n" + str(cache) + "\n" + str(prefix) + "\n")
bin_dir = prefix / "bin"
bin_dir.mkdir(parents=True, exist_ok=True)
cli = bin_dir / "skills-manager"
cli.write_text("#!" + sys.executable + "\n" + K["cli"], encoding="utf-8")
cli.chmod(0o755)
raise SystemExit(0)
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


class Smoke159(unittest.TestCase):
    def run_smoke(self, knobs=None, env=None, npm=False):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            real = td / "realhome"
            real.mkdir()
            env2 = {
                "PATH": os.environ.get("PATH", ""),
                "HOME": str(real),
                "PFY_SMOKE_RECEIPT_DIR": str(td / "r"),
            }
            stub_path = td / "skills-manager"
            if npm:
                mark = td / "mark"
                cli_body = "K = {'version': '2026.10.27-1'}\n" + CLI
                npm_path = td / "npm"
                npm_path.write_text(
                    f"#!{sys.executable}\nK = {{'mark': {str(mark)!r}, 'cli': {cli_body!r}}}\n" + NPM,
                    encoding="utf-8",
                )
                npm_path.chmod(0o755)
                env2["SKILLS_MANAGER_NPM"] = str(npm_path)
                env2["SKILLS_MANAGER_NODE"] = sys.executable
            elif knobs is not None:
                k = dict(knobs)
                if k.get("touch_real"):
                    k["touch_real"] = str(real)
                stub_path.write_text(f"#!{sys.executable}\nK = {k!r}\n" + CLI, encoding="utf-8")
                stub_path.chmod(0o755)
                env2["SKILLS_MANAGER_BIN"] = str(stub_path)
            else:
                env2["SKILLS_MANAGER_NODE"] = str(td / "missing-node")
            env2.update(env or {})
            proc = subprocess.run(
                [sys.executable, str(SCRIPT)], env=env2, capture_output=True, text=True, timeout=60,
            )
            receipt = json.loads((td / "r" / "skills-manager" / "latest.json").read_text())
            survivors = survivors_of(str(stub_path))
            self.assertEqual(survivors, [], "skills-manager outlived the smoke")
            if npm:
                home, cache, prefix = (td / "mark").read_text().splitlines()
                root = str(ROOT.resolve())
                for place in (home, cache, prefix):
                    self.assertTrue(place.startswith(root + "/tmp/"), place)
                    self.assertFalse(place.startswith(str(real)))
            return proc.returncode, receipt

    def test_missing_node_exits_2(self):
        code, rec = self.run_smoke(None)
        self.assertEqual(code, 2)
        self.assertIn("node is not available", rec["reason"])

    def test_hang_is_killed(self):
        code, rec = self.run_smoke({"hang": True}, {"PFY_XINTAKE_TIMEOUT": "2"})
        self.assertEqual(code, 2, rec)
        self.assertIn("timeout after 2s", rec["reason"])

    def test_grandchild_does_not_survive(self):
        code, rec = self.run_smoke({"orphan": True}, {"PFY_XINTAKE_TIMEOUT": "5"})
        self.assertEqual(code, 2, rec)

    def test_help_and_list_refusal_pass(self):
        code, rec = self.run_smoke({})
        self.assertEqual(code, 0, rec)
        self.assertEqual(rec["checks"]["list"], "no_skill_home")

    def test_npm_scratch_stays_in_the_worktree(self):
        code, rec = self.run_smoke(npm=True)
        self.assertEqual(code, 0, rec)
        self.assertTrue(str(rec["checks"]["npm_cache"]).startswith(str(ROOT.resolve()) + "/tmp/"))

    def test_real_home_write_fails(self):
        code, rec = self.run_smoke({"touch_real": True})
        self.assertEqual(code, 1, rec)
        self.assertIn("real_home_unchanged", rec["failed"])

    def test_bad_timeout_exits_2(self):
        self.assertEqual(self.run_smoke({}, {"PFY_XINTAKE_TIMEOUT": "soon"})[0], 2)

    def test_receipt_dir_is_gitignored(self):
        proc = subprocess.run(
            ["git", "check-ignore", "-q", "pipelines/smoke/skills-manager/latest.json"],
            cwd=ROOT,
        )
        self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
