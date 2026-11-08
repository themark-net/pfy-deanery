import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval/integrate/neatroots/run-on-main.sh"
FIXTURE = ROOT / "eval/integrate/neatroots/fixtures/trace.json"

class TestNeatrootsFixture(unittest.TestCase):
    def test_one_local_fixture_and_no_network(self):
        self.assertTrue(FIXTURE.is_file())
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("eval/integrate/neatroots/fixtures/trace.json", text)
        self.assertNotIn("curl ", text)
        self.assertNotIn("http://", text)
        self.assertNotIn("https://", text)

if __name__ == "__main__":
    unittest.main()
