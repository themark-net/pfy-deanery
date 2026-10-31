"""Built-by trailers on this branch must point at a PASS receipt.

The commit subject is the runner's subject: the task text collapsed to one
line and cut at 72 characters. A planted trailer in a temp repo fails when
the receipt is missing, not PASS, or the subject does not match.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRAILER_PREFIX = "Built-by: ./pfy build (cloud) receipt "


def expected_subject(task: str) -> str:
    collapsed = " ".join((task or "").split())
    return collapsed[:72] or "task"


def _git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def built_by_problems(repo: Path) -> list[str]:
    """Empty means every Built-by commit on HEAD points at a matching PASS receipt."""
    listed = _git(repo, ["log", "--format=%H", "--grep", TRAILER_PREFIX])
    if listed.returncode != 0:
        return ["git log failed: %s" % (listed.stderr or "").strip()]
    problems: list[str] = []
    for sha in (listed.stdout or "").split():
        shown = _git(repo, ["log", "-1", "--format=%B", sha])
        message = shown.stdout or ""
        rel = ""
        for line in message.splitlines():
            if line.startswith(TRAILER_PREFIX):
                rel = line[len(TRAILER_PREFIX) :].strip()
                break
        if not rel or rel.startswith("/") or ".." in Path(rel).parts:
            problems.append("%s trailer path is missing or unsafe" % sha[:12])
            continue
        path = repo / rel
        if not path.is_file():
            problems.append("%s receipt missing: %s" % (sha[:12], rel))
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            problems.append("%s receipt unreadable: %s" % (sha[:12], exc))
            continue
        if data.get("status") != "PASS":
            problems.append("%s receipt status is %s" % (sha[:12], data.get("status")))
            continue
        subject = message.splitlines()[0].strip() if message.splitlines() else ""
        want = expected_subject(str(data.get("task") or ""))
        if subject != want:
            problems.append("%s subject %r != receipt task %r" % (sha[:12], subject, want))
    return problems


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    _git(path, ["config", "user.email", "selfhost-test@example.com"])
    _git(path, ["config", "user.name", "selfhost-test"])


def _commit(repo: Path, message: str) -> None:
    (repo / "keep.txt").write_text("ok\n", encoding="utf-8")
    _git(repo, ["add", "keep.txt"])
    proc = _git(repo, ["commit", "-q", "-m", message])
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)


class SelfhostBuiltByTests(unittest.TestCase):
    def test_this_branch_has_no_bad_built_by_trailer(self) -> None:
        problems = built_by_problems(ROOT)
        self.assertEqual(problems, [], "\n".join(problems))

    def test_planted_bad_trailer_fails_and_a_pass_receipt_matches(self) -> None:
        scratch = ROOT / "tmp" / "selfhost-1031-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="built-by-", dir=scratch) as td:
            repo = Path(td)
            _init_repo(repo)
            rel = "eval/selfhost-1031/bad/receipt.json"
            receipt = repo / rel
            receipt.parent.mkdir(parents=True)
            receipt.write_text(
                json.dumps({"status": "FAIL", "task": "Refuse a relative receipt dir"}) + "\n",
                encoding="utf-8",
            )
            _git(repo, ["add", rel])
            bad = "Refuse a relative receipt dir\n\n%s%s\n" % (TRAILER_PREFIX, rel)
            proc = _git(repo, ["commit", "-q", "-m", bad])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            problems = built_by_problems(repo)
            self.assertTrue(any("status" in item for item in problems), problems)

            receipt.write_text(
                json.dumps({"status": "PASS", "task": "Refuse a relative receipt dir now"}) + "\n",
                encoding="utf-8",
            )
            mismatch = "Some other subject\n\n%s%s\n" % (TRAILER_PREFIX, rel)
            _commit_message_only = _git(repo, ["commit", "-q", "--allow-empty", "-m", mismatch])
            self.assertEqual(_commit_message_only.returncode, 0, _commit_message_only.stderr)
            problems = built_by_problems(repo)
            self.assertTrue(any("subject" in item for item in problems), problems)

            good_task = "Refuse a relative receipt dir now"
            good = "%s\n\n%s%s\n" % (expected_subject(good_task), TRAILER_PREFIX, rel)
            # Replace history of the bad commits with one good commit so the
            # checker sees only the matching PASS trailer.
            shutil.rmtree(repo / ".git")
            _init_repo(repo)
            receipt.parent.mkdir(parents=True, exist_ok=True)
            receipt.write_text(
                json.dumps({"status": "PASS", "task": good_task}) + "\n",
                encoding="utf-8",
            )
            _git(repo, ["add", rel])
            proc = _git(repo, ["commit", "-q", "-m", good])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(built_by_problems(repo), [])

            os.remove(receipt)
            missing = built_by_problems(repo)
            self.assertTrue(any("missing" in item for item in missing), missing)


if __name__ == "__main__":
    unittest.main()
