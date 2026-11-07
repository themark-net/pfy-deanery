#!/usr/bin/env python3
"""Run SkillSpector in static mode on each skill path and write one JSON receipt.

Exit 0 when every path is SAFE. CAUTION is not safe unless --allow-caution.
Exit 1 when any path is flagged. Prints the path, the recommendation, and the top findings.
Exit 2 when the binary is missing or the scanner output is unreadable, with a next step.

Never requests LLM analysis. Binary lookup: PFY_SKILLSPECTOR_BIN, then PATH.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

TITLE_MAX = 160
TOP_FINDINGS = 5
DROP_ENV = (
    "SKILLSPECTOR_PROVIDER",
    "SKILLSPECTOR_MODEL",
    "SKILLSPECTOR_COMPAT_API_KEY",
    "SKILLSPECTOR_COMPAT_BASE_URL",
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_PROXY_API_KEY",
    "ANTHROPIC_PROXY_ENDPOINT_URL",
    "NVIDIA_INFERENCE_KEY",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
)


def state_dir() -> Path:
    return Path(os.environ.get("PFY_STATE_DIR") or (Path.home() / ".pfy-mentat"))


def find_binary() -> Path | None:
    """PFY_SKILLSPECTOR_BIN wins. A set but unusable value does not fall through to PATH."""
    chosen = os.environ.get("PFY_SKILLSPECTOR_BIN")
    if chosen:
        path = Path(chosen)
        if path.is_file() and os.access(path, os.X_OK):
            return path
        return None
    found = shutil.which("skillspector")
    if found:
        return Path(found)
    return None


def short_title(issue: dict) -> str:
    raw = issue.get("finding") or issue.get("title") or issue.get("pattern") or issue.get("message") or ""
    return " ".join(str(raw).split())[:TITLE_MAX]


def findings_from(report: dict) -> list[dict]:
    issues = report.get("issues")
    if not isinstance(issues, list):
        return []
    out = []
    for issue in issues:
        if not isinstance(issue, dict):
            continue
        loc = issue.get("location") if isinstance(issue.get("location"), dict) else {}
        out.append(
            {
                "id": str(issue.get("id") or issue.get("rule_id") or ""),
                "category": str(issue.get("category") or ""),
                "severity": str(issue.get("severity") or ""),
                "title": short_title(issue),
                "file": str(loc.get("file") or issue.get("file") or ""),
                "line": loc.get("start_line", issue.get("start_line")),
            }
        )
    return out


def is_safe(recommendation: str, allow_caution: bool) -> bool:
    if recommendation == "SAFE":
        return True
    if recommendation == "CAUTION" and allow_caution:
        return True
    return False


def child_env() -> dict[str, str]:
    env = os.environ.copy()
    for key in DROP_ENV:
        env.pop(key, None)
    return env


def run_scan(binary: Path, skill: str, report_path: Path) -> tuple[int | None, str]:
    """Return (exit code or None on launch failure, error text)."""
    cmd = [
        str(binary),
        "scan",
        skill,
        "--no-llm",
        "--format",
        "json",
        "--output",
        str(report_path),
    ]
    try:
        proc = subprocess.run(
            cmd,
            env=child_env(),
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    err = (proc.stderr or proc.stdout or "").strip()
    return proc.returncode, err


def load_report(report_path: Path) -> dict | None:
    if not report_path.is_file():
        return None
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    risk = data.get("risk_assessment")
    if not isinstance(risk, dict):
        return None
    recommendation = risk.get("recommendation")
    if not isinstance(recommendation, str) or not recommendation.strip():
        return None
    data["risk_assessment"] = risk
    return data


def print_flagged(path: str, recommendation: str, findings: list[dict]) -> None:
    print(f"path: {path}")
    print(f"recommendation: {recommendation}")
    shown = findings[:TOP_FINDINGS]
    if not shown:
        print("findings: none")
        return
    print("findings:")
    for item in shown:
        ident = item["id"] or "?"
        category = item["category"]
        title = item["title"]
        label = f"{ident} {category}".strip()
        if title:
            print(f"  {label}: {title}")
        else:
            print(f"  {label}")


def write_receipt(path: Path, receipt: dict) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"Next: could not write the receipt at {path} ({exc}). Pass --out to a writable file.")
        return False
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Static SkillSpector scan. Never uses the LLM mode.")
    parser.add_argument("paths", nargs="*", help="Skill file or directory to scan")
    parser.add_argument("--out", default="", help="Receipt JSON path. Default: $PFY_STATE_DIR/skill-scan.json")
    parser.add_argument(
        "--allow-caution",
        action="store_true",
        help="Treat CAUTION as safe. The default blocks CAUTION.",
    )
    args = parser.parse_args(argv)
    out_path = Path(args.out) if args.out else state_dir() / "skill-scan.json"

    if not args.paths:
        print("Next: pass one or more skill paths. Example: python3 scripts/pfy_skill_scan.py path/to/skill")
        write_receipt(
            out_path,
            {
                "mode": "static",
                "llm": False,
                "allow_caution": bool(args.allow_caution),
                "verdict": "ERROR",
                "reason": "no paths",
                "paths": [],
            },
        )
        return 2

    binary = find_binary()
    receipt: dict = {
        "mode": "static",
        "llm": False,
        "allow_caution": bool(args.allow_caution),
        "binary": str(binary) if binary else "",
        "verdict": "SAFE",
        "paths": [],
    }
    if binary is None:
        receipt["verdict"] = "ERROR"
        receipt["reason"] = "binary missing"
        print(
            "Next: install SkillSpector and set PFY_SKILLSPECTOR_BIN to the executable, "
            "or put skillspector on PATH. See docs/ops/skill-scan.md."
        )
        write_receipt(out_path, receipt)
        return 2

    flagged = False
    unreadable = False
    scratch = out_path.parent / ".skill-scan-work"
    try:
        scratch.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"Next: could not create a work directory next to the receipt ({exc}). Pass --out to a writable path.")
        return 2

    for index, skill in enumerate(args.paths):
        report_path = scratch / f"report-{index}.json"
        if report_path.exists():
            report_path.unlink()
        code, err = run_scan(binary, skill, report_path)
        report = load_report(report_path)
        if report is None:
            unreadable = True
            receipt["paths"].append(
                {
                    "path": skill,
                    "ok": False,
                    "error": "unreadable",
                    "scanner_exit": code,
                    "recommendation": "",
                    "score": None,
                    "severity": "",
                    "findings": [],
                }
            )
            detail = ""
            if err:
                detail = " scanner said: " + " ".join(err.splitlines()[0].split())[:200]
            print(f"path: {skill}")
            print(f"Next: SkillSpector did not write readable JSON for {skill}.{detail}")
            print("Next: check PFY_SKILLSPECTOR_BIN points at SkillSpector and rerun. See docs/ops/skill-scan.md.")
            continue
        risk = report["risk_assessment"]
        recommendation = str(risk.get("recommendation")).strip()
        findings = findings_from(report)
        safe = is_safe(recommendation, args.allow_caution)
        if not safe:
            flagged = True
            print_flagged(skill, recommendation, findings)
        receipt["paths"].append(
            {
                "path": skill,
                "ok": safe,
                "recommendation": recommendation,
                "score": risk.get("score"),
                "severity": risk.get("severity") if isinstance(risk.get("severity"), str) else "",
                "scanner_exit": code,
                "findings": findings,
            }
        )

    if unreadable:
        receipt["verdict"] = "ERROR"
        status = 2
    elif flagged:
        receipt["verdict"] = "FLAGGED"
        status = 1
    else:
        receipt["verdict"] = "SAFE"
        status = 0
    if not write_receipt(out_path, receipt):
        return 2
    try:
        for child in scratch.iterdir():
            child.unlink()
        scratch.rmdir()
    except OSError:
        pass
    return status


if __name__ == "__main__":
    sys.exit(main())
