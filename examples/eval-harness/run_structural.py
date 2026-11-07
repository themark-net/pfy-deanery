#!/usr/bin/env python3
"""Tier S (structural): design/coding assist gates that never call an LLM.

Runs without Ollama/LiteLLM. Exit 0 only if all checks pass.

Checks:
  1. First-party Grok skills (verify_skills.py)
  2. Deterministic text scorers under tasks/*/score.py with fixtures/
  3. data/tools.json parses and has required schema fields
  4. Key design/coding skill SKILL.md files exist (agent-loops, investigate, one-shot, adr)
  5. Golden-task cards validate (validate_golden_tasks.py) when present
  6. pfy and scripts/pfy are git 100755, +x, and ./pfy help execs
  7. No encoded payloads / runtime-assembled shards under scripts/, pfy, gui/
     (scripts/check_no_encoded_payloads.py)
  8. pfylib unit tests: python3 -m unittest discover -s tests (ADR-0017; offline).
     --skip-unittests or PFY_SKIP_UNITTESTS=1 reports this check as SKIP.
  9. Catalog <-> implementation link (scripts/catalog_check.py; ADR-0015/0017)
  10. Catalog item v2 (scripts/catalog_item_validate.py)

Write summary to pipelines/eval/structural.latest.md when --write-md.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HARNESS = Path(__file__).resolve().parent
TASKS = HARNESS / "tasks"
VERIFY = ROOT / "bootstrap/grok-cli/scripts/verify_skills.py"
TOOLS_JSON = ROOT / "data/tools.json"
VALIDATE_GOLDEN = HARNESS / "validate_golden_tasks.py"
DESIGN_CODING_SKILLS = (
    "agent-loops",
    "investigate",
    "one-shot",
    "adr",
    "hermes-feedback",
    "docs",
    "open-questions",
)


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out


def check_skills() -> tuple[bool, str]:
    if not VERIFY.is_file():
        return False, "verify_skills.py missing"
    code, out = run([sys.executable, str(VERIFY)])
    lines = [ln for ln in out.splitlines() if ln.strip()]
    summary = next(
        (ln for ln in lines if ln.startswith("PASS") or ln.startswith("FAIL")),
        lines[-1] if lines else f"exit {code}",
    )
    return code == 0, summary


def check_tools_json() -> tuple[bool, str]:
    try:
        data = json.loads(TOOLS_JSON.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return False, f"parse error: {e}"
    tools = data.get("tools")
    if not isinstance(tools, list) or not tools:
        return False, "tools[] empty or missing"
    required = {"name", "primary_category", "github", "scores", "tier", "integration_stage"}
    bad = []
    for t in tools:
        missing = required - set(t.keys())
        if missing:
            bad.append(f"{t.get('name', '?')}: missing {sorted(missing)}")
            continue
        sc = t["scores"]
        for k in ("s1", "s2", "s3", "s4", "overall"):
            if k not in sc:
                bad.append(f"{t['name']}: scores.{k}")
        st = t.get("integration_stage")
        if st not in ("I0", "I1", "I2", "I3", "I4"):
            bad.append(f"{t['name']}: bad integration_stage={st!r}")
    if bad:
        return False, "; ".join(bad[:8])
    return True, f"ok n={len(tools)} version={data.get('version')} stages=required"


def check_design_skill_files() -> tuple[bool, str]:
    missing = []
    base = ROOT / "bootstrap/grok-cli/skills"
    for name in DESIGN_CODING_SKILLS:
        if name == "project-process":
            p = ROOT / "bootstrap/project-process/skills/project-process/SKILL.md"
        else:
            p = base / name / "SKILL.md"
        if not p.is_file():
            missing.append(name)
    if missing:
        return False, f"missing SKILL.md: {missing}"
    return True, f"ok {len(DESIGN_CODING_SKILLS)} design/coding skills"


def check_text_scorers() -> tuple[bool, str]:
    """For each tasks/*/score.py, run fixtures/pass* (expect 0) and fixtures/fail* (expect 1)."""
    reports: list[str] = []
    any_scorer = False
    for task_dir in sorted(TASKS.iterdir()):
        if not task_dir.is_dir():
            continue
        scorer = task_dir / "score.py"
        if not scorer.is_file():
            continue
        any_scorer = True
        fixtures = task_dir / "fixtures"
        if not fixtures.is_dir():
            reports.append(f"{task_dir.name}: no fixtures/")
            continue
        passes = list(fixtures.glob("pass*"))
        fails = list(fixtures.glob("fail*"))
        if not passes or not fails:
            reports.append(f"{task_dir.name}: need pass* and fail* fixtures")
            continue
        for f in passes:
            code, out = run([sys.executable, str(scorer), str(f)])
            if code != 0:
                reports.append(f"{task_dir.name}/{f.name}: expected PASS got {code} {out.strip()}")
        for f in fails:
            code, out = run([sys.executable, str(scorer), str(f)])
            if code == 0:
                reports.append(f"{task_dir.name}/{f.name}: expected FAIL got 0 {out.strip()}")
    if not any_scorer:
        return False, "no tasks/*/score.py found"
    if reports:
        return False, "; ".join(reports[:8])
    return True, "ok all text scorer fixtures"


def check_golden_tasks() -> tuple[bool, str]:
    cards = list((ROOT / "data" / "golden-tasks").glob("GT-*.json"))
    if not cards:
        return True, "skip (no GT-*.json yet)"
    if not VALIDATE_GOLDEN.is_file():
        return False, "validate_golden_tasks.py missing"
    code, out = run([sys.executable, str(VALIDATE_GOLDEN)])
    summary = next(
        (ln for ln in out.splitlines() if "PASS" in ln or "FAIL" in ln),
        f"exit {code}",
    )
    return code == 0, summary.strip()



def check_catalog_triple() -> tuple[bool, str]:
    """GAP-03: tools.json names should appear in TOOLS.md (soft: warn-as-fail for S-tier only)."""
    tools_md = ROOT / "TOOLS.md"
    if not tools_md.is_file():
        return False, "TOOLS.md missing"
    md = tools_md.read_text(encoding="utf-8", errors="replace")
    data = json.loads(TOOLS_JSON.read_text(encoding="utf-8"))
    missing = []
    for t in data.get("tools") or []:
        name = t.get("name") or ""
        if t.get("tier") == "S" and name and name not in md:
            missing.append(name)
    if missing:
        return False, f"S-tier not in TOOLS.md: {missing[:5]}"
    return True, f"ok S-tier names present in TOOLS.md n_tools={len(data.get('tools') or [])}"


def check_external_skills() -> tuple[bool, str]:
    """GAP-28: paths packs exist with SKILL.md."""
    packs = [
        ROOT / "bootstrap/grok-cli/skills-external/mattpocock/to-spec/SKILL.md",
        ROOT / "bootstrap/grok-cli/skills-external/mattpocock/tdd/SKILL.md",
        ROOT / "bootstrap/grok-cli/skills-external/ponytail/ponytail/SKILL.md",
        ROOT / "bootstrap/grok-cli/skills-external/claude-unified-agents/security-auditor/SKILL.md",
        ROOT / "bootstrap/grok-cli/skills-external/claude-unified-agents/PORT.md",
    ]
    miss = [str(p.relative_to(ROOT)) for p in packs if not p.is_file()]
    if miss:
        return False, f"missing {miss}"
    # curated pack integrity
    ua = ROOT / "bootstrap/grok-cli/skills-external/claude-unified-agents"
    n = len(list(ua.glob("*/SKILL.md"))) if ua.is_dir() else 0
    if n < 10:
        return False, f"claude-unified-agents too few skills: {n}"
    return True, f"ok external packs {len(packs)} ua_skills={n}"



LAUNCHERS = ("pfy", "scripts/pfy")


def check_launcher_filemode() -> tuple[bool, str]:
    """pfy and scripts/pfy must be git 100755 and +x after clone/pull."""
    bad: list[str] = []
    for rel in LAUNCHERS:
        code, out = run(["git", "ls-files", "-s", "--", rel])
        parts = out.split()
        mode = parts[0] if parts else ""
        if mode != "100755":
            bad.append(f"{rel} gitmode={mode or 'missing'}")
        path = ROOT / rel
        if not path.is_file():
            bad.append(f"{rel} missing")
        elif not os.access(path, os.X_OK):
            bad.append(f"{rel} not executable")
    if bad:
        return False, "; ".join(bad)
    return True, "ok 100755 pfy scripts/pfy"


def check_launcher_runs() -> tuple[bool, str]:
    """Bare ./pfy must exec. Permission denied / not-executable is FAIL."""
    path = ROOT / "pfy"
    if not path.is_file():
        return False, "pfy missing"
    if not os.access(path, os.X_OK):
        return False, "permission denied ./pfy"
    proc = subprocess.run([str(path), "help"], cwd=ROOT, capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode == 126 or "Permission denied" in out:
        return False, "permission denied ./pfy"
    if proc.returncode != 0:
        tail = out.strip().replace("\n", " ")[-200:]
        return False, f"./pfy help exit {proc.returncode} {tail}"
    return True, "ok ./pfy help"


NO_PAYLOADS = ROOT / "scripts/check_no_encoded_payloads.py"


def check_no_encoded_payloads() -> tuple[bool, str]:
    """No base64/gzip payloads or runtime-concatenated shards under scripts/, pfy, gui/."""
    if not NO_PAYLOADS.is_file():
        return False, "check_no_encoded_payloads.py missing"
    code, out = run([sys.executable, str(NO_PAYLOADS)])
    lines = [ln for ln in out.splitlines() if ln.strip()]
    if code == 0:
        return True, lines[0].split(":", 1)[-1].strip() if lines else "ok"
    offenders = [ln.strip()[2:] for ln in lines if ln.strip().startswith("- ")]
    return False, f"{len(offenders)} offender(s): " + "; ".join(offenders[:4])


def _skip_unittests() -> bool:
    if os.environ.get("PFY_STRUCTURAL_SKIP_UNITTESTS", "").strip() in {"1", "true", "TRUE", "yes"}:
        return True
    return os.environ.get("PFY_SKIP_UNITTESTS", "").strip() in {"1", "true", "TRUE", "yes"}


def check_pfylib_unittests() -> tuple[bool, str] | tuple[str, str]:
    """ADR-0017: tests/ (stdlib unittest) must pass offline; isolated state dir so nothing touches ~/.pfy-mentat.

    SKIP is named. Callers that run the suite themselves pass --skip-unittests
    or PFY_SKIP_UNITTESTS=1. A skipped check is not a pass of the suite.
    """
    if _skip_unittests():
        return "SKIP", "named skip: caller runs the suite separately (--skip-unittests or PFY_SKIP_UNITTESTS=1)"
    tests_dir = ROOT / "tests"
    if not tests_dir.is_dir():
        return False, "tests/ missing"
    env = dict(os.environ)
    with tempfile.TemporaryDirectory(prefix="pfy-structural-state-") as state:
        env["PFY_STATE_DIR"] = state
        p = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(tests_dir), "-t", str(ROOT)],
            cwd=ROOT, capture_output=True, text=True, env=env,
        )
    out = (p.stdout or "") + (p.stderr or "")
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    ran = next((ln for ln in lines if ln.startswith("Ran ")), "")
    verdict = lines[-1] if lines else f"exit {p.returncode}"
    if p.returncode != 0:
        fails = [ln for ln in lines if ln.startswith(("FAIL:", "ERROR:"))]
        return False, f"{ran} · {verdict} · " + "; ".join(fails[:4])
    return True, f"{ran} · {verdict}"


def check_catalog_item_v2() -> tuple[bool, str]:
    """Catalog item v2 rows pass scripts/catalog_item_validate.py."""
    script = ROOT / "scripts/catalog_item_validate.py"
    if not script.is_file():
        return False, "scripts/catalog_item_validate.py missing"
    code, out = run([sys.executable, str(script)])
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if code == 0:
        return True, (lines[0] if lines else "ok")
    return False, "; ".join(lines[:4]) or f"exit {code}"


def check_catalog_link() -> tuple[bool, str]:
    """ADR-0017: tools.json implementation <-> data/toolsets.json catalog_tool, via scripts/catalog_check.py."""
    script = ROOT / "scripts/catalog_check.py"
    if not script.is_file():
        return False, "scripts/catalog_check.py missing"
    code, out = run([sys.executable, str(script)])
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if code == 0:
        return True, (lines[0] if lines else "ok").removeprefix("PASS ").strip()
    return False, "; ".join(ln.lstrip("- ") for ln in lines[1:5]) or (lines[0] if lines else f"exit {code}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write-md", type=Path, default=None)
    ap.add_argument(
        "--skip-unittests",
        action="store_true",
        help="report pfylib_unittests as SKIP; the caller runs the suite",
    )
    args = ap.parse_args()
    if args.skip_unittests:
        os.environ["PFY_STRUCTURAL_SKIP_UNITTESTS"] = "1"

    checks = [
        ("skills_manifest", check_skills),
        ("tools_json_schema", check_tools_json),
        ("catalog_triple_s_tier", check_catalog_triple),
        ("external_skills_paths", check_external_skills),
        ("design_coding_skills", check_design_skill_files),
        ("text_scorer_fixtures", check_text_scorers),
        ("golden_tasks", check_golden_tasks),
        ("launcher_filemode", check_launcher_filemode),
        ("launcher_runs", check_launcher_runs),
        ("no_encoded_payloads", check_no_encoded_payloads),
        ("pfylib_unittests", check_pfylib_unittests),
        ("catalog_implementation_link", check_catalog_link),
        ("catalog_item_v2", check_catalog_item_v2),
    ]
    rows: list[tuple[str, str, str]] = []
    for name, fn in checks:
        raw, detail = fn()
        if raw == "SKIP":
            status = "SKIP"
        else:
            status = "PASS" if raw else "FAIL"
        rows.append((name, status, detail))
        print(f"{status}  {name}: {detail}", flush=True)

    all_ok = all(status != "FAIL" for _, status, _ in rows)
    print(f"\nSTRUCTURAL EVAL: {'PASS' if all_ok else 'FAIL'}", flush=True)

    if args.write_md:
        args.write_md.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"# Structural eval (design/coding) — {datetime.now(timezone.utc).isoformat()}",
            "",
            "| Check | Result | Detail |",
            "|-------|--------|--------|",
        ]
        for name, status, detail in rows:
            lines.append(f"| `{name}` | {status} | {detail.replace('|', '/')} |")
        lines.append("")
        lines.append(f"**Overall:** {'PASS' if all_ok else 'FAIL'} (no LLM required)")
        lines.append("")
        args.write_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"wrote {args.write_md}", flush=True)

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
