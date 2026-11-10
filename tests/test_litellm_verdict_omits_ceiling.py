import json
import unittest

from scripts.litellm_verdict_writer import build_verdict


class TestLitellmVerdictOmitsCeiling(unittest.TestCase):
    def test_writer_omits_stage_and_ceiling(self):
        raw = build_verdict(
            tool="litellm",
            measured={"timeout":False, "gpu_use_pct":12},
        )
        verdict = json.loads(raw)
        self.assertNotIn("integration_stage", verdict)
        self.assertNotIn("tier_ceiling", verdict)
        self.assertEqual(verdict["tool"], "litellm")
        self.assertFalse(verdict["measured"]["timeout"])


if __name__ == "__main__":
    unittest.main()
