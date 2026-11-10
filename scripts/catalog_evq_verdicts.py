#!/usr/bin/env python3
"""Write VERDICT.json next to a batch lane's one-line VERDICT.

Batch eval lanes (eval/evq1107/<slug>/) recorded their result as a
one-line text file, "STAY I0 <why>" or "PROMOTE I2 <why>". The apply
script reads only VERDICT.json, so those results were never checked
against the card. This writes eval/<batch>/<slug>/VERDICT.json from that
line for each slug whose line says STAY <stage> and whose card is
already at that stage, so nothing moves. The caller then runs
catalog_apply_verdict.py on it like any other verdict.

Skipped, with a reason on stdout:
  no-card       no data/stages/<slug>.json
  has-json      VERDICT.json already there
  not-stay      the line is not STAY <I0..I4> (a promotion needs a lane)
  stage-differs the card is not at the stated stage
  other-stage   --stage was given and the line names another stage

Fields: metric batch_report_verdict, threshold 1, value 0, value_gate
fail (STAY means no gain), modularity_gate pass, proposed_stage the
stated stage, pin from the card when it is a 40-hex SHA, why the rest of
the line, source the one-line file. Same inputs, same bytes. Prints
"wrote <slug>" or "skip <slug> <reason>".
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_LINE = re.compile(r"^STAY\s+(I[0-4])\b[:\s]*(.*)$", re.S)
_SHA = re.compile(r"^[0-9a-f]{40}$")


def verdict_for(line: str, card: dict, source: str) -> dict | None:
    m = _LINE.match(line.strip())
    if not m:
        return None
    stage, why = m.group(1), " ".join(m.group(2).split())
    data = {
        "metric": "batch_report_verdict",
        "threshold": 1,
        "value": 0,
        "value_gate": "fail",
        "modularity_gate": "pass",
        "proposed_stage": stage,
        "why": why,
        "source": source,
    }
    pin = card.get("pin")
    if isinstance(pin, str) and _SHA.match(pin):
        data["pin"] = pin
    return data


def run(root: Path, batch: str, only_stage: str | None, write: bool) -> list[str]:
    out: list[str] = []
    base = root / "eval" / batch
    for line_path in sorted(base.glob("*/VERDICT")):
        slug = line_path.parent.name
        card_path = root / "data" / "stages" / f"{slug}.json"
        dest = line_path.parent / "VERDICT.json"
        if not card_path.is_file():
            out.append(f"skip {slug} no-card")
            continue
        if dest.exists():
            out.append(f"skip {slug} has-json")
            continue
        card = json.loads(card_path.read_text(encoding="utf-8"))
        line = line_path.read_text(encoding="utf-8")
        rel = line_path.relative_to(root).as_posix()
        data = verdict_for(line, card, rel)
        if data is None:
            out.append(f"skip {slug} not-stay")
            continue
        if only_stage and data["proposed_stage"] != only_stage:
            out.append(f"skip {slug} other-stage")
            continue
        if card.get("integration_stage") != data["proposed_stage"]:
            out.append(f"skip {slug} stage-differs")
            continue
        if write:
            dest.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        out.append(f"wrote {slug}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--batch", required=True, help="directory under eval/, e.g. evq1107")
    parser.add_argument("--stage", help="only lines that STAY at this stage")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if "/" in args.batch or args.batch in ("", ".", ".."):
        sys.stderr.write("bad batch\n")
        return 2
    for row in run(Path(args.root).resolve(), args.batch, args.stage, not args.dry_run):
        print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
