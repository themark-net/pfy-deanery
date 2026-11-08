#!/usr/bin/env python3
"""Apply a VERDICT.json to one stage card, or scan for stages above the ceiling.

The one-line VERDICT (no extension) is generated from the JSON. The JSON is
the canonical record: metric, threshold, value_gate, modularity_gate, and
proposed_stage.

  python3 scripts/catalog_apply_verdict.py --card CARD.json --verdict VERDICT.json
  python3 scripts/catalog_apply_verdict.py --card CARD.json --verdict VERDICT.json --write-one-line VERDICT
  python3 scripts/catalog_apply_verdict.py --scan
  python3 scripts/catalog_apply_verdict.py --scan --report eval/catalog-verdicts/CEILING-MISMATCHES.md

Apply writes integration_stage only when proposed_stage is within the allowed
ceiling. Otherwise it exits nonzero, names the reason, and does not write the
card. The same legal verdict applied twice leaves the card bytes unchanged the
second time. Scan never writes a card.

Ceiling rule (same I0-I4 scale as docs/ops/integration-stages.md):

Allowed stage is the lower of the evidence ceiling and tier_ceiling when the
card has one. tier_ceiling is a cap. It does not raise weaker evidence.

Evidence comes only from the card's evidence list:

- I4: submodule: or subtree:
- I3: make: or path: (operator path in this repo)
- I2: a measured probe (results.json, check-results.json, *-results.json,
  *-bench.json, receipt.json, receipt:, tools/_probe/, probe:)
- I1: any other listed artifact (notes, pin, entry, report, scan summary,
  VERDICT, summary, script)
- I0: evidence list empty

On apply, a failing modularity gate caps the write at I1. A failing value
gate caps the write at I2. I3 and I4 need both gates to pass. A CI, testing,
or review tool cannot go above I2 unless self_pipeline passes the same check
as scripts/catalog_check.py. That check does not promote a card.

Intent on a new verdict must be in the enum or an alias. Stored card intents
are left as they are, including one-off strings.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pfylib.stage_registry import VALID_STAGES, load_stages  # noqa: E402

STAGES = VALID_STAGES
RANK = {stage: index for index, stage in enumerate(STAGES)}

INTENT_ENUM = (
    "awareness",
    "catalog_default",
    "staged_evaluation",
    "ad_hoc_probe",
    "onboard",
    "embedded",
)
INTENT_ALIASES = {
    "staged_eval": "staged_evaluation",
    "adhoc_probe": "ad_hoc_probe",
    "ad-hoc-probe": "ad_hoc_probe",
    "ad-hoc_probe": "ad_hoc_probe",
}

REPORT_INTRO = """# Ceiling mismatches

This scan does not change integration_stage. A flagged card stays where it is. Mark decides any demotion.

Allowed stage is the lower of the evidence ceiling and tier_ceiling when the card has one. tier_ceiling is a cap from the catalog tier and posture. It does not raise a card whose evidence is weaker.

Evidence ceiling, from the evidence list only:

- I4 when an item starts with `submodule:` or `subtree:`.
- I3 when an item starts with `make:` or `path:` (an operator path in this repo).
- I2 when an item is a measured probe: `results.json`, `check-results.json`, a name ending in `-results.json` or `-bench.json`, `receipt.json`, a `receipt:` item, `tools/_probe/`, or `probe:`.
- I1 when the list has any other artifact (notes, pin, entry, report, scan summary, VERDICT, summary, script).
- I0 when the evidence list is empty.

Apply adds two write caps the scan does not need. A failing modularity gate caps the write at I1. A failing value gate caps the write at I2. Both gates must pass before a write of I3 or I4.

A tool whose uses, features, or tags cover CI, testing, or review cannot sit above I2 unless self_pipeline passes the same check as scripts/catalog_check.py (applied with evidence, not_applicable with a reason, or pending with grace). That check does not promote a card. Notes, a scan summary, and a report stay I1 even when tier_ceiling is I3.

"""

_CATALOG_CHECK = None


class Refuse(Exception):
    """A named refusal. The card is not written."""


def _catalog_check():
    global _CATALOG_CHECK
    if _CATALOG_CHECK is None:
        path = ROOT / "scripts" / "catalog_check.py"
        spec = importlib.util.spec_from_file_location("catalog_check_for_verdict", path)
        if spec is None or spec.loader is None:
            raise Refuse("malformed-verdict: cannot load scripts/catalog_check.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _CATALOG_CHECK = mod
    return _CATALOG_CHECK


def canonical_intent(value: object) -> str | None:
    """Return the enum value for a new write, or None when it is not allowed."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text in INTENT_ENUM:
        return text
    return INTENT_ALIASES.get(text)


def _stage(value: object) -> str | None:
    if isinstance(value, str) and value in RANK:
        return value
    return None


def _min_stage(left: str, right: str) -> str:
    if RANK[right] < RANK[left]:
        return right
    return left


def classify_item(item: str) -> tuple[int, str]:
    """Rank and a short kind label for one evidence string. Rank 0 is unused."""
    low = item.strip().lower().replace("\\", "/")
    if not low:
        return 0, "empty"
    name = low.rsplit("/", 1)[-1]
    if low.startswith("submodule:") or low.startswith("subtree:"):
        return 4, "embed"
    if low.startswith("make:"):
        return 3, "make target"
    if low.startswith("path:"):
        return 3, "repo path"
    if low.startswith("probe:") or "tools/_probe/" in low:
        return 2, "probe artifact"
    if (
        name in {"results.json", "check-results.json", "receipt.json"}
        or name.endswith("-results.json")
        or name.endswith("-bench.json")
        or low.startswith("receipt:")
    ):
        return 2, "probe artifact"
    if "scan-summary" in name or "scan_summary" in name:
        return 1, "scan summary"
    if name.startswith("report"):
        return 1, "report"
    if name in {"verdict", "verdict.json"}:
        return 1, "VERDICT"
    if name.startswith("notes") or low.startswith("notes_doc:"):
        return 1, "notes"
    if low.startswith("pin:") or low.startswith("pin ") or name == "pin":
        return 1, "pin"
    if low.startswith("entry:"):
        return 1, "entry"
    if low.startswith("scripts/") or name.endswith(".py"):
        return 1, "script"
    if name in {"summary.json", "summary.md"}:
        return 1, "summary"
    if low.startswith((
        "scored:",
        "shadow:",
        "release:",
        "version:",
        "npm:",
        "tarball_sha256:",
        "binary_sha256:",
    )):
        return 1, "record"
    return 1, "other"


def evidence_ceiling(card: dict) -> tuple[str, str]:
    """Highest stage the evidence list supports, plus a short kind list."""
    raw = card.get("evidence")
    items = [item for item in raw if isinstance(item, str)] if isinstance(raw, list) else []
    best = 0
    kinds: list[str] = []
    for item in items:
        rank, kind = classify_item(item)
        if rank > best:
            best = rank
        if kind not in kinds and kind != "empty":
            kinds.append(kind)
    if not items:
        return "I0", "no evidence listed"
    return STAGES[best], ", ".join(kinds)


def _self_pipeline_cap(name: str, card: dict) -> str | None:
    """I2 when catalog_check would reject this card at I3. None when it would not."""
    probe = dict(card)
    probe["integration_stage"] = "I3"
    problems = _catalog_check().self_pipeline_problems(name, probe)
    if problems:
        return "I2"
    return None


def decide_ceiling(name: str, card: dict, verdict: dict | None = None) -> tuple[str, str, str | None, str]:
    """Return allowed stage, evidence stage, tier ceiling, and the reason.

    verdict gates apply only when a verdict is passed. The scan omits them.
    """
    evidence_stage, kinds = evidence_ceiling(card)
    allowed = evidence_stage
    bits = [f"evidence {evidence_stage}: {kinds}"]
    tier = _stage(card.get("tier_ceiling"))
    if tier is not None:
        if RANK[tier] < RANK[allowed]:
            allowed = tier
            bits.append(f"tier_ceiling {tier} caps the evidence")
        elif RANK[tier] > RANK[allowed]:
            bits.append(f"tier_ceiling {tier} does not raise it")
        else:
            bits.append(f"tier_ceiling {tier} agrees")
    cap = _self_pipeline_cap(name, card)
    if cap is not None and RANK[cap] < RANK[allowed]:
        allowed = cap
        bits.append("self_pipeline blocks I3 for a CI, testing, or review tool")
    if (
        isinstance(card.get("self_pipeline"), dict)
        and RANK[evidence_stage] < 3
        and RANK[allowed] == RANK[evidence_stage]
    ):
        bits.append("a self_pipeline record does not raise this evidence")
    if verdict is not None:
        if verdict["modularity_gate"] != "pass":
            if RANK["I1"] < RANK[allowed]:
                allowed = "I1"
                bits.append("modularity_gate fail caps the write at I1")
        elif verdict["value_gate"] != "pass":
            if RANK["I2"] < RANK[allowed]:
                allowed = "I2"
                bits.append("value_gate fail caps the write at I2")
    return allowed, evidence_stage, tier, "; ".join(bits)


def _threshold_text(value: int | float) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def movement(old: object, new: str) -> str:
    old_stage = _stage(old)
    if old_stage is None or RANK[new] > RANK[old_stage]:
        return "PROMOTE"
    if RANK[new] < RANK[old_stage]:
        return "DEMOTE"
    return "STAY"


def render_one_line(action: str, stage: str, verdict: dict) -> str:
    return (
        f"{action} {stage} {verdict['metric']} "
        f"threshold={_threshold_text(verdict['threshold'])} "
        f"value_gate={verdict['value_gate']} "
        f"modularity_gate={verdict['modularity_gate']}\n"
    )


def _read_object(path: Path, kind: str) -> dict:
    if not path.is_file():
        raise Refuse(f"missing-{kind}: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Refuse(f"malformed-{kind}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise Refuse(f"malformed-{kind}: top level is not an object")
    return data


def parse_verdict(path: Path) -> dict:
    data = _read_object(path, "verdict")
    metric = data.get("metric")
    if not isinstance(metric, str) or not metric.strip() or any(ch in metric for ch in "\r\n"):
        raise Refuse("malformed-verdict: metric must be a single-line string")
    threshold = data.get("threshold")
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise Refuse("malformed-verdict: threshold must be a number")
    for gate in ("value_gate", "modularity_gate"):
        if data.get(gate) not in ("pass", "fail"):
            raise Refuse(f"malformed-verdict: {gate} must be pass or fail")
    if _stage(data.get("proposed_stage")) is None:
        raise Refuse("malformed-verdict: proposed_stage must be I0, I1, I2, I3, or I4")
    if "intent" in data and canonical_intent(data.get("intent")) is None:
        shown = data.get("intent")
        raise Refuse(f"bad-intent: {shown!r} is not an allowed intent")
    return data


def _write_json(path: Path, obj: dict) -> None:
    text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def apply_verdict(card_path: Path, verdict_path: Path, one_line_path: Path | None) -> int:
    card = _read_object(card_path, "card")
    verdict = parse_verdict(verdict_path)
    name = card.get("name") if isinstance(card.get("name"), str) and card.get("name").strip() else card_path.stem
    proposed = verdict["proposed_stage"]
    allowed, _evidence, _tier, reason = decide_ceiling(name, card, verdict)
    if RANK[proposed] > RANK[allowed]:
        raise Refuse(f"above-ceiling: proposed {proposed} is above allowed {allowed} ({reason})")
    if card.get("integration_stage") != proposed:
        updated = dict(card)
        updated["integration_stage"] = proposed
        _write_json(card_path, updated)
    action = movement(card.get("integration_stage"), proposed)
    line = render_one_line(action, proposed, verdict)
    if one_line_path is not None:
        _write_text(one_line_path, line)
    sys.stdout.write(line)
    return 0


def _intent_notes(tools: dict) -> list[tuple[str, str]]:
    notes = []
    for name in sorted(tools):
        intent = tools[name].get("intent")
        if isinstance(intent, str) and intent.strip() and canonical_intent(intent) is None:
            notes.append((name, intent.strip()))
    return notes


def render_report(tools: dict) -> str:
    mismatches = []
    for name in sorted(tools):
        card = tools[name]
        stage = _stage(card.get("integration_stage"))
        allowed, evidence_stage, tier, reason = decide_ceiling(name, card, None)
        if stage is None:
            mismatches.append((name, str(card.get("integration_stage")), evidence_stage, tier, allowed, reason))
            continue
        if RANK[stage] > RANK[allowed]:
            mismatches.append((name, stage, evidence_stage, tier, allowed, reason))
    lines = [REPORT_INTRO.rstrip(), "", f"Scanned {len(tools)} cards. Mismatches {len(mismatches)}.", ""]
    lines.append("| Tool | Stage | Evidence ceiling | Tier ceiling | Allowed | Why |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    if not mismatches:
        lines.append("| (none) | - | - | - | - | - |")
    for name, stage, evidence_stage, tier, allowed, reason in mismatches:
        why = reason.replace("|", "/")
        lines.append(
            f"| {name} | {stage} | {evidence_stage} | {tier or '-'} | {allowed} | {why} |"
        )
    lines.append("")
    lines.append("## Intent values outside the enum")
    lines.append("")
    lines.append(
        "Existing card intent strings are left in place. "
        "New verdict writes must use the enum or an alias."
    )
    lines.append(
        "Enum: " + ", ".join(f"`{item}`" for item in INTENT_ENUM) + "."
    )
    alias_bits = [f"`{src}` -> `{dst}`" for src, dst in INTENT_ALIASES.items()]
    lines.append("Aliases: " + ", ".join(alias_bits) + ".")
    lines.append("")
    notes = _intent_notes(tools)
    lines.append("| Tool | Intent |")
    lines.append("| --- | --- |")
    if not notes:
        lines.append("| (none) | - |")
    for name, intent in notes:
        lines.append(f"| {name} | `{intent}` |")
    lines.append("")
    return "\n".join(lines)


def scan(root: Path, report_path: Path) -> int:
    try:
        doc = load_stages(root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise Refuse(f"malformed-card: {exc}") from exc
    tools = doc.get("tools") or {}
    text = render_report(tools)
    _write_text(report_path, text)
    sys.stdout.write(text)
    return 0


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _abs(text: str) -> Path:
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply a catalog VERDICT.json or scan ceiling mismatches.")
    parser.add_argument("--card", help="Stage card JSON. Written only when the proposed stage is legal.")
    parser.add_argument("--verdict", help="VERDICT.json (metric, threshold, gates, proposed_stage).")
    parser.add_argument("--write-one-line", metavar="PATH", help="Write the generated one-line VERDICT here.")
    parser.add_argument("--scan", action="store_true", help="Report cards above the evidence ceiling. Does not write cards.")
    parser.add_argument("--root", default="", help="Repo root for --scan. Default: this repo.")
    parser.add_argument("--report", default="", help="Mismatch report path. Default: eval/catalog-verdicts/CEILING-MISMATCHES.md under --root.")
    args = parser.parse_args(argv)
    try:
        if args.scan:
            if args.card or args.verdict or args.write_one_line:
                raise Refuse("malformed-verdict: --scan does not take --card, --verdict, or --write-one-line")
            root = _abs(args.root) if args.root else ROOT
            report = _abs(args.report) if args.report else root / "eval" / "catalog-verdicts" / "CEILING-MISMATCHES.md"
            return scan(root, report)
        if not args.card or not args.verdict:
            raise Refuse("missing-card: pass --card and --verdict, or pass --scan")
        one_line = _abs(args.write_one_line) if args.write_one_line else None
        return apply_verdict(_abs(args.card), _abs(args.verdict), one_line)
    except Refuse as exc:
        sys.stderr.write(f"refused: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
