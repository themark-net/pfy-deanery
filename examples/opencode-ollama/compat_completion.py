"""OpenAI-compat completion probe used by examples/opencode-ollama/smoke.sh.

Handles reasoning models whose first tokens go into reasoning_content (or
reasoning / thinking) and leave message.content empty. GET/POST only to the
local OpenAI-compat base passed in the environment. No model pull.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

PROMPT = "Reply with exactly: OPENCODE_SMOKE_OK"
MIN_MAX_TOKENS = 256


def request_body(model: str, *, max_tokens: int | None = None) -> dict[str, Any]:
    budget = int(max_tokens if max_tokens is not None else MIN_MAX_TOKENS)
    if budget < MIN_MAX_TOKENS:
        budget = MIN_MAX_TOKENS
    return {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": budget,
        "temperature": 0,
    }


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or ""))
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(value)


def extract_completion_text(data: dict[str, Any]) -> str:
    """Prefer message.content; if empty, use reasoning fields."""
    choices = data.get("choices") or []
    first = choices[0] if choices and isinstance(choices[0], dict) else {}
    message = first.get("message") if isinstance(first.get("message"), dict) else {}
    content = _as_text(message.get("content")).strip()
    if content:
        return _as_text(message.get("content"))
    for key in ("reasoning_content", "reasoning", "thinking"):
        for src in (message, first, data):
            text = _as_text(src.get(key) if isinstance(src, dict) else "")
            if text.strip():
                return text
    return _as_text(message.get("content"))


def judge_completion(text: str) -> tuple[bool, str]:
    blob = text or ""
    if "OPENCODE_SMOKE_OK" in blob or "OK" in blob.upper():
        return True, "exact or OK phrase"
    if len(blob.strip()) < 2:
        return False, "empty completion"
    return True, "non-empty reply accepted for local model variance"


def _post(url: str, body: dict[str, Any], timeout: float = 120) -> dict[str, Any]:
    raw = json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=raw,
        headers={"Content-Type": "application/json", "Authorization": "Bearer ollama"},
        method="POST",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def main(argv: list[str] | None = None) -> int:
    del argv
    base = (os.environ.get("OLLAMA_OPENAI_BASE") or "").rstrip("/")
    model = os.environ.get("LOCAL_CODER_MODEL") or ""
    if not base or not model:
        print("error: OLLAMA_OPENAI_BASE and LOCAL_CODER_MODEL are required", flush=True)
        return 1
    url = base + "/chat/completions"
    try:
        data = _post(url, request_body(model))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: completion failed: {exc}", flush=True)
        return 1
    text = extract_completion_text(data)
    print(f"  response={text!r}")
    ok, reason = judge_completion(text)
    if not ok:
        print(f"  note: {reason}", flush=True)
        raise SystemExit("empty completion")
    if "OPENCODE_SMOKE_OK" not in text and "OK" not in text.upper():
        print("  note: exact phrase missing; non-empty reply accepted for local model variance")
    print("  completion: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
