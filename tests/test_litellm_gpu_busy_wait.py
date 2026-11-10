import unittest

from scripts.litellm_lane_guard import decide_gpu_wait


class TestLitellmGpuBusyWait(unittest.TestCase):
    def test_still_busy_after_budget_is_non_pass(self):
        decision = decide_gpu_wait(
            samples=[{"gpu_use_pct":40, "free_ram_gib":20}],
            polls=15,
            poll_seconds=60,
        )
        self.assertEqual(decision["action"], "non_pass")
        self.assertFalse(decision["start_model"])
        self.assertEqual(decision["measured"]["gpu_use_pct"], 40)
        self.assertEqual(decision["measured"]["free_ram_gib"], 20)

    def test_idle_card_may_start(self):
        decision = decide_gpu_wait(
            samples=[{"gpu_use_pct":10, "free_ram_gib":30}],
            polls=1,
            poll_seconds=60,
        )
        self.assertEqual(decision["action"], "start")
        self.assertTrue(decision["start_model"])


if __name__ == "__main__":
    unittest.main()
