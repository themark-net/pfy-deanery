#!/usr/bin/env python3
"""Local-model catalog-fit triage. Jev gates the confidence. This is not a second engine.

A small local model (Ollama, temperature 0, JSON) fills the rubric in
data/decision-gates/catalog-fit.v0.json. scripts/pfy_jev_230.py decide_choice
checks the rubric is a Choice, then conf_gate / conf_chip / decision_exit_code
gate the model's confidence. Exit 0 is a confident verdict. Exit 3 is escalate
(conf low, or model JSON that is not a verdict). Exit 1 is broken. Unusable
JSON is never recorded as fit.

Deterministic hard stops stay in scripts/promotion_rules.py. This script does
not edit a stage card and does not pull a model.

  python3 scripts/catalog_fit_triage.py triage SLUG [--mock PATH] [--write]
  python3 scripts/catalog_fit_triage.py replay [--mock PATH] [--model NAME] [--out PATH]

PFY_CATFIT_MOCK is a JSON object mapping slug to a response object (or a raw
string). PFY_CATFIT_MODEL defaults to qwen2.5:14b. The host defaults to
http://127.0.0.1:11434 (PFY_CATFIT_HOST, else OLLAMA_HOST). --write stores
eval/catalog-fit/<slug>.json only for a schema-valid payload.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import pfy_jev_230 as jev  # noqa: E402

VERDICTS = ("fit", "skip_install", "redundant", "awareness")
NEGATIVE = frozenset({"skip_install", "redundant", "awareness"})
REQUIRED = ("slug", "fit", "overlap_with", "verdict", "reason", "confidence")
# Prior decisions (intent, posture, integration_stage, tier_ceiling) are left
# out on purpose, so the model judges the tool, not an earlier label.
CARD_KEYS = (
    "name", "uses", "features", "potential", "next_gate", "non_goals",
    "risk_class", "catalog_tags", "tags", "notes", "github",
)
SLUG_RE = re.compile(r"[a-z0-9][a-z0-9._-]*")
PROMPT_LEAD = (
    "Catalog-fit Choice for Deanery (pfy-deanery). "
    "Pick fit, skip_install, redundant, or awareness."
)
DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen2.5:14b"


class FitError(Exception):
    """A catalog-fit file on disk is unusable. Callers fail closed."""


class FitBroken(Exception):
    """The triage cannot run. Exit 1. Not a model verdict."""


def default_model() -> str:
    raw = (os.environ.get("PFY_CATFIT_MODEL") or DEFAULT_MODEL).strip()
    return raw or DEFAULT_MODEL


def default_host() -> str:
    raw = (
        os.environ.get("PFY_CATFIT_HOST")
        or os.environ.get("OLLAMA_HOST")
        or DEFAULT_HOST
    ).strip()
    return raw or DEFAULT_HOST


def gate_path(root: Path) -> Path:
    return root / "data" / "decision-gates" / "catalog-fit.v0.json"


def load_gate(root: Path) -> dict:
    path = gate_path(root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FitBroken(f"{path.name}: unreadable") from exc
    if not isinstance(data, dict):
        raise FitBroken(f"{path.name}: not an object")
    criteria = data.get("criteria")
    if not isinstance(criteria, dict) or set(criteria) != set(VERDICTS):
        raise FitBroken(f"{path.name}: criteria must be the four verdicts")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise FitBroken(f"{path.name}: cases missing")
    return data


def project_card(card: dict, slug: str) -> dict:
    subject = {"slug": slug}
    for key in CARD_KEYS:
        if key in card:
            subject[key] = card[key]
    return subject


def build_prompt(slug: str, subject: dict, gate: dict) -> str:
    rubric = gate.get("rubric") if isinstance(gate.get("rubric"), dict) else {}
    lines = [
        "You are the local catalog-fit triage for Deanery (pfy-deanery).",
        "Decide whether this subject fits the local-first catalog mission or should skip install.",
        "Weigh the rubric, then emit ONLY one JSON object. No markdown and no prose.",
        "Keys: slug, fit (boolean), overlap_with (string or null), verdict, reason, confidence.",
        "verdict is one of: fit, skip_install, redundant, awareness.",
        f"slug must be {slug}.",
        "confidence is a margin from 0 to 1, never percent-correct.",
        "Decide in this order and stop at the first match:",
        "1. awareness: blast radius is high (rewrites agent or user configs, runtime takeover,",
        "   autostart or system services, secrets or account pools) or the tool is off-mission.",
        "2. redundant: an existing cataloged tool already does the job; name it in overlap_with.",
        "3. skip_install: the tool is optional, adds no unique gap, and a safe default exists.",
        "4. fit: the tool fills a real gap with low or medium blast radius.",
        "non_goals and parked wiring limit scope; they do not make a useful tool skip_install.",
        "",
        "Rubric dimensions:",
    ]
    for key in ("fit", "overlap_with", "skip_install", "blast_radius", "unique_gap"):
        lines.append(f"- {key}: {rubric.get(key, '')}")
    lines.append("")
    lines.append("Verdict criteria:")
    for key, text in gate["criteria"].items():
        lines.append(f"- {key}: {text}")
    lines.append("")
    lines.append("Subject:")
    lines.append(json.dumps(subject, ensure_ascii=False, sort_keys=True, indent=2))
    return "\n".join(lines) + "\n"


def parse_model(text: str, slug: str) -> tuple[dict | None, str]:
    """Return a clean payload, or (None, reason). None escalates. It is never fit."""
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return None, "malformed json"
    if not isinstance(obj, dict):
        return None, "malformed json"
    if any(key not in obj for key in REQUIRED):
        return None, "missing field"
    if obj.get("slug") != slug or type(obj.get("fit")) is not bool:
        return None, "missing field"
    overlap = obj.get("overlap_with")
    if overlap is not None and (type(overlap) is not str or not overlap.strip()):
        return None, "missing field"
    reason = obj.get("reason")
    if type(reason) is not str or not reason.strip():
        return None, "missing field"
    verdict = obj.get("verdict")
    if type(verdict) is not str or verdict not in VERDICTS:
        return None, "unknown verdict"
    conf = obj.get("confidence")
    if isinstance(conf, bool) or not isinstance(conf, (int, float)):
        return None, "confidence out of range"
    conf_f = float(conf)
    if not math.isfinite(conf_f) or conf_f < 0 or conf_f > 1:
        return None, "confidence out of range"
    if (verdict == "fit") != (obj["fit"] is True):
        return None, "unknown verdict"
    return {
        "slug": slug,
        "fit": obj["fit"],
        "overlap_with": overlap.strip() if isinstance(overlap, str) else None,
        "verdict": verdict,
        "reason": reason.strip(),
        "confidence": conf_f,
    }, ""


def gate_record(probe: dict, payload: dict | None) -> dict:
    """Start from decide_choice, then put the model's choice under the Jev gate."""
    rec = dict(probe)
    gate = jev.conf_gate()
    rec["gate"] = gate
    if payload is None:
        rec["ok"] = False
        rec["choice"] = None
        rec["auto_act"] = False
        rec["usable"] = False
        rec["confidence"] = 0.0
        rec["error"] = jev.CHIP_CONF_LOW
        rec["chip_conf"] = jev.conf_chip(0.0, gate)
        rec["live"] = "FAIL"
        return rec
    conf = round(float(payload["confidence"]), 4)
    chip = jev.conf_chip(conf, gate)
    auto = chip == jev.CHIP_CONF_OK
    rec["choice"] = payload["verdict"]
    rec["confidence"] = conf
    rec["chip_conf"] = chip
    rec["auto_act"] = auto
    rec["ok"] = auto
    rec["usable"] = auto
    rec["live"] = "READY" if auto else "FAIL"
    if auto:
        rec.pop("error", None)
    else:
        rec["error"] = jev.CHIP_CONF_LOW
    return rec


def public_record(slug: str, payload: dict | None, rec: dict, model: str, code: int, problem: str) -> dict:
    verdict = rec.get("choice")
    if verdict not in VERDICTS:
        verdict = None
    if payload is None:
        verdict = None
    fit = bool(payload and payload.get("fit") is True and verdict == "fit" and code == jev.EXIT_READY)
    overlap = payload.get("overlap_with") if payload else None
    if not isinstance(overlap, str):
        overlap = None
    reason = ""
    if payload and isinstance(payload.get("reason"), str):
        reason = payload["reason"]
    elif problem:
        reason = problem
    confidence = rec.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        confidence = 0
    gate = rec.get("gate")
    if isinstance(gate, bool) or not isinstance(gate, (int, float)):
        gate = jev.conf_gate()
    return {
        "chip_conf": rec.get("chip_conf") or jev.CHIP_CONF_LOW,
        "confidence": confidence,
        "exit": code,
        "fit": fit,
        "gate": gate,
        "model": model,
        "overlap_with": overlap,
        "reason": reason,
        "slug": slug,
        "verdict": verdict,
    }


def write_result(root: Path, record: dict) -> Path:
    dest = root / "eval" / "catalog-fit" / f"{record['slug']}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    dest.write_text(text, encoding="utf-8")
    return dest


def default_call_model(prompt: str, *, model: str, host: str) -> str:
    """POST /api/generate. Does not pull a model."""
    url = host.rstrip("/") + "/api/generate"
    body = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        # Thinking models (qwen3.x) return an empty response with format json
        # unless thinking is off. Non-thinking models ignore it.
        "think": False,
        "options": {"temperature": 0},
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise FitBroken("ollama unreachable") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FitBroken("ollama response is not json") from exc
    text = data.get("response") if isinstance(data, dict) else None
    if not isinstance(text, str) or not text.strip():
        raise FitBroken("ollama response missing")
    return text


# Tests replace this. CI passes a mock and does not call it.
call_model = default_call_model


def triage(
    slug: str,
    *,
    root: Path | None = None,
    mock: dict | None = None,
    model: str | None = None,
    host: str | None = None,
    write: bool = False,
    subject: dict | None = None,
) -> tuple[int, dict]:
    root = Path(root) if root is not None else ROOT
    model_name = model or default_model()
    host_name = host or default_host()
    if not SLUG_RE.fullmatch(slug or ""):
        raise FitBroken(f"bad slug {slug}")
    gate = load_gate(root)
    criteria = gate["criteria"]
    if subject is None:
        card_path = root / "data" / "stages" / f"{slug}.json"
        if not card_path.is_file():
            raise FitBroken(f"missing card {slug}")
        try:
            card = json.loads(card_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise FitBroken(f"{slug}.json: card unreadable") from exc
        if not isinstance(card, dict):
            raise FitBroken(f"{slug}.json: card is not an object")
        subject = project_card(card, slug)
    prompt = build_prompt(slug, subject, gate)
    if mock is not None:
        if slug not in mock:
            raise FitBroken(f"mock has no {slug}")
        raw = mock[slug]
        text = raw if isinstance(raw, str) else json.dumps(raw)
    else:
        text = call_model(prompt, model=model_name, host=host_name)
    payload, problem = parse_model(text, slug)
    focus = payload["verdict"] if payload else ""
    probe = jev.decide_choice(subject, criteria, instructions=PROMPT_LEAD, focus=focus)
    if not probe.get("choice") and probe.get("error") not in (None, jev.CHIP_CONF_LOW):
        code = jev.decision_exit_code(probe)
        return code, public_record(slug, None, probe, model_name, code, str(probe.get("error") or "broken"))
    rec = gate_record(probe, payload)
    code = jev.decision_exit_code(rec)
    public = public_record(slug, payload, rec, model_name, code, problem)
    if write and payload is not None:
        write_result(root, public)
    return code, public


def _stored_ok(obj: object, slug: str) -> bool:
    if not isinstance(obj, dict):
        return False
    if obj.get("slug") != slug or type(obj.get("fit")) is not bool:
        return False
    overlap = obj.get("overlap_with")
    if overlap is not None and type(overlap) is not str:
        return False
    if type(obj.get("reason")) is not str:
        return False
    if obj.get("verdict") not in VERDICTS:
        return False
    conf = obj.get("confidence")
    if isinstance(conf, bool) or not isinstance(conf, (int, float)):
        return False
    conf_f = float(conf)
    if not math.isfinite(conf_f) or conf_f < 0 or conf_f > 1:
        return False
    return True


def load_stored(path: Path, slug: str) -> dict:
    """Read one eval/catalog-fit file. Malformed raises FitError (fail closed)."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise FitError(f"{path.name}: catalog-fit malformed") from exc
    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise FitError(f"{path.name}: catalog-fit malformed") from exc
    if not _stored_ok(obj, slug):
        raise FitError(f"{path.name}: catalog-fit malformed")
    return obj


def blocks_launch(record: dict) -> bool:
    """True only for a confident skip_install, redundant, or awareness."""
    gate = jev.conf_gate()
    conf = float(record["confidence"])
    if jev.conf_chip(conf, gate) != jev.CHIP_CONF_OK:
        return False
    return record.get("verdict") in NEGATIVE


def case_accept(case: dict) -> list[str]:
    accept = case.get("accept")
    if not isinstance(accept, list) or not accept or any(type(item) is not str or item not in VERDICTS for item in accept):
        raise FitBroken(f"{case.get('id')}: accept missing")
    return list(accept)


def subject_for_case(root: Path, case: dict) -> dict:
    slug = case["slug"]
    card_rel = case.get("card")
    if isinstance(card_rel, str) and card_rel.strip():
        path = root / card_rel
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise FitBroken(f"{path.name}: card unreadable") from exc
        if not isinstance(card, dict):
            raise FitBroken(f"{path.name}: card is not an object")
        return project_card(card, slug)
    state = case.get("state")
    if not isinstance(state, dict):
        raise FitBroken(f"{case.get('id')}: state missing")
    return {
        "slug": slug,
        "source": case.get("source") or "",
        "instructions": case.get("instructions") or "",
        "state": state,
    }


def resolve_out(path: Path) -> Path:
    if path.suffix != ".json":
        path.mkdir(parents=True, exist_ok=True)
        return path / "catalog-fit-replay.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def replay(*, root: Path, mock: dict | None, model: str, host: str, out: Path) -> int:
    gate = load_gate(root)
    rows = []
    failed = 0
    for case in gate["cases"]:
        if not isinstance(case, dict) or not isinstance(case.get("slug"), str):
            raise FitBroken("case missing slug")
        slug = case["slug"]
        accept = case_accept(case)
        try:
            subject = subject_for_case(root, case)
            code, rec = triage(
                slug, root=root, mock=mock, model=model, host=host, write=False, subject=subject,
            )
        except FitBroken as exc:
            code, rec = jev.EXIT_BROKEN, {"verdict": None, "reason": str(exc), "exit": jev.EXIT_BROKEN}
        verdict = rec.get("verdict")
        ok = code == jev.EXIT_READY and verdict in accept
        if not ok:
            failed += 1
        rows.append({
            "accept": accept,
            "exit": code,
            "id": case.get("id") or slug,
            "ok": ok,
            "reason": rec.get("reason") or "",
            "slug": slug,
            "verdict": verdict,
        })
    passed = len(rows) - failed
    payload = {"failed": failed, "model": model, "passed": passed, "results": rows}
    dest = resolve_out(out)
    dest.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"passed {passed} failed {failed}")
    return 0 if failed == 0 else 1


def load_mock_file(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FitBroken(f"mock unreadable: {path.name}") from exc
    if not isinstance(data, dict):
        raise FitBroken("mock is not an object")
    return data


def _mock_from_args(flag: str) -> dict | None:
    raw = (flag or os.environ.get("PFY_CATFIT_MOCK") or "").strip()
    if not raw:
        return None
    return load_mock_file(Path(raw))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local-model catalog-fit triage. Does not pull a model.")
    parser.add_argument("--root", default=str(ROOT))
    sub = parser.add_subparsers(dest="cmd", required=True)
    triage_p = sub.add_parser("triage", help="Triage one slug")
    triage_p.add_argument("slug")
    triage_p.add_argument("--mock", default="")
    triage_p.add_argument("--model", default="")
    triage_p.add_argument("--host", default="")
    triage_p.add_argument("--write", action="store_true")
    replay_p = sub.add_parser("replay", help="Replay the labeled goldens")
    replay_p.add_argument("--mock", default="")
    replay_p.add_argument("--model", default="")
    replay_p.add_argument("--host", default="")
    replay_p.add_argument("--out", default="tmp")
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser()
    if not root.is_absolute():
        root = (Path.cwd() / root).resolve()
    try:
        mock = _mock_from_args(args.mock)
        model = args.model.strip() or default_model()
        host = args.host.strip() or default_host()
        if args.cmd == "triage":
            code, rec = triage(
                args.slug, root=root, mock=mock, model=model, host=host, write=args.write,
            )
            print(json.dumps(rec, indent=2, sort_keys=True, ensure_ascii=False))
            return code
        out = Path(args.out)
        if not out.is_absolute():
            out = Path.cwd() / out
        return replay(root=root, mock=mock, model=model, host=host, out=out)
    except FitBroken as exc:
        print(str(exc), file=sys.stderr)
        return jev.EXIT_BROKEN


if __name__ == "__main__":
    raise SystemExit(main())
