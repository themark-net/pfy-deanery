import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval" / "integrate" / "strata" / "run-on-main.sh"


class StrataReceiptAncestryTest(unittest.TestCase):
    def test_pipeline_receipt_requires_origin_main_ancestor(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("pipeline", text)
        self.assertIn("origin/main", text)
        self.assertIn("merge-base", text)
        self.assertIn("--is-ancestor", text)
        self.assertIn("receipt.json", text)


if __name__ == "__main__":
    unittest.main()
