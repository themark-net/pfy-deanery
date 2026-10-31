"""Kills cloud-runner mutants the existing suite left alive.

C4 treats a review reply with no verdict line as accept and would commit.
C10 signals pgids from the local pid file. A zombie still answers kill(pid, 0),
so the check is poll(): None means the local process is still running.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / "tmp" / "mut-cloud-tests"
CLOUD = ROOT / "scripts" / "pfy_build_cloud.py"


def _run(argv: list[str], cwd: Path, timeout: float = 60) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["TMPDIR"] = str(SCRATCH)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        argv,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return _run(["git", *args], repo)


def _write_exe(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    init = _git(path, "init", "-b", "main")
    if init.returncode != 0:
        raise RuntimeError(init.stderr)
    _git(path, "config", "user.email", "mut-cloud@example.com")
    _git(path, "config", "user.name", "mut-cloud")
    (path / "README.md").write_text("fixture\n", encoding="utf-8")
    (path / ".gitignore").write_text("tmp/\npipelines/dogfood/build-cloud/\n", encoding="utf-8")
    _git(path, "add", "README.md", ".gitignore")
    committed = _git(path, "commit", "-m", "init")
    if committed.returncode != 0:
        raise RuntimeError(committed.stderr)
    return path


def _stop(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        os.kill(proc.pid, signal.SIGKILL)
    except OSError:
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass


class SurvivorTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.repo = _init_repo(SCRATCH / self.id().replace(".", "_"))
        self.side = SCRATCH / (self.id().replace(".", "_") + "-side")
        self.side.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self.repo, ignore_errors=True)
        shutil.rmtree(self.side, ignore_errors=True)

    def test_missing_review_verdict_is_rejected_and_not_committed(self) -> None:
        gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n",
        )
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('looks fine')\n"
            "    raise SystemExit(0)\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        proc = _run(
            [
                sys.executable,
                str(CLOUD),
                "add kept value",
                "--repo",
                str(self.repo),
                "--retries",
                "0",
                "--timeout",
                "30",
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(grok),
            ],
            self.repo,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        self.assertNotIn("PASS ok", proc.stdout or "")
        receipt = list((self.repo / "pipelines" / "dogfood" / "build-cloud").glob("*/receipt.json"))
        self.assertEqual(len(receipt), 1, text)
        payload = json.loads(receipt[0].read_text(encoding="utf-8"))
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(payload["reason"], "review-rejected")
        self.assertEqual(payload["review"]["verdict"], "reject")
        self.assertIn("review-unparseable", payload["review"]["reasons"])
        self.assertIsNone(payload["commit"])
        self.assertIsNone(payload["branch"])
        self.assertFalse(payload["pushed"])
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)
        self.assertNotIn("kept.py", _git(self.repo, "ls-tree", "-r", "--name-only", "HEAD").stdout)

    def test_reap_does_not_signal_the_local_pid_file(self) -> None:
        local = subprocess.Popen(["sleep", "30"], start_new_session=True)
        self.addCleanup(_stop, local)
        local_pids = self.repo / "tmp" / "local-build.pids.json"
        local_pids.parent.mkdir(parents=True, exist_ok=True)
        local_pids.write_text(
            json.dumps(
                {
                    "pid": local.pid,
                    "pgid": os.getpgid(local.pid),
                    "agent_pgid": os.getpgid(local.pid),
                }
            ),
            encoding="utf-8",
        )
        before = local_pids.read_bytes()
        proc = _run(
            [sys.executable, str(CLOUD), "--reap", "--repo", str(self.repo)],
            self.repo,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        self.assertIsNone(local.poll(), text)
        self.assertEqual(local_pids.read_bytes(), before)
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)


if __name__ == "__main__":
    unittest.main()
