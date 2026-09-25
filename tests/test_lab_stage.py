"""pfy stage --lab is the cage lab, and it is not the host checkout (T-0109)."""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PFY = ROOT / "scripts" / "pfy"


def _chunk() -> str:
    text = PFY.read_text(encoding="utf-8")
    start = text.index("print_fs_nav()")
    end = text.index("\nstub_harness()")
    lab = text.index("lab_stage()")
    lab_end = text.index("\ncmd_stage()")
    have = 'have() { [[ "${FAKE_DOCKER:-}" == "1" ]]; }\nmake() { printf "MAKE %s\\n" "$*"; return 0; }\n'
    return have + text[start:end] + "\n" + text[lab:lab_end]


class LabStageTests(unittest.TestCase):
    def test_inside_cage_refuses_before_make(self):
        env = os.environ.copy()
        env["FAKE_DOCKER"] = "1"
        env.pop("PFY_FS", None)
        script = _chunk() + '\nROOT="/workspace/pfy-mentat"\nlab_stage\n'
        proc = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("already in the cage tree", proc.stdout)
        self.assertNotIn("MAKE ", proc.stdout)

    def test_host_without_docker_skips_and_names_the_bind(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["HOME"] = tmp
            env.pop("PFY_FS", None)
            env.pop("FAKE_DOCKER", None)
            env.pop("AGENTCAGE_DIR", None)
            script = _chunk() + f'\nROOT="{tmp}/repo"\nlab_stage\n'
            proc = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn(f"{tmp}/.agentcage/workspace/pfy-mentat", proc.stdout)
        self.assertIn("that is not", proc.stdout)
        self.assertIn("lab skipped", proc.stdout)
        self.assertNotIn("MAKE ", proc.stdout)

    def test_host_with_docker_runs_the_three_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            env = os.environ.copy()
            env["HOME"] = tmp
            env["FAKE_DOCKER"] = "1"
            env.pop("PFY_FS", None)
            script = _chunk() + f'\nROOT="{repo}"\nlab_stage\n'
            proc = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("MAKE cage-doctor", proc.stdout)
        self.assertIn("MAKE cage-setup", proc.stdout)
        self.assertIn("MAKE cage-up-mcp", proc.stdout)
        self.assertLess(proc.stdout.index("MAKE cage-doctor"), proc.stdout.index("MAKE cage-setup"))
        self.assertLess(proc.stdout.index("MAKE cage-setup"), proc.stdout.index("MAKE cage-up-mcp"))

    def test_start_agent_cage_points_at_stage_lab(self):
        text = PFY.read_text(encoding="utf-8")
        body = text.split("stub_harness()", 1)[1]
        arm = body.split("agent-cage)", 1)[1].split("esac", 1)[0]
        self.assertIn("./pfy stage --lab", arm)
        self.assertNotIn("exec ", arm)


if __name__ == "__main__":
    unittest.main()
