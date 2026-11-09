#!/usr/bin/env python3
"""Where private operator files live.

The public repo holds code. Operator queues, handoffs, and run logs live in a
private sibling checkout named by PFY_OPS_ROOT. The private repo mirrors public
paths, so eval/catalog-queue/needs-mark.tsv sits at the same relative path there.

When PFY_OPS_ROOT is unset, operator files go to tmp/ops/ under the repo root.
tmp/ is gitignored, so nothing private lands in a public commit.

CLI: python3 scripts/ops_paths.py [--root DIR] [REL]
prints the ops root, or the ops path for REL.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEEDS_MARK_REL = "eval/catalog-queue/needs-mark.tsv"


def configured() -> Path | None:
    """PFY_OPS_ROOT as a path, or None when unset or empty."""
    raw = os.environ.get("PFY_OPS_ROOT", "").strip()
    if not raw:
        return None
    return Path(raw).expanduser()


def ops_root(repo_root: Path | None = None) -> Path:
    """The private checkout when set, else <repo>/tmp/ops (gitignored)."""
    found = configured()
    if found is not None:
        return found
    return (repo_root or ROOT) / "tmp" / "ops"


def ops_path(rel: str, repo_root: Path | None = None) -> Path:
    return ops_root(repo_root) / rel


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("rel", nargs="?", default="")
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    print(ops_path(args.rel, root) if args.rel else ops_root(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
