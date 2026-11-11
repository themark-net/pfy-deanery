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


class SupersedeOfflineStubTest(unittest.TestCase):
    def test_stub_is_used_and_network_mode_does_not_launch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            state = Path(raw)
            marker = state / "check-ran"
            launch_log = state / "launches.log"
            check = state / "supersede_check"
            runner = state / "systemd-run"
            _exe(
                check,
                "#!/bin/sh\nprintf '%s\\n' ran > \"$PFY_CHECK_MARKER\"\n"
                "printf '%s\\n' 'network-required'\nexit 2\n",
            )
            _exe(runner, "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$PFY_LAUNCH_LOG\"\n")
            env = os.environ.copy()
            env.update({
                "PFY_SUPERSEDE_CHECK": str(check),
                "PFY_SYSTEMD_RUN": str(runner),
                "PFY_LAUNCH_LOG": str(launch_log),
                "PFY_CHECK_MARKER": str(marker),
                "PFY_CATALOG_STATE_DIR": str(state),
                "PFY_CATALOG_OFFLINE": "1",
            })
            isolate_env(env, state)
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
            self.assertTrue(marker.exists())
            launched = launch_log.read_text() if launch_log.exists() else ""
            self.assertEqual(launched.strip(), "")
            latest = (state / "loop.latest.json").read_text()
            self.assertIn("error", latest)
            self.assertFalse((state / "model-prices-refresh.json").exists())
