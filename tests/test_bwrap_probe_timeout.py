#!/usr/bin/env python3
"""A hung bwrap must not hang the smoke probe.

Each Entry 148/149/154/155/156 bwrap_ok() used to call bwrap with no timeout.
A fake bwrap that sleeps past the probe timeout is treated as unusable.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKES = (
    "examples/x-intake-local/smoke_148.py",
    "examples/x-intake-local/smoke_149.py",
    "examples/x-intake-local/smoke_154.py",
    "examples/x-intake-local/smoke_155.py",
    "examples/x-intake-local/smoke_156.py",
)


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class BwrapProbeTimeoutTests(unittest.TestCase):
    def test_hanging_bwrap_is_not_usable_for_each_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            fake = td / "bwrap"
            fake.write_text(
                f"#!{sys.executable}\nimport time\ntime.sleep(30)\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            old = os.environ.get("PATH", "")
            os.environ["PATH"] = str(td) + ":" + old
            try:
                for rel in SMOKES:
                    with self.subTest(rel=rel):
                        mod = _load(ROOT / rel, "bwrap_probe_" + Path(rel).stem)
                        start = time.monotonic()
                        ok = mod.bwrap_ok(timeout=0.3)
                        elapsed = time.monotonic() - start
                        self.assertFalse(ok, rel)
                        self.assertLess(elapsed, 1.5, f"{rel} elapsed {elapsed:.2f}s")
            finally:
                os.environ["PATH"] = old


if __name__ == "__main__":
    unittest.main()
