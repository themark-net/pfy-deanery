"""Planted temp leaks for tests.test_pfylib_tmp_cleanup.

unittest discover does not collect this file (the name does not match test*.py).
`private` leaves a directory in TMPDIR. `host` creates /tmp/$PFY_TMPCLEAN_MARKER
and ignores TMPDIR. `hold` creates /tmp/$PFY_TMPCLEAN_HOLD from this process
during the parent run, writes a ready file, and exits when the stop file appears
or the parent pid changes.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time


def leak_private() -> None:
    tempfile.mkdtemp(prefix="pfy-tmpclean-leak-")


def leak_host() -> None:
    marker = os.environ["PFY_TMPCLEAN_MARKER"]
    os.mkdir("/tmp/" + marker)


def hold_host() -> int:
    """Create one host /tmp directory from this process and wait."""
    path = os.environ["PFY_TMPCLEAN_HOLD"]
    ready = os.environ["PFY_TMPCLEAN_HOLD_READY"]
    stop = os.environ["PFY_TMPCLEAN_HOLD_STOP"]
    parent = os.getppid()
    time.sleep(0.05)
    os.mkdir(path)
    with open(ready, "w", encoding="utf-8") as handle:
        handle.write("ok\n")
    while not os.path.exists(stop):
        if os.getppid() != parent:
            return 0
        time.sleep(0.05)
    return 0


def main(argv: list[str]) -> int:
    kind = argv[1] if len(argv) > 1 else ""
    if kind == "private":
        leak_private()
        return 0
    if kind == "host":
        leak_host()
        return 0
    if kind == "hold":
        return hold_host()
    print("usage: support_tmpclean_leaker.py private|host|hold", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
