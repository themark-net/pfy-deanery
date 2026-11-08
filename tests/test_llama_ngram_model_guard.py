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


class TestLlamaNgramModelGuard(unittest.TestCase):
    def test_oversize_model_falls_back_without_spawn(self):
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
            model = root / "m.gguf"
            model.write_bytes(b"0123456789abcdef")
            env = os.environ.copy()
            env.update(
                {
                    "PFY_LLAMA_NGRAM": "1",
                    "PFY_LLAMA_NGRAM_MODEL": str(model),
                    "PFY_LLAMA_NGRAM_MAX_BYTES": "8",
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
            blob = (proc.stdout + proc.stderr).lower()
            self.assertIn("baseline", blob)
            self.assertTrue("size" in blob or "25" in blob or "max" in blob, blob)
            self.assertFalse(spawns.exists(), blob)


if __name__ == "__main__":
    unittest.main()
