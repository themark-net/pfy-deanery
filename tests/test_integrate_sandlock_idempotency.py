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
    os.execvp(sys.argv[1], sys.argv[1:])
    """
)


class SandlockIdempotencyTest(unittest.TestCase):
    def test_second_same_cache_run_skips_command(self):
        self.assertTrue(WRAP.is_file(), "wrap.py is missing")
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            fake = td / "sandlock"
            fake.write_text(FAKE)
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
            log = td / "sandlock.log"
            counter = td / "count"
            counter.write_text("0")
            cache = td / "cache"
            cache.mkdir()
            payload = (
                "import os; from pathlib import Path; "
                "p=Path(os.environ['COUNTER']); "
                "p.write_text(str(int(p.read_text())+1))"
            )
            cmd = [sys.executable, "-c", payload]

            def run():
                env = os.environ.copy()
                env["SANDLOCK_BIN"] = str(fake)
                env["SANDLOCK_LOG"] = str(log)
                env["COUNTER"] = str(counter)
                env["PFY_SANDLOCK"] = "auto"
                return subprocess.run(
                    [sys.executable, str(WRAP), "--cache", str(cache), "--action", "install", "--", *cmd],
                    env=env,
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )

            first = run()
            second = run()
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(counter.read_text(), "1")
            lines = [json.loads(row) for row in log.read_text().splitlines() if row.strip()]
            user = [row for row in lines if row != ["true"]]
            self.assertEqual(len(user), 1)


if __name__ == "__main__":
    unittest.main()
