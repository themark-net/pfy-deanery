#!/usr/bin/env python3
"""Fail unless last_two returns the last two items."""
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
    ns = load("src/seq.py")
    if ns is None or "last_two" not in ns:
        print("last_two is missing")
        return 1
    fn = ns["last_two"]
    pairs = [([1, 2, 3, 4], [3, 4]), ([9], [9]), ([], []), (["a", "b"], ["a", "b"])]
    for items, want in pairs:
        got = fn(list(items))
        if list(got) != want:
            print("last_two(%r) = %r, want %r" % (items, got, want))
            return 1
    print("last_two ok")
    return 0

if __name__ == "__main__":
    sys.exit(main())
