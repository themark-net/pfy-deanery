#!/usr/bin/env python3
"""Supersede watch: no reinvention (docs/ops/supersede-watch.md).

Reads data/supersede-watchlist.json. Each project records how much of the
pfy-mentat suite it covers: track, catalog, evaluate, integrate (none,
partial, full). A project covering candidate_min_parts or more parts (partial
counts) is a supersede candidate and gets a deeper look on each recheck.

Exit 1 on a malformed watchlist, or when a project covers all four parts in
full but its verdict is not replace_us (that means: stop and decide).
Stale entries (older than recheck_days) are reported but do not fail.

Intake hook: --parts track,catalog prints whether a new tool with that
coverage is a supersede candidate, so intake and eval can tag it.

  python3 scripts/supersede_check.py
  python3 scripts/supersede_check.py --today 2026-12-20
  python3 scripts/supersede_check.py --parts track,evaluate
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "data" / "supersede-watchlist.json"
PARTS = ("track", "catalog", "evaluate", "integrate")
LEVELS = ("none", "partial", "full")
VERDICTS = ("replace_us", "adopt_part", "watch")


def covered(coverage: dict) -> list[str]:
    return [p for p in PARTS if coverage.get(p) in ("partial", "full")]


def is_candidate(parts_covered: list[str], min_parts: int = 2) -> bool:
    return len(set(parts_covered) & set(PARTS)) >= min_parts


def check(data: dict, today: dt.date) -> tuple[list[str], list[str], list[str]]:
    """Return (errors, candidates, stale)."""
    errors: list[str] = []
    candidates: list[str] = []
    stale: list[str] = []
    min_parts = data.get("candidate_min_parts", 2)
    recheck = data.get("recheck_days", 30)
    projects = data.get("projects")
    if not isinstance(projects, list) or not projects:
        return (["projects must be a non-empty list"], [], [])
    seen: set[str] = set()
    for i, p in enumerate(projects):
        name = p.get("name") or f"#{i}"
        if name in seen:
            errors.append(f"{name}: duplicate name")
        seen.add(name)
        for key in ("url", "what", "reason", "last_checked"):
            if not p.get(key):
                errors.append(f"{name}: missing {key}")
        cov = p.get("coverage") or {}
        for part in PARTS:
            if cov.get(part) not in LEVELS:
                errors.append(f"{name}: coverage.{part} must be one of {LEVELS}")
        verdict = p.get("verdict")
        if verdict not in VERDICTS:
            errors.append(f"{name}: verdict must be one of {VERDICTS}")
        full = all(cov.get(part) == "full" for part in PARTS)
        if verdict == "replace_us" and not full:
            errors.append(f"{name}: replace_us needs all four parts full")
        if full and verdict != "replace_us":
            errors.append(f"{name}: covers the full suite; STOP and decide (verdict is {verdict})")
        if is_candidate(covered(cov), min_parts):
            candidates.append(name)
        try:
            age = (today - dt.date.fromisoformat(p.get("last_checked", ""))).days
            if age > recheck:
                stale.append(f"{name} ({age} days)")
        except ValueError:
            errors.append(f"{name}: last_checked must be YYYY-MM-DD")
    return errors, candidates, stale


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", type=Path, default=DEFAULT)
    ap.add_argument("--today", default=None, help="YYYY-MM-DD (default: today)")
    ap.add_argument("--parts", default=None, help="comma list for a new tool, e.g. track,catalog")
    args = ap.parse_args(argv)
    if args.parts is not None:
        parts = [x.strip() for x in args.parts.split(",") if x.strip()]
        bad = [x for x in parts if x not in PARTS]
        if bad:
            print(f"unknown parts: {bad}; use {PARTS}", file=sys.stderr)
            return 2
        print(json.dumps({"parts": parts, "supersede_candidate": is_candidate(parts)}))
        return 0
    try:
        data = json.loads(args.file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL cannot read {args.file}: {exc}", file=sys.stderr)
        return 1
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    errors, candidates, stale = check(data, today)
    print(f"projects={len(data.get('projects') or [])} candidates={len(candidates)} stale={len(stale)}")
    for c in candidates:
        print(f"candidate: {c}")
    for s in stale:
        print(f"stale: {s}")
    for e in errors:
        print(f"FAIL {e}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
