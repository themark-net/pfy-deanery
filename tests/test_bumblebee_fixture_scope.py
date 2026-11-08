import pathlib
import unittest


class BumblebeeFixtureScopeTest(unittest.TestCase):
    def test_script_uses_worktree_fixture_not_home(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        script = root / "eval" / "integrate" / "bumblebee" / "run-on-main.sh"
        self.assertTrue(script.is_file(), "run-on-main.sh is missing")
        text = script.read_text(encoding="utf-8")
        self.assertIn("tmp/bumblebee-fixture", text)
        self.assertIn("scripts/pfy_mcp_scan.py", text)
        self.assertNotIn("~/.grok", text)
        self.assertNotIn("auth.json", text)


if __name__ == "__main__":
    unittest.main()
