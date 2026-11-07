#!/usr/bin/env python3
"""Hidden checks for clamp. The case prompt does not list these calls."""
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
    ns = load("src/clamp.py")
    if ns is None or "clamp" not in ns:
        print("clamp is missing")
        return 1
    fn = ns["clamp"]
    checks = [(5, 0, 10, 5), (-1, 0, 10, 0), (11, 0, 10, 10), (0, 0, 10, 0), (10, 0, 10, 10)]
    for value, low, high, want in checks:
        try:
            got = fn(value, low, high)
        except Exception as exc:
            print("clamp(%r, %r, %r) raised %s" % (value, low, high, type(exc).__name__))
            return 1
        if got != want:
            print("clamp(%r, %r, %r) = %r, want %r" % (value, low, high, got, want))
            return 1
    try:
        got = fn(3, 5, 1)
    except ValueError:
        got = None
    except Exception as exc:
        print("clamp(3, 5, 1) raised %s, want ValueError" % type(exc).__name__)
        return 1
    if got is not None:
        print("clamp(3, 5, 1) = %r, want ValueError" % (got,))
        return 1
    print("clamp ok")
    return 0

if __name__ == "__main__":
    sys.exit(main())
