import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval" / "integrate" / "strata" / "run-on-main.sh"
REAL_RECEIPT = ROOT / "eval" / "integrate" / "strata" / "receipt.json"


class StrataReceiptAncestryTest(unittest.TestCase):
    def test_pipeline_receipt_requires_origin_main_ancestor(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("pipeline", text)
        self.assertIn("origin/main", text)
        self.assertIn("merge-base", text)
        self.assertIn("--is-ancestor", text)
        self.assertIn("receipt.json", text)

    def test_worktree_head_writes_no_receipt(self):
        self.assertFalse(REAL_RECEIPT.exists())
        with tempfile.TemporaryDirectory() as raw:
            receipt = pathlib.Path(raw) / "receipt.json"
            env = os.environ.copy()
            for key in (
                "GIT_DIR",
                "GIT_WORK_TREE",
                "GIT_INDEX_FILE",
                "PFY_STRATA_BASE",
                "PFY_STRATA_API_KEY",
                "STRATA_API_KEY",
            ):
                env.pop(key, None)
            env["PFY_STRATA_LANE_MARKER"] = str(pathlib.Path(raw) / "missing-marker")
            proc = subprocess.run(
                ["bash", str(SCRIPT), str(receipt)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertFalse(receipt.exists())
            self.assertIn("no receipt", proc.stderr)
            self.assertIn("origin/main", proc.stderr)
        self.assertFalse(REAL_RECEIPT.exists())


if __name__ == "__main__":
    unittest.main()
