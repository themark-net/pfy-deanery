"""gpu_lane_driver.sh: one GPU lane at a time, headroom and disk checks, park with a reason.

How this fails: two GPU lanes start together, a lane starts while the GPU is
busy, a big pull starts without disk room, or a rerun repeats a finished
slug. How we recover: the driver runs lanes in the foreground one by one,
parks a slug with "no headroom" or "no disk", and skips .finished/.parked.
The lane, rocm-smi and the approvals file are stubs under TMPDIR.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "scripts" / "gpu_lane_driver.sh"


class GpuDriverTest(unittest.TestCase):
    def _setup(self, td: Path, busy: int = 5):
        root = td / "wt"
        ops_q = root / "tmp" / "ops" / "eval" / "catalog-queue"
        ops_q.mkdir(parents=True)
        (root / "data" / "stages").mkdir(parents=True)
        (ops_q / "approvals.tsv").write_text(
            "slug\tblock\tdecided\tnote\n"
            "aa-gpu\tgpu\t2026-11-10\tok\n"
            "bb-pull\tpull-over-25gb\t2026-11-10\tok\n"
            "cc-gpu\tgpu\t2026-11-10\tok\n",
            encoding="utf-8",
        )
        (root / "data" / "stages" / "bb-pull.json").write_text('{"uses": "a 37.6 GB GGUF"}\n', encoding="utf-8")
        bin_dir = td / "bin"
        bin_dir.mkdir()
        smi = bin_dir / "rocm-smi"
        smi.write_text(f"#!/bin/sh\necho 'GPU[0]\t\t: GPU use (%): {busy}'\n", encoding="utf-8")
        smi.chmod(0o755)
        lane = td / "lane.sh"
        log = td / "lane.log"
        lane.write_text(
            "#!/bin/bash\n"
            f"echo \"start $2 $(date +%s%N)\" >> {log}\n"
            "grep -q 'GPU rules' \"$8\" || exit 9\n"
            "sleep 0.2\n"
            f"echo \"end $2 $(date +%s%N)\" >> {log}\n"
            "exit 0\n",
            encoding="utf-8",
        )
        lane.chmod(0o755)
        state = td / "loop" / "eval"
        env = {k: v for k, v in os.environ.items() if k != "PFY_OPS_ROOT"}
        env.update({
            "PATH": f"{bin_dir}:{env['PATH']}",
            "PFY_GPU_LANE": str(lane),
            "PFY_GPU_SAMPLE_SEC": "0",
            "PFY_GPU_WAIT_SEC": "0",
            "PFY_GPU_MAX_WAITS": "2",
            "PFY_GPU_MIN_RAM_GIB": "0",
            "PFY_GPU_PULL_DIR": str(td),
        })
        return root, state, env, log

    def _run(self, root, state, env, **extra):
        e = dict(env, **extra)
        return subprocess.run(["bash", str(DRIVER), "--root", str(root), "--state", str(state)], capture_output=True, text=True, env=e, timeout=60)

    def test_runs_one_at_a_time_parks_no_disk_and_skips_on_rerun(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root, state, env, log = self._setup(td)
            out = self._run(root, state, env, PFY_GPU_DISK_MARGIN_GB="999999")
            self.assertEqual(out.returncode, 0, out.stderr)
            gpu = state.parent / "gpu"
            self.assertEqual((gpu / "aa-gpu.finished").read_text().strip(), "0")
            self.assertEqual((gpu / "cc-gpu.finished").read_text().strip(), "0")
            self.assertTrue((gpu / "bb-pull.parked").read_text().startswith("no disk"))
            self.assertTrue((gpu / "ALL_DONE").is_file())
            self.assertTrue((state / "aa-gpu.dispatched").is_file())
            lines = log.read_text().split("\n")
            events = [line.split()[:2] for line in lines if line]
            self.assertEqual(events, [["start", "aa-gpu"], ["end", "aa-gpu"], ["start", "cc-gpu"], ["end", "cc-gpu"]])
            again = self._run(root, state, env)
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertEqual(log.read_text().count("start"), 2)

    def test_busy_gpu_waits_then_parks_and_never_runs_the_lane(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root, state, env, log = self._setup(td, busy=95)
            out = self._run(root, state, env)
            self.assertEqual(out.returncode, 0, out.stderr)
            gpu = state.parent / "gpu"
            for slug in ("aa-gpu", "bb-pull", "cc-gpu"):
                self.assertTrue((gpu / f"{slug}.parked").read_text().startswith("no headroom (gpu_busy=95%"), slug)
            self.assertFalse(log.exists())
            self.assertIn("waiting for headroom", (gpu / "progress.md").read_text())

    def test_second_driver_and_stop_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root, state, env, log = self._setup(td)
            gpu = state.parent / "gpu"
            gpu.mkdir(parents=True)
            sleeper = subprocess.Popen(["sleep", "30"])
            try:
                (gpu / "driver.pid").write_text(f"{sleeper.pid}\n")
                out = self._run(root, state, env)
                self.assertEqual(out.returncode, 2)
                self.assertIn("driver already running", out.stderr)
            finally:
                sleeper.kill()
                sleeper.wait()
            (gpu / "STOP").write_text("stop\n")
            out = self._run(root, state, env)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertFalse(log.exists())


if __name__ == "__main__":
    unittest.main()
