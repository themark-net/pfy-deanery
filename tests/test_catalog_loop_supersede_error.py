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


class SupersedeErrorTest(unittest.TestCase):
    def _tick(self, code: int) -> None:
        with tempfile.TemporaryDirectory() as raw:
            state = Path(raw)
            launch_log = state / "launches.log"
            check = state / "supersede_check"
            runner = state / "systemd-run"
            _exe(check, f"#!/bin/sh\nexit {code}\n")
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
            self.assertEqual(latest.get("status"), "error")
            self.assertNotEqual(latest.get("supersede"), "stop")
            launched = launch_log.read_text() if launch_log.exists() else ""
            self.assertEqual(launched.strip(), "")
            needs = state / "needs-mark.tsv"
            if needs.exists():
                self.assertNotIn("supersede-stop", needs.read_text())

    def test_exit_2_is_error(self) -> None:
        self._tick(2)

    def test_exit_124_timeout_is_error(self) -> None:
        self._tick(124)
