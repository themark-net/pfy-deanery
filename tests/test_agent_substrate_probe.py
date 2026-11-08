#!/usr/bin/env python3
"""Drive the agent-substrate probe with a stub runsc. No network and no binary.

A restore that exits 0 and reprints the same tick must not count as continued
state. A later tick with the same acc byte must. Rootless restore refusal must
not skip the userns cycle, and neither result may claim the pfy build timeout
moved.
"""

from __future__ import annotations

import os
import stat
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "agent-substrate" / "probe.py"

STUB_RUNSC = """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

argv = sys.argv[1:]
if "--version" in argv:
    print("runsc version stub")
    raise SystemExit(0)

def split(argv):
    i = 0
    positionals = []
    values = {}
    while i < len(argv):
        token = argv[i]
        if token == "--":
            positionals.extend(argv[i + 1 :])
            break
        if token in ("--root", "-bundle", "-image-path", "-pid-file"):
            values[token] = argv[i + 1]
            i += 2
            continue
        if token.startswith("-"):
            i += 1
            continue
        positionals.append(token)
        i += 1
    return positionals, values

positionals, values = split(argv)
sub = positionals[0] if positionals else ""
rootless = "--rootless" in argv
if sub == "spec":
    bundle = Path(values["-bundle"])
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "config.json").write_text(
        json.dumps(
            {
                "root": {"path": "rootfs", "readonly": False},
                "process": {"terminal": True, "args": ["true"], "env": ["PATH=/usr/bin"]},
            }
        )
        + "\\n",
        encoding="utf-8",
    )
    raise SystemExit(0)
if sub == "do":
    if rootless:
        print("rootless-ok")
    raise SystemExit(0)
if sub == "run":
    print("digest=stub bytes=8 acc0=1")
    print("tick=1 acc=9")
    print("tick=2 acc=9")
    raise SystemExit(0)
if sub == "state":
    cid = positionals[1] if len(positionals) > 1 else "x"
    print(json.dumps({"id": cid, "pid": 424242, "status": "running"}))
    raise SystemExit(0)
if sub == "checkpoint":
    image = Path(values["-image-path"])
    image.mkdir(parents=True, exist_ok=True)
    (image / "pages.img").write_bytes(b"stub")
    raise SystemExit(0)
if sub == "restore":
    if rootless:
        sys.stderr.write('Rootless mode not supported with "restore"\\n')
        raise SystemExit(128)
    print("RESTORE_LINE")
    raise SystemExit(0)
raise SystemExit(0)
"""

STUB_UNSHARE = """#!/bin/sh
while [ $# -gt 0 ]; do
  if [ "$1" = "--" ]; then
    shift
    exec "$@"
  fi
  shift
done
echo "stub unshare: missing --" >&2
exit 2
"""


def _write_exe(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class AgentSubstrateProbeTests(unittest.TestCase):
    def _run(self, name: str, restore_line: str) -> subprocess.CompletedProcess[str]:
        work = ROOT / "tmp" / "agent-substrate-probe-test" / name
        if work.exists():
            for child in sorted(work.rglob("*"), reverse=True):
                if child.is_file() or child.is_symlink():
                    child.unlink()
                elif child.is_dir():
                    child.rmdir()
        work.mkdir(parents=True, exist_ok=True)
        runsc = work / "stub-runsc.py"
        unshare = work / "stub-unshare.sh"
        _write_exe(runsc, STUB_RUNSC.replace("RESTORE_LINE", restore_line))
        _write_exe(unshare, STUB_UNSHARE)
        return subprocess.run(
            [
                "python3",
                str(PROBE),
                "--runsc",
                str(runsc),
                "--unshare",
                str(unshare),
                "--work",
                str(work / "run"),
                "--results",
                str(work / "results.json"),
                "--bytes",
                "32",
                "--tick-timeout",
                "2",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LANG": "C.UTF-8"},
            check=False,
        )

    def _lines(self, proc: subprocess.CompletedProcess[str]) -> list[str]:
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout.splitlines()

    def test_same_tick_is_not_continued_state(self) -> None:
        lines = self._lines(self._run("same", "tick=2 acc=9"))
        self.assertIn("rootless_restore_ok=0", lines)
        self.assertIn("rootless_checkpoint_ok=1", lines)
        self.assertIn("userns_checkpoint_ok=1", lines)
        self.assertIn("userns_restore_ok=1", lines)
        self.assertIn("state_continued=0", lines)
        self.assertIn("acc_same=0", lines)
        self.assertIn("gap_b_timeout_changed=0", lines)
        self.assertIn("host_build_sessions_shelved=0", lines)
        self.assertIn("full_stack=SKIPPED", lines)

    def test_later_tick_counts_and_gap_b_stays_zero(self) -> None:
        lines = self._lines(self._run("later", "tick=3 acc=9"))
        self.assertIn("rootless_restore_ok=0", lines)
        self.assertIn("userns_restore_ok=1", lines)
        self.assertIn("state_continued=1", lines)
        self.assertIn("tick_before=2", lines)
        self.assertIn("tick_after=3", lines)
        self.assertIn("acc_same=1", lines)
        self.assertIn("gap_b_timeout_changed=0", lines)
        self.assertIn("host_build_sessions_shelved=0", lines)
        self.assertIn("full_stack=SKIPPED", lines)


if __name__ == "__main__":
    unittest.main()
