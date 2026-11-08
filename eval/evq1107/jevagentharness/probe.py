#!/usr/bin/env python3
"""On-repo probe for JevAgentHarness.

offline: rules router against a loopback stub. No model.
live: the same four agent steps, strong and fast tiers on local Ollama.
The live command must run under scripts/model_lock.sh.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent
RESULTS = OUT_DIR / "results.json"
CACHE = Path.home() / ".cache/pfy/tools/jevagentharness"
JAH = Path(os.environ.get("JAH_BIN", str(CACHE / "venv/bin/jah")))
SRC = CACHE / "src/JevAgentHarness"
STRONG = "qwen2.5-coder:7b-instruct"
FAST = "qwen2.5-coder:1.5b"
OLLAMA = "http://127.0.0.1:11434"
FLOOR_EXTRA = 25 * 1024**3
WAIT_S = 30 * 60
MARKER = "PFY-JAH-OLLAMA-STAGE"

# Hand labels for the rules backend on this scripted trace.
# Step 3 is routed routine, then verify_finish rewrites a text answer to strong.
HAND_FIRST = ["strong", "fast", "strong", "fast"]
HAND_WHY = [None, "no_signal", "error_signal", "no_signal"]


def stop_requested() -> bool:
    return (ROOT / "tmp/STOP").exists()


def load_results() -> dict:
    if RESULTS.exists():
        return json.loads(RESULTS.read_text())
    return {}


def save_results(doc: dict) -> None:
    RESULTS.write_text(json.dumps(doc, indent=2) + "\n")


def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def mem_available() -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("MemAvailable missing")


def stage_token() -> str:
    text = (ROOT / "data/stages/ollama.json").read_text()
    key = '"integration_stage"'
    at = text.find(key)
    if at < 0:
        raise RuntimeError("ollama card has no integration_stage")
    chunk = text[at:at + 80]
    quote = chunk.split('"')
    # "integration_stage" : "I2"
    if len(quote) < 4:
        raise RuntimeError("cannot parse integration_stage")
    return quote[3]


def tool_outputs(token: str) -> list[str]:
    # One line only, so a later edit that adds the word "failed" elsewhere
    # does not flip the routine fixture.
    line = ""
    for row in (ROOT / "data/stages/ollama.json").read_text().splitlines():
        if '"integration_stage"' in row:
            line = row.strip()
            break
    if token not in line:
        raise RuntimeError("stage line lost the token")
    hard = (
        "Traceback (most recent call last):\n"
        '  File "data/stages/ollama.json", line 3, in read\n'
        "AssertionError: 1 failed\n"
    )
    done = "exit code 0\nintegration_stage " + token + "\nALLDONE\n"
    return [line, hard, done]


def dir_bytes(path: Path) -> int:
    total = 0
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        for name in filenames:
            try:
                total += (Path(dirpath) / name).stat().st_size
            except OSError:
                pass
    return total


def pin_meta() -> dict:
    commit = subprocess.check_output(["git", "-C", str(SRC), "rev-parse", "HEAD"], text=True).strip()
    pyproject = (SRC / "pyproject.toml").read_bytes()
    version = subprocess.check_output([str(JAH), "--version"], text=True).strip()
    return {
        "commit": commit,
        "jah_version": version,
        "pyproject_sha256": hashlib.sha256(pyproject).hexdigest(),
        "src_bytes_without_git": dir_bytes(SRC),
        "jah_bin": str(JAH),
    }


def compact_steps(log_dir: Path) -> list[dict]:
    path = log_dir / "steps.jsonl"
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("kind") == "cache" or "step" not in rec:
            continue
        calls = rec.get("calls") or []
        decision = rec.get("decision") or {}
        rows.append({
            "step": rec.get("step"),
            "tier": rec.get("tier"),
            "reason": rec.get("reason"),
            "why": decision.get("why"),
            "p_hard": rec.get("p_hard"),
            "decision_error": decision.get("error"),
            "call_tiers": [call.get("tier") for call in calls],
            "call_models": [call.get("model") for call in calls],
            "call_latency_s": [call.get("latency_s") for call in calls],
            "latency_s": rec.get("latency_s"),
            "finish_check": bool(rec.get("finish_check")),
        })
    return rows


def leak_names(log_dir: Path) -> list[str]:
    found = []
    if not log_dir.exists():
        return found
    for path in log_dir.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(errors="replace")
        if MARKER in text:
            found.append(path.name)
    return found


def call_counts(steps: list[dict]) -> dict:
    strong = fast = 0
    for step in steps:
        for tier in step["call_tiers"]:
            if tier == "strong":
                strong += 1
            elif tier == "fast":
                fast += 1
    return {"strong_calls": strong, "fast_calls": fast, "upstream_calls": strong + fast}


def first_tiers(steps: list[dict]) -> list[str]:
    out = []
    for step in steps:
        tiers = step["call_tiers"]
        out.append(tiers[0] if tiers else "")
    return out


class StubUpstream(BaseHTTPRequestHandler):
    calls: list[dict] = []

    def log_message(self, fmt: str, *args) -> None:
        return None

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        messages = body.get("messages") or []
        last = messages[-1].get("content") if messages else ""
        model = body.get("model")
        StubUpstream.calls.append({
            "model": model,
            "auth": bool(self.headers.get("Authorization")),
        })
        if isinstance(last, str) and "ALLDONE" in last:
            message = {"role": "assistant", "content": "done by " + str(model)}
        else:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "c%d" % len(StubUpstream.calls),
                    "type": "function",
                    "function": {"name": "bash", "arguments": '{"cmd":"stub"}'},
                }],
            }
        payload = {
            "id": "x",
            "object": "chat.completion",
            "model": model,
            "choices": [{
                "index": 0,
                "message": message,
                "finish_reason": "stop" if message.get("content") else "tool_calls",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class DecisionAdapter(BaseHTTPRequestHandler):
    """POST /v1/systemone. Asks the fast Ollama model for one word."""

    keep_alive: str | None = "2m"
    calls: list[dict] = []

    def log_message(self, fmt: str, *args) -> None:
        return None

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = json.loads(self.rfile.read(length) or b"{}")
        auth = bool(self.headers.get("Authorization"))
        questions = body.get("questions") or {}
        question = questions.get("next_step") or next(iter(questions.values()), {})
        instructions = str(question.get("instructions") or "")[:800]
        state = str(body.get("state") or "")[-1800:]
        prompt = instructions + "\n\nReply with one word: routine or hard.\n\n" + state
        started = time.perf_counter()
        choice, error = ask_word(prompt, DecisionAdapter.keep_alive)
        elapsed = round(time.perf_counter() - started, 3)
        DecisionAdapter.calls.append({
            "path": self.path,
            "model": body.get("model"),
            "auth": auth,
            "choice": choice,
            "error": error,
            "latency_s": elapsed,
        })
        if choice not in ("routine", "hard"):
            raw = json.dumps({"error": error or "no choice"}).encode()
            self.send_response(400)
        else:
            hard_p = 0.91 if choice == "hard" else 0.09
            raw = json.dumps({
                "model": FAST,
                "answers": {
                    "next_step": {
                        "probabilities": {"hard": hard_p, "routine": round(1.0 - hard_p, 4)},
                    },
                },
                "usage": {"input_tokens": max(1, len(prompt) // 4)},
            }).encode()
            self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def ask_word(prompt: str, keep_alive: str | None) -> tuple[str, str]:
    payload: dict = {
        "model": FAST,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0, "num_predict": 8},
    }
    if keep_alive:
        payload["keep_alive"] = keep_alive
    req = urllib.request.Request(
        OLLAMA + "/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return "", type(exc).__name__ + ": " + str(exc)[:160]
    text = str(((data.get("message") or {}).get("content")) or "").lower()
    found = []
    for word in ("routine", "hard"):
        at = text.find(word)
        if at >= 0:
            found.append((at, word))
    if not found:
        return "", "unparsed: " + text[:80]
    found.sort()
    return found[0][1], ""


def serve(handler: type[BaseHTTPRequestHandler]) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def jah_env() -> dict[str, str]:
    env = os.environ.copy()
    env["HOME"] = str(CACHE / "home")
    env["XDG_CONFIG_HOME"] = str(CACHE / "xdg-config")
    env["XDG_CACHE_HOME"] = str(CACHE / "xdg-cache")
    env["TMPDIR"] = str(CACHE / "tmp")
    env["NO_PROXY"] = "127.0.0.1,localhost"
    env["no_proxy"] = "127.0.0.1,localhost"
    for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
        env.pop(key, None)
    return env


def write_config(path: Path, listen: int, log_dir: Path, upstream: str, decision: str) -> None:
    text = "\n".join([
        "listen: {host: 127.0.0.1, port: %d}" % listen,
        "log_dir: %s" % log_dir,
        "log_states: false",
        "upstreams:",
        '  main: {type: openai, base_url: "%s", key_env: "", timeout_s: 180, retries: 0}' % upstream,
        "tiers:",
        "  strong: {upstream: main, model: %s}" % STRONG,
        "  fast: {upstream: main, model: %s}" % FAST,
        "router:",
        "  decision: %s" % decision,
        "  tau: 0.75",
        "  first_steps_strong: 1",
        "  stick_strong: 0",
        "  max_fast_streak: 0",
        "  verify_finish: true",
        "  on_error: strong",
        "  decision_timeout_s: 60",
        "models:",
        "  jah-auto: {policy: route}",
        "  jah-strong: {tier: strong}",
        "default_model: jah-auto",
        "",
    ])
    path.write_text(text)


TOOLS = [{
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run one command in the repo.",
        "parameters": {"type": "object", "properties": {"cmd": {"type": "string"}}},
    },
}]

CMDS = [
    "sed -n 1,20p data/stages/ollama.json",
    "python3 -c 'raise SystemExit(1)'",
    "printf done",
]


def run_session(base: str, model: str, session: str, outputs: list[str], token: str) -> dict:
    system = "You are a coding agent in the pfy-mentat repo. Use tool results. Reply with only the integration_stage token."
    user = "Read data/stages/ollama.json and reply with only its integration_stage token. Mark %s." % MARKER
    messages: list[dict] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    replies = []
    started = time.perf_counter()

    def ask() -> dict:
        payload = {
            "model": model,
            "messages": messages,
            "tools": TOOLS,
            "temperature": 0,
            "max_tokens": 32,
        }
        req = urllib.request.Request(
            base + "/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "X-JAH-Session": session,
            },
        )
        with urllib.request.urlopen(req, timeout=200) as resp:
            data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]

    message = ask()
    replies.append(_reply_view(message, token))
    for index, output in enumerate(outputs):
        call_id = "pfy-%d" % index
        messages.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": call_id,
                "type": "function",
                "function": {"name": "bash", "arguments": json.dumps({"cmd": CMDS[index]})},
            }],
        })
        messages.append({"role": "tool", "tool_call_id": call_id, "content": output})
        message = ask()
        replies.append(_reply_view(message, token))
    return {"wall_s": round(time.perf_counter() - started, 3), "replies": replies}


def _reply_view(message: dict, token: str) -> dict:
    content = message.get("content")
    text = content if isinstance(content, str) else ""
    return {
        "has_token": token in text,
        "n_tool_calls": len(message.get("tool_calls") or []),
        "text_head": text.replace("\n", " ")[:120],
    }


def start_jah(cfg: Path, log_path: Path) -> subprocess.Popen:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(log_path, "w")
    proc = subprocess.Popen(
        [str(JAH), "serve", "-c", str(cfg)],
        stdout=handle,
        stderr=subprocess.STDOUT,
        env=jah_env(),
    )
    proc._log_handle = handle  # type: ignore[attr-defined]
    return proc


def wait_up(base: str, proc: subprocess.Popen, seconds: float = 15) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline and proc.poll() is None:
        try:
            urllib.request.urlopen(base + "/stats", timeout=1).read()
            return True
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.1)
    return False


def stop_proc(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    handle = getattr(proc, "_log_handle", None)
    if handle is not None:
        handle.close()


def arm_once(name: str, upstream: str, decision: str, model: str, outputs: list[str], token: str) -> dict:
    work = ROOT / "tmp/jevagentharness-probe" / name
    log_dir = work / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    for old in log_dir.glob("*.jsonl"):
        old.unlink()
    port = free_port()
    cfg = work / "cfg.yaml"
    write_config(cfg, port, log_dir, upstream, decision)
    proc = start_jah(cfg, work / "serve.log")
    base = "http://127.0.0.1:%d" % port
    try:
        up = wait_up(base, proc)
        if not up:
            tail = (work / "serve.log").read_text(errors="replace")[-500:]
            return {"up": False, "serve_tail": tail}
        session = run_session(base, model, name, outputs, token)
    finally:
        stop_proc(proc)
    steps = compact_steps(log_dir)
    return {
        "up": True,
        "wall_s": session["wall_s"],
        "replies": session["replies"],
        "steps": steps,
        "counts": call_counts(steps),
        "first_tiers": first_tiers(steps),
        "log_leaks": leak_names(log_dir),
        "stub_auth": any(call.get("auth") for call in StubUpstream.calls) if upstream.startswith("http://127.0.0.1") and "11434" not in upstream else None,
    }


def score_rules(steps: list[dict]) -> dict:
    reasons = [step.get("reason") for step in steps]
    whys = [step.get("why") for step in steps]
    if len(steps) != 4:
        return {"why_ok": False, "first_ok": False, "reasons": reasons, "whys": whys}
    why_ok = all(HAND_WHY[index] is None or steps[index].get("why") == HAND_WHY[index] for index in range(4))
    return {
        "why_ok": why_ok,
        "first_ok": first_tiers(steps) == HAND_FIRST,
        "reasons": reasons,
        "whys": whys,
    }


def offline() -> dict:
    if not JAH.exists():
        raise SystemExit("jah missing at %s" % JAH)
    token = stage_token()
    outputs = tool_outputs(token)
    StubUpstream.calls = []
    stub = serve(StubUpstream)
    upstream = "http://127.0.0.1:%d/v1" % stub.server_port
    try:
        routed = arm_once("offline-rules", upstream, "{type: rules}", "jah-auto", outputs, token)
    finally:
        stub.shutdown()
    routed["stub_models"] = [call["model"] for call in StubUpstream.calls]
    routed["stub_auth_seen"] = any(call["auth"] for call in StubUpstream.calls)
    routed["score"] = score_rules(routed.get("steps") or [])
    routed["token"] = token
    return routed


def ollama_json(path: str, payload: dict | None = None, timeout: float = 20) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(OLLAMA + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def model_sizes() -> dict[str, int]:
    doc = ollama_json("/api/tags", timeout=15)
    sizes = {}
    for row in doc.get("models") or []:
        sizes[row.get("name") or row.get("model")] = int(row.get("size") or 0)
    return sizes


def loaded_models() -> set[str]:
    doc = ollama_json("/api/ps", timeout=15)
    names = set()
    for row in doc.get("models") or []:
        name = row.get("name") or row.get("model")
        if name:
            names.add(name)
    return names


def wait_for_memory(need: int) -> dict:
    started = time.monotonic()
    while True:
        have = mem_available()
        if have >= need:
            return {"ok": True, "waited_s": round(time.monotonic() - started, 1), "mem_available": have, "need": need}
        if time.monotonic() - started >= WAIT_S:
            return {"ok": False, "waited_s": round(time.monotonic() - started, 1), "mem_available": have, "need": need}
        time.sleep(15)


def warmup(model: str, keep: str | None) -> dict:
    payload: dict = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with the single word ready."}],
        "stream": False,
        "options": {"temperature": 0, "num_predict": 4},
    }
    if keep:
        payload["keep_alive"] = keep
    started = time.perf_counter()
    doc = ollama_json("/api/chat", payload, timeout=180)
    text = str(((doc.get("message") or {}).get("content")) or "")
    return {"model": model, "keep_alive": keep, "wall_s": round(time.perf_counter() - started, 3), "text_head": text[:40]}


def live() -> dict:
    if os.environ.get("PFY_MODEL_LOCK_HELD") != "1":
        raise SystemExit("live must run under scripts/model_lock.sh")
    token = stage_token()
    outputs = tool_outputs(token)
    try:
        sizes = model_sizes()
        already = loaded_models()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"skipped": "ollama unreachable: " + type(exc).__name__}
    missing = [name for name in (STRONG, FAST) if name not in sizes]
    if missing:
        return {"skipped": "models not installed: " + ", ".join(missing)}
    memory = []
    we_load = []
    warms = []
    resident = set(already)
    for name in (STRONG, FAST):
        if name in resident:
            warms.append({"model": name, "skipped_warmup": True, "keep_alive": None})
            continue
        need = sizes[name] + FLOOR_EXTRA
        gate = wait_for_memory(need)
        gate["model"] = name
        gate["size"] = sizes[name]
        memory.append(gate)
        if not gate["ok"]:
            return {
                "host_busy": True,
                "memory": memory,
                "loaded_before": sorted(already),
                "we_loaded": we_load,
                "warmup": warms,
            }
        warm = warmup(name, "2m")
        warm["mem_available_after"] = mem_available()
        warms.append(warm)
        we_load.append(name)
        resident = loaded_models()
    DecisionAdapter.keep_alive = "2m" if FAST in we_load else None
    DecisionAdapter.calls = []
    adapter = serve(DecisionAdapter)
    decision = (
        '{type: jev, provider: local, base_url: "http://127.0.0.1:%d", model: %s, retries: 0, timeout_s: 45}'
        % (adapter.server_port, FAST)
    )
    upstream = OLLAMA + "/v1"
    try:
        rules = arm_once("live-rules", upstream, "{type: rules}", "jah-auto", outputs, token)
        strong = arm_once("live-strong", upstream, "{type: rules}", "jah-strong", outputs, token)
        jev = arm_once("live-jev", upstream, decision, "jah-auto", outputs, token)
    finally:
        adapter.shutdown()
    rules["score"] = score_rules(rules.get("steps") or [])
    return {
        "token": token,
        "loaded_before": sorted(already),
        "we_loaded": we_load,
        "memory": memory,
        "warmup": warms,
        "rules": rules,
        "strong": strong,
        "jev": jev,
        "jev_calls": DecisionAdapter.calls,
        "sizes": {STRONG: sizes[STRONG], FAST: sizes[FAST]},
    }


def headline(live_doc: dict) -> dict:
    if live_doc.get("skipped") or live_doc.get("host_busy"):
        return {"skipped": live_doc.get("skipped"), "host_busy": bool(live_doc.get("host_busy"))}
    rules = live_doc["rules"]
    strong = live_doc["strong"]
    jev = live_doc["jev"]
    rules_counts = rules.get("counts") or {}
    strong_counts = strong.get("counts") or {}
    jev_first = jev.get("first_tiers") or []
    rules_first = rules.get("first_tiers") or []
    agree = 0
    for left, right in zip(rules_first, jev_first):
        if left and left == right:
            agree += 1
    denom = max(len(rules_first), 1)
    rules_wall = float(rules.get("wall_s") or 0)
    strong_wall = float(strong.get("wall_s") or 0)
    ratio = round(rules_wall / strong_wall, 3) if strong_wall else None
    replies = rules.get("replies") or []
    routine_kept = False
    if len(rules.get("steps") or []) > 1:
        step = rules["steps"][1]
        routine_kept = step.get("tier") == "fast" and not step.get("finish_check")
    return {
        "rules_strong_calls": rules_counts.get("strong_calls"),
        "rules_fast_calls": rules_counts.get("fast_calls"),
        "rules_upstream_calls": rules_counts.get("upstream_calls"),
        "strong_arm_calls": strong_counts.get("strong_calls"),
        "strong_calls_saved": (strong_counts.get("strong_calls") or 0) - (rules_counts.get("strong_calls") or 0),
        "rules_wall_s": rules.get("wall_s"),
        "strong_wall_s": strong.get("wall_s"),
        "wall_ratio_rules_over_strong": ratio,
        "rules_first_tiers": rules_first,
        "rules_score": rules.get("score"),
        "jev_first_tiers": jev_first,
        "jev_agree": "%d/%d" % (agree, len(rules_first)),
        "jev_decision_errors": sum(1 for step in (jev.get("steps") or []) if step.get("reason") == "decision_error" or step.get("decision_error")),
        "routine_reply_visible_from_fast": routine_kept,
        "rules_reply_token_hits": sum(1 for row in replies if row.get("has_token")),
        "log_leaks": (rules.get("log_leaks") or []) + (strong.get("log_leaks") or []) + (jev.get("log_leaks") or []),
    }


def main(argv: list[str]) -> int:
    if stop_requested():
        print("STOP")
        return 0
    mode = argv[1] if len(argv) > 1 else "offline"
    doc = load_results()
    if mode == "offline":
        doc["pin"] = pin_meta()
        doc["offline"] = offline()
        save_results(doc)
        score = doc["offline"].get("score")
        print(json.dumps({"offline_score": score, "first": doc["offline"].get("first_tiers"), "reasons": [s.get("reason") for s in doc["offline"].get("steps") or []]}, indent=2))
        return 0
    if mode == "live":
        doc["live"] = live()
        doc["headline"] = headline(doc["live"])
        save_results(doc)
        print(json.dumps(doc["headline"], indent=2))
        return 0
    print("usage: probe.py offline|live", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
