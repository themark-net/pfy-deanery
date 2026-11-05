"""A relative PFY_SMOKE_RECEIPT_DIR must not write a typed-decisions receipt.

examples/typed-decisions-local/smoke.py write() always uses
pipelines/smoke/<entry>/latest.json. A relative override would resolve
against the cwd. write() must refuse that value, write nothing, and
return 1. An absolute directory still writes <entry>/latest.json there
and returns the given code. Unset or empty still writes the default path.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "pipelines" / "smoke" / "laya"


def _write():
    path = ROOT / "examples" / "typed-decisions-local" / "smoke.py"
    spec = importlib.util.spec_from_file_location("typed_receipt_abs", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module.write


class TypedDecisionsReceiptAbsoluteTests(unittest.TestCase):
    def test_relative_is_refused_and_absolute_still_writes(self) -> None:
        write = _write()
        scratch = ROOT / "tmp" / "selfhost2-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        had_default = DEFAULT.exists()
        prev = os.environ.get("PFY_SMOKE_RECEIPT_DIR")
        old = os.getcwd()
        try:
            with tempfile.TemporaryDirectory(prefix="typed-receipt-", dir=scratch) as td:
                root = Path(td)
                work = root / "work"
                work.mkdir()
                os.chdir(work)
                os.environ["PFY_SMOKE_RECEIPT_DIR"] = "receipts"
                buf = io.StringIO()
                with redirect_stdout(buf):
                    code = write("laya", {"reason": "relative"}, 0)
                self.assertEqual(code, 1, buf.getvalue())
                self.assertIn("absolute", buf.getvalue().lower())
                self.assertFalse((work / "receipts").exists(), buf.getvalue())
                self.assertFalse(DEFAULT.exists())

                dest = root / "abs"
                os.environ["PFY_SMOKE_RECEIPT_DIR"] = str(dest)
                with redirect_stdout(io.StringIO()):
                    code = write("laya", {"reason": "no-venv"}, 2)
                self.assertEqual(code, 2)
                got = json.loads((dest / "laya" / "latest.json").read_text(encoding="utf-8"))
                self.assertEqual(got.get("verdict"), "FAIL_CANNOT_RUN_HERE")
                self.assertEqual(got.get("exit_code"), 2)
                self.assertEqual(got.get("reason"), "no-venv")
                self.assertFalse(DEFAULT.exists())

                os.environ.pop("PFY_SMOKE_RECEIPT_DIR", None)
                with redirect_stdout(io.StringIO()):
                    code = write("laya", {"reason": "unset"}, 1)
                self.assertEqual(code, 1)
                got = json.loads((DEFAULT / "latest.json").read_text(encoding="utf-8"))
                self.assertEqual(got.get("verdict"), "FAIL")
                self.assertEqual(got.get("reason"), "unset")

                os.environ["PFY_SMOKE_RECEIPT_DIR"] = ""
                with redirect_stdout(io.StringIO()):
                    code = write("laya", {"reason": "empty"}, 0)
                self.assertEqual(code, 0)
                got = json.loads((DEFAULT / "latest.json").read_text(encoding="utf-8"))
                self.assertEqual(got.get("verdict"), "PASS")
                self.assertEqual(got.get("reason"), "empty")
        finally:
            os.chdir(old)
            if not had_default and DEFAULT.exists():
                shutil.rmtree(DEFAULT)
            if prev is None:
                os.environ.pop("PFY_SMOKE_RECEIPT_DIR", None)
            else:
                os.environ["PFY_SMOKE_RECEIPT_DIR"] = prev


if __name__ == "__main__":
    unittest.main()
