#!/usr/bin/env python3
"""Run one fetched-tool install or tool run, optionally under sandlock.

PFY_SANDLOCK=auto (the default) sandboxes action=install only, and only
after SANDLOCK_BIN passes a self-test of `true`. PFY_SANDLOCK=all also
sandboxes action=run. PFY_SANDLOCK=off keeps the direct command.

A missing binary, a failed self-test, a timeout before the command starts,
or a sandlock exit before exec logs `sandlock: unsandboxed` and runs the
command once. A command that already started keeps its exit code.

State for one call lives in --cache: an advisory lock and a success receipt
keyed by action, the exact command, and SANDLOCK_BIN. A second successful
call with the same binary exits 0 and does not run the command. An empty
SANDLOCK_BIN is a different key, so a later unsandboxed call still runs.
Two caches do not share the lock.

Self-test timeout is 30 seconds. The command timeout is 120 seconds.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

SELF_TEST_TIMEOUT = 30
COMMAND_TIMEOUT = 120
STARTED_ENV = "SANDLOCK_STARTED"
STARTER = (
    "import os, sys\n"
    "from pathlib import Path\n"
    "Path(os.environ['SANDLOCK_STARTED']).write_text('1')\n"
    "os.execvp(sys.argv[1], sys.argv[1:])\n"
)


def parse_args(argv: list[str]) -> tuple[Path, str, list[str]]:
    parser = argparse.ArgumentParser(description="Sandbox one install or run.")
    parser.add_argument("--cache", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("cmd", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    cmd = list(args.cmd)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    action = str(args.action).strip().lower()
    if action not in ("install", "run") or not cmd:
        print("usage: wrap.py --cache DIR --action install|run -- COMMAND", file=sys.stderr)
        raise SystemExit(2)
    return Path(args.cache), action, cmd


def sandbox_wanted(action: str) -> bool:
    mode = os.environ.get("PFY_SANDLOCK", "auto").strip().lower()
    if mode in ("", "auto"):
        return action == "install"
    if mode == "all":
        return True
    if mode in ("0", "off", "false", "no"):
        return False
    return action == "install"


def binary_path() -> str | None:
    raw = os.environ.get("SANDLOCK_BIN")
    if raw is None or not raw.strip():
        return None
    path = Path(raw.strip())
    if path.is_file() and os.access(path, os.X_OK):
        return str(path)
    return None


def log_unsandboxed() -> None:
    print("sandlock: unsandboxed", file=sys.stderr)


def reset_log() -> None:
    """This invocation owns SANDLOCK_LOG. A skipped call leaves the file."""
    raw = os.environ.get("SANDLOCK_LOG", "").strip()
    if not raw:
        return
    path = Path(raw)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    except OSError:
        return


def receipt_file(cache: Path, action: str, cmd: list[str]) -> Path:
    # The binary is part of the key so a later unsandboxed call is not
    # treated as a repeat of a sandboxed success for the same command.
    blob = json.dumps(
        {
            "action": action,
            "cmd": cmd,
            "bin": os.environ.get("SANDLOCK_BIN", ""),
        },
        separators=(",", ":"),
        ensure_ascii=True,
    )
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return cache / "done" / (digest + ".json")


def success_recorded(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(data, dict) and data.get("rc") == 0


def record_success(path: Path, action: str, cmd: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps({"action": action, "cmd": cmd, "rc": 0}, indent=2) + "\n"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(body, encoding="utf-8")
    os.replace(tmp, path)


def self_test(binary: str) -> bool:
    try:
        proc = subprocess.run([binary, "true"], timeout=SELF_TEST_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def sandboxed(binary: str, cmd: list[str], cache: Path) -> tuple[int, bool]:
    started_dir = cache / "started"
    started_dir.mkdir(parents=True, exist_ok=True)
    marker = started_dir / ("%d-%d" % (os.getpid(), time.time_ns()))
    env = os.environ.copy()
    env[STARTED_ENV] = str(marker)
    argv = [binary, sys.executable, "-c", STARTER, *cmd]
    try:
        proc = subprocess.run(argv, env=env, timeout=COMMAND_TIMEOUT)
        code = proc.returncode
    except subprocess.TimeoutExpired:
        code = 124
    except OSError:
        code = 127
    started = marker.is_file()
    try:
        if marker.exists():
            marker.unlink()
    except OSError:
        pass
    return code, started


def direct(cmd: list[str]) -> int:
    try:
        proc = subprocess.run(cmd, timeout=COMMAND_TIMEOUT)
    except subprocess.TimeoutExpired:
        return 124
    except OSError:
        return 127
    return proc.returncode


def run_locked(cache: Path, action: str, cmd: list[str]) -> int:
    done = receipt_file(cache, action, cmd)
    if success_recorded(done):
        return 0
    reset_log()
    if sandbox_wanted(action):
        binary = binary_path()
        if binary and self_test(binary):
            code, started = sandboxed(binary, cmd, cache)
            if started:
                if code == 0:
                    record_success(done, action, cmd)
                return code
        log_unsandboxed()
    code = direct(cmd)
    if code == 0:
        record_success(done, action, cmd)
    return code


def main(argv: list[str] | None = None) -> int:
    cache, action, cmd = parse_args(sys.argv[1:] if argv is None else argv)
    cache.mkdir(parents=True, exist_ok=True)
    lock_path = cache / "lock"
    lock_fh = lock_path.open("a+")
    try:
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        return run_locked(cache, action, cmd)
    finally:
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        lock_fh.close()


if __name__ == "__main__":
    raise SystemExit(main())
