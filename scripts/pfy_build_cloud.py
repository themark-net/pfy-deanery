#!/usr/bin/env python3
"""pfy build "<task>": daily cloud Grok build.

The checkout this process was started from is never switched, reset, stashed,
or committed. Work happens in a detached git worktree under <repo>/tmp/.
Nothing is pushed and no PR is opened. This runner does not read auth.json
and does not start a local model.

Exit codes:
  0  PASS, or a clean --dry-run, or --reap
  1  FAIL (review reject, no-change spent, scope mismatch, unauthenticated,
        interrupted, gate spent, worktree-failed)
  2  usage
  3  TIMEOUT (grok)
  4  BLOCKED (rate-limit)

Receipt schema: pfy-cloud-build/1
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_TIMEOUT = 3
EXIT_BLOCKED = 4

SCHEMA = "pfy-cloud-build/1"
DEFAULT_TEST_CMD = "python3 -m unittest discover -s tests -t ."
DEFAULT_TIMEOUT = 1200.0
DEFAULT_RETRIES = 2

HELP_TEXT = """\
Daily cloud build.

  ./pfy build "<task>"

-p is the jev dogfood wrap (./pfy build -p "<prompt>").
--local is the opt-in fallback (./pfy build --local "<task>").
"""


class UsageError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _git(repo: Path, args: list[str], timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def resolve_repo(raw: str | None) -> Path:
    start = Path(raw).resolve() if raw else Path.cwd()
    if not start.exists():
        raise UsageError("repo path does not exist: %s" % start)
    probe = start if start.is_dir() else start.parent
    proc = _git(probe, ["rev-parse", "--show-toplevel"])
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        raise UsageError("not a git repo: %s" % start)
    return Path(proc.stdout.strip()).resolve()


def resolve_base(repo: Path, requested: str | None) -> str:
    if requested and requested.strip():
        ref = requested.strip()
    else:
        probe = _git(repo, ["rev-parse", "--verify", "--quiet", "origin/main"])
        ref = "origin/main" if probe.returncode == 0 else "HEAD"
    sha = _git(repo, ["rev-parse", "--verify", ref])
    if sha.returncode != 0 or not (sha.stdout or "").strip():
        raise UsageError("base ref not found: %s" % ref)
    return ref


def default_receipt_dir(repo: Path, stamp: str) -> Path:
    return repo / "pipelines" / "dogfood" / "build-cloud" / stamp


def write_receipt(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pfy build",
        description=HELP_TEXT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("task", nargs="*", help='task text for ./pfy build "<task>"')
    parser.add_argument("--repo", default=None, help="git repo to build (default: cwd)")
    parser.add_argument(
        "--base",
        default=None,
        help="base ref (default: origin/main if it exists, else HEAD)",
    )
    parser.add_argument("--test-cmd", default=DEFAULT_TEST_CMD, help="gate command")
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="extra attempts after the first (default 2, so 3 total)",
    )
    parser.add_argument("--no-review", action="store_true", help="one attempt, no review call")
    parser.add_argument("--receipt-dir", default=None, help="directory for receipt.json")
    parser.add_argument("--dry-run", action="store_true", help="write a receipt and start no grok")
    parser.add_argument("--reap", action="store_true", help="recover a cloud pid with no receipt")
    parser.add_argument("--keep-worktree", action="store_true", help="keep the worktree after PASS")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="seconds for one grok call")
    parser.add_argument(
        "--grok-cmd",
        default=None,
        help="grok binary (default: env PFY_BUILD_GROK, else grok on PATH)",
    )
    args = parser.parse_args(argv)
    if args.retries < 0:
        raise UsageError("--retries must be >= 0")
    if args.timeout <= 0:
        raise UsageError("--timeout must be > 0")
    if len(args.task) > 1:
        raise UsageError('usage: ./pfy build "<task>"')
    args.task_text = args.task[0] if args.task else ""
    if not args.grok_cmd:
        args.grok_cmd = os.environ.get("PFY_BUILD_GROK") or ""
    return args


def _dry_run_receipt(args, repo: Path, base: str, receipt: Path) -> dict:
    return {
        "schema": SCHEMA,
        "status": "DRY-RUN",
        "reason": "dry-run",
        "exit_code": EXIT_OK,
        "branch": None,
        "commit": None,
        "base": base,
        "review": {"verdict": None, "reasons": []},
        "attempts": [],
        "gate": {"cmd": args.test_cmd, "before": None, "after": None},
        "recovery": "",
        "pushed": False,
        "worktree_removed": False,
        "task": args.task_text,
        "finished_at": _now(),
        "receipt": str(receipt),
    }


def _print_usage() -> None:
    print(HELP_TEXT, file=sys.stderr)
    print('usage: ./pfy build "<task>"', file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        args = parse_args(argv)
    except UsageError as exc:
        _print_usage()
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE
    if args.reap:
        print("FAIL: reap is not available yet", file=sys.stderr)
        return EXIT_USAGE
    if not args.task_text:
        _print_usage()
        return EXIT_USAGE
    try:
        repo = resolve_repo(args.repo)
        base = resolve_base(repo, args.base)
    except UsageError as exc:
        _print_usage()
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE
    stamp = _stamp()
    receipt_dir = Path(args.receipt_dir).resolve() if args.receipt_dir else default_receipt_dir(repo, stamp)
    receipt = receipt_dir / "receipt.json"
    if args.dry_run:
        payload = _dry_run_receipt(args, repo, base, receipt)
        write_receipt(receipt, payload)
        print("DRY-RUN dry-run branch=none receipt=%s" % receipt)
        return EXIT_OK
    print("FAIL: cloud build loop is not available yet", file=sys.stderr)
    return EXIT_FAIL


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(EXIT_OK)
    except UsageError as exc:
        _print_usage()
        print(str(exc), file=sys.stderr)
        sys.exit(EXIT_USAGE)
