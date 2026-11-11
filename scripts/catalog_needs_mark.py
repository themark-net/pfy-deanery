#!/usr/bin/env python3
"""Write the needs-mark queue. Same inputs, same bytes.

The queue is operator state, so it never goes in the public repo. Default
output: $PFY_OPS_ROOT/eval/catalog-queue/needs-mark.tsv, or
tmp/ops/eval/catalog-queue/needs-mark.tsv (gitignored) when PFY_OPS_ROOT is
unset. --out overrides both.

Columns: slug, kind, reason, evidence, since.

Only hard stops are listed (operator decision 2026-11-10, 7:04am PT: rules
move cards, nobody signs off). kind is always hard-stop and reason starts
with the rule ID from data/promotion-rules.json:
  HS-live-money, HS-release-deploy, HS-secrets, HS-runtime-takeover,
  HS-gpu-unapproved, HS-pull-over-25gb-unapproved.
Sources, in a stable order, deduped by slug+kind+reason:
  each stage card's hard stops (scripts/catalog_auto_raise.py hard_stops,
  with the ops approvals.tsv applied). A card's optional hard_stop_scope
  string is appended to the reason, so the row names the one action still
  waiting (for example "real install only"). A slug in exclusions.tsv is
  closed: it never launches, so its card hard stops are not listed.
  exclusions.tsv reasons that name a GPU run or a pull over 25 GB with no
  approval for that slug
Not listed any more: ceiling flags, demotion flags, parked lanes, unknown
risk, and exclusions that name the operator. Each of those is a failed rule
written to the card's promotion_history and re-checked by the loop. The
catalog loop adds supersede-stop rows itself. --report and --parked are
still accepted and ignored.

since is the ISO date on the first line of a parked marker, otherwise "-".
Atomic replace. No write when the bytes already match.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.catalog_auto_raise import (  # noqa: E402
    GPU_TOKENS,
    load_approvals,
    SIZE_RE,
    hard_stops,
)
from scripts.catalog_eval_queue import load_exclusions  # noqa: E402
from scripts.ops_paths import NEEDS_MARK_REL, ops_path  # noqa: E402

HEADER = ("slug", "kind", "reason", "evidence", "since")
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
MARK_RE = re.compile(r"\b(mark|operator|maintainer)\b", re.IGNORECASE)
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
ROW_RE = re.compile(r"^\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$")


class NeedsError(Exception):
    """A named failure. The output file is left untouched."""


def cell(value: str) -> str:
    return " ".join(value.replace("\t", " ").split())


def evidence_for(root: Path, path: Path) -> str:
    """Repo-relative path when the file lives in the repo. Never an absolute host path."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return f"parked/{path.name}"


def _since_text(text: str) -> str:
    match = DATE_RE.search(text)
    return match.group(1) if match else "-"


def exclusion_kind(reason: str) -> str:
    lowered = reason.lower()
    over = False
    for match in SIZE_RE.finditer(reason):
        try:
            number = float(match.group(1))
        except ValueError:
            continue
        if number > 25:
            over = True
    if over or "25 gb" in lowered or "25gb" in lowered:
        return "pull-over-25gb"
    tokens = set(re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", lowered))
    if tokens & GPU_TOKENS or "gpu" in lowered:
        return "gpu"
    if MARK_RE.search(reason):
        return "excluded"
    return ""


def _load_cards(stages: Path) -> list[tuple[str, dict]]:
    rows: list[tuple[str, dict]] = []
    if not stages.is_dir():
        raise NeedsError(f"missing-stages: {stages}")
    for path in sorted(stages.glob("*.json")):
        if not path.is_file() or path.name.startswith("_"):
            continue
        import json
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise NeedsError(f"malformed-card: {path.name}: {exc}") from exc
        if not isinstance(card, dict):
            raise NeedsError(f"malformed-card: {path.name}: top level is not an object")
        rows.append((path.stem, card))
    return rows


def collect(
    stages: Path,
    exclusions: Path,
    report: Path,
    parked_roots: list[Path],
    root: Path,
) -> list[tuple[str, str, str, str, str]]:
    cards = _load_cards(stages)
    try:
        approvals = load_approvals(root)
    except Exception as exc:
        raise NeedsError(f"approvals: {exc}") from exc
    excluded: dict[str, str] = {}
    if exclusions.is_file():
        try:
            excluded = load_exclusions(exclusions)
        except Exception as exc:
            raise NeedsError(f"exclusions: {exc}") from exc
    rows: list[tuple[str, str, str, str, str]] = []
    for slug, card in cards:
        if slug in excluded:
            continue
        scope = card.get("hard_stop_scope")
        for rid, detail in hard_stops(card, approvals.get(slug, frozenset())):
            if isinstance(scope, str) and scope.strip():
                detail = f"{detail}; {scope.strip()}"
            rows.append((slug, "hard-stop", cell(f"{rid}: {detail}"), f"data/stages/{slug}.json", "-"))
    if exclusions.is_file():
        evidence = evidence_for(root, exclusions)
        for slug in sorted(excluded):
            reason = excluded[slug]
            kind = exclusion_kind(reason)
            if kind not in ("gpu", "pull-over-25gb"):
                continue
            if kind in approvals.get(slug, frozenset()):
                continue
            rid = "HS-gpu-unapproved" if kind == "gpu" else "HS-pull-over-25gb-unapproved"
            rows.append((slug, "hard-stop", cell(f"{rid}: exclusions.tsv: {reason}"), evidence, "-"))
    deduped: list[tuple[str, str, str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        key = (row[0], row[1], row[2])
        if key in seen:
            continue
        if not SLUG_RE.match(row[0]):
            continue
        seen.add(key)
        deduped.append(row)
    deduped.sort(key=lambda row: (row[0], row[1], row[2], row[3]))
    return deduped


def render(rows: list[tuple[str, str, str, str, str]]) -> bytes:
    lines = ["\t".join(HEADER)]
    for row in rows:
        lines.append("\t".join(row))
    return ("\n".join(lines) + "\n").encode("utf-8")


def publish(dest: Path, payload: bytes) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.read_bytes() == payload:
        return False
    fd, name = tempfile.mkstemp(prefix=f".{dest.name}.", dir=dest.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, dest)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write needs-mark.tsv from cards, exclusions, mismatches, and parked lanes.")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--stages", default="")
    parser.add_argument("--exclusions", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--out", default="")
    parser.add_argument("--parked", action="append", default=[], help="Directory of <slug>.parked markers. Repeatable.")
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()

    def pick(text: str, default: Path) -> Path:
        if not text:
            return default
        path = Path(text).expanduser()
        if not path.is_absolute():
            path = root / path
        return path

    stages = pick(args.stages, root / "data" / "stages")
    exclusions = pick(args.exclusions, root / "eval" / "catalog-queue" / "exclusions.tsv")
    report = pick(args.report, root / "eval" / "catalog-verdicts" / "CEILING-MISMATCHES.md")
    dest = pick(args.out, ops_path(NEEDS_MARK_REL, root))
    parked = [Path(item).expanduser() for item in args.parked]
    try:
        payload = render(collect(stages, exclusions, report, parked, root))
        changed = publish(dest, payload)
    except NeedsError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    count = payload.count(b"\n") - 1
    print(f"{'wrote' if changed else 'unchanged'} {count} {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
