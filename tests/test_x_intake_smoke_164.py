"""Entry 164 smoke (reasonix): a missing fetcher exits 2, a hang and a grandchild are killed,
matching release metadata exits 2 because the tool is not launched, and a bad asset fails."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples/x-intake-local/smoke_164.py"
PIN = {
    "tag": 'studio-v2.57.0',
    "commit": '737a181c49367a7a153c71889c168638fcfc0ba3',
    "assets": [{
        "name": 'reasonix-linux-amd64.tar.gz',
        "size": 40362566,
        "digest": "sha256:c227bbc08c65af27dbcc49aae84e115a912123a3e2b7902a6668acda75fb948f",
    }],
}

STUB = r'''
import json, os, sys, time
if K.get("orphan"):
    if os.fork() == 0:
        time.sleep(30)
        os._exit(0)
    os._exit(0)
if K.get("hang"):
    time.sleep(60)
payload = json.loads(json.dumps(K["payload"]))
if K.get("size") is not None:
    payload["assets"][0]["size"] = K["size"]
print(json.dumps(payload))
'''


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


class Smoke164(unittest.TestCase):
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
                stub_path.write_text(f"#!{sys.executable}\nK = {k!r}\n" + STUB, encoding="utf-8")
                stub_path.chmod(0o755)
                env2["REASONIX_FETCH_BIN"] = str(stub_path)
            else:
                env2["REASONIX_FETCH_BIN"] = str(td / "missing")
            env2.update(env or {})
            proc = subprocess.run(
                [sys.executable, str(SCRIPT)], env=env2, capture_output=True, text=True, timeout=60,
            )
            receipt = json.loads((td / "r" / "reasonix" / "latest.json").read_text())
            survivors = survivors_of(str(stub_path))
            self.assertEqual(survivors, [], "reasonix fetcher outlived the smoke")
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

    def test_matching_metadata_does_not_launch(self):
        code, rec = self.run_smoke({})
        self.assertEqual(code, 2, rec)
        self.assertIn("was not", rec["reason"])
        self.assertEqual(rec["verdict"], "FAIL_CANNOT_RUN_HERE")

    def test_wrong_size_fails(self):
        code, rec = self.run_smoke({"size": 10})
        self.assertEqual(code, 1, rec)
        self.assertIn("asset_pin", rec["failed"])

    def test_bad_timeout_exits_2(self):
        self.assertEqual(self.run_smoke({}, {"PFY_XINTAKE_TIMEOUT": "nope"})[0], 2)

    def test_receipt_dir_is_gitignored(self):
        proc = subprocess.run(
            ["git", "check-ignore", "-q", "pipelines/smoke/reasonix/latest.json"],
            cwd=ROOT,
        )
        self.assertEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
