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
WRAPPER = ROOT / "eval" / "integrate" / "llama-cpp-ngram-mod" / "run-on-main.sh"


class TestLlamaNgramSingleFlight(unittest.TestCase):
    def test_duplicate_sha_does_not_start_server(self):
        self.assertTrue(RUN.is_file(), "run.py missing")
        self.assertTrue(WRAPPER.is_file(), "run-on-main.sh missing")
        wrapper = WRAPPER.read_text(encoding="utf-8")
        self.assertIn("scripts/model_lock.sh", wrapper)
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
            model.write_bytes(b"gguf")
            receipt = root / "receipt.json"
            original = '{"sha":"abc","tok_s":1}\n'
            receipt.write_text(original, encoding="utf-8")
            env = os.environ.copy()
            env.update(
                {
                    "PFY_LLAMA_NGRAM": "1",
                    "PFY_LLAMA_NGRAM_MODEL": str(model),
                    "PFY_LLAMA_NGRAM_FAKE_SERVER": str(fake),
                    "PFY_NGRAM_SPAWNS": str(spawns),
                    "PFY_LLAMA_NGRAM_RECEIPT": str(receipt),
                    "PFY_LLAMA_NGRAM_SHA": "abc",
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
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertFalse(spawns.exists(), proc.stdout + proc.stderr)
            self.assertEqual(receipt.read_text(encoding="utf-8"), original)
            blob = (proc.stdout + proc.stderr).lower()
            self.assertIn("receipt", blob)


if __name__ == "__main__":
    unittest.main()
