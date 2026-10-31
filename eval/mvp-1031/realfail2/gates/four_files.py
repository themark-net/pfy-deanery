#!/usr/bin/env python3
"""Gate: a.py b.py c.py d.py each contain only value = 1."""

from __future__ import annotations

import sys
from pathlib import Path

NAMES = ("a.py", "b.py", "c.py", "d.py")


def main() -> int:
    for name in NAMES:
        path = Path(name)
        if not path.is_file() or path.read_text(encoding="utf-8").strip() != "value = 1":
            print("GATE-RED")
            return 1
    print("GATE-OK-FOUR")
    return 0


if __name__ == "__main__":
    sys.exit(main())
