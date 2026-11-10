import unittest

from scripts.verdict_write import freeze_ceiling_fields


class TestQwen38CeilingFreeze(unittest.TestCase):
    def test_ceiling_fields_stay_at_prior_values(self):
        prior = {"integration_stage": "probe", "tier_ceiling": "local"}
        proposed = {
            "integration_stage": "adopt",
            "tier_ceiling": "fast",
            "status": "complete",
            "next_gate": "trial-1",
        }
        written = freeze_ceiling_fields(prior, proposed)
        self.assertEqual(written["integration_stage"], "probe")
        self.assertEqual(written["tier_ceiling"], "local")
        self.assertEqual(written["status"], "complete")


if __name__ == "__main__":
    unittest.main()
