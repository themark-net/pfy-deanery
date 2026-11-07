#!/usr/bin/env python3
"""Two cheap pregates on one host both PASS and keep separate roots.

How this fails: the second run deletes the first run's folder, both write
one summary, or one exits 2 because the worktree path already exists.
Recovery: each run's worktree, scratch, and summary include its pid.
Retention skips a folder whose trailing pid is still a pregate, and still
deletes a dead run that is past PREGATE_KEEP_RUNS.

State stays under /tmp via PREGATE_STATE_ROOT. The real checkout tmp is
not used. Worktrees are removed in tearDown.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREGATE = ROOT / "scripts" / "pregate.sh"
RUN_ID_RE = re.compile(r"- run id: `([^`]+)`")


def _short_state(tag: str) -> Path:
    # Worktree and scratch must stay within 60 characters. /tmp/pg<pid><tag>
    # plus /pg/<7hex>-<6digits>-<pid> fits. tempfile.mkdtemp does not.
    path = Path(f"/tmp/pg{os.getpid()}{tag}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir()
    return path


def _drop_worktrees(state: Path) -> None:
    listed = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    prefix = str(state) + "/"
    for line in listed.stdout.splitlines():
        if not line.startswith("worktree "):
            continue
        path = line.split(" ", 1)[1]
        if path == str(ROOT) or not path.startswith(prefix):
            continue
        subprocess.run(
            ["git", "-C", str(ROOT), "worktree", "remove", "--force", path],
            capture_output=True,
            text=True,
        )
    subprocess.run(
        ["git", "-C", str(ROOT), "worktree", "prune"],
        capture_output=True,
        text=True,
    )


class PregateConcurrentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.states: list[Path] = []
        self.sleepers: list[subprocess.Popen[str]] = []

    def tearDown(self) -> None:
        for proc in self.sleepers:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
        for state in self.states:
            _drop_worktrees(state)
            shutil.rmtree(state, ignore_errors=True)

    def _env(self, state: Path, keep: str) -> dict[str, str]:
        env = os.environ.copy()
        env["PREGATE_STATE_ROOT"] = str(state)
        env["PREGATE_KEEP_RUNS"] = keep
        env["PFY_TEST_CACHE"] = str(state / "cache")
        env.pop("GITHUB_ACTIONS", None)
        return env

    def _run(self, state: Path, only: str, keep: str) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [str(PREGATE), "--only", only, "HEAD"],
            cwd=ROOT,
            env=self._env(state, keep),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_two_cheap_runs_both_pass_on_separate_roots(self) -> None:
        state = _short_state("a")
        self.states.append(state)
        first = self._run(state, "lint,gate-hash", "20")
        second = self._run(state, "lint,gate-hash", "20")
        out1, err1 = first.communicate(timeout=300)
        out2, err2 = second.communicate(timeout=300)
        self.assertEqual(first.returncode, 0, out1 + err1)
        self.assertEqual(second.returncode, 0, out2 + err2)
        self.assertIn("OVERALL=PASS", out1)
        self.assertIn("OVERALL=PASS", out2)
        self.assertNotEqual(first.pid, second.pid)

        summaries = sorted((state / "pregate-runs").glob("*/pregate-summary.md"))
        self.assertEqual(len(summaries), 2, [str(p) for p in summaries])
        ids: list[str] = []
        for path in summaries:
            text = path.read_text(encoding="utf-8")
            self.assertIn("overall: **PASS**", text)
            found = RUN_ID_RE.search(text)
            self.assertIsNotNone(found, text)
            ids.append(found.group(1))
            self.assertTrue(str(path).startswith(str(state / "pregate-runs")))
        self.assertEqual(len(set(ids)), 2, ids)
        self.assertTrue(any(item.endswith(f"-{first.pid}") for item in ids), ids)
        self.assertTrue(any(item.endswith(f"-{second.pid}") for item in ids), ids)
        self.assertFalse((state / "pregate-latest-summary.md").exists())
        self.assertEqual(len({path.parent for path in summaries}), 2)

    def test_retention_keeps_a_live_pregate_and_drops_a_dead_run(self) -> None:
        state = _short_state("b")
        self.states.append(state)
        sleeper = subprocess.Popen(
            ["bash", "-c", "exec -a scripts/pregate.sh sleep 120"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        self.sleepers.append(sleeper)
        deadline = time.monotonic() + 5
        cmdline = ""
        while time.monotonic() < deadline:
            try:
                raw = Path(f"/proc/{sleeper.pid}/cmdline").read_bytes()
            except OSError:
                raw = b""
            cmdline = raw.replace(b"\0", b" ").decode("utf-8", "replace")
            if "pregate.sh" in cmdline:
                break
            time.sleep(0.05)
        self.assertIn("pregate.sh", cmdline, cmdline)

        dead = subprocess.Popen(["true"])
        dead.wait(timeout=5)
        runs = state / "pregate-runs"
        runs.mkdir()
        live = runs / f"abc1234-20200101T000000Z-{sleeper.pid}"
        gone = runs / f"abc1235-20200101T000001Z-{dead.pid}"
        live.mkdir()
        gone.mkdir()
        (live / "marker").write_text("live", encoding="utf-8")
        (gone / "marker").write_text("dead", encoding="utf-8")
        old = time.time() - 7200
        os.utime(live, (old, old))
        os.utime(gone, (old, old))

        proc = self._run(state, "gate-hash", "1")
        out, err = proc.communicate(timeout=180)
        self.assertEqual(proc.returncode, 0, out + err)
        self.assertTrue((live / "marker").is_file(), "live pregate run was deleted")
        self.assertFalse(gone.exists(), "dead run was kept")
        summaries = list(runs.glob("*/pregate-summary.md"))
        self.assertEqual(len(summaries), 1, [str(p) for p in summaries])


if __name__ == "__main__":
    unittest.main()
