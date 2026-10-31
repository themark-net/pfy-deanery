"""Planted temp leaks for tests.test_pfylib_tmp_cleanup.

unittest discover does not collect this file (the name does not match test*.py).
`private` leaves a directory in TMPDIR. `host` creates /tmp/$PFY_TMPCLEAN_MARKER
and ignores TMPDIR.
"""
from __future__ import annotations

import os
import sys
import tempfile


def leak_private() -> None:
    tempfile.mkdtemp(prefix="pfy-tmpclean-leak-")


def leak_host() -> None:
    marker = os.environ["PFY_TMPCLEAN_MARKER"]
    os.mkdir("/tmp/" + marker)


def main(argv: list[str]) -> int:
    kind = argv[1] if len(argv) > 1 else ""
    if kind == "private":
        leak_private()
        return 0
    if kind == "host":
        leak_host()
        return 0
    print("usage: support_tmpclean_leaker.py private|host", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
