#!/usr/bin/env python3
"""Fixed-prompt bench of one OpenAI-compatible local engine. Stdlib only.

Hits /v1/chat/completions with temperature 0 and streaming. Records time to
first token, wall time, prompt tok/s, decode tok/s, and whether the reply is
usable. Does not start or stop a server. Does not load a second engine.

Decode tok/s uses completion tokens after the first, over the time from the
first token to the end of the stream. Prompt tok/s is prompt_tokens / TTFT.
The median of a metric is the middle of the per-run values for that prompt,
and the engine median is the middle of every run of that metric.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request


SHORT_CODE = (
    "Write a Python function named add that takes two numbers and returns their sum. "
    "Output only the function."
)
SHORT_CODE_2 = (
    "Write a bash one-liner that prints how many lines are in a file named notes.txt. "
    "Output only the command."
)
CHAT_1 = "In one sentence, what is a hash map?"
CHAT_2 = "Name three primary colors, separated by commas, and nothing else."
TOOL_USER = "What is the weather in Lisbon? You must call the get_weather tool."
TOOL = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get the current weather for a city.",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "City name"}},
            "required": ["city"],
        },
    },
}

# About 4k tokens: the word "token" plus a space is one token on these BPE models,
# and the instruction is a few dozen more. usage.prompt_tokens is the real count.
LONG_BODY = ("token " * 4000).strip()
LONG_USER = (
    "The following text is a prompt-speed sample. Reply with exactly the word OK.\n\n" + LONG_BODY
)


def prompts():
    return [
        {"id": "code-1", "kind": "code", "max_tokens": 128, "user": SHORT_CODE, "tools": None},
        {"id": "code-2", "kind": "code", "max_tokens": 128, "user": SHORT_CODE_2, "tools": None},
        {"id": "chat-1", "kind": "chat", "max_tokens": 128, "user": CHAT_1, "tools": None},
        {"id": "chat-2", "kind": "chat", "max_tokens": 64, "user": CHAT_2, "tools": None},
        {"id": "tool-1", "kind": "tool", "max_tokens": 256, "user": TOOL_USER, "tools": [TOOL]},
        {"id": "long-4k", "kind": "long", "max_tokens": 64, "user": LONG_USER, "tools": None},
    ]


def _median(values):
    nums = [v for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    return statistics.median(nums)


def _text_of(delta, message):
    parts = []
    for src in (delta, message):
        if not isinstance(src, dict):
            continue
        for key in ("content", "reasoning", "reasoning_content"):
            val = src.get(key)
            if isinstance(val, str) and val:
                parts.append(val)
    return "".join(parts)


def _merge_tool_calls(into, delta_calls):
    if not isinstance(delta_calls, list):
        return
    for i, call in enumerate(delta_calls):
        if not isinstance(call, dict):
            continue
        idx = call.get("index")
        if not isinstance(idx, int):
            idx = i
        slot = into.setdefault(idx, {"id": "", "name": "", "arguments": ""})
        if call.get("id"):
            slot["id"] = str(call["id"])
        fn = call.get("function") if isinstance(call.get("function"), dict) else {}
        if fn.get("name"):
            slot["name"] += str(fn["name"])
        args = fn.get("arguments")
        if isinstance(args, str):
            slot["arguments"] += args
        elif isinstance(args, dict):
            slot["arguments"] = json.dumps(args)


def _tool_ok(calls):
    if not calls:
        return False, "no tool call"
    call = calls[0]
    name = (call.get("name") or "").strip()
    if name != "get_weather":
        return False, "tool name %s" % (name or "(empty)")
    raw = call.get("arguments") or ""
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError:
        return False, "arguments are not JSON"
    if not isinstance(parsed, dict):
        return False, "arguments are not a JSON object"
    return True, ""


def _chat_url(base):
    root = base.rstrip("/")
    if root.endswith("/v1"):
        return root + "/chat/completions"
    return root + "/v1/chat/completions"


def run_once(base, model, item, timeout, keep_alive):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": item["user"]}],
        "temperature": 0,
        "max_tokens": item["max_tokens"],
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    if item["tools"]:
        body["tools"] = item["tools"]
        body["tool_choice"] = "required"
    if keep_alive:
        body["keep_alive"] = keep_alive
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        _chat_url(base),
        data=data,
        headers={"Content-Type": "application/json", "Authorization": "Bearer local"},
        method="POST",
    )
    started = time.perf_counter()
    first = None
    usage = {}
    text_parts = []
    tool_slots = {}
    raw_error = ""
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            while True:
                line = resp.readline()
                if not line:
                    break
                s = line.decode("utf-8", "replace").strip()
                if not s or not s.startswith("data:"):
                    continue
                payload = s[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    event = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if isinstance(event.get("usage"), dict):
                    usage = event["usage"]
                choices = event.get("choices") or []
                if not choices or not isinstance(choices[0], dict):
                    continue
                choice = choices[0]
                delta = choice.get("delta") if isinstance(choice.get("delta"), dict) else {}
                message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
                piece = _text_of(delta, message)
                calls = delta.get("tool_calls") or message.get("tool_calls")
                if piece or calls:
                    if first is None:
                        first = time.perf_counter()
                if piece:
                    text_parts.append(piece)
                _merge_tool_calls(tool_slots, calls)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        raw_error = "HTTP %s %s" % (exc.code, detail)
    except Exception as exc:
        raw_error = "%s: %s" % (type(exc).__name__, exc)
    ended = time.perf_counter()
    calls = [tool_slots[k] for k in sorted(tool_slots)]
    text = "".join(text_parts).strip()
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    ttft = (first - started) if first is not None else None
    wall = ended - started
    decode_span = (ended - first) if first is not None else None
    prompt_tok_s = None
    decode_tok_s = None
    if isinstance(prompt_tokens, int) and ttft and ttft > 0:
        prompt_tok_s = prompt_tokens / ttft
    if isinstance(completion_tokens, int) and decode_span and decode_span > 0 and completion_tokens > 1:
        decode_tok_s = (completion_tokens - 1) / decode_span
    if item["kind"] == "tool":
        ok, why = _tool_ok(calls)
    else:
        ok = bool(text) or (isinstance(completion_tokens, int) and completion_tokens > 0 and not raw_error)
        why = "" if ok else (raw_error or "empty completion")
    if raw_error and item["kind"] == "tool":
        ok = False
        why = raw_error
    return {
        "id": item["id"],
        "kind": item["kind"],
        "ttft_s": ttft,
        "wall_s": wall,
        "decode_span_s": decode_span,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "prompt_tok_s": prompt_tok_s,
        "decode_tok_s": decode_tok_s,
        "valid": bool(ok) and not raw_error,
        "valid_reason": why if not ok else "",
        "error": raw_error,
        "text_head": text[:180],
        "tool_calls": [{"name": c["name"], "arguments": c["arguments"][:300]} for c in calls],
    }


def summarize(runs):
    by_id = {}
    for run in runs:
        by_id.setdefault(run["id"], []).append(run)
    prompts_out = []
    for pid, group in by_id.items():
        prompts_out.append({
            "id": pid,
            "kind": group[0]["kind"],
            "n": len(group),
            "valid": sum(1 for g in group if g["valid"]),
            "median_ttft_s": _median([g["ttft_s"] for g in group]),
            "median_wall_s": _median([g["wall_s"] for g in group]),
            "median_prompt_tok_s": _median([g["prompt_tok_s"] for g in group]),
            "median_decode_tok_s": _median([g["decode_tok_s"] for g in group]),
            "median_prompt_tokens": _median([g["prompt_tokens"] for g in group]),
        })
    return {
        "median_ttft_s": _median([r["ttft_s"] for r in runs]),
        "median_wall_s": _median([r["wall_s"] for r in runs]),
        "median_prompt_tok_s": _median([r["prompt_tok_s"] for r in runs]),
        "median_decode_tok_s": _median([r["decode_tok_s"] for r in runs]),
        "valid_runs": sum(1 for r in runs if r["valid"]),
        "runs": len(runs),
        "prompts": prompts_out,
    }


def main(argv):
    ap = argparse.ArgumentParser(description="Bench one OpenAI-compatible local engine.")
    ap.add_argument("--base", required=True, help="Engine origin or /v1 base URL")
    ap.add_argument("--model", required=True)
    ap.add_argument("--engine", required=True, help="Label stored in the result, for example ollama or strata")
    ap.add_argument("--out", required=True)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--keep-alive", default="", help="Ollama keep_alive value. Empty omits the field.")
    ap.add_argument("--only", default="", help="Comma-separated prompt ids. Default is every prompt.")
    args = ap.parse_args(argv)
    wanted = {p for p in args.only.split(",") if p} if args.only else set()
    items = [p for p in prompts() if not wanted or p["id"] in wanted]
    if not items:
        print("no prompts selected", file=sys.stderr)
        return 2
    runs = []
    for n in range(args.runs):
        for item in items:
            print("run %s/%s %s" % (n + 1, args.runs, item["id"]), flush=True)
            rec = run_once(args.base, args.model, item, args.timeout, args.keep_alive.strip())
            rec["run"] = n + 1
            runs.append(rec)
            print(
                "  valid=%s ttft=%s decode=%s prompt_tok_s=%s wall=%.2f prompt_tokens=%s"
                % (
                    rec["valid"],
                    None if rec["ttft_s"] is None else round(rec["ttft_s"], 3),
                    None if rec["decode_tok_s"] is None else round(rec["decode_tok_s"], 2),
                    None if rec["prompt_tok_s"] is None else round(rec["prompt_tok_s"], 1),
                    rec["wall_s"],
                    rec["prompt_tokens"],
                ),
                flush=True,
            )
            if rec["error"]:
                print("  error: %s" % rec["error"][:240], flush=True)
    summary = summarize(runs)
    out = {
        "engine": args.engine,
        "base": args.base,
        "model": args.model,
        "runs_each": args.runs,
        "temperature": 0,
        "summary": summary,
        "runs": runs,
    }
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
        fh.write("\n")
    med = summary
    print(
        "MEDIAN %s decode_tok_s=%s prompt_tok_s=%s ttft_s=%s wall_s=%s valid=%s/%s"
        % (
            args.engine,
            med["median_decode_tok_s"],
            med["median_prompt_tok_s"],
            med["median_ttft_s"],
            med["median_wall_s"],
            med["valid_runs"],
            med["runs"],
        )
    )
    if not med["runs"] or med["valid_runs"] != med["runs"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
