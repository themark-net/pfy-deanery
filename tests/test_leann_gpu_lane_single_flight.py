import unittest
from pathlib import Path


class LeannGpuLaneSingleFlightTest(unittest.TestCase):
    def test_driver_holds_leann_model_lock_across_verdict_write(self):
        driver = Path("scripts/gpu_lane_driver.sh").read_text(encoding="utf-8")
        lock = Path("scripts/model_lock.sh").read_text(encoding="utf-8")
        self.assertIn("model_lock.sh", driver)
        self.assertRegex(driver, r"model_lock\.sh[^\n]*leann")
        self.assertIn("VERDICT.json", driver)
        self.assertRegex(lock, r"flock|mkdir")
        self.assertNotRegex(lock, r"global[_-]?ci[_-]?lock")


if __name__ == "__main__":
    unittest.main()
