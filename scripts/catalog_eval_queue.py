#!/usr/bin/env python3
"""Build the catalog eval queue from stage cards.

Same cards and the same exclusions file always produce the same bytes.
This replaces the hand-built tmp/evq/queue.tsv list. That file is not an
input. Exclusions are a separate committed input. Do not hand-edit the
generated queue.

Sort key
    (mode rank, slug)
    mode rank is trial 0, model 1, ref 2.
    slug is the card filename without ``.json``, in Unicode code point order
    (Python's default string order). A slug field inside the JSON is not the
    id. The filename is already the slug.
    Row 4 is the fourth card in that order after exclusions. A tie on mode
    stays on slug order, so a new card cannot shuffle an existing tie.

Mode, first match wins
    ref when any of these hold:
      - intent, stripped and lowercased, is reference, design_reference,
        ref_only, or pattern_only
      - a tag from ``tags`` or ``catalog_tags`` is design-reference
        (lowercased, one leading # removed)
      - next_gate, stripped and lowercased, is read, or starts with "read "
      - next_gate contains the whole word "reference" (any case)
    model when it is not ref and any of these hold:
      - a tag is local-model (same normalization)
      - next_gate, stripped and lowercased, is model-probe, or starts with
        "model-probe "
    trial otherwise.
    trial is an install-and-probe candidate. model is a probe that needs the
    local-model lock. ref is a design read with no install.

Filters
    Every ``*.json`` in the stages directory is a candidate except names that
    start with ``_`` (``_registry.json`` is shared metadata, not a tool).
    ``integration_stage`` must be a non-empty string. The stage value does not
    drop or reorder a row.
    A slug listed in the exclusions file is omitted. The reason is required and
    is not copied into the queue. A slug with no card is kept in the exclusions
    file so the reason stays on record.
    ``tier_ceiling``, ``handoff_by``, ``potential``, and ``features`` do not
    change membership or order.

Columns, tab-separated
    n       1-based position after the sort
    slug    filename stem
    mode    trial, model, or ref
    gap     next_gate, or - when that field is missing or blank
    entry   entry, or -
    card    {slug}.json
    why     uses (a list is joined with "; "), or -
    Tabs, newlines, and runs of whitespace inside a cell become one space.

Fail closed
    Malformed JSON, a card that is not an object, a missing integration_stage,
    a bad field type on a field this script reads, a missing exclusions file,
    a header other than "slug" then "reason", an empty reason, or a duplicate
    slug: print a named error on stderr, exit 1, and do not create or replace
    the queue file. Cards are validated before any write, including cards that
    exclusions will omit.

Write
    The full file is built in memory. If the output already has those bytes,
    the run leaves it in place. Otherwise the bytes go to a temporary file in
    the same directory and os.replace publishes them.

Defaults
    --stages data/stages
    --exclusions eval/catalog-queue/exclusions.tsv
    --out eval/catalog-queue/queue.tsv
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STAGES = ROOT / "data" / "stages"
DEFAULT_EXCLUSIONS = ROOT / "eval" / "catalog-queue" / "exclusions.tsv"
DEFAULT_OUT = ROOT / "eval" / "catalog-queue" / "queue.tsv"

HEADER = ("n", "slug", "mode", "gap", "entry", "card", "why")
MODE_RANK = {"trial": 0, "model": 1, "ref": 2}
REF_INTENTS = frozenset({"reference", "design_reference", "ref_only", "pattern_only"})
REF_WORD = re.compile(r"\breference\b", re.IGNORECASE)


class QueueError(Exception):
    """A named failure. The queue file is left untouched."""


def cell(value: str) -> str:
    text = " ".join(value.split())
    return text if text else "-"


def _string_field(obj: dict, filename: str, field: str) -> str:
    if field not in obj or obj[field] is None:
        return ""
    value = obj[field]
    if not isinstance(value, str):
        raise QueueError(f"{filename}: {field} is not a string")
    return value


def _uses_text(obj: dict, filename: str) -> str:
    if "uses" not in obj or obj["uses"] is None:
        return ""
    value = obj["uses"]
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise QueueError(f"{filename}: uses item is not a string")
            parts.append(item)
        return "; ".join(parts)
    raise QueueError(f"{filename}: uses is not a string")


def _tags(obj: dict, filename: str) -> set[str]:
    found: set[str] = set()
    for field in ("tags", "catalog_tags"):
        if field not in obj or obj[field] is None:
            continue
        value = obj[field]
        if isinstance(value, str):
            items = [value]
        elif isinstance(value, list):
            items = value
        else:
            raise QueueError(f"{filename}: {field} is not a list")
        for item in items:
            if not isinstance(item, str):
                raise QueueError(f"{filename}: {field} item is not a string")
            token = item.strip().lower()
            if token.startswith("#"):
                token = token[1:]
            if token:
                found.add(token)
    return found


def assign_mode(intent: str, next_gate: str, tags: set[str]) -> str:
    """Return trial, model, or ref. Ref wins over model when both match."""
    gate = " ".join(next_gate.strip().lower().split())
    intent_key = intent.strip().lower()
    if (
        intent_key in REF_INTENTS
        or "design-reference" in tags
        or gate == "read"
        or gate.startswith("read ")
        or REF_WORD.search(next_gate) is not None
    ):
        return "ref"
    if "local-model" in tags or gate == "model-probe" or gate.startswith("model-probe "):
        return "model"
    return "trial"


def load_exclusions(path: Path) -> dict[str, str]:
    if not path.is_file():
        raise QueueError(f"{path.name}: exclusions file is missing")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise QueueError(f"{path.name}: exclusions file is not utf-8") from exc
    except OSError as exc:
        raise QueueError(f"{path.name}: cannot read exclusions file") from exc
    lines = text.splitlines()
    if not lines or lines[0].rstrip("\r") != "slug\treason":
        raise QueueError(f"{path.name}: header must be slug and reason")
    found: dict[str, str] = {}
    for lineno, raw in enumerate(lines[1:], start=2):
        line = raw.rstrip("\r")
        if line.strip() == "":
            continue
        if "\t" not in line:
            raise QueueError(f"{path.name}:{lineno}: missing reason")
        slug, reason = line.split("\t", 1)
        slug = slug.strip()
        reason = reason.strip()
        if not slug:
            raise QueueError(f"{path.name}:{lineno}: missing slug")
        if not reason:
            raise QueueError(f"{path.name}:{lineno}: empty reason")
        if slug in found:
            raise QueueError(f"{path.name}:{lineno}: duplicate slug {slug}")
        found[slug] = reason
    return found


def exclusion_reason(root: Path, slug: str) -> str:
    """Reason from eval/catalog-queue/exclusions.tsv, or empty when the slug is absent.

    A missing file means there is nothing to refuse. A malformed file raises QueueError.
    """
    path = root / "eval" / "catalog-queue" / "exclusions.tsv"
    if not path.is_file():
        return ""
    return load_exclusions(path).get(slug, "")


def load_cards(stages: Path) -> list[tuple[str, str, str, str, str, str]]:
    """Return rows (slug, mode, gap, entry, card, why), unsorted."""
    if not stages.is_dir():
        raise QueueError(f"{stages.name}: stages directory is missing")
    rows: list[tuple[str, str, str, str, str, str]] = []
    for path in sorted(stages.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise QueueError(f"{path.name}: malformed JSON") from exc
        except OSError as exc:
            raise QueueError(f"{path.name}: cannot read card") from exc
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise QueueError(f"{path.name}: malformed JSON") from exc
        if not isinstance(obj, dict):
            raise QueueError(f"{path.name}: card is not an object")
        stage = obj.get("integration_stage")
        if not isinstance(stage, str) or not stage.strip():
            raise QueueError(f"{path.name}: missing integration_stage")
        intent = _string_field(obj, path.name, "intent")
        next_gate = _string_field(obj, path.name, "next_gate")
        entry = _string_field(obj, path.name, "entry")
        uses = _uses_text(obj, path.name)
        tags = _tags(obj, path.name)
        slug = path.stem
        mode = assign_mode(intent, next_gate, tags)
        rows.append((slug, mode, cell(next_gate), cell(entry), f"{slug}.json", cell(uses)))
    return rows


def render(rows: list[tuple[str, str, str, str, str, str]]) -> bytes:
    ordered = sorted(rows, key=lambda row: (MODE_RANK[row[1]], row[0]))
    lines = ["\t".join(HEADER)]
    for number, row in enumerate(ordered, start=1):
        lines.append("\t".join((str(number), *row)))
    return ("\n".join(lines) + "\n").encode("utf-8")


def publish(dest: Path, payload: bytes) -> bool:
    """Atomically replace dest. Return True when the bytes changed."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file():
        try:
            current = dest.read_bytes()
        except OSError as exc:
            raise QueueError(f"{dest.name}: cannot read existing queue") from exc
        if current == payload:
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


def build(stages: Path, exclusions: Path) -> tuple[bytes, int, int]:
    skipped = load_exclusions(exclusions)
    loaded = load_cards(stages)
    rows = [row for row in loaded if row[0] not in skipped]
    return render(rows), len(rows), len(loaded) - len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the catalog eval queue from stage cards."
    )
    parser.add_argument("--stages", type=Path, default=DEFAULT_STAGES)
    parser.add_argument("--exclusions", type=Path, default=DEFAULT_EXCLUSIONS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    try:
        payload, count, omitted = build(args.stages, args.exclusions)
        changed = publish(args.out, payload)
    except QueueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    verb = "wrote" if changed else "unchanged"
    print(f"{verb} {count} rows, excluded {omitted} {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
