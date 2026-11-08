#!/usr/bin/env python3
"""Turn a passthrough argv into one real `sandlock run`.

wrap.py calls this file the same way it calls the test double: `binary true`
for the self-test, then `binary COMMAND...` for the user command. The real
binary does not exec that argv. This adapter builds `sandlock run` with
read grants on the system dirs, a write grant on SANDLOCK_STAGE and on the
start-marker directory, default-deny network, and `--clean-env`.

SANDLOCK_REAL selects the binary. When it is unset, the cache unpack path
is used. A missing binary exits 1 before exec so wrap.py can fall open.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

READS = ("/usr", "/lib", "/lib64", "/bin", "/etc")
SELF_TEST_TIMEOUT = 30
COMMAND_TIMEOUT = "120"


def find_real() -> str | None:
    raw = os.environ.get("SANDLOCK_REAL", "").strip()
    candidates = []
    if raw:
        candidates.append(Path(raw))
    else:
        candidates.append(Path.home() / ".cache" / "pfy" / "tools" / "sandlock" / "unpack" / "sandlock")
    here = Path(__file__).resolve()
    for path in candidates:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved == here:
            continue
        if resolved.is_file() and os.access(resolved, os.X_OK):
            return str(resolved)
    return None


def extra_reads(cmd: list[str]) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for arg in cmd:
        if not arg.startswith("/"):
            continue
        path = Path(arg)
        target = path if path.is_dir() else path.parent if path.is_file() else None
        if target is None:
            continue
        text = str(target)
        if text not in seen:
            seen.add(text)
            found.append(text)
    return found


def build_run(real: str, cmd: list[str]) -> list[str]:
    argv = [real, "run"]
    for path in READS:
        if os.path.isdir(path):
            argv.extend(["-r", path])
    for path in extra_reads(cmd):
        argv.extend(["-r", path])
    writes: list[str] = []
    started = os.environ.get("SANDLOCK_STARTED", "").strip()
    if started:
        parent = str(Path(started).parent)
        writes.append(parent)
        argv.extend(["--env", "SANDLOCK_STARTED=%s" % started])
    stage = os.environ.get("SANDLOCK_STAGE", "").strip()
    if stage:
        writes.append(stage)
        argv.extend(["--env", "SANDLOCK_STAGE=%s" % stage])
    for key in ("PATH", "LANG", "LC_ALL", "TMPDIR"):
        value = os.environ.get(key, "")
        if value:
            argv.extend(["--env", "%s=%s" % (key, value)])
    seen: set[str] = set()
    for write in writes:
        if write in seen:
            continue
        seen.add(write)
        argv.extend(["-w", write, "-r", write])
    argv.extend(["--clean-env", "--timeout", COMMAND_TIMEOUT, "--"])
    argv.extend(cmd)
    return argv


def self_test(real: str) -> bool:
    try:
        check = subprocess.run([real, "check"], timeout=SELF_TEST_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return False
    if check.returncode != 0:
        return False
    true_bin = "/bin/true" if os.path.isfile("/bin/true") else "/usr/bin/true"
    try:
        proc = subprocess.run(build_run(real, [true_bin]), timeout=SELF_TEST_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def main(argv: list[str] | None = None) -> int:
    cmd = list(sys.argv[1:] if argv is None else argv)
    if not cmd:
        print("usage: confine.py true | COMMAND...", file=sys.stderr)
        return 2
    real = find_real()
    if real is None:
        return 1
    if cmd == ["true"]:
        return 0 if self_test(real) else 1
    try:
        os.execv(real, build_run(real, cmd))
    except OSError:
        return 1
    return 127


if __name__ == "__main__":
    raise SystemExit(main())
