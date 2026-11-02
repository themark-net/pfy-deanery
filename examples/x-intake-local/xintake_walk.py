"""One no-follow tree walk for the x-intake smokes (smoke.py, smoke_148, smoke_149)."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def walk_nofollow(root: Path, errors: list[OSError] | None = None) -> list[Path]:
    """Every file, directory, and symlink under root.

    A symlink to a directory is one entry and is not descended into. Same
    membership as Path.rglob("*", recurse_symlinks=False), which is 3.13+.
    os.walk(followlinks=False) is that walk on 3.12 and later. Callers that
    need a stable order sort the result.

    A directory os.walk cannot list is still an entry, and its contents are
    missing. That is reported on stderr and appended to errors, never dropped
    silently.
    """

    def report(exc: OSError) -> None:
        print("walk_nofollow: cannot read %s: %s" % (exc.filename, exc.strerror or exc), file=sys.stderr)
        if errors is not None:
            errors.append(exc)

    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False, onerror=report):
        parent = Path(dirpath)
        found.extend(parent / name for name in (*dirnames, *filenames))
    return found
