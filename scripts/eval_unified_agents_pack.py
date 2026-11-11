#!/usr/bin/env python3
"""Extensive eval loop: stretchcloud/claude-code-unified-agents pack.

Scores each agent markdown for structural quality, Claude lock-in, bloat,
overlap with pfy-deanery skills, and port priority. Writes markdown + JSON.
Exit 0 always (observational) unless --strict and pack fails gate.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Agents we already cover (first-party or paths)
EXISTING = {
    "code-reviewer": "mattpocock code-review / ponytail-review",
    "error-detective": "/investigate",
    "orchestrator": "/agent-loops + /worker-monitor",
    "context-manager": "/hermes-feedback + memory",
    "documentation-writer": "/docs + /catalog-docs",
    "technical-writer": "/docs",
    "project-manager": "TODO/OQ process",
    "product-strategist": "/adr + DESIGN",
    "requirements-analyst": "mattpocock to-spec",
    "test-engineer": "make smoke-* / eval-structural",
    "workflow-optimizer": "CI + one-shot DoDs",
    "agent-generator": "skill authoring (catalog-docs)",
}

# High local-agent value for Grok+cage even if overlap
HIGH_SIGNAL = {
    "security-auditor",
    "code-reviewer",
    "error-detective",
    "orchestrator",
    "test-engineer",
    "e2e-test-specialist",
    "performance-engineer",
    "accessibility-auditor",
    "api-designer",
    "devops-engineer",
    "incident-responder",
    "prompt-engineer",
    "context-manager",
    "backend-architect",
    "ux-designer",
}

CLAUDE_LOCKIN = re.compile(
    r"\b(claude code|claude\.ai|anthropic|/agents|@[\w-]+|MultiEdit|Task tool)\b",
    re.I,
)
CODE_FENCE = re.compile(r"```[\w]*\n[\s\S]*?```")
FRONTMATTER = re.compile(r"^---\s*\n([\s\S]*?)\n---\s*\n", re.M)


@dataclass
class AgentScore:
    path: str
    name: str
    category: str
    lines: int
    has_frontmatter: bool
    has_name: bool
    has_description: bool
    has_tools: bool
    description_len: int
    body_lines: int
    code_fence_count: int
    code_lines_est: int
    claude_lockin_hits: int
    structural: float  # 0-5
    content_density: float  # 0-5 prose vs code dump
    portability: float  # 0-5 Grok/cage fit
    uniqueness: float  # 0-5 vs our stack
    relevance: float  # 0-5 local agent workflow
    overall: float
    pass_gate: bool
    notes: list[str] = field(default_factory=list)
    port_action: str = "skip"  # first_party | paths | docs_map | skip


def parse_frontmatter(text: str) -> dict:
    m = FRONTMATTER.match(text)
    if not m:
        return {}
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta


def score_agent(path: Path, root: Path) -> AgentScore:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    meta = parse_frontmatter(text)
    name = meta.get("name") or path.stem
    cat = meta.get("category") or path.parent.name
    body = FRONTMATTER.sub("", text, count=1)
    body_lines = [ln for ln in body.splitlines() if ln.strip()]
    fences = CODE_FENCE.findall(text)
    code_lines = sum(f.count("\n") for f in fences)
    lockin = len(CLAUDE_LOCKIN.findall(text))
    notes: list[str] = []

    # Structural 0-5
    s = 0.0
    if meta:
        s += 1.5
    if meta.get("name"):
        s += 1.0
    if meta.get("description") and len(meta["description"]) >= 20:
        s += 1.0
    elif meta.get("description"):
        s += 0.5
        notes.append("short description")
    if meta.get("tools") or meta.get("category"):
        s += 0.5
    if len(body_lines) >= 15:
        s += 1.0
    elif len(body_lines) >= 5:
        s += 0.5
        notes.append("thin body")
    else:
        notes.append("very thin body")
    structural = min(5.0, s)

    # Content density: prefer structured guidance over pure code dumps
    prose_lines = max(1, len(body_lines) - code_lines // 2)
    ratio = code_lines / max(1, len(lines))
    if ratio > 0.75 and len(lines) > 400:
        content_density = 2.0
        notes.append("heavy code dump (>75%)")
    elif ratio > 0.5 and len(lines) > 200:
        content_density = 3.0
        notes.append("code-heavy")
    elif len(body_lines) < 20:
        content_density = 2.5
        notes.append("checklist-thin")
    else:
        content_density = 4.5
    # bonus for clear sections
    if re.search(r"(?m)^##\s+", body):
        content_density = min(5.0, content_density + 0.5)

    # Portability to Grok (not Claude Task/MultiEdit dependent as exclusive)
    port = 4.0
    if lockin >= 8:
        port = 2.0
        notes.append("strong Claude lock-in")
    elif lockin >= 3:
        port = 3.0
        notes.append("some Claude-specific tooling")
    tools = (meta.get("tools") or "").lower()
    if "task" in tools and "read" not in tools:
        port = min(port, 2.5)
        notes.append("Task-only tools")
    # Language-specific pros still portable as advice
    if name.endswith("-pro") or name.endswith("-expert") or name.endswith("-specialist"):
        port = min(5.0, port + 0.3)

    # Uniqueness
    if name in EXISTING:
        uniqueness = 2.0
        notes.append(f"overlap: {EXISTING[name]}")
    elif any(k in name for k in ("healthcare", "fintech", "ecommerce", "game-", "embedded", "blockchain")):
        uniqueness = 4.0  # domain packs — niche for us
        notes.append("domain niche (catalog ref)")
    else:
        uniqueness = 4.0

    # Relevance to local coding agent stack
    if name in HIGH_SIGNAL:
        relevance = 5.0
    elif cat in ("quality", "infrastructure", "development", "core"):
        relevance = 4.0
    elif cat in ("data-ai", "business"):
        relevance = 3.5
    elif cat in ("specialized", "creative"):
        relevance = 3.0
    else:
        relevance = 3.0

    overall = round(
        0.25 * structural
        + 0.15 * content_density
        + 0.25 * port
        + 0.15 * uniqueness
        + 0.20 * relevance,
        2,
    )

    # Gate: structural >= 3, overall >= 3.2, not pure empty
    pass_gate = structural >= 3.0 and overall >= 3.2 and len(body_lines) >= 8

    # Port action
    if not pass_gate:
        action = "skip"
    elif name in HIGH_SIGNAL and uniqueness >= 3.5 and overall >= 3.8:
        action = "paths"
    elif name in HIGH_SIGNAL and overall >= 3.5:
        action = "paths" if name not in EXISTING else "docs_map"
    elif name in EXISTING:
        action = "docs_map"
    elif overall >= 3.8 and cat in ("quality", "infrastructure", "development", "data-ai"):
        action = "paths"
    elif overall >= 3.5:
        action = "docs_map"
    else:
        action = "skip"

    # Prefer not first_party for bulk Claude pack (ADR-0009)
    if action == "paths" and name in ("security-auditor", "e2e-test-specialist", "accessibility-auditor"):
        # still paths — thin first-party only if we rewrite; keep paths
        pass

    return AgentScore(
        path=str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
        name=name,
        category=cat,
        lines=len(lines),
        has_frontmatter=bool(meta),
        has_name=bool(meta.get("name")),
        has_description=bool(meta.get("description")),
        has_tools=bool(meta.get("tools")),
        description_len=len(meta.get("description") or ""),
        body_lines=len(body_lines),
        code_fence_count=len(fences),
        code_lines_est=code_lines,
        claude_lockin_hits=lockin,
        structural=structural,
        content_density=content_density,
        portability=port,
        uniqueness=uniqueness,
        relevance=relevance,
        overall=overall,
        pass_gate=pass_gate,
        notes=notes,
        port_action=action,
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--root",
        type=Path,
        default=Path("/tmp/claude-code-unified-agents/claude-code-unified-agents/.claude/agents"),
    )
    ap.add_argument("--out-md", type=Path, default=Path("pipelines/eval/unified-agents-eval.latest.md"))
    ap.add_argument("--out-json", type=Path, default=Path("pipelines/eval/unified-agents-eval.latest.json"))
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--min-pass-rate", type=float, default=0.55)
    args = ap.parse_args()

    root = args.root
    files = sorted(root.rglob("*.md"))
    scores = [score_agent(f, root) for f in files]
    passed = [s for s in scores if s.pass_gate]
    pass_rate = len(passed) / max(1, len(scores))
    by_action: dict[str, list[str]] = {}
    for s in scores:
        by_action.setdefault(s.port_action, []).append(s.name)

    overalls = [s.overall for s in scores]
    pack_pass = pass_rate >= args.min_pass_rate and statistics.mean(overalls) >= 3.3

    lines = [
        "# Unified Agents pack eval",
        "",
        f"date: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')}",
        f"source: https://github.com/stretchcloud/claude-code-unified-agents",
        f"x_post: https://x.com/i/status/2082997925014053075",
        f"agents_scored: {len(scores)}",
        f"pass_gate: {len(passed)}/{len(scores)} ({pass_rate:.0%})",
        f"mean_overall: {statistics.mean(overalls):.2f}",
        f"median_overall: {statistics.median(overalls):.2f}",
        f"pack_decision: {'PASS → integrate curated' if pack_pass else 'FAIL → catalog only'}",
        "",
        "## Port actions",
        "",
    ]
    for act, names in sorted(by_action.items()):
        lines.append(f"- **{act}** ({len(names)}): {', '.join(sorted(names))}")

    lines += [
        "",
        "## Top overall",
        "",
        "| name | cat | overall | struct | port | uniq | rel | dens | action | notes |",
        "|------|-----|--------:|-------:|-----:|-----:|----:|-----:|--------|-------|",
    ]
    for s in sorted(scores, key=lambda x: -x.overall)[:20]:
        notes = "; ".join(s.notes)[:60]
        lines.append(
            f"| {s.name} | {s.category} | {s.overall} | {s.structural} | {s.portability} | "
            f"{s.uniqueness} | {s.relevance} | {s.content_density} | {s.port_action} | {notes} |"
        )

    lines += [
        "",
        "## All agents",
        "",
        "| name | lines | overall | pass | action |",
        "|------|------:|--------:|:----:|--------|",
    ]
    for s in sorted(scores, key=lambda x: (x.category, x.name)):
        lines.append(
            f"| {s.name} | {s.lines} | {s.overall} | {'Y' if s.pass_gate else 'N'} | {s.port_action} |"
        )

    lines += [
        "",
        "## Integration recommendation",
        "",
        "1. **Do not** install full Claude Code agent tree as Grok primary (ADR-0002/0009).",
        "2. **Catalog** the pack at I1 (pin + eval receipt).",
        "3. **paths snapshot** curated agents that scored paths + pass_gate.",
        "4. **docs_map** overlaps onto existing first-party skills (gstack-style recipes).",
        "5. Skip domain mega-files as first-party (game/healthcare code dumps) unless product needs them.",
        "",
    ]

    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    payload = {
        "pack_pass": pack_pass,
        "pass_rate": pass_rate,
        "mean_overall": statistics.mean(overalls),
        "agents": [asdict(s) for s in scores],
        "by_action": by_action,
    }
    args.out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    print(f"pack_pass={pack_pass} pass_rate={pass_rate:.0%} mean={statistics.mean(overalls):.2f}")
    print("paths:", sorted(by_action.get("paths", [])))
    print("docs_map:", sorted(by_action.get("docs_map", [])))
    if args.strict and not pack_pass:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
