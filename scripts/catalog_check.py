#!/usr/bin/env python3
"""ADR-0015: tools.json is a slim machine subset of TOOLS.md.
ADR-0017: catalog <-> implementation link between tools.json and data/toolsets.json.
T-0005: every TOOLS.md row has a stage card under data/stages/<slug>.json.

Exit 0 if
  1. every JSON tool name appears in TOOLS.md (does not require row counts to match);
  2. data/toolsets.json is well-formed against data/harnesses.json (pfylib.registry.validate);
  3. every tools.json `implementation` object names an existing toolset whose
     `catalog_tool` is this row's name, with a stage in I0-I4;
  4. every toolset with a non-null `catalog_tool` has exactly that reverse link;
  5. no two sources/entries/NNN-*.md files share an NNN prefix
     (--entries-dir overrides only that scan; default is sources/entries);
  6. every I3 or I4 tool whose uses, features, or tags cover CI, testing, or
     review has self_pipeline applied (with evidence) or not_applicable (with
     a reason). pending is allowed only with grace true. See
     pipeline_role_hits and docs/ops/integration-stages.md.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pfylib import registry  # noqa: E402
from pfylib.stage_registry import VALID_STAGES, load_stages, validate_stage_files  # noqa: E402

STAGES = VALID_STAGES
CARD = ("uses", "features", "potential", "non_goals", "next_gate")
ROW_RE = re.compile(r"^\| \*\*([^*]+)\*\*([^|]*)\|", re.M)
ENTRY_NUM_RE = re.compile(r"^(\d{3})-.+\.md$")
TOKEN_RE = re.compile(r"[a-z0-9]+")
# Explicit role labels. A tag token, or a feature whose whole text is one
# token, wins over the prose scan. `eval` is a label only: the word inside a
# sentence is not enough (`#pipeline` and `#evaluation` are not role tags).
ROLE_TAGS = frozenset({
    "ci",
    "testing",
    "test",
    "tests",
    "review",
    "reviews",
    "reviewer",
    "qa",
    "tdd",
    "junit",
    "pytest",
    "lint",
    "linter",
    "eval",
})
# Prose fallback, whole words in uses and features. No bare `eval`.
ROLE_WORDS = frozenset({
    "ci",
    "testing",
    "test",
    "tests",
    "review",
    "reviews",
    "reviewer",
    "qa",
    "tdd",
    "junit",
    "pytest",
    "lint",
    "linter",
})
SELF_PIPELINE_STAGES = frozenset({"I3", "I4"})


def entry_number_collisions(entries_dir: Path | None = None) -> list[str]:
    """One problem per NNN shared by two or more sources/entries/NNN-*.md files."""
    if entries_dir is None:
        entries_dir = ROOT / "sources" / "entries"
    if not entries_dir.is_dir():
        return ["sources/entries directory missing: %s" % entries_dir]
    groups: dict[str, list[str]] = {}
    for path in sorted(entries_dir.iterdir()):
        if not path.is_file():
            continue
        match = ENTRY_NUM_RE.match(path.name)
        if not match:
            continue
        groups.setdefault(match.group(1), []).append(path.name)
    problems = []
    for number in sorted(groups):
        names = groups[number]
        if len(names) > 1:
            problems.append(
                "sources/entries number %s is used by more than one file: %s"
                % (number, ", ".join(names))
            )
    return problems


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


def _string_list(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _unique(items: list[str]) -> list[str]:
    out: list[str] = []
    for item in items:
        if item not in out:
            out.append(item)
    return out


def pipeline_role_hits(row: dict) -> list[str]:
    """Why a card covers CI, testing, or review.

    Prefer an explicit role tag on `tags` or `catalog_tags`. If none, a
    feature whose entire text is one role token counts (the catalog stored
    the role as a label). Otherwise whole words in uses and features.
    Empty means the self-pipeline rule does not apply.
    """
    if not isinstance(row, dict):
        return []
    tag_hits: list[str] = []
    for raw in _string_list(row.get("tags")) + _string_list(row.get("catalog_tags")):
        for token in _tokens(raw):
            if token in ROLE_TAGS:
                tag_hits.append(token)
    tag_hits = _unique(tag_hits)
    if tag_hits:
        return ["tag:%s" % token for token in tag_hits]
    feature_hits: list[str] = []
    for raw in _string_list(row.get("features")):
        tokens = _tokens(raw)
        if len(tokens) == 1 and tokens[0] in ROLE_TAGS:
            feature_hits.append(tokens[0])
    feature_hits = _unique(feature_hits)
    if feature_hits:
        return ["feature:%s" % token for token in feature_hits]
    words: list[str] = []
    blob = " ".join(_string_list(row.get("uses")) + _string_list(row.get("features")))
    for token in _tokens(blob):
        if token in ROLE_WORDS:
            words.append(token)
    return ["word:%s" % token for token in _unique(words)]


def _plain(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def self_pipeline_problems(name: str, row: dict) -> list[str]:
    """Problems for one stage card. Empty when the rule does not apply or the card passes.

    Fail closed at I3 and I4: missing field, applied without evidence,
    not_applicable without a reason, or pending without grace. pending with
    grace true is a listed exception and does not demote the card.
    """
    if not isinstance(row, dict) or not pipeline_role_hits(row):
        return []
    stage = row.get("integration_stage")
    if stage not in SELF_PIPELINE_STAGES:
        return []
    field = row.get("self_pipeline")
    if not isinstance(field, dict):
        return [
            "%s: %s tool covers CI, testing, or review but self_pipeline is missing "
            "(applied with evidence, or not_applicable with a reason)"
            % (name, stage)
        ]
    status = field.get("status")
    if status == "applied":
        if not _plain(field.get("evidence")):
            return [
                "%s: self_pipeline status applied needs evidence (a commit or a doc path)"
                % name
            ]
        return []
    if status == "not_applicable":
        if not _plain(field.get("reason")):
            return ["%s: self_pipeline status not_applicable needs a reason" % name]
        return []
    if status == "pending":
        if field.get("grace") is True:
            return []
        return [
            "%s: self_pipeline pending at %s needs grace true, or applied evidence, "
            "or a not_applicable reason"
            % (name, stage)
        ]
    return [
        "%s: self_pipeline status %r is not applied, not_applicable, or pending"
        % (name, status)
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Catalog subset check and duplicate entry-number guard.")
    ap.add_argument(
        "--entries-dir",
        default="",
        help="Directory of NNN-*.md files for the duplicate-number check. Default: sources/entries. Other checks still use this repo.",
    )
    args = ap.parse_args(argv)
    raw_entries = str(args.entries_dir or "").strip()
    entries_dir = Path(raw_entries).expanduser() if raw_entries else None

    tools = json.loads((ROOT / "data/tools.json").read_text())
    stage_problems = validate_stage_files(ROOT)
    problems: list[str] = entry_number_collisions(entries_dir)
    problems.extend(stage_problems)
    try:
        stages_doc = load_stages(ROOT)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        stages_doc = {"tools": {}}
        text = str(exc)
        if not any(text in item or item in text for item in stage_problems):
            problems.append("stage registry: %s" % text)
    stage_rows = stages_doc.get("tools") or {}
    md = (ROOT / "TOOLS.md").read_text(encoding="utf-8", errors="replace")
    catalog_names = tools_md_names(md, set(stage_rows))
    rows = tools.get("tools") or []

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
    for name in sorted(stage_rows):
        row = stage_rows[name]
        if isinstance(row, dict):
            problems.extend(self_pipeline_problems(name, row))

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
