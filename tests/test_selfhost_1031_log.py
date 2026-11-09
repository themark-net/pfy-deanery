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

# bot/mvp-selfhost2-1031 cherry-picked each cloud build with a readable
# subject, as its drop-in asked. Their receipts are PASS. Only the subject
# check is skipped for these exact commits, and only while the commit's
# `git patch-id --stable` equals the receipt commit's, recorded here (S1).
# Recorded in the private ops handoff for the mvp-land-1031 lane.
REWORDED_PATCH_IDS = {
    "4a0fe4eeebd2": "a8f753bf6787ebd6a549ae5e87955c9b244363b2",
    "cdf4d681c19c": "e20e3149f2c812c58c5909303b6e62cf75faf588",
    "36bc071c3e82": "7b440a5182510475a22ea846f8f86c6b11240e92",
    "ae5e5e5e7459": "95fd165c5326d0bf053a5ee8d67a681c10d7283b",
    "91386568b3c5": "3730685bb7410c1147ca49dd73f137bf7e89f164",
    "1faa9fd7e80b": "7f3a790fdc403cd739acf16af5c4798e5dbf5ea6",
    "e6339ca3c6de": "bfc57e5324a7f3fe383cad013bef11ebf44bf9ef",
    "67e3333a76c3": "0e6f4ce86700748862329d36452ce865f6999dc4",
    "d217349f1acc": "753d397bf8510701d92480e5d1d77d0c077f1b3b",
    "3eeab428e879": "1726ad83ff6e833cafe0c724c47a9f70ef1e8404",
}
TRAILER_PREFIX = "Built-by: ./pfy build (cloud) receipt "


def expected_subject(task: str) -> str:
    """Runner subject: collapsed task, cut at 72, trailing space removed.

    git stores the subject without a trailing space when the cut lands on
    the space between words. The comparison uses that stored subject.
    """
    collapsed = " ".join((task or "").split())
    return (collapsed[:72] or "task").rstrip()


def runner_subject(task: str) -> str:
    """Current runner subject (scripts/pfy_build_cloud.py commit_subject).

    Whole words, at most 72 characters, with "..." when cut. Kept in step
    with the runner by test_runner_subject_matches_the_cloud_runner.
    """
    flat = " ".join((task or "").split())
    if not flat:
        return "task"
    if len(flat) <= 72:
        return flat
    cut = flat[:69]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    cut = cut.rstrip() or flat[:69].rstrip()
    return (cut or "task") + "..."


def _git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
    )


def stable_patch_id(repo: Path, sha: str) -> str:
    """`git show <sha> | git patch-id --stable`, or "" when git fails."""
    shown = subprocess.run(
        ["git", "-C", str(repo), "show", "--format=", sha], check=False, capture_output=True
    )
    if shown.returncode != 0:
        return ""
    pid = subprocess.run(
        ["git", "-C", str(repo), "patch-id", "--stable"],
        input=shown.stdout,
        check=False,
        capture_output=True,
    )
    out = (pid.stdout or b"").decode("ascii", "replace").split()
    return out[0] if out else ""


def built_by_problems(repo: Path, reworded: dict[str, str] | None = None) -> list[str]:
    """Empty means every Built-by commit on HEAD points at a matching PASS receipt."""
    listed = _git(repo, ["log", "--format=%H", "--grep", TRAILER_PREFIX])
    if listed.returncode != 0:
        return ["git log failed: %s" % (listed.stderr or "").strip()]
    allow = REWORDED_PATCH_IDS if reworded is None else reworded
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
        if sha[:12] in allow:
            got = stable_patch_id(repo, sha)
            if got != allow[sha[:12]]:
                problems.append(
                    "%s patch-id %s != recorded %s" % (sha[:12], got or "unknown", allow[sha[:12]])
                )
            continue
        task = str(data.get("task") or "")
        want = expected_subject(task)
        if subject not in (want, runner_subject(task)):
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

    def test_runner_subject_matches_the_cloud_runner(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "pfy_build_cloud_subject", ROOT / "scripts" / "pfy_build_cloud.py"
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
        long_task = "Edit only examples/x-intake-local/smoke_106_108.py. Do not edit any file under tests/."
        for task in ("", "short task", "x" * 80, long_task, "word " * 30):
            self.assertEqual(runner_subject(task), mod.commit_subject(task), task)
        self.assertTrue(runner_subject(long_task).endswith("any..."))

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

    def test_reworded_commit_must_keep_its_recorded_patch_id(self) -> None:
        # S1: the subject skip holds only while the diff is the one the
        # receipt built. A rebase that changes the diff changes the patch-id.
        scratch = ROOT / "tmp" / "selfhost-1031-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="patch-id-", dir=scratch) as td:
            repo = Path(td)
            _init_repo(repo)
            rel = "eval/selfhost-1031/ok/receipt.json"
            receipt = repo / rel
            receipt.parent.mkdir(parents=True)
            receipt.write_text(json.dumps({"status": "PASS", "task": "runner subject"}) + "\n", encoding="utf-8")
            _git(repo, ["add", rel])
            msg = "A readable reworded subject\n\n%s%s\n" % (TRAILER_PREFIX, rel)
            proc = _git(repo, ["commit", "-q", "-m", msg])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            sha = _git(repo, ["rev-parse", "HEAD"]).stdout.strip()
            real = stable_patch_id(repo, sha)
            self.assertRegex(real, r"^[0-9a-f]{40}$")
            self.assertEqual(built_by_problems(repo, {sha[:12]: real}), [])
            wrong = built_by_problems(repo, {sha[:12]: "0" * 40})
            self.assertTrue(any("patch-id" in item for item in wrong), wrong)
            # Not on the allowlist: the subject check runs and fails.
            plain = built_by_problems(repo, {})
            self.assertTrue(any("subject" in item for item in plain), plain)

    def test_allowlist_patch_ids_are_full_stable_ids(self) -> None:
        self.assertEqual(len(REWORDED_PATCH_IDS), 10)
        for sha, pid in REWORDED_PATCH_IDS.items():
            self.assertRegex(sha, r"^[0-9a-f]{12}$")
            self.assertRegex(pid, r"^[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
