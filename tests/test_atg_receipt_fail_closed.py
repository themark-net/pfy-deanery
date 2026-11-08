import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval/integrate/atomic-task-graph-atg/run-on-main.sh"
CARD = ROOT / "data/stages/atomic-task-graph-atg.json"


class ReceiptFailClosedTest(unittest.TestCase):
    def test_not_ancestor_writes_no_receipt(self):
        before = CARD.read_bytes() if CARD.exists() else None
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "receipt.json"
            env = os.environ.copy()
            env["ATG_FORCE_NOT_ANCESTOR"] = "1"
            env.pop("ATG_SKIP_MAIN_ANCESTOR", None)
            proc = subprocess.run(
                ["bash", str(SCRIPT), str(receipt)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertNotEqual(proc.returncode, 0, proc.stdout)
            self.assertFalse(receipt.exists())
        if before is not None:
            self.assertEqual(CARD.read_bytes(), before)

    def test_unloaded_model_writes_no_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "receipt.json"
            env = os.environ.copy()
            env["ATG_OFFLINE_CHECK"] = ""
            env["ATG_MODEL_LOADED"] = "0"
            env["ATG_SKIP_MAIN_ANCESTOR"] = "1"
            proc = subprocess.run(
                ["bash", str(SCRIPT), str(receipt)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(receipt.exists())


if __name__ == "__main__":
    unittest.main()
