#!/usr/bin/env python3
"""Install a quarantined repo's dependencies inside a container, never on the host.

npm and pip install hooks run arbitrary code. This tool copies a quarantine
tree (from scripts/quarantine_clone.py) to <tree>.deps, then runs the install
in a rootless podman container: no host HOME, no ~/.ssh, all capabilities
dropped, no-new-privileges, only that copy mounted. Package managers run with
install scripts off:

  npm:  npm ci --ignore-scripts  (npm install --ignore-scripts without a lockfile)
  pip:  pip install --only-binary=:all: --target .pydeps -r requirements*.txt

There is no host fallback. Missing podman exits 2 ("can't run here").

  python3 scripts/quarantine_install.py --tree ~/.cache/pfy/quarantine/foo --kind npm
  python3 scripts/quarantine_install.py --tree DIR --kind pip [--dry-run]

Env: PFY_PODMAN (default podman), PFY_QI_NODE_IMAGE, PFY_QI_PY_IMAGE.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

NODE_IMAGE = os.environ.get("PFY_QI_NODE_IMAGE", "docker.io/library/node:22-bookworm-slim")
PY_IMAGE = os.environ.get("PFY_QI_PY_IMAGE", "docker.io/library/python:3.12-slim")


def install_command(kind: str, tree: Path) -> list[str] | None:
    if kind == "npm":
        if (tree / "package-lock.json").is_file() or (tree / "npm-shrinkwrap.json").is_file():
            return ["npm", "ci", "--ignore-scripts", "--no-audit", "--no-fund"]
        if (tree / "package.json").is_file():
            return ["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund"]
        return None
    if kind == "pip":
        reqs = sorted(p.name for p in tree.glob("requirements*.txt") if p.is_file())
        if not reqs:
            return None
        cmd = ["pip", "install", "--disable-pip-version-check", "--no-cache-dir",
               "--only-binary=:all:", "--target", ".pydeps"]
        for r in reqs:
            cmd += ["-r", r]
        return cmd
    return None


def podman_argv(podman: str, kind: str, work: Path, cmd: list[str]) -> list[str]:
    image = NODE_IMAGE if kind == "npm" else PY_IMAGE
    return [
        podman, "run", "--rm", "--pull=missing",
        "--userns=keep-id", "--cap-drop=all", "--security-opt", "no-new-privileges",
        "--env", "HOME=/tmp/home", "--env", "npm_config_ignore_scripts=true",
        "--env", "PIP_ONLY_BINARY=:all:",
        "--tmpfs", "/tmp:rw,size=512m",
        "--volume", f"{work}:/w:rw,Z", "--workdir", "/w",
        image, *cmd,
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Container-only dependency install for quarantined code.")
    ap.add_argument("--tree", required=True)
    ap.add_argument("--kind", required=True, choices=("npm", "pip"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    tree = Path(args.tree).expanduser().resolve()
    if not (tree / "QUARANTINE.json").is_file():
        print("refused: --tree is not a quarantine tree (no QUARANTINE.json). Use scripts/quarantine_clone.py.",
              file=sys.stderr)
        return 2
    cmd = install_command(args.kind, tree)
    if cmd is None:
        print(f"nothing to install: no {args.kind} manifest", file=sys.stderr)
        return 0
    podman = os.environ.get("PFY_PODMAN", "podman")
    if shutil.which(podman) is None:
        print("can't run here: podman is missing. Installs never run on the host.", file=sys.stderr)
        return 2
    work = tree.with_name(tree.name + ".deps")
    argv_run = podman_argv(podman, args.kind, work, cmd)
    if args.dry_run:
        print(" ".join(argv_run))
        return 0
    if work.exists():
        for dirpath, _d, _f in os.walk(work):
            Path(dirpath).chmod(0o700)
        shutil.rmtree(work)
    shutil.copytree(tree, work, symlinks=True, ignore=shutil.ignore_patterns(".git"))
    for dirpath, dirnames, filenames in os.walk(work):
        Path(dirpath).chmod(0o755)
        for f in filenames:
            p = Path(dirpath) / f
            if not p.is_symlink():
                p.chmod(0o644)
    r = subprocess.run(argv_run, timeout=1800)
    print(work)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
