#!/usr/bin/env python3
"""Kolibri-1 operate-or-FAIL smoke (Entry 085). Stdlib only.

Backend: any OpenAI-compatible endpoint serving Kolibri-1.
  * KOLIBRI_BASE_URL set  -> use it (vLLM + aleph-alpha-inference, hosted, ...). Optional KOLIBRI_API_KEY_ENV
    names the env var holding the key (value is never printed). KOLIBRI_MODEL picks the model id.
  * else localhost:$KOLIBRI_PORT if already up
  * else start examples/kolibri1-llamacpp/serve.sh (patched llama.cpp + community GGUF) and wait for /health.

Three checks: English (expects "Paris"), German (expects "391"), and a tool call (expects get_weather + Berlin).
Writes pipelines/smoke/kolibri1/latest.json every time, PASS or FAIL.
Exit 0 = all PASS. 1 = backend answered but a check failed. 2 = no backend (prereq FAIL, reason recorded).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RECEIPT = ROOT / "pipelines/smoke/kolibri1/latest.json"


def env_paths() -> dict:
    out = subprocess.run(["bash", "-c", f"source '{HERE}/env.sh' && env"], capture_output=True, text=True).stdout
    return dict(l.split("=", 1) for l in out.splitlines() if l.startswith(("KOLIBRI_", "PFY_MAIN_ROOT")))


def http(url: str, body: dict | None = None, key: str | None = None, timeout: float = 600) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    if key:
        req.add_header("Authorization", "Bearer " + key)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def up(base: str) -> bool:
    try:
        http(base.rsplit("/v1", 1)[0] + "/health", timeout=3)
        return True
    except Exception:
        try:
            http(base + "/models", timeout=3)
            return True
        except Exception:
            return False


def write(receipt: dict, code: int) -> int:
    override = os.environ.get("PFY_SMOKE_RECEIPT_DIR")
    if override:
        dest = Path(override)
        if not dest.is_absolute():
            print("PFY_SMOKE_RECEIPT_DIR must be absolute")
            return 1
        path = dest / "latest.json"
    else:
        path = RECEIPT
    receipt["exit_code"] = code
    receipt["verdict"] = {0: "PASS", 1: "FAIL", 2: "FAIL_NO_BACKEND"}[code]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: receipt[k] for k in ("verdict", "backend", "reason") if k in receipt}, ensure_ascii=False))
    print(f"receipt: {path}")
    return code


def main() -> int:
    e = env_paths()
    receipt: dict = {"model": "Aleph-Alpha/Kolibri-1", "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                     "host": os.uname().nodename, "checks": []}
    key = os.environ.get(os.environ["KOLIBRI_API_KEY_ENV"]) if os.environ.get("KOLIBRI_API_KEY_ENV") else None
    base = os.environ.get("KOLIBRI_BASE_URL")
    model = os.environ.get("KOLIBRI_MODEL", "Kolibri-1-Q3_K_S")
    proc = None
    if base:
        receipt["backend"] = f"remote:{base}"
        if not up(base):
            receipt["reason"] = f"KOLIBRI_BASE_URL {base} not reachable"
            return write(receipt, 2)
    else:
        base = f"http://127.0.0.1:{e.get('KOLIBRI_PORT', '8081')}/v1"
        receipt["backend"] = f"llama.cpp-kolibri1-patch:{e.get('KOLIBRI_BACKEND')} {e.get('KOLIBRI_GGUF')}"
        if not up(base):
            srv, gguf = Path(e["KOLIBRI_LLAMA_SERVER"]), Path(e["KOLIBRI_GGUF"])
            want = int(e.get("KOLIBRI_GGUF_BYTES") or 33870242400)
            have = gguf.stat().st_size if gguf.exists() else 0
            parts = gguf.parent / "parts"
            if parts.is_dir():
                have = max(have, sum(p.stat().st_size for p in parts.iterdir()))
            if not os.access(srv, os.X_OK):
                receipt["reason"] = (f"no patched llama-server at {srv}; stock llama.cpp/Ollama lack the kolibri1 arch "
                                     "(ggml-org/llama.cpp#29922). Run examples/kolibri1-llamacpp/build.sh")
                return write(receipt, 2)
            if not gguf.exists() or gguf.stat().st_size != want:
                receipt["reason"] = (f"GGUF incomplete: {have}/{want} bytes ({100*have/want:.1f}%) at {gguf}. "
                                     "Official FP8 weights need >=2x A100 80GB / 1x H200 (no NVIDIA GPU here). "
                                     "Run examples/kolibri1-llamacpp/download.sh")
                return write(receipt, 2)
            log = open(RECEIPT.parent.mkdir(parents=True, exist_ok=True) or RECEIPT.parent / "server.log", "w")
            proc = subprocess.Popen([str(HERE / "serve.sh")], stdout=log, stderr=subprocess.STDOUT)
            t0 = time.time()
            deadline = t0 + float(os.environ.get("KOLIBRI_LOAD_TIMEOUT", "1200"))
            while time.time() < deadline and proc.poll() is None and not up(base):
                time.sleep(3)
            receipt["load_seconds"] = round(time.time() - t0, 1)
            if not up(base):
                proc.kill()
                tail = (RECEIPT.parent / "server.log").read_text(errors="replace")[-1500:]
                receipt["reason"] = f"llama-server failed to come up (rc={proc.poll()}); log tail: {tail}"
                return write(receipt, 2)
    try:
        def chat(messages, **kw):
            body = {"model": model, "messages": messages, "max_tokens": kw.pop("max_tokens", 256),
                    "temperature": 1.0, "top_p": 0.97, "top_k": 128,
                    "reasoning_effort": "none", "chat_template_kwargs": {"reasoning_effort": "none"}, **kw}
            t = time.time()
            r = http(base + "/chat/completions", body, key)
            return r, round(time.time() - t, 2)

        tool = {"type": "function", "function": {"name": "get_weather", "description": "Current weather for a city",
                "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}
        cases = [
            ("english", [{"role": "user", "content": "What is the capital of France? Answer with one word."}], {},
             lambda m: "paris" in (m.get("content") or "").lower()),
            ("german", [{"role": "user", "content": "Wie viel ist 17 mal 23? Antworte kurz auf Deutsch."}], {},
             lambda m: "391" in (m.get("content") or "")),
            ("tool_call", [{"role": "user", "content": "Wie ist das Wetter gerade in Berlin? Nutze das Tool."}],
             {"tools": [tool], "tool_choice": "auto"},
             lambda m: any(c.get("function", {}).get("name") == "get_weather"
                           and "berlin" in c["function"].get("arguments", "").lower()
                           for c in (m.get("tool_calls") or []))),
        ]
        ok = True
        for name, msgs, kw, check in cases:
            try:
                r, dt = chat(msgs, **kw)
                m = r["choices"][0]["message"]
                passed = bool(check(m))
                receipt["checks"].append({"name": name, "pass": passed, "latency_s": dt, "usage": r.get("usage"),
                                          "content": (m.get("content") or "")[:400],
                                          "tool_calls": m.get("tool_calls")})
            except Exception as ex:  # noqa: BLE001
                passed = False
                receipt["checks"].append({"name": name, "pass": False, "error": repr(ex)[:400]})
            ok &= passed
            print(f"{'PASS' if passed else 'FAIL'} {name} {receipt['checks'][-1].get('latency_s', '-')}s")
        if not ok:
            receipt["reason"] = "one or more checks failed: " + ",".join(c["name"] for c in receipt["checks"] if not c["pass"])
        return write(receipt, 0 if ok else 1)
    finally:
        if proc:
            proc.terminate()


if __name__ == "__main__":
    sys.exit(main())
