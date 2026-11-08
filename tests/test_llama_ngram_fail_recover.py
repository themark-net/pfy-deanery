#!/usr/bin/env python3
"""Fail and recover: missing server, missing model, and a HEAD that is not on main."""
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "scripts" / "integrations" / "llama_ngram" / "run.py"
WRAPPER = ROOT / "eval" / "integrate" / "llama-cpp-ngram-mod" / "run-on-main.sh"


class TestLlamaNgramFailRecover(unittest.TestCase):
    def test_missing_server_uses_baseline(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            spawns = root / "spawns"
            model = root / "m.gguf"
            model.write_bytes(b"gguf")
            env = os.environ.copy()
            env.update(
                {
                    "PFY_LLAMA_NGRAM": "1",
                    "PFY_LLAMA_NGRAM_MODEL": str(model),
                    "PFY_LLAMA_NGRAM_FAKE_SERVER": str(root / "missing-llama-server"),
                    "PFY_NGRAM_SPAWNS": str(spawns),
                    "PFY_LLAMA_NGRAM_LOCK_DIR": str(root / "lock"),
                }
            )
            proc = subprocess.run(
                [sys.executable, str(RUN)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            blob = (proc.stdout + proc.stderr).lower()
            self.assertEqual(proc.returncode, 0, blob)
            self.assertIn("baseline", blob)
            self.assertIn("missing", blob)
            self.assertFalse(spawns.exists(), blob)

    def test_missing_model_uses_baseline(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            spawns = root / "spawns"
            fake = root / "llama-server"
            fake.write_text(
                "#!/bin/sh\nprintf x >> \"$PFY_NGRAM_SPAWNS\"\nprintf 'ok\\n'\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
            env = os.environ.copy()
            env.update(
                {
                    "PFY_LLAMA_NGRAM": "1",
                    "PFY_LLAMA_NGRAM_MODEL": str(root / "no-such.gguf"),
                    "PFY_LLAMA_NGRAM_FAKE_SERVER": str(fake),
                    "PFY_NGRAM_SPAWNS": str(spawns),
                    "PFY_LLAMA_NGRAM_LOCK_DIR": str(root / "lock"),
                }
            )
            proc = subprocess.run(
                [sys.executable, str(RUN)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            blob = (proc.stdout + proc.stderr).lower()
            self.assertEqual(proc.returncode, 0, blob)
            self.assertIn("baseline", blob)
            self.assertIn("missing", blob)
            self.assertFalse(spawns.exists(), blob)

    def test_run_on_main_rejects_a_sha_that_is_not_on_main(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            spawns = root / "spawns"
            fake_git = root / "git"
            fake_git.write_text(
                "#!/bin/sh\n"
                "if [ \"$1\" = rev-parse ]; then\n"
                "  echo aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
                "  exit 0\n"
                "fi\n"
                "exit 1\n",
                encoding="utf-8",
            )
            fake_git.chmod(fake_git.stat().st_mode | stat.S_IEXEC)
            fake = root / "llama-server"
            fake.write_text(
                "#!/bin/sh\nprintf x >> \"$PFY_NGRAM_SPAWNS\"\nprintf 'ok\\n'\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
            model = root / "m.gguf"
            model.write_bytes(b"gguf")
            env = os.environ.copy()
            env["PATH"] = str(root) + os.pathsep + env.get("PATH", "")
            env.update(
                {
                    "PFY_LLAMA_NGRAM_MODEL": str(model),
                    "PFY_LLAMA_NGRAM_FAKE_SERVER": str(fake),
                    "PFY_NGRAM_SPAWNS": str(spawns),
                    "PFY_LLAMA_NGRAM_LOCK_DIR": str(root / "lock"),
                }
            )
            proc = subprocess.run(
                ["sh", str(WRAPPER), str(root / "receipt.json")],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
            )
            blob = (proc.stdout + proc.stderr).lower()
            self.assertNotEqual(proc.returncode, 0, blob)
            self.assertTrue("ancestor" in blob or "origin/main" in blob, blob)
            self.assertFalse(spawns.exists(), blob)


if __name__ == "__main__":
    unittest.main()
