import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval/integrate/atomic-task-graph-atg/run-on-main.sh"


class OfflineBeforeModelTest(unittest.TestCase):
    def test_offline_check_skips_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "receipt.json"
            calls = Path(tmp) / "model_calls"
            offline = Path(tmp) / "offline_ok"
            offline.write_text("#!/bin/sh\necho offline\n", encoding="utf-8")
            offline.chmod(0o755)
            env = os.environ.copy()
            env["ATG_OFFLINE_CHECK"] = str(offline)
            env["ATG_MODEL_CMD"] = f"sh -c 'echo called >> {calls}'"
            env["ATG_SKIP_MAIN_ANCESTOR"] = "1"
            proc = subprocess.run(
                ["bash", str(SCRIPT), str(receipt)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertFalse(calls.exists())
            self.assertTrue(receipt.is_file(), proc.stderr)
            self.assertFalse(Path(str(receipt) + ".lock").exists())

    def test_relative_receipt_stays_on_the_caller_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "receipt.json"
            offline = Path(tmp) / "offline_ok"
            offline.write_text("#!/bin/sh\necho offline\n", encoding="utf-8")
            offline.chmod(0o755)
            caller = ROOT / "tests"
            relative = os.path.relpath(receipt, caller)
            env = os.environ.copy()
            env["ATG_OFFLINE_CHECK"] = str(offline)
            env["ATG_SKIP_MAIN_ANCESTOR"] = "1"
            env.pop("ATG_FORCE_NOT_ANCESTOR", None)
            env.pop("ATG_LANE_MARKER", None)
            proc = subprocess.run(
                ["bash", str(SCRIPT), relative],
                cwd=caller,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(receipt.is_file(), proc.stderr)
            wrong = (ROOT / relative).resolve()
            if wrong != receipt.resolve():
                self.assertFalse(wrong.exists())


if __name__ == "__main__":
    unittest.main()
