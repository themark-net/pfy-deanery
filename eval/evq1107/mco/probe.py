#!/usr/bin/env python3
"""Offline probe: does mco turn two disagreeing reviews of gap B into a decision?

No hosted CLI, no account, no model. Built-in provider review is recorded as
SKIPPED because `mco doctor` auth checks launch those CLIs.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
FIXTURE = Path("eval/evq1107/mco/fixture/gap-b.txt")
STUB = Path(__file__).resolve().parent / "stubs" / "lane_review.py"
CACHE = Path(os.environ.get("MCO_CACHE", Path.home() / ".cache/pfy/tools/mco"))
MCO = CACHE / "venv/bin/mco"
PY = CACHE / "venv/bin/python"
OUT = Path(__file__).resolve().parent / "results.json"

DECISION_KEYS = frozenset({
    "agreement",
    "agreements",
    "consensus",
    "severity",
    "confidence",
    "finding",
    "findings",
    "decision",
    "decisions",
    "score",
    "scores",
    "winner",
    "merged",
    "merge",
    "vote",
    "votes",
    "ranking",
    "rank",
})

BINARIES = (
    ("agy", "agy"),
    ("claude", "claude"),
    ("codex", "codex"),
    ("copilot", "copilot"),
    ("cursor", "agent"),
    ("gemini", "gemini"),
    ("grok", "grok"),
    ("hermes", "hermes"),
    ("opencode", "opencode"),
    ("pi", "pi"),
    ("qwen", "qwen"),
)

PROMPT = (
    "Review the single blocker in %s. "
    "Name one blocker. Do not merge a second opinion."
) % FIXTURE.as_posix()


def decision_keys(value: object, found: list[str]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in DECISION_KEYS:
                found.append(str(key))
            decision_keys(item, found)
    elif isinstance(value, list):
        for item in value:
            decision_keys(item, found)


def provider_inventory() -> dict:
    rows = []
    for provider, binary in BINARIES:
        resolved = shutil.which(binary)
        row = {"provider": provider, "binary": binary, "present": bool(resolved)}
        if provider == "cursor":
            # Path text only. A miss does not prove this is not the Cursor CLI.
            row["path_mentions_cursor"] = bool(resolved) and "cursor" in resolved.lower()
        rows.append(row)
    return {
        "providers": len(rows),
        "present": sum(1 for row in rows if row["present"]),
        "rows": rows,
        "doctor": "SKIPPED",
        "doctor_reason": "auth checks launch provider CLIs (grok models, gemini prompt, copilot --allow-all-tools). Not run.",
        "live_review": "SKIPPED",
    }


def context_file_count() -> dict:
    code = (
        "import json\n"
        "from runtime.adapters import adapter_registry\n"
        "reg = adapter_registry()\n"
        "names = []\n"
        "for name, adapter in reg.items():\n"
        "    fn = getattr(adapter, 'supported_context_keys', None)\n"
        "    keys = fn() if callable(fn) else []\n"
        "    if isinstance(keys, list) and 'context_files' in keys:\n"
        "        names.append(name)\n"
        "print(json.dumps({'registry': len(reg), 'context_files': names}))\n"
    )
    proc = subprocess.run([str(PY), "-c", code], text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        return {"error": (proc.stderr or proc.stdout)[-400:]}
    return json.loads(proc.stdout)


def clean_env(config_dir: Path, log_path: Path) -> dict[str, str]:
    home = CACHE / "home"
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(CACHE / "config"),
        "XDG_CACHE_HOME": str(CACHE / "cache"),
        "TMPDIR": str(CACHE / "tmp"),
        "MCO_CONFIG_DIR": str(config_dir),
        "MCO_PROBE_LOG": str(log_path),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def write_agents(config_dir: Path) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    stub = STUB.as_posix()
    text = (
        "agents:\n"
        "  - name: lane-timeout\n"
        "    transport: shim\n"
        "    command: /usr/bin/python3 %s timeout\n"
        "  - name: lane-pregate\n"
        "    transport: shim\n"
        "    command: /usr/bin/python3 %s pregate\n"
    ) % (stub, stub)
    (config_dir / "agents.yaml").write_text(text, encoding="utf-8")


def parse_log(log_path: Path) -> dict:
    starts = {}
    ends = {}
    lines = log_path.read_text(encoding="utf-8").splitlines() if log_path.exists() else []
    for line in lines:
        parts = line.split()
        if len(parts) != 4:
            continue
        kind, role, stamp, _pid = parts
        bucket = starts if kind == "start" else ends if kind == "end" else None
        if bucket is None or role in bucket:
            continue
        bucket[role] = float(stamp)
    roles = sorted(set(starts) & set(ends))
    overlap = False
    if len(roles) >= 2:
        overlap = max(starts[role] for role in roles) < min(ends[role] for role in roles)
    return {
        "lines": len(lines),
        "roles": roles,
        "overlap": overlap,
        "span_s": round(max(ends.values()) - min(starts.values()), 3) if starts and ends else None,
    }


def run_mco(args: list[str], env: dict[str, str], log_path: Path) -> dict:
    if log_path.exists():
        log_path.unlink()
    started = time.perf_counter()
    proc = subprocess.run(
        [str(MCO), *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    payload = None
    parse_error = ""
    try:
        payload = json.loads(proc.stdout) if proc.stdout.strip() else None
    except json.JSONDecodeError as exc:
        parse_error = str(exc)
    keys: list[str] = []
    if payload is not None:
        decision_keys(payload, keys)
    outputs = []
    if isinstance(payload, dict):
        for item in payload.get("outputs") or []:
            if not isinstance(item, dict):
                continue
            outputs.append({
                "provider": item.get("provider"),
                "stage": item.get("stage"),
                "status": item.get("status"),
                "error": item.get("error"),
                "output": item.get("output"),
            })
    return {
        "exit_code": proc.returncode,
        "elapsed_ms": elapsed_ms,
        "parse_error": parse_error,
        "status": payload.get("status") if isinstance(payload, dict) else None,
        "would_execute": payload.get("would_execute") if isinstance(payload, dict) else None,
        "invocation_count": len(payload.get("invocations") or []) if isinstance(payload, dict) else 0,
        "decision_keys": keys,
        "outputs": outputs,
        "stderr_tail": (proc.stderr or "")[-500:],
        "timing": parse_log(log_path),
    }


def repo_dirt() -> list[str]:
    names = []
    for rel in ("reports/review", ".mco", ".mcorc.json", ".mcorc.yaml"):
        if (ROOT / rel).exists():
            names.append(rel)
    return names


def main() -> int:
    if not MCO.is_file():
        raise SystemExit("mco is not installed at %s" % MCO)
    if repo_dirt():
        raise SystemExit("refusing to run; repo already has %s" % ", ".join(repo_dirt()))
    config_dir = CACHE / "home" / ".mco"
    log_path = CACHE / "tmp" / "mco-probe.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    write_agents(config_dir)
    env = clean_env(config_dir, log_path)
    common = [
        "--repo", str(ROOT),
        "--prompt", PROMPT,
        "--providers", "lane-timeout,lane-pregate",
        "--target-paths", FIXTURE.as_posix(),
        "--json",
        "--result-mode", "stdout",
        "--artifact-base", str(CACHE / "tmp" / "artifacts"),
    ]
    dry = run_mco(["review", *common, "--dry-run", "--task-id", "gap-b-dry"], env, log_path)
    parallel = run_mco(["review", *common, "--task-id", "gap-b-parallel"], env, log_path)
    synth = run_mco(
        ["review", *common, "--synthesize", "--synth-provider", "lane-timeout", "--task-id", "gap-b-synth"],
        env,
        log_path,
    )
    answers = [item.get("output") for item in parallel["outputs"] if item.get("stage") in (None, "run")]
    distinct = sorted({str(item).strip() for item in answers if item})
    synth_errors = [item.get("error") for item in synth["outputs"] if item.get("stage") == "synthesis"]
    results = {
        "fixture": FIXTURE.as_posix(),
        "inventory": provider_inventory(),
        "context_files": context_file_count(),
        "dry_run": dry,
        "parallel": parallel,
        "synthesize": {
            "exit_code": synth["exit_code"],
            "elapsed_ms": synth["elapsed_ms"],
            "status": synth["status"],
            "decision_keys": synth["decision_keys"],
            "outputs": synth["outputs"],
            "synthesis_errors": synth_errors,
            "stderr_tail": synth["stderr_tail"],
            "timing": synth["timing"],
        },
        "distinct_answers": distinct,
        "decision_key_count": len(parallel["decision_keys"]),
        "repo_writes": repo_dirt(),
        "gap_b_closed": 0,
    }
    OUT.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "present": results["inventory"]["present"],
        "dry_would_execute": dry["would_execute"],
        "dry_invocations": dry["invocation_count"],
        "parallel_exit": parallel["exit_code"],
        "parallel_ms": parallel["elapsed_ms"],
        "overlap": parallel["timing"]["overlap"],
        "answers": distinct,
        "decision_keys": parallel["decision_keys"],
        "synth_status": synth["status"],
        "synth_errors": synth_errors,
        "context_files": results["context_files"],
        "repo_writes": results["repo_writes"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
