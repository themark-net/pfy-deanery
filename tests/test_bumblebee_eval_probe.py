"""Bumblebee eval probe pins the hashed binary inside sandlock.

confine.py --clean-env does not forward PFY_BUMBLEBEE_BIN or HOME. A PATH
decoy must not satisfy the scan, and the home refuse must exit 2 before the
sentinel starts. Recovery is the pin script in the sandboxed command.
"""

from __future__ import annotations

import importlib.util
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evals" / "bumblebee" / "probe.py"

FAKE = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import os, sys
    if sys.argv[1:] == ["true"]:
        raise SystemExit(0)
    env = {}
    for key in ("PATH", "SANDLOCK_STARTED", "TMPDIR", "LANG", "LC_ALL"):
        if os.environ.get(key):
            env[key] = os.environ[key]
    os.execvpe(sys.argv[1], sys.argv[1:], env)
    """
)


def load_probe():
    spec = importlib.util.spec_from_file_location("bumblebee_eval_probe", PROBE)
    if spec is None or spec.loader is None:
        raise RuntimeError("probe import failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BumblebeeEvalProbeTests(unittest.TestCase):
    def setUp(self):
        self.probe = load_probe()
        self.tmp = Path(tempfile.mkdtemp(prefix="bumblebee-probe-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.fake = self.tmp / "fake-sandlock.py"
        self.fake.write_text(FAKE, encoding="utf-8")
        self.fake.chmod(self.fake.stat().st_mode | stat.S_IEXEC)
        self.decoy_mark = self.tmp / "decoy-ran"
        decoy_dir = self.tmp / "decoy-bin"
        decoy_dir.mkdir()
        decoy = decoy_dir / "bumblebee"
        decoy.write_text(
            "#!/bin/sh\nprintf decoy > %s\nexit 0\n" % self._q(self.decoy_mark),
            encoding="utf-8",
        )
        decoy.chmod(decoy.stat().st_mode | stat.S_IEXEC)
        self.old_path = os.environ.get("PATH")
        os.environ["PATH"] = "%s:%s" % (decoy_dir, "/usr/bin:/bin")

    def tearDown(self):
        if self.old_path is None:
            os.environ.pop("PATH", None)
        else:
            os.environ["PATH"] = self.old_path

    @staticmethod
    def _q(path: Path) -> str:
        return shlex.quote(str(path))

    def test_sandboxed_scan_uses_the_pinned_binary_not_path(self):
        mark = self.tmp / "pinned-ran"
        pinned = self.tmp / "pinned-bumblebee"
        pinned.write_text(
            "#!/bin/sh\nprintf pinned > %s\nexit 0\n" % self._q(mark),
            encoding="utf-8",
        )
        pinned.chmod(pinned.stat().st_mode | stat.S_IEXEC)
        work = self.tmp / "work"
        code, stdout, stderr, unsandboxed = self.probe.run_wrapped(
            self.probe.FIXTURES / "clean",
            work / "stage",
            work / "wrap",
            pinned,
            sandlock_bin=self.fake,
        )
        scan = self.probe.load_scan(work / "stage")
        self.assertEqual(code, 0, stderr)
        self.assertEqual(unsandboxed, 0)
        self.assertEqual(scan.get("verdict"), "CLEAN")
        self.assertTrue(mark.is_file(), stdout)
        self.assertFalse(self.decoy_mark.exists(), stdout)
        self.assertNotIn("fixture-not-a-secret", stdout)
        self.assertNotIn("fixture-not-a-secret", stderr)

    def test_home_refuse_is_sandboxed_and_does_not_start_the_sentinel(self):
        row = self.probe.case_home(self.tmp / "home-work", sandlock_bin=self.fake)
        self.assertEqual(row["exit"], 2)
        self.assertTrue(row["refused"])
        self.assertFalse(row["sentinel_started"])
        self.assertEqual(row["unsandboxed_lines"], 0)
        self.assertTrue(row["sandboxed"])
        self.assertFalse(self.decoy_mark.exists())

    def test_committed_eval_files_have_no_home_path_or_owner_name(self):
        paths = [
            "eval/evals/bumblebee/VERDICT.json",
            "eval/evals/bumblebee/results.json",
            "eval/evals/bumblebee/probe.py",
            "eval/evals/bumblebee/fixtures/clean/.cursor/mcp.json",
            "eval/evals/bumblebee/fixtures/git-selector/.cursor/mcp.json",
            "eval/evals/bumblebee/fixtures/plaintext-env/.cursor/mcp.json",
            "eval/evals/bumblebee/fixtures/clean/clean-app/package-lock.json",
            "eval/evals/bumblebee/fixtures/git-selector/clean-app/package-lock.json",
            "eval/evals/bumblebee/fixtures/plaintext-env/clean-app/package-lock.json",
        ]
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_public_paths.py"), "--paths", *paths],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
