import unittest

from scripts.lane_claim import duplicate_run_blocked


class TestQwen38DuplicateRun(unittest.TestCase):
    def test_completed_same_gate_blocks_before_start(self):
        verdict = {"status": "complete", "next_gate": "trial-1"}
        self.assertTrue(duplicate_run_blocked(verdict, "trial-1"))

    def test_different_gate_allows_start(self):
        verdict = {"status": "complete", "next_gate": "trial-1"}
        self.assertFalse(duplicate_run_blocked(verdict, "trial-2"))

    def test_failed_same_gate_allows_start(self):
        verdict = {"status": "fail", "next_gate": "trial-1"}
        self.assertFalse(duplicate_run_blocked(verdict, "trial-1"))

    def test_missing_verdict_allows_start(self):
        self.assertFalse(duplicate_run_blocked(None, "trial-1"))


if __name__ == "__main__":
    unittest.main()
