#!/usr/bin/env python3
"""Fail unless greet rejects an empty name and still greets a real one."""
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
    ns = load("src/greet.py")
    if ns is None or "greet" not in ns:
        print("greet is missing")
        return 1
    fn = ns["greet"]
    if fn("Ada") != "Hello, Ada":
        print("greet('Ada') = %r" % (fn("Ada"),))
        return 1
    for bad in ("", "   ", None):
        try:
            got = fn(bad)
        except ValueError:
            continue
        except Exception as exc:
            print("greet(%r) raised %s, want ValueError" % (bad, type(exc).__name__))
            return 1
        print("greet(%r) returned %r, want ValueError" % (bad, got))
        return 1
    print("greet ok")
    return 0

if __name__ == "__main__":
    sys.exit(main())
