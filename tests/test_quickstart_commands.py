"""Re-run the safe commands in the pfy build quickstart.

Fail: a runnable fence documents the wrong exit code, or a fence would
start a real build or pass --local.
Recovery: set exit= to the code ./pfy returns, and leave live builds
out of runnable fences. The planted-exit test is the fail case.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUICKSTART = ROOT / "docs" / "QUICKSTART-pfy-build.md"
FENCE_RE = re.compile(r"```bash runnable exit=(\d+)\n(.*?)```", re.S)
MIN_SAFE = 3


def _command_lines(body: str) -> list[str]:
    lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
    return lines


def _classify(line: str) -> str:
    """safe: help, dry-run, or usage. refuse: would start work. skip: not pfy build."""
    try:
        argv = shlex.split(line)
    except ValueError:
        return "refuse"
    if len(argv) < 2 or argv[0] != "./pfy" or argv[1] != "build":
        return "skip"
    rest = argv[2:]
    if "--local" in rest or "--reap" in rest:
        return "refuse"
    if "--help" in rest or "-h" in rest or "--dry-run" in rest:
        return "safe"
    positionals = [arg for arg in rest if not arg.startswith("-")]
    if len(positionals) == 1:
        return "refuse"
    return "safe"


def _run(body: str, cwd: Path) -> int:
    env = os.environ.copy()
    env["TMPDIR"] = str(cwd / "tmp")
    proc = subprocess.run(
        ["bash", "-lc", body],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return proc.returncode


def mismatches(text: str, cwd: Path, runner=_run) -> list[str]:
    found: list[str] = []
    safe_count = 0
    blocks = FENCE_RE.findall(text)
    if not blocks:
        return ["no runnable fences"]
    for expected_s, body in blocks:
        expected = int(expected_s)
        lines = _command_lines(body)
        if not lines:
            found.append("empty runnable fence")
            continue
        kinds = [_classify(line) for line in lines]
        if any(kind == "refuse" for kind in kinds):
            found.append("refusing live command:\n%s" % body)
            continue
        if not all(kind == "safe" for kind in kinds):
            continue
        safe_count += 1
        actual = runner(body, cwd)
        if actual != expected:
            found.append("exit %s != documented %s for:\n%s" % (actual, expected, body))
    if safe_count < MIN_SAFE:
        found.append("expected at least %s safe commands, found %s" % (MIN_SAFE, safe_count))
    return found


class QuickstartCommandTests(unittest.TestCase):
    def test_safe_commands_match_documented_exits(self) -> None:
        """Fail: ./pfy build --help is documented as exit 2, or the no-task
        command is documented as exit 0.
        Recovery: put the real exit code in the fence tag."""
        text = QUICKSTART.read_text(encoding="utf-8")
        self.assertEqual(mismatches(text, ROOT), [])

    def test_planted_wrong_exit_fails(self) -> None:
        """Fail: this test stays green after the no-task fence is changed to exit=0.
        Recovery: the checker compares the fence to the process, so the plant fails."""
        text = QUICKSTART.read_text(encoding="utf-8")
        planted = text.replace(
            "```bash runnable exit=2\n./pfy build\n```",
            "```bash runnable exit=0\n./pfy build\n```",
            1,
        )
        self.assertNotEqual(planted, text)
        problems = mismatches(planted, ROOT)
        self.assertTrue(problems, problems)
        self.assertTrue(
            any("exit 2 != documented 0" in item and "./pfy build" in item for item in problems),
            problems,
        )

    def test_local_and_reap_are_refused_before_subprocess(self) -> None:
        """Fail: a fence with --local or --reap is executed.
        Recovery: refuse those flags before subprocess.run."""

        def boom(_body: str, _cwd: Path) -> int:
            raise AssertionError("subprocess ran")

        local = '```bash runnable exit=0\n./pfy build --local "nope" --dry-run\n```\n'
        reap = "```bash runnable exit=0\n./pfy build --reap\n```\n"
        for text in (local, reap):
            problems = mismatches(text, ROOT, runner=boom)
            self.assertTrue(any(item.startswith("refusing live command:") for item in problems), problems)
            self.assertFalse(any("subprocess ran" in item for item in problems))


if __name__ == "__main__":
    unittest.main()
