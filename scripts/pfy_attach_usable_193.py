#!/usr/bin/env python3
"""Attach OpenCode developer-usable prove helpers -- cite #193."""
from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path


def openai_compat_root(base):
    """Strip trailing /v1 so probes are not /v1/v1/models. Same class as #187."""
    root = str(base or "").rstrip("/")
    if root.endswith("/v1"):
        root = root[:-3].rstrip("/")
    return root


def _recorded_model():
    """Model name stored for this state dir, if any. pinned-model, then ft-model."""
    root = os.environ.get("PFY_STATE_DIR", "").strip()
    if not root:
        return ""
    base = Path(root)
    for name in ("pinned-model", "ft-model"):
        path = base / name
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line
    return ""


def choose_smoke_model(models):
    """PFY_OLLAMA_MODEL, then LOCAL_CODER_MODEL, then the state pin, then models[0].

    The first name that is set is the choice. It must be on the live list.
    Returns (name, error). error is empty when name is usable.
    """
    listed = []
    for raw in models or []:
        name = str(raw).strip()
        if name and name not in listed:
            listed.append(name)
    picked = ""
    for key in ("PFY_OLLAMA_MODEL", "LOCAL_CODER_MODEL"):
        val = os.environ.get(key, "").strip()
        if val:
            picked = val
            break
    if not picked:
        picked = _recorded_model()
    if not picked and listed:
        picked = listed[0]
    if not picked:
        return "", "empty model name"
    if picked not in listed:
        return picked, "model %s not on live endpoint" % picked
    return picked, ""


def _reply_text(message, choice):
    """First non-empty reply field. Returns (field, text)."""
    if isinstance(message, dict):
        for key in ("content", "reasoning", "reasoning_content"):
            val = message.get(key)
            if val is None:
                continue
            text = val if isinstance(val, str) else str(val)
            if text.strip():
                return key, text.strip()
    if isinstance(choice, dict):
        text = choice.get("text") or ""
        if str(text).strip():
            return "text", str(text).strip()
    return "", ""


def prove_developer_usable(base, inspect_models):
    """List models + one smoke prompt against live base. Cite #193.

    Returns (ok, model_name, error, field). field is which message field
    carried the reply (content, reasoning, or reasoning_content). Fail means
    Attach must not paint attached. A reasoning model that leaves content
    empty still passes when reasoning or reasoning_content is non-empty.
    """
    root = openai_compat_root(base)
    models = []
    try:
        models = list(inspect_models(root) or [])
    except Exception as e:
        return False, "", "models list failed: %s" % str(e)[:200], ""
    if not models:
        return False, "", "no models on live endpoint", ""
    name, err = choose_smoke_model(models)
    if err:
        return False, name, err, ""
    url = root + "/v1/chat/completions"
    payload = json.dumps({
        "model": name,
        "messages": [{"role": "user", "content": "Reply with exactly: PFY_ATTACH_SMOKE_OK"}],
        "max_tokens": 256,
        "temperature": 0,
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer local",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode() or "{}")
    except Exception as e:
        return False, name, "smoke failed: %s" % str(e)[:200], ""
    field = ""
    text = ""
    try:
        choice = (data.get("choices") or [{}])[0]
        if not isinstance(choice, dict):
            choice = {}
        msg = choice.get("message") or {}
        field, text = _reply_text(msg, choice)
    except Exception:
        field, text = "", ""
    if not text:
        return False, name, "smoke empty completion", ""
    return True, name, "", field


def fail_not_usable(clear_session_reach, STATE, hid, reason, next_step, engine, status, base="", model=""):
    clear_session_reach(STATE)
    attach_base_path = Path(STATE) / "opencode-attach-base"
    try:
        if attach_base_path.is_file():
            attach_base_path.unlink()
    except OSError:
        pass
    copy = "FAIL attach -- %s \u00b7 %s" % (reason, next_step)
    return {
        "ok": False,
        "id": hid,
        "live": "FAIL",
        "copy": copy,
        "error": reason,
        "session_reach": "FAIL",
        "next_step": next_step,
        "next_steps": [{"id": "next", "label": next_step, "value": next_step}],
        "engine": engine,
        "detect_status": status or "missing",
        "base_url": base,
        "model": model,
        "usable": False,
    }


SESSION_REACH_USABLE = "terminal \u00b7 OpenCode \u00b7 models \u00b7 smoke"
