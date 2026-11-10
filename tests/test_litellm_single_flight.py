import unittest
from pathlib import Path

from scripts.litellm_lane_guard import second_run_may_start


class TestLitellmSingleFlight(unittest.TestCase):
    def test_blocks_when_lock_held_or_state_exists(self):
        self.assertFalse(second_run_may_start(lock_held=True, state_exists=False))
        self.assertFalse(second_run_may_start(lock_held=False, state_exists=True))
        self.assertTrue(second_run_may_start(lock_held=False, state_exists=False))

    def test_marker_exit_and_flock_comment(self):
        script = Path("eval/integrate/litellm/run-on-main.sh")
        text = script.read_text(encoding="utf-8")
        self.assertIn(
            "$HOME/DEVELOP/pfy-mentat/tmp/integrate2/litellm.dispatched",
            text,
        )
        self.assertIn("exit 2", text)
        self.assertIn("flock", text)
        self.assertNotIn("git push", text)


if __name__ == "__main__":
    unittest.main()
