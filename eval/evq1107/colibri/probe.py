#!/usr/bin/env python3
"""Short localhost probe for one OpenAI-compatible server or for Ollama.

Reads two prompts about this repo. Scores an exact first-line match.
Decode tok/s is (completion_tokens - 1) / seconds from the first content
byte to the last content byte. No network except the base URL you pass.
"""

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request

SYS = "Reply with only the requested token. No extra words."

PROMPTS = [
    {
        "id": "stage",
        "expect": "I2",
        "max_tokens": 16,
        "user": (
            "The integration stage table in this repo says: "
            "I0 Awareness, I1 Staged evaluation, I2 Ad-hoc probe, "
            "I3 Onboard, I4 Embedded. "
            "Reply with only the stage id for Ad-hoc probe."
        ),
    },
    {
        "id": "lock",
        "expect": "PFY_MODEL_LOCK_HELD",
        "max_tokens": 24,
        "user": (
            "In scripts/model_lock.sh a nested call sees "
            "PFY_MODEL_LOCK_HELD=1 and does not take the lock again. "
            "Reply with only the environment variable name that marks "
            "the lock as already held."
        ),
    },
]


def first_line(text):
    raw = (text or "").strip()
    if not raw:
        return ""
    line = raw.splitlines()[0].strip()
    return line.strip("`\"' .,")


def median(values):
    nums = [v for v in values if isinstance(v, (int, float))]
    if not nums:
        return None
    return statistics.median(nums)


def post(url, payload, timeout):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    t0 = time.perf_counter()
    t_first = None
    t_last = None
    parts = []
    usage = None
    extra = {}
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            now = time.perf_counter()
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            body = line
            if body.startswith("data:"):
                body = body[5:].strip()
                if body == "[DONE]":
                    break
            try:
                event = json.loads(body)
            except json.JSONDecodeError:
                continue
            if event.get("usage"):
                usage = event["usage"]
            if event.get("done") is True:
                extra = {
                    "eval_count": event.get("eval_count"),
                    "eval_duration_ns": event.get("eval_duration"),
                    "prompt_eval_count": event.get("prompt_eval_count"),
                    "prompt_eval_duration_ns": event.get("prompt_eval_duration"),
                }
            content = ""
            choices = event.get("choices") or []
            if choices:
                delta = choices[0].get("delta") or {}
                content = delta.get("content") or ""
            message = event.get("message") or {}
            if message.get("content"):
                content = message.get("content") or ""
            if content:
                if t_first is None:
                    t_first = now
                t_last = now
                parts.append(content)
    text = "".join(parts)
    elapsed = time.perf_counter() - t0
    prompt_tokens = None
    completion_tokens = None
    if isinstance(usage, dict):
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
    if completion_tokens is None and extra.get("eval_count") is not None:
        completion_tokens = extra["eval_count"]
    if prompt_tokens is None and extra.get("prompt_eval_count") is not None:
        prompt_tokens = extra["prompt_eval_count"]
    ttft = None if t_first is None else t_first - t0
    decode = None
    if (
        isinstance(completion_tokens, int)
        and completion_tokens > 1
        and t_first is not None
        and t_last is not None
        and t_last > t_first
    ):
        decode = (completion_tokens - 1) / (t_last - t_first)
    prompt_tps = None
    if isinstance(prompt_tokens, int) and prompt_tokens > 0 and ttft and ttft > 0:
        prompt_tps = prompt_tokens / ttft
    official = None
    if extra.get("eval_count") and extra.get("eval_duration_ns"):
        official = extra["eval_count"] / (extra["eval_duration_ns"] / 1e9)
    return {
        "text": text,
        "line": first_line(text),
        "wall_s": elapsed,
        "ttft_s": ttft,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "decode_tps": decode,
        "prompt_tps": prompt_tps,
        "engine_decode_tps": official,
        "usage": usage,
    }


def openai_payload(model, user, max_tokens):
    return {
        "model": model,
        "messages": [
            {"role": "system", "content": SYS},
            {"role": "user", "content": user},
        ],
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": 0,
        "max_tokens": max_tokens,
    }


def ollama_payload(model, user, max_tokens, keep_alive):
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYS},
            {"role": "user", "content": user},
        ],
        "stream": True,
        "think": False,
        "options": {"temperature": 0, "num_predict": max_tokens},
    }
    if keep_alive:
        body["keep_alive"] = keep_alive
    return body


def run_one(api, url, model, prompt, timeout, keep_alive):
    if api == "openai":
        payload = openai_payload(model, prompt["user"], prompt["max_tokens"])
    else:
        payload = ollama_payload(model, prompt["user"], prompt["max_tokens"], keep_alive)
    row = post(url, payload, timeout)
    row["id"] = prompt["id"]
    row["expect"] = prompt["expect"]
    row["ok"] = row["line"] == prompt["expect"]
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", choices=("openai", "ollama"), required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--runs", type=int, default=2)
    parser.add_argument("--keep-alive", default="")
    parser.add_argument("--skip-warmup", action="store_true")
    args = parser.parse_args()

    rows = []
    warmup = None
    if not args.skip_warmup:
        warm = dict(PROMPTS[0], max_tokens=8)
        t0 = time.perf_counter()
        try:
            warmup = run_one(args.api, args.url, args.model, warm, args.timeout, args.keep_alive)
        except Exception as exc:
            warmup = {"error": str(exc)}
        warmup["wall_including_error_s"] = time.perf_counter() - t0
        warmup["scored"] = False

    for prompt in PROMPTS:
        for run in range(1, args.runs + 1):
            try:
                row = run_one(
                    args.api, args.url, args.model, prompt, args.timeout, args.keep_alive
                )
            except Exception as exc:
                row = {
                    "id": prompt["id"],
                    "expect": prompt["expect"],
                    "ok": False,
                    "error": str(exc),
                }
            row["run"] = run
            row["scored"] = True
            rows.append(row)
            print(
                "%s run %d ok=%s decode=%s line=%r"
                % (
                    row.get("id"),
                    run,
                    row.get("ok"),
                    row.get("decode_tps"),
                    row.get("line", row.get("error")),
                ),
                flush=True,
            )

    scored = [r for r in rows if r.get("scored")]
    summary = {
        "api": args.api,
        "url": args.url,
        "model": args.model,
        "scored": len(scored),
        "ok": sum(1 for r in scored if r.get("ok")),
        "decode_tps_median": median([r.get("decode_tps") for r in scored]),
        "prompt_tps_median": median([r.get("prompt_tps") for r in scored]),
        "ttft_s_median": median([r.get("ttft_s") for r in scored]),
        "wall_s_median": median([r.get("wall_s") for r in scored]),
        "engine_decode_tps_median": median([r.get("engine_decode_tps") for r in scored]),
    }
    doc = {"summary": summary, "warmup": warmup, "runs": rows}
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(doc, handle, indent=2)
        handle.write("\n")
    print(json.dumps(summary), flush=True)
    if any(row.get("error") for row in scored):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
