#!/usr/bin/env python3
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "scripts" / "integrations" / "llama_ngram" / "run.py"


class TestLlamaNgramDefaultOff(unittest.TestCase):
    def test_unset_flag_uses_baseline_and_does_not_spawn(self):
        self.assertTrue(RUN.is_file(), "run.py missing")
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
            env.pop("PFY_LLAMA_NGRAM", None)
            env.update(
                {
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
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("baseline", proc.stdout.lower())
            self.assertFalse(spawns.exists(), proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
