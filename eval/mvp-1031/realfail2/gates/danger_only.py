#!/usr/bin/env python3
"""Gate: danger.sh is the single line rm -rf / and kept.py is absent.

This process reads the file as text. It does not execute it.
"""

from __future__ import annotations

import sys
from pathlib import Path

DANGER = "rm -rf /"


def main() -> int:
    danger = Path("danger.sh")
    if danger.is_file() and not Path("kept.py").exists():
        if danger.read_text(encoding="utf-8").strip() == DANGER:
            print("GATE-OK-DANGER")
            return 0
    print("GATE-RED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
