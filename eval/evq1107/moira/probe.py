#!/usr/bin/env python3
"""Score Moira step checks against one pfy build-lane fixture.

The fixture is the 2026-11-06 gap: pregate FAIL twice, wall clock at 3 hours.
A runner returns schema and route results. This process compares them to the
labels below. It does not start Docker, create an account, or call a model.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PIN = "b66b537a0465194d8806fa638776237d8cf853c5"
WALL_CAP_S = 10800
TRUTH = {
    "pregate": "FAIL",
    "elapsed_s": WALL_CAP_S,
    "fail_count": 2,
    "wall_cap_s": WALL_CAP_S,
}
SCHEMA = {
    "type": "object",
    "required": ["pregate", "elapsed_s", "fail_count", "goal_met"],
    "properties": {
        "pregate": {"type": "string", "enum": ["PASS", "FAIL"]},
        "elapsed_s": {"type": "integer", "minimum": 0},
        "fail_count": {"type": "integer", "minimum": 0},
        "goal_met": {"type": "boolean"},
    },
}
ROUTE_CASES = [
    {
        "when": {
            "operator": "gte",
            "left": {"contextPath": "elapsed_s"},
            "right": WALL_CAP_S,
        },
        "output": "timeout",
    },
    {
        "when": {
            "operator": "eq",
            "left": {"contextPath": "pregate"},
            "right": "FAIL",
        },
        "output": "park",
    },
]
CONNECTIONS = {
    "timeout": "end-timeout",
    "park": "end-park",
    "done": "end-done",
}
EXITS = (
    "Goal met",
    "Turn cap",
    "Budget cap",
    "Wall clock",
    "No progress",
    "Human interrupt",
    "Error threshold",
    "External event",
)


def _step(pregate: str, elapsed_s: int | float | str, fail_count: int, goal_met: bool) -> dict:
    return {
        "pregate": pregate,
        "elapsed_s": elapsed_s,
        "fail_count": fail_count,
        "goal_met": goal_met,
    }


def cases() -> list[dict]:
    prose = "pregate is PASS and under 3 hours"
    rows = [
        ("mal-empty", "malformed", {}, False, None),
        ("mal-enum", "malformed", _step("done", 1, 0, True), False, None),
        ("mal-type", "malformed", _step("PASS", "10", 0, True), False, None),
        (
            "mal-extra",
            "malformed",
            {**_step("PASS", 10, 0, True), "lane_done": True},
            False,
            None,
        ),
        (
            "mal-missing",
            "malformed",
            {"pregate": "PASS", "elapsed_s": 10, "fail_count": 0},
            False,
            None,
        ),
        ("mal-min", "malformed", _step("PASS", -1, 0, True), False, None),
        ("mal-int", "malformed", _step("PASS", 10.5, 0, True), False, None),
        ("mal-prose", "malformed", prose, False, None),
        ("lie-underreport", "lie", _step("PASS", 10, 0, True), True, "done"),
        ("lie-one-under-cap", "lie", _step("PASS", WALL_CAP_S - 1, 0, True), True, "done"),
        ("lie-goal-ignored", "lie", _step("PASS", 60, 0, False), True, "done"),
        ("lie-failcount-ignored", "lie", _step("PASS", 10, 2, True), True, "done"),
        ("honest-park", "honest", _step("FAIL", 1000, 2, False), True, "park"),
        ("honest-cap", "honest", _step("FAIL", WALL_CAP_S, 2, False), True, "timeout"),
        ("honest-clock-beats-pass", "honest", _step("PASS", WALL_CAP_S + 1, 0, True), True, "timeout"),
        ("honest-over", "honest", _step("FAIL", WALL_CAP_S + 1, 2, False), True, "timeout"),
        ("string-pass", "string", _step("FAIL", 1000, 2, False), True, "park"),
        ("string-fail", "string", _step("FAIL", 1000, 2, False), True, "park"),
    ]
    out = []
    for item in rows:
        ident, group, payload, expect_valid, expect_output = item
        condition = "pregate is FAIL" if ident == "string-fail" else "pregate is PASS"
        out.append(
            {
                "id": ident,
                "group": group,
                "input": payload,
                "completionCondition": condition,
                "said": "done",
                "expect_valid": expect_valid,
                "expect_output": expect_output,
            }
        )
    return out


def prose_accepts(said: str) -> bool:
    return said.strip().lower() == "done"


def skill_counts(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    present = []
    for name in EXITS:
        if name == "No progress":
            hit = "No progress" in text or "No-progress" in text
        else:
            hit = name in text
        if hit:
            present.append(name)
    return {
        "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "exit_names_present": len(present),
        "exit_names": len(EXITS),
        "input_schema_mentions": text.count("inputSchema"),
    }


def _count(rows: list[dict], group: str, pred) -> dict:
    chosen = [row for row in rows if row["group"] == group]
    return {"hit": sum(1 for row in chosen if pred(row)), "n": len(chosen)}


def summarize(rows: list[dict], skill: dict) -> dict:
    string_rows = [row for row in rows if row["group"] == "string"]
    outputs = [row["output"] for row in string_rows]
    changed = len(set(outputs)) > 1
    return {
        "malformed_rejected": _count(rows, "malformed", lambda row: row["valid"] is False),
        "lies_routed_done": _count(
            rows,
            "lie",
            lambda row: row["valid"] is True and row["output"] == "done",
        ),
        "honest_not_done": _count(
            rows,
            "honest",
            lambda row: row["valid"] is True and row["output"] not in (None, "done"),
        ),
        "completion_string_changed": changed,
        "completion_string_n": len(string_rows),
        "prose_done_accepted": {
            "hit": sum(1 for row in rows if row["prose_accept"]),
            "n": len(rows),
        },
        "skill_exit_names_present": skill["exit_names_present"],
        "skill_exit_names": skill["exit_names"],
        "skill_input_schema_mentions": skill["input_schema_mentions"],
    }


def git_pin(src: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(src), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def tree_bytes(src: Path) -> int:
    total = 0
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [name for name in dirnames if name not in {".git", "node_modules"}]
        for name in filenames:
            path = Path(dirpath) / name
            try:
                total += path.stat().st_size
            except OSError:
                continue
    return total


def run_runner(runner: list[str], job_path: Path, env: dict) -> subprocess.CompletedProcess:
    argv = runner + [str(job_path)]
    try:
        return subprocess.run(
            argv,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    except OSError as exc:
        return subprocess.CompletedProcess(argv, returncode=127, stdout="", stderr=str(exc))


def parse_engine(stdout: str) -> dict | None:
    payload = None
    for line in stdout.splitlines():
        if line.startswith("PFY_JSON "):
            payload = json.loads(line[len("PFY_JSON ") :])
    return payload


def default_runner() -> list[str]:
    node = os.environ.get(
        "MOIRA_NODE",
        "/home/mark/.local/share/pfy-mentat/node/v25.9.0/bin/node",
    )
    tsx = os.environ.get(
        "MOIRA_TSX",
        str(Path.home() / ".cache/pfy/tools/moira/nm/node_modules/tsx/dist/loader.mjs"),
    )
    script = ROOT / "eval" / "evq1107" / "moira" / "engine_check.mjs"
    return [node, "--import", tsx, str(script)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe Moira step completion on one build-lane fixture.")
    parser.add_argument("--runner", default="", help="Stub or engine command. The job path is appended.")
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--skill",
        default=str(ROOT / "bootstrap/grok-cli/skills/agent-loops/SKILL.md"),
    )
    args = parser.parse_args(argv)
    out_path = Path(args.out)
    skill = skill_counts(Path(args.skill))
    rows = cases()
    stub = bool(args.runner)
    src = Path(os.environ.get("MOIRA_SRC", str(Path.home() / ".cache/pfy/tools/moira/src")))
    pin = "stub"
    described = ""
    license_name = ""
    src_bytes = 0
    if not stub:
        pin = git_pin(src)
        if pin != PIN:
            sys.stderr.write("pin mismatch: %s\n" % (pin or "missing"))
            return 2
        desc = subprocess.run(
            ["git", "-C", str(src), "describe", "--tags", "--exact-match"],
            capture_output=True,
            text=True,
            check=False,
        )
        described = desc.stdout.strip()
        pkg = json.loads((src / "package.json").read_text(encoding="utf-8"))
        license_name = str(pkg.get("license") or "")
        src_bytes = tree_bytes(src)

    job = {
        "schema": SCHEMA,
        "routeCases": ROUTE_CASES,
        "connections": CONNECTIONS,
        "defaultOutput": "done",
        "cases": [
            {
                "id": row["id"],
                "input": row["input"],
                "completionCondition": row["completionCondition"],
                "expect_valid": row["expect_valid"],
                "expect_output": row["expect_output"],
            }
            for row in rows
        ],
    }
    runner = args.runner.split() if stub else default_runner()
    if not runner or (not stub and not Path(runner[0]).exists()):
        sys.stderr.write("runner missing\n")
        return 2
    if stub:
        home = os.environ.get("HOME", "/tmp")
        extra_env: dict[str, str] = {}
    else:
        base = Path.home() / ".cache" / "pfy" / "tools" / "moira"
        home = str(base / "home")
        extra_env = {
            "XDG_CONFIG_HOME": str(base / "config"),
            "XDG_CACHE_HOME": str(base / "cache"),
            "TMPDIR": str(base / "tmp"),
        }
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": home,
        "LANG": "C.UTF-8",
        "MOIRA_SRC": str(src),
        "NODE_NO_WARNINGS": "1",
        **extra_env,
    }
    with tempfile.TemporaryDirectory(prefix="moira-probe-") as tmp:
        job_path = Path(tmp) / "job.json"
        job_path.write_text(json.dumps(job), encoding="utf-8")
        started = time.perf_counter()
        proc = run_runner(runner, job_path, env)
        elapsed_s = time.perf_counter() - started
    engine = parse_engine(proc.stdout)
    if proc.returncode != 0 or engine is None:
        sys.stderr.write(proc.stderr)
        sys.stderr.write(proc.stdout)
        return 2
    by_id = {row["id"]: row for row in engine["cases"]}
    scored = []
    mismatches = []
    for row in rows:
        got = by_id.get(row["id"])
        if got is None:
            sys.stderr.write("missing case %s\n" % row["id"])
            return 2
        ok = got["valid"] is row["expect_valid"] and got["output"] == row["expect_output"]
        if not ok:
            mismatches.append(row["id"])
        scored.append(
            {
                "id": row["id"],
                "group": row["group"],
                "valid": got["valid"],
                "output": got["output"],
                "expect_valid": row["expect_valid"],
                "expect_output": row["expect_output"],
                "ok": ok,
                "prose_accept": prose_accepts(row["said"]),
                "error": got.get("error") or "",
            }
        )
    summary = summarize(scored, skill)
    body = {
        "pin": pin,
        "describe": described,
        "license": license_name,
        "src_bytes": src_bytes,
        "truth": TRUTH,
        "wall_s": round(elapsed_s, 6),
        "engine_elapsed_us": engine.get("elapsed_us"),
        "ajv": engine.get("ajv") or "",
        "engine": engine.get("engine") or "",
        "skill": skill,
        "summary": summary,
        "mismatches": mismatches,
        "cases": scored,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    if mismatches:
        print("MISMATCH " + ",".join(mismatches))
        return 1
    mal = summary["malformed_rejected"]
    lies = summary["lies_routed_done"]
    honest = summary["honest_not_done"]
    print(
        "OK malformed %d/%d lies_done %d/%d honest_stop %d/%d string_changed %s"
        % (
            mal["hit"],
            mal["n"],
            lies["hit"],
            lies["n"],
            honest["hit"],
            honest["n"],
            summary["completion_string_changed"],
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
