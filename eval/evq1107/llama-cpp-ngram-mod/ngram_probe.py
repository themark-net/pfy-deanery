#!/usr/bin/env python3
"""Decode-speed smoke for llama-server --spec-type ngram-mod.

The number is median decode tok/s with the flag on, divided by the same
median with --spec-type none, on five repetitive code prompts. The keep
bar from the toolset drop-in is 1.15 and identical outputs on all five.
This script records the numbers. It does not write a verdict.

Stdlib only. Live model work belongs under scripts/model_lock.sh.
A missing binary, a binary without the flag, or a server that never
becomes healthy writes status skipped and exits 0.
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "results.json"
DEFAULT_SERVER = "/usr/local/lib/ollama/llama-server"
DEFAULT_MODEL = (
    "/usr/share/ollama/.ollama/models/blobs/"
    "sha256-60e05f2100071479f596b964f89f510f057ce397ea22f2833a0cfe029bfc2463"
)
DEFAULT_OLLAMA = "http://127.0.0.1:11434"
MODEL_NAME = "qwen2.5-coder:7b-instruct"
PIN_COMMIT = "6f3a9f3dee3c27545371044a3a38005721ac8a8e"
SPEED_BAR = 1.15
MATCH_BAR = 5
N_PREDICT = 256
SEED = 7

# cut is how many leading lines the unfinished copy already contains.
# The model is asked to emit the rest. Repeat tails are long so a
# 24-token ngram lookup can draft the default 48 to 64 tokens.
CASES = [
    {
        "id": "repeat-load-rows",
        "kind": "repeat",
        "cut": 2,
        "lines": [
            "def load_rows(path, limit):",
            "    rows = []",
            "    handle = open(path, \"r\", encoding=\"utf-8\")",
            "    try:",
            "        for line in handle:",
            "            text = line.rstrip(\"\\n\")",
            "            if not text or text.startswith(\"#\"):",
            "                continue",
            "            parts = text.split(\",\")",
            "            rows.append([part.strip() for part in parts])",
            "            if len(rows) >= limit:",
            "                break",
            "    finally:",
            "        handle.close()",
            "    if not rows:",
            "        return []",
            "    width = max(len(row) for row in rows)",
            "    clean = []",
            "    for row in rows:",
            "        if len(row) < width:",
            "            row = row + [\"\"] * (width - len(row))",
            "        clean.append(row)",
            "    return clean",
        ],
    },
    {
        "id": "repeat-clamp-scores",
        "kind": "repeat",
        "cut": 2,
        "lines": [
            "def clamp_scores(pairs, low, high):",
            "    kept = []",
            "    for name, score in pairs:",
            "        if name is None or name == \"\":",
            "            continue",
            "        try:",
            "            value = float(score)",
            "        except (TypeError, ValueError):",
            "            continue",
            "        if value < low:",
            "            value = low",
            "        elif value > high:",
            "            value = high",
            "        kept.append((name.strip(), round(value, 4)))",
            "    kept.sort(key=lambda item: (-item[1], item[0]))",
            "    seen = set()",
            "    unique = []",
            "    for name, value in kept:",
            "        if name in seen:",
            "            continue",
            "        seen.add(name)",
            "        unique.append({\"name\": name, \"score\": value})",
            "    return unique",
        ],
    },
    {
        "id": "repeat-merge-maps",
        "kind": "repeat",
        "cut": 2,
        "lines": [
            "def merge_maps(base, extra):",
            "    out = {}",
            "    for key, value in base.items():",
            "        if not isinstance(key, str):",
            "            continue",
            "        if isinstance(value, dict):",
            "            out[key] = dict(value)",
            "        elif isinstance(value, list):",
            "            out[key] = list(value)",
            "        else:",
            "            out[key] = value",
            "    for key, value in extra.items():",
            "        if not isinstance(key, str):",
            "            continue",
            "        current = out.get(key)",
            "        if isinstance(current, dict) and isinstance(value, dict):",
            "            merged = dict(current)",
            "            merged.update(value)",
            "            out[key] = merged",
            "        elif isinstance(current, list) and isinstance(value, list):",
            "            out[key] = current + [item for item in value if item not in current]",
            "        else:",
            "            out[key] = value",
            "    return out",
        ],
    },
    {
        "id": "edit-retry-delay",
        "kind": "edit",
        "cut": 9,
        "instr": (
            "Complete the unfinished copy so it matches the finished function, "
            "except time.sleep must use 4 instead of 3. Output only the missing lines."
        ),
        "lines": [
            "def retry_call(call, tries):",
            "    last = None",
            "    for attempt in range(tries):",
            "        try:",
            "            return call()",
            "        except TimeoutError as exc:",
            "            last = exc",
            "            if attempt + 1 >= tries:",
            "                break",
            "            time.sleep(3)",
            "    notes = []",
            "    notes.append(\"tries=%s\" % tries)",
            "    notes.append(\"last=%r\" % (last,))",
            "    text = \"; \".join(notes)",
            "    detail = {",
            "        \"tries\": tries,",
            "        \"attempt\": attempt if last is not None else 0,",
            "        \"message\": text,",
            "    }",
            "    if last is None:",
            "        return {\"ok\": True, \"detail\": detail}",
            "    err = TimeoutError(text)",
            "    err.__cause__ = last",
            "    err.detail = detail",
            "    raise err",
        ],
        "expect": [
            "            time.sleep(4)",
            "    notes = []",
            "    notes.append(\"tries=%s\" % tries)",
            "    notes.append(\"last=%r\" % (last,))",
            "    text = \"; \".join(notes)",
            "    detail = {",
            "        \"tries\": tries,",
            "        \"attempt\": attempt if last is not None else 0,",
            "        \"message\": text,",
            "    }",
            "    if last is None:",
            "        return {\"ok\": True, \"detail\": detail}",
            "    err = TimeoutError(text)",
            "    err.__cause__ = last",
            "    err.detail = detail",
            "    raise err",
        ],
    },
    {
        "id": "edit-row-label",
        "kind": "edit",
        "cut": 4,
        "instr": (
            "Complete the unfinished copy so it matches the finished function, "
            "except the label string must be new instead of old. Output only the missing lines."
        ),
        "lines": [
            "def format_row(row, width):",
            "    cells = []",
            "    for cell in row:",
            "        cells.append(\"\" if cell is None else str(cell).strip())",
            "    label = \"old\"",
            "    if len(cells) < width:",
            "        cells = cells + [\"\"] * (width - len(cells))",
            "    elif len(cells) > width:",
            "        cells = cells[:width]",
            "    body = \" | \".join(cells)",
            "    line = \"%s: %s\" % (label, body)",
            "    if len(line) > 120:",
            "        line = line[:117] + \"...\"",
            "    if not line:",
            "        line = label + \":\"",
            "    parts = line.split(\":\", 1)",
            "    head = parts[0].strip() or label",
            "    tail = parts[1].strip() if len(parts) > 1 else \"\"",
            "    padded = tail.ljust(width)",
            "    shown = padded[:80]",
            "    return \"%s: %s\" % (head, shown)",
        ],
        "expect": [
            "    label = \"new\"",
            "    if len(cells) < width:",
            "        cells = cells + [\"\"] * (width - len(cells))",
            "    elif len(cells) > width:",
            "        cells = cells[:width]",
            "    body = \" | \".join(cells)",
            "    line = \"%s: %s\" % (label, body)",
            "    if len(line) > 120:",
            "        line = line[:117] + \"...\"",
            "    if not line:",
            "        line = label + \":\"",
            "    parts = line.split(\":\", 1)",
            "    head = parts[0].strip() or label",
            "    tail = parts[1].strip() if len(parts) > 1 else \"\"",
            "    padded = tail.ljust(width)",
            "    shown = padded[:80]",
            "    return \"%s: %s\" % (head, shown)",
        ],
    },
]


def env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    return Path(raw) if raw else default


def cache_root() -> Path:
    raw = os.environ.get("LLAMA_NGRAM_CACHE")
    if raw:
        return Path(raw)
    return Path.home() / ".cache" / "pfy" / "tools" / "llama-cpp-ngram-mod"


def opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def url_json(url: str, payload: dict | None, timeout: float) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with opener().open(req, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:400]
        raise RuntimeError("HTTP %s %s" % (exc.code, detail)) from exc
    return json.loads(raw.decode("utf-8", "replace"))


def mem_available_bytes() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("MemAvailable missing")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_text(cmd: list[str], timeout: float) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        errors="replace",
        check=False,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def render(case: dict) -> tuple[str, str]:
    lines = case["lines"]
    cut = case["cut"]
    finished = "\n".join(lines + ["# END"])
    unfinished = "\n".join(lines[:cut])
    if case["kind"] == "repeat":
        instr = (
            "Complete the unfinished copy so it matches the finished function "
            "exactly. Output only the missing lines."
        )
        expected = "\n".join(lines[cut:])
    else:
        instr = case["instr"]
        expected = "\n".join(case["expect"])
    prompt = instr + "\n\n" + finished + "\n\n" + unfinished + "\n"
    return prompt, expected


def child_env(cache: Path, gpu: bool) -> dict:
    env = dict(os.environ)
    env["HOME"] = str(cache / "home")
    env["XDG_CONFIG_HOME"] = str(cache / "xdg" / "config")
    env["XDG_CACHE_HOME"] = str(cache / "xdg" / "cache")
    env["XDG_DATA_HOME"] = str(cache / "xdg" / "data")
    env["TMPDIR"] = str(cache / "tmp")
    if not gpu:
        return env
    lib = "/usr/local/lib/ollama"
    env["HSA_OVERRIDE_GFX_VERSION"] = os.environ.get("HSA_OVERRIDE_GFX_VERSION", "11.5.1")
    env["GGML_BACKEND_PATH"] = f"{lib}/rocm_v7_2/libggml-hip.so"
    ld = f"{lib}/rocm_v7_2:{lib}"
    old = os.environ.get("LD_LIBRARY_PATH")
    env["LD_LIBRARY_PATH"] = ld if not old else ld + ":" + old
    env["GGML_CUDA_ENABLE_UNIFIED_MEMORY"] = "1"
    env["GGML_HIP_UMA"] = "1"
    return env


def port_busy(port: int) -> bool:
    import socket
    sock = socket.socket()
    sock.settimeout(0.2)
    try:
        return sock.connect_ex(("127.0.0.1", port)) == 0
    finally:
        sock.close()


def pick_port(start: int) -> int:
    for port in range(start, start + 6):
        if not port_busy(port):
            return port
    raise RuntimeError(f"no free port from {start}")


def healthy(port: int) -> bool:
    req = urllib.request.Request("http://127.0.0.1:%s/health" % port)
    try:
        with opener().open(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def stop_proc(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        proc.wait(timeout=5)


def wait_healthy(proc: subprocess.Popen, port: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False
        if healthy(port):
            return True
        time.sleep(0.1)
    return proc.poll() is None and healthy(port)


def decode_tok_s(payload: dict) -> float | None:
    timings = payload.get("timings") or {}
    if isinstance(timings, dict) and timings.get("predicted_per_second"):
        return float(timings["predicted_per_second"])
    n = timings.get("predicted_n") if isinstance(timings, dict) else None
    ms = timings.get("predicted_ms") if isinstance(timings, dict) else None
    if n and ms:
        return float(n) / (float(ms) / 1000.0)
    return None


def completion(port: int, prompt: str) -> dict:
    body = {
        "prompt": prompt,
        "n_predict": N_PREDICT,
        "temperature": 0,
        "top_k": 1,
        "top_p": 1,
        "seed": SEED,
        "repeat_penalty": 1.0,
        "stream": False,
        "cache_prompt": False,
        "stop": ["# END"],
    }
    return url_json(f"http://127.0.0.1:{port}/completion", body, 180)


def acceptance(log_text: str) -> dict:
    import re
    summary = re.findall(
        r"draft acceptance = ([0-9.]+) \(\s*(\d+) accepted / \s*(\d+) generated\)",
        log_text,
    )
    steps = re.findall(r"accepted\s+(\d+)/(\d+) draft tokens", log_text)
    return {
        "summary_lines": [
            {"rate": float(a), "accepted": int(b), "generated": int(c)}
            for a, b, c in summary
        ],
        "step_lines": [{"accepted": int(a), "drafted": int(b)} for a, b in steps],
    }


def excerpt(log_text: str, limit: int = 30) -> list[str]:
    import re
    hits = []
    for line in log_text.splitlines():
        if re.search(r"ngram|specul|accept|error|HIP|ggml_backend|device", line, re.I):
            hits.append(line[:240])
        if len(hits) >= limit:
            break
    return hits


def ps_models(ollama: str) -> tuple[list, str]:
    try:
        data = url_json(ollama.rstrip("/") + "/api/ps", None, 5)
        models = data.get("models") or []
        return models, ""
    except Exception as exc:
        err = str(exc)
    try:
        code, text = run_text(["ollama", "ps"], 10)
    except Exception as exc:
        return [], err + " | " + str(exc)
    if code != 0:
        return [], err + " | ollama ps exit %s" % code
    rows = []
    for line in text.splitlines():
        if not line.strip() or line.upper().startswith("NAME"):
            continue
        rows.append({"raw": line.strip()})
    return rows, ""


def ps_has(rows: list, name: str) -> bool:
    for row in rows:
        text = json.dumps(row) if isinstance(row, dict) else str(row)
        if name in text:
            return True
    return False


def wait_for_host(need: int, ollama: str) -> tuple[bool, dict]:
    if os.environ.get("LLAMA_NGRAM_SKIP_WAIT") == "1":
        return True, {"skipped": True}
    deadline = time.monotonic() + 30 * 60
    last = {}
    while True:
        avail = mem_available_bytes()
        rows, err = ps_models(ollama)
        busy = bool(rows) if not err else False
        last = {
            "mem_available": avail,
            "need": need,
            "ps_error": err,
            "ps_count": len(rows) if not err else None,
            "busy": busy,
        }
        if avail >= need and not busy:
            return True, last
        if time.monotonic() >= deadline:
            return False, last
        print(
            "wait mem_gib=%.1f need_gib=%.1f busy=%s" % (avail / 1024**3, need / 1024**3, busy),
            flush=True,
        )
        time.sleep(20)


def start_server(server: str, model: str, spec: str, port: int, cache: Path, log_path: Path):
    gpu = os.environ.get("LLAMA_NGRAM_NO_GPU") != "1"
    cmd = [
        server,
        "--model", model,
        "--host", "127.0.0.1",
        "--port", str(port),
        "--no-mmap",
        "-ngl", "999",
        "-c", "2048",
        "-np", "1",
        "-fa", "on",
        "--no-webui",
        "--log-colors", "off",
        "--spec-type", spec,
    ]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        cmd,
        stdout=handle,
        stderr=subprocess.STDOUT,
        env=child_env(cache, gpu),
        start_new_session=True,
    )
    return proc, handle, cmd


def run_mode(server: str, model: str, spec: str, port: int, cache: Path, prompts: list[dict]) -> dict:
    tries = int(os.environ.get("LLAMA_NGRAM_START_TRIES", "2"))
    health_s = float(os.environ.get("LLAMA_NGRAM_HEALTH_S", "180"))
    log_path = cache / "tmp" / ("server-%s.log" % spec)
    last_tail = ""
    cmd: list[str] = []
    for attempt in range(1, tries + 1):
        proc, handle, cmd = start_server(server, model, spec, port, cache, log_path)
        ok = False
        try:
            ok = wait_healthy(proc, port, health_s)
            if not ok:
                handle.flush()
                last_tail = log_path.read_text(encoding="utf-8", errors="replace")[-1500:]
                print("server %s attempt %s not healthy" % (spec, attempt), flush=True)
                continue
            rows = []
            t0 = time.perf_counter()
            for item in prompts:
                one = {"id": item["id"], "kind": item["kind"]}
                try:
                    payload = completion(port, item["prompt"])
                except Exception as exc:
                    one["error"] = str(exc)[:400]
                    rows.append(one)
                    print("%s %s ERROR %s" % (spec, item["id"], one["error"]), flush=True)
                    continue
                text = payload.get("content")
                if not isinstance(text, str):
                    text = ""
                got = text.strip()
                one["content"] = got
                one["exact_off_later"] = False
                one["expected_match"] = got == item["expected"].strip()
                one["tok_s"] = decode_tok_s(payload)
                timings = payload.get("timings") if isinstance(payload.get("timings"), dict) else {}
                one["predicted_n"] = timings.get("predicted_n")
                one["prompt_n"] = timings.get("prompt_n")
                rows.append(one)
                print("%s %s tok_s=%s" % (spec, item["id"], one["tok_s"]), flush=True)
            wall = time.perf_counter() - t0
            handle.flush()
            log_text = log_path.read_text(encoding="utf-8", errors="replace")
            return {
                "spec": spec,
                "status": "ok",
                "attempt": attempt,
                "port": port,
                "command": cmd,
                "wall_s": round(wall, 3),
                "rows": rows,
                "acceptance": acceptance(log_text),
                "log_excerpt": excerpt(log_text),
            }
        finally:
            stop_proc(proc)
            handle.close()
    return {
        "spec": spec,
        "status": "skipped",
        "reason": "server did not become healthy",
        "command": cmd,
        "log_tail": last_tail,
    }


def ollama_rows(base: str, prompts: list[dict], send_keep: bool) -> dict:
    rows = []
    t0 = time.perf_counter()
    for item in prompts:
        payload = {
            "model": MODEL_NAME,
            "prompt": item["prompt"],
            "raw": True,
            "stream": False,
            "options": {
                "temperature": 0,
                "seed": SEED,
                "num_predict": N_PREDICT,
                "top_k": 1,
                "repeat_penalty": 1.0,
                "stop": ["# END"],
            },
        }
        if send_keep:
            payload["keep_alive"] = "2m"
        one = {"id": item["id"], "kind": item["kind"]}
        try:
            data = url_json(base.rstrip("/") + "/api/generate", payload, 180)
        except Exception as exc:
            one["error"] = str(exc)[:400]
            rows.append(one)
            continue
        text = data.get("response") if isinstance(data.get("response"), str) else ""
        count = data.get("eval_count") or 0
        dur = data.get("eval_duration") or 0
        one["content"] = text.strip()
        one["expected_match"] = one["content"] == item["expected"].strip()
        one["tok_s"] = (float(count) / (float(dur) / 1e9)) if count and dur else None
        one["eval_count"] = count
        rows.append(one)
        print("ollama %s tok_s=%s" % (item["id"], one["tok_s"]), flush=True)
    return {"status": "ok", "keep_alive": "2m" if send_keep else None, "wall_s": round(time.perf_counter() - t0, 3), "rows": rows}


def median(values: list[float]) -> float | None:
    if not values:
        return None
    return float(statistics.median(values))


def summarize(modes: list[dict], ollama: dict | None) -> dict:
    by_spec = {m.get("spec"): m for m in modes}
    off = by_spec.get("none") or {}
    on = by_spec.get("ngram-mod") or {}
    off_rows = {r["id"]: r for r in off.get("rows") or []}
    matches = 0
    compared = 0
    per = []
    if on.get("rows"):
        for row in on["rows"]:
            other = off_rows.get(row["id"]) or {}
            same = (
                "content" in row
                and "content" in other
                and row["content"] == other["content"]
            )
            compared += 1 if "content" in row and "content" in other else 0
            matches += 1 if same else 0
            per.append({
                "id": row["id"],
                "kind": row["kind"],
                "off_tok_s": other.get("tok_s"),
                "on_tok_s": row.get("tok_s"),
                "identical": same,
                "on_expected": row.get("expected_match"),
                "off_expected": other.get("expected_match"),
                "on_prompt_n": row.get("prompt_n"),
            })
    off_speeds = [r["tok_s"] for r in off.get("rows") or [] if isinstance(r.get("tok_s"), (int, float))]
    on_speeds = [r["tok_s"] for r in on.get("rows") or [] if isinstance(r.get("tok_s"), (int, float))]
    off_med = median(off_speeds)
    on_med = median(on_speeds)
    ratio = (on_med / off_med) if off_med and on_med else None
    oll_speeds = []
    if ollama and ollama.get("rows"):
        oll_speeds = [r["tok_s"] for r in ollama["rows"] if isinstance(r.get("tok_s"), (int, float))]
    return {
        "off_median_tok_s": None if off_med is None else round(off_med, 4),
        "on_median_tok_s": None if on_med is None else round(on_med, 4),
        "ratio_on_over_off": None if ratio is None else round(ratio, 4),
        "identical": matches,
        "compared": compared,
        "ollama_median_tok_s": None if not oll_speeds else round(median(oll_speeds), 4),
        "bar_ratio": SPEED_BAR,
        "bar_identical": MATCH_BAR,
        "prompts": per,
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def ensure_cache(cache: Path) -> None:
    for sub in ("home", "xdg/config", "xdg/cache", "xdg/data", "tmp"):
        (cache / sub).mkdir(parents=True, exist_ok=True)


def run_live() -> int:
    out = env_path("LLAMA_NGRAM_OUT", DEFAULT_OUT)
    server = os.environ.get("LLAMA_NGRAM_SERVER", DEFAULT_SERVER)
    model = os.environ.get("LLAMA_NGRAM_MODEL", DEFAULT_MODEL)
    ollama = os.environ.get("LLAMA_NGRAM_OLLAMA", DEFAULT_OLLAMA)
    cache = cache_root()
    ensure_cache(cache)
    result: dict = {
        "tool": "llama.cpp ngram-mod",
        "pin_commit": PIN_COMMIT,
        "model_name": MODEL_NAME,
        "model_path": model,
        "server": server,
        "status": "skipped",
    }
    try:
        server_path = Path(server)
        if not server_path.is_file() or not os.access(server_path, os.X_OK):
            result["reason"] = "server binary missing"
            return 0
        try:
            code, help_text = run_text([server, "--help"], 60)
        except Exception as exc:
            result["reason"] = "server help failed: %s" % exc
            return 0
        result["help_exit"] = code
        if "ngram-mod" not in help_text:
            result["reason"] = "binary help has no ngram-mod"
            return 0
        try:
            _, version = run_text([server, "--version"], 30)
        except Exception as exc:
            version = "version failed: %s" % exc
        result["version_line"] = " ".join(version.split())[:300]
        model_path = Path(model)
        if not model_path.is_file():
            result["reason"] = "model file missing"
            return 0
        result["model_bytes"] = model_path.stat().st_size
        if model_path.name.startswith("sha256-"):
            expect = model_path.name.split("-", 1)[1]
            print("hashing model", flush=True)
            got = sha256_file(model_path)
            result["model_sha256"] = got
            if got != expect:
                result["reason"] = "model sha256 does not match the blob name"
                return 0
        impl = Path("/usr/local/lib/ollama/libllama-server-impl.so")
        libllama = Path("/usr/local/lib/ollama/libllama.so.0.0.1")
        if os.environ.get("LLAMA_NGRAM_NO_GPU") != "1":
            if impl.is_file():
                result["libllama_server_impl_sha256"] = sha256_file(impl)
            if libllama.is_file():
                result["libllama_sha256"] = sha256_file(libllama)
            result["server_sha256"] = sha256_file(server_path)
        need = model_path.stat().st_size + 25 * 1024 ** 3
        ok, host = wait_for_host(need, ollama)
        result["host"] = host
        if not ok:
            result["status"] = "HOST-BUSY"
            result["reason"] = "MemAvailable stayed below model size plus 25 GiB, or another model stayed loaded"
            return 0
        prompts = []
        for case in CASES:
            prompt, expected = render(case)
            prompts.append({
                "id": case["id"],
                "kind": case["kind"],
                "prompt": prompt,
                "expected": expected,
            })
        port = pick_port(int(os.environ.get("LLAMA_NGRAM_PORT", "18151")))
        modes = [
            run_mode(server, model, "none", port, cache, prompts),
            run_mode(server, model, "ngram-mod", port, cache, prompts),
        ]
        result["modes"] = modes
        ollama_part = None
        if os.environ.get("LLAMA_NGRAM_SKIP_OLLAMA") != "1" and all(m.get("status") == "ok" for m in modes):
            rows, err = ps_models(ollama)
            loaded = ps_has(rows, MODEL_NAME) if not err else False
            result["ollama_ps_before"] = {"error": err, "loaded": loaded, "count": len(rows) if not err else None}
            ollama_part = ollama_rows(ollama, prompts, send_keep=not loaded)
            result["ollama"] = ollama_part
        elif os.environ.get("LLAMA_NGRAM_SKIP_OLLAMA") == "1":
            result["ollama"] = {"status": "skipped", "reason": "LLAMA_NGRAM_SKIP_OLLAMA"}
        summary = summarize(modes, ollama_part)
        result["summary"] = summary
        if all(m.get("status") == "ok" for m in modes) and summary.get("ratio_on_over_off") is not None:
            result["status"] = "ok"
            result["reason"] = ""
        else:
            result["status"] = "skipped"
            reasons = [m.get("reason") for m in modes if m.get("status") != "ok" and m.get("reason")]
            result["reason"] = "; ".join(reasons) or "a llama-server mode did not finish"
        pin = {
            "commit": PIN_COMMIT,
            "commit_subject": "server: avoid unnecessary checkpoint restore when new tokens are present (#24110)",
            "commit_date": "2026-06-04T13:09:01Z",
            "version_line": result.get("version_line"),
            "server": server,
            "server_sha256": result.get("server_sha256"),
            "libllama_server_impl_sha256": result.get("libllama_server_impl_sha256"),
            "libllama_sha256": result.get("libllama_sha256"),
            "model_name": MODEL_NAME,
            "model_path": model,
            "model_sha256": result.get("model_sha256"),
            "ollama": "0.30.8",
            "debian_cpu_package_not_used": "llama.cpp-tools 8681+dfsg-1",
            "spec_type": "ngram-mod",
            "spec_ngram_mod_defaults": {"n_min": 48, "n_max": 64, "n_match": 24},
        }
        write_json(cache / "pin.json", pin)
        result["pin"] = pin
        return 0
    except Exception as exc:
        result["status"] = "error"
        result["reason"] = str(exc)[:500]
        return 1
    finally:
        write_json(out, result)
        print("wrote %s status=%s" % (out, result.get("status")), flush=True)


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] != "live":
        print("usage: ngram_probe.py live", flush=True)
        return 2
    return run_live()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
