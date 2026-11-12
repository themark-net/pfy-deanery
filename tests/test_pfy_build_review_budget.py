import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TestReviewBudget(unittest.TestCase):
    def test_ceiling_allows_exact_limit_and_refuses_past_it(self):
        from pfylib.review_chunks import ReviewBudgetExceeded, assert_review_budget

        assert_review_budget(total_chars=2_000_000, prompts=200)
        with self.assertRaises(ReviewBudgetExceeded) as too_big:
            assert_review_budget(total_chars=2_000_001, prompts=1)
        self.assertEqual(too_big.exception.status, "review-budget-exceeded")
        self.assertIn("split", str(too_big.exception).lower())
        with self.assertRaises(ReviewBudgetExceeded) as too_many:
            assert_review_budget(total_chars=1, prompts=201)
        self.assertEqual(too_many.exception.status, "review-budget-exceeded")
