#!/usr/bin/env python3
"""Supersede watch: no reinvention (docs/ops/supersede-watch.md).

Reads data/supersede-watchlist.json. Each project records coverage of the
four-part suite: track, catalog, evaluate, integrate. Integrate is the
local-first part (there is no separate local key). Levels are none, partial,
or full. A part counts only at partial or full. none is not coverage, and a
list of part names is not coverage. candidate_min_parts is how many parts
with real coverage make a supersede candidate. recheck_days is unchanged.

Exit 1 on a malformed watchlist, or when a project covers all four parts in
full but its verdict is not replace_us (that means: stop and decide).
Stale entries (older than recheck_days) are reported but do not fail.

Intake hook: pass levels, not a name list.

  python3 scripts/supersede_check.py
  python3 scripts/supersede_check.py --today 2026-12-20
  python3 scripts/supersede_check.py --parts track=partial,catalog=partial
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "data" / "supersede-watchlist.json"
# Suite stored on each project. integrate is local-first. Do not add a local key.
PARTS = ("track", "catalog", "evaluate", "integrate")
LEVELS = ("none", "partial", "full")
VERDICTS = ("replace_us", "adopt_part", "watch")
REAL = ("partial", "full")


class ClaimError(ValueError):
    """A --parts claim is not coverage. The caller can fix the text and rerun."""


def real_coverage(coverage: dict) -> list[str]:
    """Suite parts whose level is partial or full, in suite order."""
    return [part for part in PARTS if coverage.get(part) in REAL]


def is_candidate(coverage: dict, min_parts: int = 2) -> bool:
    """True when enough suite parts have a real level. Key count does not count."""
    return len(real_coverage(coverage)) >= min_parts


def parse_claim(text: str) -> dict[str, str]:
    """Turn part=level pairs into a full suite map. Bare names are an error."""
    coverage = {part: "none" for part in PARTS}
    seen: list[str] = []
    errors: list[str] = []
    tokens = [item.strip() for item in text.split(",") if item.strip()]
    for token in tokens:
        if "=" not in token:
            errors.append(
                f"{token}: coverage level required (none, partial, full). "
                "A part name alone is not coverage."
            )
            continue
        name, level = (piece.strip() for piece in token.split("=", 1))
        if name not in PARTS:
            errors.append(
                f"unknown part: {name}; suite is {', '.join(PARTS)} "
                "(integrate is the local-first part)"
            )
            continue
        if level not in LEVELS:
            errors.append(f"{name}: level {level!r} must be one of {', '.join(LEVELS)}")
            continue
        if name in seen:
            errors.append(f"{name}: duplicate part")
            continue
        seen.append(name)
        coverage[name] = level
    if errors:
        errors.append("example: --parts track=partial,catalog=partial")
        raise ClaimError("\n".join(errors))
    return coverage


def schema_errors(data: dict) -> list[str]:
    """The declared suite, levels, and verdicts must match the watchlist schema."""
    errors: list[str] = []
    declared = data.get("parts")
    if declared is not None and (
        not isinstance(declared, dict) or set(declared) != set(PARTS)
    ):
        errors.append(
            "parts must describe the suite "
            + ", ".join(PARTS)
            + " (integrate is the local-first part)"
        )
    levels = data.get("levels")
    if levels is not None and list(levels) != list(LEVELS):
        errors.append(f"levels must be {list(LEVELS)}")
    verdicts = data.get("verdicts")
    if verdicts is not None and list(verdicts) != list(VERDICTS):
        errors.append(f"verdicts must be {list(VERDICTS)}")
    return errors


def check(data: dict, today: dt.date) -> tuple[list[str], list[str], list[str]]:
    """Return (errors, candidates, stale)."""
    errors: list[str] = schema_errors(data)
    candidates: list[str] = []
    stale: list[str] = []
    min_parts = data.get("candidate_min_parts", 2)
    recheck = data.get("recheck_days", 30)
    if isinstance(min_parts, bool) or not isinstance(min_parts, int):
        errors.append("candidate_min_parts must be an integer")
        min_parts = None
    projects = data.get("projects")
    if not isinstance(projects, list) or not projects:
        errors.append("projects must be a non-empty list")
        return errors, [], []
    seen: set[str] = set()
    for i, project in enumerate(projects):
        name = project.get("name") or f"#{i}"
        if name in seen:
            errors.append(f"{name}: duplicate name")
        seen.add(name)
        for key in ("url", "what", "reason", "last_checked"):
            if not project.get(key):
                errors.append(f"{name}: missing {key}")
        cov = project.get("coverage")
        if not isinstance(cov, dict):
            errors.append(f"{name}: coverage must be an object of none, partial, full")
            cov = {}
        for part in PARTS:
            if cov.get(part) not in LEVELS:
                errors.append(f"{name}: coverage.{part} must be one of {LEVELS}")
        verdict = project.get("verdict")
        if verdict not in VERDICTS:
            errors.append(f"{name}: verdict must be one of {VERDICTS}")
        full = all(cov.get(part) == "full" for part in PARTS)
        if verdict == "replace_us" and not full:
            errors.append(f"{name}: replace_us needs all four parts full")
        if full and verdict != "replace_us":
            errors.append(
                f"{name}: covers the full suite; STOP and decide (verdict is {verdict})"
            )
        if min_parts is not None and is_candidate(cov, min_parts):
            shown = " ".join(f"{part}={cov.get(part)}" for part in PARTS)
            candidates.append(f"{name} {shown}")
        try:
            age = (today - dt.date.fromisoformat(project.get("last_checked", ""))).days
            if age > recheck:
                stale.append(f"{name} ({age} days)")
        except ValueError:
            errors.append(f"{name}: last_checked must be YYYY-MM-DD")
    return errors, candidates, stale


def claim_report(coverage: dict, min_parts: int = 2) -> dict:
    covered = real_coverage(coverage)
    return {
        "parts": covered,
        "coverage": {part: coverage[part] for part in PARTS},
        "suite": list(PARTS),
        "supersede_candidate": len(covered) >= min_parts,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", type=Path, default=DEFAULT)
    ap.add_argument("--today", default=None, help="YYYY-MM-DD (default: today)")
    ap.add_argument(
        "--parts",
        default=None,
        help="coverage claim, e.g. track=partial,catalog=partial",
    )
    args = ap.parse_args(argv)
    if args.parts is not None:
        try:
            coverage = parse_claim(args.parts)
        except ClaimError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(json.dumps(claim_report(coverage)))
        return 0
    try:
        data = json.loads(args.file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL cannot read {args.file}: {exc}", file=sys.stderr)
        return 1
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    errors, candidates, stale = check(data, today)
    print(
        f"projects={len(data.get('projects') or [])} "
        f"candidates={len(candidates)} stale={len(stale)}"
    )
    for candidate in candidates:
        print(f"candidate: {candidate}")
    for item in stale:
        print(f"stale: {item}")
    for error in errors:
        print(f"FAIL {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
