#!/usr/bin/env python3
"""Raise tier_ceiling to I3 when a verdict and the risk class allow it.

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
    pentest, penetration, exploit, vulnerability, sast, keyring
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
RISK_ENUM = ("security", "live-money", "runtime-takeover", "none")
TOKEN_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
SIZE_RE = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*(gb|gib)\b", re.IGNORECASE)

SECURITY_TOKENS = frozenset({
    "security", "secret", "secrets", "credential", "credentials", "password",
    "pentest", "penetration", "exploit", "vulnerability", "sast", "keyring",
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


def block_reason(card: dict) -> str:
    """gpu, pull-over-25gb, release-deploy, or empty when the card may launch."""
    tokens = tokens_of(card)
    if size_over_25(card):
        return "pull-over-25gb"
    if has_gpu(tokens):
        return "gpu"
    if tokens & RELEASE_TOKENS or any(part in RELEASE_TOKENS for token in tokens for part in token.split("-")):
        return "release-deploy"
    return ""


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


def plan_card(card: dict, verdict: dict | None) -> tuple[str, str]:
    """Return (raise|refuse|skip, reason). raise is the only write."""
    current = _ceiling(card)
    if current is not None and RANK[current] > RANK["I3"]:
        return "skip", "ceiling above I3"
    if current == "I3":
        return "skip", "ceiling already I3"
    blocked = block_reason(card)
    if blocked:
        return "refuse", blocked
    risk = classify_risk(card)
    if risk != "none":
        return "refuse", risk
    if not gates_pass(verdict):
        return "skip", "gates"
    return "raise", "value_gate and modularity_gate passed and risk_class is none"


def _dumps(card: dict) -> str:
    return json.dumps(card, indent=2, ensure_ascii=False) + "\n"


def raise_card(path: Path, root: Path, today: str, dry_run: bool) -> tuple[str, str]:
    try:
        raw = path.read_text(encoding="utf-8")
        card = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RaiseError(f"malformed-card: {path.name}: {exc}") from exc
    if not isinstance(card, dict):
        raise RaiseError(f"malformed-card: {path.name}: top level is not an object")
    slug = path.stem
    try:
        if exclusion_reason(root, slug):
            return "refuse", "excluded"
    except QueueError as exc:
        raise RaiseError(f"exclusions: {exc}") from exc
    verdict_path, verdict = latest_verdict(root, slug)
    action, reason = plan_card(card, verdict)
    if action != "raise":
        return action, reason
    current = card.get("tier_ceiling")
    current_text = current.strip() if isinstance(current, str) else ""
    evidence: list[str] = []
    if verdict_path is not None:
        try:
            evidence.append(verdict_path.relative_to(root).as_posix())
        except ValueError:
            evidence.append(verdict_path.as_posix())
    entry = {
        "from": current_text,
        "to": "I3",
        "by": "catalog_loop",
        "date": today,
        "reason": reason,
        "evidence": evidence,
    }
    updated = dict(card)
    updated["tier_ceiling"] = "I3"
    history = updated.get("ceiling_history")
    if not isinstance(history, list):
        history = []
    else:
        history = list(history)
    if not history or history[-1] != entry:
        history.append(entry)
    updated["ceiling_history"] = history
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
            try:
                if exclusion_reason(root, args.launch_check):
                    print(f"skip\t{args.launch_check}\texcluded")
                    return 0
            except QueueError as exc:
                raise RaiseError(f"exclusions: {exc}") from exc
            blocked = block_reason(card)
            risk = classify_risk(card)
            if blocked:
                print(f"skip\t{args.launch_check}\t{blocked}")
                return 0
            if risk != "none":
                print(f"skip\t{args.launch_check}\t{risk}")
                return 0
            print(f"launch\t{args.launch_check}\t{risk}")
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
