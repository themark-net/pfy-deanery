import unittest
from pathlib import Path


class TestLitellmSingleFlight(unittest.TestCase):
    def test_marker_exit_and_flock_comment(self):
        script = Path("eval/integrate/litellm/run-on-main.sh")
        text = script.read_text(encoding="utf-8")
        self.assertIn(
            "/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/litellm.dispatched",
            text,
        )
        self.assertIn("exit 2", text)
        self.assertIn("flock", text)
        self.assertNotIn("git push", text)


if __name__ == "__main__":
    unittest.main()
