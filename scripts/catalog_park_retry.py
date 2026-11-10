#!/usr/bin/env python3
"""Re-open parked catalog lanes once main is green, with a cap and a backoff.

Most lane parks on Nov 8 were "run_tests failed" while main itself was red.
Nothing ever re-opened them, so the slugs sat in needs-mark. The catalog
loop calls this once per tick, before it writes needs-mark and before it
launches lanes:

  catalog_park_retry.py --repo "$PWD" --dir eval="$STATE/eval" \
      --dir integrate="$STATE/integrate" [--history FILE]

For each <dir>/<slug>.parked:
  1. Record it in park-history.tsv (once per park): slug, kind, reason,
     parked_at (marker mtime, UTC), retries so far, origin/main SHA.
  2. Re-open it only when all of these hold, else leave it and print why:
       the reason is one a green main can fix (RETRYABLE, or a
       RETRYABLE_PREFIXES prefix such as "receipt run failed")   not-retryable
       retries so far are under --max-retries (default 2)        cap
       now >= parked_at + backoff * 2**retries (default 2 h)     backoff
       the lane worktree <dir>/wt/<slug>, if any, is clean       dirty-worktree
       today's branch bot/<kind>-<slug>-<mmdd> does not exist    branch-exists
       eval-structural on origin/main's SHA concluded success    main-not-green
  3. Re-open: remove the clean worktree (its branch and commits stay),
     rename <slug>.parked to <slug>.parked.<n>, drop <slug>.dispatched,
     write <slug>.retry-count n. The loop's normal launch path then picks
     the slug up, so the 20-a-day and 4-at-once caps still apply.

Main green is read from the public GitHub API, no token. PFY_MAIN_GREEN=1
or 0 overrides it (tests). Any API error counts as not green. The API is
called only when some park would otherwise retry. Prints one line per
park: "retry <kind> <slug> <n>" or "hold <kind> <slug> <why>".
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

RETRYABLE = (
    "run_tests failed",
    "test_select failed",
    "git fetch failed",
    "rebase failed",
    "land failed",
    "push failed",
)
# Prefixes a green main can also fix (the receipt reruns on the new main).
RETRYABLE_PREFIXES = ("receipt run failed",)
HISTORY_HEADER = "slug\tkind\treason\tparked_at\tretries\tmain_sha\n"


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=60)


def main_sha(repo: Path) -> str:
    out = git(repo, "rev-parse", "origin/main")
    return out.stdout.strip() if out.returncode == 0 else ""


def github_slug(repo: Path) -> str:
    url = git(repo, "remote", "get-url", "origin").stdout.strip()
    for mark in ("github.com:", "github.com/"):
        if mark in url:
            tail = url.split(mark, 1)[1]
            return tail[:-4] if tail.endswith(".git") else tail
    return ""


def main_green(repo: Path, sha: str) -> bool:
    forced = os.environ.get("PFY_MAIN_GREEN")
    if forced is not None:
        return forced == "1"
    slug = github_slug(repo)
    if not slug or not sha:
        return False
    url = f"https://api.github.com/repos/{slug}/actions/workflows/eval-structural.yml/runs?head_sha={sha}&per_page=5"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "pfy-park-retry"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            runs = json.load(resp).get("workflow_runs", [])
    except Exception:
        return False
    done = [r for r in runs if r.get("head_sha") == sha and r.get("status") == "completed"]
    return bool(done) and done[0].get("conclusion") == "success"


def read_count(path: Path) -> int:
    try:
        return max(0, int(path.read_text(encoding="utf-8").split()[0]))
    except (OSError, ValueError, IndexError):
        return 0


def record(history: Path, row: tuple[str, ...]) -> None:
    key = "\t".join(row[:4])
    if history.is_file():
        for line in history.read_text(encoding="utf-8").splitlines():
            if line.startswith(key + "\t"):
                return
    history.parent.mkdir(parents=True, exist_ok=True)
    new = not history.is_file()
    with history.open("a", encoding="utf-8") as fh:
        if new:
            fh.write(HISTORY_HEADER)
        fh.write("\t".join(row) + "\n")


def run(repo: Path, dirs: list[tuple[str, Path]], history: Path, now: float, cap: int, backoff_h: float) -> list[str]:
    out: list[str] = []
    sha = main_sha(repo)
    green: bool | None = None
    today = time.strftime("%m%d", time.gmtime(now))
    for kind, base in dirs:
        if not base.is_dir():
            continue
        for parked in sorted(base.glob("*.parked")):
            slug = parked.name[: -len(".parked")]
            try:
                reason = (parked.read_text(encoding="utf-8").splitlines() or [""])[0].strip()
                mtime = parked.stat().st_mtime
            except OSError:
                continue
            count_path = base / f"{slug}.retry-count"
            n = read_count(count_path)
            parked_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(mtime))
            record(history, (slug, kind, reason or "-", parked_at, str(n), sha or "-"))
            why = ""
            wt = base / "wt" / slug
            if reason not in RETRYABLE and not reason.startswith(RETRYABLE_PREFIXES):
                why = "not-retryable"
            elif n >= cap:
                why = "cap"
            elif now < mtime + backoff_h * 3600 * (2 ** n):
                why = "backoff"
            elif wt.exists() and git(wt, "status", "--porcelain").stdout.strip():
                why = "dirty-worktree"
            elif git(repo, "rev-parse", "--verify", "-q", f"refs/heads/bot/{kind}-{slug}-{today}").returncode == 0:
                why = "branch-exists"
            else:
                if green is None:
                    green = main_green(repo, sha)
                if not green:
                    why = "main-not-green"
            if why:
                out.append(f"hold {kind} {slug} {why}")
                continue
            if wt.exists():
                rm = git(repo, "worktree", "remove", str(wt))
                if rm.returncode != 0:
                    out.append(f"hold {kind} {slug} worktree-remove-failed")
                    continue
            n += 1
            parked.rename(base / f"{slug}.parked.{n}")
            (base / f"{slug}.dispatched").unlink(missing_ok=True)
            count_path.write_text(f"{n}\n", encoding="utf-8")
            out.append(f"retry {kind} {slug} {n}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Re-open parked lanes once main is green.")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--dir", action="append", default=[], help="kind=path, e.g. eval=$STATE/eval")
    parser.add_argument("--history", help="default: park-history.tsv beside the first --dir")
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument("--backoff-hours", type=float, default=2.0)
    parser.add_argument("--now", type=float, help="epoch seconds (tests)")
    args = parser.parse_args(argv)
    dirs: list[tuple[str, Path]] = []
    for item in args.dir:
        kind, sep, path = item.partition("=")
        if not sep or kind not in ("eval", "integrate") or not path:
            sys.stderr.write(f"bad --dir {item!r}\n")
            return 2
        dirs.append((kind, Path(path)))
    if not dirs:
        sys.stderr.write("no --dir\n")
        return 2
    history = Path(args.history) if args.history else dirs[0][1].parent / "park-history.tsv"
    now = args.now if args.now is not None else time.time()
    for line in run(Path(args.repo), dirs, history, now, args.max_retries, args.backoff_hours):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
