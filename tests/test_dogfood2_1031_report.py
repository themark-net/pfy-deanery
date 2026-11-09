"""The dogfood2 report matches its receipts, and a planted mismatch fails.

How this fails: a row's status, exit code, or review disagrees with
receipt.json, the median line disagrees with the walls, or a human-accept
PASS commit does not carry the Built-by trailer for that receipt.
How we recover: fix the report row or the trailer, then rerun the checker.
A shallow clone skips the real-tree audit when a referenced commit is
absent. The planted trailer mismatch builds its own git repo under TMPDIR.
The planted status mismatch stays under this worktree's tmp/.
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from tests._ops import OPS, require  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
CHECK = OPS / "eval" / "dogfood2-1031" / "check_reports.py"
DOGFOOD = OPS / "eval" / "dogfood2-1031"
SCRATCH = REPO / "tmp" / "dogfood2-check-tests"


def _run(root: Path, repo: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECK), str(root), str(repo or REPO)],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )


def _checker():
    spec = importlib.util.spec_from_file_location("dogfood2_check_reports", CHECK)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load %s" % CHECK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _shallow(repo: Path) -> bool:
    proc = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip() == "true"


def _missing_trailer_commits(repo: Path) -> list[str]:
    """PASS human-accept shas check_trailer looks up. Other rows are not commits."""
    rows = _checker().parse_runs_table((DOGFOOD / "REPORT.md").read_text(encoding="utf-8"))
    missing: list[str] = []
    for row in rows:
        if row["status"] != "PASS" or row["human"] != "yes":
            continue
        sha = row["commit"]
        probe = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "-e", "%s^{commit}" % sha],
            capture_output=True,
            text=True,
            check=False,
        )
        if probe.returncode != 0:
            missing.append(sha)
    return missing


def _git(repo: Path, args: list[str]) -> None:
    proc = subprocess.run(
        ["git", "-C", str(repo), "-c", "commit.gpgsign=false", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "git %s failed" % " ".join(args))


def setUpModule() -> None:
    require(CHECK)


class Dogfood2ReportTests(unittest.TestCase):
    def test_real_tree_matches_receipts_and_trailers(self) -> None:
        # A fetch-depth 1 clone does not have the build commits. Skip only
        # then. A full clone still runs, and a missing commit fails the checker.
        if _shallow(REPO):
            missing = _missing_trailer_commits(REPO)
            if missing:
                self.skipTest(
                    "shallow clone; referenced commit %s is not in this repo"
                    % ", ".join(missing)
                )
        proc = _run(DOGFOOD)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OK runs=9", proc.stdout)

    def test_planted_status_mismatch_fails(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            root = Path(raw)
            src = DOGFOOD / "06-daemon-stop-timeout" / "receipt.json"
            dest_dir = root / "06-daemon-stop-timeout"
            dest_dir.mkdir()
            payload = json.loads(src.read_text(encoding="utf-8"))
            payload["status"] = "FAIL"
            (dest_dir / "receipt.json").write_text(
                json.dumps(payload, indent=2) + "\n", encoding="utf-8"
            )
            report = (DOGFOOD / "REPORT.md").read_text(encoding="utf-8")
            # Keep the other rows out so this fixture is one run.
            kept = [
                line
                for line in report.splitlines()
                if not line.startswith("| 0") or line.startswith("| 06-")
            ]
            text = "\n".join(kept) + "\n"
            text = text.replace("- runs: 9\n", "- runs: 1\n")
            text = text.replace("- gate_pass_rate: 8/9\n", "- gate_pass_rate: 1/1\n")
            text = text.replace("- review_accept_rate: 8/9\n", "- review_accept_rate: 1/1\n")
            text = text.replace("- human_accept_rate: 8/9\n", "- human_accept_rate: 1/1\n")
            text = text.replace("- median_wall_s: 643\n", "- median_wall_s: 301\n")
            (root / "REPORT.md").write_text(text, encoding="utf-8")
            proc = _run(root)
            blob = proc.stdout + proc.stderr
            self.assertEqual(proc.returncode, 1, blob)
            self.assertIn("06-daemon-stop-timeout", proc.stderr)
            self.assertIn("status report=PASS receipt=FAIL", proc.stderr)
            self.assertNotIn("OK runs=", proc.stdout)

    def test_planted_trailer_mismatch_fails(self) -> None:
        scratch = Path(os.environ.get("TMPDIR") or tempfile.gettempdir())
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="dogfood2-trailer-", dir=scratch) as raw:
            repo = Path(raw)
            _git(repo, ["init", "-q"])
            _git(repo, ["config", "user.email", "dogfood2-test@example.com"])
            _git(repo, ["config", "user.name", "dogfood2-test"])
            (repo / "keep.txt").write_text("ok\n", encoding="utf-8")
            _git(repo, ["add", "keep.txt"])
            _git(repo, [
                "commit", "-q", "-m", "plant",
                "-m", "Built-by: ./pfy build (cloud) receipt other/receipt.json",
            ])
            sha = subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True,
            ).strip()
            name = "06-trailer-mismatch"
            dest = repo / name
            dest.mkdir()
            (dest / "receipt.json").write_text(
                json.dumps({
                    "status": "PASS",
                    "exit_code": 0,
                    "review": {"verdict": "accept"},
                }, indent=2) + "\n",
                encoding="utf-8",
            )
            report = "\n".join([
                "# planted",
                "",
                "## Runs",
                "",
                "| dir | status | exit_code | review | human | wall_s | commit | reason |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |",
                "| %s | PASS | 0 | accept | yes | 10 | %s | ok |" % (name, sha),
                "",
                "## Rates",
                "",
                "- runs: 1",
                "- gate_pass_rate: 1/1",
                "- review_accept_rate: 1/1",
                "- human_accept_rate: 1/1",
                "- median_wall_s: 10",
                "",
            ])
            (repo / "REPORT.md").write_text(report, encoding="utf-8")
            proc = _run(repo, repo)
            blob = proc.stdout + proc.stderr
            self.assertEqual(proc.returncode, 1, blob)
            self.assertIn(name, proc.stderr)
            self.assertIn("trailer", proc.stderr)
            self.assertNotIn("is not in the repo", proc.stderr)
            self.assertNotIn("OK runs=", proc.stdout)


if __name__ == "__main__":
    unittest.main()
