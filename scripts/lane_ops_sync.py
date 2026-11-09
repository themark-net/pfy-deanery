#!/usr/bin/env python3
"""Keep a lane's operator records out of the public repo.

Run in a lane worktree after the agent commits and before landing.

1. Files the lane committed under --subdir that the public guard calls
   operator records (traces, .jsonl or .log logs, REPORT.md, notes.md) are
   moved to <worktree>/tmp/ops/<same path> and removed in one commit.
2. The lane's remaining committed files under --subdir get the operator home
   path replaced by $HOME and the owner's name by "the operator" (one commit).
3. Every file the lane changed must pass scripts/check_public_paths.py.
   A failure exits 1 so the lane parks instead of publishing.
4. <worktree>/tmp/ops/<subdir> (where agents write prose reports, traces and
   logs) is copied to PFY_OPS_ROOT, committed there (that path only) and
   pushed. PFY_OPS_ROOT unset: the records stay in the gitignored tmp/ops.
   PFY_LOOP_NO_PUSH=1: commit, no push. An ops push failure is reported and
   does not fail the lane, because the public outputs are fine.

Usage: lane_ops_sync.py --worktree WT --subdir eval/evals/<slug> [--label TEXT]
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def _guard():
    spec = importlib.util.spec_from_file_location("check_public_paths", SCRIPT_DIR / "check_public_paths.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise RuntimeError("git %s: %s" % (" ".join(args), (proc.stderr or proc.stdout).strip()))
    return proc


def lane_changes(wt: Path, base: str) -> list[str]:
    out = _git(wt, "diff", "--name-only", "--diff-filter=ACMR", "%s...HEAD" % base).stdout
    return [line for line in out.splitlines() if line.strip()]


def move_records(wt: Path, subdir: str, changed: list[str], guard) -> list[str]:
    moved = []
    prefix = subdir.rstrip("/") + "/"
    for rel in changed:
        if not rel.startswith(prefix) or not guard.eval_problems(rel):
            continue
        src = wt / rel
        dest = wt / "tmp" / "ops" / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        _git(wt, "rm", "-q", "--", rel)
        moved.append(rel)
    if moved:
        _git(wt, "commit", "-q", "-m", "eval: move operator records to the ops checkout", "--", *moved)
    return moved


def scrub(wt: Path, subdir: str, changed: list[str], guard) -> list[str]:
    home = str(Path.home()).rstrip("/")
    prefix = subdir.rstrip("/") + "/"
    touched = []
    for rel in changed:
        path = wt / rel
        if not rel.startswith(prefix) or not path.is_file():
            continue
        text = guard._text(wt, rel)
        if text is None:
            continue
        new = text
        if home and home != "/":
            new = new.replace(home + "/", "$HOME/").replace(home, "$HOME")
        new = guard.OWNER_RE.sub("the operator", new)
        if new != text:
            path.write_text(new, encoding="utf-8")
            touched.append(rel)
    if touched:
        _git(wt, "add", "--", *touched)
        _git(wt, "commit", "-q", "-m", "eval: scrub home paths and names from public outputs", "--", *touched)
    return touched


def sync_ops(wt: Path, subdir: str, label: str) -> str:
    src = wt / "tmp" / "ops" / subdir
    if not src.is_dir() or not any(p.is_file() for p in src.rglob("*")):
        return "ops nothing to sync"
    raw = os.environ.get("PFY_OPS_ROOT", "").strip()
    if not raw:
        return "ops unset; records stay in %s" % src
    ops = Path(raw).expanduser()
    if not (ops / ".git").exists():
        return "ops not a git checkout: %s" % ops
    dest = ops / subdir
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest, dirs_exist_ok=True)
    _git(ops, "add", "--", subdir)
    if _git(ops, "diff", "--cached", "--quiet", "--", subdir, check=False).returncode == 0:
        return "ops unchanged"
    _git(ops, "commit", "-q", "-m", "%s: operator records" % label, "--", subdir)
    if os.environ.get("PFY_LOOP_NO_PUSH") == "1":
        return "ops committed %s (no push)" % subdir
    for _attempt in range(3):
        if _git(ops, "fetch", "-q", "origin", check=False).returncode != 0:
            continue
        if _git(ops, "merge-base", "--is-ancestor", "origin/main", "HEAD", check=False).returncode != 0:
            if _git(ops, "-c", "rebase.autoStash=true", "rebase", "-q", "origin/main", check=False).returncode != 0:
                _git(ops, "rebase", "--abort", check=False)
                return "ops rebase failed; commit kept locally"
        if _git(ops, "push", "-q", "origin", "HEAD:refs/heads/main", check=False).returncode == 0:
            return "ops pushed %s" % subdir
    return "ops push failed; commit kept locally"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--subdir", required=True)
    parser.add_argument("--label", default="lane")
    parser.add_argument("--base", default="origin/main")
    args = parser.parse_args(argv)
    wt = Path(args.worktree).resolve()
    subdir = args.subdir.strip("/")
    if not subdir or subdir.startswith("/") or ".." in Path(subdir).parts:
        print("lane_ops_sync: bad --subdir", file=sys.stderr)
        return 2
    guard = _guard()
    try:
        changed = lane_changes(wt, args.base)
        moved = move_records(wt, subdir, changed, guard)
        changed = lane_changes(wt, args.base)
        scrubbed = scrub(wt, subdir, changed, guard)
        changed = lane_changes(wt, args.base)
    except RuntimeError as exc:
        print("lane_ops_sync: %s" % exc, file=sys.stderr)
        return 1
    for rel in moved:
        print("moved %s" % rel)
    for rel in scrubbed:
        print("scrubbed %s" % rel)
    problems = guard.check(wt, [rel for rel in changed if (wt / rel).exists()])
    if problems:
        for line in problems:
            print("FAIL %s" % line)
        return 1
    try:
        print(sync_ops(wt, subdir, args.label))
    except RuntimeError as exc:
        print("ops sync failed: %s" % exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
