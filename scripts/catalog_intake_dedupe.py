#!/usr/bin/env python3
"""Match a GitHub URL, repo, name, or local directory to an existing catalog row.

Same input prints the same line. A duplicate does not write a card.
--write-card creates one card through pfylib.stage_registry.write_tool
when the input is new. integration_stage stays I0.

Evidence comes from the input, and only when it is actually there:
the repo URL, a license when a local tree states one, a pin SHA from a
commit URL, an owner/repo@SHA, or a local git HEAD, and one README claim
from a local tree. No network. tier_ceiling is I1 when that list is
non-empty, so catalog_apply_verdict.py can allow I1. A bare name stays
evidence [] and tier_ceiling I0. This script does not invent evidence
and does not raise integration_stage.

Prints one line:
  new <slug>
  duplicate <slug> <match>
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pfylib.stage_registry import slug_for, write_tool  # noqa: E402

GITHUB_RE = re.compile(
    r"github\.com[:/](?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)",
    re.IGNORECASE,
)
_COMMIT_SHA = re.compile(r"/(?:commit|tree)/([0-9a-fA-F]{7,40})(?:/|[?#]|$)")
_AT_SHA = re.compile(r"@([0-9a-fA-F]{7,40})$")
_SHA = re.compile(r"^[0-9a-f]{7,40}$")
_SPDX = re.compile(r"SPDX-License-Identifier:\s*([A-Za-z0-9.+-]+)", re.IGNORECASE)
_LICENSE_NAMES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "COPYING.md")
_README_NAMES = ("README.md", "README.rst", "README.txt", "README")
_LICENSE_LINE = {
    "mit": "MIT",
    "apache-2.0": "Apache-2.0",
    "apache 2.0": "Apache-2.0",
    "bsd-2-clause": "BSD-2-Clause",
    "bsd-3-clause": "BSD-3-Clause",
    "gpl-2.0": "GPL-2.0",
    "gpl-3.0": "GPL-3.0",
    "gpl-3.0-only": "GPL-3.0-only",
    "agpl-3.0": "AGPL-3.0",
    "agpl-3.0-only": "AGPL-3.0-only",
    "mpl-2.0": "MPL-2.0",
    "isc": "ISC",
    "unlicense": "Unlicense",
    "lgpl-2.1": "LGPL-2.1",
    "lgpl-3.0": "LGPL-3.0",
    "0bsd": "0BSD",
    "cc0-1.0": "CC0-1.0",
    "bsl-1.0": "BSL-1.0",
}
# Longer, more specific phrases first. A short MIT grant line is last.
_LICENSE_PHRASES = (
    ("AGPL-3.0", ("GNU AFFERO GENERAL PUBLIC LICENSE",)),
    ("Apache-2.0", ("Apache License",)),
    ("LGPL-3.0", ("GNU LESSER GENERAL PUBLIC LICENSE",)),
    ("GPL-3.0", ("GNU GENERAL PUBLIC LICENSE",)),
    ("MPL-2.0", ("Mozilla Public License",)),
    ("BSD-3-Clause", ("BSD 3-Clause", "Neither the name of the copyright holder")),
    ("BSD-2-Clause", ("BSD 2-Clause",)),
    ("ISC", ("ISC License",)),
    ("MIT", ("MIT License", "Permission is hereby granted, free of charge")),
    ("Unlicense", ("This is free and unencumbered software",)),
    ("CC0-1.0", ("CC0 1.0 Universal",)),
)


def _norm_repo(repo: str) -> str:
    text = repo.strip()
    if text.lower().endswith(".git"):
        text = text[:-4]
    return text


def _plain(text: str) -> str:
    return text.replace("\u2014", "-").replace("\u2013", "-")


def _github_of(value: object) -> str:
    if not isinstance(value, str):
        return ""
    match = GITHUB_RE.search(value)
    if not match:
        return ""
    return f"{match.group('owner')}/{_norm_repo(match.group('repo'))}".lower()


def _github_url(repo: str) -> str:
    if repo.count("/") != 1:
        return ""
    owner, name = repo.split("/", 1)
    if not owner or not name:
        return ""
    return f"https://github.com/{owner}/{name}"


def _strip_pin(text: str) -> tuple[str, str]:
    """Return the source without a trailing @SHA, plus a commit SHA when present."""
    match = _COMMIT_SHA.search(text)
    if match:
        return text, match.group(1).lower()
    match = _AT_SHA.search(text)
    if match:
        return text[: match.start()], match.group(1).lower()
    return text, ""


def _parse_text(text: str) -> tuple[str, str]:
    """Return (slug, owner/repo or empty) for a string that is not a local directory."""
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


def _local_tree(source: str, root: Path | None) -> Path | None:
    text = source.strip()
    if not text or "://" in text or text.startswith("git@"):
        return None
    candidates = [Path(text).expanduser()]
    if root is not None and not Path(text).is_absolute():
        candidates.append(root / text)
    for path in candidates:
        try:
            if path.is_dir():
                return path.resolve()
        except OSError:
            continue
    return None


def _git(local: Path, *args: str) -> str:
    if not (local / ".git").exists():
        return ""
    try:
        proc = subprocess.run(
            ["git", "-C", str(local), *args],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def _remote_repo(local: Path) -> str:
    return _github_of(_git(local, "remote", "get-url", "origin"))


def _head_sha(local: Path) -> str:
    sha = _git(local, "rev-parse", "HEAD").lower()
    if _SHA.fullmatch(sha):
        return sha
    return ""


def _read_text(path: Path, limit: int = 8192) -> str:
    if not path.is_file():
        return ""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            return handle.read(limit)
    except OSError:
        return ""


def _known_license(text: str) -> str:
    if not text:
        return ""
    match = _SPDX.search(text)
    if match:
        return match.group(1)
    first = ""
    for raw in text.splitlines():
        if raw.strip():
            first = raw.strip()
            break
    mapped = _LICENSE_LINE.get(first.lower())
    if mapped:
        return mapped
    head = text[:4000]
    for name, needles in _LICENSE_PHRASES:
        if any(needle in head for needle in needles):
            return name
    return ""


def _license_of(local: Path) -> str:
    for name in _LICENSE_NAMES:
        found = _known_license(_read_text(local / name))
        if found:
            return found
    return ""


def _readme_claim(text: str) -> str:
    if not text:
        return ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("<", "![", "[!")):
            continue
        line = line.lstrip("#").strip().strip("`*_")
        line = _plain(line).replace("/", " ").replace("\\", " ")
        line = " ".join(line.split())
        if line:
            return line[:160]
    return ""


def _readme_of(local: Path) -> str:
    for name in _README_NAMES:
        claim = _readme_claim(_read_text(local / name))
        if claim:
            return claim
    return ""


def _i1(item: str) -> str:
    """Keep an evidence string the ceiling rule ranks as I1. Drop the rest.

    Rank comes from catalog_apply_verdict.classify_item. This does not
    change that rule and does not invent a higher rank.
    """
    from scripts.catalog_apply_verdict import classify_item

    text = " ".join(_plain(item).split())
    if not text:
        return ""
    rank, _kind = classify_item(text)
    if rank == 1:
        return text
    flat = " ".join(text.replace("/", " ").replace("\\", " ").split())
    if not flat or flat == text:
        return ""
    rank, _kind = classify_item(flat)
    if rank == 1:
        return flat
    return ""


def _add_evidence(items: list[str], item: str) -> None:
    safe = _i1(item)
    if safe and safe not in items:
        items.append(safe)


def intake_facts(source: str, root: Path | None = None) -> dict:
    """Slug, repo, and the evidence the source actually contains."""
    text = source.strip()
    local = _local_tree(text, root)
    pin = ""
    license_id = ""
    readme = ""
    if local is not None:
        slug = slug_for(local.name)
        repo = _remote_repo(local)
        pin = _head_sha(local)
        license_id = _license_of(local)
        readme = _readme_of(local)
    else:
        body, pin = _strip_pin(text)
        if pin and not _SHA.fullmatch(pin):
            pin = ""
        slug, repo = _parse_text(body)
    github = _github_url(repo)
    evidence: list[str] = []
    if github:
        _add_evidence(evidence, github)
    if license_id:
        _add_evidence(evidence, f"license:{license_id}")
    if pin:
        _add_evidence(evidence, f"pin:{pin}")
    if readme:
        _add_evidence(evidence, f"readme: {readme}")
    return {
        "slug": slug,
        "repo": repo,
        "github": github,
        "license": license_id,
        "pin": pin,
        "evidence": evidence,
    }


def parse_source(source: str, root: Path | None = None) -> tuple[str, str]:
    """Return (slug, normalized owner/repo or empty)."""
    facts = intake_facts(source, root)
    return facts["slug"], facts["repo"]


def find_duplicate(root: Path, source: str, facts: dict | None = None) -> tuple[str, str] | None:
    facts = intake_facts(source, root) if facts is None else facts
    slug, repo = facts["slug"], facts["repo"]
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


def _i0_card(facts: dict) -> dict:
    evidence = list(facts["evidence"])
    card = {
        "integration_stage": "I0",
        "uses": "",
        "features": [],
        "potential": "ambiguous",
        "non_goals": ["raised without a verdict"],
        "next_gate": "eval",
        "evidence": evidence,
        "tier_ceiling": "I1" if evidence else "I0",
        "risk_class": "none",
    }
    if facts["github"]:
        card["github"] = facts["github"]
    if facts["license"]:
        card["license"] = facts["license"]
    if facts["pin"]:
        card["pin"] = facts["pin"]
    return card


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Match a source to an existing card, entry, or X post.")
    parser.add_argument("source", help="GitHub URL, owner/repo, name, or local directory.")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--write-card", action="store_true", help="Create an I0 card when the source is new.")
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    facts = intake_facts(args.source, root)
    if not facts["slug"]:
        sys.stderr.write("empty slug\n")
        return 1
    found = find_duplicate(root, args.source, facts)
    if found:
        print(f"duplicate {found[0]} {found[1]}")
        return 0
    if args.write_card:
        write_tool(root, facts["slug"], _i0_card(facts))
    print(f"new {facts['slug']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
