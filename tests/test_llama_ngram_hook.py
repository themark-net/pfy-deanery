#!/usr/bin/env python3
"""The model-bound hook uses ngram text only when the check matches."""
import importlib.util
import os
import stat
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "examples" / "eval-harness"


def _load():
    spec = importlib.util.spec_from_file_location(
        "run_scored_task_ngram_hook", HARNESS / "run_scored_task.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class TestLlamaNgramHook(unittest.TestCase):
    def test_matching_fake_returns_text_and_oversize_does_not_spawn(self):
        mod = _load()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            spawns = root / "spawns"
            fake = root / "llama-server"
            fake.write_text(
                "#!/bin/sh\nprintf x >> \"$PFY_NGRAM_SPAWNS\"\nprintf 'BASELINE\\n'\n",
                encoding="utf-8",
            )
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
            model = root / "m.gguf"
            model.write_bytes(b"gguf")
            saved = os.environ.copy()
            try:
                os.environ["PFY_LLAMA_NGRAM"] = "1"
                os.environ["PFY_LLAMA_NGRAM_MODEL"] = str(model)
                os.environ["PFY_LLAMA_NGRAM_FAKE_SERVER"] = str(fake)
                os.environ["PFY_LLAMA_NGRAM_BASELINE_TEXT"] = "BASELINE"
                os.environ["PFY_NGRAM_SPAWNS"] = str(spawns)
                os.environ["PFY_LLAMA_NGRAM_LOCK_DIR"] = str(root / "lock")
                os.environ.pop("PFY_LLAMA_NGRAM_RECEIPT", None)
                os.environ.pop("PFY_LLAMA_NGRAM_SHA", None)
                text = mod._llama_ngram_or_none("task prompt", 32)
                self.assertEqual(text, "BASELINE")
                self.assertTrue(spawns.is_file())
                spawns.unlink()
                os.environ["PFY_LLAMA_NGRAM_MAX_BYTES"] = "1"
                again = mod._llama_ngram_or_none("task prompt", 32)
                self.assertIsNone(again)
                self.assertFalse(spawns.exists())
            finally:
                os.environ.clear()
                os.environ.update(saved)


if __name__ == "__main__":
    unittest.main()
