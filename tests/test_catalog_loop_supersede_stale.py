import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _exe(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


class SupersedeStaleTest(unittest.TestCase):
    def test_exit_0_records_stale_lines_and_launches(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            state = Path(raw)
            launch_log = state / "launches.log"
            check = state / "supersede_check"
            runner = state / "systemd-run"
            _exe(
                check,
                "#!/bin/sh\nprintf '%s\\n' 'stale: old-tool' 'note: ignore' 'stale: other-tool'\nexit 0\n",
            )
            _exe(runner, "#!/bin/sh\nprintf '%s\\n' launched >> \"$PFY_LAUNCH_LOG\"\n")
            env = os.environ.copy()
            env.update({
                "PFY_SUPERSEDE_CHECK": str(check),
                "PFY_SYSTEMD_RUN": str(runner),
                "PFY_LAUNCH_LOG": str(launch_log),
                "PFY_CATALOG_STATE_DIR": str(state),
                "PFY_CATALOG_OFFLINE": "1",
            })
            proc = subprocess.run(
                ["bash", str(ROOT / "scripts" / "catalog_loop.sh"), "tick"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                timeout=90,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            latest = json.loads((state / "loop.latest.json").read_text())
            self.assertEqual(
                latest.get("supersede_stale"),
                ["stale: old-tool", "stale: other-tool"],
            )
            self.assertNotEqual(latest.get("status"), "stopped")
            needs = state / "needs-mark.tsv"
            if needs.exists():
                self.assertNotIn("supersede-stop", needs.read_text())
            self.assertIn("launched", launch_log.read_text())
