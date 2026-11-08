import unittest
from pathlib import Path


class TestHeadsonOnePreview(unittest.TestCase):
    def test_single_strict_preview_in_temp(self):
        script = Path("eval/integrate/headson/run-on-main.sh").read_text()
        self.assertIn("-c", script)
        self.assertIn("-t", script)
        self.assertIn("strict", script)
        self.assertIn("mktemp", script)
        self.assertEqual(script.count("headson"), script.lower().count("headson"))
        self.assertNotIn(" -g", script)


if __name__ == "__main__":
    unittest.main()
