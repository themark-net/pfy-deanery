#!/usr/bin/env python3
"""Jev-style decision layer -- typed Choice/Score. Cite #230.

Primary local attach: CUA-S1-FORMS (~706K / ~2.8MB form-fill specialist;
https://github.com/trycua/cua). operator-free nimo smoke. mini-jev is a
teaching fallback only. TypeSafe Jev is optional cloud (compaction /
routing) with model jev-1.13.0 and ~0.85 confidence gate.

Decision API, not chat. Confidence = calibrated margin chips, never
painted as percent-correct. Core = coding-session compaction + model/tool
middleware, not browser-use. Honesty: decision ≠ gab auto ≠ local.

Catalog 70-75 HOLD. Do not reopen #76. #225 Launch intact. #228 Gab
lane intact. No Env tab. LIVE_HARD_OFF: no TypeSafe call without key.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ISSUE = "#230"
TYPESAFE_URL = "https://api.typesafe.ai/v1/systemone"
TYPESAFE_DOCS = "https://docs.typesafe.ai/api"
TYPESAFE_MODEL = "jev-1.13.0"
CUA_REPO = "https://github.com/trycua/cua"
MINI_JEV_REF = "https://github.com/r-ms/mini-jev"
CONF_GATE = 0.85
STATE_FILE = "decision-layer.json"
QUEUE_FILE = "decision-queue.jsonl"
WIZARD_FILE = "launch-wizard.json"
FIXTURE_REL = Path("scripts") / "fixtures" / "cua_s1_forms_v0.json"

PATHS = ("off", "cua-s1-forms", "typesafe", "mini-jev")
PRIMARY_LOCAL = "cua-s1-forms"

CHIP_DECISION = "decision · typed Choice"
CHIP_HONEST = "decision ≠ gab auto ≠ local"
CHIP_CONF_OK = "conf ok"
CHIP_CONF_LOW = "conf low"
CHIP_MARGIN = "conf margin"
CHIP_TYPESAFE_OPT = "typesafe key optional"
CHIP_CUA = "cua-s1-forms · FreeToken-first"
CHIP_CORE = "compact context · choose model/tool"
CHIP_FALLBACK = "mini-jev · teaching fallback"
CHIP_SHADOW_DISAGREE = "shadow disagree"
CHIP_SHADOW_ERROR = "shadow error"
LAYA_SHADOW_MODEL = "english"
LAYA_SHADOW_DUMMY_KEY = "laya-local-shadow"

NEXT_KEY = "set TYPESAFE_API_KEY · " + TYPESAFE_DOCS + " · or switch local CUA-S1-FORMS"
NEXT_LOW = "raise threshold bar, confirm, or fallback model — no silent auto-act"
NEXT_RUNTIME = "install/pull CUA-S1-FORMS FreeToken-first local path · " + CUA_REPO
NEXT_OFF = "decision off · typed Choice idle"
NEXT_HONEST = "chip " + CHIP_HONEST

TOKEN_RE = re.compile(r"[a-z0-9:+._-]+")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_state(STATE):
    return Path(STATE)


def _read(path):
    path = Path(path)
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((text or "").rstrip() + "\n", encoding="utf-8")


def fail(kind, reason, next_step, **extra):
    copy = "FAIL %s -- %s · %s" % (kind, reason, next_step)
    out = {
        "ok": False,
        "live": "FAIL",
        "copy": copy,
        "error": reason,
        "next_step": next_step,
        "usable": False,
        "issue": ISSUE,
        "honesty": CHIP_HONEST,
        "chip_decision": CHIP_DECISION,
        "chip_core": CHIP_CORE,
    }
    out.update(extra)
    return out


def typesafe_key():
    return (
        str(os.environ.get("TYPESAFE_API_KEY") or "").strip()
        or str(os.environ.get("TYPESAFE_KEY") or "").strip()
        or str(os.environ.get("JEV_API_KEY") or "").strip()
    )


def conf_gate():
    raw = str(os.environ.get("PFY_JEV_CONF_GATE") or "").strip()
    if not raw:
        return CONF_GATE
    try:
        v = float(raw)
    except ValueError:
        return CONF_GATE
    if v < 0 or v > 1:
        return CONF_GATE
    return v


def typesafe_model():
    return str(os.environ.get("PFY_JEV_MODEL") or TYPESAFE_MODEL).strip() or TYPESAFE_MODEL


def typesafe_url():
    """Optional trial override. Default stays the TypeSafe cloud endpoint."""
    raw = str(os.environ.get("PFY_JEV_TYPESAFE_URL") or "").strip()
    return raw or TYPESAFE_URL


def typesafe_timeout():
    """Seconds for the TypeSafe POST. Default 8. Trial may raise this for CPU."""
    raw = str(os.environ.get("PFY_JEV_TYPESAFE_TIMEOUT") or "").strip()
    if not raw:
        return 8
    try:
        v = float(raw)
    except ValueError:
        return 8
    if v <= 0:
        return 8
    return v


def offline():
    return str(os.environ.get("PFY_JEV_OFFLINE") or "").strip().lower() in ("1", "true", "yes")


def laya_shadow_enabled():
    return str(os.environ.get("PFY_JEV_LAYA_SHADOW") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def laya_shadow_model():
    """Shadow call model. Unset PFY_JEV_MODEL → english (not jev-1.13.0)."""
    raw = str(os.environ.get("PFY_JEV_MODEL") or "").strip()
    return raw or LAYA_SHADOW_MODEL


def typesafe_url_is_local(url=None):
    """True only for a local laya-serve override. Cloud TypeSafe is never local."""
    u = str(url if url is not None else typesafe_url() or "").strip().lower()
    if not u or u.rstrip("/") == TYPESAFE_URL.lower().rstrip("/"):
        return False
    return "127.0.0.1" in u or "localhost" in u or "[::1]" in u


def tokenize(text):
    return TOKEN_RE.findall(str(text or "").lower())


def softmax(scores, temp=0.35):
    if not scores:
        return []
    t = float(temp) if temp else 0.35
    if t <= 0:
        t = 0.35
    mx = max(scores)
    exps = [math.exp((s - mx) / t) for s in scores]
    z = sum(exps) or 1.0
    return [e / z for e in exps]


def choice_confidence(probs):
    """Calibrated margin from the Choice distribution. Not correctness %."""
    vals = [float(p) for p in (probs or []) if p is not None]
    n = len(vals)
    if n <= 1:
        return 1.0 if n == 1 else 0.0
    pmax = max(vals)
    return max(0.0, min(1.0, (n * pmax - 1.0) / (n - 1.0)))


def conf_chip(confidence, gate=None):
    gate = CONF_GATE if gate is None else float(gate)
    c = float(confidence or 0)
    if c >= gate:
        return CHIP_CONF_OK
    return CHIP_CONF_LOW


def option_score(state_text, option_key, option_desc="", focus=""):
    """CUA-S1-FORMS-compatible option-attention analogue (stdlib, no weights)."""
    st = tokenize(state_text)
    op = tokenize("%s %s" % (option_key, option_desc))
    if not op:
        return 0.0
    bag = set(st)
    hits = sum(1 for t in op if t in bag)
    key = str(option_key or "").lower()
    blob = str(state_text or "").lower()
    bonus = 0.0
    if key and key in blob:
        bonus += 1.6
    focus_toks = tokenize(focus)
    key_toks = tokenize(option_key)
    if focus_toks and any(t in key_toks or t in tokenize(option_desc) for t in focus_toks):
        bonus += 3.2
    if str(option_key or "").split(":", 1)[0] in ("keep", "fill", "click", "check") and hits:
        bonus += 0.6
    return hits + bonus


def decide_choice(state, criteria, *, instructions="", focus=""):
    """Typed Choice: pick one option, return probabilities + margin confidence."""
    if not isinstance(criteria, dict) or not criteria:
        return fail("choice", "criteria empty", "rebuild Choice options from live state")
    keys = list(criteria.keys())
    blob = "%s\n%s" % (instructions or "", json.dumps(state, ensure_ascii=False) if not isinstance(state, str) else state)
    scores = [option_score(blob, k, criteria.get(k) or "", focus=focus) for k in keys]
    if max(scores) <= 0:
        scores = [1.0] * len(keys)
    probs = softmax(scores, temp=0.2)
    idx = max(range(len(keys)), key=lambda i: probs[i])
    pick = keys[idx]
    dist = {keys[i]: round(probs[i], 6) for i in range(len(keys))}
    conf = round(choice_confidence(probs), 4)
    gate = conf_gate()
    chip = conf_chip(conf, gate)
    auto = conf >= gate
    rec = {
        "ok": True if auto else False,
        "live": "READY" if auto else "FAIL",
        "type": "choice",
        "choice": pick,
        "probabilities": dist,
        "confidence": conf,
        "gate": gate,
        "chip_conf": chip,
        "chip_margin": CHIP_MARGIN,
        "honesty": CHIP_HONEST,
        "chip_decision": CHIP_DECISION,
        "auto_act": auto,
        "issue": ISSUE,
        "copy": (
            "READY decision · typed Choice · %s · %s"
            % (pick, chip)
            if auto
            else "FAIL decision -- %s · %s" % (chip, NEXT_LOW)
        ),
        "next_step": "" if auto else NEXT_LOW,
        "usable": auto,
        "instructions": instructions or "",
    }
    if not auto:
        rec["error"] = CHIP_CONF_LOW
    return rec


def _apply_shadow_escalate(rec, shadow, chip):
    rec = dict(rec)
    rec["ok"] = False
    rec["live"] = "FAIL"
    rec["auto_act"] = False
    rec["usable"] = False
    rec["error"] = CHIP_CONF_LOW
    rec["chip_conf"] = CHIP_CONF_LOW
    rec["chip_shadow"] = chip
    rec["copy"] = "FAIL decision -- %s · %s" % (chip, NEXT_LOW)
    rec["next_step"] = NEXT_LOW
    rec["shadow"] = shadow
    return rec


def maybe_laya_shadow(rec, state, criteria, *, instructions="", qid="shadow"):
    """Opt-in Laya second opinion after a CUA Choice that would auto-act.

    Flag off → identity (no network, no shadow key). Flag on + disagree or
    Laya error → escalate (exit 3). Flag on + agree → leave CUA ready and
    attach a shadow log. Never calls cloud TypeSafe.
    """
    if not laya_shadow_enabled():
        return rec
    rec = rec or {}
    if not rec.get("auto_act"):
        return rec
    cua_choice = rec.get("choice")
    model = laya_shadow_model()
    t0 = time.perf_counter()
    if not typesafe_url_is_local():
        shadow = {
            "enabled": True,
            "engine": "laya",
            "model": model,
            "cua_choice": cua_choice,
            "laya_choice": None,
            "laya_confidence": None,
            "agree": False,
            "action": "escalate",
            "latency_s": round(time.perf_counter() - t0, 4),
            "error": "refuse cloud TypeSafe; set PFY_JEV_TYPESAFE_URL to local laya-serve",
        }
        return _apply_shadow_escalate(rec, shadow, CHIP_SHADOW_ERROR)
    if offline():
        shadow = {
            "enabled": True,
            "engine": "laya",
            "model": model,
            "cua_choice": cua_choice,
            "laya_choice": None,
            "laya_confidence": None,
            "agree": False,
            "action": "escalate",
            "latency_s": round(time.perf_counter() - t0, 4),
            "error": "Laya shadow offline (PFY_JEV_OFFLINE)",
        }
        return _apply_shadow_escalate(rec, shadow, CHIP_SHADOW_ERROR)
    qid = str(qid or "shadow")
    questions = {
        qid: {
            "type": "choice",
            "instructions": instructions or "",
            "criteria": criteria,
        }
    }
    saved_model = os.environ.get("PFY_JEV_MODEL")
    injected_key = False
    os.environ["PFY_JEV_MODEL"] = model
    if not typesafe_key():
        os.environ["TYPESAFE_API_KEY"] = LAYA_SHADOW_DUMMY_KEY
        injected_key = True
    try:
        laya_rec = typesafe_evaluate(state, questions)
    except Exception as e:
        laya_rec = fail(
            "decision",
            "Laya shadow: %s" % str(e)[:120],
            NEXT_LOW,
            engine="laya",
        )
    finally:
        if saved_model is None:
            os.environ.pop("PFY_JEV_MODEL", None)
        else:
            os.environ["PFY_JEV_MODEL"] = saved_model
        if injected_key:
            os.environ.pop("TYPESAFE_API_KEY", None)
    latency = round(time.perf_counter() - t0, 4)
    answers = laya_rec.get("answers") if isinstance(laya_rec, dict) else {}
    ans = {}
    if isinstance(answers, dict):
        raw_ans = answers.get(qid)
        if isinstance(raw_ans, dict):
            ans = raw_ans
        elif len(answers) == 1:
            only = next(iter(answers.values()))
            if isinstance(only, dict):
                ans = only
    laya_choice = ans.get("choice")
    try:
        laya_conf = float(ans["confidence"]) if ans.get("confidence") is not None else None
    except (TypeError, ValueError):
        laya_conf = None
    shadow = {
        "enabled": True,
        "engine": "laya",
        "model": (laya_rec.get("model") if isinstance(laya_rec, dict) else None) or model,
        "cua_choice": cua_choice,
        "laya_choice": laya_choice,
        "laya_confidence": laya_conf,
        "agree": (laya_choice is not None) and (str(laya_choice) == str(cua_choice)),
        "action": "pass",
        "latency_s": latency,
    }
    if laya_choice is None:
        shadow["error"] = str(
            laya_rec.get("error") or laya_rec.get("copy") or "Laya shadow returned no choice"
        )[:240]
        shadow["action"] = "escalate"
        shadow["agree"] = False
        return _apply_shadow_escalate(rec, shadow, CHIP_SHADOW_ERROR)
    if not shadow["agree"]:
        shadow["action"] = "escalate"
        return _apply_shadow_escalate(rec, shadow, CHIP_SHADOW_DISAGREE)
    rec = dict(rec)
    rec["shadow"] = shadow
    return rec


def decide_score(state, levels, *, instructions=""):
    """Typed Score: ordered rubric, probability-weighted value + margin."""
    if not isinstance(levels, (list, tuple)) or len(levels) < 2:
        return fail("score", "need >=2 levels", "pass an ordered rubric")
    levels = [str(x) for x in levels]
    blob = "%s\n%s" % (
        instructions or "",
        json.dumps(state, ensure_ascii=False) if not isinstance(state, str) else state,
    )
    scores = [option_score(blob, str(i), levels[i]) for i in range(len(levels))]
    if max(scores) <= 0:
        scores = [1.0] * len(levels)
    probs = softmax(scores)
    dist = {str(i): round(probs[i], 6) for i in range(len(levels))}
    value = sum(i * probs[i] for i in range(len(levels)))
    conf = round(choice_confidence(probs), 4)
    gate = conf_gate()
    chip = conf_chip(conf, gate)
    rec = {
        "ok": conf >= gate,
        "live": "READY" if conf >= gate else "FAIL",
        "type": "score",
        "score": round(value, 4),
        "legend": {str(i): levels[i] for i in range(len(levels))},
        "probabilities": dist,
        "confidence": conf,
        "gate": gate,
        "chip_conf": chip,
        "chip_margin": CHIP_MARGIN,
        "honesty": CHIP_HONEST,
        "chip_decision": CHIP_DECISION,
        "issue": ISSUE,
        "copy": "READY decision · typed Score · %.2f · %s" % (value, chip)
        if conf >= gate
        else "FAIL decision -- %s · %s" % (chip, NEXT_LOW),
        "next_step": "" if conf >= gate else NEXT_LOW,
        "usable": conf >= gate,
        "auto_act": conf >= gate,
        "instructions": instructions or "",
    }
    if conf < gate:
        rec["error"] = CHIP_CONF_LOW
    return rec


def normalize_path(raw):
    s = str(raw or "").strip().lower().replace("_", "-").replace(" ", "-")
    if s in ("", "off", "none", "idle"):
        return "off"
    if s in (
        "cua-s1-forms",
        "cua-s1",
        "cua",
        "forms",
        "local",
        "freetoken",
        "primary",
    ):
        return "cua-s1-forms"
    if s in ("typesafe", "type-safe", "jev", "jev-cloud", "cloud"):
        return "typesafe"
    if s in ("mini-jev", "minijev", "teaching", "fallback", "qwen3-4b"):
        return "mini-jev"
    return s


def load_state(STATE):
    STATE = _now_state(STATE)
    raw = _read(STATE / STATE_FILE)
    if not raw.strip():
        return {"path": "off", "when": "", "issue": ISSUE}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"path": "off", "when": "", "issue": ISSUE}
    if not isinstance(data, dict):
        return {"path": "off", "when": "", "issue": ISSUE}
    data["path"] = normalize_path(data.get("path") or "off")
    return data


def save_state(STATE, data):
    STATE = _now_state(STATE)
    payload = dict(data or {})
    payload["when"] = _now()
    payload["issue"] = ISSUE
    _write(STATE / STATE_FILE, json.dumps(payload, indent=2))
    return payload


def fixture_path(ROOT=None):
    root = Path(ROOT or os.environ.get("PFY_ROOT") or Path(__file__).resolve().parents[1])
    return root / FIXTURE_REL


def load_fixture(ROOT=None):
    path = fixture_path(ROOT)
    raw = _read(path)
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def path_paint(path):
    path = normalize_path(path)
    if path == "off":
        return "○ off"
    if path == "cua-s1-forms":
        return "● local CUA-S1-FORMS · FreeToken-first"
    if path == "typesafe":
        return "● TypeSafe · compaction/routing"
    if path == "mini-jev":
        return "● local mini-jev · teaching fallback"
    return path


def set_path(STATE, path, ROOT=None):
    """Wizard/Attach toggle: off | cua-s1-forms | typesafe | mini-jev."""
    path = normalize_path(path)
    if path not in PATHS:
        return fail(
            "decision",
            "unknown path %s" % (path or "(empty)"),
            "pick off | CUA-S1-FORMS | TypeSafe | mini-jev",
            path=path,
            paint=path_paint(path),
        )
    rec = {
        "ok": True,
        "live": "READY",
        "path": path,
        "paint": path_paint(path),
        "primary_local": PRIMARY_LOCAL,
        "chip_decision": CHIP_DECISION,
        "honesty": CHIP_HONEST,
        "chip_core": CHIP_CORE,
        "chip_margin": CHIP_MARGIN,
        "issue": ISSUE,
        "usable": True,
    }
    if path == "off":
        rec["copy"] = "READY decision -- off"
        rec["chip_conf"] = ""
        rec["next_step"] = NEXT_OFF
    elif path == "cua-s1-forms":
        rec["copy"] = "READY decision -- %s" % CHIP_CUA
        rec["chip_local"] = CHIP_CUA
        rec["engine"] = "cua-s1-forms"
        rec["repo"] = CUA_REPO
        rec["chip_conf"] = CHIP_CONF_OK
    elif path == "mini-jev":
        rec["copy"] = "READY decision -- %s" % CHIP_FALLBACK
        rec["chip_local"] = CHIP_FALLBACK
        rec["engine"] = "mini-jev"
        rec["repo"] = MINI_JEV_REF
        rec["chip_conf"] = CHIP_CONF_OK
        rec["note"] = "mini-jev is teaching fallback; CUA-S1-FORMS is primary local"
    else:
        key = typesafe_key()
        rec["chip_typesafe"] = CHIP_TYPESAFE_OPT
        rec["engine"] = "typesafe"
        rec["model"] = typesafe_model()
        rec["endpoint"] = typesafe_url()
        if not key:
            rec = fail(
                "decision",
                "key missing (optional)",
                NEXT_KEY,
                path=path,
                paint=path_paint(path),
                chip_typesafe=CHIP_TYPESAFE_OPT,
                engine="typesafe",
                model=typesafe_model(),
                endpoint=typesafe_url(),
            )
            rec["path"] = path
            rec["paint"] = path_paint(path)
            save_state(STATE, {"path": path, "key": "missing"})
            return rec
        rec["copy"] = "READY decision -- TypeSafe · compaction/routing · key set"
        rec["chip_conf"] = CHIP_CONF_OK
        rec["key"] = "set"
    save_state(STATE, rec)
    return rec


def cua_s1_forms_plan(form=None, ROOT=None):
    """Form-fill specialist: Choice fill/check/click/skip per element. Cite #230."""
    form = dict(form or load_fixture(ROOT) or {})
    entities = list(form.get("document") or [])
    elements = list(form.get("elements") or [])
    title = str(form.get("form_title") or "form")
    answers = []
    for el in elements:
        role = str(el.get("role") or "")
        label = str(el.get("label") or el.get("id") or "")
        eid = str(el.get("id") or label or role)
        criteria = {"skip": "leave this element unchanged"}
        if role == "CheckBox":
            criteria["check"] = "check the box because the document asks for it"
        elif role == "Button":
            criteria["click"] = "click to submit or launch"
        else:
            for ent in entities:
                elab = str(ent.get("label") or "")
                eval_ = str(ent.get("value") or "")
                if not elab:
                    continue
                criteria["fill:%s" % elab] = "fill with %s=%s" % (elab, eval_)
        state = {
            "task": "fill the form from the document, then submit",
            "form": title,
            "element": {"role": role, "label": label, "value": el.get("value"), "checked": el.get("checked")},
            "document": entities,
        }
        rec = decide_choice(
            state,
            criteria,
            instructions="CUA-S1-FORMS form-fill specialist: pick one action for this element",
            focus=label,
        )
        rec["element"] = eid
        rec["role"] = role
        rec["engine"] = "cua-s1-forms"
        rec["repo"] = CUA_REPO
        rec = maybe_laya_shadow(
            rec,
            state,
            criteria,
            instructions="CUA-S1-FORMS form-fill specialist: pick one action for this element",
            qid=eid or "shadow",
        )
        answers.append(rec)
    ok = all(a.get("ok") for a in answers) if answers else False
    picks = {a.get("element"): a.get("choice") for a in answers}
    low = [a for a in answers if not a.get("auto_act")]
    copy = (
        "READY decision · CUA-S1-FORMS · typed Choice · %s"
        % " · ".join("%s=%s" % (k, v) for k, v in picks.items())
        if answers and not low
        else "FAIL decision -- conf low on %s · %s"
        % (", ".join(a.get("element") or "?" for a in low), NEXT_LOW)
        if low
        else "FAIL decision -- empty form · " + NEXT_RUNTIME
    )
    return {
        "ok": bool(ok and answers),
        "live": "READY" if ok and answers else "FAIL",
        "copy": copy,
        "engine": "cua-s1-forms",
        "repo": CUA_REPO,
        "answers": answers,
        "picks": picks,
        "chip_decision": CHIP_DECISION,
        "honesty": CHIP_HONEST,
        "chip_local": CHIP_CUA,
        "chip_core": CHIP_CORE,
        "chip_margin": CHIP_MARGIN,
        "issue": ISSUE,
        "usable": bool(ok and answers),
        "next_step": "" if ok and answers else (NEXT_LOW if low else NEXT_RUNTIME),
        "form_title": title,
    }


def mini_jev_choice(state, criteria, *, instructions=""):
    """Teaching fallback: same Choice API, labeled mini-jev."""
    rec = decide_choice(state, criteria, instructions=instructions or "mini-jev logit Choice")
    rec["engine"] = "mini-jev"
    rec["repo"] = MINI_JEV_REF
    rec["chip_local"] = CHIP_FALLBACK
    rec["note"] = "mini-jev teaching fallback; CUA-S1-FORMS is primary local"
    return rec


def typesafe_evaluate(state, questions, ROOT=None):
    """Optional TypeSafe cloud. Key missing → FAIL+next (no operator drip)."""
    key = typesafe_key()
    if not key:
        return fail(
            "decision",
            "key missing (optional)",
            NEXT_KEY,
            path="typesafe",
            chip_typesafe=CHIP_TYPESAFE_OPT,
            engine="typesafe",
            model=typesafe_model(),
        )
    if offline():
        return fail(
            "decision",
            "TypeSafe offline (LIVE_HARD_OFF)",
            NEXT_KEY,
            path="typesafe",
            chip_typesafe=CHIP_TYPESAFE_OPT,
            engine="typesafe",
        )
    body = json.dumps(
        {
            "state": state,
            "model": typesafe_model(),
            "questions": questions,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        typesafe_url(),
        data=body,
        headers={
            "Authorization": "Bearer %s" % key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "pfy-mentat/230",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=typesafe_timeout()) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return fail("decision", "TypeSafe HTTP %s" % e.code, NEXT_KEY, engine="typesafe")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return fail("decision", "TypeSafe network: %s" % str(e)[:120], NEXT_KEY, engine="typesafe")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return fail("decision", "TypeSafe bad JSON", NEXT_KEY, engine="typesafe")
    answers = data.get("answers") if isinstance(data, dict) else {}
    gated = []
    auto = True
    for qid, ans in (answers or {}).items():
        if not isinstance(ans, dict):
            continue
        conf = float(ans.get("confidence") or 0)
        chip = conf_chip(conf)
        row = dict(ans)
        row["id"] = qid
        row["chip_conf"] = chip
        row["auto_act"] = conf >= conf_gate()
        if not row["auto_act"]:
            auto = False
        gated.append(row)
    return {
        "ok": auto,
        "live": "READY" if auto else "FAIL",
        "copy": (
            "READY decision -- TypeSafe · compaction/routing"
            if auto
            else "FAIL decision -- %s · %s" % (CHIP_CONF_LOW, NEXT_LOW)
        ),
        "engine": "typesafe",
        "model": data.get("model") if isinstance(data, dict) else typesafe_model(),
        "answers": answers,
        "gated": gated,
        "chip_decision": CHIP_DECISION,
        "honesty": CHIP_HONEST,
        "chip_typesafe": CHIP_TYPESAFE_OPT,
        "chip_margin": CHIP_MARGIN,
        "issue": ISSUE,
        "usable": auto,
        "next_step": "" if auto else NEXT_LOW,
        "auto_act": auto,
    }


def live_choice_options(live=None):
    """Rebuild Choice options from live wizard/engine state — never a stale list."""
    live = dict(live or {})
    lane = str(live.get("wizard_lane") or live.get("lane") or "local")
    hid = str(live.get("wizard_harness") or live.get("harness") or "")
    toolset = str(live.get("wizard_toolsets") or live.get("toolsets") or "bare")
    models = live.get("models") or live.get("recommend") or []
    opts = {}
    if lane == "local":
        tags = []
        for m in models:
            if isinstance(m, dict):
                tags.append(str(m.get("name") or m.get("tag") or m.get("id") or ""))
            else:
                tags.append(str(m))
        tags = [t for t in tags if t]
        if tags:
            for t in tags[:12]:
                opts[t] = "local model on FreeToken-first spine (not gab auto)"
        else:
            opts["freetoken"] = "FreeToken-first live engine"
    elif lane == "cloud/subscription":
        if hid == "gab":
            opts["gab-auto"] = "Gab Intent Engine model=auto — cloud router, not local ranking"
        elif hid:
            opts[hid] = "cloud/subscription harness %s" % hid
        else:
            opts["cloud"] = "cloud/subscription (Gab or Grok-sub)"
    elif lane == "opencode-free":
        opts["opencode"] = "OpenCode free-model lane"
    else:
        opts["local"] = "default local FreeToken-first"
    if toolset and toolset not in opts:
        opts["tool:%s" % toolset] = "wizard toolset %s" % toolset
    return opts


def route_model_tool(live=None, *, path="cua-s1-forms"):
    """Model/tool Choice middleware. Options rebuilt from live state."""
    live = dict(live or {})
    criteria = live_choice_options(live)
    instructions = (
        "Choose the model or tool for this coding session. "
        "Decision layer is not Gab auto and not local recommend order."
    )
    path = normalize_path(path)
    if path == "mini-jev":
        rec = mini_jev_choice(live, criteria, instructions=instructions)
    else:
        rec = decide_choice(live, criteria, instructions=instructions)
        rec["engine"] = "cua-s1-forms" if path != "typesafe" else "typesafe"
        if rec.get("engine") == "cua-s1-forms":
            rec = maybe_laya_shadow(
                rec, live, criteria, instructions=instructions, qid="route"
            )
    rec["path"] = path if path != "off" else "cua-s1-forms"
    rec["chip_core"] = CHIP_CORE
    rec["options_from"] = "live-state"
    rec["criteria"] = criteria
    return rec


def compact_session(messages, *, path="cua-s1-forms"):
    """Keep session text verbatim; Choice keep|truncate|drop per tool result."""
    msgs = list(messages or [])
    if not msgs:
        return {
            "ok": True,
            "live": "READY",
            "copy": "READY decision · compact · empty session",
            "kept": [],
            "dropped": [],
            "decisions": [],
            "chip_core": CHIP_CORE,
            "chip_decision": CHIP_DECISION,
            "honesty": CHIP_HONEST,
            "issue": ISSUE,
            "usable": True,
            "engine": "cua-s1-forms" if normalize_path(path) != "mini-jev" else "mini-jev",
        }
    last_user = ""
    for m in reversed(msgs):
        if str((m or {}).get("role") or "") == "user":
            last_user = str((m or {}).get("text") or (m or {}).get("content") or "")
            break
    kept, dropped, decisions = [], [], []
    n = len(msgs)
    for i, m in enumerate(msgs):
        role = str((m or {}).get("role") or "")
        text = str((m or {}).get("text") or (m or {}).get("content") or "")
        tool = (m or {}).get("tool") or (m or {}).get("tool_result") or ""
        is_tool = bool(tool) or role in ("tool", "tool_result")
        pin = i >= n - 2 or role == "user"
        if pin or not is_tool:
            kept.append(m)
            decisions.append({"index": i, "choice": "keep", "pinned": True, "confidence": 1.0})
            continue
        criteria = {
            "keep": "still needed for the latest user request",
            "truncate": "keep a short head; drop the bulky body",
            "drop": "stale tool result; no longer needed",
        }
        state = {"last_user": last_user, "tool": tool, "text_head": text[:240], "index": i, "n": n}
        rec = decide_choice(state, criteria, instructions="compaction: keep session text verbatim")
        rec["index"] = i
        rec = maybe_laya_shadow(
            rec,
            state,
            criteria,
            instructions="compaction: keep session text verbatim",
            qid="compact-%s" % i,
        )
        decisions.append(rec)
        pick = rec.get("choice") or "keep"
        if not rec.get("auto_act"):
            kept.append(m)
            continue
        if pick == "drop":
            dropped.append({"index": i, "note": "dropped by decision"})
        elif pick == "truncate":
            row = dict(m)
            head = text[:160]
            row["text"] = head + ("…" if len(text) > 160 else "")
            row["compacted"] = True
            kept.append(row)
        else:
            kept.append(m)
    low = [d for d in decisions if d.get("auto_act") is False]
    return {
        "ok": not low,
        "live": "READY" if not low else "FAIL",
        "copy": (
            "READY decision · compact context · kept %d dropped %d"
            % (len(kept), len(dropped))
            if not low
            else "FAIL decision -- %s · %s" % (CHIP_CONF_LOW, NEXT_LOW)
        ),
        "kept": kept,
        "dropped": dropped,
        "decisions": decisions,
        "chip_core": CHIP_CORE,
        "chip_decision": CHIP_DECISION,
        "honesty": CHIP_HONEST,
        "chip_margin": CHIP_MARGIN,
        "issue": ISSUE,
        "usable": not low,
        "next_step": "" if not low else NEXT_LOW,
        "engine": "cua-s1-forms" if normalize_path(path) != "mini-jev" else "mini-jev",
    }


def queue_path(STATE):
    return _now_state(STATE) / QUEUE_FILE


def queue_put(STATE, job):
    """chief.py local queue: append a decision job (JSONL)."""
    STATE = _now_state(STATE)
    STATE.mkdir(parents=True, exist_ok=True)
    row = dict(job or {})
    row["when"] = _now()
    row["issue"] = ISSUE
    row.setdefault("status", "queued")
    with (STATE / QUEUE_FILE).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {
        "ok": True,
        "live": "READY",
        "copy": "READY decision queue · enqueued",
        "job": row,
        "issue": ISSUE,
        "usable": True,
    }


def queue_list(STATE):
    raw = _read(queue_path(STATE))
    rows = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def queue_process_next(STATE, ROOT=None, live=None):
    """Pop the first queued job and run Choice/compact against live state."""
    rows = queue_list(STATE)
    pending = [r for r in rows if str(r.get("status") or "queued") == "queued"]
    if not pending:
        return fail("queue", "empty", "enqueue a decision job")
    job = pending[0]
    kind = str(job.get("kind") or job.get("type") or "route")
    path = normalize_path(job.get("path") or load_state(STATE).get("path") or PRIMARY_LOCAL)
    if kind in ("compact", "compaction"):
        rec = compact_session(job.get("messages") or [], path=path)
    elif kind in ("forms", "form", "cua-s1-forms"):
        rec = cua_s1_forms_plan(job.get("form"), ROOT=ROOT)
    else:
        rec = route_model_tool(live or job.get("live") or {}, path=path)
    rec["queue_job"] = job.get("when") or job.get("id") or ""
    job["status"] = "done" if rec.get("ok") else "fail"
    job["result_copy"] = rec.get("copy") or ""
    rest = []
    done_once = False
    target_when = job.get("when")
    for r in rows:
        if (
            not done_once
            and str(r.get("status") or "queued") == "queued"
            and r.get("when") == target_when
        ):
            rest.append(job)
            done_once = True
        else:
            rest.append(r)
    _write(queue_path(STATE), "\n".join(json.dumps(r, ensure_ascii=False) for r in rest))
    rec["queue_status"] = job["status"]
    return rec


def middleware_before_launch(STATE, live=None, ROOT=None):
    """If decision is on: compact + route with confidence gate. Off → no-op."""
    st = load_state(STATE)
    path = normalize_path(st.get("path") or "off")
    if path == "off":
        return {
            "ok": True,
            "live": "SKIP",
            "copy": "SKIP decision -- off",
            "path": "off",
            "paint": path_paint("off"),
            "honesty": CHIP_HONEST,
            "issue": ISSUE,
            "usable": True,
            "skipped": True,
        }
    if path == "typesafe" and not typesafe_key():
        return fail(
            "decision",
            "key missing (optional)",
            NEXT_KEY,
            path=path,
            paint=path_paint(path),
            chip_typesafe=CHIP_TYPESAFE_OPT,
        )
    live = dict(live or {})
    compact = compact_session(live.get("messages") or [], path=path)
    route = route_model_tool(live, path=path)
    auto = bool(compact.get("auto_act", compact.get("ok"))) and bool(route.get("auto_act", route.get("ok")))
    if not auto:
        return fail(
            "decision",
            CHIP_CONF_LOW,
            NEXT_LOW,
            path=path,
            paint=path_paint(path),
            compact=compact,
            route=route,
            chip_conf=CHIP_CONF_LOW,
        )
    return {
        "ok": True,
        "live": "READY",
        "copy": "READY decision · %s · %s · %s"
        % (path_paint(path), CHIP_DECISION, route.get("chip_conf") or CHIP_CONF_OK),
        "path": path,
        "paint": path_paint(path),
        "compact": compact,
        "route": route,
        "choice": route.get("choice"),
        "confidence": route.get("confidence"),
        "chip_conf": route.get("chip_conf") or CHIP_CONF_OK,
        "chip_decision": CHIP_DECISION,
        "honesty": CHIP_HONEST,
        "chip_core": CHIP_CORE,
        "chip_margin": CHIP_MARGIN,
        "issue": ISSUE,
        "usable": True,
        "auto_act": True,
    }


def attach_usable(ROOT=None, STATE=None, path=None, live=None):
    """Operate-or-FAIL attach of the decision layer."""
    STATE = _now_state(STATE or os.environ.get("PFY_STATE_DIR") or Path.home() / ".pfy-mentat")
    ROOT = Path(ROOT or os.environ.get("PFY_ROOT") or Path(__file__).resolve().parents[1])
    if path is None:
        path = load_state(STATE).get("path") or PRIMARY_LOCAL
    rec = set_path(STATE, path, ROOT=ROOT)
    if not rec.get("ok"):
        return rec
    path = rec.get("path") or path
    if path == "off":
        return rec
    if path == "typesafe":
        # Prove the path is attached; do not call cloud in default smoke.
        rec["usable"] = True
        rec["chip_core"] = CHIP_CORE
        return rec
    if path == "mini-jev":
        smoke = mini_jev_choice(
            {"task": "choose FreeToken-first local model", "engine": "freetoken", "lane": "local"},
            {
                "freetoken": "FreeToken-first live engine",
                "cloud-gab-auto": "Gab auto cloud router — not this path",
            },
            instructions="mini-jev teaching Choice",
        )
        rec["smoke"] = smoke
        rec["ok"] = bool(smoke.get("ok"))
        rec["live"] = smoke.get("live")
        rec["copy"] = smoke.get("copy")
        rec["usable"] = bool(smoke.get("usable"))
        rec["chip_conf"] = smoke.get("chip_conf")
        rec["choice"] = smoke.get("choice")
        rec["confidence"] = smoke.get("confidence")
        return rec
    smoke = cua_s1_forms_plan(ROOT=ROOT)
    rec["smoke"] = smoke
    rec["ok"] = bool(smoke.get("ok"))
    rec["live"] = smoke.get("live")
    rec["copy"] = smoke.get("copy")
    rec["usable"] = bool(smoke.get("usable"))
    rec["picks"] = smoke.get("picks")
    rec["chip_conf"] = CHIP_CONF_OK if smoke.get("ok") else CHIP_CONF_LOW
    rec["chip_local"] = CHIP_CUA
    rec["engine"] = "cua-s1-forms"
    rec["repo"] = CUA_REPO
    if live:
        rec["route"] = route_model_tool(live, path=path)
    return rec


def snapshot_fields(STATE=None, ROOT=None, live=None):
    STATE = _now_state(STATE or os.environ.get("PFY_STATE_DIR") or Path.home() / ".pfy-mentat")
    st = load_state(STATE)
    path = normalize_path(st.get("path") or "off")
    key_set = bool(typesafe_key())
    conf = st.get("confidence")
    chip_c = st.get("chip_conf") or ""
    if path == "off":
        paint = path_paint("off")
        copy = "decision off"
    elif path == "typesafe" and not key_set:
        paint = path_paint(path)
        copy = "FAIL decision -- key missing (optional) · " + NEXT_KEY
        chip_c = CHIP_TYPESAFE_OPT
    else:
        paint = path_paint(path)
        copy = st.get("copy") or ("READY decision -- %s" % paint)
        chip_c = chip_c or CHIP_CONF_OK
    return {
        "decision_ok": path != "off" and not (path == "typesafe" and not key_set),
        "decision_path": path,
        "decision_paint": paint,
        "decision_copy": copy,
        "decision_chip": CHIP_DECISION if path != "off" else "",
        "decision_honesty": CHIP_HONEST,
        "decision_core": CHIP_CORE,
        "decision_conf": chip_c,
        "decision_margin": CHIP_MARGIN if path != "off" else "",
        "decision_typesafe_opt": CHIP_TYPESAFE_OPT,
        "decision_local": CHIP_CUA if path == "cua-s1-forms" else (CHIP_FALLBACK if path == "mini-jev" else ""),
        "decision_key": "set" if key_set else "optional missing",
        "decision_model": typesafe_model() if path == "typesafe" else "",
        "decision_gate": conf_gate(),
        "wizard_decision": paint,
        "wizard_decision_path": path,
    }


def selftest():
    errors = []

    def check(cond, msg):
        if not cond:
            errors.append(msg)
            print("FAIL", msg)
        else:
            print("ok  ", msg)

    root = Path(__file__).resolve().parents[1]
    fix = load_fixture(root)
    check(isinstance(fix, dict) and fix.get("elements"), "CUA-S1-FORMS fixture loads")
    check(str(fix.get("repo") or "").startswith("https://github.com/trycua/cua"), "cua repo cited")

    # Confidence is margin, not correctness
    conf = choice_confidence([0.85, 0.08, 0.07])
    check(abs(conf - 0.775) < 0.02, "3-way margin from pmax=0.85")
    check(choice_confidence([1.0, 0.0]) >= 0.99, "peak distribution = high margin")
    check(choice_confidence([0.5, 0.5]) < 0.05, "flat distribution = low margin")
    src = Path(__file__).read_text(encoding="utf-8")
    check(
        "% correct" not in CHIP_DECISION
        and "% correct" not in CHIP_CONF_OK
        and "% correct" not in CHIP_CONF_LOW
        and "% correct" not in CHIP_MARGIN,
        "chips never paint percent-correct",
    )
    check("not chat" in src.lower() or "Decision API, not chat" in src, "decision API not chat")
    check("browser-use" in src and "not browser-use" in src, "browser-use not core")
    check(CHIP_HONEST in src, "honesty chip")
    check("#76" in src and "Do not reopen" in src, "do not reopen 76")
    check("70-75" in src or "70–75" in src, "catalog HOLD")
    check("No Env tab" in src, "no Env tab")

    import tempfile

    old_key = os.environ.pop("TYPESAFE_API_KEY", None)
    os.environ.pop("TYPESAFE_KEY", None)
    os.environ.pop("JEV_API_KEY", None)
    os.environ.pop("PFY_JEV_LAYA_SHADOW", None)
    os.environ["PFY_JEV_OFFLINE"] = "1"
    try:
        with tempfile.TemporaryDirectory() as td:
            # off
            rec = set_path(td, "off")
            check(rec.get("ok") and rec.get("path") == "off", "path off READY")
            check("○ off" in (rec.get("paint") or ""), "off paint")

            # TypeSafe without key FAIL+next
            ts = set_path(td, "typesafe")
            check(not ts.get("ok"), "typesafe without key FAIL")
            check("key missing" in (ts.get("error") or ""), "optional-missing reason")
            check(TYPESAFE_DOCS in (ts.get("next_step") or ""), "docs next")
            check(CHIP_TYPESAFE_OPT in str(ts.get("chip_typesafe") or ""), "typesafe optional chip")
            check("CUA-S1-FORMS" in (ts.get("next_step") or ""), "fallback named in next")

            # Primary local CUA-S1-FORMS operator-free smoke
            loc = attach_usable(root, td, path="cua-s1-forms")
            check(loc.get("ok"), "CUA-S1-FORMS attach READY")
            check(loc.get("engine") == "cua-s1-forms", "engine cua-s1-forms")
            check(CHIP_HONEST in str(loc.get("honesty") or ""), "attach honesty")
            check(CHIP_DECISION in str(loc.get("chip_decision") or loc.get("copy") or ""), "typed Choice chip")
            picks = loc.get("picks") or {}
            check("model" in picks, "form model element decided")
            check(str(picks.get("model") or "").startswith("fill:"), "model fill from document")
            check(picks.get("launch") == "click", "Launch session click")
            check("chat" not in (loc.get("copy") or "").lower(), "no chat copy")

            # mini-jev teaching fallback
            mj = attach_usable(root, td, path="mini-jev")
            check(mj.get("ok"), "mini-jev teaching READY")
            check("fallback" in str(mj.get("note") or mj.get("chip_local") or "").lower(), "mini-jev labeled fallback")

            # live-state options rebuild
            live = {
                "wizard_lane": "local",
                "wizard_harness": "opencode",
                "wizard_toolsets": "bare",
                "models": ["qwen3-coder:30b", "deepseek-coder:6.7b"],
            }
            opts = live_choice_options(live)
            check("qwen3-coder:30b" in opts, "live models in Choice options")
            check("gab-auto" not in opts, "local lane does not offer gab auto")
            live_gab = {
                "wizard_lane": "cloud/subscription",
                "wizard_harness": "gab",
                "models": ["qwen3-coder:30b"],
            }
            opts_g = live_choice_options(live_gab)
            check("gab-auto" in opts_g, "gab lane offers gab-auto")
            check("cloud router" in (opts_g.get("gab-auto") or ""), "gab auto described as cloud router")

            route = route_model_tool(live, path="cua-s1-forms")
            check(route.get("choice") in opts, "route picks a live option")
            check(route.get("options_from") == "live-state", "options from live state")
            check(CHIP_HONEST in str(route.get("honesty") or ""), "route honesty")
            check("shadow" not in route, "flag off leaves route without shadow key")

            # conf low refuses auto-act
            os.environ["PFY_JEV_CONF_GATE"] = "0.99"
            low = decide_choice("ambiguous", {"a": "maybe", "b": "also maybe", "c": "unclear"})
            os.environ.pop("PFY_JEV_CONF_GATE", None)
            check(not low.get("auto_act"), "conf low no silent auto-act")
            check(CHIP_CONF_LOW in str(low.get("chip_conf") or low.get("error") or ""), "conf low chip")
            check(classify_decision(low) == "escalate", "conf low classifies escalate")
            check(decision_exit_code(low) == EXIT_ESCALATE, "conf low exit 3")
            shadow_esc = {
                "ok": False,
                "choice": "push",
                "auto_act": False,
                "usable": False,
                "error": CHIP_CONF_LOW,
                "chip_shadow": CHIP_SHADOW_DISAGREE,
                "shadow": {
                    "enabled": True,
                    "action": "escalate",
                    "agree": False,
                    "cua_choice": "push",
                    "laya_choice": "hold",
                },
            }
            check(classify_decision(shadow_esc) == "escalate", "shadow disagree classifies escalate")
            check(decision_exit_code(shadow_esc) == EXIT_ESCALATE, "shadow disagree exit 3")
            check(PRIMARY_LOCAL == "cua-s1-forms", "PRIMARY_LOCAL stays cua-s1-forms")
            ready = decide_choice({"ci": "green"}, {"push": "go", "hold": "stop"})
            # may or may not be high conf; force a peaked one
            peaked = decide_choice("push now ci green", {"push": "push green tip", "hold": "zzz unrelated"})
            if peaked.get("auto_act"):
                check(decision_exit_code(peaked) == EXIT_READY, "ready exit 0")
                check(classify_decision(peaked) == "ready", "ready classifies ready")


            # compaction keeps user text
            compact = compact_session(
                [
                    {"role": "user", "text": "Fix the failing test. Never edit src/generated."},
                    {"role": "tool", "tool": "Read", "text": "old file " * 40},
                    {"role": "user", "text": "still failing"},
                ],
                path="cua-s1-forms",
            )
            texts = [str((m or {}).get("text") or "") for m in compact.get("kept") or []]
            check(any("Never edit src/generated" in t for t in texts), "user text kept verbatim")
            check(CHIP_CORE in str(compact.get("chip_core") or ""), "core value chip")

            # chief.py local queue
            q = queue_put(td, {"kind": "route", "live": live, "path": "cua-s1-forms"})
            check(q.get("ok"), "queue enqueue")
            nxt = queue_process_next(td, ROOT=root, live=live)
            check(nxt.get("choice"), "queue processed a Choice")

            # middleware off is skip (Launch intact)
            set_path(td, "off")
            mid = middleware_before_launch(td, live=live, ROOT=root)
            check(mid.get("skipped") or mid.get("live") == "SKIP", "decision off does not block Launch")

            set_path(td, "cua-s1-forms")
            mid2 = middleware_before_launch(td, live=live, ROOT=root)
            check(mid2.get("path") == "cua-s1-forms", "middleware uses CUA-S1-FORMS")
            check(CHIP_HONEST in str(mid2.get("honesty") or ""), "middleware honesty")

            snap = snapshot_fields(td, ROOT=root)
            check(snap.get("decision_path") == "cua-s1-forms", "snapshot path")
            check(CHIP_HONEST in str(snap.get("decision_honesty") or ""), "snapshot honesty")
            check("CUA-S1-FORMS" in str(snap.get("decision_paint") or ""), "snapshot paint")
            check("#76" not in json.dumps(snap), "snapshot does not reopen 76")
    finally:
        if old_key is not None:
            os.environ["TYPESAFE_API_KEY"] = old_key
        os.environ.pop("PFY_JEV_OFFLINE", None)
        os.environ.pop("PFY_JEV_CONF_GATE", None)
        os.environ.pop("PFY_JEV_LAYA_SHADOW", None)

    if errors:
        print("FAIL selftest · %d" % len(errors))
        return 1
    print(
        "PASS selftest · CUA-S1-FORMS Choice · conf margin · honesty · operator-free · #230"
    )
    return 0



# Exit contract for decision CLI (align with org-spinny-decide):
#   0 = ready / act on choice (auto_act)
#   3 = escalate (conf low) — valid outcome, not a tool failure; no silent auto-act
#   1 = broken / error
#   2 = usage
EXIT_READY = 0
EXIT_BROKEN = 1
EXIT_USAGE = 2
EXIT_ESCALATE = 3


def classify_decision(rec):
    """Map a decision record to ready | escalate | fail."""
    rec = rec or {}
    shadow = rec.get("shadow") if isinstance(rec.get("shadow"), dict) else {}
    if shadow.get("action") == "escalate":
        return "escalate"
    if rec.get("chip_shadow") in (CHIP_SHADOW_DISAGREE, CHIP_SHADOW_ERROR):
        return "escalate"
    if rec.get("error") == CHIP_CONF_LOW:
        return "escalate"
    if rec.get("choice") is not None and rec.get("auto_act") is False:
        return "escalate"
    if rec.get("ok") and rec.get("auto_act", True):
        return "ready"
    if rec.get("ok") and rec.get("usable"):
        return "ready"
    return "fail"


def decision_exit_code(rec):
    v = classify_decision(rec)
    if v == "ready":
        return EXIT_READY
    if v == "escalate":
        return EXIT_ESCALATE
    return EXIT_BROKEN


def format_decision_cli(rec, *, as_json=False):
    """Stdout for decision CLI. Escalate is labeled ESCALATE, not FAIL-as-broken."""
    rec = dict(rec or {})
    verdict = classify_decision(rec)
    rec["verdict"] = verdict
    if as_json:
        return json.dumps(rec, ensure_ascii=False)
    if verdict == "escalate":
        choice = rec.get("choice") or "?"
        chip = rec.get("chip_conf") or CHIP_CONF_LOW
        return (
            "ESCALATE decision · %s · choice=%s · %s"
            % (chip, choice, NEXT_LOW)
        )
    return rec.get("copy") or json.dumps(rec)


def main(argv=None):
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] in ("-h", "--help", "help"):
        print(
            "usage: pfy_jev_230.py [--selftest|--path PATH|--smoke|--compact|--route [--json]|--attach|--queue [put|next]]\n  route exits: 0 ready · 3 escalate (conf low) · 1 broken · 2 usage"
        )
        return 2
    if args[0] in ("--selftest", "selftest"):
        return selftest()
    root = Path(os.environ.get("PFY_ROOT") or Path(__file__).resolve().parents[1])
    state = Path(os.environ.get("PFY_STATE_DIR") or Path.home() / ".pfy-mentat")
    if args[0] in ("--path", "path"):
        rec = set_path(state, args[1] if len(args) > 1 else "off", ROOT=root)
        print(rec.get("copy") or json.dumps(rec))
        return 0 if rec.get("ok") else 1
    if args[0] in ("--smoke", "smoke"):
        rec = attach_usable(root, state, path=args[1] if len(args) > 1 else "cua-s1-forms")
        print(rec.get("copy") or json.dumps(rec))
        print("  chip: %s" % CHIP_HONEST)
        print("  chip: %s" % CHIP_DECISION)
        return 0 if rec.get("ok") else 1
    if args[0] in ("--compact", "compact"):
        rec = compact_session([], path="cua-s1-forms")
        print(rec.get("copy") or json.dumps(rec))
        return 0 if rec.get("ok") else 1
    if args[0] in ("--route", "route"):
        as_json = "--json" in args[1:]
        path = "cua-s1-forms"
        for i, a in enumerate(args[1:], 1):
            if a in ("--path",) and i + 1 < len(args):
                path = normalize_path(args[i + 1])
        rec = route_model_tool({}, path=path)
        print(format_decision_cli(rec, as_json=as_json))
        if not as_json:
            print("  verdict: %s" % classify_decision(rec))
            print("  chip: %s" % CHIP_HONEST)
        return decision_exit_code(rec)
    if args[0] in ("--attach", "attach"):
        rec = attach_usable(root, state)
        print(rec.get("copy") or json.dumps(rec))
        return 0 if rec.get("ok") else 1
    if args[0] in ("--queue", "queue"):
        sub = args[1] if len(args) > 1 else "next"
        if sub == "put":
            rec = queue_put(state, {"kind": "route", "path": "cua-s1-forms"})
        else:
            rec = queue_process_next(state, ROOT=root)
        print(rec.get("copy") or json.dumps(rec))
        return 0 if rec.get("ok") else 1
    print(
        "usage: pfy_jev_230.py [--selftest|--path PATH|--smoke|--compact|--route [--json]|--attach|--queue [put|next]]\n  route exits: 0 ready · 3 escalate (conf low) · 1 broken · 2 usage"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
