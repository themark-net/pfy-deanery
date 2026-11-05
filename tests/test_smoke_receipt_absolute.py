"""A relative PFY_SMOKE_RECEIPT_DIR must not write a receipt.

The variable exists so tests can keep latest.json out of the repo. A relative
value is resolved against the process cwd and can clobber a real smoke receipt.
write() refuses that value, writes nothing, and returns 1. An absolute
directory still writes the receipt and returns the given code.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _write():
    path = ROOT / "examples" / "x-intake-local" / "smoke.py"
    spec = importlib.util.spec_from_file_location("xintake_smoke_receipt_abs", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module.write


class SmokeReceiptAbsoluteTests(unittest.TestCase):
    def test_relative_dir_is_refused_and_absolute_still_writes(self) -> None:
        write = _write()
        scratch = ROOT / "tmp" / "selfhost-1031-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        prev = os.environ.get("PFY_SMOKE_RECEIPT_DIR")
        old = os.getcwd()
        try:
            with tempfile.TemporaryDirectory(prefix="receipt-abs-", dir=scratch) as td:
                root = Path(td)
                work = root / "work"
                work.mkdir()
                os.chdir(work)
                os.environ["PFY_SMOKE_RECEIPT_DIR"] = "receipts"
                buf = io.StringIO()
                with redirect_stdout(buf):
                    code = write("demoentry", {"reason": "relative"}, 0)
                self.assertEqual(code, 1, buf.getvalue())
                self.assertFalse((work / "receipts").exists(), buf.getvalue())
                self.assertFalse((ROOT / "pipelines" / "smoke" / "demoentry").exists())
                self.assertIn("absolute", buf.getvalue().lower())

                dest = root / "abs"
                os.environ["PFY_SMOKE_RECEIPT_DIR"] = str(dest)
                with redirect_stdout(io.StringIO()):
                    code = write("demoentry", {"reason": "ok"}, 0)
                self.assertEqual(code, 0)
                got = json.loads((dest / "demoentry" / "latest.json").read_text(encoding="utf-8"))
                self.assertEqual(got.get("verdict"), "PASS")
                self.assertEqual(got.get("exit_code"), 0)
                self.assertEqual(got.get("reason"), "ok")
        finally:
            os.chdir(old)
            if prev is None:
                os.environ.pop("PFY_SMOKE_RECEIPT_DIR", None)
            else:
                os.environ["PFY_SMOKE_RECEIPT_DIR"] = prev


if __name__ == "__main__":
    unittest.main()
