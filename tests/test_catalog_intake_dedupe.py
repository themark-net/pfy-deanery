"""Intake dedupe: same source, same line. A duplicate does not write a second card.

--write-card records evidence the source actually has. That list is what
catalog_apply_verdict.py needs to allow I1. A source with no facts stays
I0, and an I1 proposal is refused. Apply is not changed here.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "catalog_intake_dedupe.py"
APPLY = ROOT / "scripts" / "catalog_apply_verdict.py"


def run(root, source, write=False):
    cmd = ["python3", str(SCRIPT), source, "--root", str(root)]
    if write:
        cmd.append("--write-card")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30)


def catalog_root(tmp):
    root = Path(tmp) / "catalog"
    (root / "data" / "stages").mkdir(parents=True)
    return root


def card_path(root, slug):
    return root / "data" / "stages" / f"{slug}.json"


def load_card(root, slug):
    return json.loads(card_path(root, slug).read_text(encoding="utf-8"))


def write_verdict(path, stage):
    path.write_text(
        json.dumps(
            {
                "metric": "intake_evidence",
                "threshold": 1,
                "value_gate": "pass",
                "modularity_gate": "pass",
                "proposed_stage": stage,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def apply(card, verdict):
    return subprocess.run(
        ["python3", str(APPLY), "--card", str(card), "--verdict", str(verdict)],
        capture_output=True,
        text=True,
        timeout=30,
    )


def git(path, *args, hooks):
    return subprocess.run(
        ["git", "-c", f"core.hooksPath={hooks}", "-C", str(path), *args],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


class IntakeDedupeTest(unittest.TestCase):
    def test_same_source_is_new_once_then_a_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data" / "stages").mkdir(parents=True)
            first = run(root, "https://github.com/Example/Widget.git", write=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout.strip(), "new widget")
            card = load_card(root, "widget")
            self.assertEqual(card["integration_stage"], "I0")
            self.assertEqual(card["tier_ceiling"], "I1")
            self.assertEqual(card["github"], "https://github.com/example/widget")
            self.assertIn("https://github.com/example/widget", card["evidence"])
            self.assertNotIn("license", card)
            self.assertNotIn("pin", card)
            written = card_path(root, "widget").read_bytes()
            again = run(root, "Example/Widget", write=True)
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertEqual(again.stdout.strip(), "duplicate widget data/stages/widget.json")
            self.assertEqual(card_path(root, "widget").read_bytes(), written)
            entries = root / "sources" / "entries"
            entries.mkdir(parents=True)
            (entries / "090-other-tool.md").write_text(
                "see https://github.com/acme/other-tool\n", encoding="utf-8"
            )
            posted = run(root, "https://github.com/acme/other-tool")
            self.assertEqual(posted.returncode, 0, posted.stderr)
            self.assertTrue(posted.stdout.startswith("duplicate other-tool "), posted.stdout)
            self.assertFalse((root / "data" / "stages" / "other-tool.json").exists())
            fresh = run(root, "Brand New Tool", write=True)
            self.assertEqual(fresh.stdout.strip(), "new brand-new-tool")
            bare = load_card(root, "brand-new-tool")
            self.assertEqual(bare["evidence"], [])
            self.assertEqual(bare["tier_ceiling"], "I0")
            self.assertEqual(bare["integration_stage"], "I0")
            repeat = run(root, "Brand New Tool")
            self.assertEqual(repeat.stdout.strip(), "duplicate brand-new-tool data/stages/brand-new-tool.json")
            self.assertEqual(run(root, "Brand New Tool").stdout, repeat.stdout)

    def test_empty_source_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = catalog_root(tmp)
            proc = run(root, "   ", write=True)
            self.assertEqual(proc.returncode, 1)
            self.assertEqual(proc.stderr, "empty slug\n")
            self.assertEqual(list((root / "data" / "stages").glob("*.json")), [])

    def test_repo_url_evidence_can_reach_i1_and_i2_stays_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = catalog_root(tmp)
            source = "https://github.com/example/widget/commit/0123456789abcdef"
            proc = run(root, source, write=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout.strip(), "new widget")
            path = card_path(root, "widget")
            card = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(card["integration_stage"], "I0")
            self.assertEqual(card["tier_ceiling"], "I1")
            self.assertEqual(card["github"], "https://github.com/example/widget")
            self.assertEqual(card["pin"], "0123456789abcdef")
            self.assertIn("https://github.com/example/widget", card["evidence"])
            self.assertIn("pin:0123456789abcdef", card["evidence"])
            verdict = Path(tmp) / "VERDICT.json"
            before = path.read_bytes()
            write_verdict(verdict, "I2")
            refused = apply(path, verdict)
            self.assertEqual(refused.returncode, 1, refused.stdout)
            self.assertIn("above-ceiling", refused.stderr)
            self.assertIn("proposed I2", refused.stderr)
            self.assertEqual(path.read_bytes(), before)
            write_verdict(verdict, "I1")
            allowed = apply(path, verdict)
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            self.assertIn("PROMOTE I1", allowed.stdout)
            promoted = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(promoted["integration_stage"], "I1")
            self.assertEqual(promoted["tier_ceiling"], "I1")
            self.assertEqual(promoted["evidence"], card["evidence"])

    def test_name_without_facts_cannot_reach_i1(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = catalog_root(tmp)
            proc = run(root, "Brand New Tool", write=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            path = card_path(root, "brand-new-tool")
            before = path.read_bytes()
            verdict = Path(tmp) / "VERDICT.json"
            write_verdict(verdict, "I1")
            refused = apply(path, verdict)
            self.assertEqual(refused.returncode, 1, refused.stdout)
            self.assertIn("above-ceiling", refused.stderr)
            self.assertIn("no evidence listed", refused.stderr)
            self.assertEqual(path.read_bytes(), before)

    def test_local_fixture_records_license_pin_and_readme(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = catalog_root(tmp)
            hooks = tmp_path / "hooks"
            hooks.mkdir()
            fixture = tmp_path / "widget"
            fixture.mkdir()
            (fixture / "README.md").write_text(
                "[![badge](https://example.invalid/b.svg)](https://example.invalid)\n"
                "\n"
                "# Widget sorts files\n"
                "\n"
                "More text that must not be copied.\n",
                encoding="utf-8",
            )
            (fixture / "LICENSE").write_text(
                "MIT License\n\nCopyright (c) 2026 Example\n\n"
                "Permission is hereby granted, free of charge, to any person.\n",
                encoding="utf-8",
            )
            self.assertEqual(git(fixture, "init", hooks=hooks).returncode, 0)
            self.assertEqual(git(fixture, "add", "README.md", "LICENSE", hooks=hooks).returncode, 0)
            committed = git(
                fixture,
                "-c",
                "user.email=intake@example.com",
                "-c",
                "user.name=intake",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-m",
                "init",
                hooks=hooks,
            )
            self.assertEqual(committed.returncode, 0, committed.stderr)
            remote = git(fixture, "remote", "add", "origin", "https://github.com/Example/Widget.git", hooks=hooks)
            self.assertEqual(remote.returncode, 0, remote.stderr)
            sha = git(fixture, "rev-parse", "HEAD", hooks=hooks).stdout.strip()
            self.assertEqual(len(sha), 40)
            proc = run(root, str(fixture), write=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout.strip(), "new widget")
            card = load_card(root, "widget")
            self.assertEqual(card["integration_stage"], "I0")
            self.assertEqual(card["tier_ceiling"], "I1")
            self.assertEqual(card["uses"], "")
            self.assertEqual(card["github"], "https://github.com/example/widget")
            self.assertEqual(card["license"], "MIT")
            self.assertEqual(card["pin"], sha)
            self.assertEqual(
                card["evidence"],
                [
                    "https://github.com/example/widget",
                    "license:MIT",
                    f"pin:{sha}",
                    "readme: Widget sorts files",
                ],
            )
            self.assertNotIn("More text", json.dumps(card))
            verdict = Path(tmp) / "VERDICT.json"
            write_verdict(verdict, "I1")
            allowed = apply(card_path(root, "widget"), verdict)
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            self.assertEqual(load_card(root, "widget")["integration_stage"], "I1")

    def test_local_checkout_with_same_github_is_a_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = catalog_root(tmp)
            first = run(root, "https://github.com/example/widget", write=True)
            self.assertEqual(first.stdout.strip(), "new widget")
            written = card_path(root, "widget").read_bytes()
            hooks = tmp_path / "hooks"
            hooks.mkdir()
            fixture = tmp_path / "othername"
            fixture.mkdir()
            (fixture / "README.md").write_text("# Other checkout\n", encoding="utf-8")
            self.assertEqual(git(fixture, "init", hooks=hooks).returncode, 0)
            self.assertEqual(git(fixture, "add", "README.md", hooks=hooks).returncode, 0)
            committed = git(
                fixture,
                "-c",
                "user.email=intake@example.com",
                "-c",
                "user.name=intake",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-m",
                "init",
                hooks=hooks,
            )
            self.assertEqual(committed.returncode, 0, committed.stderr)
            remote = git(fixture, "remote", "add", "origin", "git@github.com:Example/Widget.git", hooks=hooks)
            self.assertEqual(remote.returncode, 0, remote.stderr)
            proc = run(root, str(fixture), write=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout.strip(), "duplicate widget data/stages/widget.json")
            self.assertFalse(card_path(root, "othername").exists())
            self.assertEqual(card_path(root, "widget").read_bytes(), written)

    def test_parent_git_and_unknown_license_do_not_invent_facts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = catalog_root(tmp)
            hooks = tmp_path / "hooks"
            hooks.mkdir()
            parent = tmp_path / "parent"
            parent.mkdir()
            (parent / "README.md").write_text("# Parent only\n", encoding="utf-8")
            self.assertEqual(git(parent, "init", hooks=hooks).returncode, 0)
            self.assertEqual(git(parent, "add", "README.md", hooks=hooks).returncode, 0)
            committed = git(
                parent,
                "-c",
                "user.email=intake@example.com",
                "-c",
                "user.name=intake",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "-m",
                "parent",
                hooks=hooks,
            )
            self.assertEqual(committed.returncode, 0, committed.stderr)
            parent_sha = git(parent, "rev-parse", "HEAD", hooks=hooks).stdout.strip()
            child = parent / "childtool"
            child.mkdir()
            (child / "README.md").write_text("# Child claim\n", encoding="utf-8")
            (child / "LICENSE").write_text("All rights reserved by Example Corp.\n", encoding="utf-8")
            proc = run(root, str(child), write=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout.strip(), "new childtool")
            card = load_card(root, "childtool")
            self.assertEqual(card["evidence"], ["readme: Child claim"])
            self.assertNotIn("license", card)
            self.assertNotIn("pin", card)
            self.assertNotIn(parent_sha, json.dumps(card))
            self.assertEqual(card["tier_ceiling"], "I1")
            self.assertEqual(card["integration_stage"], "I0")
            verdict = Path(tmp) / "VERDICT.json"
            write_verdict(verdict, "I1")
            allowed = apply(card_path(root, "childtool"), verdict)
            self.assertEqual(allowed.returncode, 0, allowed.stderr)

    def test_broken_git_and_unreadable_license_still_keep_the_readme(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = catalog_root(tmp)
            fixture = tmp_path / "brokentool"
            fixture.mkdir()
            (fixture / ".git").write_text("not a git dir\n", encoding="utf-8")
            (fixture / "README.md").write_text("# Broken tree still claims\n", encoding="utf-8")
            license_path = fixture / "LICENSE"
            license_path.write_text("MIT\n", encoding="utf-8")
            license_path.chmod(0)
            try:
                proc = run(root, str(fixture), write=True)
            finally:
                license_path.chmod(0o644)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout.strip(), "new brokentool")
            card = load_card(root, "brokentool")
            self.assertEqual(card["evidence"], ["readme: Broken tree still claims"])
            self.assertNotIn("license", card)
            self.assertNotIn("pin", card)
            self.assertEqual(card["tier_ceiling"], "I1")
            verdict = Path(tmp) / "VERDICT.json"
            write_verdict(verdict, "I1")
            allowed = apply(card_path(root, "brokentool"), verdict)
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            self.assertEqual(load_card(root, "brokentool")["integration_stage"], "I1")

    def test_empty_directory_stays_i0(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            root = catalog_root(tmp)
            fixture = tmp_path / "emptytool"
            fixture.mkdir()
            proc = run(root, str(fixture), write=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(proc.stdout.strip(), "new emptytool")
            path = card_path(root, "emptytool")
            before = path.read_bytes()
            card = json.loads(before.decode("utf-8"))
            self.assertEqual(card["evidence"], [])
            self.assertEqual(card["tier_ceiling"], "I0")
            verdict = Path(tmp) / "VERDICT.json"
            write_verdict(verdict, "I1")
            refused = apply(path, verdict)
            self.assertEqual(refused.returncode, 1, refused.stdout)
            self.assertIn("no evidence listed", refused.stderr)
            self.assertEqual(path.read_bytes(), before)
