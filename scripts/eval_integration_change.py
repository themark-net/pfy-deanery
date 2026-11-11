#!/usr/bin/env python3
"""Exo-inspired self-mod eval for catalog/skill/smoke ingestion (pfy-deanery).

Hard gates → adopt | soft-only → hold | hard fail → rollback.
Writes pipelines/eval/integration-change.latest.{md,json}
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out


def gate_structural() -> tuple[bool, str]:
    code, out = run([sys.executable, "examples/eval-harness/run_structural.py"])
    summary = next(
        (ln for ln in out.splitlines() if "STRUCTURAL" in ln or ln.startswith("PASS") or ln.startswith("FAIL")),
        out[-200:],
    )
    return code == 0, summary.strip()


def gate_golden() -> tuple[bool, str]:
    code, out = run([sys.executable, "examples/eval-harness/run_golden.py"])
    last = [ln for ln in out.splitlines() if ln.strip()][-1:] or [f"exit {code}"]
    return code == 0, last[0]


def gate_catalog() -> tuple[bool, str]:
    path = ROOT / "data/tools.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return False, f"parse: {e}"
    tools = data.get("tools") or []
    bad = []
    for t in tools:
        if "integration_stage" not in t:
            bad.append(t.get("name", "?"))
            continue
        if t["integration_stage"] not in ("I0", "I1", "I2", "I3", "I4"):
            bad.append(f"{t.get('name')}:{t.get('integration_stage')}")
    if bad:
        return False, f"stage issues: {bad[:5]}"
    return True, f"ok n={len(tools)} v={data.get('version')}"


def gate_triple_soft() -> tuple[bool, str, bool]:
    """Returns ok, detail, hard_if_failed (True when new S-tier missing)."""
    code, out = run([sys.executable, "scripts/catalog_check.py"])
    return code == 0, out.strip().splitlines()[-1] if out.strip() else f"exit {code}", True


def gate_smoke_contract() -> tuple[bool, str]:
    code, out = run([sys.executable, "scripts/smoke_contract_lint.py"])
    return code == 0, (out.strip().splitlines() or [f"exit {code}"])[-1]


def gate_size_policy() -> tuple[bool, str]:
    """Hard: no obvious weight files; warn large skill dumps."""
    bad = []
    for pat in ("*.gguf", "*.bin", "*.safetensors"):
        for p in ROOT.rglob(pat):
            if ".git" in p.parts or "node_modules" in p.parts:
                continue
            bad.append(str(p.relative_to(ROOT)))
    if bad:
        return False, f"weight-like files in repo: {bad[:5]}"
    # soft warn via notes handled elsewhere
    large = []
    ua = ROOT / "bootstrap/grok-cli/skills-external"
    if ua.is_dir():
        for skill in ua.rglob("SKILL.md"):
            n = sum(1 for _ in skill.open(encoding="utf-8", errors="replace"))
            if n > 600:
                large.append(f"{skill.relative_to(ROOT)}:{n}L")
    detail = "ok no weights"
    if large:
        detail += f"; large skills (info): {large[:5]}"
    return True, detail


def gate_paths_pack() -> tuple[bool, str]:
    packs = [
        ROOT / "bootstrap/grok-cli/skills-external/claude-unified-agents",
        ROOT / "bootstrap/grok-cli/skills-external/mattpocock",
        ROOT / "bootstrap/grok-cli/skills-external/ponytail",
    ]
    notes = []
    for p in packs:
        if not p.is_dir():
            notes.append(f"missing {p.name}")
            continue
        n = len(list(p.glob("*/SKILL.md")))
        notes.append(f"{p.name}={n}")
    # claude pack should stay >=10 if present
    cua = ROOT / "bootstrap/grok-cli/skills-external/claude-unified-agents"
    if cua.is_dir() and len(list(cua.glob("*/SKILL.md"))) < 10:
        return False, "claude-unified-agents degraded: " + ", ".join(notes)
    return True, ", ".join(notes)


def git_blast_radius() -> str:
    code, out = run(["git", "status", "--short"])
    if code != 0:
        return "git unavailable"
    lines = [ln for ln in out.splitlines() if ln.strip()]
    classes = {"catalog": 0, "skills": 0, "eval": 0, "docs": 0, "ci": 0, "other": 0}
    for ln in lines:
        path = ln[3:].strip() if len(ln) > 3 else ln
        if path.startswith("data/") or path in ("TOOLS.md", "CATEGORIZATION.md"):
            classes["catalog"] += 1
        elif "skills" in path or path.startswith("bootstrap/"):
            classes["skills"] += 1
        elif path.startswith("examples/eval") or path.startswith("pipelines/"):
            classes["eval"] += 1
        elif path.startswith("docs/"):
            classes["docs"] += 1
        elif path.startswith(".github/"):
            classes["ci"] += 1
        else:
            classes["other"] += 1
    return f"dirty={len(lines)} " + " ".join(f"{k}={v}" for k, v in classes.items() if v)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reason", default=os.environ.get("REASON", "unspecified integration change"))
    ap.add_argument("--strict-soft", action="store_true", help="treat soft fails as rollback")
    args = ap.parse_args()

    rows: list[dict] = []

    def add(gid: str, name: str, hard: bool, ok: bool, detail: str) -> None:
        rows.append({"id": gid, "name": name, "hard": hard, "ok": ok, "detail": detail[:500]})

    ok, d = gate_structural()
    add("S1", "structural_G0", True, ok, d)
    ok, d = gate_golden()
    add("S2", "golden_cards", True, ok, d)
    ok, d = gate_catalog()
    add("S3", "catalog_schema", True, ok, d)
    ok, d, _ = gate_triple_soft()
    add("S4", "triple_write_S_tier", False, ok, d)
    ok, d = gate_smoke_contract()
    add("S5", "smoke_contract", False, ok, d)
    ok, d = gate_size_policy()
    add("S6", "size_policy_no_weights", True, ok, d)
    ok, d = gate_paths_pack()
    add("S7", "paths_pack_integrity", False, ok, d)
    add("S8", "diff_blast_radius", False, True, git_blast_radius())
    add("S0", "intent", False, True, args.reason)

    hard_fail = [r for r in rows if r["hard"] and not r["ok"]]
    soft_fail = [r for r in rows if not r["hard"] and not r["ok"]]
    if hard_fail or (args.strict_soft and soft_fail):
        outcome = "rollback"
    elif soft_fail:
        outcome = "hold"
    else:
        outcome = "adopt"

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    md_lines = [
        "# Integration self-mod eval",
        "",
        f"date: {ts}",
        f"reason: {args.reason}",
        f"outcome: **{outcome}**",
        "",
        "| ID | Gate | Hard | Result | Detail |",
        "|----|------|:----:|:------:|--------|",
    ]
    for r in rows:
        md_lines.append(
            f"| {r['id']} | {r['name']} | {'Y' if r['hard'] else 'n'} | "
            f"{'PASS' if r['ok'] else 'FAIL'} | {r['detail'][:80]} |"
        )
    md_lines += [
        "",
        "## Exo mapping",
        "",
        "- Before: intent + optional branch (snapshot)",
        "- Validate: this script (S1–S7)",
        "- Adopt/hold/rollback: outcome above",
        "- Memory: this receipt under pipelines/eval/",
        "",
    ]
    out_md = ROOT / "pipelines/eval/integration-change.latest.md"
    out_json = ROOT / "pipelines/eval/integration-change.latest.json"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    payload = {
        "date": ts,
        "reason": args.reason,
        "outcome": outcome,
        "gates": rows,
        "hard_failures": [r["id"] for r in hard_fail],
        "soft_failures": [r["id"] for r in soft_fail],
    }
    out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"outcome={outcome}")
    for r in rows:
        print(f"  {'HARD' if r['hard'] else 'soft'} {r['id']} {'PASS' if r['ok'] else 'FAIL'}: {r['detail'][:100]}")
    print(f"wrote {out_md}")

    return 0 if outcome != "rollback" else 1


if __name__ == "__main__":
    raise SystemExit(main())
