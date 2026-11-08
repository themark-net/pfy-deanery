#!/usr/bin/env python3
"""Regenerate catalog counts from stage cards.

Stage cards under data/stages are the source of truth.
_registry.json is not a tool. This script does not read data/tools.json.
Same cards produce the same bytes. When the stored card hash matches and
the three outputs already equal that render, the run does not rewrite them.
Writes use a temp file plus rename. No flock and no model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CARDS = ROOT / "data" / "stages"
DEFAULT_DASHBOARD = ROOT / "pipelines" / "catalog" / "dashboard.latest.md"
DEFAULT_PROGRESS = ROOT / "pipelines" / "catalog" / "counts.latest.json"
REGISTRY_NAME = "_registry.json"
I2_PLUS = frozenset({"I2", "I3", "I4"})
MISSING_FIELDS = (
    "uses",
    "features",
    "potential",
    "non_goals",
    "next_gate",
    "evidence",
    "tier_ceiling",
)


class CountError(Exception):
    """A named input failure. Nothing has been written yet."""


class Card:
    def __init__(self, path: Path, data: dict, raw: bytes) -> None:
        self.path = path
        self.data = data
        self.raw = raw


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regenerate catalog counts from stage cards (the source of truth)."
    )
    parser.add_argument("--cards", type=Path, default=DEFAULT_CARDS)
    parser.add_argument("--registry", type=Path, default=None)
    parser.add_argument("--dashboard", type=Path, default=DEFAULT_DASHBOARD)
    parser.add_argument("--progress", type=Path, default=DEFAULT_PROGRESS)
    args = parser.parse_args(argv)
    if args.registry is None:
        args.registry = args.cards / REGISTRY_NAME
    return args


def read_cards(directory: Path) -> list[Card]:
    if not directory.is_dir():
        raise CountError(f"{directory}: cards directory is missing")
    cards: list[Card] = []
    for path in sorted(directory.glob("*.json")):
        if not path.is_file() or path.name == REGISTRY_NAME:
            continue
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise CountError(f"{path}: invalid UTF-8 ({exc.reason})") from exc
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise CountError(f"{path}: invalid JSON ({exc.msg})") from exc
        if not isinstance(data, dict):
            raise CountError(f"{path}: top level is not an object")
        cards.append(Card(path, data, raw))
    return cards


def read_registry(path: Path) -> dict:
    if not path.is_file():
        raise CountError(f"{path}: registry is missing")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CountError(f"{path}: invalid JSON ({exc.msg})") from exc
    if not isinstance(data, dict):
        raise CountError(f"{path}: top level is not an object")
    return data


def card_digest(cards: list[Card]) -> str:
    digest = hashlib.sha256()
    for card in cards:
        digest.update(card.path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(card.raw)
        digest.update(b"\0")
    return digest.hexdigest()


def stage_of(data: dict) -> str:
    for key in ("stage", "integration_stage"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "(missing)"


def intent_of(data: dict) -> str:
    if "intent" not in data or data["intent"] is None:
        return "(missing)"
    value = data["intent"]
    return value if isinstance(value, str) else str(value)


def tool_id(data: dict, path: Path) -> str:
    for key in ("id", "name"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return path.stem


def build_progress(cards: list[Card], digest: str) -> dict:
    count = len(cards)
    return {
        "card_count": count,
        "cards_sha256": digest,
        "coverage": f"{count} tools registered",
        "i2_plus": sum(1 for card in cards if stage_of(card.data) in I2_PLUS),
        "missing_fields": {
            field: sum(1 for card in cards if field not in card.data)
            for field in MISSING_FIELDS
        },
        "per_intent": dict(Counter(intent_of(card.data) for card in cards)),
        "per_stage": dict(Counter(stage_of(card.data) for card in cards)),
    }


def cell(value: str) -> str:
    return value.replace("|", "/").replace("\n", " ")


def build_dashboard(cards: list[Card], progress: dict) -> str:
    lines = [
        "# Catalog counts",
        "",
        "Stage cards are the source of truth.",
        "",
        f"Coverage: {progress['coverage']}.",
        "",
        f"Cards: {progress['card_count']}. I2+: {progress['i2_plus']}.",
        "",
        "## Stage counts",
        "",
        "| Stage | Count |",
        "|-------|------:|",
    ]
    for stage, count in sorted(progress["per_stage"].items()):
        lines.append(f"| {cell(str(stage))} | {count} |")
    lines += [
        "",
        "## Intent counts",
        "",
        "| Intent | Count |",
        "|--------|------:|",
    ]
    for intent, count in sorted(progress["per_intent"].items()):
        lines.append(f"| {cell(str(intent))} | {count} |")
    lines += [
        "",
        "## Missing fields",
        "",
        "| Field | Cards missing it |",
        "|-------|-----------------:|",
    ]
    for field in MISSING_FIELDS:
        lines.append(f"| {field} | {progress['missing_fields'][field]} |")
    lines += [
        "",
        "## Tools",
        "",
        "| Id | Stage | Intent |",
        "|----|-------|--------|",
    ]
    rows = [
        (tool_id(card.data, card.path), stage_of(card.data), intent_of(card.data), card.path.name)
        for card in cards
    ]
    for ident, stage, intent, _name in sorted(rows, key=lambda row: (row[0].casefold(), row[3])):
        lines.append(f"| {cell(ident)} | {cell(stage)} | {cell(intent)} |")
    lines.append("")
    return "\n".join(lines)


def render_registry(data: dict, coverage: str) -> str:
    out = dict(data)
    out["coverage"] = coverage
    return json.dumps(out, indent=2, ensure_ascii=False) + "\n"


def render_progress(progress: dict) -> str:
    return json.dumps(progress, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def stored_card_hash(progress_path: Path) -> str | None:
    if not progress_path.is_file():
        return None
    try:
        data = json.loads(progress_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    value = data.get("cards_sha256")
    return value if isinstance(value, str) else None


def same_bytes(path: Path, text: str) -> bool:
    if not path.is_file():
        return False
    return path.read_bytes() == text.encode("utf-8")


def atomic_write(path: Path, text: str) -> None:
    data = text.encode("utf-8")
    if path.is_file() and path.read_bytes() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        cards = read_cards(args.cards)
        registry = read_registry(args.registry)
        digest = card_digest(cards)
        progress = build_progress(cards, digest)
        dashboard = build_dashboard(cards, progress)
        registry_text = render_registry(registry, progress["coverage"])
        progress_text = render_progress(progress)
        # Same cards (matching hash) and outputs that already match: do not rewrite.
        if stored_card_hash(args.progress) == digest and all(
            same_bytes(path, text)
            for path, text in (
                (args.registry, registry_text),
                (args.dashboard, dashboard),
                (args.progress, progress_text),
            )
        ):
            return 0
        # Progress last, so a crash before it does not record a hash for stale outputs.
        atomic_write(args.registry, registry_text)
        atomic_write(args.dashboard, dashboard)
        atomic_write(args.progress, progress_text)
    except CountError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except OSError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
