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
FAKE_OK = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, os, sys
    from pathlib import Path
    Path(os.environ["SANDLOCK_LOG"]).open("a").write(json.dumps(sys.argv[1:]) + "\\n")
    os.execvp(sys.argv[1], sys.argv[1:])
    """
)
FAKE_BAD = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import sys
    raise SystemExit(1)
    """
)


class SandlockFlagTest(unittest.TestCase):
    def _run(self, td, mode, action, binary):
        log = td / "sandlock.log"
        counter = td / (action + ".count")
        counter.write_text("0")
        cache = td / ("cache-" + action + "-" + (mode or "default"))
        # The missing-binary install reuses the first install's cache directory.
        cache.mkdir(exist_ok=True)
        payload = (
            "import os; from pathlib import Path; "
            "p=Path(os.environ['COUNTER']); "
            "p.write_text(str(int(p.read_text())+1))"
        )
        env = os.environ.copy()
        env.pop("PFY_SANDLOCK", None)
        if mode is not None:
            env["PFY_SANDLOCK"] = mode
        if binary is not None:
            env["SANDLOCK_BIN"] = str(binary)
        else:
            env.pop("SANDLOCK_BIN", None)
        env["SANDLOCK_LOG"] = str(log)
        env["COUNTER"] = str(counter)
        proc = subprocess.run(
            [sys.executable, str(WRAP), "--cache", str(cache), "--action", action, "--", sys.executable, "-c", payload],
            env=env,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        return proc, counter.read_text(), log.read_text() if log.exists() else ""

    def test_auto_install_run_and_missing_binary(self):
        self.assertTrue(WRAP.is_file(), "wrap.py is missing")
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            ok = td / "sandlock-ok"
            ok.write_text(FAKE_OK)
            ok.chmod(ok.stat().st_mode | stat.S_IEXEC)
            install, count, log = self._run(td, None, "install", ok)
            self.assertEqual(install.returncode, 0, install.stderr)
            self.assertEqual(count, "1")
            rows = [json.loads(row) for row in log.splitlines() if row.strip()]
            self.assertTrue(any(row != ["true"] for row in rows))
            run, run_count, run_log = self._run(td, None, "run", ok)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run_count, "1")
            run_rows = [json.loads(row) for row in run_log.splitlines() if row.strip()]
            self.assertFalse(any(row != ["true"] for row in run_rows))
            missing, missing_count, _missing_log = self._run(td, None, "install", None)
            self.assertEqual(missing.returncode, 0, missing.stderr)
            self.assertEqual(missing_count, "1")
            self.assertIn("sandlock: unsandboxed", missing.stderr)


if __name__ == "__main__":
    unittest.main()
