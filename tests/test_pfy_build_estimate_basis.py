import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TestNoHistoryEstimate(unittest.TestCase):
    def test_fixed_token_assumptions(self):
        from pfylib.review_chunks import estimate_without_history

        prices = {"grok-4.7": {"in": 5.0, "out": 15.0, "cached_in": 1.0}}
        est = estimate_without_history(
            prices, model="grok-4.7", attempts=1, review_prompts=1
        )
        self.assertEqual(est["usd"], 0.6875)
        self.assertEqual(est["low"], 0.34375)
        self.assertEqual(est["high"], 1.375)
        self.assertTrue(est["basis"].startswith("no-history"))
        self.assertIn("100000", est["basis"])
        self.assertIn("8000", est["basis"])
        self.assertIn("12000", est["basis"])
