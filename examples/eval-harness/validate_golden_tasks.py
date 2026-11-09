#!/usr/bin/env python3
"""Validate data/golden-tasks/*.json cards (no LLM).

Checks required fields and simple acceptance_checks that look like
"File path exists" or "path Status answered" for open-question docs.

Usage:
  python3 examples/eval-harness/validate_golden_tasks.py
  python3 examples/eval-harness/validate_golden_tasks.py --strict-artifacts
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GT_DIR = ROOT / "data" / "golden-tasks"
REQUIRED = {
    "id",
    "title",
    "created",
    "scale",
    "human_request",
    "agent_tasks",
    "artifacts",
    "acceptance_checks",
    "replay_prompt",
}
SCALES = {"orchestration", "multi_file", "single_code", "docs"}


def load_cards() -> list[Path]:
    return sorted(GT_DIR.glob("GT-*.json"))


def check_file_exists(text: str) -> bool | None:
    m = re.search(r"[Ff]ile\s+(`?)([^`\s]+)\1\s+exists", text)
    if not m:
        m = re.search(r"^(data|docs|examples|bootstrap)/\S+\s+exists", text)
    if not m:
        return None
    rel = m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(0).split()[0]
    rel = rel.strip("`")
    return (ROOT / rel).is_file()


def check_oq_answered(text: str) -> bool | None:
    m = re.search(r"(docs/open-questions/OQ-\d{4}[^\s]+\.md)\s+Status\s+answered", text)
    if not m:
        return None
    path = ROOT / m.group(1)
    if not path.is_file():
        # OQ records moved to the private ops checkout (PFY_OPS_ROOT), which
        # mirrors public paths. Without it the claim cannot be checked here.
        ops = os.environ.get("PFY_OPS_ROOT", "").strip()
        alt = Path(ops).expanduser() / m.group(1) if ops else None
        if alt is None or not alt.is_file():
            return None
        path = alt
    body = path.read_text(encoding="utf-8")
    return re.search(r"\*\*Status:\*\*\s*answered", body) is not None or re.search(
        r"^- \*\*Status:\*\* answered", body, re.M
    )


def validate_card(path: Path, strict_artifacts: bool) -> list[str]:
    errs: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"{path.name}: invalid JSON: {e}"]

    missing = REQUIRED - set(data)
    if missing:
        errs.append(f"{path.name}: missing fields {sorted(missing)}")

    scale = data.get("scale")
    if scale and scale not in SCALES:
        errs.append(f"{path.name}: bad scale {scale!r}")

    if not isinstance(data.get("agent_tasks"), list) or not data.get("agent_tasks"):
        errs.append(f"{path.name}: agent_tasks must be non-empty list")

    if not isinstance(data.get("acceptance_checks"), list) or not data.get("acceptance_checks"):
        errs.append(f"{path.name}: acceptance_checks must be non-empty list")

    for i, check in enumerate(data.get("acceptance_checks") or []):
        if not isinstance(check, str):
            errs.append(f"{path.name}: acceptance_checks[{i}] not string")
            continue
        fe = check_file_exists(check)
        if fe is False:
            errs.append(f"{path.name}: FAIL check (file missing): {check}")
        oq = check_oq_answered(check)
        if oq is False:
            errs.append(f"{path.name}: FAIL check (OQ not answered): {check}")

    if strict_artifacts:
        for a in data.get("artifacts") or []:
            if not isinstance(a, dict):
                continue
            ref = a.get("ref") or ""
            if a.get("kind") == "file" or (
                isinstance(ref, str) and not ref.startswith("http") and "/" in ref
            ):
                if ref.startswith("http"):
                    continue
                if not (ROOT / ref).exists():
                    errs.append(f"{path.name}: artifact missing: {ref}")

    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict-artifacts", action="store_true")
    args = ap.parse_args()

    cards = load_cards()
    if not cards:
        print("FAIL: no GT-*.json under data/golden-tasks/")
        return 1

    all_errs: list[str] = []
    for p in cards:
        all_errs.extend(validate_card(p, args.strict_artifacts))

    print(f"=== golden-tasks validate ({len(cards)} cards) ===")
    if all_errs:
        for e in all_errs:
            print(f"  FAIL: {e}")
        return 1
    print(f"  PASS: {', '.join(p.name for p in cards)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
