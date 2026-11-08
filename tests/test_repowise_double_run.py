import unittest
from pathlib import Path


class TestRepowiseDoubleRun(unittest.TestCase):
    def test_script_stops_a_second_start(self):
        text = Path("eval/integrate/repowise/run-on-main.sh").read_text()
        self.assertIn("repowise.dispatched", text)
        self.assertIn("exit 2", text)
        self.assertNotIn("model_lock.sh", text)
        self.assertNotIn("mkdir", text.lower().split("repowise.dispatched")[0][-80:])
        self.assertTrue("flock" in text)
