#!/usr/bin/env python3
"""Offline kanbots probe for gap B.

Runs the pinned dispatcher worktree helpers on a throwaway git repo.
Does not spawn Claude, Codex, OpenCode, or Electron, and does not start
./pfy build. Writes results.json next to this file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pwd
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "results.json"
MEASURE = Path(__file__).resolve().parent / "measure.mjs"
PIN = "7b256a024e65268d359ab3286e6c5d2c3d63a072"
TAG = "v1.2.0"
TAG_COMMIT = "80a978c590b5cb13fdb5c8aa0ec15479e8a422cc"
APPIMAGE_SHA256 = "e7466c7ca3bc02a2e04ea664c194121104ea8bdfc134a5e6078c48bddc917b6a"

CLIS = [
    ("claude-code", "claude"),
    ("codex", "codex"),
    ("gemini", "gemini"),
    ("cursor", "cursor-agent"),
    ("copilot", "gh-copilot"),
    ("amp", "amp"),
    ("opencode", "opencode"),
    ("droid", "droid"),
    ("ccr", "ccr"),
    ("qwen", "qwen"),
    ("acp", None),
]

GAP = (
    "Gap B: ./pfy build is not proven bot-usable. "
    "The 2026-11-06 trial hit the 3 hour timeout. "
    "The recheck fix is parked after two pregate FAILs.\n"
)


def cache_base() -> Path:
    return Path.home() / ".cache" / "pfy" / "tools" / "kanbots"


def real_home() -> Path:
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def run(cmd: list[str], cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)


def git_env(home: Path, tmp: Path) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(home),
        "TMPDIR": str(tmp),
        "LANG": "C.UTF-8",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_AUTHOR_NAME": "kanbots-probe",
        "GIT_AUTHOR_EMAIL": "probe@example.com",
        "GIT_COMMITTER_NAME": "kanbots-probe",
        "GIT_COMMITTER_EMAIL": "probe@example.com",
    }


def require_pin(src: Path) -> str:
    if not (src / ".git").exists():
        print(f"SKIPPED checkout missing at {src}", file=sys.stderr)
        raise SystemExit(2)
    head = subprocess.check_output(["git", "-C", str(src), "rev-parse", "HEAD"], text=True).strip()
    if head != PIN:
        print(f"SKIPPED pin mismatch: {head} != {PIN}", file=sys.stderr)
        raise SystemExit(2)
    return head


def appimage_check() -> dict[str, object]:
    path = cache_base() / "kanbots-1.2.0-linux-x64.AppImage"
    if not path.is_file():
        return {"present": False, "sha256_match": False}
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    got = digest.hexdigest()
    return {
        "present": True,
        "bytes": path.stat().st_size,
        "sha256_match": got == APPIMAGE_SHA256,
    }


def home_markers(home: Path) -> dict[str, bool]:
    return {
        ".kanbots": (home / ".kanbots").exists(),
        ".config/kanbots": (home / ".config" / "kanbots").exists(),
    }


def baseline_worktree(repo: Path, env: dict[str, str]) -> dict[str, float]:
    slot = repo.parent / "baseline-slot"
    t0 = time.perf_counter()
    add = run(["git", "worktree", "add", "-b", "plain/slot-1", str(slot), "HEAD"], repo, env)
    add_s = time.perf_counter() - t0
    if add.returncode != 0:
        return {"ok": 0, "add_s": round(add_s, 4), "error": add.stderr[-300:]}
    t1 = time.perf_counter()
    rm = run(["git", "worktree", "remove", "--force", str(slot)], repo, env)
    rm_s = time.perf_counter() - t1
    run(["git", "branch", "-D", "plain/slot-1"], repo, env)
    return {
        "ok": 1 if rm.returncode == 0 else 0,
        "add_s": round(add_s, 4),
        "remove_s": round(rm_s, 4),
        "total_s": round(add_s + rm_s, 4),
    }


def source_markers(src: Path) -> dict[str, bool]:
    orch = (src / "packages/api/src/autopilot/orchestrator.ts").read_text()
    feature = (src / "packages/api/src/autopilot/feature-dev.ts").read_text()
    checks = (src / "packages/dispatcher/src/checks.ts").read_text()
    cli = (src / "packages/cli/src/cli.ts").read_text()
    return {
        "qa_throws_not_implemented": "is not implemented yet" in orch,
        "feature_dev_loops_until_abort": "while (!signal.aborted)" in feature,
        "feature_dev_has_turn_cap_symbol": any(
            token in feature for token in ("turnCap", "maxIterations", "MAX_TURNS")
        ),
        "session_budget_error": "SessionBudgetExceededError" in feature,
        "check_default_timeout_5_min": "DEFAULT_TIMEOUT_MS = 5 * 60_000" in checks,
        "cli_registers_no_command_call": ".command(" not in cli,
        "supervisor_stamps_after_create": _supervisor_order(src),
    }


def _supervisor_order(src: Path) -> bool:
    text = (src / "packages/api/src/agent-runs/supervisor.ts").read_text()
    create_at = text.find("await makeWorktree(")
    stamp_at = text.find("await stampIdentity(")
    return create_at >= 0 and stamp_at > create_at


def cli_help(src: Path, home: Path, tmp: Path) -> dict[str, object]:
    """Run the published CLI entry. commander is a cache install, not a global one."""
    deps = cache_base() / "cli-deps" / "node_modules" / "commander"
    if not deps.exists():
        return {"skipped": "commander not installed under the cache", "commands": None}
    stage = Path(tempfile.mkdtemp(prefix="kanbots-cli-", dir=tmp))
    pkg = stage / "package.json"
    shutil.copy(src / "packages/cli/package.json", pkg)
    source = stage / "src"
    source.mkdir()
    shutil.copy(src / "packages/cli/src/cli.ts", source / "cli.ts")
    modules = stage / "node_modules"
    modules.mkdir()
    os.symlink(deps, modules / "commander")
    env = git_env(home, tmp)
    env["NODE_NO_WARNINGS"] = "1"
    proc = run(
        ["node", "--experimental-strip-types", str(source / "cli.ts"), "--help"],
        stage,
        env,
    )
    text = (proc.stdout or "") + (proc.stderr or "")
    return {
        "code": proc.returncode,
        "commands_registered_in_source": 0 if ".command(" not in (src / "packages/cli/src/cli.ts").read_text() else 1,
        "help_mentions_subcommand": "Commands:" in text,
        "help_head": "\n".join(text.strip().splitlines()[:8]),
    }


def npm_view(home: Path, tmp: Path) -> dict[str, object]:
    env = git_env(home, tmp)
    env["npm_config_cache"] = str(cache_base() / "npm-cache")
    proc = run(["npm", "view", "kanbots", "version", "--json"], cache_base(), env)
    blob = (proc.stdout or "") + (proc.stderr or "")
    return {
        "code": proc.returncode,
        "not_found": proc.returncode != 0 and "E404" in blob,
    }


def dispatcher_matches_tag(src: Path) -> str:
    proc = subprocess.run(
        [
            "git",
            "-C",
            str(src),
            "diff",
            "--name-only",
            TAG,
            "HEAD",
            "--",
            "packages/dispatcher",
            "packages/cli",
            "packages/api/src/autopilot",
            "packages/api/src/agent-runs/supervisor.ts",
        ],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        return "tag diff failed"
    names = [line for line in proc.stdout.splitlines() if line.strip()]
    return "same" if not names else "differs: " + ", ".join(names)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, default=cache_base() / "src" / "kanbots")
    parser.add_argument("--net", action="store_true")
    args = parser.parse_args()

    src = args.src.resolve()
    head = require_pin(src)
    real = real_home()
    before = home_markers(real)

    home = cache_base() / "home"
    tmp = cache_base() / "tmp"
    home.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)
    env = git_env(home, tmp)

    work = Path(tempfile.mkdtemp(prefix="kanbots-probe-", dir=tmp))
    repo = work / "fixture"
    remote = work / "remote.git"
    repo.mkdir()
    run(["git", "init", "-b", "main", str(remote), "--bare"], work, env)
    run(["git", "init", "-b", "main", str(repo)], work, env)
    (repo / "GAP.md").write_text(GAP)
    run(["git", "add", "GAP.md"], repo, env)
    committed = run(["git", "commit", "-m", "gap B fixture"], repo, env)
    if committed.returncode != 0:
        raise SystemExit(f"fixture commit failed: {committed.stderr}")

    t_base = baseline_worktree(repo, env)
    measure = run(
        [
            "node",
            "--experimental-strip-types",
            "--disable-warning=ExperimentalWarning",
            str(MEASURE),
            "--src",
            str(src),
            "--repo",
            str(repo),
            "--remote",
            str(remote),
        ],
        work,
        env,
    )
    if measure.returncode != 0:
        raise SystemExit(f"measure failed ({measure.returncode}): {measure.stderr[-800:]}")
    measured = json.loads(measure.stdout)

    present = []
    absent = []
    for provider, binary in CLIS:
        found = bool(binary) and shutil.which(binary) is not None
        row = {"provider": provider, "binary": binary, "present": found}
        (present if found else absent).append(row)

    tree = src
    tree_bytes = sum(p.stat().st_size for p in tree.rglob("*") if p.is_file() and ".git" not in p.parts)

    results = {
        "pin": head,
        "tag": TAG,
        "tag_commit": TAG_COMMIT,
        "dispatcher_vs_tag": dispatcher_matches_tag(src),
        "appimage_sha256": APPIMAGE_SHA256,
        "appimage": appimage_check(),
        "source_bytes_without_git": tree_bytes,
        "baseline_git_worktree": t_base,
        "kanbots": measured,
        "clis_present": len(present),
        "clis_absent": len(absent),
        "clis_dispatched": 0,
        "cli_rows": present + absent,
        "live_dispatch": "SKIPPED each CLI reuses its own sign-in; this lane does not call them",
        "gui": "SKIPPED Electron binary can open a cloud login; not started",
        "npm_package": npm_view(home, tmp) if args.net else {"skipped": "pass --net to recheck the registry"},
        "cli": cli_help(src, home, tmp),
        "source_markers": source_markers(src),
        "build_timeout_hours_removed": 0,
        "home_markers_before": before,
        "home_markers_after": home_markers(real),
    }
    OUT.write_text(json.dumps(results, indent=2) + "\n")
    print(f"wrote {OUT}")
    print(
        "create_stamp_remove_ms",
        measured["create_stamp_remove_ms"],
        "baseline_s",
        t_base.get("total_s"),
        "explicit_before",
        measured["push_explicit_before_stamp"]["status"],
        "head_before",
        measured["push_head_before_stamp"]["status"],
        "explicit_after",
        measured["push_explicit_after_stamp"]["status"],
        "author",
        measured["author"],
        "outside",
        f"{measured['outside_blocked']}/{measured['outside_total']}",
        "clis",
        f"{len(present)}/11",
    )


if __name__ == "__main__":
    main()
