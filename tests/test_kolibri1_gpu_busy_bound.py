import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestKolibri1GpuBusyBound(unittest.TestCase):
    def test_busy_past_bound_records_non_pass_without_model_start(self):
        driver = ROOT / "scripts" / "gpu_lane_driver.sh"
        with tempfile.TemporaryDirectory() as tmp:
            verdict = Path(tmp) / "VERDICT.json"
            env = os.environ.copy()
            env["PFY_TOOL"] = "kolibri-1"
            env["PFY_GPU_USE_PCT"] = "90"
            env["PFY_FREE_GIB"] = "8"
            env["PFY_GPU_WAIT_BOUND_SEC"] = "0"
            env["PFY_VERDICT_PATH"] = str(verdict)
            proc = subprocess.run(
                ["bash", str(driver), "--gpu-preflight"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            combined = proc.stdout + proc.stderr
            self.assertNotEqual(proc.returncode, 0)
            self.assertNotIn("ollama run", combined)
            data = json.loads(verdict.read_text())
            self.assertNotEqual(data.get("result"), "pass")
            blob = json.dumps(data)
            self.assertIn("90", blob)
            self.assertIn("8", blob)


if __name__ == "__main__":
    unittest.main()
