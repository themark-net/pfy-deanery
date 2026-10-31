"""Behavior tests for preflight and receipt checks the baseline suite left open.

Each test passes on the current source and fails if the matching mutant is
applied. P9 (``rc == 0 or rc == 0.0``) is not here: that clause cannot
change a real exit code, so no test can kill it.

How this fails and how it recovers:

- A negative exit that names a quota or a login failure must not be classed
  as other. Recovery: only an exact zero exit skips the phrase rules.
- Extra spaces must not invent a phrase. Recovery: match the substring as
  written. The existing phrase tests still cover the real spellings.
- A PASS-shaped receipt with a bad status, reason, exit code, gate command,
  pushed value, attempt list, or branch prefix must be rejected. Recovery:
  exit 1 and one stderr reason line. A truncated file and a missing file
  take the same path.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib.build_preflight import classify_cloud_failure  # noqa: E402

CHECKER = ROOT / "eval" / "mvp-1031" / "check_receipt.py"
SCRATCH = ROOT / "tmp" / "mutation-1031" / "preflight" / "survivor-tests"


def _pass_receipt() -> dict:
    return {
        "schema": "pfy-cloud-build/1",
        "status": "PASS",
        "reason": "ok",
        "exit_code": 0,
        "branch": "cloud/add-sum-20261031",
        "commit": "a" * 40,
        "review": {"verdict": "accept"},
        "attempts": [{"status": "PASS"}],
        "pushed": False,
        "gate": {"cmd": "python3 -m unittest test_add"},
    }


class ClassifierGapTests(unittest.TestCase):
    def test_negative_rc_still_classifies_quota_and_auth(self) -> None:
        # Fail: rc <= 0 would treat a signaled grok as a clean exit and skip recovery.
        # Recover: only rc == 0 is other. A negative code still selects the phrase class.
        self.assertEqual(classify_cloud_failure(-1, "rate limit", ""), "rate-limit")
        self.assertEqual(classify_cloud_failure(-1, "", "not logged in"), "unauthenticated")

    def test_double_spaced_phrases_stay_other(self) -> None:
        # Fail: collapsing repeated spaces would block a log that only looks similar.
        # Recover: "rate limit" and "not logged in" must appear as those substrings.
        self.assertEqual(classify_cloud_failure(1, "rate  limit", ""), "other")
        self.assertEqual(classify_cloud_failure(1, "", "not  logged in"), "other")


class ReceiptGapTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.work = Path(tempfile.mkdtemp(prefix="gap-", dir=SCRATCH))

    def tearDown(self) -> None:
        for child in self.work.iterdir():
            child.unlink()
        self.work.rmdir()

    def _check(self, raw: str) -> subprocess.CompletedProcess[str]:
        path = self.work / "receipt.json"
        path.write_text(raw, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(CHECKER), str(path)],
            capture_output=True,
            text=True,
        )

    def _reject(self, body: dict, reason: str) -> None:
        proc = self._check(json.dumps(body))
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertEqual(proc.stdout, "")
        self.assertEqual(proc.stderr.strip(), reason)
        self.assertEqual(proc.stderr.count("\n"), 1)

    def test_status_other_than_pass_is_rejected(self) -> None:
        # Fail: status FAIL with every other PASS field would be archived as success.
        # Recover: exit 1 and name status. The operator keeps the failed run off the demo path.
        body = _pass_receipt()
        body["status"] = "FAIL"
        self._reject(body, "rejected: status is not PASS")

    def test_reason_other_than_ok_is_rejected(self) -> None:
        # Fail: reason gate-failed would still look like a PASS receipt.
        # Recover: exit 1 and name reason. A later retry can replace the receipt.
        body = _pass_receipt()
        body["reason"] = "gate-failed"
        self._reject(body, "rejected: reason is not ok")

    def test_nonzero_and_boolean_exit_codes_are_rejected(self) -> None:
        # Fail: exit_code 1, or JSON false, would count as a zero exit.
        # Recover: the value must be the integer 0. Bool is not that integer.
        for value in (1, False):
            body = _pass_receipt()
            body["exit_code"] = value
            self._reject(body, "rejected: exit_code is not 0")

    def test_empty_gate_cmd_is_rejected(self) -> None:
        # Fail: an empty gate command would record a PASS that ran no test.
        # Recover: exit 1 and name gate.cmd. The demo command has to be non-empty.
        body = _pass_receipt()
        body["gate"] = {"cmd": ""}
        self._reject(body, "rejected: gate.cmd is empty")

    def test_truncated_json_is_rejected(self) -> None:
        # Fail: a cut-off receipt would be accepted, or the checker would traceback.
        # Recover: exit 1 with the json reason and no traceback on either stream.
        proc = self._check("{")
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertEqual(proc.stdout, "")
        self.assertEqual(proc.stderr.strip(), "rejected: receipt is not json")
        self.assertNotIn("Traceback", proc.stderr)

    def test_pushed_zero_is_rejected(self) -> None:
        # Fail: JSON 0 is not false. Treating it as not-pushed would hide a bad flag.
        # Recover: only boolean false passes. The operator does not push a PASS.
        body = _pass_receipt()
        body["pushed"] = 0
        self._reject(body, "rejected: pushed is not false")

    def test_attempts_string_is_rejected(self) -> None:
        # Fail: a truthy string would count as a non-empty attempt list.
        # Recover: attempts must be a non-empty list. Exit 1 names that field.
        body = _pass_receipt()
        body["attempts"] = "done"
        self._reject(body, "rejected: attempts is empty")

    def test_branch_without_the_cloud_slash_is_rejected(self) -> None:
        # Fail: "cloud" or "cloudy" would count as a cloud/ branch.
        # Recover: the prefix is cloud plus a slash. Exit 1 names the branch field.
        for branch in ("cloud", "cloudy"):
            body = _pass_receipt()
            body["branch"] = branch
            self._reject(body, "rejected: branch does not start with cloud/")

    def test_missing_receipt_file_is_rejected(self) -> None:
        # Fail: a missing path that exits 0 would let the demo checker pass with no receipt.
        # Recover: exit 1 and say the file is missing. Do not create the path.
        missing = self.work / "missing.json"
        proc = subprocess.run(
            [sys.executable, str(CHECKER), str(missing)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertEqual(proc.stdout, "")
        self.assertEqual(proc.stderr.strip(), "rejected: receipt file is missing")
        self.assertFalse(missing.exists())
