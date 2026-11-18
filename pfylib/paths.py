"""Generic Deanery path defaults (no private checkout paths, no host /tmp/pfy)."""

from __future__ import annotations

import os
from pathlib import Path


def pfy_tmp() -> Path:
    """Operator scratch directory.

    Prefer ``$PFY_TMP``. Otherwise ``$XDG_CACHE_HOME/pfy/tmp`` or
    ``$HOME/.cache/pfy/tmp``. Do not default to ``/tmp/pfy``: the tmp-cleanup
    check treats that path as a host leak when a smoke mkdir's a staged tool
    home under the default (pfy-deanery #9).
    """
    raw = os.environ.get("PFY_TMP")
    if raw:
        return Path(raw)
    cache = os.environ.get("XDG_CACHE_HOME")
    base = Path(cache) if cache else Path.home() / ".cache"
    return base / "pfy" / "tmp"
