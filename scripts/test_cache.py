#!/usr/bin/env python3
"""One run per commit: cache a PASS for the git tree, never a failure.

Key = sha256(tree SHA of HEAD, sha256 of config/test_select.json, python
version, host class). Host class is nimo (self-hosted or this lab) or ubuntu
(GitHub-hosted). Store under ${PFY_TEST_CACHE:-$HOME/.cache/pfy/test-pass}/<key>.json.

  python3 scripts/test_cache.py check [--need affected|structural|full]
  python3 scripts/test_cache.py record --mode affected --selection sel.json --receipt receipt.json
  python3 scripts/test_cache.py key

check exits 0 on a recorded PASS for this key. A full PASS also satisfies an
affected or structural check. An affected PASS does not satisfy --need full.
A corrupt file, a FAIL, a dirty worktree, or a different tree is a miss.
record writes only a PASS, atomically. A dirty worktree is not recorded:
the command prints "not recorded: dirty worktree" and exits 0. A non-PASS
still exits 1 and writes nothing. check still exits 1 on a dirty tree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

MODES = ("none", "structural", "affected", "full")


def repo_root(start: Path | None = None) -> Path:
    here = (start or Path(__file__)).resolve()
    for cand in [here, *here.parents]:
        if (cand / "config" / "test_select.json").is_file():
            return cand
    return Path.cwd()


def config_path(root: Path) -> Path:
    return root / "config" / "test_select.json"


def git_out(root: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return (proc.stdout or "").strip()


def worktree_dirty(root: Path) -> bool:
    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return True
    return bool((proc.stdout or "").strip())


def host_class() -> str:
    """nimo for the lab and self-hosted runners, ubuntu for GitHub-hosted.

    Inside GitHub Actions, RUNNER_ENVIRONMENT wins. PFY_HOST_CLASS cannot
    retarget a hosted runner onto the nimo cache (or the reverse).
    """
    if os.environ.get("GITHUB_ACTIONS") == "true":
        if os.environ.get("RUNNER_ENVIRONMENT") == "self-hosted":
            return "nimo"
        return "ubuntu"
    forced = os.environ.get("PFY_HOST_CLASS", "").strip().lower()
    if forced in {"nimo", "ubuntu"}:
        return forced
    return "nimo"


def identity(root: Path) -> dict[str, str]:
    cfg = config_path(root)
    if not cfg.is_file():
        raise SystemExit(f"missing {cfg}")
    tree = git_out(root, "rev-parse", "HEAD^{tree}")
    config_sha = hashlib.sha256(cfg.read_bytes()).hexdigest()
    py = platform.python_version()
    host = host_class()
    raw = f"{tree}\n{config_sha}\n{py}\n{host}\n"
    key = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return {
        "tree": tree,
        "config_sha256": config_sha,
        "python": py,
        "host_class": host,
        "key": key,
    }


def cache_dir() -> Path:
    env = os.environ.get("PFY_TEST_CACHE", "").strip()
    if env:
        return Path(env)
    return Path.home() / ".cache" / "pfy" / "test-pass"


def cache_file(key: str) -> Path:
    return cache_dir() / f"{key}.json"


def load_entry(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def satisfies(stored: str, need: str | None) -> bool:
    if stored == "full":
        return True
    if not need:
        return True
    return stored == need


def cmd_key(root: Path) -> int:
    ident = identity(root)
    print(ident["key"])
    return 0


def cmd_check(root: Path, need: str | None) -> int:
    ident = identity(root)
    key = ident["key"]
    if worktree_dirty(root):
        print(f"MISS {key} dirty worktree")
        return 1
    path = cache_file(key)
    if not path.is_file():
        print(f"MISS {key} absent")
        return 1
    entry = load_entry(path)
    if entry is None:
        print(f"MISS {key} corrupt")
        return 1
    if entry.get("result") != "PASS":
        print(f"MISS {key} not a PASS")
        return 1
    if entry.get("key") != key or entry.get("tree") != ident["tree"]:
        print(f"MISS {key} identity mismatch")
        return 1
    if entry.get("config_sha256") != ident["config_sha256"]:
        print(f"MISS {key} config mismatch")
        return 1
    if entry.get("python") != ident["python"] or entry.get("host_class") != ident["host_class"]:
        print(f"MISS {key} runtime mismatch")
        return 1
    stored = str(entry.get("mode") or "")
    if stored not in MODES or not satisfies(stored, need):
        print(f"MISS {key} mode {stored or 'missing'} does not satisfy {need or 'any'}")
        return 1
    print(f"HIT {key}")
    return 0


def atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    with tmp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def cmd_record(root: Path, args: argparse.Namespace) -> int:
    mode = args.mode
    modules: list[str] = list(args.modules or [])
    if args.selection:
        sel = json.loads(Path(args.selection).read_text(encoding="utf-8"))
        if not isinstance(sel, dict):
            print("not recorded: selection is not an object", file=sys.stderr)
            return 1
        mode = mode or sel.get("mode")
        if not modules:
            raw = sel.get("modules") or []
            if not isinstance(raw, list):
                print("not recorded: selection modules is not a list", file=sys.stderr)
                return 1
            modules = [str(item) for item in raw]
    if mode not in MODES:
        print(f"not recorded: mode must be one of {', '.join(MODES)}", file=sys.stderr)
        return 1
    result = args.result
    receipt = None
    if args.receipt:
        try:
            receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"not recorded: receipt unreadable: {exc}", file=sys.stderr)
            return 1
        if isinstance(receipt, dict) and receipt.get("rc") not in (0, None):
            result = "FAIL"
    if result != "PASS":
        print("not recorded: only PASS is cached")
        return 1
    # affected and full claim tests ran. A PASS with no receipt would let a
    # later check skip the suite. none and structural have no unittest receipt.
    if mode in {"affected", "full"} and (
        not isinstance(receipt, dict) or receipt.get("rc") != 0
    ):
        print("not recorded: affected and full need a receipt with rc 0", file=sys.stderr)
        return 1
    if worktree_dirty(root):
        # Skip, do not fail. A passing suite stays green. The file is not written,
        # so a later clean check cannot skip tests that ran against other files.
        print("not recorded: dirty worktree")
        return 0
    ident = identity(root)
    payload = {
        "key": ident["key"],
        "tree": ident["tree"],
        "config_sha256": ident["config_sha256"],
        "python": ident["python"],
        "host_class": ident["host_class"],
        "mode": mode,
        "modules": modules,
        "result": "PASS",
        "receipt": receipt,
    }
    atomic_write(cache_file(ident["key"]), payload)
    print(f"recorded {ident['key']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("key")
    check = sub.add_parser("check")
    check.add_argument("--need", choices=MODES, default=None)
    rec = sub.add_parser("record")
    rec.add_argument("--mode", choices=MODES, default=None)
    rec.add_argument("--modules", nargs="*", default=[])
    rec.add_argument("--selection", default=None)
    rec.add_argument("--receipt", default=None)
    rec.add_argument("--result", default="PASS")
    args = ap.parse_args(argv)
    root = (args.root or repo_root()).resolve()
    if args.cmd == "key":
        return cmd_key(root)
    if args.cmd == "check":
        return cmd_check(root, args.need)
    return cmd_record(root, args)


if __name__ == "__main__":
    raise SystemExit(main())
