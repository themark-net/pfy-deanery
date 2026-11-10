#!/usr/bin/env python3
"""List I2 stage cards that have no integration yet.

A card is open when integration_stage is I2, no evidence item starts with
receipt:, and integration_ticket is missing or blank. The same cards always
produce the same table and the same JSON. Ceilings are read and never written.

  python3 scripts/integrate_intake.py
  python3 scripts/integrate_intake.py --json
  python3 scripts/integrate_intake.py --stages data/stages --json

A ceiling of I0, I1, I2, blank, or anything other than I3 or I4 sets flag to
"tier_ceiling below I3: <rule IDs>", the ceiling rules from
data/promotion-rules.json that fail for the card now (scripts/catalog_auto_raise.py
plan). "tier_ceiling below I3: rules pass" means the next auto-raise raises it.
Nobody signs off. This script does not change that ceiling.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AT_I3 = frozenset({"I3", "I4"})
FLAG = "tier_ceiling below I3"


class IntakeError(Exception):
    """A named failure. No card is written."""


def _failed_rules(stages: Path, slug: str, card: dict) -> str:
    """Comma list of the ceiling rules that fail now, or 'rules pass'."""
    sys.path.insert(0, str(ROOT))
    from scripts import catalog_auto_raise as ar
    root = stages.resolve().parent.parent
    try:
        _path, verdict = ar.latest_verdict(root, slug)
        approved = ar.load_approvals(root).get(slug, frozenset())
        result = ar.plan(card, verdict, approved, root, slug)
    except Exception as exc:  # noqa: BLE001 - a broken rules file is named, not hidden
        return f"rules error {exc}"
    failed = [rid for rid, ok, _d in result["results"] if not ok]
    if result["action"] == "raise" or not failed:
        return "rules pass"
    return ",".join(failed)


def _rows(stages: Path) -> list[dict[str, str]]:
    if not stages.is_dir():
        raise IntakeError(f"missing-stages: {stages}")
    rows: list[dict[str, str]] = []
    paths = sorted(p for p in stages.glob("*.json") if not p.name.startswith("_"))
    for path in paths:
        try:
            raw = path.read_text(encoding="utf-8")
            card = json.loads(raw)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise IntakeError(f"malformed-card: {path.name}: {exc}") from exc
        if not isinstance(card, dict):
            raise IntakeError(f"malformed-card: {path.name}: top level is not an object")
        stage = card.get("integration_stage")
        if not isinstance(stage, str) or not stage.strip():
            raise IntakeError(f"malformed-card: {path.name}: integration_stage is not a string")
        if stage != "I2":
            continue
        evidence = card.get("evidence", [])
        if evidence is None:
            evidence = []
        if not isinstance(evidence, list):
            raise IntakeError(f"malformed-card: {path.name}: evidence is not a list")
        if any(isinstance(item, str) and item.strip().lower().startswith("receipt:") for item in evidence):
            continue
        if "integration_ticket" in card and card["integration_ticket"] is not None:
            ticket = card["integration_ticket"]
            if not isinstance(ticket, str):
                raise IntakeError(f"malformed-card: {path.name}: integration_ticket is not a string")
            if ticket.strip():
                continue
        ceiling = card.get("tier_ceiling")
        if ceiling is None:
            ceiling_text = ""
        elif isinstance(ceiling, str):
            ceiling_text = ceiling.strip()
        else:
            raise IntakeError(f"malformed-card: {path.name}: tier_ceiling is not a string")
        flag = "" if ceiling_text in AT_I3 else f"{FLAG}: {_failed_rules(stages, path.stem, card)}"
        rows.append({
            "slug": path.stem,
            "tier_ceiling": ceiling_text,
            "flag": flag,
        })
    rows.sort(key=lambda row: row["slug"])
    return rows


def render_table(rows: list[dict[str, str]]) -> str:
    lines = [
        "| slug | tier_ceiling | flag |",
        "| --- | --- | --- |",
    ]
    if not rows:
        lines.append("| (none) | - | - |")
    for row in rows:
        lines.append(
            f"| {row['slug']} | {row['tier_ceiling'] or '-'} | {row['flag']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List open I2 cards for an integration lane.")
    parser.add_argument("--stages", default=str(ROOT / "data" / "stages"), help="Directory of stage cards.")
    parser.add_argument("--json", action="store_true", help="Print a JSON list instead of a table.")
    args = parser.parse_args(argv)
    try:
        rows = _rows(Path(args.stages))
    except IntakeError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    if args.json:
        sys.stdout.write(json.dumps(rows) + "\n")
    else:
        sys.stdout.write(render_table(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
