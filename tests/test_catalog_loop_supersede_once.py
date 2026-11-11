import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
from tests._model_choice_isolation import isolate_env  # noqa: E402


def _exe(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


class TwoTickSupersedeTest(unittest.TestCase):
    def test_second_tick_does_not_launch_or_duplicate_stop_row(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            state = Path(raw)
            launch_log = state / "launches.log"
            check = state / "supersede_check"
            runner = state / "systemd-run"
            _exe(check, "#!/bin/sh\nprintf '%s\\n' 'sample-proj'\nexit 1\n")
            _exe(runner, "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$PFY_LAUNCH_LOG\"\n")
            env = os.environ.copy()
            env.update({
                "PFY_SUPERSEDE_CHECK": str(check),
                "PFY_SYSTEMD_RUN": str(runner),
                "PFY_LAUNCH_LOG": str(launch_log),
                "PFY_CATALOG_STATE_DIR": str(state),
                "PFY_CATALOG_OFFLINE": "1",
            })
            isolate_env(env, state)
            for _ in range(2):
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
            self.assertEqual(latest.get("status"), "stopped")
            self.assertEqual(latest.get("supersede"), "stop")
            rows = [
                line for line in (state / "needs-mark.tsv").read_text().splitlines()
                if line and not line.startswith("#") and "supersede-stop" in line
            ]
            self.assertEqual(len(rows), 1)
            self.assertIn("sample-proj", rows[0])
            launched = launch_log.read_text() if launch_log.exists() else ""
            self.assertEqual(launched.strip(), "")
