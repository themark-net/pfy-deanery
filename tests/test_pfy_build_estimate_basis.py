import os
import sys
import tempfile
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


class TestPackedReviewAndFlakeQuote(unittest.TestCase):
    """The quote must name packed reviews and local flake-gate re-runs."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pfy-est-"))
        self._saved = {
            key: os.environ.get(key)
            for key in ("HOME", "GROK_HOME", "PFY_COST_HISTORY_ROOT")
        }
        os.environ["HOME"] = str(self.tmp / "home")
        os.environ["GROK_HOME"] = str(self.tmp / "grok")
        os.environ["PFY_COST_HISTORY_ROOT"] = str(self.tmp / "no-history")
        (self.tmp / "home").mkdir()

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        for path in sorted(self.tmp.rglob("*"), reverse=True):
            if path.is_file() or path.is_symlink():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                path.rmdir()
        self.tmp.rmdir()

    def test_banner_and_receipt_name_packed_reviews_and_flake_runs(self):
        from pfylib.review_chunks import (
            build_route_quotes,
            estimate_receipt,
            format_route_banner,
        )

        prices = {"grok-4.7": {"in": 5.0, "out": 15.0, "cached_in": 1.0}}
        choice, chosen, other = build_route_quotes(
            "cloud", "grok-4.7", "test", 2, 2, prices, flake_runs=0
        )
        banner = format_route_banner(choice, chosen, other, 2)
        self.assertIn("packed review", banner)
        self.assertNotIn("per-file review", banner)
        rec = estimate_receipt(chosen, other)
        self.assertEqual(rec["review_prompts"], 2)
        self.assertEqual(rec["flake_runs"], 0)
        self.assertEqual(rec["alternative"]["route"], "local")
        self.assertEqual(rec["alternative"]["usd"], 0)

        choice, chosen, other = build_route_quotes(
            "local", "qwen3.6:35b", "local", 1, 1, prices, flake_runs=2
        )
        banner = format_route_banner(choice, chosen, other, 1)
        self.assertIn("flake-gate re-run", banner)
        self.assertIn("packed review", banner)
        rec = estimate_receipt(chosen, other)
        self.assertEqual(rec["usd"], 0)
        self.assertEqual(rec["flake_runs"], 2)
        self.assertEqual(rec["review_prompts"], 1)
        self.assertGreater(rec["alternative"]["usd"], 0)
        self.assertEqual(rec["alternative"]["review_prompts"], 1)
