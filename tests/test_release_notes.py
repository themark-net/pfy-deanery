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
    """Public product docs use plain punctuation.

    Catches em (U+2014) and en (U+2013) dashes in the whole file. Scope is
    docs/*.md plus the top-level product markdown (README, CHANGELOG,
    AGENTS, TOOLS, CONTRIBUTING, SUBTREES, CATEGORIZATION). The v0.5.0 pin
    covered the three release surfaces; pfy-deanery #8 extends the same
    rule to the rest of those docs.
    """

    TOP_LEVEL = (
        "README.md",
        "CHANGELOG.md",
        "AGENTS.md",
        "TOOLS.md",
        "CONTRIBUTING.md",
        "SUBTREES.md",
        "CATEGORIZATION.md",
    )

    def _public_doc_paths(self) -> list[Path]:
        paths = [ROOT / name for name in self.TOP_LEVEL]
        missing = [path for path in paths if not path.is_file()]
        if missing:
            raise AssertionError("missing product docs: %s" % ", ".join(str(p) for p in missing))
        paths.extend(sorted((ROOT / "docs").rglob("*.md")))
        return paths

    def _offenders(self, paths: list[Path]) -> list[str]:
        offenders: list[str] = []
        for path in paths:
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if "\u2014" in line or "\u2013" in line:
                    offenders.append("%s:%d" % (path.relative_to(ROOT), i))
        return offenders

    def test_release_files_have_no_em_or_en_dashes(self) -> None:
        version = _project_version()
        paths = [
            ROOT / "README.md",
            ROOT / "CHANGELOG.md",
            ROOT / "docs" / "release-notes" / f"v{version}.md",
        ]
        self.assertEqual(
            self._offenders(paths),
            [],
            "em or en dashes in release files: %s" % ", ".join(self._offenders(paths)),
        )

    def test_public_docs_have_no_em_or_en_dashes(self) -> None:
        offenders = self._offenders(self._public_doc_paths())
        self.assertEqual(
            offenders,
            [],
            "em or en dashes in public docs: %s" % ", ".join(offenders),
        )
