import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUG = "grill-fixture-not-a-real-lane"


class DispatchedMarkerTest(unittest.TestCase):
    def test_second_start_exits_2_before_git_or_grok(self):
        script = ROOT / "scripts" / "integrate_lane.sh"
        marker = ROOT / "tmp" / "integrate" / f"{SLUG}.dispatched"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("busy\n")
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            log = td / "calls.log"
            bindir = td / "bin"
            bindir.mkdir()
            fake = "#!/bin/sh\nprintf '%s\\n' \"$0 $*\" >> " + str(log) + "\nexit 0\n"
            for name in ("git", "grok"):
                path = bindir / name
                path.write_text(fake)
                path.chmod(path.stat().st_mode | stat.S_IEXEC)
            env = os.environ.copy()
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            try:
                result = subprocess.run(
                    ["bash", str(script), "--slug", SLUG],
                    cwd=ROOT,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            finally:
                marker.unlink(missing_ok=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse(log.exists(), "git or grok ran: " + log.read_text() if log.exists() else "")
