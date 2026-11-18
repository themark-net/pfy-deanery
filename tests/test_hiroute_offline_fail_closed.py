import json
import os
import pathlib
import stat
import subprocess
import tempfile
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval" / "integrate" / "hiroute" / "run-on-main.sh"


class HirouteOfflineFailClosedTest(unittest.TestCase):
    def test_missing_binary_writes_no_receipt(self):
        self.assertTrue(SCRIPT.is_file(), "run-on-main.sh missing")
        empty = pathlib.Path(tempfile.mkdtemp())
        dest = empty / "receipt.json"
        env = os.environ.copy()
        env["PATH"] = str(empty)
        env["HIROUTE_BIN"] = str(empty / "hiroute-missing")
        proc = subprocess.run(
            ["/bin/bash", str(SCRIPT), str(dest)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(dest.exists())
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("11434", text)
        self.assertIn("no-listen", text)

    def test_stand_in_on_claimed_main_does_not_run_or_write(self):
        self._assert_stand_in(ancestor=True)

    def test_stand_in_off_main_does_not_run_or_write(self):
        self._assert_stand_in(ancestor=False)

    def _assert_stand_in(self, ancestor):
        work = pathlib.Path(tempfile.mkdtemp(dir="/tmp"))
        try:
            stamp = work / "stamp"
            dest = work / "receipt.json"
            git_bin = work / "git"
            hi = work / "hiroute"
            code = "0" if ancestor else "1"
            git_bin.write_text(
                textwrap.dedent(
                    """\
                    #!/bin/sh
                    if [ "$1" = merge-base ]; then
                      exit %s
                    fi
                    if [ "$1" = rev-parse ] && [ "$2" = HEAD ]; then
                      printf '%%s\\n' 0123456789abcdef0123456789abcdef01234567
                      exit 0
                    fi
                    exit 0
                    """
                    % code
                ),
                encoding="utf-8",
            )
            hi.write_text("#!/bin/sh\ntouch '%s'\nexit 0\n" % stamp, encoding="utf-8")
            for path in (git_bin, hi):
                path.chmod(path.stat().st_mode | stat.S_IEXEC)
            env = os.environ.copy()
            env["PATH"] = "%s:/usr/bin:/bin" % work
            env["HIROUTE_BIN"] = str(hi)
            proc = self._run(env, dest)
            self.assertNotEqual(proc.returncode, 0, proc.stderr)
            self.assertFalse(dest.exists(), proc.stderr)
            self.assertNotIn("already dispatched", proc.stderr)
            if ancestor:
                self.assertTrue(stamp.exists(), proc.stderr)
                self.assertNotIn("not an ancestor", proc.stderr)
            else:
                self.assertFalse(stamp.exists(), proc.stderr)
                self.assertIn("not an ancestor", proc.stderr)
        finally:
            for path in sorted(work.rglob("*"), reverse=True):
                path.unlink(missing_ok=True)
            work.rmdir()

    def test_routing_list_success_writes_receipt(self):
        # The script cds to its repo root and requires HEAD to be an ancestor
        # of origin/main. Drive a copy of the script from a temp repo so this
        # check does not depend on the checkout that is running the tests.
        work = pathlib.Path(tempfile.mkdtemp(prefix="hiroute-ok-", dir="/tmp"))
        try:
            repo = work / "repo"
            remote = work / "remote.git"
            repo.mkdir()
            env = os.environ.copy()
            env["GIT_AUTHOR_NAME"] = "hiroute"
            env["GIT_AUTHOR_EMAIL"] = "hiroute@example.com"
            env["GIT_COMMITTER_NAME"] = "hiroute"
            env["GIT_COMMITTER_EMAIL"] = "hiroute@example.com"
            subprocess.run(
                ["git", "init", "-b", "main"],
                cwd=repo,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            (repo / "README").write_text("ok\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "README"],
                cwd=repo,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "init"],
                cwd=repo,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "clone", "--bare", str(repo), str(remote)],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "remote", "add", "origin", str(remote)],
                cwd=repo,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "fetch", "origin"],
                cwd=repo,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["git", "branch", "--set-upstream-to=origin/main", "main"],
                cwd=repo,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            dest_script = repo / "eval" / "integrate" / "hiroute" / "run-on-main.sh"
            dest_script.parent.mkdir(parents=True)
            dest_script.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")
            dest_script.chmod(dest_script.stat().st_mode | stat.S_IEXEC)
            hi = work / "hiroute"
            dest = work / "receipt.json"
            marker = work / "missing-marker"
            hi.write_text(
                textwrap.dedent(
                    """\
                    #!/bin/sh
                    if [ "$1" = version ]; then
                      printf '%s\\n' 'hiroute 0.3.1-test'
                      exit 0
                    fi
                    if [ "$1" = routing ] && [ "$2" = list ]; then
                      printf '%s\\n' '{"status":"succeeded","data":{"plans":[{"model_alias":"stub-route"}]}}'
                      exit 0
                    fi
                    exit 2
                    """
                ),
                encoding="utf-8",
            )
            hi.chmod(hi.stat().st_mode | stat.S_IEXEC)
            env["HIROUTE_BIN"] = str(hi)
            env["PFY_HIROUTE_LANE_MARKER"] = str(marker)
            env["HIROUTE_CACHE"] = str(work / "cache")
            env["HOME"] = str(work / "home")
            (work / "home").mkdir()
            proc = subprocess.run(
                ["/bin/bash", str(dest_script), str(dest)],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            doc = json.loads(dest.read_text(encoding="utf-8"))
            self.assertEqual(doc["slug"], "hiroute")
            self.assertEqual(doc["run_kind"], "pipeline")
            self.assertEqual(doc["outcome"], "ok")
            self.assertEqual(doc["tool_version"], "hiroute 0.3.1-test")
            self.assertIn("stub-route", doc["did"])
            self.assertIn("model_call never", doc["did"])
            self.assertIn("routing_agreement_of_20", doc["did"])
            self.assertNotIn("hr_", doc["did"])
        finally:
            for path in sorted(work.rglob("*"), reverse=True):
                if path.is_file() or path.is_symlink():
                    path.unlink(missing_ok=True)
            for path in sorted(work.rglob("*"), reverse=True):
                if path.is_dir():
                    path.rmdir()
            work.rmdir()

    def _run(self, env, dest):
        marker = pathlib.Path(
            "$PFY_TMP/integrate2/hiroute.dispatched"
        )
        cmd = ["/bin/bash", str(SCRIPT), str(dest)]
        if not marker.exists():
            return subprocess.run(
                cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=30
            )
        bwrap = "/usr/bin/bwrap"
        if not os.access(bwrap, os.X_OK):
            self.skipTest("bwrap missing; cannot hide the dispatched marker")
        integrate = marker.parent
        wt = integrate / "wt"
        return subprocess.run(
            [
                bwrap,
                "--dev-bind",
                "/",
                "/",
                "--tmpfs",
                str(integrate),
                "--ro-bind",
                str(wt),
                str(wt),
                "--chdir",
                str(ROOT),
                "--setenv",
                "PATH",
                env["PATH"],
                "--setenv",
                "HIROUTE_BIN",
                env["HIROUTE_BIN"],
                "--setenv",
                "HOME",
                "/tmp",
                "--",
                *cmd,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )


if __name__ == "__main__":
    unittest.main()
