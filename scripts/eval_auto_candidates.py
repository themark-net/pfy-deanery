#!/usr/bin/env python3
"""T-0074: gate models for make eval-auto, in try order.

EVAL_GATE_CANDIDATES, else EVAL_GATE_MODEL, else LOCAL_CODER_MODEL,
else the lab-proven deepseek-coder tags. Prints one model per line.
"""
from __future__ import annotations

import os
import sys

DEFAULT = "deepseek-coder:6.7b-instruct,deepseek-coder:6.7b"


def gate_candidates(env: dict | None = None) -> list[str]:
    src = env if env is not None else os.environ
    raw = (
        src.get("EVAL_GATE_CANDIDATES")
        or src.get("EVAL_GATE_MODEL")
        or src.get("LOCAL_CODER_MODEL")
        or DEFAULT
    )
    out = []
    for part in raw.split(","):
        name = part.strip()
        if name and name not in out:
            out.append(name)
    return out


def main() -> int:
    for name in gate_candidates():
        print(name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
