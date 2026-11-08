import unittest
from pathlib import Path


class TestHeadsonSingleFlight(unittest.TestCase):
    def test_second_start_exits_2_without_new_lock(self):
        script = Path("eval/integrate/headson/run-on-main.sh").read_text()
        self.assertIn(
            "/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/headson.dispatched",
            script,
        )
        self.assertIn("exit 2", script)
        self.assertIn("flock", script.lower())
        self.assertNotIn("model_lock.sh", script)
        self.assertNotIn("git push", script)


if __name__ == "__main__":
    unittest.main()
