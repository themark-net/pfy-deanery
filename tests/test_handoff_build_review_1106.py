"""The build-review handoff names the cap env var and the trial impact source.

How this fails: the note is missing, so a bot never learns
PFY_REVIEW_FILE_CAP, or the note names a catalog tool as the source when
the 2026-11-06 trial recorded git-grep. A cited SHA that is not the
landed commit sends the bot to the wrong change. An em dash, or an empty
Still open, hides the timed-out trial. The receipt stores wall_seconds
10802.404 and worktree_removed false, and it does not store flags. A note
that only says "longer than the default" sends the next run back through
1200 or through the same 3600 that already fired (3600 times 3 attempts
is 10800s). A note that omits --keep-worktree makes that leftover
directory look like a removal failure.
Recover: write docs/HANDOFF-build-review-1106.md from the receipt, cite
the git SHAs, name --timeout 3600 and --keep-worktree, and point the
headless note at it. ASCII hyphens only. A shallow checkout has no
history, so the SHA check skips there.
"""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "docs" / "HANDOFF-build-review-1106.md"
PRIOR = ROOT / "docs" / "HANDOFF-headless-1105.md"

# The trial receipt recorded this source. The cap is the env var ./pfy build
# --help advertises. They are the ticket, not a copy of the doc.
CAP_ENV = "PFY_REVIEW_FILE_CAP"
IMPACT_SOURCE = "git-grep"

LANDED = (
    "Review cloud builds one file at a time.",
    "Put cloud build worktrees on a short path and allow ordinary test edits.",
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _shallow() -> bool:
    proc = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip() == "true"


def _commit(subject: str) -> str:
    log = subprocess.check_output(
        ["git", "log", "--format=%H%x09%s"],
        cwd=ROOT,
        text=True,
    )
    hits = [line.split("\t", 1)[0] for line in log.splitlines() if line.endswith("\t" + subject)]
    if len(hits) != 1:
        raise AssertionError("expected one commit for %r, found %s" % (subject, hits))
    return hits[0]


def _still_open(text: str) -> list[str]:
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == "## Still open":
            start = index + 1
            break
    if start is None:
        return []
    bullets = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if line.startswith("- "):
            bullets.append(line)
    return bullets


class BuildReviewHandoffTests(unittest.TestCase):
    def test_note_names_cap_env_and_impact_source(self):
        self.assertTrue(HANDOFF.is_file(), "docs/HANDOFF-build-review-1106.md is missing")
        note = _text(HANDOFF)
        self.assertIn(CAP_ENV, note, "handoff dropped the cap env var")
        self.assertIn(IMPACT_SOURCE, note, "handoff dropped the trial impact source")
        self.assertIn("10802.404", note, "handoff dropped the receipt wall_seconds")
        self.assertIn("wall_s=10803", note, "handoff dropped the trial.meta wall")
        self.assertIn("| commit | null |", note, "handoff dropped the null commit")
        self.assertIn("| branch | null |", note, "handoff dropped the null branch")
        self.assertIn("codebase-memory-mcp", note, "handoff dropped the preferred catalog tool")
        self.assertIn("tree-sitter-analyzer", note, "handoff dropped the Tree-sitter Analyzer source id")
        self.assertNotIn("\u2014", note, "em dash in the handoff")
        self.assertNotIn("\u2013", note, "en dash in the handoff")
        bullets = _still_open(note)
        self.assertGreaterEqual(len(bullets), 1, "Still open has no items")
        self.assertIn("TIMEOUT", "\n".join(bullets), "Still open dropped the timed-out trial")
        prior = _text(PRIOR)
        self.assertIn(HANDOFF.name, prior, "headless note does not point at the build-review handoff")
        proc = subprocess.run(
            [str(ROOT / "pfy"), "build", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        help_text = proc.stdout
        self.assertIn(CAP_ENV, help_text, "CLI help no longer names the cap env var")
        self.assertIn("--review-file-cap", help_text)
        self.assertIn("--review-file-cap", note, "handoff dropped the cap flag")
        self.assertIn('./pfy build "<task>"', note, "handoff dropped the bot build command")

    def test_handoff_cites_the_landed_commits(self):
        self.assertTrue(HANDOFF.is_file(), "docs/HANDOFF-build-review-1106.md is missing")
        if _shallow():
            self.skipTest("shallow checkout: landed commits not in git log")
        note = _text(HANDOFF)
        missing = []
        for subject in LANDED:
            sha = _commit(subject)
            if sha not in note:
                missing.append("%s %s" % (sha, subject))
            ancestor = subprocess.run(
                ["git", "merge-base", "--is-ancestor", sha, "HEAD"],
                cwd=ROOT,
                check=False,
            )
            self.assertEqual(ancestor.returncode, 0, sha)
        self.assertEqual(missing, [], "handoff does not cite the landed SHA")

    def test_trial_names_the_timeout_that_fired_and_why_the_worktree_remains(self):
        # Receipt fields are wall and worktree_removed. The flags are not
        # on the receipt. 3600 * 3 attempts = 10800, next to wall 10802.404.
        self.assertTrue(HANDOFF.is_file(), "docs/HANDOFF-build-review-1106.md is missing")
        note = _text(HANDOFF)
        self.assertIn("--timeout 3600", note, "handoff hides the timeout the trial already used")
        self.assertIn("10800", note, "handoff does not show 3600 times 3 attempts")
        bullets = "\n".join(_still_open(note))
        self.assertIn(
            "greater than 3600",
            bullets,
            "Still open lets a rerun repeat the timeout that fired",
        )
        self.assertIn(
            "--keep-worktree",
            bullets,
            "Still open treats the kept worktree as a removal failure",
        )


if __name__ == "__main__":
    unittest.main()
