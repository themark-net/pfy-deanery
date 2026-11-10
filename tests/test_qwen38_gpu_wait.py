import unittest

from scripts.gpu_preflight import wait_expired_verdict


class TestQwen38GpuWait(unittest.TestCase):
    def test_timeout_is_non_pass_with_measurements(self):
        samples = [
            {"gpu_use_pct": 80, "avail_ram_gib": 10},
            {"gpu_use_pct": 40, "avail_ram_gib": 20},
        ]
        verdict = wait_expired_verdict(samples, timed_out=True)
        self.assertNotEqual(verdict["status"], "pass")
        self.assertEqual(verdict["gpu_use_pct"], 40)
        self.assertEqual(verdict["avail_ram_gib"], 20)
        self.assertEqual(verdict["signaled_pids"], [])

    def test_clear_sample_does_not_expire(self):
        samples = [{"gpu_use_pct": 10, "avail_ram_gib": 64}]
        verdict = wait_expired_verdict(samples, timed_out=False)
        self.assertIsNone(verdict)


if __name__ == "__main__":
    unittest.main()
