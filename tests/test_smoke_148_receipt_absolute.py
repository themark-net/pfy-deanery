"""A relative PFY_SMOKE_RECEIPT_DIR must not write a skillspector receipt.

smoke_148.finish writes latest.json under that directory. A relative value
can clobber a receipt in the cwd. finish refuses it, writes nothing, and
returns 1. An absolute directory still writes latest.json and returns the
given code.
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


def _finish():
    path = ROOT / "examples" / "x-intake-local" / "smoke_148.py"
    spec = importlib.util.spec_from_file_location("xintake_smoke_148_receipt", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module.finish


class Smoke148ReceiptAbsoluteTests(unittest.TestCase):
    def test_relative_dir_is_refused_and_absolute_still_writes(self) -> None:
        finish = _finish()
        scratch = ROOT / "tmp" / "selfhost-1031-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        prev = os.environ.get("PFY_SMOKE_RECEIPT_DIR")
        old = os.getcwd()
        repo_receipt = ROOT / "pipelines" / "smoke" / "skillspector" / "latest.json"
        before_repo = repo_receipt.read_bytes() if repo_receipt.exists() else None
        try:
            with tempfile.TemporaryDirectory(prefix="receipt-148-", dir=scratch) as td:
                root = Path(td)
                work = root / "work"
                work.mkdir()
                os.chdir(work)
                os.environ["PFY_SMOKE_RECEIPT_DIR"] = "receipts"
                buf = io.StringIO()
                with redirect_stdout(buf):
                    code = finish(2, {"reason": "relative"})
                self.assertEqual(code, 1, buf.getvalue())
                self.assertFalse((work / "receipts").exists(), buf.getvalue())
                self.assertIn("absolute", buf.getvalue().lower())
                after_repo = repo_receipt.read_bytes() if repo_receipt.exists() else None
                self.assertEqual(after_repo, before_repo)

                dest = root / "abs"
                os.environ["PFY_SMOKE_RECEIPT_DIR"] = str(dest)
                with redirect_stdout(io.StringIO()):
                    code = finish(2, {"reason": "staged"})
                self.assertEqual(code, 2)
                got = json.loads((dest / "latest.json").read_text(encoding="utf-8"))
                self.assertEqual(got.get("exit"), 2)
                self.assertEqual(got.get("status"), "SKIP")
                self.assertEqual(got.get("reason"), "staged")
        finally:
            os.chdir(old)
            if prev is None:
                os.environ.pop("PFY_SMOKE_RECEIPT_DIR", None)
            else:
                os.environ["PFY_SMOKE_RECEIPT_DIR"] = prev


if __name__ == "__main__":
    unittest.main()
