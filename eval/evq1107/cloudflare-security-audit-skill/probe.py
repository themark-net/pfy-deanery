#!/usr/bin/env python3
"""H2 probe for the pinned Cloudflare security-audit validators.

Question: does validate-findings.cjs block one planted shell=True line in a
skill fixture from this repo? Offline. No model, no network, no skill install.
Exit 0 writes results.json. Exit 2 means the pin or the fixture drifted.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

PIN = "c1c8a8c1471069fb0e188eeaff69b8e8db6564a8"
TREE = "8cd03bb3941496e441d6248aaae2429a35b93cc3"
HAZARD = "shell=True"
FILE_SHA256 = {
    "validate-findings.cjs": "e85f232e36bfac0f866f244da50376692d6b45c690beadcb00608b0e6c8b5283",
    "validate-coverage-ledger.cjs": "2eb280bd2e33c002916f86db9b29f9edfedb6454e5db973c766290465b868ac8",
    "report-schema.json": "6575c9de4a62255699ea052ebf9a49ebfb373a32891bcd89af6f55cc84b35519",
}

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FETCHED = HERE / "fixtures" / "fetched-skill" / "SKILL.md"
CLEAN = HERE / "fixtures" / "clean-skill" / "SKILL.md"
FETCHED_REL = "eval/evq1107/cloudflare-security-audit-skill/fixtures/fetched-skill/SKILL.md"
MISSING_REL = "eval/evq1107/cloudflare-security-audit-skill/fixtures/missing-source.py"
CACHE = Path.home() / ".cache" / "pfy" / "tools" / "cloudflare-security-audit-skill"
SRC = CACHE / "src"
SKILL = SRC / "skills" / "security-audit"
OUT = HERE / "results.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def dir_bytes(root: Path, *, skip_git: bool) -> int:
    total = 0
    for path in root.rglob("*"):
        if skip_git and ".git" in path.parts:
            continue
        if path.is_file():
            total += path.stat().st_size
    return total


def child_env() -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(CACHE / "home"),
        "XDG_CONFIG_HOME": str(CACHE / "config"),
        "XDG_CACHE_HOME": str(CACHE / "cache"),
        "TMPDIR": str(CACHE / "tmp"),
        "npm_config_cache": str(CACHE / "npm"),
        "LANG": "C.UTF-8",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
    }


def run_cmd(args: list[str], *, cwd: Path, timeout: float) -> tuple[int, str, str, float]:
    started = time.perf_counter()
    proc = subprocess.run(
        args,
        cwd=cwd,
        env=child_env(),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    elapsed = time.perf_counter() - started
    return proc.returncode, proc.stdout, proc.stderr, elapsed


def clip(text: str, limit: int = 400) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def parse_tap(text: str) -> dict[str, float]:
    found: dict[str, float] = {}
    keys = {"tests", "suites", "pass", "fail", "cancelled", "skipped", "todo", "duration_ms"}
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) == 3 and parts[0] == "#" and parts[1] in keys:
            found[parts[1]] = float(parts[2])
    return found


def source(kind: str, file: str, line: int) -> dict:
    return {
        "kind": kind,
        "file": file,
        "line": line,
        "scope": "fixture",
        "description": "Cited line in the fixture path.",
    }


def rejected(file: str, line: int, fingerprint: str, reason: str) -> dict:
    return {
        "verdict": "rejected",
        "fingerprint": fingerprint,
        "title": "Planted skill line",
        "description": "The candidate claimed the skill line runs a shell.",
        "claimed_root_cause": "A line was claimed to call the shell.",
        "trace": [source("sink", file, line)],
        "evidence": [{"file": file, "line": line, "description": "The cited line is the claimed call."}],
        "reason": reason,
    }


def confirmed(file: str, line: int, fingerprint: str, observed: str) -> dict:
    return {
        "verdict": "confirmed",
        "fingerprint": fingerprint,
        "title": "Cited source was not opened",
        "description": "A confirmed record names a path the validator does not open.",
        "root_cause": "The record is accepted from JSON alone.",
        "intended_behavior": "A confirmed record matches a line in the tree.",
        "trace": [source("entrypoint", file, line), source("sink", file, line)],
        "evidence": [{"file": file, "line": line, "description": "The cited path is the whole claim."}],
        "conditions": [],
        "execution": {
            "attacker_perspective": "A reader of the findings file.",
            "payloads": ["the cited path"],
            "instructions": ["Open the cited path and compare the line."],
            "observed_result": observed,
        },
        "remediation": {"strategy": "Open the cited path before accepting the record."},
        "severity": {
            "likelihood": {"score": "low", "reason": "Only the findings file is in play."},
            "impact": {"score": "low", "reason": "The effect is a false record."},
            "overall_severity": "low",
        },
        "confidence": {"score": "high", "reason": "The validator result is local."},
    }


def hazard_line(path: Path) -> int:
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if HAZARD in line:
            return number
    raise SystemExit(2)


def validate_case(name: str, role: str, target: Path | None, body: object | None, work: Path) -> dict:
    if body is not None:
        target = work / f"{name}.json"
        target.write_text(json.dumps(body) + "\n", encoding="utf-8")
    assert target is not None
    code, stdout, stderr, elapsed = run_cmd(
        ["node", str(SKILL / "validate-findings.cjs"), str(target)],
        cwd=SKILL,
        timeout=30,
    )
    combined = stdout + stderr
    return {
        "name": name,
        "role": role,
        "exit": code,
        "seconds": round(elapsed, 4),
        "stdout": clip(stdout),
        "stderr": clip(stderr),
        "mentions_hazard": HAZARD in combined,
    }


def check_pin() -> dict:
    problems = []
    if not SKILL.is_dir():
        problems.append(f"missing skill dir {SKILL}")
    head = ""
    tree = ""
    if (SRC / ".git").exists():
        code, stdout, stderr, _ = run_cmd(["git", "-C", str(SRC), "rev-parse", "HEAD"], cwd=SRC, timeout=20)
        head = stdout.strip()
        if code != 0:
            problems.append(clip(stderr) or "git rev-parse HEAD failed")
        code, stdout, stderr, _ = run_cmd(["git", "-C", str(SRC), "rev-parse", "HEAD^{tree}"], cwd=SRC, timeout=20)
        tree = stdout.strip()
        if code != 0:
            problems.append(clip(stderr) or "git rev-parse tree failed")
    else:
        problems.append("cache checkout has no .git")
    if head != PIN:
        problems.append(f"HEAD {head} != {PIN}")
    if tree != TREE:
        problems.append(f"tree {tree} != {TREE}")
    hashes = {}
    for name, expect in FILE_SHA256.items():
        path = SKILL / name
        if not path.is_file():
            problems.append(f"missing {name}")
            continue
        actual = sha256_file(path)
        hashes[name] = actual
        if actual != expect:
            problems.append(f"{name} sha256 {actual} != {expect}")
    return {"head": head, "tree": tree, "sha256": hashes, "problems": problems}


def main() -> int:
    pin = check_pin()
    fetched_text = FETCHED.read_text(encoding="utf-8")
    clean_text = CLEAN.read_text(encoding="utf-8")
    if fetched_text.count(HAZARD) != 1 or clean_text.count(HAZARD) != 0:
        pin["problems"].append("fixture hazard count drifted")
    if pin["problems"]:
        OUT.write_text(json.dumps({"pin": pin}, indent=2) + "\n", encoding="utf-8")
        return 2

    line = hazard_line(FETCHED)
    before = fetched_text.count(HAZARD)
    code, stdout, stderr, elapsed = run_cmd(
        [
            "node",
            "--test",
            "--test-reporter=tap",
            "validate-findings.test.cjs",
            "validate-coverage-ledger.test.cjs",
        ],
        cwd=SKILL,
        timeout=180,
    )
    tap = parse_tap(stdout + "\n" + stderr)
    upstream = {
        "exit": code,
        "seconds": round(elapsed, 4),
        "tests": int(tap.get("tests", 0)),
        "pass": int(tap.get("pass", 0)),
        "fail": int(tap.get("fail", 0)),
        "skipped": int(tap.get("skipped", 0)),
        "duration_ms": tap.get("duration_ms"),
        "tail": clip(stdout + stderr, 500) if code != 0 else "",
    }

    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="cf-audit-", dir=CACHE / "tmp") as tmp:
        work = Path(tmp)
        cases = [
            validate_case("fetched_skill_file", "skill_input", FETCHED, None, work),
            validate_case("clean_skill_file", "skill_input", CLEAN, None, work),
            validate_case("fetched_skill_dir", "skill_input", FETCHED.parent, None, work),
            validate_case(
                "empty_findings",
                "receipt",
                None,
                [],
                work,
            ),
            validate_case(
                "false_clear",
                "receipt",
                None,
                [
                    rejected(
                        FETCHED_REL,
                        line,
                        "fetched-probe-shell-rejected",
                        "The line is a comment in a fixture and does not run.",
                    )
                ],
                work,
            ),
            validate_case("missing_fields", "malformed", None, [{}], work),
            validate_case(
                "path_escape",
                "malformed",
                None,
                [rejected("../outside.py", 1, "path-escape", "The path leaves the tree.")],
                work,
            ),
            validate_case(
                "confirmed_missing_file",
                "citation",
                None,
                [
                    confirmed(
                        MISSING_REL,
                        1,
                        "missing-source-claim",
                        "The validator did not need the file to exist.",
                    )
                ],
                work,
            ),
            validate_case(
                "confirmed_false_claim",
                "citation",
                None,
                [
                    confirmed(
                        FETCHED_REL,
                        line,
                        "fetched-probe-shell-confirmed",
                        "The fixture process ran and changed a file outside the skill directory.",
                    )
                ],
                work,
            ),
        ]
    h2_seconds = round(time.perf_counter() - started, 4)
    after = FETCHED.read_text(encoding="utf-8").count(HAZARD)
    missing_exists = (ROOT / MISSING_REL).exists()

    skill_cases = [item for item in cases if item["role"] == "skill_input" and item["name"].endswith("_file")]
    separated = len({item["exit"] for item in skill_cases}) > 1
    receipts = [item for item in cases if item["role"] == "receipt"]
    passing_receipts = [item["name"] for item in receipts if item["exit"] == 0]
    malformed = [item for item in cases if item["role"] == "malformed"]
    missing = next(item for item in cases if item["name"] == "confirmed_missing_file")
    false_claim = next(item for item in cases if item["name"] == "confirmed_false_claim")

    summary = {
        "planted_hazard_lines": before,
        "hazard_lines_after": after,
        "hazard_line": line,
        "hazard_block_rule": "counted only when a case names shell=True in its output and exits non-zero",
        "hazards_blocked": sum(1 for item in cases if item["mentions_hazard"] and item["exit"] != 0),
        "skill_files": len(skill_cases),
        "skill_files_separated_by_exit": int(separated),
        "passing_receipts": passing_receipts,
        "passing_receipts_that_leave_hazard": passing_receipts if after == before and before == 1 else [],
        "malformed_rejected": sum(1 for item in malformed if item["exit"] != 0),
        "malformed_total": len(malformed),
        "missing_file_exists": missing_exists,
        "confirmed_missing_file_exit": missing["exit"],
        "confirmed_false_claim_exit": false_claim["exit"],
    }
    node_code, node_out, _, _ = run_cmd(["node", "--version"], cwd=SKILL, timeout=10)
    payload = {
        "question": "Does schema-checked findings block one planted shell=True skill line?",
        "full_audit_mode": "SKIPPED",
        "full_audit_reason": "Full mode needs a parent agent and isolated sub-agents. This lane does not call a model.",
        "pin": pin,
        "node": node_out.strip() if node_code == 0 else "",
        "worktree_bytes": dir_bytes(SRC, skip_git=True),
        "cache_bytes": dir_bytes(CACHE, skip_git=False),
        "upstream": upstream,
        "h2_seconds": h2_seconds,
        "summary": summary,
        "cases": cases,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    blocked = summary["hazards_blocked"]
    left = len(summary["passing_receipts_that_leave_hazard"])
    print(
        f"hazards_blocked={blocked}/{summary['planted_hazard_lines']} "
        f"passing_receipts_that_leave_hazard={left} "
        f"upstream={upstream['pass']}/{upstream['tests']} "
        f"seconds={upstream['seconds']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
