#!/usr/bin/env python3
"""Behavior tests for eval/mvp-1031/rerun_local.py. No local model."""
from __future__ import annotations

import importlib.util
import io
import json
import os
import signal
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "eval" / "mvp-1031" / "rerun_local.py"
SCRATCH = ROOT / "tmp" / "scratch"
SCRATCH.mkdir(parents=True, exist_ok=True)
os.environ["TMPDIR"] = str(SCRATCH)

spec = importlib.util.spec_from_file_location("rerun_local", SCRIPT)
rerun_local = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(rerun_local)


def _git(cwd: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout)
    return proc.stdout.strip()


def make_repo(path: Path, ignored_name: str | None) -> str:
    path.mkdir(parents=True)
    subprocess.check_call(["git", "init", "-q"], cwd=str(path))
    (path / "README").write_text("ok\n", encoding="utf-8")
    if ignored_name:
        (path / ".gitignore").write_text(ignored_name + "\n", encoding="utf-8")
        (path / ignored_name).write_text("secret-looking-but-not\n", encoding="utf-8")
    _git(path, ["add", "-A", "-f"])
    _git(
        path,
        [
            "-c",
            "user.name=rerun-test",
            "-c",
            "user.email=rerun-test@localhost",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-qm",
            "init",
        ],
    )
    return _git(path, ["rev-parse", "HEAD"])


class RerunLocalTests(unittest.TestCase):
    def _clean_env(self, out: Path, extra: dict | None = None) -> dict:
        env = os.environ.copy()
        for key in list(env):
            if key.startswith("PFY_RERUN_"):
                env.pop(key)
        env["TMPDIR"] = str(SCRATCH)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PFY_RERUN_OUT"] = str(out)
        env["PFY_RERUN_SKIP_HOST"] = "1"
        if extra:
            env.update(extra)
        return env

    def _ollama_trap(self, folder: Path, env: dict) -> Path:
        bindir = folder / "bin"
        bindir.mkdir()
        marker = folder / "ollama-called"
        script = bindir / "ollama"
        script.write_text(
            "#!/bin/sh\necho called >> '%s'\nexit 0\n" % marker,
            encoding="utf-8",
        )
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
        return marker

    def _write_stub(self, folder: Path, cfg: dict) -> Path:
        stub = folder / "stub-pfy.py"
        (folder / "stub_config.json").write_text(json.dumps(cfg), encoding="utf-8")
        stub.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json, os, sys, time
                from pathlib import Path
                here = Path(__file__).resolve().parent
                cfg = json.loads((here / "stub_config.json").read_text())
                (here / "argv.json").write_text(json.dumps(sys.argv))
                (here / "stub.pid").write_text(str(os.getpid()))
                receipt = None
                args = sys.argv
                for i, arg in enumerate(args):
                    if arg == "--receipt-dir" and i + 1 < len(args):
                        receipt = Path(args[i + 1])
                if receipt is not None:
                    receipt.mkdir(parents=True, exist_ok=True)
                    (receipt / "receipt.json").write_text(json.dumps({
                        "status": cfg.get("status", "PASS"),
                        "reason": cfg.get("reason", "ok"),
                        "commit": cfg.get("commit"),
                        "worktree": cfg.get("worktree"),
                    }) + "\\n")
                time.sleep(float(cfg.get("sleep") or 0))
                raise SystemExit(int(cfg.get("exit", 0)))
                """
            ),
            encoding="utf-8",
        )
        stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
        return stub

    def _run(self, args: list[str], env: dict, lock: Path | None = None, timeout: float = 20) -> subprocess.CompletedProcess[str]:
        cmd = [sys.executable, str(SCRIPT), *args]
        if lock is not None:
            lock.parent.mkdir(parents=True, exist_ok=True)
            lock.write_text("", encoding="utf-8")
            env = dict(env)
            env["PFY_RERUN_LOCK"] = str(lock)
            cmd = ["flock", str(lock), *cmd]
        return subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )

    def test_no_task_exits_2_and_does_not_call_ollama(self) -> None:
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            folder = Path(raw)
            env = self._clean_env(folder / "out")
            marker = self._ollama_trap(folder, env)
            proc = self._run([], env)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertFalse(marker.exists())
            self.assertNotIn("11434", proc.stderr + proc.stdout)

    def test_unknown_task_exits_2_and_does_not_call_ollama(self) -> None:
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            folder = Path(raw)
            env = self._clean_env(folder / "out")
            marker = self._ollama_trap(folder, env)
            started = time.monotonic()
            proc = self._run(["not-a-task"], env, timeout=3)
            self.assertLess(time.monotonic() - started, 3)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertIn("unknown task", proc.stderr)
            self.assertFalse(marker.exists())

    def test_known_task_without_flock_exits_2_and_does_not_spawn(self) -> None:
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            folder = Path(raw)
            env = self._clean_env(folder / "out")
            marker = self._ollama_trap(folder, env)
            stub = self._write_stub(folder, {"exit": 0})
            env["PFY_RERUN_PFY"] = str(stub)
            proc = self._run(["t5-receipts-outside-repo"], env, timeout=3)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertIn("heavy-1030.lock", proc.stderr)
            self.assertIn("flock", proc.stderr)
            self.assertFalse((folder / "argv.json").exists())
            self.assertFalse(marker.exists())

    def test_t4_before_t5_exits_2_and_does_not_spawn(self) -> None:
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            folder = Path(raw)
            out = folder / "out"
            env = self._clean_env(out)
            stub = self._write_stub(folder, {"exit": 0})
            env["PFY_RERUN_PFY"] = str(stub)
            proc = self._run(
                ["t4-timeout-substep"],
                env,
                lock=folder / "lock",
            )
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertIn("t5 receipt is not recorded", proc.stderr)
            self.assertFalse((folder / "argv.json").exists())

    def test_gitignored_path_fails_the_rerun(self) -> None:
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            folder = Path(raw)
            repo = folder / "repo"
            sha = make_repo(repo, "secret.txt")
            out = folder / "out"
            env = self._clean_env(out)
            stub = self._write_stub(
                folder,
                {"exit": 0, "status": "PASS", "reason": "ok", "commit": sha, "worktree": str(repo)},
            )
            env["PFY_RERUN_PFY"] = str(stub)
            env["PFY_RERUN_REPO"] = str(repo)
            env["PFY_RERUN_BASE"] = sha
            proc = self._run(["t5-receipts-outside-repo"], env, lock=folder / "lock")
            self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
            note = (out / "NOTE.md").read_text(encoding="utf-8")
            self.assertIn("Gitignored path in the commit: yes", note)
            self.assertIn("secret.txt", note)
            self.assertIn("Exit code: 1", note)
            self.assertIn("Runner exit code: 0", note)
            self.assertIn("receipt.json", note)
            self.assertIn("Rerun: failed", note)
            argv = json.loads((folder / "argv.json").read_text(encoding="utf-8"))
            self.assertIn("--local", argv)
            self.assertIn("--review", argv)
            self.assertNotIn("--no-review", argv)
            self.assertEqual(argv[argv.index("--retries") + 1], "2")
            self.assertEqual(argv[argv.index("--model") + 1], "qwen3.6:35b")
            self.assertTrue(any(part.endswith("t5-receipts-outside-repo.md") for part in argv))

    def test_parent_gitignored_file_does_not_fail_the_child_commit(self) -> None:
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            folder = Path(raw)
            repo = folder / "repo"
            first = make_repo(repo, "secret.txt")
            self.assertIn("secret.txt", rerun_local.gitignored_in_commit(repo, first))
            (repo / "README").write_text("changed\n", encoding="utf-8")
            _git(repo, ["add", "--", "README"])
            _git(
                repo,
                [
                    "-c",
                    "user.name=rerun-test",
                    "-c",
                    "user.email=rerun-test@localhost",
                    "-c",
                    "commit.gpgsign=false",
                    "commit",
                    "-qm",
                    "readme only",
                ],
            )
            second = _git(repo, ["rev-parse", "HEAD"])
            self.assertEqual(rerun_local.gitignored_in_commit(repo, second), [])

    def test_clean_commit_copies_receipt_and_records_no(self) -> None:
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            folder = Path(raw)
            repo = folder / "repo"
            sha = make_repo(repo, None)
            out = folder / "out"
            env = self._clean_env(out)
            stub = self._write_stub(
                folder,
                {"exit": 0, "status": "PASS", "reason": "ok", "commit": sha, "worktree": str(repo)},
            )
            env["PFY_RERUN_PFY"] = str(stub)
            env["PFY_RERUN_REPO"] = str(repo)
            env["PFY_RERUN_BASE"] = sha
            proc = self._run(["t5-receipts-outside-repo"], env, lock=folder / "lock")
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            receipt = out / "t5-receipts-outside-repo" / "receipt.json"
            self.assertTrue(receipt.is_file())
            body = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(body["commit"], sha)
            note = (out / "NOTE.md").read_text(encoding="utf-8")
            self.assertIn("Gitignored path in the commit: no", note)
            self.assertIn("Exit code: 0", note)
            self.assertIn("Gate: PASS ok", note)
            self.assertIn(str(receipt.name), note)

    def test_runner_failure_records_exit_and_no_ignored_path(self) -> None:
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            folder = Path(raw)
            repo = folder / "repo"
            sha = make_repo(repo, None)
            out = folder / "out"
            env = self._clean_env(out)
            stub = self._write_stub(
                folder,
                {"exit": 1, "status": "FAIL", "reason": "tests-failed", "commit": None, "worktree": str(repo)},
            )
            env["PFY_RERUN_PFY"] = str(stub)
            env["PFY_RERUN_REPO"] = str(repo)
            env["PFY_RERUN_BASE"] = sha
            proc = self._run(["t5-receipts-outside-repo"], env, lock=folder / "lock")
            self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
            note = (out / "NOTE.md").read_text(encoding="utf-8")
            self.assertIn("Exit code: 1", note)
            self.assertIn("Gate: FAIL tests-failed", note)
            self.assertIn("Gitignored path in the commit: no", note)
            self.assertIn("Commit: none", note)
            self.assertIn("Rerun: failed", note)

    def test_t4_after_t5_keeps_both_sections(self) -> None:
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            folder = Path(raw)
            repo = folder / "repo"
            sha = make_repo(repo, None)
            out = folder / "out"
            t5_dir = out / "t5-receipts-outside-repo"
            t5_dir.mkdir(parents=True)
            (t5_dir / "receipt.json").write_text("{}\n", encoding="utf-8")
            (out / "NOTE.md").write_text(
                "# Local rerun\n\n## t5-receipts-outside-repo\n\nReceipt: kept\nExit code: 0\n",
                encoding="utf-8",
            )
            env = self._clean_env(out)
            stub = self._write_stub(
                folder,
                {"exit": 0, "status": "FAIL", "reason": "no-change", "commit": None, "worktree": str(repo)},
            )
            env["PFY_RERUN_PFY"] = str(stub)
            env["PFY_RERUN_REPO"] = str(repo)
            env["PFY_RERUN_BASE"] = sha
            proc = self._run(["t4-timeout-substep"], env, lock=folder / "lock")
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            note = (out / "NOTE.md").read_text(encoding="utf-8")
            self.assertIn("## t5-receipts-outside-repo", note)
            self.assertIn("Receipt: kept", note)
            self.assertIn("## t4-timeout-substep", note)
            self.assertIn("Gate: FAIL no-change", note)
            argv = json.loads((folder / "argv.json").read_text(encoding="utf-8"))
            self.assertTrue(any(part.endswith("t4-timeout-substep.md") for part in argv))
            self.assertIn("--writable-test", argv)
            self.assertIn("tests/test_x_intake_smoke_112_114.py", argv)

    def test_host_busy_does_not_spawn(self) -> None:
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            folder = Path(raw)
            lock = folder / "lock"
            lock.write_text("", encoding="utf-8")
            fd = os.open(str(lock), os.O_RDWR)
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX)
            old_term = signal.getsignal(signal.SIGTERM)
            old_int = signal.getsignal(signal.SIGINT)
            old_env = {
                key: os.environ.get(key)
                for key in ("PFY_RERUN_LOCK", "PFY_RERUN_OUT", "PFY_RERUN_SKIP_HOST")
            }
            os.environ["PFY_RERUN_LOCK"] = str(lock)
            os.environ["PFY_RERUN_OUT"] = str(folder / "out")
            os.environ.pop("PFY_RERUN_SKIP_HOST", None)

            def busy() -> str:
                return "host busy"

            def explode(*_args, **_kwargs):
                raise AssertionError("spawned while host busy")

            original_host = rerun_local.host_block
            original_spawn = rerun_local.spawn_runner
            original_plant = rerun_local.plant
            rerun_local.host_block = busy
            rerun_local.spawn_runner = explode
            rerun_local.plant = explode
            try:
                buf = io.StringIO()
                with redirect_stderr(buf):
                    code = rerun_local.main(["t5-receipts-outside-repo"])
            finally:
                rerun_local.host_block = original_host
                rerun_local.spawn_runner = original_spawn
                rerun_local.plant = original_plant
                signal.signal(signal.SIGTERM, old_term)
                signal.signal(signal.SIGINT, old_int)
                for key, value in old_env.items():
                    if value is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = value
                os.close(fd)
            self.assertEqual(code, 4)
            self.assertIn("host busy", buf.getvalue())

    def test_missing_runner_records_failure_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            folder = Path(raw)
            repo = folder / "repo"
            sha = make_repo(repo, None)
            out = folder / "out"
            env = self._clean_env(out)
            env["PFY_RERUN_PFY"] = str(folder / "missing-pfy")
            env["PFY_RERUN_REPO"] = str(repo)
            env["PFY_RERUN_BASE"] = sha
            proc = self._run(["t5-receipts-outside-repo"], env, lock=folder / "lock")
            self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
            self.assertNotIn("Traceback", proc.stderr)
            self.assertIn("runner failed to start", proc.stderr)
            note = (out / "NOTE.md").read_text(encoding="utf-8")
            self.assertIn("Exit code: 1", note)
            self.assertIn("Gitignored path in the commit: no", note)
            self.assertIn("Commit: none", note)

    def test_sigterm_stops_the_child(self) -> None:
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            folder = Path(raw)
            repo = folder / "repo"
            sha = make_repo(repo, None)
            out = folder / "out"
            env = self._clean_env(out)
            stub = self._write_stub(folder, {"exit": 0, "sleep": 30, "commit": None, "worktree": str(repo)})
            env["PFY_RERUN_PFY"] = str(stub)
            env["PFY_RERUN_REPO"] = str(repo)
            env["PFY_RERUN_BASE"] = sha
            lock = folder / "lock"
            lock.write_text("", encoding="utf-8")
            env["PFY_RERUN_LOCK"] = str(lock)
            proc = subprocess.Popen(
                ["flock", str(lock), sys.executable, str(SCRIPT), "t5-receipts-outside-repo"],
                cwd=str(ROOT),
                env=env,
                start_new_session=True,
            )
            try:
                self._assert_sigterm_stops(proc, folder)
            finally:
                if proc.poll() is None:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except OSError:
                        pass
                    proc.wait(timeout=5)

    def _assert_sigterm_stops(self, proc: subprocess.Popen, folder: Path) -> None:
        child = None
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and child is None:
            try:
                comm = Path("/proc/%s/comm" % proc.pid).read_text(encoding="utf-8").strip()
            except OSError:
                comm = ""
            if comm.startswith("python"):
                child = proc.pid
                break
            kids_path = Path("/proc/%s/task/%s/children" % (proc.pid, proc.pid))
            try:
                kids = kids_path.read_text(encoding="utf-8").split()
            except OSError:
                kids = []
            if kids:
                child = int(kids[0])
                break
            time.sleep(0.05)
        self.assertIsNotNone(child, "script did not start")
        stub_pid = None
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and stub_pid is None:
            pid_file = folder / "stub.pid"
            if pid_file.is_file():
                stub_pid = int(pid_file.read_text(encoding="utf-8").strip())
                break
            time.sleep(0.05)
        self.assertIsNotNone(stub_pid, "stub did not start")
        os.kill(child, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            self.fail("script did not exit on SIGTERM")
        self.assertNotEqual(proc.returncode, 0)
        with self.assertRaises(ProcessLookupError):
            os.kill(stub_pid, 0)


if __name__ == "__main__":
    unittest.main()
