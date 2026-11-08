import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRAP = ROOT / "scripts" / "integrations" / "sandlock" / "wrap.py"
FAKE = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import os, sys, time
    time.sleep(0.3)
    os.execvp(sys.argv[1], sys.argv[1:])
    """
)


class SandlockModularCITest(unittest.TestCase):
    def test_distinct_caches_run_together_without_shared_runner(self):
        text = WRAP.read_text(encoding="utf-8")
        self.assertNotIn("model_lock", text)
        self.assertNotIn("scripts/test_cache.py", text)
        self.assertNotIn("scripts/run_tests.py", text)
        self.assertNotIn("scripts/pregate.sh", text)
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            fake = td / "sandlock"
            fake.write_text(FAKE)
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)

            def once(name):
                cache = td / name
                cache.mkdir()
                marker = td / (name + ".marker")
                payload = (
                    "from pathlib import Path; import os; "
                    "Path(os.environ['MARKER']).write_text('ok')"
                )
                env = os.environ.copy()
                env["SANDLOCK_BIN"] = str(fake)
                env["MARKER"] = str(marker)
                env["PFY_SANDLOCK"] = "auto"
                proc = subprocess.run(
                    [sys.executable, str(WRAP), "--cache", str(cache), "--action", "install", "--", sys.executable, "-c", payload],
                    env=env,
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )
                return proc.returncode, proc.stderr, marker.read_text() if marker.exists() else ""

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(once, ["a", "b"]))
            for code, err, body in results:
                self.assertEqual(code, 0, err)
                self.assertEqual(body, "ok")


if __name__ == "__main__":
    unittest.main()
