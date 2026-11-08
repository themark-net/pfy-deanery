#!/usr/bin/env python3
"""Drive the moira probe with a stub runner. No network and no engine binary.

A runner that marks every claim done must not exit 0. A runner that returns
the labeled decisions must. A missing runner must not write a result file.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "moira" / "probe.py"

STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json
    import sys

    job = json.loads(open(sys.argv[1], encoding="utf-8").read())
    mode = sys.argv[2]
    cases = []
    for case in job["cases"]:
        if mode == "leak":
            valid = True
            output = "done"
        elif mode == "match":
            valid = case["expect_valid"]
            output = case["expect_output"]
        else:
            sys.stderr.write("unknown mode\\n")
            sys.exit(3)
        cases.append({"id": case["id"], "valid": valid, "output": output, "error": ""})
    print("PFY_JSON " + json.dumps({
        "engine": "stub",
        "ajv": "",
        "elapsed_us": 1,
        "cases": cases,
    }))
    """
)


class MoiraProbeTest(unittest.TestCase):
    def _run(self, runner: str, out_path: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(PROBE), "--runner", runner, "--out", str(out_path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env={
                "PATH": "/usr/bin:/bin",
                "HOME": os.environ.get("HOME", "/tmp"),
                "LANG": "C.UTF-8",
            },
        )

    def test_leaking_runner_fails_and_a_matching_runner_recovers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="moira-probe-test-") as tmp:
            folder = Path(tmp)
            stub = folder / "stub.py"
            stub.write_text(STUB)
            stub.chmod(0o755)
            leak = folder / "leak.sh"
            match = folder / "match.sh"
            leak.write_text('#!/bin/sh\nexec python3 "%s" "$1" leak\n' % stub)
            match.write_text('#!/bin/sh\nexec python3 "%s" "$1" match\n' % stub)
            leak.chmod(0o755)
            match.chmod(0o755)

            dead_out = folder / "dead.json"
            dead = self._run(str(folder / "missing-runner"), dead_out)
            self.assertEqual(dead.returncode, 2, dead.stderr)
            self.assertFalse(dead_out.exists())

            leak_out = folder / "leak.json"
            leaked = self._run(str(leak), leak_out)
            self.assertEqual(leaked.returncode, 1, leaked.stdout + leaked.stderr)
            self.assertIn("MISMATCH", leaked.stdout)
            self.assertIn("mal-empty", leaked.stdout)
            self.assertIn("honest-park", leaked.stdout)
            body = json.loads(leak_out.read_text())
            self.assertEqual(body["summary"]["lies_routed_done"], {"hit": 4, "n": 4})
            self.assertEqual(body["summary"]["malformed_rejected"], {"hit": 0, "n": 8})
            self.assertGreater(len(body["mismatches"]), 0)

            match_out = folder / "match.json"
            restored = self._run(str(match), match_out)
            self.assertEqual(restored.returncode, 0, restored.stdout + restored.stderr)
            self.assertIn("OK malformed 8/8", restored.stdout)
            restored_body = json.loads(match_out.read_text())
            self.assertEqual(restored_body["mismatches"], [])
            self.assertEqual(restored_body["summary"]["malformed_rejected"], {"hit": 8, "n": 8})
            self.assertEqual(restored_body["summary"]["lies_routed_done"], {"hit": 4, "n": 4})
            self.assertEqual(restored_body["summary"]["honest_not_done"], {"hit": 4, "n": 4})
            self.assertFalse(restored_body["summary"]["completion_string_changed"])
            self.assertEqual(restored_body["summary"]["completion_string_n"], 2)
            self.assertEqual(restored_body["summary"]["prose_done_accepted"], {"hit": 18, "n": 18})
            self.assertEqual(restored_body["summary"]["skill_input_schema_mentions"], 0)
            self.assertEqual(restored_body["summary"]["skill_exit_names_present"], 8)
            self.assertTrue(all(row["ok"] for row in restored_body["cases"]))


if __name__ == "__main__":
    unittest.main()
