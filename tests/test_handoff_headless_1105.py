"""The headless bot handoff matches the CLI and the commits that landed it.

How this fails: the note is missing, a command is not the one `./pfy` help
advertises, a cited SHA is not the commit with that subject, an em dash
slips in, or Still open is empty. A bot then runs the wrong command or
treats a closed gap as open.
A shallow checkout (CI fetch-depth 1) has no history, so the SHA check
skips there and runs in pregate on full history.
Recover: put the four commands back, cite the git SHAs, and list what is
still open in ASCII hyphens. Point the prior handoff, the pfy module map,
and the README simple path at this note.
"""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from tests._ops import OPS, require  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = OPS / "docs" / "HANDOFF-headless-1105.md"
HELP = ROOT / "scripts" / "pfy"

# Exact bot commands. They are the ticket, not a copy of the doc.
COMMANDS = (
    './pfy launch --headless',
    './pfy launch status',
    './pfy launch stop',
    './pfy build "<task>"',
)

# Help lines that make those commands real. A doc that invents a flag
# the CLI does not advertise fails here.
HELP_LINES = (
    "pfy launch [--headless]",
    "pfy launch status|stop",
    'pfy build "<task>"',
)

LANDED = (
    "Launch headless sessions without DISPLAY for bot use",
    "Reap the launch terminal when smoke fails after spawn.",
)

# Handoffs live in the private ops checkout. Public docs never link them.
POINTERS = (
    OPS / "docs" / "HANDOFF-mvp-1104.md",
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


def setUpModule() -> None:
    require(HANDOFF)


class HeadlessHandoffTests(unittest.TestCase):
    def test_handoff_names_the_bot_commands(self):
        self.assertTrue(HANDOFF.is_file(), "docs/HANDOFF-headless-1105.md is missing")
        note = _text(HANDOFF)
        help_text = _text(HELP)
        missing = [cmd for cmd in COMMANDS if cmd not in note]
        self.assertEqual(missing, [], "handoff dropped a bot command")
        unpublished = [line for line in HELP_LINES if line not in help_text]
        self.assertEqual(unpublished, [], "CLI help no longer advertises a documented command")

    def test_handoff_cites_the_landed_commits(self):
        self.assertTrue(HANDOFF.is_file(), "docs/HANDOFF-headless-1105.md is missing")
        if _shallow():
            # CI checks out fetch-depth 1, so the landed commits are not in
            # the log there. Pregate runs this on full history.
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

    def test_still_open_is_present_and_the_note_has_no_em_dash(self):
        self.assertTrue(HANDOFF.is_file(), "docs/HANDOFF-headless-1105.md is missing")
        note = _text(HANDOFF)
        self.assertNotIn("\u2014", note, "em dash in the handoff")
        self.assertNotIn("\u2013", note, "en dash in the handoff")
        bullets = _still_open(note)
        self.assertGreaterEqual(len(bullets), 1, "Still open has no items")
        joined = "\n".join(bullets)
        for needle in ("SIGKILL", "Tauri", "#305", "#309", "without `--headless`"):
            self.assertIn(needle, joined, "Still open dropped %s" % needle)

    def test_prior_notes_point_at_the_headless_handoff(self):
        name = "HANDOFF-headless-1105.md"
        missing = [path.name for path in POINTERS if name not in _text(path)]
        self.assertEqual(missing, [], "a bot reading the old note cannot find the headless handoff")
