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
card. A slug listed in eval/catalog-queue/exclusions.tsv is refused before
any ceiling check, including a stay at the current stage. The same legal
verdict applied twice leaves the card bytes unchanged the second time. Scan
never writes a card.

Ceiling rule (same I0-I4 scale as docs/ops/integration-stages.md):

Allowed stage is the lower of the evidence ceiling and tier_ceiling when the
card has one. tier_ceiling is a cap. It does not raise weaker evidence.

Evidence comes only from the card's evidence list:

- I4: submodule: or subtree:, and a valid main-run receipt
- I3: a valid main-run receipt (receipt:eval/integrate/<slug>/receipt.json
  on origin/main, run_kind pipeline or gate). make: and path: do not reach I3.
- I2: a measured probe (results.json, check-results.json, *-results.json,
  *-bench.json, receipt.json, receipt:, tools/_probe/, probe:) or an
  operator path (make:, path:)
- I1: any other listed artifact (notes, pin, entry, report, scan summary,
  VERDICT, summary, script)
- I0: evidence list empty

Receipt link: when a verdict proposes I3 or I4 and the card lists no valid
main-run receipt, apply checks the conventional eval/integrate/<slug>/receipt.json.
If that file is a valid main-run receipt on origin/main, the card's risk class
is none, and it has no GPU, over-25 GB, or release block (the same classifier
as scripts/catalog_auto_raise.py), apply adds
receipt:eval/integrate/<slug>/receipt.json to the evidence before the ceiling
check, and writes it with the stage. A refusal still writes nothing.
tier_ceiling still caps the result.

Security full gate (operator decision 2026-11-10): when the card's risk
class is security (scripts/catalog_auto_raise.py classify_risk), the allowed
stage is capped at I2 unless the card cites gate:eval/integrate/<slug>/GATE.json
and that file is a passing full gate: JSON with slug equal to the card file
stem, pinned_sha a 40-hex SHA that is an ancestor of origin/main, and both
tester and reviewer objects with verdict PASS and sha equal to pinned_sha.
Anything else is named (security-gate-missing, security-gate-malformed,
security-gate-not-pass, security-gate-sha-mismatch, or the receipt SHA
reasons). A security verdict proposing I2 or above is capped at I1 unless it
records "sandbox": "sandlock" (the I2 trial ran under
scripts/integrations/sandlock/wrap.py). Nothing here self-approves: the gate
file is written by the Tester and Reviewer, not by apply or a lane.

I3 and I4 also need that receipt when applying a stage. A missing file is
missing-main-receipt. Bad JSON or a run_kind other than pipeline or gate is
receipt-malformed. A main_sha that is not an ancestor of origin/main is
receipt-sha-not-on-main. When origin/main cannot be resolved, the reason is
git-unavailable. The card bytes stay as they are on every refusal. Scan flags
cards already at I3 or I4 that fail this rule and does not demote them.

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
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pfylib.stage_registry import VALID_STAGES, load_stages, slug_for  # noqa: E402
from scripts.catalog_eval_queue import QueueError, exclusion_reason  # noqa: E402

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

This scan does not change integration_stage. A flagged card stays where it is. The operator decides any demotion.

Allowed stage is the lower of the evidence ceiling and tier_ceiling when the card has one. tier_ceiling is a cap from the catalog tier and posture. It does not raise a card whose evidence is weaker.

Evidence ceiling, from the evidence list only:

- I4 when an item starts with `submodule:` or `subtree:` and a valid main-run receipt is an ancestor of `origin/main`.
- I3 when the card has a valid main-run receipt: an evidence item `receipt:eval/integrate/<slug>/receipt.json` whose file parses, whose `run_kind` is `pipeline` or `gate`, and whose `main_sha` is an ancestor of `origin/main`.
- `make:` and `path:` are operator paths. They support I2. They do not support I3 or I4.
- I2 when an item is a measured probe: `results.json`, `check-results.json`, a name ending in `-results.json` or `-bench.json`, `receipt.json`, a `receipt:` item, `tools/_probe/`, or `probe:`.
- I1 when the list has any other artifact (notes, pin, entry, report, scan summary, VERDICT, summary, script).
- I0 when the evidence list is empty.

A card already at I3 or I4 without a valid receipt is flagged with `missing-main-receipt`, `receipt-malformed`, `receipt-sha-not-on-main`, or `git-unavailable`. The scan does not demote it. Cards below I3 do not get those codes.

Apply adds two write caps the scan does not need. A failing modularity gate caps the write at I1. A failing value gate caps the write at I2. Both gates must pass before a write of I3 or I4.

A tool whose uses, features, or tags cover CI, testing, or review cannot sit above I2 unless self_pipeline passes the same check as scripts/catalog_check.py (applied with evidence, not_applicable with a reason, or pending with grace). That check does not promote a card. Notes, a scan summary, and a report stay I1 even when tier_ceiling is I3.

"""

_CATALOG_CHECK = None


class Refuse(Exception):
    """A named refusal. The card is not written."""


_AUTO_RAISE = None


def _auto_raise():
    global _AUTO_RAISE
    if _AUTO_RAISE is None:
        path = ROOT / "scripts" / "catalog_auto_raise.py"
        spec = importlib.util.spec_from_file_location("catalog_auto_raise_for_verdict", path)
        if spec is None or spec.loader is None:
            raise Refuse("malformed-verdict: cannot load scripts/catalog_auto_raise.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _AUTO_RAISE = mod
    return _AUTO_RAISE


def link_main_receipt(card: dict, repo: Path, slug: str) -> tuple[dict, str | None, str]:
    """Return (card, linked_rel, note).

    linked_rel is the receipt: item added to a copy of the card, or None when
    the card is unchanged. note names why nothing was linked.
    """
    if receipt_problem(card, repo, slug) is None:
        return card, None, "already-linked"
    rel = f"eval/integrate/{slug}/receipt.json"
    problem = _one_receipt(card, repo, rel, slug)
    if problem is not None:
        return card, None, problem
    raiser = _auto_raise()
    risk = raiser.classify_risk(card)
    if risk != "none":
        return card, None, f"risk-class {risk}"
    block = raiser.block_reason(card)
    if block:
        return card, None, f"blocked {block}"
    updated = dict(card)
    evidence = list(card.get("evidence") or []) if isinstance(card.get("evidence"), list) else []
    evidence.append(f"receipt:{rel}")
    updated["evidence"] = evidence
    return updated, f"receipt:{rel}", "linked"


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
        return 2, "make target"
    if low.startswith("path:"):
        return 2, "repo path"
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


_SHA = re.compile(r"^[0-9a-fA-F]{7,64}$")
_RUN_KINDS = frozenset({"pipeline", "gate"})


def _expected_slug(card: dict, fallback: str) -> str:
    slug = card.get("slug")
    if isinstance(slug, str) and slug.strip():
        return slug.strip()
    name = card.get("name")
    if isinstance(name, str) and name.strip():
        return slug_for(name)
    return fallback


def _has_embed(card: dict) -> bool:
    raw = card.get("evidence")
    if not isinstance(raw, list):
        return False
    for item in raw:
        if not isinstance(item, str):
            continue
        low = item.strip().lower()
        if low.startswith("submodule:") or low.startswith("subtree:"):
            return True
    return False


def _receipt_rels(card: dict) -> list[str]:
    raw = card.get("evidence")
    if not isinstance(raw, list):
        return []
    rels: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        text = item.strip()
        if text.lower().startswith("receipt:"):
            rels.append(text.split(":", 1)[1].strip())
    return rels


def _nonempty(data: dict, key: str) -> bool:
    value = data.get(key)
    return isinstance(value, str) and bool(value.strip())


def _sha_on_origin_main(repo: Path, sha: str) -> str | None:
    """None when sha is an ancestor of origin/main. Else a reason code."""
    try:
        probe = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--verify", "--quiet", "origin/main^{commit}"],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return "git-unavailable"
    if probe.returncode != 0:
        return "git-unavailable"
    try:
        anc = subprocess.run(
            ["git", "-C", str(repo), "merge-base", "--is-ancestor", sha, "origin/main"],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return "git-unavailable"
    if anc.returncode == 0:
        return None
    if anc.returncode == 1:
        return "receipt-sha-not-on-main"
    return "git-unavailable"


def _one_receipt(card: dict, repo: Path, rel: str, slug: str) -> str | None:
    """None when this receipt file is a valid main-run receipt."""
    rel = rel.replace("\\", "/").strip()
    if not rel or rel.startswith("/") or any(part == ".." for part in Path(rel).parts):
        return "receipt-malformed"
    path = (repo / rel).resolve()
    try:
        path.relative_to(repo.resolve())
    except ValueError:
        return "receipt-malformed"
    if not path.is_file():
        return "missing-main-receipt"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "receipt-malformed"
    if not isinstance(data, dict):
        return "receipt-malformed"
    if data.get("run_kind") not in _RUN_KINDS:
        return "receipt-malformed"
    for key in ("slug", "main_sha", "started", "finished", "outcome", "tool_version", "did"):
        if not _nonempty(data, key):
            return "receipt-malformed"
    if not (_nonempty(data, "run_id") or _nonempty(data, "log") or _nonempty(data, "log_path")):
        return "receipt-malformed"
    if slug and data["slug"] != slug:
        return "receipt-malformed"
    if _SHA.fullmatch(data["main_sha"]) is None:
        return "receipt-malformed"
    return _sha_on_origin_main(repo, data["main_sha"])


def _gate_rels(card: dict) -> list[str]:
    raw = card.get("evidence")
    if not isinstance(raw, list):
        return []
    return [item.split(":", 1)[1].strip() for item in raw if isinstance(item, str) and item.strip().lower().startswith("gate:")]


def gate_problem(card: dict, repo: Path, slug: str) -> str | None:
    """None when the card cites a passing full gate (Tester and Reviewer PASS at one pinned SHA)."""
    rels = _gate_rels(card)
    if not rels:
        return "security-gate-missing"
    first = "security-gate-missing"
    for index, rel in enumerate(rels):
        problem = _one_gate(repo, rel, slug)
        if problem is None:
            return None
        if index == 0:
            first = problem
    return first


def _one_gate(repo: Path, rel: str, slug: str) -> str | None:
    rel = rel.replace("\\", "/").strip()
    if not rel or rel.startswith("/") or any(part == ".." for part in Path(rel).parts):
        return "security-gate-malformed"
    path = repo / rel
    if not path.is_file():
        return "security-gate-missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return "security-gate-malformed"
    if not isinstance(data, dict) or (slug and data.get("slug") != slug):
        return "security-gate-malformed"
    pinned = data.get("pinned_sha")
    if not isinstance(pinned, str) or _SHA.fullmatch(pinned) is None:
        return "security-gate-malformed"
    for role in ("tester", "reviewer"):
        item = data.get(role)
        if not isinstance(item, dict):
            return "security-gate-malformed"
        if item.get("verdict") != "PASS":
            return "security-gate-not-pass"
        if item.get("sha") != pinned:
            return "security-gate-sha-mismatch"
    return _sha_on_origin_main(repo, pinned)


def _is_security(card: dict) -> bool:
    return _auto_raise().classify_risk(card) == "security"


def receipt_problem(card: dict, repo: Path, slug: str = "") -> str | None:
    """None when any receipt: evidence item is a valid main-run receipt.

    Otherwise the first named reason. No receipt: item is missing-main-receipt.
    """
    rels = _receipt_rels(card)
    if not rels:
        return "missing-main-receipt"
    first = "missing-main-receipt"
    for rel in rels:
        problem = _one_receipt(card, repo, rel, slug)
        if problem is None:
            return None
        if first == "missing-main-receipt":
            first = problem
    return first


def evidence_ceiling(card: dict, repo: Path | None = None, slug: str = "") -> tuple[str, str]:
    """Highest stage the evidence list supports, plus a short kind list.

    make: and path: stop at I2. A valid main-run receipt lifts the ceiling to
    I3, or to I4 when the list also has submodule: or subtree:.
    """
    raw = card.get("evidence")
    items = [item for item in raw if isinstance(item, str)] if isinstance(raw, list) else []
    best = 0
    embed = False
    kinds: list[str] = []
    for item in items:
        rank, kind = classify_item(item)
        if rank >= 4:
            embed = True
        if rank > best:
            best = rank
        if kind not in kinds and kind != "empty":
            kinds.append(kind)
    if not items:
        return "I0", "no evidence listed"
    valid = False
    if repo is not None and _receipt_rels(card):
        valid = receipt_problem(card, repo, slug) is None
    if valid:
        best = 4 if embed else max(best, 3)
        if "main-run receipt" not in kinds:
            kinds.append("main-run receipt")
    elif best > 2:
        best = 2
    return STAGES[best], ", ".join(kinds)


def _self_pipeline_cap(name: str, card: dict) -> str | None:
    """I2 when catalog_check would reject this card at I3. None when it would not."""
    probe = dict(card)
    probe["integration_stage"] = "I3"
    problems = _catalog_check().self_pipeline_problems(name, probe)
    if problems:
        return "I2"
    return None


def decide_ceiling(
    name: str,
    card: dict,
    verdict: dict | None = None,
    repo: Path | None = None,
) -> tuple[str, str, str | None, str]:
    """Return allowed stage, evidence stage, tier ceiling, and the reason.

    verdict gates apply only when a verdict is passed. The scan omits them.
    """
    root = repo if repo is not None else ROOT
    slug = _expected_slug(card, "")
    evidence_stage, kinds = evidence_ceiling(card, root, slug)
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
    stage = _stage(card.get("integration_stage"))
    if stage in ("I3", "I4"):
        problem = receipt_problem(card, root, slug)
        if problem:
            bits.append(problem)
            if RANK[allowed] >= RANK["I3"]:
                allowed = "I2"
    if RANK[allowed] >= RANK["I3"] and _is_security(card):
        problem = gate_problem(card, root, slug)
        if problem:
            allowed = "I2"
            bits.append(f"security tool: I3 needs the full gate ({problem})")
    if verdict is not None and _is_security(card) and verdict.get("sandbox") != "sandlock":
        if RANK["I1"] < RANK[allowed]:
            allowed = "I1"
            bits.append("security verdict without sandbox sandlock caps the write at I1")
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


def apply_stage(card_path: Path, target: str, repo_root: Path) -> str | None:
    """Write target onto the card, or return a named refusal.

    A refusal leaves the card bytes unchanged. None means the stage is target.
    I3 and I4 need a valid main-run receipt and a tier_ceiling at or above
    the target. I4 also needs a submodule: or subtree: evidence item.
    The self_pipeline cap still blocks a CI, testing, or review tool that
    would fail catalog_check at I3.
    """
    path = Path(card_path)
    repo = Path(repo_root)
    before = path.read_bytes()
    try:
        card = json.loads(before.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        return "receipt-malformed"
    if not isinstance(card, dict) or _stage(target) is None:
        return "missing-main-receipt"
    tier = _stage(card.get("tier_ceiling"))
    if tier is not None and RANK[tier] < RANK[target]:
        return "tier_ceiling"
    name = card.get("name") if isinstance(card.get("name"), str) and str(card.get("name")).strip() else path.stem
    cap = _self_pipeline_cap(str(name), card)
    if cap is not None and RANK[cap] < RANK[target]:
        return "self_pipeline"
    if RANK[target] >= RANK["I3"]:
        problem = receipt_problem(card, repo, _expected_slug(card, path.stem))
        if problem:
            return problem
    if target == "I4" and not _has_embed(card):
        return "missing-embed"
    if card.get("integration_stage") != target:
        updated = dict(card)
        updated["integration_stage"] = target
        _write_json(path, updated)
    return None


def apply_verdict(
    card_path: Path,
    verdict_path: Path,
    one_line_path: Path | None,
    repo: Path | None = None,
) -> int:
    root = repo if repo is not None else ROOT
    card = _read_object(card_path, "card")
    slug = card_path.stem
    try:
        if exclusion_reason(root, slug):
            raise Refuse(f"excluded: {slug}")
    except QueueError as exc:
        raise Refuse(f"exclusions: {exc}") from exc
    verdict = parse_verdict(verdict_path)
    name = card.get("name") if isinstance(card.get("name"), str) and card.get("name").strip() else card_path.stem
    proposed = verdict["proposed_stage"]
    linked: str | None = None
    if RANK[proposed] >= RANK["I3"]:
        card, linked, _note = link_main_receipt(card, root, slug)
    allowed, _evidence, _tier, reason = decide_ceiling(name, card, verdict, root)
    if RANK[proposed] > RANK[allowed]:
        raise Refuse(f"above-ceiling: proposed {proposed} is above allowed {allowed} ({reason})")
    if card.get("integration_stage") != proposed or linked is not None:
        updated = dict(card)
        updated["integration_stage"] = proposed
        _write_json(card_path, updated)
    if linked is not None:
        sys.stdout.write(f"linked {linked}\n")
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


def render_report(tools: dict, root: Path) -> str:
    mismatches = []
    for name in sorted(tools):
        card = tools[name]
        stage = _stage(card.get("integration_stage"))
        allowed, evidence_stage, tier, reason = decide_ceiling(name, card, None, root)
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
    text = render_report(tools, root)
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
                raise Refuse("scan-only: --scan does not take --card, --verdict, or --write-one-line")
            root = _abs(args.root) if args.root else ROOT
            report = _abs(args.report) if args.report else root / "eval" / "catalog-verdicts" / "CEILING-MISMATCHES.md"
            return scan(root, report)
        if not args.card:
            raise Refuse("missing-card: pass --card and --verdict, or pass --scan")
        if not args.verdict:
            raise Refuse("missing-verdict: pass --verdict")
        one_line = _abs(args.write_one_line) if args.write_one_line else None
        return apply_verdict(_abs(args.card), _abs(args.verdict), one_line)
    except Refuse as exc:
        sys.stderr.write(f"refused: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
