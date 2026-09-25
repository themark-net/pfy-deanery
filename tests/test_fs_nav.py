"""pfy tells a harness whether it sees the host tree or the cage bind (T-0108)."""
from __future__ import annotations

import json
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
    return text[start:end]


class FsNavTests(unittest.TestCase):
    def test_host_root_is_direct_and_names_the_cage_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["HOME"] = tmp
            env.pop("PFY_FS", None)
            env.pop("AGENTCAGE_DIR", None)
            script = _chunk() + '\nROOT="/home/mark/DEVELOP/pfy-mentat"\nprint_fs_nav\nprintf "%s\\n" "$PFY_FS"\n'
            proc = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("filesystem: direct", proc.stdout)
        self.assertIn("root: /home/mark/DEVELOP/pfy-mentat", proc.stdout)
        self.assertIn(f"{tmp}/.agentcage/workspace/pfy-mentat", proc.stdout)
        self.assertIn("make cage-code-sync", proc.stdout)
        self.assertTrue(proc.stdout.strip().endswith("direct"))

    def test_workspace_root_is_cage(self):
        env = os.environ.copy()
        env.pop("PFY_FS", None)
        script = _chunk() + '\nROOT="/workspace/pfy-mentat"\nprint_fs_nav\nprintf "%s\\n" "$PFY_FS_ROOT"\n'
        proc = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("filesystem: cage", proc.stdout)
        self.assertIn("filesystem MCP", proc.stdout)
        self.assertTrue(proc.stdout.strip().endswith("/workspace/pfy-mentat"))

    def test_continue_config_uses_live_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["STATE_DIR"] = tmp
            env["LOCAL_OPENAI_BASE_URL"] = "http://127.0.0.1:11434"
            script = _chunk() + "\nwrite_continue_config\n"
            proc = subprocess.run(["bash", "-c", script], env=env, capture_output=True, text=True)
            doc = json.loads((Path(tmp) / "continue-config.json").read_text(encoding="utf-8"))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(doc["models"][0]["apiBase"], "http://127.0.0.1:11434/v1")
        self.assertIn("apiBase: http://127.0.0.1:11434/v1", proc.stdout)

    def test_continue_stub_prints_filesystem_and_does_not_exec(self):
        text = PFY.read_text(encoding="utf-8")
        body = text.split("stub_harness()", 1)[1]
        arm = body.split("continue)", 1)[1].split("agent-cage)", 1)[0]
        self.assertIn("write_continue_config", arm)
        self.assertNotIn("exec ", arm)
        self.assertIn("print_fs_nav", body.split('echo "STUB harness:', 1)[0])


if __name__ == "__main__":
    unittest.main()
