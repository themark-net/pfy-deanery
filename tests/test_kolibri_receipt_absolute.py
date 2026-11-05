"""A relative PFY_SMOKE_RECEIPT_DIR must not write the Kolibri receipt.

examples/kolibri1-llamacpp/smoke.py always writes pipelines/smoke/kolibri1/latest.json.
That file is tracked. A relative override is resolved against the cwd and can
clobber it. write() must refuse a relative value, write nothing, and return 1.
An absolute directory still writes latest.json and returns the given code.
Unset or empty still writes the tracked path.
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
TRACKED = ROOT / "pipelines" / "smoke" / "kolibri1" / "latest.json"


def _write():
    path = ROOT / "examples" / "kolibri1-llamacpp" / "smoke.py"
    spec = importlib.util.spec_from_file_location("kolibri_receipt_abs", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module.write


class KolibriReceiptAbsoluteTests(unittest.TestCase):
    def test_relative_is_refused_and_absolute_still_writes(self) -> None:
        write = _write()
        scratch = ROOT / "tmp" / "selfhost2-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        original = TRACKED.read_bytes()
        prev = os.environ.get("PFY_SMOKE_RECEIPT_DIR")
        old = os.getcwd()
        try:
            with tempfile.TemporaryDirectory(prefix="kolibri-receipt-", dir=scratch) as td:
                root = Path(td)
                work = root / "work"
                work.mkdir()
                os.chdir(work)
                os.environ["PFY_SMOKE_RECEIPT_DIR"] = "receipts"
                buf = io.StringIO()
                with redirect_stdout(buf):
                    code = write({"reason": "relative"}, 0)
                self.assertEqual(code, 1, buf.getvalue())
                self.assertIn("absolute", buf.getvalue().lower())
                self.assertFalse((work / "receipts").exists(), buf.getvalue())
                self.assertEqual(TRACKED.read_bytes(), original)

                dest = root / "abs"
                os.environ["PFY_SMOKE_RECEIPT_DIR"] = str(dest)
                with redirect_stdout(io.StringIO()):
                    code = write({"reason": "no-backend"}, 2)
                self.assertEqual(code, 2)
                got = json.loads((dest / "latest.json").read_text(encoding="utf-8"))
                self.assertEqual(got.get("verdict"), "FAIL_NO_BACKEND")
                self.assertEqual(got.get("exit_code"), 2)
                self.assertEqual(got.get("reason"), "no-backend")
                self.assertEqual(TRACKED.read_bytes(), original)

                os.environ.pop("PFY_SMOKE_RECEIPT_DIR", None)
                with redirect_stdout(io.StringIO()):
                    code = write({"reason": "unset"}, 1)
                self.assertEqual(code, 1)
                got = json.loads(TRACKED.read_text(encoding="utf-8"))
                self.assertEqual(got.get("verdict"), "FAIL")
                self.assertEqual(got.get("reason"), "unset")

                os.environ["PFY_SMOKE_RECEIPT_DIR"] = ""
                with redirect_stdout(io.StringIO()):
                    code = write({"reason": "empty"}, 0)
                self.assertEqual(code, 0)
                got = json.loads(TRACKED.read_text(encoding="utf-8"))
                self.assertEqual(got.get("verdict"), "PASS")
                self.assertEqual(got.get("reason"), "empty")
        finally:
            os.chdir(old)
            TRACKED.write_bytes(original)
            if prev is None:
                os.environ.pop("PFY_SMOKE_RECEIPT_DIR", None)
            else:
                os.environ["PFY_SMOKE_RECEIPT_DIR"] = prev


if __name__ == "__main__":
    unittest.main()
