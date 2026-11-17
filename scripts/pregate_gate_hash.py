#!/usr/bin/env python3
"""Worktree vs HEAD for tests/ and gate files, plus committed gate-file changes vs base.

Compares blob hash and git file mode. New or gitignored protected paths with a
GATE name or a .py/.pth suffix fail. Cache junk is excluded: __pycache__/,
.pytest_cache/, *.pyc, *.pyo.

Run from the worktree. BASE_SHA must be set (pregate exports it).
"""
from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

GATE = {
    "conftest.py",
    "pytest.ini",
    "tox.ini",
    "setup.cfg",
    "pyproject.toml",
    "sitecustomize.py",
    "usercustomize.py",
    ".gitignore",
    ".gitattributes",
}
STRICT = GATE - {".gitignore", ".gitattributes"}
PAYLOAD_SUFFIXES = {".py", ".pth"}
CACHE_DIRS = {"__pycache__", ".pytest_cache"}
CACHE_SUFFIXES = {".pyc", ".pyo"}


def git(*a: str) -> bytes:
    return subprocess.run(["git", *a], check=True, capture_output=True).stdout


def names(raw: bytes) -> list[str]:
    return [r.decode("utf-8", "surrogateescape") for r in raw.split(b"\0") if r]


def protected(rel: str) -> bool:
    return rel.startswith("tests/") or Path(rel).name in GATE


def is_cache(rel: str) -> bool:
    parts = Path(rel).parts
    if any(part in CACHE_DIRS for part in parts):
        return True
    return Path(rel).suffix in CACHE_SUFFIXES


def is_payload(rel: str) -> bool:
    if is_cache(rel):
        return False
    return Path(rel).name in GATE or Path(rel).suffix in PAYLOAD_SUFFIXES


def worktree_git_mode(path: Path) -> str | None:
    try:
        st = path.lstat()
    except OSError:
        return None
    if stat.S_ISLNK(st.st_mode):
        return "120000"
    if stat.S_ISDIR(st.st_mode):
        return "040000"
    if stat.S_ISREG(st.st_mode):
        return "100755" if st.st_mode & stat.S_IXUSR else "100644"
    return None


def main() -> int:
    fail: list[str] = []
    notes: list[str] = []
    head: dict[str, tuple[str, str]] = {}
    for line in git("ls-tree", "-r", "-z", "HEAD").split(b"\0"):
        if not line:
            continue
        meta, path = line.split(b"\t", 1)
        rel = path.decode("utf-8", "surrogateescape")
        if not protected(rel):
            continue
        parts = meta.split()
        head[rel] = (parts[0].decode(), parts[2].decode())
    for rel, (mode, blob) in head.items():
        p = Path(rel)
        if not p.exists() and not p.is_symlink():
            fail.append(f"deleted or renamed vs HEAD: {rel}")
            continue
        got_mode = worktree_git_mode(p)
        if got_mode and got_mode != mode:
            fail.append(f"mode changed vs HEAD: {rel} ({mode} -> {got_mode})")
        if p.is_file() or p.is_symlink():
            if git("hash-object", "--", rel).decode().strip() != blob:
                fail.append(f"modified vs HEAD: {rel}")
    current = set(names(git("ls-files", "-z", "--cached", "--others", "--exclude-standard")))
    ignored = set(names(git("ls-files", "-z", "--others", "--ignored", "--exclude-standard")))
    for rel in sorted((current | ignored) - set(head)):
        if rel.startswith("tmp/") or not protected(rel) or not is_payload(rel):
            continue
        fail.append(f"new vs HEAD (staged, untracked, or ignored): {rel}")

    base = os.environ.get("BASE_SHA", "")
    if base:
        mb = git("merge-base", base, "HEAD").decode().strip()
        raw = names(git("diff", "--name-status", "-z", "--no-renames", mb, "HEAD"))
        for status, rel in zip(raw[0::2], raw[1::2]):
            name = Path(rel).name
            if name in STRICT:
                fail.append(
                    f"committed {status} of gate file vs base {mb[:7]}: {rel} "
                    "(needs explicit reviewer waiver)"
                )
            elif name in GATE:
                notes.append(f"committed {status} vs base: {rel}")
            elif rel.startswith("tests/") and status in ("M", "D"):
                kind = "modified" if status == "M" else "deleted"
                notes.append(f"REVIEW: existing test {kind} vs base: {rel}")
    else:
        fail.append("base sha missing; committed gate-file diff cannot run")

    print(f"checked {len(head)} protected paths at HEAD")
    for n in notes:
        print("NOTE", n)
    if fail:
        print("FAIL gate-hash:")
        for item in fail:
            print(" ", item)
        return 1
    print("PASS gate-hash")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as exc:
        sys.stderr.write(exc.stderr.decode("utf-8", "replace") if exc.stderr else str(exc))
        sys.exit(1)
