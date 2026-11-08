#!/usr/bin/env python3
"""Local shim for the mco probe. Reads the gap-b fixture and prints one blocker line."""

import os
import sys
import time
from pathlib import Path


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "--version":
        print("mco-probe-stub 1")
        return 0
    if len(sys.argv) < 2:
        print("blocker: missing-role")
        return 1
    role = sys.argv[1]
    prompt = " ".join(sys.argv[2:])
    log_path = os.environ.get("MCO_PROBE_LOG", "")
    started = time.time()
    if log_path:
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write("start %s %.6f %s\n" % (role, started, os.getpid()))
    time.sleep(0.6)
    fixture = None
    for token in prompt.split():
        path = Path(token.strip(".,;:"))
        if path.is_file():
            fixture = path
            break
    if fixture is None:
        print("blocker: fixture-missing")
        if log_path:
            with open(log_path, "a", encoding="utf-8") as handle:
                handle.write("end %s %.6f %s\n" % (role, time.time(), os.getpid()))
        return 1
    text = fixture.read_text(encoding="utf-8")
    if role == "timeout":
        line = "blocker: timeout 3h" if "TIMEOUT_HOURS=3" in text else "blocker: timeout-not-found"
    elif role == "pregate":
        line = "blocker: pregate fails 2" if "PREGATE_FAIL_COUNT=2" in text else "blocker: pregate-not-found"
    else:
        line = "blocker: unknown-role"
    ok = line.startswith("blocker: ") and not line.endswith("not-found") and "unknown-role" not in line
    print(line)
    if log_path:
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write("end %s %.6f %s\n" % (role, time.time(), os.getpid()))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
