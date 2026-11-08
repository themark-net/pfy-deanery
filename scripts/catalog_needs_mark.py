#!/usr/bin/env python3
"""Write eval/catalog-queue/needs-mark.tsv. Same inputs, same bytes.

Columns: slug, kind, reason, evidence, since.
Kinds: ceiling, gpu, pull-over-25gb, excluded, demotion-flag, parked, risky-class.

Sources, in a stable order, deduped by slug+kind+reason:
  integrate intake flags (ceiling below I3 on an open I2 card)
  exclusions.tsv reasons that say Mark, GPU, or 25 GB
  card text that the auto-raise classifier refuses (risky class, gpu, size, release)
  CEILING-MISMATCHES.md rows (demotion flags; the scan does not demote)
  parked lane markers (*.parked)

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
    SIZE_RE,
    block_reason,
    classify_risk,
)
from scripts.catalog_eval_queue import load_exclusions  # noqa: E402
from scripts.integrate_intake import _rows  # noqa: E402

HEADER = ("slug", "kind", "reason", "evidence", "since")
DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
MARK_RE = re.compile(r"\bmark\b", re.IGNORECASE)
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


def _name_to_slug(cards: list[tuple[str, dict]]) -> dict[str, str]:
    found: dict[str, str] = {}
    for slug, card in cards:
        name = card.get("name")
        if isinstance(name, str) and name.strip():
            found[name.strip()] = slug
        found.setdefault(slug, slug)
    return found


def _demotions(root: Path, report: Path, names: dict[str, str]) -> list[tuple[str, str, str, str, str]]:
    if not report.is_file():
        return []
    try:
        lines = report.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise NeedsError(f"malformed-report: {exc}") from exc
    rows: list[tuple[str, str, str, str, str]] = []
    evidence = evidence_for(root, report)
    for line in lines:
        if not line.startswith("|"):
            continue
        match = ROW_RE.match(line)
        if not match:
            continue
        tool, stage, _evidence, _tier, allowed, why = match.groups()
        if tool in ("Tool", "---", "(none)"):
            continue
        if stage in ("-", "Stage") or allowed in ("-", "Allowed"):
            continue
        slug = names.get(tool, "")
        if not slug:
            slug_key = tool.strip().lower().replace(" ", "-")
            slug = names.get(slug_key, slug_key if SLUG_RE.match(slug_key) else "")
        if not slug or not SLUG_RE.match(slug):
            continue
        rows.append((slug, "demotion-flag", cell(why) or "ceiling mismatch", evidence, "-"))
    return rows


def _parked(repo: Path, roots: list[Path]) -> list[tuple[str, str, str, str, str]]:
    rows: list[tuple[str, str, str, str, str]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.parked")):
            slug = path.name[: -len(".parked")]
            if not SLUG_RE.match(slug):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                raise NeedsError(f"parked-unreadable: {path}: {exc}") from exc
            first = text.splitlines()[0] if text.splitlines() else ""
            rows.append((slug, "parked", cell(first) or "parked", evidence_for(repo, path), _since_text(first)))
    return rows


def collect(
    stages: Path,
    exclusions: Path,
    report: Path,
    parked_roots: list[Path],
    root: Path,
) -> list[tuple[str, str, str, str, str]]:
    cards = _load_cards(stages)
    names = _name_to_slug(cards)
    rows: list[tuple[str, str, str, str, str]] = []
    try:
        intake = _rows(stages)
    except Exception as exc:
        raise NeedsError(f"intake: {exc}") from exc
    for item in intake:
        if item.get("flag"):
            slug = item["slug"]
            rows.append((
                slug,
                "ceiling",
                cell(item["flag"]),
                f"data/stages/{slug}.json",
                "-",
            ))
    if exclusions.is_file():
        try:
            excluded = load_exclusions(exclusions)
        except Exception as exc:
            raise NeedsError(f"exclusions: {exc}") from exc
        evidence = evidence_for(root, exclusions)
        for slug in sorted(excluded):
            reason = excluded[slug]
            kind = exclusion_kind(reason)
            if not kind:
                continue
            rows.append((slug, kind, cell(reason), evidence, "-"))
    for slug, card in cards:
        blocked = block_reason(card)
        risk = classify_risk(card)
        evidence = f"data/stages/{slug}.json"
        if blocked == "pull-over-25gb":
            rows.append((slug, "pull-over-25gb", "card text is over 25 GB", evidence, "-"))
        elif blocked == "gpu":
            rows.append((slug, "gpu", "card text names a GPU run", evidence, "-"))
        elif blocked == "release-deploy":
            rows.append((slug, "risky-class", "release or deploy stays with Mark", evidence, "-"))
        if risk in ("security", "live-money", "runtime-takeover", "unknown"):
            rows.append((slug, "risky-class", risk, evidence, "-"))
    rows.extend(_demotions(root, report, names))
    rows.extend(_parked(root, parked_roots))
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
    dest = pick(args.out, root / "eval" / "catalog-queue" / "needs-mark.tsv")
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
