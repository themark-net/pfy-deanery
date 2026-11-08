#!/usr/bin/env python3
"""Match a GitHub URL, repo, or name to an existing catalog row.

Same input prints the same line. A duplicate does not write a card.
--write-card creates one I0 card through pfylib.stage_registry.write_tool
when the input is new.

Prints one line:
  new <slug>
  duplicate <slug> <match>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pfylib.stage_registry import slug_for, write_tool  # noqa: E402

GITHUB_RE = re.compile(
    r"github\.com[:/](?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)",
    re.IGNORECASE,
)


def _norm_repo(repo: str) -> str:
    text = repo.strip()
    if text.lower().endswith(".git"):
        text = text[:-4]
    return text


def parse_source(source: str) -> tuple[str, str]:
    """Return (slug, normalized owner/repo or empty)."""
    text = source.strip()
    match = GITHUB_RE.search(text)
    if match:
        owner = match.group("owner")
        repo = _norm_repo(match.group("repo"))
        return slug_for(repo), f"{owner}/{repo}".lower()
    if "/" in text and " " not in text and not text.startswith("http"):
        owner, repo = text.split("/", 1)
        repo = _norm_repo(repo)
        return slug_for(repo), f"{owner}/{repo}".lower()
    return slug_for(text), ""


def _github_of(value: object) -> str:
    if not isinstance(value, str):
        return ""
    match = GITHUB_RE.search(value)
    if not match:
        return ""
    return f"{match.group('owner')}/{_norm_repo(match.group('repo'))}".lower()


def find_duplicate(root: Path, source: str) -> tuple[str, str] | None:
    slug, repo = parse_source(source)
    if not slug:
        return None
    stages = root / "data" / "stages"
    card = stages / f"{slug}.json"
    if card.is_file():
        return slug, card.relative_to(root).as_posix()
    if stages.is_dir() and repo:
        for path in sorted(stages.glob("*.json")):
            if path.name.startswith("_"):
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if isinstance(data, dict) and _github_of(data.get("github")) == repo:
                return path.stem, path.relative_to(root).as_posix()
    entries = root / "sources" / "entries"
    if entries.is_dir():
        named = sorted(entries.glob(f"*-{slug}.md"))
        if named:
            return slug, named[0].relative_to(root).as_posix()
        if repo:
            needle = f"github.com/{repo}".lower()
            for path in sorted(entries.glob("*.md")):
                try:
                    text = path.read_text(encoding="utf-8", errors="replace").lower()
                except OSError:
                    continue
                if needle in text:
                    return slug, path.relative_to(root).as_posix()
    posts = root / "sources" / "x-posts.md"
    if repo and posts.is_file():
        try:
            text = posts.read_text(encoding="utf-8", errors="replace").lower()
        except OSError:
            text = ""
        if f"github.com/{repo}" in text:
            return slug, "sources/x-posts.md"
    return None


def _i0_card(slug: str, source: str) -> dict:
    card = {
        "integration_stage": "I0",
        "uses": "",
        "features": [],
        "potential": "ambiguous",
        "non_goals": ["raised without a verdict"],
        "next_gate": "eval",
        "evidence": [],
        "tier_ceiling": "I0",
        "risk_class": "none",
    }
    _slug, repo = parse_source(source)
    if repo:
        card["github"] = f"https://github.com/{repo}"
    return card


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Match a source to an existing card, entry, or X post.")
    parser.add_argument("source", help="GitHub URL, owner/repo, or name.")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--write-card", action="store_true", help="Create an I0 card when the source is new.")
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    slug, _repo = parse_source(args.source)
    if not slug:
        sys.stderr.write("empty slug\n")
        return 1
    found = find_duplicate(root, args.source)
    if found:
        print(f"duplicate {found[0]} {found[1]}")
        return 0
    if args.write_card:
        write_tool(root, slug, _i0_card(slug, args.source))
    print(f"new {slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
