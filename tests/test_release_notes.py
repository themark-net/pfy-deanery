"""Release notes and CHANGELOG must exist for the pyproject version.

A later version bump without matching notes should fail this test.
Offline, no network, no writes to product files.
"""
from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _project_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    version = data["project"]["version"]
    if not version or "v" in version.lower():
        raise AssertionError("pyproject project.version must be a bare semver")
    return version


class ReleaseNotesFollowVersion(unittest.TestCase):
    def test_release_notes_file_exists_for_pyproject_version(self) -> None:
        version = _project_version()
        path = ROOT / "docs" / "release-notes" / f"v{version}.md"
        self.assertTrue(
            path.is_file(),
            f"expected release notes at {path.relative_to(ROOT)} for project.version {version}",
        )
        text = path.read_text()
        self.assertIn(version, text)
        self.assertGreater(len(text.strip()), 80)

    def test_changelog_has_a_section_for_pyproject_version(self) -> None:
        version = _project_version()
        path = ROOT / "CHANGELOG.md"
        self.assertTrue(path.is_file(), "CHANGELOG.md is missing")
        text = path.read_text()
        heading = re.compile(
            rf"^##[ \t]+(?:\[)?{re.escape(version)}(?:\])?(?:[ \t].*)?$",
            re.MULTILINE,
        )
        self.assertRegex(
            text,
            heading,
            f"CHANGELOG.md has no section heading for {version}",
        )

class ReleaseNotesUsePlainPunctuation(unittest.TestCase):
    """README, CHANGELOG, and the current release notes use plain punctuation.

    These three files are the user-facing v0.5.0 surfaces. Catches em
    (U+2014) and en (U+2013) dashes in the whole file. Other docs are
    out of scope.
    """

    def test_release_files_have_no_em_or_en_dashes(self) -> None:
        version = _project_version()
        paths = [
            ROOT / "README.md",
            ROOT / "CHANGELOG.md",
            ROOT / "docs" / "release-notes" / f"v{version}.md",
        ]
        offenders: list[str] = []
        for path in paths:
            self.assertTrue(path.is_file(), path)
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if "—" in line or "–" in line:
                    offenders.append("%s:%d" % (path.relative_to(ROOT), i))
        self.assertEqual(
            offenders,
            [],
            "em or en dashes in release files: %s" % ", ".join(offenders),
        )
