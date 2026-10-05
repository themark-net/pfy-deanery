#!/usr/bin/env python3
"""Deterministic scorer: integration-stage handoff card (T-0070)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

POTENTIAL = ("high", "medium", "low", "ambiguous")


def score(text: str) -> tuple[bool, str]:
    low = text.lower()
    if not re.search(r"integration[_\s-]?stage\s*[:=]\s*i[0-4]\b", low):
        return False, "missing integration_stage I0-I4"
    found = [p for p in POTENTIAL if re.search(rf"potential\s*[:=]\s*{p}\b", low)]
    if not found:
        return False, "potential must be high, medium, low, or ambiguous"
    if not re.search(r"next[_\s-]?gate\s*[:=]", low):
        return False, "missing next_gate"
    if not re.search(r"non[_\s-]?goals?\s*[:=]", low):
        return False, "missing non_goals"
    return True, f"ok potential={found[0]}"


def main() -> int:
    text = sys.stdin.read() if len(sys.argv) < 2 or sys.argv[1] == "-" else Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
    ok, detail = score(text)
    print(f"SCORE: {'PASS' if ok else 'FAIL'} ({detail})")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
