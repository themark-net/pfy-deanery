#!/usr/bin/env python3
"""Fail unless inclusive_count counts both ends."""
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
    ns = load("src/span.py")
    if ns is None or "inclusive_count" not in ns:
        print("inclusive_count is missing")
        return 1
    fn = ns["inclusive_count"]
    got = fn(1, 3)
    if got != 3:
        print("inclusive_count(1, 3) = %r, want 3" % (got,))
        return 1
    got = fn(5, 5)
    if got != 1:
        print("inclusive_count(5, 5) = %r, want 1" % (got,))
        return 1
    got = fn(0, 2)
    if got != 3:
        print("inclusive_count(0, 2) = %r, want 3" % (got,))
        return 1
    print("span ok")
    return 0

if __name__ == "__main__":
    sys.exit(main())
