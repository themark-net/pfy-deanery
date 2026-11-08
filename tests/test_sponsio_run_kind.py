import unittest
from pathlib import Path


class SponsioRunKindTest(unittest.TestCase):
    def test_run_kind_pipeline(self):
        text = Path("eval/integrate/sponsio/run-on-main.sh").read_text()
        self.assertIn("pipeline", text)
        self.assertNotIn("gate", text)


if __name__ == "__main__":
    unittest.main()
