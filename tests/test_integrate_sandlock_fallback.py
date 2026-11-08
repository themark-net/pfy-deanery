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
WRAP = ROOT / "scripts" / "integrations" / "sandlock" / "wrap.py"
FAKE = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, os, sys
    from pathlib import Path
    Path(os.environ["SANDLOCK_LOG"]).open("a").write(json.dumps(sys.argv[1:]) + "\\n")
    if os.environ.get("SANDLOCK_FAIL_BEFORE") == "1" and sys.argv[1:] != ["true"]:
        raise SystemExit(1)
    os.execvp(sys.argv[1], sys.argv[1:])
    """
)


class SandlockFallbackTest(unittest.TestCase):
    def _wrap(self, td, fail_before, code):
        fake = td / "sandlock"
        if not fake.exists():
            fake.write_text(FAKE)
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        log = td / "sandlock.log"
        counter = td / "count"
        counter.write_text("0")
        cache = td / ("cache-" + str(fail_before))
        cache.mkdir()
        payload = (
            "import os, sys; from pathlib import Path; "
            "p=Path(os.environ['COUNTER']); "
            "p.write_text(str(int(p.read_text())+1)); "
            "sys.exit(int(os.environ['EXIT_CODE']))"
        )
        env = os.environ.copy()
        env["SANDLOCK_BIN"] = str(fake)
        env["SANDLOCK_LOG"] = str(log)
        env["COUNTER"] = str(counter)
        env["EXIT_CODE"] = str(code)
        env["PFY_SANDLOCK"] = "auto"
        if fail_before:
            env["SANDLOCK_FAIL_BEFORE"] = "1"
        else:
            env.pop("SANDLOCK_FAIL_BEFORE", None)
        proc = subprocess.run(
            [sys.executable, str(WRAP), "--cache", str(cache), "--action", "install", "--", sys.executable, "-c", payload],
            env=env,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        return proc, counter.read_text(), log.read_text() if log.exists() else ""

    def test_inner_failure_does_not_retry_and_pre_exec_falls_back_once(self):
        self.assertTrue(WRAP.is_file(), "wrap.py is missing")
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            failed, count, log = self._wrap(td, False, 3)
            self.assertEqual(failed.returncode, 3, failed.stderr)
            self.assertEqual(count, "1")
            rows = [json.loads(row) for row in log.splitlines() if row.strip()]
            self.assertEqual(len([row for row in rows if row != ["true"]]), 1)
            fallback, fallback_count, _log = self._wrap(td, True, 0)
            self.assertEqual(fallback.returncode, 0, fallback.stderr)
            self.assertEqual(fallback_count, "1")
            self.assertIn("sandlock: unsandboxed", fallback.stderr)


if __name__ == "__main__":
    unittest.main()
