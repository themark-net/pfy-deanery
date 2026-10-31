#!/usr/bin/env python3
"""Exit 0 only when four named files exist and each has 70 lines.

70 times 4 is 280 lines, which is past the local 250-line cap, and four
files is past the local 3-file cap. The cloud runner has no such cap.
"""

from __future__ import annotations

import pathlib
import sys

NAMES = ("a.py", "b.py", "c.py", "d.py")


def main() -> int:
    total = 0
    for name in NAMES:
        path = pathlib.Path(name)
        if not path.is_file():
            print("missing %s" % name)
            return 1
        lines = path.read_text(encoding="utf-8").splitlines()
        total += len(lines)
        if len(lines) != 70:
            print("%s has %d lines" % (name, len(lines)))
            return 1
    print("files 4 lines %d" % total)
    return 0 if total > 250 else 1


if __name__ == "__main__":
    raise SystemExit(main())
