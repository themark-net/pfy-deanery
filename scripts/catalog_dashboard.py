#!/usr/bin/env python3
"""Shim: stage cards are the source of truth.

Delegates to catalog_counts.py. Does not read data/tools.json.
"""
from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().with_name("catalog_counts.py")),
        run_name="__main__",
    )
