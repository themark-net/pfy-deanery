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
            self.assertFalse(stamp.exists(), proc.stderr)
            self.assertNotIn("already dispatched", proc.stderr)
            if ancestor:
                self.assertIn("classification needs a listener", proc.stderr)
            else:
                self.assertIn("not an ancestor", proc.stderr)
        finally:
            for path in sorted(work.rglob("*"), reverse=True):
                path.unlink(missing_ok=True)
            work.rmdir()

    def _run(self, env, dest):
        marker = pathlib.Path(
            "/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/hiroute.dispatched"
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
