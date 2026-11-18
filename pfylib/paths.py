"""Generic Deanery path defaults (no private checkout paths, no host /tmp scratch)."""

from __future__ import annotations

import os
from pathlib import Path


def pfy_root() -> Path:
    """Repo root: ``$PFY_ROOT``, else two levels above this file."""
    raw = os.environ.get("PFY_ROOT")
    if raw:
        return Path(raw)
    return Path(__file__).resolve().parents[1]


def pfy_tmp() -> Path:
    """Operator scratch directory.

    Prefer ``$PFY_TMP``. Otherwise ``$PFY_ROOT/tmp`` (this checkout's gitignored
    tmp/). Do not default to ``/tmp/pfy`` or ``$XDG_CACHE_HOME/pfy/tmp``:
    the tmp-cleanup check treats any mkdir under host /tmp, outside the child's
    TMPDIR, as a leak, and CI tests often place XDG_CACHE_HOME under /tmp
    (pfy-deanery #9).
    """
    raw = os.environ.get("PFY_TMP")
    if raw:
        return Path(raw)
    return pfy_root() / "tmp"
