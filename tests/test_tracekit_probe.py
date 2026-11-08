#!/usr/bin/env python3
"""Drive probe.py --score. No network, no signer, no tracekit binary.

A flag on an allow must not count as a block. An ask must.
A missing score file fails. The same file present recovers.
An unsigned JSON row with a deny rewritten as allow still passes.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "tracekit" / "probe.py"


def rows(pip_decision: str) -> dict:
    loads = [
        ("load-clone", "allow", ["TK-F012"]),
        ("load-cp", "allow", []),
        ("load-write", "allow", []),
        ("load-bash", "allow", []),
        ("load-pip-name", pip_decision, ["TK-F004"]),
        ("load-npm", "allow", []),
    ]
    body = [
        {"id": name, "bucket": "h2_load", "decision": decision, "rules": rules}
        for name, decision, rules in loads
    ]
    body.append({"id": "overlap-sudo", "bucket": "overlap", "decision": "deny", "rules": ["TK-D001"]})
    return {"rows": body}


def run_score(path: Path, env: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(PROBE), "--score", str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


class TracekitScoreTests(unittest.TestCase):
    def test_flag_is_not_a_block_and_ask_is(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tk-score-") as tmp:
            work = Path(tmp)
            stub = work / "tracekit"
            stub.write_text("#!/bin/sh\necho STUB >&2\nexit 9\n", encoding="utf-8")
            stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
            env = os.environ.copy()
            env["PATH"] = str(work) + os.pathsep + env.get("PATH", "")
            allow_path = work / "allow.json"
            allow_path.write_text(json.dumps(rows("allow")), encoding="utf-8")
            allow = run_score(allow_path, env)
            self.assertEqual(allow.returncode, 0, allow.stdout + allow.stderr)
            self.assertNotIn("STUB", allow.stderr)
            self.assertIn("h2_blocked=0/6", allow.stdout.splitlines())
            self.assertIn("json_original=1", allow.stdout.splitlines())
            self.assertIn("json_edited=1", allow.stdout.splitlines())
            self.assertIn("json_caught=0", allow.stdout.splitlines())
            self.assertIn("bad_id_accepts=0", allow.stdout.splitlines())

            ask_path = work / "ask.json"
            ask_path.write_text(json.dumps(rows("ask")), encoding="utf-8")
            ask = run_score(ask_path, env)
            self.assertEqual(ask.returncode, 0, ask.stdout + ask.stderr)
            self.assertIn("h2_blocked=1/6", ask.stdout.splitlines())

    def test_missing_score_file_fails_and_present_file_recovers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="tk-score-") as tmp:
            work = Path(tmp)
            missing = run_score(work / "absent.json", os.environ.copy())
            self.assertEqual(missing.returncode, 2, missing.stdout + missing.stderr)
            self.assertIn("score file missing", missing.stderr)
            present_path = work / "present.json"
            present_path.write_text(json.dumps(rows("allow")), encoding="utf-8")
            present = run_score(present_path, os.environ.copy())
            self.assertEqual(present.returncode, 0, present.stdout + present.stderr)
            self.assertIn("h2_blocked=0/6", present.stdout.splitlines())


if __name__ == "__main__":
    unittest.main()
