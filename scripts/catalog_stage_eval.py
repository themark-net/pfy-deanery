#!/usr/bin/env python3
"""T-0005: facts from TOOLS.md, judgments from data/catalog_stage_handoff.json.

Deterministic (recomputed every run): tier, scores, tags, github, posture
phrases, repo evidence, tier ceiling. Those do not change integration_stage.

LLM handoff (written once, not recomputed): uses, features, potential,
non-goals added beyond the card, next_gate.

  python3 scripts/catalog_stage_eval.py            # report
  python3 scripts/catalog_stage_eval.py --apply    # merge handoff into stage cards
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def _catalog_check():
    spec = importlib.util.spec_from_file_location("catalog_check", ROOT / "scripts" / "catalog_check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_cc = _catalog_check()
CARD = _cc.CARD
tools_md_names = _cc.tools_md_names

STAGES_PATH = ROOT / "data" / "tool_integration_stages.json"
HANDOFF_PATH = ROOT / "data" / "catalog_stage_handoff.json"
METHODS_PATH = ROOT / "data" / "catalog_stage_methods.json"
TOOLS_MD = ROOT / "TOOLS.md"
MAKEFILE = ROOT / "Makefile"

CELL_RE = re.compile(r"^\| (.+) \|$")
POSTURE = (
    ("not_integrated", re.compile(r"not integrated", re.I)),
    ("reference_only", re.compile(r"reference only|not primary", re.I)),
    ("skip_install", re.compile(r"skip install", re.I)),
    ("i1_stay", re.compile(r"I1 stay", re.I)),
    ("i0_explicit", re.compile(r"\(I0\)|\bI0\b", re.I)),
    ("docs_only", re.compile(r"docs-only|docs only", re.I)),
    ("pattern_only", re.compile(r"pattern only|do not clone|raw-port-blocked", re.I)),
    ("no_weights", re.compile(r"no weights", re.I)),
)
TIER_CEILING = {"S": "I3", "A": "I1", "B": "I1", "C": "I0"}
EVIDENCE_TARGETS = {
    "Grok CLI bootstrap": "smoke-grok-skills",
    "agent-cage (PNNL)": "cage-grok",
    "codebase-memory-mcp": "smoke-codebase-memory",
    "LiteLLM": "smoke-litellm-ollama",
    "Ollama": "smoke-litellm-ollama",
    "repowise": "smoke-repowise",
    "write-guard-mcp": "smoke-write-guard",
    "eval-harness (pfy)": "eval-structural",
}
PATH_EVIDENCE = {
    "Grok CLI bootstrap": "bootstrap/grok-cli",
    "project-process bootstrap": "bootstrap/project-process",
    "AgenC": "bootstrap/agenc",
    "agent-cage (PNNL)": "harness/agent-cage",
    "Continue.dev": "bootstrap/continue",
    "write-guard-mcp": "harness/write-guard-mcp",
    "eval-harness (pfy)": "examples/eval-harness",
    "Hermes Agent (feedback loops)": "bootstrap/grok-cli/skills/hermes-feedback",
    "Finn Loop / eval-loop / 8-exits patterns": "bootstrap/grok-cli/skills/agent-loops",
    "ponytail (skills pack)": "bootstrap/grok-cli/skills-external/ponytail",
    "karpathy-guidelines": "bootstrap/grok-cli/skills/karpathy-guidelines",
    "mattpocock/skills": "bootstrap/grok-cli/skills-external/mattpocock",
    "marketing-skills (marketing-council)": "bootstrap/grok-cli/skills/marketing-council",
}

DETERMINISTIC = [
    "catalog_tier",
    "catalog_scores",
    "catalog_tags",
    "catalog_github",
    "posture",
    "evidence",
    "tier_ceiling",
]
LLM = ["uses", "features", "potential", "non_goals", "next_gate"]


def parse_tools_md(md: str) -> list[dict]:
    rows = []
    for line in md.splitlines():
        if not line.startswith("| **"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 11:
            continue
        raw = cells[0]
        bold = re.match(r"\*\*([^*]+)\*\*(.*)", raw)
        if not bold:
            continue
        short, rest = bold.group(1).strip(), bold.group(2).strip()
        full = re.sub(r"\s+", " ", f"{short} {rest}".strip())
        if len(cells) >= 13 and re.fullmatch(r"\*\*[SABC]\*\*", cells[10] or ""):
            tier = cells[10].replace("*", "")
            scores = cells[3:9]
            overall = cells[9].replace("*", "")
            tags, notes, github, cat = cells[11], cells[12], cells[2], cells[1]
        else:
            tier = cells[8]
            scores = cells[3:7]
            overall = cells[7]
            tags, notes, github, cat = cells[9], cells[10], cells[2], cells[1]
        rows.append({
            "full": full,
            "short": short,
            "tier": tier,
            "scores": scores,
            "overall": overall,
            "tags": [t for t in tags.split() if t.startswith("#")],
            "github": github,
            "notes": notes,
            "category": cat,
        })
    return rows


def resolve_name(row: dict, keys: set[str]) -> str:
    if row["full"] in keys:
        return row["full"]
    if row["short"] in keys:
        return row["short"]
    return row["full"]


def posture_flags(notes: str) -> list[str]:
    return [name for name, rx in POSTURE if rx.search(notes or "")]


def tier_ceiling(tier: str, flags: list[str]) -> str:
    if "i0_explicit" in flags or "skip_install" in flags or "reference_only" in flags:
        return "I0"
    if "not_integrated" in flags or "i1_stay" in flags or "docs_only" in flags or "pattern_only" in flags:
        return "I1"
    return TIER_CEILING.get(tier, "I1")


def evidence_for(name: str, card: dict, makefile: str, toolset_names: set[str]) -> list[str]:
    found = []
    target = EVIDENCE_TARGETS.get(name)
    if target and target in makefile:
        found.append("make:%s" % target)
    path = PATH_EVIDENCE.get(name)
    if path and (ROOT / path).exists():
        found.append("path:%s" % path)
    doc = card.get("notes_doc")
    if doc and (ROOT / doc).is_file():
        found.append("notes_doc:%s" % doc)
    if card.get("pin"):
        found.append("pin")
    if name in toolset_names:
        found.append("toolset")
    return found


def load() -> tuple[dict, dict, str]:
    stages = json.loads(STAGES_PATH.read_text(encoding="utf-8"))
    handoff = json.loads(HANDOFF_PATH.read_text(encoding="utf-8"))
    makefile = MAKEFILE.read_text(encoding="utf-8", errors="replace") if MAKEFILE.is_file() else ""
    return stages, handoff, makefile


def toolset_catalog_names() -> set[str]:
    from pfylib import registry
    return {t.get("catalog_tool") for t in registry.toolset_rows(ROOT) if t.get("catalog_tool")}


def evaluations() -> list[dict]:
    stages, handoff, makefile = load()
    cards = stages["tools"]
    keys = set(cards)
    linked = toolset_catalog_names()
    out = []
    for row in parse_tools_md(TOOLS_MD.read_text(encoding="utf-8")):
        name = resolve_name(row, keys)
        card = cards.get(name) or {}
        flags = posture_flags(row["notes"])
        ev = evidence_for(name, card, makefile, linked)
        judge = handoff.get(name) or {}
        out.append({
            "name": name,
            "tier": row["tier"],
            "scores": row["scores"],
            "overall": row["overall"],
            "tags": row["tags"],
            "github": row["github"],
            "posture": flags,
            "evidence": ev,
            "tier_ceiling": tier_ceiling(row["tier"], flags),
            "integration_stage": card.get("integration_stage"),
            "handoff": judge,
            "methods": {
                "deterministic": DETERMINISTIC,
                "llm": [k for k in LLM if judge.get(k)],
            },
        })
    return out


def apply() -> int:
    stages, handoff, _makefile = load()
    cards = stages["tools"]
    missing = []
    for ev in evaluations():
        name = ev["name"]
        card = cards.get(name)
        if card is None:
            missing.append(name)
            continue
        judge = ev["handoff"]
        card["catalog_tier"] = ev["tier"]
        card["catalog_overall"] = ev["overall"]
        card["catalog_tags"] = ev["tags"]
        card["catalog_github"] = ev["github"]
        card["posture"] = ev["posture"]
        card["evidence"] = ev["evidence"]
        card["tier_ceiling"] = ev["tier_ceiling"]
        if not judge:
            continue
        card["uses"] = judge["uses"]
        card["features"] = judge["features"]
        card["potential"] = judge["potential"]
        card["next_gate"] = judge["next_gate"]
        card["handoff_by"] = "llm"
        prior = list(card.get("non_goals") or [])
        for item in judge.get("non_goals") or []:
            if item not in prior:
                prior.append(item)
        card["non_goals"] = prior
    if missing:
        print("FAIL no stage card: %s" % missing)
        return 1
    stages["last_updated"] = "2026-09-25"
    stages["handoff"] = "data/catalog_stage_handoff.json"
    STAGES_PATH.write_text(json.dumps(stages, indent=2) + "\n", encoding="utf-8")
    methods = {
        "deterministic": {
            "attributes": DETERMINISTIC,
            "how": [
                "Parse the TOOLS.md table cell (tier, scores, tags, github).",
                "Resolve the bold name plus parenthetical onto an existing stage key.",
                "Regex the notes for not-integrated, reference-only, skip-install, I0, I1-stay, docs-only, pattern-only.",
                "Tier ceiling: those phrases cap I0 or I1; otherwise S→I3, A/B→I1, C→I0. Ceiling is not a promotion.",
                "Evidence: known Makefile target, known repo path, notes_doc file, pin, toolset catalog_tool.",
            ],
        },
        "llm": {
            "attributes": LLM,
            "how": "Judged once from the catalog note and ADRs. Stored in catalog_stage_handoff.json. Re-run does not invent a new potential.",
        },
        "per_tool": [
            {"name": ev["name"], "posture": ev["posture"], "evidence": ev["evidence"], "ceiling": ev["tier_ceiling"], "llm": ev["methods"]["llm"]}
            for ev in evaluations()
        ],
    }
    METHODS_PATH.write_text(json.dumps(methods, indent=2) + "\n", encoding="utf-8")
    open_n = sum(1 for ev in evaluations() if any(not (cards[ev["name"]].get(k)) for k in CARD))
    print("applied %d cards · still open %d · methods %s" % (len(evaluations()), open_n, METHODS_PATH.relative_to(ROOT)))
    return 0


def report() -> int:
    rows = evaluations()
    print("tools %d · handoff %d" % (len(rows), sum(1 for r in rows if r["handoff"])))
    for r in rows:
        h = r["handoff"]
        print("%s stage=%s ceiling=%s potential=%s posture=%s evidence=%s" % (
            r["name"], r["integration_stage"], r["tier_ceiling"], h.get("potential", "—"),
            ",".join(r["posture"]) or "-", ",".join(r["evidence"]) or "-",
        ))
    return 0


def main() -> int:
    if "--apply" in sys.argv:
        return apply()
    return report()


if __name__ == "__main__":
    sys.exit(main())
