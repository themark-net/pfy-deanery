#!/usr/bin/env python3
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "scripts" / "integrations" / "llama_ngram" / "run.py"


class TestLlamaNgramMismatchFallback(unittest.TestCase):
    def test_mismatch_falls_back_and_stops_own_server(self):
        self.assertTrue(RUN.is_file(), "run.py missing")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pidfile = root / "server.pid"
            fake = root / "llama-server"
            fake.write_text(
                "#!/bin/sh\necho $$ > \"$PFY_NGRAM_PIDFILE\"\n"
                "printf 'NOT-BASELINE\\n'\n"
                "while true; do sleep 1; done\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
            model = root / "m.gguf"
            model.write_bytes(b"gguf")
            env = os.environ.copy()
            env.update(
                {
                    "PFY_LLAMA_NGRAM": "1",
                    "PFY_LLAMA_NGRAM_MODEL": str(model),
                    "PFY_LLAMA_NGRAM_FAKE_SERVER": str(fake),
                    "PFY_NGRAM_PIDFILE": str(pidfile),
                    "PFY_LLAMA_NGRAM_BASELINE_TEXT": "BASELINE",
                    "PFY_LLAMA_NGRAM_LOCK_DIR": str(root / "lock"),
                }
            )
            proc = subprocess.run(
                [sys.executable, str(RUN)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            blob = (proc.stdout + proc.stderr).lower()
            self.assertIn("baseline", blob)
            self.assertIn("mismatch", blob)
            self.assertTrue(pidfile.is_file(), blob)
            pid = int(pidfile.read_text(encoding="utf-8").strip())
            time.sleep(0.2)
            alive = True
            try:
                os.kill(pid, 0)
            except OSError:
                alive = False
            self.assertFalse(alive, "fake server pid %s still running" % pid)


if __name__ == "__main__":
    unittest.main()
