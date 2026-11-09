"""Private ops checkout for tests that audit internal run records.

Handoffs, run logs, and internal eval runs live in a private sibling repo that
mirrors public paths. Tests that audit those records read them from
PFY_OPS_ROOT and skip when it is unset or the record is absent, so a public
clone and public CI stay green without the private repo.
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_RAW = os.environ.get("PFY_OPS_ROOT", "").strip()
OPS = Path(_RAW).expanduser() if _RAW else ROOT / "tmp" / "ops-unset"


def present(*paths: Path) -> bool:
    return all(Path(p).exists() for p in paths)


def require(*paths: Path) -> None:
    """Skip the caller (module, class, or test) when a private record is absent."""
    missing = [str(p) for p in paths if not Path(p).exists()]
    if missing:
        raise unittest.SkipTest(
            "private ops record absent (set PFY_OPS_ROOT): " + ", ".join(missing)
        )
