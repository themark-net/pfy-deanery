"""headson probe: budget overrun, lost row id, and invalid JSON.

The child is eval/evq1107/headson/probe.py. Each test runs that script
against a stub hson in a temp dir. No network, no model, no real binary.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "headson" / "probe.py"

FIXTURE = (
    '{"run":"t","results":[{"id":7,"verdict":"FAIL"},'
    '{"id":8,"verdict":"PASS"}],"meta":{"n":2,"note":"' + ("y" * 180) + '"}}\n'
)

STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import os, sys
    args = sys.argv[1:]
    mode = os.environ.get("STUB_MODE", "good")
    if "--version" in args or "-V" in args:
        sys.stdout.write("hson 0.17.1\\n")
        raise SystemExit(0)
    good = '{"run":"t","results":[{"id":7,"verdict":"FAIL"}],"meta":{"n":2}}\\n'
    omit = '{"run":"t","results":[{"verdict":"FAIL"}],"meta":{"n":2}}\\n'
    if mode == "bad":
        sys.stdout.write("NOT JSON\\n")
    elif mode == "over" and "--capped-grep" not in args and "--grep" in args:
        sys.stdout.write(good.strip()[:-1] + ',"pad":"' + ("x" * 400) + '"}\\n')
    elif mode == "omit" and "--head" not in args:
        sys.stdout.write(omit)
    else:
        sys.stdout.write(good)
    """
)


class HeadsonProbeTests(unittest.TestCase):
    def _run(self, mode: str, home: Path) -> dict:
        stub = home / "hson"
        stub.write_text(STUB, encoding="utf-8")
        stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
        fixture = home / "fixture.json"
        fixture.write_text(FIXTURE, encoding="utf-8")
        out = home / "out.json"
        env = os.environ.copy()
        env["HOME"] = str(home)
        env["HSON_BIN"] = str(stub)
        env["STUB_MODE"] = mode
        env["PATH"] = "/usr/bin:/bin"
        proc = subprocess.run(
            [
                sys.executable,
                str(PROBE),
                "--fixture",
                str(fixture),
                "--out",
                str(out),
                "--budget",
                "120",
                "--sentinel-id",
                "7",
                "--child-home",
                str(home / "child"),
            ],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertTrue(out.is_file(), proc.stdout)
        return json.loads(out.read_text(encoding="utf-8"))

    def test_grep_over_budget_fails_the_cap_and_default_recovers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="headson-over-") as tmp:
            doc = self._run("over", Path(tmp))
        modes = doc["documents"][0]["modes"]
        grep = modes["hson_grep"]
        self.assertTrue(grep["parse_ok"])
        self.assertTrue(grep["keys_ok"])
        self.assertFalse(grep["under_budget"])
        self.assertFalse(grep["hard_cap_pass"])
        default = modes["hson"]
        self.assertTrue(default["parse_ok"])
        self.assertTrue(default["keys_ok"])
        self.assertTrue(default["under_budget"])
        self.assertTrue(default["hard_cap_pass"])
        self.assertLessEqual(default["payload_bytes"], 120)

    def test_omitted_row_id_is_shape_only_and_head_mode_recovers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="headson-omit-") as tmp:
            doc = self._run("omit", Path(tmp))
        modes = doc["documents"][0]["modes"]
        default = modes["hson"]
        self.assertTrue(default["needle_kept"])
        self.assertFalse(default["sentinel_id_kept"])
        self.assertTrue(default["shape_only"])
        self.assertTrue(default["hard_cap_pass"])
        headed = modes["hson_head"]
        self.assertTrue(headed["sentinel_id_kept"])
        self.assertFalse(headed["shape_only"])
        self.assertTrue(headed["hard_cap_pass"])

    def test_invalid_preview_fails_the_parse_and_strict_json_recovers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="headson-bad-") as tmp:
            parent = Path(tmp)
            (parent / "bad").mkdir()
            (parent / "good").mkdir()
            bad = self._run("bad", parent / "bad")
            good = self._run("good", parent / "good")
        bad_mode = bad["documents"][0]["modes"]["hson"]
        self.assertFalse(bad_mode["parse_ok"])
        self.assertFalse(bad_mode["hard_cap_pass"])
        self.assertEqual(bad["summary"]["hson_hard_cap_pass"], 0)
        good_mode = good["documents"][0]["modes"]["hson"]
        self.assertTrue(good_mode["parse_ok"])
        self.assertTrue(good_mode["keys_ok"])
        self.assertTrue(good_mode["hard_cap_pass"])
        self.assertEqual(good["summary"]["hson_hard_cap_pass"], 1)


if __name__ == "__main__":
    unittest.main()
