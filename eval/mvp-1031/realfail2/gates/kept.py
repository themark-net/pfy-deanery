#!/usr/bin/env python3
"""Gate: kept.py is exactly value = 1. Does not execute any other file."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    path = Path("kept.py")
    if path.is_file() and path.read_text(encoding="utf-8").strip() == "value = 1":
        print("GATE-OK")
        return 0
    print("GATE-RED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
