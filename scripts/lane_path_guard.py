#!/usr/bin/env python3
"""Landing path allowlist for catalog lane results (fix 2).

A lane agent reads hostile text. Whatever it commits must stay inside its
own slug's data, or it goes to the full Tester + Reviewer gate instead of
main. The driver runs this before it executes anything from the lane
worktree on the host, and before land.

  eval:      eval/evals/<slug>/**, data/stages/<slug>.json,
             examples/x-intake-local/smoke_<slug_>*.py
  integrate: eval/integrate/<slug>/**, data/stages/<slug>.json,
             examples/x-intake-local/smoke_<slug_>*.py
  supersede: data/supersede-watchlist.json

Always parked, whatever the kind: scripts/, pfylib/, bootstrap/, harness/,
ci/, .github/, ops/, tests/, Makefile, install.sh, pyproject.toml, pfy,
any SKILL.md, AGENTS.md, CLAUDE.md, GEMINI.md, .cursor/, .grok/, .claude/;
symlinks; executable-bit changes outside the allowlist.

  python3 scripts/lane_path_guard.py --kind eval --slug foo --wt WT [--base origin/main]

Exit 0 allowed (prints "ok N paths"), 3 park for the full gate (prints each
path and why), 2 usage or git error.
"""
from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,80}$")
PARK_PREFIXES = ("scripts/", "pfylib/", "bootstrap/", "harness/", "ci/", ".github/", "ops/", "tests/",
                 ".cursor/", ".grok/", ".claude/", "gui/", "pfy/", "tools/", "config/")
PARK_FILES = frozenset({"Makefile", "install.sh", "pyproject.toml", "pfy", "AGENTS.md", "CLAUDE.md",
                        "GEMINI.md", ".gitattributes", ".gitmodules", ".gitignore"})
PARK_BASENAMES = frozenset({"SKILL.md", "AGENTS.md", "CLAUDE.md", "GEMINI.md", ".cursorrules",
                            "copilot-instructions.md"})


def allow_globs(kind: str, slug: str) -> list[str]:
    under = slug.replace("-", "_").replace(".", "_")
    smoke = [f"examples/x-intake-local/smoke_{under}.py", f"examples/x-intake-local/smoke_{under}_*.py"]
    if kind == "eval":
        return [f"eval/evals/{slug}/**", f"data/stages/{slug}.json", *smoke]
    if kind == "integrate":
        return [f"eval/integrate/{slug}/**", f"data/stages/{slug}.json", *smoke]
    if kind == "supersede":
        return ["data/supersede-watchlist.json"]
    raise ValueError(kind)


def _match(rel: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        return rel.startswith(pattern[:-2])
    return fnmatch.fnmatchcase(rel, pattern) and "/" not in rel[len(pattern.split("*")[0]):]


def classify(kind: str, slug: str, changes: list[tuple[str, str, str]]) -> list[str]:
    """changes: (status, old_mode_new_mode_or_type, path). Returns park reasons."""
    reasons = []
    globs = allow_globs(kind, slug)
    for status, mode, rel in changes:
        base = rel.rsplit("/", 1)[-1]
        if rel.startswith(PARK_PREFIXES) or rel in PARK_FILES:
            reasons.append(f"{rel}: protected path (full gate)")
            continue
        if base in PARK_BASENAMES:
            reasons.append(f"{rel}: agent instruction file (full gate)")
            continue
        if mode == "120000":
            reasons.append(f"{rel}: symlink (full gate)")
            continue
        if not any(_match(rel, g) for g in globs):
            reasons.append(f"{rel}: outside the {kind} allowlist for {slug} (full gate)")
    return reasons


def changed(wt: Path, base: str) -> list[tuple[str, str, str]]:
    mb = subprocess.run(["git", "-C", str(wt), "merge-base", base, "HEAD"], capture_output=True, text=True)
    if mb.returncode != 0:
        raise RuntimeError(f"merge-base failed: {mb.stderr.strip()}")
    r = subprocess.run(["git", "-C", str(wt), "diff", "--raw", "--no-renames", "-z", mb.stdout.strip(), "HEAD"],
                       capture_output=True, check=True)
    out = []
    parts = r.stdout.split(b"\0")
    i = 0
    while i < len(parts) - 1:
        meta = parts[i].decode()
        path = parts[i + 1].decode("utf-8", "surrogateescape")
        i += 2
        if not meta.startswith(":"):
            continue
        fields = meta[1:].split()
        new_mode = fields[1]
        status = fields[4]
        out.append((status, new_mode, path))
    # Uncommitted or untracked files are also lane output.
    st = subprocess.run(["git", "-C", str(wt), "status", "--porcelain", "-z", "--untracked-files=all"],
                        capture_output=True, check=True).stdout.split(b"\0")
    for entry in st:
        if len(entry) > 3:
            out.append(("W", "", entry[3:].decode("utf-8", "surrogateescape")))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Lane landing path allowlist.")
    ap.add_argument("--kind", required=True, choices=("eval", "integrate", "supersede"))
    ap.add_argument("--slug", required=True)
    ap.add_argument("--wt", required=True)
    ap.add_argument("--base", default="origin/main")
    args = ap.parse_args(argv)
    if args.kind != "supersede" and not SLUG_RE.match(args.slug):
        print(f"bad slug: {args.slug!r}", file=sys.stderr)
        return 2
    try:
        changes = changed(Path(args.wt), args.base)
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"path guard: git error: {exc}", file=sys.stderr)
        return 2
    reasons = classify(args.kind, args.slug, changes)
    if reasons:
        for r in reasons:
            print(r)
        print(f"park: {len(reasons)} path(s) need the full Tester + Reviewer gate")
        return 3
    print(f"ok {len(changes)} paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
