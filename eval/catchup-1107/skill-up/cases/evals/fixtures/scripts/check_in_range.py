#!/usr/bin/env python3
"""Fail unless in_range includes both ends."""
import pathlib
import sys

def load(rel):
    path = pathlib.Path(rel)
    if not path.is_file():
        print("missing %s" % rel)
        return None
    ns = {}
    try:
        exec(path.read_text(encoding="utf-8"), ns, ns)
    except (Exception, SystemExit) as exc:
        print("load failed: %s" % type(exc).__name__)
        return None
    return ns

def main():
    ns = load("src/range_check.py")
    if ns is None or "in_range" not in ns:
        print("in_range is missing")
        return 1
    fn = ns["in_range"]
    want = {(1, 1, 3): True, (3, 1, 3): True, (0, 1, 3): False, (2, 1, 3): True, (4, 1, 3): False}
    for args, expected in want.items():
        got = bool(fn(*args))
        if got != expected:
            print("in_range%r = %r, want %r" % (args, got, expected))
            return 1
    print("in_range ok")
    return 0

if __name__ == "__main__":
    sys.exit(main())
