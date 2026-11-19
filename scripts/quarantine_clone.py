#!/usr/bin/env python3
"""Clone an outside repo into quarantine, with its agent instruction files removed.

Outside code is data. A third-party repo's own AGENTS.md, CLAUDE.md, .cursor
rules, Copilot instructions or SKILL.md files would be auto-loaded by agent
CLIs as prompt if they sat near an agent's working dir. This tool:

1. Clones outside every agent working dir: $PFY_QUARANTINE_DIR, default
   ${XDG_CACHE_HOME:-~/.cache}/pfy/quarantine/<slug>. It refuses a
   destination under the current directory or inside any git worktree
   (lane worktrees included).
2. Clones shallow, no submodules, no LFS smudge, no hooks, file:// off.
3. Checks out --pin when given and refuses a mismatch.
4. Strips agent instruction files (STRIP_NAMES / STRIP_DIRS / STRIP_RELS)
   and writes QUARANTINE.json listing each one with its sha256.
5. Makes the tree read-only.

  python3 scripts/quarantine_clone.py --slug foo --url https://github.com/o/foo [--pin SHA]
  python3 scripts/quarantine_clone.py --strip-only DIR   # strip an existing tree

Prints the quarantine path on success. Exit 2 on a refused destination or pin.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

STRIP_NAMES = frozenset({
    "AGENTS.md", "AGENT.md", "CLAUDE.md", "CLAUDE.local.md", "GEMINI.md", "SKILL.md",
    ".cursorrules", ".windsurfrules", ".clinerules", ".roorules", ".goosehints",
    "copilot-instructions.md", ".aider.conf.yml", "CONVENTIONS.md", ".mcp.json",
})
STRIP_DIRS = frozenset({
    ".cursor", ".claude", ".grok", ".codex", ".gemini", ".opencode", ".windsurf",
    ".clinerules", ".roo", ".continue", ".kiro", ".agents", ".augment", ".junie",
})
STRIP_RELS = frozenset({".github/copilot-instructions.md", ".github/instructions", ".github/prompts",
                        ".github/chatmodes", ".vscode/mcp.json"})
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,80}$")
URL_RE = re.compile(r"^https://(?:github\.com|gitlab\.com|codeberg\.org)/[A-Za-z0-9._-]+/[A-Za-z0-9._-]+?(?:\.git)?/?$")
PIN_RE = re.compile(r"^[0-9a-f]{7,40}$")


def default_root() -> Path:
    """PFY_QUARANTINE_DIR, else ${XDG_CACHE_HOME:-~/.cache}/pfy/quarantine.

    Outside every checkout on purpose: lane worktrees run their own copy of
    this script, so a repo-relative default would land under the agent's cwd.
    """
    if os.environ.get("PFY_QUARANTINE_DIR"):
        return Path(os.environ["PFY_QUARANTINE_DIR"]).expanduser()
    cache = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(cache) / "pfy" / "quarantine"


def _nearest_git_root(path: Path) -> Path | None:
    for parent in [path, *path.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def refuse_reason(dest: Path, cwd: Path) -> str:
    """Agent CLIs load instruction files from their cwd, its parents and files
    they open nearby. Refuse a destination under the current directory (the
    agent's working dir) or inside any git worktree (lane worktrees included).
    """
    dest = dest.resolve()
    cwd = cwd.resolve()
    if dest == cwd or cwd in dest.parents:
        return f"destination {dest} is under the current directory (an agent working dir)"
    git_root = _nearest_git_root(dest.parent)
    if git_root is not None:
        return f"destination {dest} is inside a git worktree ({git_root})"
    return ""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _rm(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def strip_tree(root: Path) -> list[dict]:
    """Remove agent instruction files. Returns what was removed."""
    removed: list[dict] = []
    root = root.resolve()
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        here = Path(dirpath)
        rel_here = here.relative_to(root)
        if rel_here.parts[:1] == (".git",):
            dirnames[:] = []
            continue
        for d in list(dirnames):
            rel = (rel_here / d).as_posix()
            if d in STRIP_DIRS or rel in STRIP_RELS:
                target = here / d
                files = sum(1 for _ in target.rglob("*")) if not target.is_symlink() else 0
                removed.append({"path": rel + "/", "kind": "dir", "entries": files})
                _rm(target)
                dirnames.remove(d)
        for f in filenames:
            rel = (rel_here / f).as_posix()
            if f in STRIP_NAMES or rel in STRIP_RELS or f.lower().endswith((".prompt.md", ".instructions.md", ".chatmode.md")):
                target = here / f
                digest = _sha256(target) if target.is_file() and not target.is_symlink() else "symlink"
                removed.append({"path": rel, "kind": "file", "sha256": digest})
                _rm(target)
    return removed


def make_read_only(root: Path) -> None:
    for dirpath, dirnames, filenames in os.walk(root):
        for name in filenames:
            p = Path(dirpath) / name
            if not p.is_symlink():
                p.chmod(p.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        p = Path(dirpath)
        p.chmod(p.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "SSH_"))}
    env.update({"GIT_TERMINAL_PROMPT": "0", "GIT_LFS_SKIP_SMUDGE": "1", "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_ALLOW_PROTOCOL": "https"})
    base = ["git", "-c", "core.hooksPath=/dev/null", "-c", "protocol.file.allow=never",
            "-c", "submodule.recurse=false", "-c", "core.symlinks=false"]
    return subprocess.run(base + list(args), cwd=cwd, env=env, text=True, capture_output=True, timeout=600)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Clone an outside repo into quarantine (data only).")
    ap.add_argument("--slug")
    ap.add_argument("--url")
    ap.add_argument("--pin", default="")
    ap.add_argument("--root", default="", help="quarantine root (default PFY_QUARANTINE_DIR or ~/.cache/pfy/quarantine)")
    ap.add_argument("--strip-only", default="", help="strip agent files from an existing tree and exit")
    args = ap.parse_args(argv)

    if args.strip_only:
        tree = Path(args.strip_only)
        removed = strip_tree(tree)
        print(json.dumps({"stripped": removed}, indent=2))
        return 0
    if not args.slug or not SLUG_RE.match(args.slug):
        print("refused: --slug must be lower-case [a-z0-9._-]", file=sys.stderr)
        return 2
    if not args.url or not URL_RE.match(args.url):
        print("refused: --url must be an https GitHub, GitLab or Codeberg repo URL", file=sys.stderr)
        return 2
    if args.pin and not PIN_RE.match(args.pin):
        print("refused: --pin must be a hex commit", file=sys.stderr)
        return 2
    root = Path(args.root).expanduser() if args.root else default_root()
    dest = root / args.slug
    why = refuse_reason(dest, Path.cwd())
    if why:
        print(f"refused: {why}. Use the default quarantine root.", file=sys.stderr)
        return 2
    if dest.exists():
        # Prior quarantine is read-only; make writable to replace it.
        for dirpath, _d, _f in os.walk(dest):
            Path(dirpath).chmod(0o700)
        shutil.rmtree(dest)
    root.mkdir(parents=True, exist_ok=True)
    depth = [] if args.pin else ["--depth", "1"]
    r = git("clone", "--no-recurse-submodules", "--no-tags", *depth, args.url, str(dest))
    if r.returncode != 0:
        print(f"clone failed: {r.stderr.strip()[-400:]}", file=sys.stderr)
        return 1
    if args.pin:
        r = git("checkout", "--detach", "-q", args.pin, cwd=dest)
        if r.returncode != 0:
            print(f"refused: pin {args.pin} not found", file=sys.stderr)
            return 2
    head = git("rev-parse", "HEAD", cwd=dest).stdout.strip()
    if args.pin and not head.startswith(args.pin):
        print(f"refused: HEAD {head} does not match pin {args.pin}", file=sys.stderr)
        return 2
    removed = strip_tree(dest)
    manifest = {
        "slug": args.slug,
        "url": args.url,
        "head": head,
        "provenance": "upstream-untrusted",
        "note": "Quarantined outside code. Data only, never instructions. Agent instruction files were removed.",
        "stripped": removed,
    }
    (dest / "QUARANTINE.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    make_read_only(dest)
    print(dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
