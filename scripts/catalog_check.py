#!/usr/bin/env python3
"""ADR-0015: tools.json is a slim machine subset of TOOLS.md.
ADR-0017: catalog <-> implementation link between tools.json and data/toolsets.json.
T-0005: every TOOLS.md row has a stage card in data/tool_integration_stages.json.

Exit 0 if
  1. every JSON tool name appears in TOOLS.md (does not require row counts to match);
  2. data/toolsets.json is well-formed against data/harnesses.json (pfylib.registry.validate);
  3. every tools.json `implementation` object names an existing toolset whose
     `catalog_tool` is this row's name, with a stage in I0-I4;
  4. every toolset with a non-null `catalog_tool` has exactly that reverse link.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pfylib import registry  # noqa: E402

STAGES = ("I0", "I1", "I2", "I3", "I4")
CARD = ("uses", "features", "potential", "non_goals", "next_gate")
ROW_RE = re.compile(r"^\| \*\*([^*]+)\*\*([^|]*)\|", re.M)


def tools_md_names(md: str, stage_keys: set[str] | None = None) -> list[str]:
    """First-column catalog names. Prefer the full cell when that stage card exists."""
    out = []
    keys = stage_keys or set()
    for bold, rest in ROW_RE.findall(md):
        full = (bold + rest).replace("**", "").strip()
        short = bold.strip()
        name = full if full in keys or short not in keys else short
        if name and name not in out:
            out.append(name)
    return out


def card_open(row: dict) -> bool:
    return any(not row.get(k) for k in CARD)


def main() -> int:
    tools = json.loads((ROOT / "data/tools.json").read_text())
    stages_doc = json.loads((ROOT / "data/tool_integration_stages.json").read_text())
    stage_rows = stages_doc.get("tools") or {}
    md = (ROOT / "TOOLS.md").read_text(encoding="utf-8", errors="replace")
    catalog_names = tools_md_names(md, set(stage_rows))
    rows = tools.get("tools") or []
    problems: list[str] = []

    missing_stage = [n for n in catalog_names if n not in stage_rows]
    if missing_stage:
        problems.append("TOOLS.md rows with no stage card: %s" % missing_stage)
    bad_stage = [
        "%s=%s" % (n, (stage_rows.get(n) or {}).get("integration_stage"))
        for n in catalog_names
        if n in stage_rows and (stage_rows[n] or {}).get("integration_stage") not in STAGES
    ]
    if bad_stage:
        problems.append("stage card not I0-I4: %s" % bad_stage)
    open_cards = [n for n in catalog_names if n in stage_rows and card_open(stage_rows[n])]
    stage_only = sorted(set(stage_rows) - set(catalog_names))

    missing = [t["name"] for t in rows if t.get("name") and t["name"] not in md]
    if missing:
        problems.append("JSON tools missing from TOOLS.md: %s" % missing)

    problems += ["toolsets: %s" % p for p in registry.validate(root_dir=ROOT)]

    toolsets = {t.get("id"): t for t in registry.toolset_rows(ROOT)}
    linked: dict[str, str] = {}
    for t in rows:
        impl = t.get("implementation")
        if impl is None:
            continue
        name = t.get("name", "?")
        if not isinstance(impl, dict):
            problems.append("%s: implementation must be an object {toolset, stage}" % name)
            continue
        tid = impl.get("toolset")
        if tid not in toolsets:
            problems.append("%s: implementation.toolset %r not in data/toolsets.json" % (name, tid))
        elif toolsets[tid].get("catalog_tool") != name:
            problems.append(
                "%s: implementation.toolset %r has catalog_tool %r (must equal this row name)"
                % (name, tid, toolsets[tid].get("catalog_tool"))
            )
        else:
            linked[tid] = name
        if impl.get("stage") not in STAGES:
            problems.append("%s: implementation.stage %r not in %s" % (name, impl.get("stage"), list(STAGES)))

    for tid, t in toolsets.items():
        ct = t.get("catalog_tool")
        if ct is None:
            continue
        if ct not in md:
            problems.append("toolset %s: catalog_tool %r not found in TOOLS.md" % (tid, ct))
        if linked.get(tid) != ct:
            problems.append(
                "toolset %s: catalog_tool %r has no tools.json row with implementation.toolset == %r" % (tid, ct, tid)
            )

    if problems:
        print("FAIL catalog-check:")
        for p in problems:
            print("  - %s" % p)
        return 1
    n_linked = len(linked)
    n_null = sum(1 for t in toolsets.values() if t.get("catalog_tool") is None)
    print(
        "PASS catalog-check slim-subset ok n_json=%d (not a 1:1 dump of TOOLS.md) · toolsets=%d linked=%d catalog_tool=null:%d"
        " · tools_md=%d stage_cards=%d i1_cards_open=%d stage_only=%d"
        % (
            len(rows),
            len(toolsets),
            n_linked,
            n_null,
            len(catalog_names),
            len(catalog_names) - len(missing_stage),
            len(open_cards),
            len(stage_only),
        )
    )
    if stage_only:
        print("stage-only (not a TOOLS.md row): %s" % ", ".join(stage_only))
    return 0


if __name__ == "__main__":
    sys.exit(main())
