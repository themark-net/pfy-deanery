#!/usr/bin/env python3
"""Restore disallowed tier_ceiling and integration_stage edits after a rebase.

Compare to current origin/main, not to the lane's base snapshot.
Only cards this lane changed are touched. The set is
`git diff --name-only origin/main...HEAD -- data/stages` after the rebase.
A card absent from that diff is left byte-for-byte, including a card another
lane landed on main while this lane was running.

--allow-stage SLUG keeps integration_stage on that slug (the apply result).
--allow-ceiling SLUG keeps tier_ceiling and ceiling_history on that slug.
A new card (absent from origin/main) stays at I0 with no ceiling unless the
matching allow flag is set.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _git(worktree: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=worktree,
        check=False,
        capture_output=True,
        text=True,
    )


def changed_cards(worktree: Path) -> list[str]:
    proc = _git(
        worktree,
        "diff",
        "--name-only",
        "--diff-filter=ACMR",
        "origin/main...HEAD",
        "--",
        "data/stages",
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(proc.returncode or 1)
    found: list[str] = []
    for line in proc.stdout.splitlines():
        if not line.endswith(".json"):
            continue
        if line.endswith("/_registry.json") or line == "data/stages/_registry.json":
            continue
        found.append(line)
    return found


def _show(worktree: Path, path: str) -> dict | None:
    proc = _git(worktree, "show", f"origin/main:{path}")
    if proc.returncode != 0:
        return None
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _write(path: Path, card: dict) -> None:
    text = json.dumps(card, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")


def guard(worktree: Path, allow_stage: set[str], allow_ceiling: set[str]) -> list[str]:
    restored: list[str] = []
    for rel in changed_cards(worktree):
        path = worktree / rel
        if not path.is_file():
            continue
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if not isinstance(current, dict):
            continue
        slug = path.stem
        origin = _show(worktree, rel)
        updated = dict(current)
        changed = False
        if origin is None:
            if slug not in allow_stage and updated.get("integration_stage") != "I0":
                updated["integration_stage"] = "I0"
                changed = True
            if slug not in allow_ceiling:
                if "tier_ceiling" in updated:
                    updated.pop("tier_ceiling", None)
                    changed = True
                if "ceiling_history" in updated:
                    updated.pop("ceiling_history", None)
                    changed = True
        else:
            if slug not in allow_stage and updated.get("integration_stage") != origin.get("integration_stage"):
                if "integration_stage" in origin:
                    updated["integration_stage"] = origin["integration_stage"]
                else:
                    updated.pop("integration_stage", None)
                changed = True
            if slug not in allow_ceiling and updated.get("tier_ceiling") != origin.get("tier_ceiling"):
                if "tier_ceiling" in origin:
                    updated["tier_ceiling"] = origin["tier_ceiling"]
                else:
                    updated.pop("tier_ceiling", None)
                changed = True
            if slug not in allow_ceiling and updated.get("ceiling_history") != origin.get("ceiling_history"):
                if "ceiling_history" in origin:
                    updated["ceiling_history"] = origin["ceiling_history"]
                else:
                    updated.pop("ceiling_history", None)
                changed = True
        if changed:
            _write(path, updated)
            restored.append(rel)
    return restored


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Restore disallowed ceiling and stage edits against current origin/main.")
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--allow-stage", action="append", default=[])
    parser.add_argument("--allow-ceiling", action="append", default=[])
    args = parser.parse_args(argv)
    worktree = Path(args.worktree).expanduser().resolve()
    restored = guard(worktree, set(args.allow_stage), set(args.allow_ceiling))
    for rel in restored:
        print(rel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
