"""Refuse to start Hermes against the operator's real HERMES_HOME."""

from __future__ import annotations

import os
from pathlib import Path


def assert_hermes_home(value: str | None = None) -> Path:
    raw = value if value is not None else os.environ.get("HERMES_HOME")
    if not raw or not str(raw).strip():
        raise SystemExit("FAIL: HERMES_HOME is unset")
    resolved = Path(raw).expanduser().resolve()
    forbidden = (Path.home() / ".hermes").resolve()
    if resolved == forbidden or forbidden in resolved.parents:
        raise SystemExit(f"FAIL: HERMES_HOME resolves under ~/.hermes ({resolved})")
    return resolved
