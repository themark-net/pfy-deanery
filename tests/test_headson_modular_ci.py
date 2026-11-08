import unittest
from pathlib import Path


class TestHeadsonModularCi(unittest.TestCase):
    def test_lane_adds_no_ci_job_or_model_lock(self):
        script = Path("eval/integrate/headson/run-on-main.sh").read_text()
        self.assertNotIn(".github/workflows", script)
        self.assertNotIn("model_lock.sh", script)
        self.assertNotIn("test_select.py", script)
        self.assertNotIn("run_tests.py", script)
        self.assertFalse(Path(".github/workflows/headson.yml").exists())
        self.assertFalse(Path("ci/headson.yml").exists())


if __name__ == "__main__":
    unittest.main()
