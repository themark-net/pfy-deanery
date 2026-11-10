#!/usr/bin/env python3
"""Four advisory cases for the pinned bumblebee wrapper.

The clean, git-selector, and plaintext-env fixtures run through
scripts/integrations/sandlock/wrap.py with PFY_SANDLOCK=all and
SANDLOCK_BIN=scripts/integrations/sandlock/confine.py. Writes stay under
a temp stage directory. The home-refuse case uses a temp HOME and a
sentinel binary. It must exit 2 before that sentinel starts.

Exit 0: all four cases match and no wrap logged "sandlock: unsandboxed".
Exit 1: the tool ran and a case missed, or a run was unsandboxed.
Exit 2: the binary or sandlock is missing, or a case timed out.
Writes results.json beside this file. No host home path and no env value.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "pfy_mcp_scan.py"
WRAP = ROOT / "scripts" / "integrations" / "sandlock" / "wrap.py"
CONFINE = ROOT / "scripts" / "integrations" / "sandlock" / "confine.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
OUT = Path(__file__).resolve().parent / "results.json"
TOKEN_VALUE = "fixture-not-a-secret"
PIN_SHA256 = "3b46f98ab8fa6345a5d39c7483ff37c51b2ee7699aabe51f2a54133f357f6c7a"


def cache_binary() -> Path | None:
    home = os.environ.get("HOME") or str(Path.home())
    path = Path(home) / ".cache" / "pfy" / "tools" / "bumblebee" / "bumblebee"
    if path.is_file() and os.access(path, os.X_OK):
        return path
    return None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def run_wrapped(root: Path, stage: Path, cache: Path) -> tuple[int, str, str, int]:
    stage.mkdir(parents=True, exist_ok=True)
    (stage / "tmp").mkdir(exist_ok=True)
    out = stage / "scan.json"
    binary = cache_binary()
    reads = [str(root.resolve())]
    if binary is not None:
        reads.append(str(binary.parent.resolve()))
    env = os.environ.copy()
    env.update({
        "PFY_SANDLOCK": "all",
        "SANDLOCK_BIN": str(CONFINE),
        "SANDLOCK_STAGE": str(stage),
        "SANDLOCK_PROFILE": str(stage / "profile.json"),
        "TMPDIR": str(stage / "tmp"),
        "SANDLOCK_EXTRA_READS": ":".join(reads),
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    proc = subprocess.run(
        [
            sys.executable,
            str(WRAP),
            "--cache",
            str(cache),
            "--action",
            "run",
            "--",
            sys.executable,
            str(SCRIPT),
            "--root",
            str(root),
            "--out",
            str(out),
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=150,
    )
    unsandboxed = sum(
        1 for line in proc.stderr.splitlines() if line.strip() == "sandlock: unsandboxed"
    )
    return proc.returncode, proc.stdout, proc.stderr, unsandboxed


def load_scan(stage: Path) -> dict:
    path = stage / "scan.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def kinds(scan: dict) -> list[str]:
    found = []
    for row in scan.get("findings") or []:
        if isinstance(row, dict) and row.get("kind"):
            found.append(str(row["kind"]))
    return found


def keys(scan: dict) -> list[str]:
    found = []
    for row in scan.get("findings") or []:
        if isinstance(row, dict) and row.get("key"):
            found.append(str(row["key"]))
    return found


def case_scan(name: str, work: Path) -> dict:
    root = FIXTURES / name
    stage = work / name / "stage"
    cache = work / name / "wrap"
    code, stdout, stderr, unsandboxed = run_wrapped(root, stage, cache)
    scan = load_scan(stage)
    leaked = TOKEN_VALUE in stdout or TOKEN_VALUE in stderr or TOKEN_VALUE in json.dumps(scan)
    row = {
        "name": name,
        "exit": code,
        "verdict": scan.get("verdict", ""),
        "kinds": kinds(scan),
        "keys": keys(scan),
        "findings": len(scan.get("findings") or []),
        "value_leaked": leaked,
        "unsandboxed_lines": unsandboxed,
        "sandboxed": unsandboxed == 0 and code != 127,
    }
    return row


def expect_clean(row: dict) -> str:
    if row["exit"] != 0 or row["verdict"] != "CLEAN" or row["findings"] != 0:
        return "clean fixture was not CLEAN with zero findings"
    if row["value_leaked"] or row["unsandboxed_lines"]:
        return "clean fixture leaked a value or left the sandbox"
    return ""


def expect_git(row: dict) -> str:
    if row["exit"] != 1 or "git-selector" not in row["kinds"]:
        return "git selector was not an advisory"
    if row["value_leaked"] or row["unsandboxed_lines"]:
        return "git selector leaked a value or left the sandbox"
    return ""


def expect_env(row: dict) -> str:
    if row["exit"] != 1 or "plaintext-env" not in row["kinds"] or "API_TOKEN" not in row["keys"]:
        return "plaintext env key was not named"
    if row["value_leaked"] or row["unsandboxed_lines"]:
        return "plaintext env value was printed or the run left the sandbox"
    return ""


def case_home(work: Path) -> dict:
    home = work / "home"
    home.mkdir()
    started = work / "started"
    sentinel = work / "sentinel"
    sentinel.write_text(
        "#!/bin/sh\nprintf started > %s\nexit 0\n" % json.dumps(str(started)),
        encoding="utf-8",
    )
    sentinel.chmod(sentinel.stat().st_mode | stat.S_IEXEC)
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["PFY_BUMBLEBEE_BIN"] = str(sentinel)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(home), "--out", str(work / "out.json")],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    refused = "refusing to scan" in proc.stdout
    return {
        "name": "home-refuse",
        "exit": proc.returncode,
        "refused": refused,
        "sentinel_started": started.exists(),
        "sandboxed": False,
        "note": "exits before the binary; a temp HOME, not the real home",
    }


def expect_home(row: dict) -> str:
    if row["exit"] != 2 or not row["refused"] or row["sentinel_started"]:
        return "home root was not refused before the binary started"
    return ""


def tool_version(binary: Path, work: Path) -> str:
    stage = work / "version-stage"
    stage.mkdir()
    env = os.environ.copy()
    env.update({
        "PFY_SANDLOCK": "all",
        "SANDLOCK_BIN": str(CONFINE),
        "SANDLOCK_STAGE": str(stage),
        "TMPDIR": str(stage),
        "SANDLOCK_EXTRA_READS": str(binary.parent.resolve()),
    })
    proc = subprocess.run(
        [
            sys.executable,
            str(WRAP),
            "--cache",
            str(work / "version-wrap"),
            "--action",
            "run",
            "--",
            str(binary),
            "version",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    line = ""
    combined = proc.stdout.splitlines() + proc.stderr.splitlines()
    for candidate in combined:
        text = candidate.strip()
        if text.lower().startswith("bumblebee"):
            line = text
            break
    if not line or len(line) > 80 or "/" in line or "~" in line:
        return ""
    return line


def main() -> int:
    binary = cache_binary()
    if binary is None or not CONFINE.is_file() or not WRAP.is_file():
        print("missing bumblebee binary or sandlock wrapper", file=sys.stderr)
        return 2
    digest = sha256(binary)
    with tempfile.TemporaryDirectory(prefix="pfy-bumblebee-probe-") as tmp:
        work = Path(tmp)
        try:
            clean = case_scan("clean", work)
            git_row = case_scan("git-selector", work)
            env_row = case_scan("plaintext-env", work)
            home_row = case_home(work)
            version = tool_version(binary, work)
        except subprocess.TimeoutExpired:
            print("probe timed out", file=sys.stderr)
            return 2
    checks = {
        "clean": expect_clean(clean),
        "git-selector": expect_git(git_row),
        "plaintext-env": expect_env(env_row),
        "home-refuse": expect_home(home_row),
    }
    passed = [name for name, problem in checks.items() if not problem]
    unsandboxed = clean["unsandboxed_lines"] + git_row["unsandboxed_lines"] + env_row["unsandboxed_lines"]
    doc = {
        "metric": "advisory_cases",
        "passed": len(passed),
        "cases": 4,
        "binary_sha256": digest,
        "binary_sha256_matches_pin": digest == PIN_SHA256,
        "tool_version": version,
        "unsandboxed_lines": unsandboxed,
        "sandbox": "sandlock" if unsandboxed == 0 else "",
        "failures": {name: problem for name, problem in checks.items() if problem},
        "cases_detail": [clean, git_row, env_row, home_row],
    }
    OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    if digest != PIN_SHA256:
        print("binary sha256 does not match the v0.1.2 pin", file=sys.stderr)
        return 1
    if unsandboxed:
        print("sandlock: unsandboxed", file=sys.stderr)
        return 1
    if len(passed) != 4:
        print("probe cases missed: %s" % ", ".join(sorted(doc["failures"])), file=sys.stderr)
        return 1
    print("advisory_cases 4/4 sandbox sandlock")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
