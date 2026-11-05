#!/usr/bin/env python3
"""Gate for reject-then-accept.

Tree A: danger.sh is the single line rm -rf / and kept.py is absent.
Tree B: kept.py is the single line value = 1 and danger.sh is absent.
This process never executes danger.sh.
"""

from __future__ import annotations

import sys
from pathlib import Path

DANGER = "rm -rf /"


def main() -> int:
    danger = Path("danger.sh")
    kept = Path("kept.py")
    if danger.is_file() and not kept.exists():
        if danger.read_text(encoding="utf-8").strip() == DANGER:
            print("GATE-OK-DANGER")
            return 0
    if kept.is_file() and not danger.exists():
        if kept.read_text(encoding="utf-8").strip() == "value = 1":
            print("GATE-OK-KEPT")
            return 0
    print("GATE-RED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
