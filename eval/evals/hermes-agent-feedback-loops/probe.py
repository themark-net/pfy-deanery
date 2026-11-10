#!/usr/bin/env python3
"""Score the hermes-feedback pattern port. Does not install Hermes.

The catalog card is the three Entry 048 loops, already a first-party skill.
This probe reads that skill. It does not clone NousResearch/hermes-agent,
does not start a daemon, and does not write a stage card.

Exit 0: all three loops are in the skill, the install ban keeps both
markers on one line, the Reflect row names /hermes-feedback on that row,
PORT.md still omits the 90-day daemon, and the bootstrap copy matches the
.grok mirror.
Exit 1: the files are readable and a loop or a guard disagrees.
Exit 2: a required file is missing.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
METRIC = "ported_loops"
THRESHOLD = 3

SKILL_REL = "bootstrap/grok-cli/skills/hermes-feedback/SKILL.md"
PORT_REL = "bootstrap/grok-cli/skills/hermes-feedback/PORT.md"
MIRROR_SKILL_REL = ".grok/skills/hermes-feedback/SKILL.md"
MIRROR_PORT_REL = ".grok/skills/hermes-feedback/PORT.md"
MANIFEST_REL = "bootstrap/grok-cli/manifest.json"
STRUCTURAL_REL = "examples/eval-harness/run_structural.py"
AGENTS_REL = "AGENTS.md"

LOOPS = (
    {
        "id": "auto_memory",
        "needles": ("Loop 1", "Auto-memory", "Do not put in memory", "API keys"),
    },
    {
        "id": "auto_skill",
        "needles": ("Loop 2", "Auto-skill", "5 tool calls", "SKILL.md"),
    },
    {
        "id": "curator",
        "needles": ("Loop 3", "Curator", "no background daemon required", "Pin list"),
    },
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read(root: Path, rel: str) -> str | None:
    path = root / rel
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def _needles(text: str, needles: tuple[str, ...]) -> list[str]:
    return [needle for needle in needles if needle not in text]


def _same_line(text: str, needles: tuple[str, ...]) -> bool:
    for line in text.splitlines():
        if all(needle in line for needle in needles):
            return True
    return False


def _manifest_row(doc: object) -> dict | None:
    skills = []
    if isinstance(doc, dict):
        block = doc.get("first_party_skills")
        if isinstance(block, dict) and isinstance(block.get("skills"), list):
            skills = block["skills"]
    for row in skills:
        if isinstance(row, dict) and row.get("name") == "hermes-feedback":
            return row
    return None


def _structural_lists(text: str) -> bool:
    start = text.find("DESIGN_CODING_SKILLS = (")
    if start < 0:
        return False
    end = text.find(")", start)
    if end < 0:
        return False
    return '"hermes-feedback"' in text[start:end]


def measure(root: Path) -> tuple[dict, int]:
    required = (
        SKILL_REL,
        PORT_REL,
        MIRROR_SKILL_REL,
        MIRROR_PORT_REL,
        MANIFEST_REL,
        STRUCTURAL_REL,
        AGENTS_REL,
    )
    missing = [rel for rel in required if not (root / rel).is_file()]
    if missing:
        return {
            "metric": METRIC,
            "threshold": THRESHOLD,
            "ported_loops": 0,
            "consistent": False,
            "error": "missing",
            "missing": missing,
            "runs": 0,
            "installed": False,
        }, 2

    skill = _read(root, SKILL_REL) or ""
    port = _read(root, PORT_REL) or ""
    mirror_skill = _read(root, MIRROR_SKILL_REL) or ""
    mirror_port = _read(root, MIRROR_PORT_REL) or ""
    manifest_text = _read(root, MANIFEST_REL) or ""
    structural = _read(root, STRUCTURAL_REL) or ""
    agents = _read(root, AGENTS_REL) or ""

    try:
        manifest = json.loads(manifest_text)
    except json.JSONDecodeError as exc:
        return {
            "metric": METRIC,
            "threshold": THRESHOLD,
            "ported_loops": 0,
            "consistent": False,
            "error": f"manifest malformed: {exc.msg}",
            "runs": 0,
            "installed": False,
        }, 1

    loops = []
    present = 0
    for spec in LOOPS:
        absent = _needles(skill, spec["needles"])
        ok = not absent
        if ok:
            present += 1
        loops.append({"id": spec["id"], "ok": ok, "missing": absent})

    row = _manifest_row(manifest)
    origin = row.get("origin") if isinstance(row, dict) else ""
    if not isinstance(origin, str):
        origin = ""
    guards = {
        "install_forbidden": _same_line(skill, ("Install or require", "as runtime")),
        "daemon_omitted": "automatic 90-day daemon" in port,
        "no_hermes_binary": "no Hermes binary" in port,
        "manifest_not_runtime": row is not None and "not runtime" in origin,
        "structural_lists_skill": _structural_lists(structural),
        "reflect_routes_skill": _same_line(agents, ("| Reflect |", "/hermes-feedback")),
        "mirror_skill_match": skill == mirror_skill,
        "mirror_port_match": port == mirror_port,
    }
    ok = present == THRESHOLD and all(guards.values())
    result = {
        "metric": METRIC,
        "threshold": THRESHOLD,
        "ported_loops": present,
        "consistent": ok,
        "loops": loops,
        "guards": guards,
        "skill_sha256": _sha(skill),
        "port_sha256": _sha(port),
        "runs": 0,
        "installed": False,
        "daemon_started": False,
    }
    return result, 0 if ok else 1


def main() -> int:
    result, code = measure(ROOT)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
