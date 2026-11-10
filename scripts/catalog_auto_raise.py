#!/usr/bin/env python3
"""Raise tier_ceiling when the promotion rules pass (data/promotion-rules.json).

Rule-based promotion (operator decision 2026-11-10, 7:04am PT)
    Nobody signs off. A card's ceiling is raised when every rule in the
    rules file's "ceiling" table passes for its track (default or security).
    Default track: I3 when not excluded, no hard stop, classifiable, and the
    latest verdict passes both gates. Security track (a scanner or guard):
    I2 for the sandlock trial, then I3 when the trial is clean, its profile
    is read-only, and the card is wired advisory, non-blocking, or deny-only
    with a fail-open test. Each raise and each refusal writes the rule IDs
    that passed and failed to the card's promotion_history (kind ceiling).
    A refusal with no verdict yet and no hard stop is not written.

Hard stops (the only rules that write a needs-mark row)
    HS-live-money, HS-release-deploy, HS-secrets, HS-runtime-takeover,
    HS-gpu-unapproved, HS-pull-over-25gb-unapproved. GPU and over-25 GB
    blocks are cleared per slug by eval/catalog-queue/approvals.tsv in the
    private ops checkout (scripts/ops_paths.py). --launch-check prints
    skip <slug> gpu-driver for a card with an approved block, because the
    loop must not start GPU lanes in parallel: scripts/gpu_lane_driver.sh
    runs them one at a time.

--launch-check prints launch or skip with the failed rule ID. A security
card below I2 with a ceiling of I2 or more launches with reason
security-sandbox: the loop starts the eval lane with PFY_LANE_SANDBOX=sandlock.

Writes only tier_ceiling and ceiling_history. Never lowers a ceiling.
Never edits a card whose ceiling is already I3 or I4. --dry-run writes nothing.

Risk class
    The card field risk_class wins when it is security, live-money,
    runtime-takeover, or none. Otherwise a keyword classifier reads tags,
    catalog_tags, uses, features, and next_gate. Two classes at once, an
    invalid risk_class, or no classifiable text yields unknown. unknown
    fails safe and is not raised.

Word lists (whole tokens, hyphenated compounds kept)
    security: security, secret, secrets, credential, credentials, password,
    pentest, penetration, exploit, vulnerability, sast
    secrets handling (hard stop): keyring, vault, password-manager,
    secrets-manager, secret-store, credential-store, credential-helper
    live-money: trading, broker, payment, payments, wallet, invoice, bank,
    funds, stripe, live-money
    runtime-takeover: runtime-takeover, takeover, privilege, sudo, rootkit,
    host-control
    gpu: gpu, vulkan, rocm, hip, cuda, weights
    launch block (also never raised): release, deploy, deployment
    A size strictly over 25 GB or 25 GiB in that text is pull-over-25gb.

Latest verdict
    eval/**/<slug>/VERDICT.json, last path in sorted order. Both gates must
    pass. The date defaults to America/Los_Angeles today, or --date, or
    PFY_LOOP_TODAY.

Exclusions
    A slug listed in eval/catalog-queue/exclusions.tsv is refused. The card
    is not written. atomic-task-graph-atg stays on that list. Passing gates
    do not raise it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.catalog_eval_queue import QueueError, exclusion_reason  # noqa: E402

STAGES = ("I0", "I1", "I2", "I3", "I4")
RANK = {stage: index for index, stage in enumerate(STAGES)}
RISK_ENUM = ("security", "live-money", "runtime-takeover", "secrets", "none")
TOKEN_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
SIZE_RE = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*(gb|gib)\b", re.IGNORECASE)

SECURITY_TOKENS = frozenset({
    "security", "secret", "secrets", "credential", "credentials", "password",
    "pentest", "penetration", "exploit", "vulnerability", "sast",
})
SECRETS_TOKENS = frozenset({
    "keyring", "vault", "password-manager", "secrets-manager", "secret-store",
    "secrets-store", "credential-store", "credential-helper", "secrets-handling",
})
LIVE_MONEY_TOKENS = frozenset({
    "trading", "broker", "payment", "payments", "wallet", "invoice", "bank",
    "funds", "stripe", "live-money",
})
RUNTIME_TOKENS = frozenset({
    "runtime-takeover", "takeover", "privilege", "sudo", "rootkit", "host-control",
})
GPU_TOKENS = frozenset({"gpu", "vulkan", "rocm", "hip", "cuda", "weights"})
RELEASE_TOKENS = frozenset({"release", "deploy", "deployment"})
TEXT_FIELDS = ("uses", "features", "tags", "catalog_tags", "next_gate")


class RaiseError(Exception):
    """A named failure. No card is written after the failing card."""


def pt_today() -> str:
    override = os.environ.get("PFY_LOOP_TODAY", "").strip()
    if override:
        return override
    return datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat()


def tokens_of(card: dict) -> set[str]:
    found: set[str] = set()
    for key in TEXT_FIELDS:
        value = card.get(key)
        blobs: list[str] = []
        if isinstance(value, str):
            blobs.append(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    blobs.append(item)
        for blob in blobs:
            found.update(TOKEN_RE.findall(blob.lower()))
    return found


def text_of(card: dict) -> str:
    parts: list[str] = []
    for key in TEXT_FIELDS:
        value = card.get(key)
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(item for item in value if isinstance(item, str))
    return "\n".join(parts)


def size_over_25(card: dict) -> bool:
    for match in SIZE_RE.finditer(text_of(card)):
        try:
            number = float(match.group(1))
        except ValueError:
            continue
        if number > 25:
            return True
    return False


def classify_risk(card: dict) -> str:
    """Return security, live-money, runtime-takeover, none, or unknown."""
    raw = card.get("risk_class")
    if isinstance(raw, str) and raw.strip():
        key = raw.strip().lower()
        if key in RISK_ENUM:
            return key
        return "unknown"
    if raw not in (None, ""):
        return "unknown"
    tokens = tokens_of(card)
    if not tokens:
        return "unknown"
    hits: list[str] = []
    if tokens & SECURITY_TOKENS:
        hits.append("security")
    if tokens & LIVE_MONEY_TOKENS:
        hits.append("live-money")
    if tokens & RUNTIME_TOKENS:
        hits.append("runtime-takeover")
    if tokens & SECRETS_TOKENS:
        hits.append("secrets")
    if len(hits) > 1:
        return "unknown"
    if len(hits) == 1:
        return hits[0]
    return "none"


def has_gpu(tokens: set[str]) -> bool:
    """gpu, vulkan, rocm, hip, and cuda match inside a hyphenated tag. weights matches whole."""
    if "weights" in tokens:
        return True
    parts: set[str] = set()
    for token in tokens:
        parts.update(token.split("-"))
    return bool(parts & {"gpu", "vulkan", "rocm", "hip", "cuda"})


APPROVABLE = ("gpu", "pull-over-25gb")
APPROVALS_REL = "eval/catalog-queue/approvals.tsv"
APPROVALS_HEADER = "slug\tblock\tdecided\tnote"


def load_approvals(root: Path) -> dict[str, frozenset[str]]:
    """slug -> approved blocks. A missing file is no approvals. Bad rows raise RaiseError."""
    from scripts.ops_paths import ops_path

    path = ops_path(APPROVALS_REL, Path(root))
    if not path.is_file():
        return {}
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].rstrip("\r") != APPROVALS_HEADER:
        raise RaiseError(f"{APPROVALS_REL}: header must be {APPROVALS_HEADER!r}")
    found: dict[str, set[str]] = {}
    for lineno, raw in enumerate(lines[1:], start=2):
        if not raw.strip():
            continue
        parts = raw.rstrip("\r").split("\t")
        if len(parts) != 4 or not all(part.strip() for part in parts):
            raise RaiseError(f"{APPROVALS_REL}:{lineno}: need slug, block, decided, note")
        slug, block, decided = parts[0].strip(), parts[1].strip(), parts[2].strip()
        if block not in APPROVABLE:
            raise RaiseError(f"{APPROVALS_REL}:{lineno}: block must be gpu or pull-over-25gb")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", decided):
            raise RaiseError(f"{APPROVALS_REL}:{lineno}: decided must be YYYY-MM-DD")
        found.setdefault(slug, set()).add(block)
    return {slug: frozenset(blocks) for slug, blocks in found.items()}


def card_blocks(card: dict) -> list[str]:
    """Every launch block on the card, in check order."""
    tokens = tokens_of(card)
    blocks: list[str] = []
    if size_over_25(card):
        blocks.append("pull-over-25gb")
    if has_gpu(tokens):
        blocks.append("gpu")
    if tokens & RELEASE_TOKENS or any(part in RELEASE_TOKENS for token in tokens for part in token.split("-")):
        blocks.append("release-deploy")
    return blocks


def block_reason(card: dict, approved: frozenset[str] = frozenset()) -> str:
    """gpu, pull-over-25gb, release-deploy, or empty when the card may launch.

    approved names operator-approved blocks (gpu, pull-over-25gb) to ignore.
    """
    for block in card_blocks(card):
        if block not in approved:
            return block
    return ""


def needs_gpu_driver(card: dict, approved: frozenset[str]) -> bool:
    """True when an approved block is what kept this card from launching."""
    return any(block in approved for block in card_blocks(card))


HARD_CLASSES = {
    "live-money": "HS-live-money",
    "runtime-takeover": "HS-runtime-takeover",
    "secrets": "HS-secrets",
}


def risk_track(card: dict) -> str:
    """security, none, or unknown. Hard-stop classes are separate (hard_stops)."""
    raw = card.get("risk_class")
    if isinstance(raw, str) and raw.strip():
        key = raw.strip().lower()
        if key not in RISK_ENUM:
            return "unknown"
        return "security" if key == "security" else "none"
    if raw not in (None, ""):
        return "unknown"
    tokens = tokens_of(card)
    if not tokens:
        return "unknown"
    return "security" if tokens & SECURITY_TOKENS else "none"


def hard_stops(card: dict, approved: frozenset[str] = frozenset()) -> list[tuple[str, str]]:
    """(rule ID, detail) for every hard stop on the card. Empty when none."""
    found: list[tuple[str, str]] = []
    raw = card.get("risk_class")
    key = raw.strip().lower() if isinstance(raw, str) else ""
    tokens = tokens_of(card)
    if key in RISK_ENUM:
        if key in HARD_CLASSES:
            found.append((HARD_CLASSES[key], f"risk_class {key}"))
    else:
        for name, words in (("live-money", LIVE_MONEY_TOKENS), ("runtime-takeover", RUNTIME_TOKENS), ("secrets", SECRETS_TOKENS)):
            hit = sorted(tokens & words)
            if hit:
                found.append((HARD_CLASSES[name], f"card text names {', '.join(hit)}"))
    for block in card_blocks(card):
        if block == "release-deploy":
            found.append(("HS-release-deploy", "card text names a release or deploy"))
        elif block == "gpu" and block not in approved:
            found.append(("HS-gpu-unapproved", "card text names a GPU run; no gpu row in approvals.tsv"))
        elif block == "pull-over-25gb" and block not in approved:
            found.append(("HS-pull-over-25gb-unapproved", "card text is over 25 GB; no pull-over-25gb row in approvals.tsv"))
    order = ["HS-live-money", "HS-release-deploy", "HS-secrets", "HS-runtime-takeover", "HS-gpu-unapproved", "HS-pull-over-25gb-unapproved"]
    found.sort(key=lambda item: order.index(item[0]))
    return found


def latest_verdict(root: Path, slug: str) -> tuple[Path | None, dict | None]:
    """Last sorted eval/<dir>/<slug>/VERDICT.json. Missing file yields (None, None)."""
    base = root / "eval"
    if not base.is_dir():
        return None, None
    found = sorted(path for path in base.glob(f"**/{slug}/VERDICT.json") if path.is_file())
    if not found:
        return None, None
    path = found[-1]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return path, None
    if not isinstance(data, dict):
        return path, None
    return path, data


def gates_pass(verdict: dict | None) -> bool:
    if not isinstance(verdict, dict):
        return False
    return verdict.get("value_gate") == "pass" and verdict.get("modularity_gate") == "pass"


def _ceiling(card: dict) -> str | None:
    value = card.get("tier_ceiling")
    if isinstance(value, str) and value.strip() in RANK:
        return value.strip()
    return None


def _rules():
    from scripts import promotion_rules
    return promotion_rules


def plan(card: dict, verdict: dict | None, approved: frozenset[str] = frozenset(),
         root: Path | None = None, slug: str = "") -> dict:
    """Decide a ceiling raise by the rules. Keys: action, reason, target, results, hard."""
    pr = _rules()
    rules = pr.load_rules(root)
    current = _ceiling(card)
    if current is not None and RANK[current] > RANK["I3"]:
        return {"action": "skip", "reason": "ceiling above I3", "target": current, "results": [], "hard": False}
    if current == "I3":
        return {"action": "skip", "reason": "ceiling already I3", "target": current, "results": [], "hard": False}
    ctx = pr.Ctx(card=card, slug=slug or str(card.get("slug") or ""), root=Path(root) if root else ROOT,
                 name=str(card.get("name") or slug), verdict=verdict, approved=approved, mode="ceiling")
    allowed, passed, failing = pr.stage_allowed(rules, ctx, kind="ceiling", top="I3")
    if allowed != "I0" and (current is None or RANK[allowed] > RANK[current]):
        ids = ", ".join(rid for rid, _ok, _d in passed)
        return {"action": "raise", "reason": f"rules passed for {allowed}: {ids}", "target": allowed,
                "results": passed, "hard": False}
    failed = [(rid, detail) for rid, ok, detail in failing if not ok]
    if not failed:
        return {"action": "skip", "reason": f"ceiling {current} already meets the rules", "target": current or "",
                "results": [], "hard": False}
    hard = [item for item in failed if pr.is_hard_stop(rules, item[0])]
    excluded = [item for item in failed if item[0] == "R-not-excluded"]
    rid, detail = (hard or excluded or failed)[0]
    action = "refuse" if hard or any(rid == "R-not-excluded" for rid, _d in failed) else "skip"
    steps = rules["ceiling"][pr.track_of(card)]
    next_stage = next((st for st in sorted(steps, key=RANK.get) if RANK[st] > RANK[allowed]), "I3")
    return {"action": action, "reason": f"{rid}: {detail}", "target": next_stage, "results": failing, "hard": bool(hard)}


def plan_card(card: dict, verdict: dict | None, approved: frozenset[str] = frozenset(),
              root: Path | None = None, slug: str = "") -> tuple[str, str]:
    """Return (raise|refuse|skip, reason). raise is the only ceiling write."""
    result = plan(card, verdict, approved, root, slug)
    return result["action"], result["reason"]


def raise_target(card: dict, verdict: dict | None = None, approved: frozenset[str] = frozenset(),
                 root: Path | None = None, slug: str = "") -> str:
    """The ceiling the rules allow now."""
    return plan(card, verdict, approved, root, slug)["target"]


def _dumps(card: dict) -> str:
    return json.dumps(card, indent=2, ensure_ascii=False) + "\n"


def _only_missing_verdict(results: list) -> bool:
    failed = [(rid, detail) for rid, ok, detail in results if not ok]
    return bool(failed) and all(detail == "no verdict" for _rid, detail in failed)


def raise_card(path: Path, root: Path, today: str, dry_run: bool) -> tuple[str, str]:
    try:
        raw = path.read_text(encoding="utf-8")
        card = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RaiseError(f"malformed-card: {path.name}: {exc}") from exc
    if not isinstance(card, dict):
        raise RaiseError(f"malformed-card: {path.name}: top level is not an object")
    slug = path.stem
    pr = _rules()
    try:
        rules = pr.load_rules(root)
        verdict_path, verdict = latest_verdict(root, slug)
        result = plan(card, verdict, load_approvals(root).get(slug, frozenset()), root, slug)
    except pr.RuleError as exc:
        raise RaiseError(f"rules: {exc}") from exc
    action, reason = result["action"], result["reason"]
    verdict_rel = ""
    if verdict_path is not None:
        try:
            verdict_rel = verdict_path.relative_to(root).as_posix()
        except ValueError:
            verdict_rel = verdict_path.as_posix()
    updated = dict(card)
    current = card.get("tier_ceiling")
    current_text = current.strip() if isinstance(current, str) else ""
    if action == "raise":
        target = result["target"]
        entry = {
            "from": current_text,
            "to": target,
            "by": "catalog_loop",
            "date": today,
            "reason": reason,
            "evidence": [verdict_rel] if verdict_rel and target == "I3" else [],
            "rules": [rid for rid, _ok, _d in result["results"]],
        }
        updated["tier_ceiling"] = target
        history = updated.get("ceiling_history")
        history = list(history) if isinstance(history, list) else []
        if not history or history[-1] != entry:
            history.append(entry)
        updated["ceiling_history"] = history
        pr.append_ledger(updated, pr.ledger_entry(rules, "ceiling", current_text, target, "raise",
                                                  result["results"], today, verdict_rel))
    elif result["results"] and (result["hard"] or not _only_missing_verdict(result["results"])):
        pr.append_ledger(updated, pr.ledger_entry(rules, "ceiling", current_text, result["target"], "refuse",
                                                  result["results"], today, verdict_rel))
    text = _dumps(updated)
    if text != raw and not dry_run:
        _atomic(path, text)
    return action, reason


def _atomic(path: Path, text: str) -> None:
    import tempfile
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise


def iter_cards(stages: Path) -> list[Path]:
    if not stages.is_dir():
        raise RaiseError(f"missing-stages: {stages}")
    return sorted(path for path in stages.glob("*.json") if path.is_file() and not path.name.startswith("_"))


def lane_kind(card: dict, receipt_exists: bool) -> str:
    """I2 with an I3 or I4 ceiling and no receipt is an integrate lane."""
    stage = card.get("integration_stage")
    ceiling = card.get("tier_ceiling")
    evidence = card.get("evidence") or []
    if not isinstance(evidence, list):
        evidence = []
    has_receipt = receipt_exists or any(
        isinstance(item, str) and item.strip().lower().startswith("receipt:")
        for item in evidence
    )
    if stage == "I2" and ceiling in ("I3", "I4") and not has_receipt:
        return "integrate"
    return "eval"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auto-raise tier_ceiling to I3 when the gates and risk class allow it.")
    parser.add_argument("--root", default=str(ROOT), help="Repo root. Verdicts are read under eval/.")
    parser.add_argument("--stages", default="", help="Stage card directory. Default: <root>/data/stages.")
    parser.add_argument("--date", default="", help="YYYY-MM-DD stored on ceiling_history. Default: PT today or PFY_LOOP_TODAY.")
    parser.add_argument("--slug", default="", help="Only this card.")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan. Write nothing.")
    parser.add_argument("--launch-check", default="", help="Print launch or skip for this slug and do not write.")
    parser.add_argument("--kind", default="", help="Print integrate or eval for this slug and do not write.")
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    stages = Path(args.stages).expanduser() if args.stages else root / "data" / "stages"
    if not stages.is_absolute():
        stages = root / stages
    today = args.date.strip() or pt_today()
    try:
        if args.kind:
            path = stages / f"{args.kind}.json"
            if not path.is_file():
                print("eval")
                return 0
            card = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(card, dict):
                print("eval")
                return 0
            receipt = root / "eval" / "integrate" / args.kind / "receipt.json"
            print(lane_kind(card, receipt.is_file()))
            return 0
        if args.launch_check:
            path = stages / f"{args.launch_check}.json"
            if not path.is_file():
                print(f"skip\t{args.launch_check}\tmissing-card")
                return 0
            card = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(card, dict):
                print(f"skip\t{args.launch_check}\tmalformed-card")
                return 0
            slug = args.launch_check
            approved = load_approvals(root).get(slug, frozenset())
            pr = _rules()
            try:
                rules = pr.load_rules(root)
            except pr.RuleError as exc:
                raise RaiseError(f"rules: {exc}") from exc
            ctx = pr.Ctx(card=card, slug=slug, root=root, name=str(card.get("name") or slug), approved=approved)
            failed = [(rid, detail) for rid, ok, detail in pr.launch_results(rules, ctx) if not ok]
            if failed:
                rid = failed[0][0]
                print(f"skip\t{slug}\t{'excluded' if rid == 'R-not-excluded' else rid}")
                return 0
            if needs_gpu_driver(card, approved):
                print(f"skip\t{slug}\tgpu-driver")
                return 0
            # A card already above its rule-allowed stage is re-checked by the
            # scan each tick; an eval lane would only re-propose that stage.
            stage = card.get("integration_stage")
            if isinstance(stage, str) and stage in RANK and RANK[stage] >= RANK["I2"]:
                ctx.mode = "scan"
                allowed, _passed, failing = pr.stage_allowed(rules, ctx)
                if RANK[stage] > RANK[allowed]:
                    first = next((rid for rid, ok, _d in failing if not ok), "rules")
                    print(f"skip\t{slug}\t{first}: {stage} above allowed {allowed}")
                    return 0
            if risk_track(card) == "security":
                ceiling = _ceiling(card)
                stage = card.get("integration_stage")
                if ceiling is not None and RANK[ceiling] >= RANK["I2"] and stage in ("I0", "I1"):
                    print(f"launch\t{slug}\tsecurity-sandbox")
                    return 0
                if ceiling in ("I3", "I4") and stage == "I2":
                    print(f"launch\t{slug}\tsecurity")
                    return 0
                print(f"skip\t{slug}\tsecurity: ceiling rules not met")
                return 0
            print(f"launch\t{slug}\tnone")
            return 0
        paths = iter_cards(stages)
        if args.slug:
            paths = [path for path in paths if path.stem == args.slug]
        for path in paths:
            action, reason = raise_card(path, root, today, args.dry_run)
            print(f"{action}\t{path.stem}\t{reason}")
    except RaiseError as exc:
        sys.stderr.write(f"{exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
