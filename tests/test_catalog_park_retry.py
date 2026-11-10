"""catalog_park_retry.py: re-open fixable parks once main is green, capped and backed off."""
from __future__ import annotations

import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "catalog_park_retry.py"
HOUR = 3600.0


def git(cwd, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True, env=env, timeout=60)


def make_repo(td: Path) -> Path:
    repo = td / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-q", "--allow-empty", "-m", "base")
    git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    return repo


def park(state: Path, slug: str, reason: str, age_h: float, now: float) -> Path:
    state.mkdir(parents=True, exist_ok=True)
    marker = state / f"{slug}.parked"
    marker.write_text(reason + "\n", encoding="utf-8")
    (state / f"{slug}.dispatched").write_text("pid 1\n", encoding="utf-8")
    t = now - age_h * HOUR
    os.utime(marker, (t, t))
    return marker


def run(repo: Path, state: Path, now: float, green: str = "1") -> list[str]:
    env = dict(os.environ, PFY_MAIN_GREEN=green)
    out = subprocess.run(
        ["python3", str(SCRIPT), "--repo", str(repo), "--dir", f"eval={state}", "--now", str(now)],
        capture_output=True, text=True, env=env, timeout=60,
    )
    assert out.returncode == 0, out.stderr
    return out.stdout.splitlines()


class ParkRetryTest(unittest.TestCase):
    def test_retry_cap_backoff_and_reasons(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            repo = make_repo(td)
            state = td / "loop" / "eval"
            now = time.time()
            park(state, "fixable", "run_tests failed", 3, now)
            park(state, "fresh", "run_tests failed", 1, now)
            park(state, "grok", "grok failed", 30, now)
            wt = state / "wt" / "fixable"
            git(repo, "worktree", "add", "-q", "-b", "bot/eval-fixable-0101", str(wt), "HEAD")
            lines = run(repo, state, now)
            self.assertEqual(lines, ["retry eval fixable 1", "hold eval fresh backoff", "hold eval grok not-retryable"])
            self.assertFalse((state / "fixable.parked").exists())
            self.assertTrue((state / "fixable.parked.1").is_file())
            self.assertFalse((state / "fixable.dispatched").exists())
            self.assertEqual((state / "fixable.retry-count").read_text(), "1\n")
            self.assertFalse(wt.exists())
            git(repo, "rev-parse", "--verify", "bot/eval-fixable-0101")  # branch and its commits stay
            self.assertTrue((state / "fresh.dispatched").exists())
            history = (td / "loop" / "park-history.tsv").read_text(encoding="utf-8").splitlines()
            self.assertEqual(history[0].split("\t"), ["slug", "kind", "reason", "parked_at", "retries", "main_sha"])
            self.assertEqual(sorted(r.split("\t")[0] for r in history[1:]), ["fixable", "fresh", "grok"])
            self.assertIn("run_tests failed", history[2] + history[1])

            # Second park of the same lane: backoff doubles, then the cap holds.
            park(state, "fixable", "run_tests failed", 3.5, now)
            self.assertIn("hold eval fixable backoff", run(repo, state, now))
            park(state, "fixable", "run_tests failed", 5, now)
            self.assertIn("retry eval fixable 2", run(repo, state, now))
            park(state, "fixable", "run_tests failed", 100, now)
            self.assertIn("hold eval fixable cap", run(repo, state, now))
            rows = (td / "loop" / "park-history.tsv").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len([r for r in rows if r.startswith("fixable\t")]), 4)
            again = run(repo, state, now)
            self.assertEqual((td / "loop" / "park-history.tsv").read_text(encoding="utf-8").splitlines(), rows)
            self.assertIn("hold eval fixable cap", again)

    def test_red_main_dirty_tree_and_todays_branch_hold(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            repo = make_repo(td)
            state = td / "loop" / "eval"
            now = time.time()
            park(state, "red", "run_tests failed", 3, now)
            self.assertEqual(run(repo, state, now, green="0"), ["hold eval red main-not-green"])
            self.assertTrue((state / "red.parked").exists())
            wt = state / "wt" / "red"
            git(repo, "worktree", "add", "-q", "-b", "bot/eval-red-0101", str(wt), "HEAD")
            (wt / "junk").write_text("x", encoding="utf-8")
            self.assertEqual(run(repo, state, now), ["hold eval red dirty-worktree"])
            (wt / "junk").unlink()
            today = time.strftime("%m%d", time.gmtime(now))
            git(repo, "branch", f"bot/eval-red-{today}")
            self.assertEqual(run(repo, state, now), ["hold eval red branch-exists"])
            self.assertTrue(wt.exists())

    def test_no_parks_no_network_and_bad_dir_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            repo = make_repo(td)
            env = {k: v for k, v in os.environ.items() if k != "PFY_MAIN_GREEN"}
            out = subprocess.run(["python3", str(SCRIPT), "--repo", str(repo), "--dir", f"eval={td / 'none'}"], capture_output=True, text=True, env=env, timeout=60)
            self.assertEqual((out.returncode, out.stdout), (0, ""))
            bad = subprocess.run(["python3", str(SCRIPT), "--repo", str(repo), "--dir", "evq=/tmp"], capture_output=True, text=True, timeout=60)
            self.assertEqual(bad.returncode, 2)


if __name__ == "__main__":
    unittest.main()
