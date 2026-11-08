#!/usr/bin/env python3
"""Drive the sponsio probe with stub runners. No network and no wheel.

A runner that allows a known-bad call must not exit 0. A runner that
returns the labeled decisions must. A dead runner must not look like a pass.
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
PROBE = ROOT / "eval" / "evq1107" / "sponsio" / "probe.py"


STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json
    import sys

    job = json.loads(open(sys.argv[1], encoding="utf-8").read())
    mode = sys.argv[2]
    cases = []
    for case in job["cases"]:
        count = len(case["steps"])
        if mode == "leak":
            allowed = [True] * count
        elif mode == "match":
            allowed = list(case["expect"])
        else:
            sys.stderr.write("unknown mode\\n")
            sys.exit(3)
        cases.append({
            "id": case["id"],
            "allowed": allowed,
            "actions": [[] for _ in allowed],
            "us": [1.0] * count,
        })
    print("PFY_JSON " + json.dumps({
        "version": "stub",
        "armed": {},
        "cases": cases,
        "warm_ls_us": [1.0],
    }))
    """
)


class SponsioProbeTest(unittest.TestCase):
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
                "SPONSIO_CACHE": str(out_path.parent),
            },
        )

    def test_leaking_runner_fails_and_a_matching_runner_recovers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="sponsio-probe-test-") as tmp:
            folder = Path(tmp)
            (folder / "tmp").mkdir()
            stub = folder / "stub.py"
            stub.write_text(STUB)
            stub.chmod(0o755)
            leak = folder / "leak.sh"
            match = folder / "match.sh"
            leak.write_text("#!/bin/sh\nexec python3 \"%s\" \"$1\" leak\n" % stub)
            match.write_text("#!/bin/sh\nexec python3 \"%s\" \"$1\" match\n" % stub)
            leak.chmod(0o755)
            match.chmod(0o755)

            dead_out = folder / "dead.json"
            dead = self._run(str(folder / "missing-runner"), dead_out)
            self.assertEqual(dead.returncode, 2, dead.stderr)
            self.assertFalse(dead_out.exists())

            leak_out = folder / "leak.json"
            leaked = self._run(str(leak), leak_out)
            self.assertEqual(leaked.returncode, 1, leaked.stdout + leaked.stderr)
            self.assertIn("sh-curl-bash", leaked.stdout)
            body = json.loads(leak_out.read_text())
            curl = next(row for row in body["cases"] if row["id"] == "sh-curl-bash")
            self.assertEqual(curl["allowed"], [True])
            self.assertFalse(curl["match"])
            self.assertGreater(len(body["mismatches"]), 0)

            match_out = folder / "match.json"
            restored = self._run(str(match), match_out)
            self.assertEqual(restored.returncode, 0, restored.stdout + restored.stderr)
            self.assertIn("OK shell_bad", restored.stdout)
            restored_body = json.loads(match_out.read_text())
            self.assertEqual(restored_body["mismatches"], [])
            self.assertTrue(all(row["match"] for row in restored_body["cases"]))
            order = restored_body["summary"]["order_premature_blocked"]
            self.assertEqual(order, {"hit": 2, "n": 2})
            args_only = restored_body["summary"]["args_only_order_premature_blocked"]
            self.assertEqual(args_only, {"hit": 0, "n": 2})


if __name__ == "__main__":
    unittest.main()
