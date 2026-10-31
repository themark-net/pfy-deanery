#!/usr/bin/env python3
"""First call exits 0. Later calls sleep until the runner's timeout kills them.

The counter path is outside the throwaway worktree so the gate does not
dirty the build.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: hang_once.py COUNTER", file=sys.stderr)
        return 2
    counter = Path(sys.argv[1])
    if counter.exists():
        print("hang")
        time.sleep(10**6)
        return 1
    counter.parent.mkdir(parents=True, exist_ok=True)
    counter.write_text("seen\n", encoding="utf-8")
    print("pass-before")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
