import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestKolibri1LaneSingleFlight(unittest.TestCase):
    def test_second_run_exits_without_starting_model(self):
        driver = ROOT / "scripts" / "gpu_lane_driver.sh"
        env = os.environ.copy()
        env["PFY_MODEL_LOCK_HELD"] = "1"
        env["PFY_TOOL"] = "kolibri-1"
        proc = subprocess.run(
            ["bash", str(driver), "--check-lock"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        combined = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 75)
        self.assertNotIn("ollama run", combined)
        self.assertIn("kolibri-1", combined)


if __name__ == "__main__":
    unittest.main()
