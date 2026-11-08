#!/usr/bin/env python3
"""Drive the gitai probe with stub binaries. No network and no real gitaly.

A missing build must stay SKIPPED and still record the plain-git race.
A stub that exits and prints the server token must come back redacted.
The same-line race must still conflict after the card leaves I0.
Neither run may rewrite the recorded results.json.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "gitai" / "probe.py"
RECORDED = ROOT / "eval" / "evq1107" / "gitai" / "results.json"
HEX64 = re.compile(r"\b[0-9a-f]{64}\b")


def _recorded_digest() -> str:
    return hashlib.sha256(RECORDED.read_bytes()).hexdigest()


def _stub(path: Path, body: str) -> None:
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run(cache: Path, out: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GITAI_CACHE"] = str(cache)
    env["GITAI_OUT"] = str(out)
    env["GITAI_WORK"] = str(cache / "work")
    env.pop("GITAI_KEEP", None)
    return subprocess.run(
        ["python3", str(PROBE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=120,
    )


class GitaiProbeTests(unittest.TestCase):
    def test_missing_binaries_skip_and_same_line_still_conflicts(self) -> None:
        before = _recorded_digest()
        with tempfile.TemporaryDirectory(prefix="gitai-missing-") as tmp:
            work = Path(tmp)
            proc = _run(work / "cache", work / "out.json")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            payload = json.loads((work / "out.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["gitai"]["status"], "SKIPPED")
        self.assertIn("missing binaries", payload["gitai"]["reason"])
        same = payload["plain"]["same_line"]
        self.assertEqual(same["landed"], 1)
        self.assertEqual(same["conflicts"], 1)
        self.assertEqual(same["unresolved"], 0)
        disjoint = payload["plain"]["disjoint"]
        self.assertEqual(disjoint["landed"], 8)
        self.assertEqual(disjoint["conflicts"], 0)
        self.assertEqual(disjoint["unresolved"], 0)
        self.assertEqual(_recorded_digest(), before)
        self.assertIsNone(HEX64.search(json.dumps(payload)))

    def test_stub_server_redacts_the_token_and_stays_skipped(self) -> None:
        before = _recorded_digest()
        with tempfile.TemporaryDirectory(prefix="gitai-stub-") as tmp:
            work = Path(tmp)
            bindir = work / "cache" / "src" / "git-ai" / "_build" / "bin"
            bindir.mkdir(parents=True)
            script = (
                'if [ "$1" = "--version" ]; then\n'
                '  echo "Gitaly, version stub"\n'
                "  exit 0\n"
                "fi\n"
                'token=$(sed -n \'s/^token = "\\(.*\\)"/\\1/p\' "$2" | head -1)\n'
                'echo "leaked $token"\n'
                "exit 1\n"
            )
            for name in ("gitaly", "graft", "gitaly-hooks", "gitaly-ssh"):
                _stub(bindir / name, script)
            proc = _run(work / "cache", work / "out.json")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            text = (work / "out.json").read_text(encoding="utf-8")
            payload = json.loads(text)
        self.assertEqual(payload["gitai"]["status"], "SKIPPED")
        self.assertIn("server did not listen", payload["gitai"]["reason"])
        self.assertIn("leaked [redacted]", payload["gitai"]["reason"])
        self.assertIsNone(HEX64.search(text))
        self.assertEqual(payload["plain"]["same_line"]["conflicts"], 1)
        self.assertEqual(payload["plain"]["same_line"]["landed"], 1)
        self.assertEqual(_recorded_digest(), before)


if __name__ == "__main__":
    unittest.main()
