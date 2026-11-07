#!/usr/bin/env python3
"""The model lock blocks a second command and does not deadlock when nested.

How this fails: two local-model commands run at once, or a Make target that
wraps model_lock.sh hangs because the recipe calls it again.
Recovery: the second command starts only after the first exits. A nested
call sees PFY_MODEL_LOCK_HELD and returns immediately. No arguments exit 2.
Landing scripts do not call the lock.
"""
from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "scripts" / "model_lock.sh"
LANDINGS = (
    "scripts/pregate.sh",
    "scripts/ci_selected_tests.sh",
    "scripts/run_tests.py",
)


class ModelLockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pfy-lock-"))
        self.env = os.environ.copy()
        self.env["HOME"] = str(self.tmp)
        self.env["PFY_MODEL_LOCK"] = str(self.tmp / "local-model.lock")
        self.env.pop("PFY_MODEL_LOCK_HELD", None)

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_second_command_waits_and_nested_call_returns(self) -> None:
        held = self.tmp / "held"
        release = self.tmp / "release"
        second_flag = self.tmp / "second"
        holder_src = self.tmp / "hold.py"
        holder_src.write_text(
            textwrap.dedent(
                """\
                import os, pathlib, time
                pathlib.Path(os.environ["HELD"]).write_text("1")
                deadline = time.monotonic() + 15
                while not pathlib.Path(os.environ["RELEASE"]).exists():
                    if time.monotonic() > deadline:
                        raise SystemExit("holder timed out")
                    time.sleep(0.05)
                """
            ),
            encoding="utf-8",
        )
        env = dict(self.env)
        env["HELD"] = str(held)
        env["RELEASE"] = str(release)
        holder = subprocess.Popen(
            [str(LOCK), sys.executable, str(holder_src)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.monotonic() + 10
        while not held.exists():
            if holder.poll() is not None or time.monotonic() > deadline:
                out, err = holder.communicate()
                self.fail(f"holder exited {holder.returncode}\n{out}\n{err}")
            time.sleep(0.05)
        second_src = self.tmp / "second.py"
        second_src.write_text(
            "import os, pathlib\npathlib.Path(os.environ['SECOND']).write_text('1')\n",
            encoding="utf-8",
        )
        env["SECOND"] = str(second_flag)
        second = subprocess.Popen(
            [str(LOCK), sys.executable, str(second_src)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        time.sleep(0.4)
        self.assertFalse(second_flag.exists(), "second command ran while the lock was held")
        self.assertIsNone(second.poll())
        release.write_text("1", encoding="utf-8")
        out, err = second.communicate(timeout=10)
        self.assertEqual(second.returncode, 0, out + err)
        self.assertTrue(second_flag.exists())
        hout, herr = holder.communicate(timeout=10)
        self.assertEqual(holder.returncode, 0, hout + herr)

        started = time.monotonic()
        nested = subprocess.run(
            [str(LOCK), str(LOCK), "true"],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(nested.returncode, 0, nested.stderr)
        self.assertLess(time.monotonic() - started, 4)

        usage = subprocess.run(
            [str(LOCK)],
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(usage.returncode, 2, usage.stderr)
        self.assertIn("usage:", usage.stderr)

    def test_landing_scripts_do_not_take_the_lock(self) -> None:
        for rel in LANDINGS:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotIn("model_lock.sh", text, rel)
            self.assertNotIn("heavy-1030.lock", text, rel)
            self.assertNotIn("local-model.lock", text, rel)
        mode = LOCK.stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR, "scripts/model_lock.sh is not executable")


if __name__ == "__main__":
    unittest.main()
