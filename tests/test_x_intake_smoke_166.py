"""Entry 166 smoke (odai): a missing fetcher exits 2, a hang and a grandchild are killed,
matching commit metadata exits 2 because the tool is not installed, and a bad sha fails."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples/x-intake-local/smoke_166.py"
PIN = {
    "sha": 'ce7a999843ca42ecd84778561cb0ac7642c5648e',
    "match": True,
    "message": "pinned",
}

STUB = r"""
import json, os, sys, time
if K.get("orphan"):
    if os.fork() == 0:
        time.sleep(30)
        os._exit(0)
    os._exit(0)
if K.get("hang"):
    time.sleep(60)
payload = json.loads(json.dumps(K["payload"]))
if K.get("sha") is not None:
    payload["sha"] = K["sha"]
print(json.dumps(payload))
"""


def survivors_of(path: str) -> list[int]:
    found = []
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            argv = (entry / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        if path.encode() in argv:
            found.append(int(entry.name))
            try:
                os.kill(int(entry.name), 9)
            except OSError:
                pass
    return found


class Smoke166(unittest.TestCase):
    def run_smoke(self, knobs=None, env=None):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            real = td / "realhome"
            real.mkdir()
            env2 = {
                "PATH": os.environ.get("PATH", ""),
                "HOME": str(real),
                "PFY_SMOKE_RECEIPT_DIR": str(td / "r"),
            }
            stub_path = td / "fetch"
            if knobs is not None:
                k = dict(knobs)
                k.setdefault("payload", PIN)
                stub_path.write_text("#!" + sys.executable + "\nK = " + repr(k) + "\n" + STUB, encoding="utf-8")
                stub_path.chmod(0o755)
                env2["ODAI_FETCH_BIN"] = str(stub_path)
            else:
                env2["ODAI_FETCH_BIN"] = str(td / "missing")
            env2.update(env or {})
            proc = subprocess.run(
                [sys.executable, str(SCRIPT)], env=env2, capture_output=True, text=True, timeout=60,
            )
            receipt_path = td / "r" / 'odai' / "latest.json"
            if not receipt_path.exists():
                self.fail("smoke wrote no receipt: rc=%s out=%r err=%r" % (proc.returncode, proc.stdout, proc.stderr))
            receipt = json.loads(receipt_path.read_text())
            survivors = survivors_of(str(stub_path))
            self.assertEqual(survivors, [], "odai fetcher outlived the smoke")
            return proc.returncode, receipt

    def test_missing_fetcher_exits_2(self):
        code, rec = self.run_smoke(None)
        self.assertEqual(code, 2)
        self.assertIn("not executable", rec["reason"])

    def test_hang_is_killed(self):
        code, rec = self.run_smoke({"hang": True}, {"PFY_XINTAKE_TIMEOUT": "2"})
        self.assertEqual(code, 2, rec)
        self.assertIn("timeout after 2s", rec["reason"])

    def test_grandchild_does_not_survive(self):
        code, _rec = self.run_smoke({"orphan": True}, {"PFY_XINTAKE_TIMEOUT": "5"})
        self.assertEqual(code, 2)

    def test_match_exits_2_catalog_only(self):
        code, rec = self.run_smoke({})
        self.assertEqual(code, 2, rec)
        self.assertIn("not installed", rec["reason"])

    def test_bad_sha_exits_1(self):
        code, rec = self.run_smoke({"sha": "0" * 40})
        self.assertEqual(code, 1, rec)
        self.assertIn("mismatch", rec["reason"])

    def test_bad_timeout_exits_2(self):
        code, rec = self.run_smoke({}, {"PFY_XINTAKE_TIMEOUT": "nope"})
        self.assertEqual(code, 2)
        self.assertIn("PFY_XINTAKE_TIMEOUT", rec["reason"])

    def test_fetch_error_payload_exits_2(self):
        code, rec = self.run_smoke({"payload": {"error": "boom", "sha": ""}})
        self.assertEqual(code, 2, rec)
        self.assertIn("error", rec["reason"])


if __name__ == "__main__":
    unittest.main()
