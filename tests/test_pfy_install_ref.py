"""install.sh defaults to main; PFY_REF can pin a ref or SHA.

Temp HOME, fake git on PATH, no public network, no real clone.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "install.sh"
ONE_LINER = "https://raw.githubusercontent.com/themark-net/pfy-deanery/main/install.sh"
FAKE_GIT = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path

log = os.environ.get("PFY_FAKE_GIT_LOG")
allowed = [x for x in (os.environ.get("PFY_FAKE_GIT_REFS") or "main").split(",") if x]
args = sys.argv[1:]
cwd = os.getcwd()
if len(args) >= 2 and args[0] == "-C":
    cwd = args[1]
    args = args[2:]
if log:
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"cwd": cwd, "args": args}) + "\n")

def die(msg, code=128):
    sys.stderr.write(msg + "\n")
    raise SystemExit(code)

if not args:
    die("usage: git <command>")

cmd = args[0]
if cmd == "init":
    target = Path(cwd)
    for a in args[1:]:
        if not a.startswith("-"):
            target = Path(a)
            break
    (target / ".git").mkdir(parents=True, exist_ok=True)
    raise SystemExit(0)
if cmd == "remote":
    raise SystemExit(0)
if cmd == "fetch":
    ref = args[-1]
    if ref not in allowed:
        die("fatal: couldn't find remote ref %s" % ref)
    Path(cwd).mkdir(parents=True, exist_ok=True)
    raise SystemExit(0)
if cmd == "checkout":
    root = Path(cwd)
    root.mkdir(parents=True, exist_ok=True)
    pfy = root / "pfy"
    pfy.write_text("#!/bin/sh\necho fake-pfy\n")
    pfy.chmod(pfy.stat().st_mode | 0o111)
    raise SystemExit(0)
die("unexpected git command: %s" % " ".join(args), 2)
'''


def _write_exe(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


class InstallRefTests(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="pfy-install-ref-"))
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.bindir = self.home / "bin"
        self.git_log = self.home / "fake-git.log"
        _write_exe(self.bindir / "git", FAKE_GIT)
        # Stub id so a real uid-0 environment cannot skip these tests.
        _write_exe(self.bindir / "id", "#!/bin/sh\necho 1000\n")

    def env(self, **extra: str) -> dict[str, str]:
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env["PATH"] = str(self.bindir) + os.pathsep + "/usr/bin:/bin"
        env["PFY_FAKE_GIT_LOG"] = str(self.git_log)
        env["PFY_FAKE_GIT_REFS"] = "main"
        env.pop("PFY_REF", None)
        env.pop("PFY_INSTALL_SOURCE", None)
        env.pop("PFY_ALLOW_ROOT", None)
        env.pop("GIT_DIR", None)
        env.pop("GIT_WORK_TREE", None)
        env.pop("GIT_COMMON_DIR", None)
        env.update(extra)
        return env

    def run_install(self, *args: str, **extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["sh", str(INSTALL), *args],
            cwd=str(self.home),
            env=self.env(**extra),
            capture_output=True,
            text=True,
            timeout=15,
        )

    def git_calls(self) -> list[dict]:
        if not self.git_log.is_file():
            return []
        return [json.loads(line) for line in self.git_log.read_text().splitlines() if line.strip()]

    def test_one_liner_points_at_main(self) -> None:
        text = INSTALL.read_text()
        self.assertIn(ONE_LINER, text)
        self.assertNotIn("v0.4.17", text)
        self.assertNotIn("pfy-mentat/main/", text)

    def test_default_ref_is_main_and_resolves_with_fake_git(self) -> None:
        proc = self.run_install("--no-setup")
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        self.assertIn("main", blob)
        dest = self.home / ".local" / "share" / "pfy" / "main"
        self.assertTrue((dest / "pfy").is_file())
        shim = self.home / ".local" / "bin" / "pfy"
        self.assertTrue(shim.is_file())
        fetches = [c for c in self.git_calls() if c["args"] and c["args"][0] == "fetch"]
        self.assertTrue(fetches, self.git_calls())
        self.assertEqual(fetches[0]["args"][-1], "main")
        self.assertFalse(any("github.com" in " ".join(c["args"]) and "clone" in c["args"] for c in self.git_calls()) or False)

    def test_version_and_dry_run_print_main(self) -> None:
        proc = self.run_install("--version")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "main")
        proc = self.run_install("--dry-run")
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        self.assertIn("ref: main", blob)
        self.assertIn("dry_run: true", blob)
        self.assertIn("main", blob)
        self.assertEqual(self.git_calls(), [])
        self.assertEqual(list(self.home.iterdir()), [self.home / "bin"])

    def test_missing_pfy_ref_fails_clearly_and_writes_nothing(self) -> None:
        proc = self.run_install("--no-setup", PFY_REF="does-not-exist", PFY_FAKE_GIT_REFS="main")
        blob = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, blob)
        self.assertIn("does not exist", blob.lower())
        self.assertIn("does-not-exist", blob)
        self.assertIn("pfy install:", blob)
        share = self.home / ".local" / "share" / "pfy"
        leftovers = [p.name for p in share.iterdir()] if share.exists() else []
        self.assertEqual(leftovers, [], leftovers)

    def test_empty_or_whitespace_pfy_ref_fails_and_writes_nothing(self) -> None:
        for value in ("", "   ", "\t"):
            with self.subTest(PFY_REF=repr(value)):
                proc = self.run_install("--no-setup", PFY_REF=value)
                blob = proc.stdout + proc.stderr
                self.assertNotEqual(proc.returncode, 0, blob)
                self.assertIn("pfy install:", blob)
                lower = blob.lower()
                self.assertTrue("empty" in lower or "invalid ref" in lower, blob)
                share = self.home / ".local" / "share" / "pfy"
                leftovers = [p.name for p in share.iterdir()] if share.exists() else []
                self.assertEqual(leftovers, [], leftovers)
                self.assertFalse((self.home / ".local" / "bin" / "pfy").exists())

    def test_pfy_ref_sha_resolves_when_fake_allows_it(self) -> None:
        sha = "0123456789abcdef0123456789abcdef01234567"
        proc = self.run_install("--no-setup", PFY_REF=sha, PFY_FAKE_GIT_REFS=sha)
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        dest = self.home / ".local" / "share" / "pfy" / sha
        self.assertTrue((dest / "pfy").is_file())
        fetches = [c for c in self.git_calls() if c["args"] and c["args"][0] == "fetch"]
        self.assertTrue(fetches)
        self.assertEqual(fetches[0]["args"][-1], sha)

    def test_pfy_ref_v050_tag_resolves_offline_when_fake_allows_it(self) -> None:
        proc = self.run_install("--no-setup", PFY_REF="v0.5.0", PFY_FAKE_GIT_REFS="v0.5.0")
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        dest = self.home / ".local" / "share" / "pfy" / "v0.5.0"
        self.assertTrue((dest / "pfy").is_file())
        fetches = [c for c in self.git_calls() if c["args"] and c["args"][0] == "fetch"]
        self.assertTrue(fetches, blob)
        self.assertEqual(fetches[0]["args"][-1], "v0.5.0")
        self.assertNotIn("ref: main", proc.stdout)

    def test_missing_v050_tag_fails_closed_and_default_stays_main(self) -> None:
        proc = self.run_install("--no-setup", PFY_REF="v0.5.0", PFY_FAKE_GIT_REFS="main")
        blob = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, blob)
        self.assertIn("does not exist", blob.lower())
        self.assertIn("v0.5.0", blob)
        share = self.home / ".local" / "share" / "pfy"
        leftovers = [p.name for p in share.iterdir()] if share.exists() else []
        self.assertEqual(leftovers, [], leftovers)
        self.assertFalse((self.home / ".local" / "bin" / "pfy").exists())
        proc = self.run_install("--dry-run")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("ref: main", proc.stdout)
