#!/usr/bin/env python3
"""Score Deanery's hand-written guards against a pinned local AgentLint.

Deanery side, offline:
  commands: scripts/integrations/dcg/guard.sh built-in list
    (PFY_DCG_BIN points at a missing file, so the external binary is not used)
  writes: pfy build protected paths plus scripts/check_public_paths.py

AgentLint side:
  `agentlint check` in a scratch project whose packs match this repo
  (universal, quality, python, security). AgentChute stays off.
  Cache, heartbeat, and the credentials file stay under the worktree tmp/.

A catch is an error or a warning. Info does not count.
Deanery's deny is a block. AgentLint error is a block. A warning is a flag.

Usage:
  python3 eval/agentlint-trial/score.py
  python3 eval/agentlint-trial/score.py --write eval/agentlint-trial/results.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = Path(__file__).with_name("corpus.json")
GUARD = ROOT / "scripts" / "integrations" / "dcg" / "guard.sh"
PINNED_VERSION = "2.12.0"
PACKS = ["universal", "quality", "python", "security"]

# Patterns the trial treats as a block when AgentLint says error, or when
# Deanery's guard exits 126 / the path checkers complain.


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _deanery():
    cloud = _load("pfy_build_cloud_score", ROOT / "scripts" / "pfy_build_cloud.py")
    public = _load("check_public_paths_score", ROOT / "scripts" / "check_public_paths.py")
    return cloud, public


def find_agentlint(explicit: str | None) -> Path | None:
    if explicit:
        path = Path(explicit)
        return path if path.is_file() else None
    env = os.environ.get("PFY_AGENTLINT_BIN")
    if env:
        path = Path(env)
        return path if path.is_file() else None
    local = ROOT / "tmp" / "agentlint-venv" / "bin" / "agentlint"
    if local.is_file():
        return local
    found = shutil.which("agentlint")
    return Path(found) if found else None


def deanery_command(command: str) -> dict:
    argv = shlex.split(command)
    env = os.environ.copy()
    env.pop("PFY_DCG_DISABLE", None)
    env["PFY_DCG_BIN"] = "/nonexistent/dcg"
    started = time.monotonic()
    proc = subprocess.run(
        ["bash", str(GUARD), *argv],
        env=env,
        capture_output=True,
        text=True,
        timeout=5,
    )
    elapsed = time.monotonic() - started
    caught = proc.returncode == 126
    return {
        "catch": caught,
        "block": caught,
        "severity": "error" if caught else "allow",
        "detail": (proc.stderr or "").strip().splitlines()[:2],
        "seconds": round(elapsed, 4),
    }


def deanery_write(cloud, public, path: str, content: str, scratch: Path) -> dict:
    started = time.monotonic()
    reasons = []
    if cloud._protected(path) or cloud._protected_gate_path(path):
        reasons.append("protected-path")
    target = scratch / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    problems = public.check(scratch, [path])
    if problems:
        reasons.append("public-path")
    elapsed = time.monotonic() - started
    caught = bool(reasons)
    return {
        "catch": caught,
        "block": caught,
        "severity": "error" if caught else "allow",
        "detail": reasons,
        "seconds": round(elapsed, 4),
    }


def _isolated_env(home: Path) -> dict:
    home.mkdir(parents=True, exist_ok=True)
    cred = home / "no-agentchute.json"
    cred.write_text("{}\n", encoding="utf-8")
    path = os.environ.get("PATH") or "/usr/bin:/bin"
    return {
        "HOME": str(home),
        "PATH": path,
        "LANG": "C",
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "AGENTLINT_CACHE_DIR": str(home / "cache"),
        "AGENTLINT_HEARTBEAT_DIR": str(home / "heartbeat"),
        "AGENTLINT_AGENTCHUTE_CREDENTIALS_FILE": str(cred),
        "AGENTLINT_SESSION_ID": "agentlint-trial",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def _scratch_project(root: Path) -> Path:
    project = root / "project"
    project.mkdir(parents=True, exist_ok=True)
    (project / "agentlint.yml").write_text(
        "severity: standard\n"
        "packs:\n"
        + "".join("  - %s\n" % name for name in PACKS)
        + "agentchute:\n  enabled: false\n",
        encoding="utf-8",
    )
    return project


def agentlint_version(binary: Path, env: dict) -> str:
    proc = subprocess.run(
        [str(binary), "--version"],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    return (proc.stdout or proc.stderr or "").strip()


def agentlint_check(binary: Path, env: dict, project: Path, item: dict) -> dict:
    if item["kind"] == "command":
        payload = {"tool_name": "Bash", "tool_input": {"command": item["command"]}}
    else:
        payload = {
            "tool_name": "Write",
            "tool_input": {"file_path": item["path"], "content": item["content"]},
        }
    # A shared session degrades a rule after a few fires. Each corpus row is
    # its own session so the score is the first-time severity.
    run_env = dict(env)
    run_env["AGENTLINT_SESSION_ID"] = "trial-%s" % item["id"]
    started = time.monotonic()
    proc = subprocess.run(
        [
            str(binary),
            "check",
            "--adapter",
            "generic",
            "--event",
            "pre_tool_use",
            "--project-dir",
            str(project),
        ],
        input=json.dumps(payload),
        env=run_env,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(project),
    )
    elapsed = time.monotonic() - started
    raw = (proc.stdout or "").strip()
    if proc.returncode not in (0, 1) or not raw or raw == "None":
        if proc.returncode in (0, 1) and not raw:
            return {
                "catch": False,
                "block": False,
                "severity": "allow",
                "rules": [],
                "detail": [],
                "seconds": round(elapsed, 4),
                "exit": proc.returncode,
            }
        return {
            "catch": False,
            "block": False,
            "severity": "error-run",
            "rules": [],
            "detail": ((proc.stderr or raw)[:400]).splitlines()[:6],
            "seconds": round(elapsed, 4),
            "exit": proc.returncode,
        }
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {
            "catch": False,
            "block": False,
            "severity": "error-run",
            "rules": [],
            "detail": [raw[:400]],
            "seconds": round(elapsed, 4),
            "exit": proc.returncode,
        }
    violations = data.get("violations") or []
    severities = [str(item.get("severity") or "") for item in violations]
    rules = [str(item.get("rule_id") or "") for item in violations]
    if "error" in severities or data.get("blocked") is True:
        severity = "error"
    elif "warning" in severities:
        severity = "warning"
    elif severities:
        severity = "info"
    else:
        severity = "allow"
    caught = severity in ("error", "warning")
    return {
        "catch": caught,
        "block": severity == "error",
        "severity": severity,
        "rules": rules,
        "detail": [str(item.get("message") or "") for item in violations][:4],
        "seconds": round(elapsed, 4),
        "exit": proc.returncode,
    }


def network_probe(binary: Path, env: dict, project: Path) -> dict:
    """One check under strace. A hit is an AF_INET connect or sendto."""
    if shutil.which("strace") is None:
        return {"method": "strace-missing", "inet_lines": 0, "ok": None}
    log = Path(env["AGENTLINT_CACHE_DIR"]).parent / "strace.txt"
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git status"}})
    subprocess.run(
        [
            "strace",
            "-f",
            "-e",
            "trace=network",
            "-o",
            str(log),
            str(binary),
            "check",
            "--adapter",
            "generic",
            "--event",
            "pre_tool_use",
            "--project-dir",
            str(project),
        ],
        input=payload,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(project),
    )
    text = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
    inet = [
        line
        for line in text.splitlines()
        if ("AF_INET" in line or "AF_INET6" in line)
        and ("connect" in line or "sendto" in line)
    ]
    return {"method": "strace", "inet_lines": len(inet), "ok": len(inet) == 0}


def _count(rows: list[dict], group: str, key: str) -> int:
    return sum(1 for row in rows if row["group"] == group and row[key])


def _mean(rows: list[dict], key: str) -> float:
    if not rows:
        return 0.0
    return round(sum(row[key] for row in rows) / len(rows), 4)


def summarize(rows: list[dict]) -> dict:
    risky = [row for row in rows if row["group"] == "risky"]
    benign = [row for row in rows if row["group"] == "benign"]
    extra = [
        row["id"]
        for row in risky
        if row["agentlint_block"] and not row["deanery_block"]
    ]
    extra_warn = [
        row["id"]
        for row in risky
        if row["agentlint_catch"] and not row["agentlint_block"] and not row["deanery_catch"]
    ]
    missed_both = [
        row["id"]
        for row in risky
        if not row["union_catch"]
    ]
    fp_block = [row["id"] for row in benign if row["agentlint_block"] or row["deanery_block"]]
    fp_warn = [
        row["id"]
        for row in benign
        if row["agentlint_catch"] and not row["agentlint_block"] and not row["deanery_catch"]
    ]
    return {
        "risky": len(risky),
        "benign": len(benign),
        "deanery_risky_catch": _count(rows, "risky", "deanery_catch"),
        "agentlint_risky_catch": _count(rows, "risky", "agentlint_catch"),
        "agentlint_risky_block": _count(rows, "risky", "agentlint_block"),
        "union_risky_catch": _count(rows, "risky", "union_catch"),
        "deanery_benign_flag": _count(rows, "benign", "deanery_catch"),
        "agentlint_benign_flag": _count(rows, "benign", "agentlint_catch"),
        "agentlint_benign_block": _count(rows, "benign", "agentlint_block"),
        "union_benign_flag": _count(rows, "benign", "union_catch"),
        "extra_blocks": extra,
        "extra_warnings": extra_warn,
        "missed_by_both": missed_both,
        "false_blocks": fp_block,
        "false_warnings": fp_warn,
        "deanery_mean_s": _mean(rows, "deanery_s"),
        "agentlint_mean_s": _mean(rows, "agentlint_s"),
    }


def markdown_table(summary: dict) -> str:
    lines = [
        "| checker | risky catches | benign flags | mean seconds |",
        "|---|---:|---:|---:|",
        "| Deanery | %d/%d | %d/%d | %s |"
        % (
            summary["deanery_risky_catch"],
            summary["risky"],
            summary["deanery_benign_flag"],
            summary["benign"],
            summary["deanery_mean_s"],
        ),
        "| AgentLint | %d/%d (%d block) | %d/%d (%d block) | %s |"
        % (
            summary["agentlint_risky_catch"],
            summary["risky"],
            summary["agentlint_risky_block"],
            summary["agentlint_benign_flag"],
            summary["benign"],
            summary["agentlint_benign_block"],
            summary["agentlint_mean_s"],
        ),
        "| Union | %d/%d | %d/%d |  |"
        % (
            summary["union_risky_catch"],
            summary["risky"],
            summary["union_benign_flag"],
            summary["benign"],
        ),
    ]
    return "\n".join(lines)


def _shown_binary(binary: Path | None) -> str:
    """Repo-relative path. A binary outside the repo is only its file name."""
    if binary is None:
        return ""
    try:
        return binary.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return binary.name


def score(binary: Path | None, work: Path) -> dict:
    cloud, public = _deanery()
    corpus = json.loads(CORPUS.read_text(encoding="utf-8").replace("@@STRIPE_PREFIX@@", "sk_" + "live_"))
    home = work / "home"
    env = _isolated_env(home)
    project = _scratch_project(work)
    path_root = work / "public-paths"
    version = ""
    probe = {"method": "not-run", "inet_lines": None, "ok": None}
    if binary is not None:
        version = agentlint_version(binary, env)
        probe = network_probe(binary, env, project)
    rows = []
    for item in corpus["items"]:
        if item["kind"] == "command":
            deanery = deanery_command(item["command"])
        else:
            deanery = deanery_write(cloud, public, item["path"], item["content"], path_root)
        if binary is None:
            agent = {
                "catch": False,
                "block": False,
                "severity": "missing",
                "rules": [],
                "detail": ["agentlint binary missing"],
                "seconds": 0.0,
            }
        else:
            agent = agentlint_check(binary, env, project, item)
        rows.append(
            {
                "id": item["id"],
                "group": item["group"],
                "kind": item["kind"],
                "note": item.get("note", ""),
                "deanery_catch": deanery["catch"],
                "deanery_block": deanery["block"],
                "deanery_detail": deanery["detail"],
                "deanery_s": deanery["seconds"],
                "agentlint_catch": agent["catch"],
                "agentlint_block": agent["block"],
                "agentlint_severity": agent["severity"],
                "agentlint_rules": agent.get("rules") or [],
                "agentlint_detail": agent["detail"],
                "agentlint_s": agent["seconds"],
                "union_catch": bool(deanery["catch"] or agent["catch"]),
                "union_block": bool(deanery["block"] or agent["block"]),
            }
        )
    summary = summarize(rows)
    return {
        "schema": "agentlint-trial-results/1",
        "pinned_version": PINNED_VERSION,
        "agentlint_version": version,
        "binary": _shown_binary(binary),
        "packs": PACKS,
        "license": "MIT",
        "osi_permissive": True,
        "network_probe": probe,
        "summary": summary,
        "table": markdown_table(summary),
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score Deanery guards against AgentLint")
    parser.add_argument("--bin", default=None, help="agentlint binary")
    parser.add_argument("--work", default=None, help="scratch directory (default: tmp/agentlint-score)")
    parser.add_argument("--write", default=None, help="write the JSON results here")
    args = parser.parse_args(argv)
    work = Path(args.work) if args.work else ROOT / "tmp" / "agentlint-score"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    binary = find_agentlint(args.bin)
    payload = score(binary, work)
    text = json.dumps(payload, indent=2) + "\n"
    if args.write:
        dest = Path(args.write)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
    print(payload["table"])
    print("version:", payload["agentlint_version"] or "missing")
    print("network:", json.dumps(payload["network_probe"]))
    summary = payload["summary"]
    print("extra blocks:", ", ".join(summary["extra_blocks"]) or "(none)")
    print("extra warnings:", ", ".join(summary["extra_warnings"]) or "(none)")
    print("missed by both:", ", ".join(summary["missed_by_both"]) or "(none)")
    print("false blocks:", ", ".join(summary["false_blocks"]) or "(none)")
    print("false warnings:", ", ".join(summary["false_warnings"]) or "(none)")
    if binary is None:
        return 2
    if PINNED_VERSION not in payload["agentlint_version"]:
        print("version pin mismatch", file=sys.stderr)
        return 2
    if payload["network_probe"].get("ok") is False:
        print("network probe saw inet traffic", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
