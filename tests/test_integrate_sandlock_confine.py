"""confine.py turns a passthrough argv into sandlock check / sandlock run.

The double records argv. It does not call the real binary.
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
CONFINE = ROOT / "scripts" / "integrations" / "sandlock" / "confine.py"
REAL = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, os, sys
    from pathlib import Path
    Path(os.environ["TRACE"]).open("a").write(json.dumps(sys.argv[1:]) + "\\n")
    if len(sys.argv) < 2:
        raise SystemExit(2)
    if sys.argv[1] == "check":
        raise SystemExit(0 if os.environ.get("CHECK_FAIL") != "1" else 1)
    if sys.argv[1] == "run":
        if "--" not in sys.argv:
            raise SystemExit(2)
        cmd = sys.argv[sys.argv.index("--") + 1:]
        os.execvp(cmd[0], cmd)
    raise SystemExit(2)
    """
)


class SandlockConfineTest(unittest.TestCase):
    def test_self_test_command_and_missing_binary(self):
        self.assertTrue(CONFINE.is_file(), "confine.py is missing")
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            fake = td / "sandlock"
            fake.write_text(REAL)
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
            trace = td / "trace.log"
            env = os.environ.copy()
            env["SANDLOCK_REAL"] = str(fake)
            env["TRACE"] = str(trace)
            env.pop("CHECK_FAIL", None)

            ok = subprocess.run(
                [sys.executable, str(CONFINE), "true"],
                env=env,
                cwd=td,
                capture_output=True,
                text=True,
            )
            self.assertEqual(ok.returncode, 0, ok.stderr)
            rows = [json.loads(row) for row in trace.read_text().splitlines() if row.strip()]
            self.assertEqual(rows[0], ["check"])
            self.assertEqual(rows[1][0], "run")
            self.assertIn("--clean-env", rows[1])
            self.assertIn("--timeout", rows[1])
            self.assertIn("120", rows[1])
            self.assertIn("--", rows[1])

            trace.write_text("")
            env["CHECK_FAIL"] = "1"
            bad = subprocess.run(
                [sys.executable, str(CONFINE), "true"],
                env=env,
                cwd=td,
                capture_output=True,
                text=True,
            )
            self.assertEqual(bad.returncode, 1, bad.stderr)
            failed_rows = [json.loads(row) for row in trace.read_text().splitlines() if row.strip()]
            self.assertEqual(failed_rows, [["check"]])

            env.pop("CHECK_FAIL", None)
            trace.write_text("")
            stage = td / "stage"
            stage.mkdir()
            marker = td / "marks" / "started"
            marker.parent.mkdir()
            env["SANDLOCK_STAGE"] = str(stage)
            env["SANDLOCK_STARTED"] = str(marker)
            env["PFY_BUMBLEBEE_BIN"] = str(td / "not-the-pinned-binary")
            env["HOME"] = str(td / "caller-home")
            out = stage / "out.txt"
            payload = "from pathlib import Path; import os; Path(os.environ['OUT']).write_text('ok')"
            env["OUT"] = str(out)
            ran = subprocess.run(
                [sys.executable, str(CONFINE), sys.executable, "-c", payload],
                env=env,
                cwd=td,
                capture_output=True,
                text=True,
            )
            self.assertEqual(ran.returncode, 0, ran.stderr)
            self.assertEqual(out.read_text(encoding="utf-8"), "ok")
            command_rows = [json.loads(row) for row in trace.read_text().splitlines() if row.strip()]
            self.assertEqual(len(command_rows), 1)
            argv = command_rows[0]
            self.assertIn("--clean-env", argv)
            self.assertIn(str(stage), argv)
            joined = " ".join(argv)
            self.assertIn("SANDLOCK_STARTED=%s" % marker, joined)
            self.assertIn("SANDLOCK_STAGE=%s" % stage, joined)
            self.assertNotIn("PFY_BUMBLEBEE_BIN", joined)
            self.assertNotIn("HOME=", joined)

            missing_env = env.copy()
            missing_env["SANDLOCK_REAL"] = str(td / "no-such-sandlock")
            missing = subprocess.run(
                [sys.executable, str(CONFINE), "true"],
                env=missing_env,
                cwd=td,
                capture_output=True,
                text=True,
            )
            self.assertEqual(missing.returncode, 1, missing.stderr)


if __name__ == "__main__":
    unittest.main()
