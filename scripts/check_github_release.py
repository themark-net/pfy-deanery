#!/usr/bin/env python3
"""Fail unless this checkout has release notes and a matching pyproject version.

Usage: python3 scripts/check_github_release.py v0.5.0 [--root DIR]

Reads pyproject.toml and docs/release-notes/<tag>.md from --root, or the
current working directory. CI checks out the tag into a separate path
because this script is not on older tags. No network and no GitHub writes.
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path


def project_version(root: Path) -> str:
    path = root / "pyproject.toml"
    if not path.is_file():
        raise SystemExit("FAIL: missing pyproject.toml")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict) or not project.get("version"):
        raise SystemExit("FAIL: pyproject.toml has no [project].version")
    return str(project["version"]).strip()


def check(root: Path, tag: str) -> None:
    text = (tag or "").strip()
    if not text.startswith("v") or len(text) < 2 or "/" in text or ".." in text:
        raise SystemExit("FAIL: tag must look like v0.5.0, got %r" % tag)
    notes = root / "docs" / "release-notes" / f"{text}.md"
    if not notes.is_file():
        raise SystemExit("FAIL: missing release notes file %s" % notes)
    version = project_version(root)
    expected = text[1:]
    if version != expected:
        raise SystemExit(
            "FAIL: pyproject version %s does not equal tag %s (expected %s)"
            % (version, text, expected)
        )
    print("OK %s notes=%s version=%s" % (text, notes, version))


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path.cwd()
    if "--root" in args:
        idx = args.index("--root")
        if idx + 1 >= len(args):
            print("usage: check_github_release.py v0.5.0 [--root DIR]", file=sys.stderr)
            return 2
        root = Path(args[idx + 1])
        del args[idx : idx + 2]
    if len(args) != 1:
        print("usage: check_github_release.py v0.5.0 [--root DIR]", file=sys.stderr)
        return 2
    try:
        check(root, args[0])
    except SystemExit as exc:
        if exc.code not in (0, None):
            print(exc.code if isinstance(exc.code, str) else exc, file=sys.stderr)
            return 1 if not isinstance(exc.code, int) else exc.code
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
