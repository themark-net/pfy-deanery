#!/usr/bin/env python3
"""Turn a passthrough argv into one real `sandlock run`.

wrap.py calls this file the same way it calls the test double: `binary true`
for the self-test, then `binary COMMAND...` for the user command. The real
binary does not exec that argv. This adapter builds `sandlock run` with
read grants on the system dirs, a write grant on SANDLOCK_STAGE and on the
start-marker directory, default-deny network, and `--clean-env`.

SANDLOCK_REAL selects the binary. When it is unset, the cache unpack path
is used. A missing binary exits 1 before exec so wrap.py can fall open.

SANDLOCK_EXTRA_READS (colon list) adds read grants, for example the
directory of a pinned tool binary. SANDLOCK_PROFILE, when set, names a JSON
file that gets the profile of the run this adapter builds, just before exec:
reads, writes, network "deny", clean_env, sudo false, and the timeout. The
home directory is written as $HOME. data/promotion-rules.json rule
S-profile-readonly reads that profile from the sandbox trial
(scripts/integrations/sandlock/trial.py). The self-test of `true` writes no
profile.
"""

from __future__ import annotations

import json
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


def env_reads() -> list[str]:
    raw = os.environ.get("SANDLOCK_EXTRA_READS", "")
    return [item for item in raw.split(":") if item.startswith("/") and os.path.isdir(item)]


def _label(path: str) -> str:
    home = str(Path.home())
    if path == home or path.startswith(home + "/"):
        return "$HOME" + path[len(home):]
    return path


def profile_of(argv: list[str], cmd: list[str]) -> dict:
    """What the sandlock run built from argv allows. Paths under the home are $HOME/..."""
    reads: list[str] = []
    writes: list[str] = []
    index = 0
    while index < len(argv):
        item = argv[index]
        if item == "--":
            break
        if item in ("-r", "-w") and index + 1 < len(argv):
            target = reads if item == "-r" else writes
            label = _label(argv[index + 1])
            if label not in target:
                target.append(label)
            index += 2
            continue
        index += 1
    names = {os.path.basename(part) for part in cmd}
    return {
        "sandbox": "sandlock",
        "reads": reads,
        "writes": writes,
        "network": "deny",
        "clean_env": "--clean-env" in argv,
        "sudo": bool(names & {"sudo", "doas", "pkexec", "su"}) or os.geteuid() == 0,
        "timeout_sec": int(COMMAND_TIMEOUT),
    }


def write_profile(argv: list[str], cmd: list[str]) -> None:
    raw = os.environ.get("SANDLOCK_PROFILE", "").strip()
    if not raw:
        return
    path = Path(raw)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile_of(argv, cmd), indent=2) + "\n", encoding="utf-8")


def build_run(real: str, cmd: list[str]) -> list[str]:
    argv = [real, "run"]
    for path in READS:
        if os.path.isdir(path):
            argv.extend(["-r", path])
    for path in extra_reads(cmd) + env_reads():
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
    # Shell scripts redirect to /dev/null. Writing there reaches no file.
    if os.path.exists("/dev/null"):
        writes.append("/dev/null")
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
    argv = build_run(real, cmd)
    try:
        write_profile(argv, cmd)
    except OSError:
        return 1
    try:
        os.execv(real, argv)
    except OSError:
        return 1
    return 127


if __name__ == "__main__":
    raise SystemExit(main())
