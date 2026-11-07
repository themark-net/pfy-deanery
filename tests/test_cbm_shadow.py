#!/usr/bin/env python3
"""Report-only shadow beside test_select. The gate result does not move.

How this fails: a detect_changes crash or a 30s hang changes the gate exit,
a disagreement is dropped, a risky path is logged as a subset, or
PFY_CBM_SHADOW=0 still runs the binary. Recovery: the hook returns without
waiting, every tool failure is one JSONL line, and the process exits 0.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHADOW = ROOT / "scripts" / "cbm_shadow.py"
PREGATE = ROOT / "scripts" / "pregate.sh"
PAD = 3

FAKE = textwrap.dedent(
    '''\
    #!/usr/bin/env python3
    import os, sys, time
    args = sys.argv[1:]
    stamp = os.environ.get("FAKE_STAMP", "")
    if stamp:
        with open(stamp, "a", encoding="utf-8") as handle:
            handle.write(" ".join(args) + "\\n")
    if args[:1] == ["--version"]:
        print("fake 0.0.0")
        raise SystemExit(0)
    if "list_projects" in args:
        print('{"projects":[]}')
        raise SystemExit(0)
    if "index_repository" in args:
        print('{"status":"indexed"}')
        raise SystemExit(0)
    if "detect_changes" in args:
        mode = os.environ.get("FAKE_MODE", "json")
        if mode == "fail":
            print("detect failed", file=sys.stderr)
            raise SystemExit(1)
        if mode == "sleep":
            time.sleep(30)
            raise SystemExit(0)
        print(os.environ.get("FAKE_JSON", '{"changed_files":[]}'))
        raise SystemExit(0)
    print("unexpected " + " ".join(args), file=sys.stderr)
    raise SystemExit(2)
    '''
)


def _git(cwd: Path, *args: str) -> str:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "shadow-test"
    env["GIT_AUTHOR_EMAIL"] = "shadow-test@example.com"
    env["GIT_COMMITTER_NAME"] = "shadow-test"
    env["GIT_COMMITTER_EMAIL"] = "shadow-test@example.com"
    proc = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise AssertionError(f"git {args[0]} failed: {proc.stderr or proc.stdout}")
    return proc.stdout.strip()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _base_repo(tmp: Path) -> None:
    _git(tmp, "init", "-b", "main")
    _git(tmp, "config", "user.email", "shadow-test@example.com")
    _git(tmp, "config", "user.name", "shadow-test")
    _write(tmp / "pfylib" / "__init__.py", '"""pkg"""\n')
    _write(tmp / "pfylib" / "leaf.py", "VALUE = 1\n")
    _write(tmp / "tests" / "__init__.py", "")
    _write(tmp / "tests" / "test_a.py", "def test_a():\n    assert True\n")
    _write(tmp / "tests" / "test_b.py", "def test_b():\n    assert True\n")
    _write(tmp / "tests" / "test_c.py", "def test_c():\n    assert True\n")
    for index in range(PAD):
        _write(
            tmp / "tests" / f"test_pad{index}.py",
            f"def test_pad_{index}():\n    assert True\n",
        )
    _write(tmp / "docs" / "readme.md", "# readme\n")
    _git(tmp, "add", "-A")
    _git(tmp, "commit", "-m", "base")


def _commit_all(tmp: Path, message: str) -> None:
    _git(tmp, "add", "-A")
    _git(tmp, "commit", "-m", message)


def _pids_with(needle: str) -> list[int]:
    found = []
    if not needle:
        return found
    raw_needle = needle.encode()
    me = os.getpid()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid == me:
            continue
        try:
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        if raw_needle in raw:
            found.append(pid)
    return found


def _kill_matching(*needles: str) -> None:
    for needle in needles:
        for pid in _pids_with(needle):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass


class CbmShadowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pfy-cbm-shadow-"))
        self.cache = self.tmp / "cache"
        self.log = self.tmp / "selections.jsonl"
        self.stamp = self.tmp / "fake-stamp.txt"
        self.fake = self.tmp / "fake-cbm"
        self.fake.write_text(FAKE, encoding="utf-8")
        self.fake.chmod(0o755)
        _base_repo(self.tmp)
        self.base = _git(self.tmp, "rev-parse", "HEAD")
        self.env = {
            "PFY_CBM_SHADOW_BIN": str(self.fake),
            "PFY_CBM_SHADOW_CACHE": str(self.cache),
            "PFY_CBM_SHADOW_LOG": str(self.log),
            "PFY_CBM_SHADOW_ROOT": str(self.tmp),
            "FAKE_STAMP": str(self.stamp),
            "FAKE_MODE": "json",
            "FAKE_JSON": '{"changed_files":[]}',
        }

    def tearDown(self) -> None:
        _kill_matching(str(self.fake), str(self.cache), self.head if hasattr(self, "head") else "")
        wt = self.cache / "wt"
        if wt.exists():
            subprocess.run(
                ["git", "-C", str(self.tmp), "worktree", "remove", "--force", str(wt)],
                capture_output=True,
                text=True,
            )
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _change_test(self) -> str:
        path = self.tmp / "tests" / "test_a.py"
        path.write_text("def test_a():\n    assert 1 == 1\n", encoding="utf-8")
        _commit_all(self.tmp, "edit test_a")
        self.head = _git(self.tmp, "rev-parse", "HEAD")
        return self.head

    def _run(self, extra: dict | None = None, args: list[str] | None = None, timeout: float = 60) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.update(self.env)
        if extra:
            env.update(extra)
        proc = subprocess.run(
            [sys.executable, str(SHADOW), *(args or ["--base", self.base, "--head", self.head])],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc

    def _records(self) -> list[dict]:
        if not self.log.is_file():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_detect_failure_logs_and_exits_0(self) -> None:
        self._change_test()
        started = time.monotonic()
        proc = self._run(extra={"FAKE_MODE": "fail"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertLess(time.monotonic() - started, 20)
        rows = self._records()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIn("detect failed", row["cbm_error"])
        self.assertIn("tests/test_a.py", row["test_select"])
        self.assertFalse(row["cbm_timeout"])
        stamp = self.stamp.read_text(encoding="utf-8")
        self.assertIn("detect_changes", stamp)
        self.assertIn("--scope tests", stamp)

    def test_detect_timeout_stays_under_the_sleep_and_exits_0(self) -> None:
        self._change_test()
        started = time.monotonic()
        proc = self._run(extra={"FAKE_MODE": "sleep", "PFY_CBM_SHADOW_TIMEOUT": "1"}, timeout=20)
        elapsed = time.monotonic() - started
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertLess(elapsed, 10, "timeout recovery waited on the 30s sleep")
        row = self._records()[0]
        self.assertTrue(row["cbm_timeout"])
        self.assertEqual(row["cbm_error"], "timeout")
        self.assertIn("tests/test_a.py", row["test_select"])

    def test_disagreement_logs_both_sets_and_report_names_them(self) -> None:
        self._change_test()
        payload = json.dumps(
            {
                "changed_files": ["tests/test_b.py", "pkg/x.py"],
                "impacted_symbols": [{"file": "tests/test_c.py", "is_test": True, "name": "test_c"}],
            }
        )
        proc = self._run(extra={"FAKE_JSON": payload})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        row = self._records()[0]
        self.assertEqual(row["only_in_test_select"], ["tests/test_a.py"])
        self.assertEqual(row["only_in_cbm"], ["tests/test_b.py", "tests/test_c.py"])
        self.assertNotIn("pkg/x.py", row["cbm"])
        self.assertIn("--scope tests", row["invocation"])
        report = self._run(args=["--report"])
        self.assertEqual(report.returncode, 0, report.stderr)
        self.assertIn("tests/test_b.py", report.stdout)
        self.assertIn("tests/test_c.py", report.stdout)
        self.assertIn("tests/test_a.py", report.stdout)

    def test_risky_path_logs_run_all(self) -> None:
        _write(self.tmp / "docs" / "secret-note.md", "secret note\n")
        _commit_all(self.tmp, "secret")
        self.head = _git(self.tmp, "rev-parse", "HEAD")
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        row = self._records()[0]
        self.assertTrue(row["run_all"])
        self.assertIn("risky", row["run_all_reason"])

    def test_disabled_flag_does_not_run_or_write(self) -> None:
        self._change_test()
        self.log.write_text('{"sentinel": true}\n', encoding="utf-8")
        proc = self._run(extra={"PFY_CBM_SHADOW": "0"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self.log.read_text(encoding="utf-8"), '{"sentinel": true}\n')
        self.assertFalse(self.stamp.exists())

    def test_missing_binary_is_one_log_line(self) -> None:
        self.head = self.base
        proc = self._run(extra={"PFY_CBM_SHADOW_BIN": str(self.tmp / "no-such-binary")})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        rows = self._records()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["cbm_error"], "binary missing")
        self.assertFalse((self.cache / "wt").exists())

    def test_gate_exit_is_unchanged_and_the_hook_returns_quickly(self) -> None:
        # If the launch sits before the orphan reaper, pregate kills the shadow
        # before it can log. The call has to be the last step of cleanup.
        text = PREGATE.read_text(encoding="utf-8")
        start = text.index("cleanup() {")
        end = text.index("\ntrap cleanup EXIT", start)
        body = text[start:end]
        self.assertLess(body.index("reap_recorded_orphans"), body.index("launch_cbm_shadow"))
        tail = [line.strip() for line in body.splitlines() if line.strip() and line.strip() != "}"]
        self.assertEqual(tail[-1], "launch_cbm_shadow || true")

        self._change_test()
        fn_start = text.index("launch_cbm_shadow() {")
        fn_end = text.index("\nreap_recorded_orphans()", fn_start)
        fn = text[fn_start:fn_end]
        script = self.tmp / "gate.sh"
        script.write_text(
            "set -euo pipefail\n"
            'eval "$LAUNCH_FN"\n'
            "trap 'launch_cbm_shadow || true' EXIT\n"
            'exit "$WANT"\n',
            encoding="utf-8",
        )
        env = os.environ.copy()
        env.update(self.env)
        env.update(
            {
                "FAKE_MODE": "sleep",
                "LAUNCH_FN": fn,
                "SCRIPT_DIR": str(ROOT / "scripts"),
                "BASE_SHA": self.base,
                "SHA": self.head,
            }
        )
        for want, label in (("0", "pass"), ("1", "fail")):
            env["WANT"] = want
            started = time.monotonic()
            proc = subprocess.run(
                ["bash", str(script)],
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )
            elapsed = time.monotonic() - started
            self.assertEqual(proc.returncode, int(want), f"{label} gate moved: {proc.stderr}")
            self.assertLess(elapsed, 2.0, f"{label} hook took {elapsed:.2f}s")

        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.stamp.exists() and "detect_changes" in self.stamp.read_text(encoding="utf-8"):
                break
            time.sleep(0.1)
        stamp = self.stamp.read_text(encoding="utf-8") if self.stamp.exists() else ""
        self.assertIn("detect_changes", stamp)
        quiet = time.monotonic() + 2
        while time.monotonic() < quiet:
            _kill_matching(str(self.fake), str(self.cache), self.head)
            if not _pids_with(str(self.fake)) and not _pids_with(self.head):
                break
            time.sleep(0.1)


if __name__ == "__main__":
    unittest.main()
