#!/usr/bin/env python3
"""Exit 0 when a file's stripped text equals the expected line."""

from __future__ import annotations

import pathlib
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: value_is.py REL_PATH EXPECTED", file=sys.stderr)
        return 2
    path = pathlib.Path(sys.argv[1])
    try:
        got = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        print(exc)
        return 1
    print("got %s" % got)
    return 0 if got == sys.argv[2] else 1


if __name__ == "__main__":
    raise SystemExit(main())
