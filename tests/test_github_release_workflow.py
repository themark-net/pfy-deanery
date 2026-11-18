"""Structural checks for .github/workflows/release.yml and the tag/notes gate.

The workflow itself is not executed here. These tests read the YAML and run
scripts/check_github_release.py against temp trees (missing notes, version
mismatch, and a matching tag). No network, no GitHub token, no tag writes.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
CHECKER = ROOT / "scripts" / "check_github_release.py"
CHECKOUT_SHA = "11d5960a326750d5838078e36cf38b85af677262"


def _run_checker(root: Path, tag: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), tag],
        cwd=str(root),
        capture_output=True,
        text=True,
        timeout=10,
    )


def _write_tree(tmp: Path, *, version: str, notes_tag: str | None, notes_body: str = "notes\n") -> None:
    (tmp / "pyproject.toml").write_text(
        "[project]\nname = \"pfy-deanery\"\nversion = \"%s\"\n" % version,
        encoding="utf-8",
    )
    if notes_tag is not None:
        dest = tmp / "docs" / "release-notes"
        dest.mkdir(parents=True)
        (dest / f"{notes_tag}.md").write_text(notes_body, encoding="utf-8")


class ReleaseWorkflowStructure(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(WORKFLOW.is_file(), "missing .github/workflows/release.yml")
        self.data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        self.assertIsInstance(self.data, dict)

    def test_triggers_are_tag_push_and_required_tag_dispatch(self) -> None:
        on = self.data.get("on") or self.data.get(True)
        self.assertIsInstance(on, dict, on)
        tags = ((on.get("push") or {}).get("tags")) or []
        self.assertIn("v*", tags)
        dispatch = on.get("workflow_dispatch") or {}
        tag_input = ((dispatch.get("inputs") or {}).get("tag") or {})
        self.assertTrue(tag_input.get("required"), tag_input)

    def test_contents_write_is_scoped_to_the_release_job(self) -> None:
        top = self.data.get("permissions")
        if top is not None:
            self.assertNotEqual((top or {}).get("contents"), "write", top)
        jobs = self.data.get("jobs") or {}
        self.assertTrue(jobs, "release workflow has no jobs")
        writers = []
        for name, job in jobs.items():
            self.assertIsInstance(job, dict, name)
            self.assertEqual(job.get("runs-on"), "ubuntu-24.04", name)
            perms = job.get("permissions") or {}
            if perms.get("contents") == "write":
                writers.append(name)
        self.assertEqual(
            writers,
            list(jobs),
            "contents: write must sit on the release job only, and every job in this workflow must declare it or not use write",
        )
        self.assertEqual(len(writers), 1, "exactly one job should have contents: write")

    def test_notes_file_is_checked_and_used(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("docs/release-notes/", text)
        self.assertIn("check_github_release.py", text)
        self.assertIn("--notes-file", text)
        self.assertIn("already exists", text)
        self.assertIn("Deanery", text)
        # No third-party actions besides the pinned checkout already used in the repo.
        uses = []
        for job in (self.data.get("jobs") or {}).values():
            for step in job.get("steps") or []:
                if not isinstance(step, dict):
                    continue
                ref = step.get("uses")
                if ref:
                    uses.append(ref)
        self.assertEqual(uses, [f"actions/checkout@{CHECKOUT_SHA}"], uses)


class ReleaseNotesGate(unittest.TestCase):
    def test_checker_exists(self) -> None:
        self.assertTrue(CHECKER.is_file(), "missing scripts/check_github_release.py")

    def test_missing_notes_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-release-miss-") as raw:
            root = Path(raw)
            _write_tree(root, version="0.5.0", notes_tag=None)
            proc = _run_checker(root, "v0.5.0")
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            text = (proc.stdout + proc.stderr).lower()
            self.assertIn("release-notes", text)
            self.assertIn("v0.5.0", text)

    def test_version_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-release-ver-") as raw:
            root = Path(raw)
            _write_tree(root, version="0.4.0", notes_tag="v0.5.0")
            proc = _run_checker(root, "v0.5.0")
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            text = proc.stdout + proc.stderr
            self.assertIn("0.4.0", text)
            self.assertIn("0.5.0", text)

    def test_matching_tag_and_notes_pass(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-release-ok-") as raw:
            root = Path(raw)
            _write_tree(root, version="0.5.0", notes_tag="v0.5.0")
            proc = _run_checker(root, "v0.5.0")
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
