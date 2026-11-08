#!/usr/bin/env python3
"""Drive the aider probe with stub editors. No network, no model, no aider binary.

A missing editor must not look like a pass. An edit that multiplies, even when
add(2, 2) is 4, is a miss. The asked line recovers. The live step must not
start that editor until the model lock holds, and low memory must skip it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "aider" / "probe.py"
FIXTURE = ROOT / "eval" / "evq1107" / "aider" / "fixtures" / "mathutil.py"


def _stub(folder: Path, name: str, body: str) -> Path:
    path = folder / name
    path.write_text(textwrap.dedent(body))
    path.chmod(0o755)
    return path


class AiderProbeTest(unittest.TestCase):
    def _common(self, folder: Path) -> list[str]:
        return [
            "--work",
            str(folder / "repo"),
            "--out",
            str(folder / "results.json"),
            "--home",
            str(folder / "home"),
            "--gitconfig",
            str(folder / "gitconfig"),
        ]

    def _run(self, args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(PROBE), *args],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=env,
        )

    def test_wrong_product_is_a_miss_and_the_asked_line_recovers(self) -> None:
        before = FIXTURE.read_bytes()
        with tempfile.TemporaryDirectory(prefix="aider-probe-") as tmp:
            folder = Path(tmp)
            (folder / "home").mkdir()
            missing = self._run(
                ["run", "--editor", str(folder / "no-such-editor"), *self._common(folder)],
                env={"PATH": "/usr/bin:/bin", "HOME": str(folder / "home"), "LANG": "C.UTF-8"},
            )
            self.assertEqual(missing.returncode, 2, missing.stderr)
            self.assertFalse((folder / "results.json").exists())

            wrong = _stub(
                folder,
                "wrong.py",
                """\
                #!/usr/bin/env python3
                from pathlib import Path
                path = Path("mathutil.py")
                path.write_text(path.read_text().replace("return a - b", "return a * b"))
                import subprocess, os
                subprocess.check_call(["git", "add", "mathutil.py"])
                subprocess.check_call(["git", "commit", "-m", "wrong"])
                """,
            )
            wrong_out = folder / "wrong.json"
            wrong_run = self._run(
                [
                    "run",
                    "--editor",
                    str(wrong),
                    "--work",
                    str(folder / "wrong-repo"),
                    "--out",
                    str(wrong_out),
                    "--home",
                    str(folder / "home"),
                    "--gitconfig",
                    str(folder / "gitconfig"),
                ],
                env={"PATH": "/usr/bin:/bin", "HOME": str(folder / "home"), "LANG": "C.UTF-8"},
            )
            self.assertEqual(wrong_run.returncode, 0, wrong_run.stderr)
            wrong_body = json.loads(wrong_out.read_text())
            self.assertEqual(wrong_body["correct_edits"], 0)
            self.assertEqual(wrong_body["git_edit"], 0)
            self.assertTrue(wrong_body["add_2_2_ok"])
            self.assertEqual(wrong_body["status"], "miss")

            good = _stub(
                folder,
                "good.py",
                """\
                #!/usr/bin/env python3
                from pathlib import Path
                import subprocess
                path = Path("mathutil.py")
                path.write_text(path.read_text().replace("return a - b", "return a + b"))
                subprocess.check_call(["git", "add", "mathutil.py"])
                subprocess.check_call(["git", "commit", "-m", "fix add"])
                """,
            )
            good_out = folder / "good.json"
            good_run = self._run(
                [
                    "run",
                    "--editor",
                    str(good),
                    "--work",
                    str(folder / "good-repo"),
                    "--out",
                    str(good_out),
                    "--home",
                    str(folder / "home"),
                    "--gitconfig",
                    str(folder / "gitconfig"),
                ],
                env={"PATH": "/usr/bin:/bin", "HOME": str(folder / "home"), "LANG": "C.UTF-8"},
            )
            self.assertEqual(good_run.returncode, 0, good_run.stdout + good_run.stderr)
            good_body = json.loads(good_out.read_text())
            self.assertEqual(good_body["correct_edits"], 1)
            self.assertEqual(good_body["git_edit"], 1)
            self.assertEqual(good_body["new_commits"], 1)
            self.assertEqual(good_body["status"], "pass")
        self.assertEqual(FIXTURE.read_bytes(), before)

    def test_live_does_not_start_the_editor_until_the_lock_holds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aider-lock-") as tmp:
            folder = Path(tmp)
            (folder / "home").mkdir()
            seen = folder / "lock-seen"
            editor = _stub(
                folder,
                "editor.py",
                """\
                #!/usr/bin/env python3
                from pathlib import Path
                Path("called").write_text("yes")
                """,
            )
            lock = _stub(
                folder,
                "lock.sh",
                """\
                #!/bin/sh
                echo locked > "%s"
                exit 9
                """
                % seen,
            )
            proc = self._run(
                ["live", "--editor", str(editor), *self._common(folder)],
                env={
                    "PATH": "/usr/bin:/bin",
                    "HOME": str(folder / "home"),
                    "LANG": "C.UTF-8",
                    "AIDER_PROBE_LOCK": str(lock),
                },
            )
            self.assertEqual(proc.returncode, 9, proc.stderr)
            self.assertEqual(seen.read_text().strip(), "locked")
            self.assertFalse((folder / "repo" / "called").exists())
            self.assertFalse((folder / "results.json").exists())

    def test_low_memory_skips_the_editor_and_records_host_busy(self) -> None:
        with tempfile.TemporaryDirectory(prefix="aider-mem-") as tmp:
            folder = Path(tmp)
            (folder / "home").mkdir()
            editor = _stub(
                folder,
                "editor.py",
                """\
                #!/usr/bin/env python3
                from pathlib import Path
                Path("called").write_text("yes")
                """,
            )
            lock = _stub(
                folder,
                "lock.sh",
                """\
                #!/bin/sh
                export PFY_MODEL_LOCK_HELD=1
                exec "$@"
                """,
            )
            proc = self._run(
                ["live", "--editor", str(editor), *self._common(folder)],
                env={
                    "PATH": "/usr/bin:/bin",
                    "HOME": str(folder / "home"),
                    "LANG": "C.UTF-8",
                    "AIDER_PROBE_LOCK": str(lock),
                    "AIDER_PROBE_SKIP_OLLAMA": "1",
                    "AIDER_PROBE_MEM_KIB": "1",
                    "AIDER_PROBE_MODEL_BYTES": "999999999999999",
                    "AIDER_PROBE_WAIT_SEC": "0",
                },
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            body = json.loads((folder / "results.json").read_text())
            self.assertEqual(body["status"], "HOST-BUSY")
            self.assertTrue(body["host_busy"])
            self.assertEqual(body["correct_edits"], 0)
            self.assertEqual(body["git_edit"], 0)
            self.assertFalse(body["keep_alive_sent"])
            self.assertFalse((folder / "repo" / "called").exists())


if __name__ == "__main__":
    unittest.main()
