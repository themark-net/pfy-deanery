"""Scratch paths in host scripts follow TMPDIR instead of a fixed /tmp file.

Each script prints the path it will actually use and exits before any server,
model, or onboard step. A leftover hardcoded /tmp name fails the source check.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (script, flag, literals that must not remain)
CASES = (
    ("scripts/smoke-product-levers.sh", "--tmpdir-path", ("/tmp/pfy-product-",)),
    ("scripts/eval-auto.sh", "--exports-path", ("/tmp/pfy-eval-model-exports.sh",)),
    ("examples/litellm-ollama/host-ollama-gateway.sh", "--paths", ()),
    ("examples/eval-harness/smoke_tools_model.sh", "--scratch-path", ("/tmp/tools-sel.json", "/tmp/tools-sel.err")),
    ("examples/opencode-ollama/smoke.sh", "--scratch-path", ("/tmp/oc-ollama-tags.json",)),
    ("examples/voice-stt-edge/smoke-agent.sh", "--scratch-path", ("/tmp/voice-t0092-remote.log",)),
    ("examples/voice-stt-edge/smoke-orchestrate.sh", "--scratch-path", ("/tmp/voice-t0096-remote.log",)),
    ("examples/voice-stt-edge/smoke.sh", "--scratch-path", ("/tmp/voice-stt-probe.txt",)),
    ("examples/voice-stt-edge/smoke-remote.sh", "--scratch-path", ("/tmp/vr-", "/tmp/voice-remote-smoke.log")),
)


class TmpdirScriptTests(unittest.TestCase):
    def test_scratch_paths_follow_tmpdir_and_drop_fixed_tmp_names(self):
        for rel, flag, banned in CASES:
            with self.subTest(rel=rel):
                script = ROOT / rel
                text = script.read_text(encoding="utf-8")
                for needle in banned:
                    self.assertNotIn(needle, text, rel)
                td = Path(tempfile.mkdtemp(prefix="script-tmpdir-"))
                printed: list[str] = []
                try:
                    env = os.environ.copy()
                    env["TMPDIR"] = str(td)
                    env.pop("XDG_RUNTIME_DIR", None)
                    proc = subprocess.run(
                        ["bash", str(script), flag],
                        cwd=ROOT,
                        env=env,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(proc.returncode, 0, proc.stderr)
                    printed = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
                    self.assertTrue(printed, proc.stdout)
                    root = td.resolve()
                    for line in printed:
                        self.assertTrue(Path(line).resolve().is_relative_to(root), line)
                finally:
                    shutil.rmtree(td, ignore_errors=True)
                    for line in printed:
                        path = Path(line)
                        if path.is_dir():
                            shutil.rmtree(path, ignore_errors=True)
                        elif path.is_file():
                            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
