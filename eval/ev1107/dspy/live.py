#!/usr/bin/env python3
"""Live DSPy probe: plain Predict versus BootstrapFewShot on the #230 cases.

Talks only to local Ollama at 127.0.0.1:11434. DSPy speaks the OpenAI
chat shape. The loopback proxy turns each completion into native /api/chat
with think false, temperature 0, seed 230, and num_ctx 4096. The OpenAI
route on this host ignores those fields, spends the completion on reasoning,
and reloads the model at a 262k context.

Run under scripts/model_lock.sh via eval/ev1107/dspy/run_live.sh.
No hosted model and no API key. The bearer value sent to Ollama is the
dummy word local, and program.json redacts it.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import probe  # noqa: E402

MODEL = "qwen3.6:35b"
OLLAMA = "http://127.0.0.1:11434"
MODEL_GIB = 22.0
MEM_MARGIN_GIB = 25.0
NUM_CTX = 4096
MAX_CTX = 8192
MAX_TOKENS = 128
SEED = 230
MODEL_BUDGET_S = 60 * 60
MEM_WAIT_S = 30 * 60
CALL_TIMEOUT_S = 90
LOAD_TIMEOUT_S = 600
CASES_PATH = ROOT / "data" / "decision-gates" / "laya-trial.cases.v0.json"
SECRET_VALUE = re.compile(
    r"(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|xai-[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})"
)


class TimeCap(BaseException):
    """Not an Exception: BootstrapFewShot swallows Exception and would keep going."""


class ContextCap(BaseException):
    """Loaded context blew past the cap. Same reason as TimeCap: do not let DSPy swallow it."""

    def __init__(self, ctx: int):
        self.ctx = ctx
        super().__init__(f"context grew to {ctx}")


def cache_root() -> Path:
    return Path(os.environ.get("PFY_DSPY_CACHE") or os.path.expanduser("~/.cache/pfy/tools/dspy"))


def isolate_home() -> None:
    root = cache_root()
    mapping = {
        "HOME": "home",
        "XDG_CACHE_HOME": "xdg-cache",
        "XDG_CONFIG_HOME": "xdg-config",
        "TMPDIR": "tmp",
        "DSPY_CACHEDIR": "dspy-cache",
    }
    for key, name in mapping.items():
        path = root / name
        path.mkdir(parents=True, exist_ok=True)
        os.environ[key] = str(path)
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
    os.environ["NO_PROXY"] = "127.0.0.1,localhost"


def mem_available_gib() -> float | None:
    try:
        text = Path("/proc/meminfo").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        if line.startswith("MemAvailable:"):
            return float(line.split()[1]) / (1024 * 1024)
    return None


def http_json(method: str, url: str, body: dict | None = None, timeout: float = 30) -> tuple[int, dict]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"raw": raw[:500]}
        return exc.code, parsed


def ollama_ps() -> str:
    try:
        proc = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"ollama ps failed: {exc}"
    return proc.stdout


def model_loaded(ps_text: str, model: str) -> bool:
    for line in ps_text.splitlines():
        if line.startswith("NAME"):
            continue
        if line.split() and line.split()[0] == model:
            return True
    return False


def context_from_cli(ps_text: str, model: str) -> int | None:
    for line in ps_text.splitlines():
        parts = line.split()
        if not parts or parts[0] != model:
            continue
        nums = [int(item) for item in re.findall(r"\b\d{3,}\b", line)]
        return max(nums) if nums else None
    return None


def context_from_ps_api(blob: dict, model: str) -> int | None:
    found = []
    for row in blob.get("models") or []:
        name = row.get("name") or row.get("model") or ""
        if name != model and not name.startswith(model):
            continue
        for key in ("context_length", "context"):
            if isinstance(row.get(key), int):
                found.append(row[key])
        details = row.get("details") or {}
        if isinstance(details.get("context_length"), int):
            found.append(details["context_length"])
    return max(found) if found else None


def wait_for_memory(need: float, log) -> str | None:
    deadline = time.monotonic() + MEM_WAIT_S
    while True:
        avail = mem_available_gib()
        if avail is not None and avail >= need:
            return None
        if time.monotonic() >= deadline:
            shown = "unknown" if avail is None else f"{avail:.1f}"
            return f"HOST-BUSY MemAvailable {shown} GiB needs {need:.0f} GiB"
        log(f"waiting for memory avail={avail} need={need:.0f}")
        time.sleep(30)


def preload(model: str, keep_alive: str | None) -> dict:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with the single word pong."}],
        "stream": False,
        "think": False,
        "options": {"num_ctx": NUM_CTX, "num_predict": 8, "temperature": 0, "seed": SEED},
    }
    if keep_alive:
        body["keep_alive"] = keep_alive
    status, data = http_json("POST", OLLAMA + "/api/chat", body, timeout=LOAD_TIMEOUT_S)
    message = data.get("message") if isinstance(data, dict) else None
    content = ""
    thinking = ""
    if isinstance(message, dict):
        content = str(message.get("content") or "")
        thinking = str(message.get("thinking") or "")
    return {
        "status": status,
        "eval_count": data.get("eval_count") if isinstance(data, dict) else None,
        "content": content[:80],
        "thinking_chars": len(thinking),
        "error": None if status == 200 else json.dumps(data)[:400],
    }


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        self._forward()

    def do_POST(self) -> None:  # noqa: N802
        self._forward()

    def log_message(self, fmt: str, *args) -> None:
        return

    def _send(self, status: int, payload: bytes, content_type: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _forward(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        route = self.path.split("?", 1)[0]
        if self.command == "POST" and route == "/v1/chat/completions":
            status, payload = self._native_chat(raw)
            self._send(status, payload)
            return
        url = self.server.upstream + self.path  # type: ignore[attr-defined]
        headers = {}
        ctype = self.headers.get("Content-Type")
        if ctype:
            headers["Content-Type"] = ctype
        auth = self.headers.get("Authorization")
        if auth:
            headers["Authorization"] = auth
        req = urllib.request.Request(url, data=raw if self.command == "POST" else None, headers=headers, method=self.command)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(req, timeout=CALL_TIMEOUT_S) as resp:
                payload = resp.read()
                status = resp.status
                resp_type = resp.headers.get("Content-Type") or "application/json"
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            status = exc.code
            resp_type = "application/json"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            payload = json.dumps({"error": str(exc)}).encode("utf-8")
            status = 502
            resp_type = "application/json"
        self._send(status, payload, resp_type)

    def _native_chat(self, raw: bytes) -> tuple[int, bytes]:
        try:
            body = json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            return 400, b'{"error":"body is not json"}'
        if not isinstance(body, dict):
            return 400, b'{"error":"body is not an object"}'
        native = native_chat_body(body, self.server.keep_alive)  # type: ignore[attr-defined]
        url = self.server.upstream + "/api/chat"  # type: ignore[attr-defined]
        data = json.dumps(native).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(req, timeout=CALL_TIMEOUT_S) as resp:
                payload = resp.read()
                status = resp.status
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return 502, json.dumps({"error": str(exc)}).encode("utf-8")
        if status != 200:
            return status, payload
        try:
            parsed = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return 502, b'{"error":"native chat was not json"}'
        model = str(native.get("model") or "")
        wide = context_too_wide(self.server.upstream, model)  # type: ignore[attr-defined]
        if wide is not None:
            return 409, json.dumps({"error": f"context grew to {wide}"}).encode("utf-8")
        return 200, json.dumps(openai_from_native(parsed, model)).encode("utf-8")


def _message_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                if "text" in part:
                    parts.append(str(part.get("text") or ""))
                elif "content" in part:
                    parts.append(str(part.get("content") or ""))
        return "".join(parts)
    if content is None:
        return ""
    return str(content)


def native_chat_body(body: dict, keep_alive: str | None) -> dict:
    cap = body.get("max_tokens") if body.get("max_tokens") is not None else body.get("max_completion_tokens")
    if cap is None:
        cap = MAX_TOKENS
    try:
        cap = int(cap)
    except (TypeError, ValueError):
        cap = MAX_TOKENS
    if cap < 1:
        cap = MAX_TOKENS
    messages = []
    for msg in body.get("messages") or []:
        if not isinstance(msg, dict):
            continue
        messages.append({"role": str(msg.get("role") or "user"), "content": _message_text(msg.get("content"))})
    native = {
        "model": body.get("model"),
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {
            "num_ctx": NUM_CTX,
            "num_predict": cap,
            "temperature": 0,
            "seed": SEED,
        },
    }
    if body.get("response_format"):
        native["format"] = "json"
    if keep_alive:
        native["keep_alive"] = keep_alive
    return native


def openai_from_native(native: dict, model: str) -> dict:
    msg = native.get("message") if isinstance(native.get("message"), dict) else {}
    content = msg.get("content")
    if not isinstance(content, str):
        content = "" if content is None else str(content)
    reason = native.get("done_reason") or ""
    finish = "length" if reason == "length" else "stop"
    prompt = int(native.get("prompt_eval_count") or 0)
    completion = int(native.get("eval_count") or 0)
    return {
        "id": "chatcmpl-local",
        "object": "chat.completion",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": finish,
            }
        ],
        "usage": {
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion,
        },
    }


def context_too_wide(upstream: str, model: str) -> int | None:
    try:
        status, blob = http_json("GET", upstream.rstrip("/") + "/api/ps", timeout=10)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None
    if status != 200 or not isinstance(blob, dict):
        return None
    ctx = context_from_ps_api(blob, model)
    if ctx is not None and ctx > MAX_CTX:
        return ctx
    return None


def start_proxy(keep_alive: str | None) -> tuple[ThreadingHTTPServer, int]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    server.upstream = OLLAMA  # type: ignore[attr-defined]
    server.keep_alive = keep_alive  # type: ignore[attr-defined]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, server.server_address[1]


def inputs_of(case: dict) -> dict:
    payload = probe.payload_for(case)
    return {
        "task": payload["task"],
        "state": json.dumps(payload["state"], ensure_ascii=False, sort_keys=True),
        "criteria": json.dumps(payload["criteria"], ensure_ascii=False, sort_keys=True),
    }


def example_of(case: dict, dspy):
    fields = inputs_of(case)
    fields["choice"] = case["label"]
    fields["confidence"] = 0.9
    return dspy.Example(**fields).with_inputs("task", "state", "criteria")


def score_cases(program, cases: list[dict], gate: float, deadline: float) -> list[dict]:
    rows = []
    errors = 0
    for case in cases:
        if time.monotonic() > deadline:
            raise TimeCap()
        fields = inputs_of(case)
        try:
            pred = program(**fields)
            answer = {"choice": getattr(pred, "choice", None), "confidence": getattr(pred, "confidence", None)}
        except TimeCap:
            raise
        except ContextCap:
            raise
        except Exception as exc:  # noqa: BLE001 -- one bad call is a wrong case, three aborts
            text = str(exc)
            if "context grew to" in text:
                digits = re.findall(r"context grew to (\d+)", text)
                raise ContextCap(int(digits[0]) if digits else 0) from exc
            errors += 1
            answer = {"choice": None, "confidence": None, "error": type(exc).__name__}
            if errors >= 3:
                raise
        row = probe.score_answer(case, answer, gate)
        if answer.get("error"):
            row["error"] = answer["error"]
        rows.append(row)
    return rows


def build_program(dspy):
    class Decide(dspy.Signature):
        """You are a typed Choice decision engine, not a chatbot.
        Pick exactly one criteria key. Confidence is a calibrated margin in 0..1, never percent-correct.
        """

        task: str = dspy.InputField()
        state: str = dspy.InputField()
        criteria: str = dspy.InputField()
        choice: str = dspy.OutputField(desc="exactly one criteria key")
        confidence: float = dspy.OutputField(desc="a number from 0 to 1")

    class Chooser(dspy.Module):
        def __init__(self):
            super().__init__()
            self.decide = dspy.Predict(Decide)

        def forward(self, task, state, criteria):
            return self.decide(task=task, state=state, criteria=criteria)

    return Chooser()


def metric_factory(deadline: float):
    def metric(example, pred, trace=None):
        if time.monotonic() > deadline:
            raise TimeCap()
        try:
            criteria = json.loads(example.criteria)
        except (TypeError, json.JSONDecodeError):
            criteria = {}
        choice = probe.normalize_choice(getattr(pred, "choice", None), criteria)
        confidence = probe.parse_confidence(getattr(pred, "confidence", None))
        return bool(choice is not None and confidence is not None and choice == example.choice)

    return metric


def _case_pair(case: dict) -> tuple[str, str]:
    return (
        case.get("instructions") or "",
        json.dumps(case.get("state"), ensure_ascii=False, sort_keys=True),
    )


def _demos_leave_train(program, train: list[dict], held: list[dict]) -> bool:
    train_pairs = {_case_pair(case) for case in train}
    held_only = {_case_pair(case) for case in held} - train_pairs
    for demo in list(getattr(program.decide, "demos", []) or []):
        task = getattr(demo, "task", None)
        state = getattr(demo, "state", None)
        if task is None and isinstance(demo, dict):
            task = demo.get("task")
            state = demo.get("state")
        if (task, state) in held_only:
            return True
    return False


def demo_counts(program) -> dict:
    demos = list(getattr(program.decide, "demos", []) or [])
    augmented = 0
    for demo in demos:
        flag = getattr(demo, "augmented", None)
        if flag is None and isinstance(demo, dict):
            flag = demo.get("augmented")
        if flag:
            augmented += 1
    return {"n_demos": len(demos), "n_bootstrapped": augmented, "n_labeled": len(demos) - augmented}


def redact_program(path: Path) -> None:
    if not path.is_file():
        return
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        path.unlink(missing_ok=True)
        return

    def walk(node):
        if isinstance(node, dict):
            for key, value in list(node.items()):
                if key.lower() in {"api_key", "authorization", "token"} and isinstance(value, str):
                    node[key] = "redacted"
                elif isinstance(value, str) and SECRET_VALUE.search(value):
                    node[key] = "redacted"
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(blob)
    path.write_text(json.dumps(blob, indent=2) + "\n", encoding="utf-8")


def write_outputs(out_dir: Path, receipt: dict, line: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    one = " ".join(line.split())
    (out_dir / "VERDICT").write_text(one + "\n", encoding="utf-8")


def stopped() -> bool:
    return (ROOT / "tmp" / "STOP").exists() or (ROOT / "tmp" / "ev1107" / "STOP").exists()


def select(bank: dict, ids: list[str]) -> list[dict]:
    table = probe.by_id(bank)
    missing = [item for item in ids if item not in table]
    if missing:
        raise ValueError(f"missing cases: {missing[:3]}")
    return [table[item] for item in ids]


def arm_block(rows_a: list[dict] | None, rows_b: list[dict] | None, dev_rows: list[dict] | None, gate: float) -> dict:
    block = {}
    if rows_a is not None:
        block["heldout_a"] = probe.summarize(rows_a, gate)
        block["heldout_a"]["ids_correct"] = [row["id"] for row in rows_a if row["correct"]]
        block["heldout_a"]["rows"] = rows_a
    if rows_b is not None:
        block["heldout_b"] = probe.summarize(rows_b, gate)
        block["heldout_b"]["ids_correct"] = [row["id"] for row in rows_b if row["correct"]]
        block["heldout_b"]["rows"] = rows_b
    if dev_rows is not None:
        block["dev"] = probe.summarize(dev_rows, gate)
    if rows_a is not None and rows_b is not None:
        block["n_correct"] = [block["heldout_a"]["n_correct"], block["heldout_b"]["n_correct"]]
    return block


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Live DSPy decision probe against local Ollama")
    parser.add_argument("--cases", type=Path, default=CASES_PATH)
    parser.add_argument("--out-dir", type=Path, default=HERE)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--base-url", default=OLLAMA)
    args = parser.parse_args(argv)

    out_dir = args.out_dir
    t0 = time.monotonic()
    log_lines: list[str] = []

    def log(message: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        line = f"{stamp} {message}"
        log_lines.append(line)
        print(line, file=sys.stderr, flush=True)

    receipt: dict = {
        "tool": "dspy",
        "model": args.model,
        "base_url": probe._root_url(args.base_url),
        "num_ctx": NUM_CTX,
        "max_tokens": MAX_TOKENS,
        "temperature": 0,
        "seed": SEED,
        "optimizer": "BootstrapFewShot",
        "optimizer_params": {
            "max_bootstrapped_demos": 4,
            "max_labeled_demos": 4,
            "max_rounds": 1,
            "max_errors": 8,
        },
        "phases": log_lines,
    }
    line = "STAY I1 live probe did not finish"
    server = None
    try:
        if stopped():
            line = "STAY I1 stopped before the live probe"
            return 0
        if probe._root_url(args.base_url) != OLLAMA:
            line = "STAY I1 refusing a base url that is not 127.0.0.1:11434"
            return 0
        ok, detail = probe.preflight_base(args.base_url, timeout=5)
        if not ok:
            line = f"STAY I1 {detail}"[:300]
            return 0
        bank = probe.load_bank(args.cases)
        gate = float(bank.get("conf_gate") or 0.85)
        split = probe.split_ids(probe.case_ids(bank), SEED)
        receipt["split"] = split
        receipt["conf_gate"] = gate
        train = select(bank, split["train"])
        dev = select(bank, split["dev"])
        held = select(bank, split["heldout"])

        ps_before = ollama_ps()
        receipt["ollama_ps_before"] = ps_before.strip()
        already = model_loaded(ps_before, args.model)
        receipt["loaded_by_us"] = not already
        need = MODEL_GIB + MEM_MARGIN_GIB
        if not already:
            busy = wait_for_memory(need, log)
            if busy:
                line = f"STAY I1 {busy}"
                receipt["mem_available_gib"] = mem_available_gib()
                return 0
        receipt["mem_available_gib"] = mem_available_gib()
        keep_alive = None if already else "2m"
        receipt["keep_alive"] = keep_alive

        started = time.monotonic()
        receipt["model_clock_start"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        log("preload")
        loaded = preload(args.model, keep_alive)
        receipt["preload"] = loaded
        if loaded["status"] != 200:
            line = f"STAY I1 preload failed status {loaded['status']}"
            return 0
        if loaded["thinking_chars"] > 0 or (loaded["eval_count"] or 0) > 40:
            line = "STAY I1 thinking stayed on after think false"
            return 0
        ps_after = ollama_ps()
        receipt["ollama_ps_after_preload"] = ps_after.strip()
        _status, ps_blob = http_json("GET", OLLAMA + "/api/ps", timeout=10)
        ctx = context_from_ps_api(ps_blob, args.model)
        ctx_cli = context_from_cli(ps_after, args.model)
        receipt["context_after_preload"] = ctx if ctx is not None else ctx_cli
        receipt["api_ps_after_preload"] = ps_blob.get("models")
        seen_ctx = max([item for item in (ctx, ctx_cli) if item is not None], default=None)
        if seen_ctx is not None and seen_ctx > MAX_CTX:
            line = f"STAY I1 context {seen_ctx} exceeds {MAX_CTX}"
            return 0

        isolate_home()
        import dspy

        receipt["dspy"] = importlib.metadata.version("dspy")
        receipt["litellm"] = importlib.metadata.version("litellm")
        deadline = started + MODEL_BUDGET_S
        server, port = start_proxy(keep_alive)
        lm = dspy.LM(
            f"openai/{args.model}",
            api_base=f"http://127.0.0.1:{port}/v1",
            api_key="local",
            temperature=0,
            max_tokens=MAX_TOKENS,
            cache=False,
            num_retries=0,
            timeout=CALL_TIMEOUT_S,
        )
        dspy.configure(lm=lm, adapter=dspy.JSONAdapter())
        receipt["adapter"] = "JSONAdapter"
        receipt["transport"] = "ollama /api/chat"
        baseline = build_program(dspy)
        log("baseline held-out A")
        base_a = score_cases(baseline, held, gate, deadline)
        _status, ps_mid = http_json("GET", OLLAMA + "/api/ps", timeout=10)
        ctx_mid = context_from_ps_api(ps_mid, args.model)
        receipt["context_after_first_score"] = ctx_mid
        if ctx_mid is not None and ctx_mid > MAX_CTX:
            line = f"STAY I1 context grew to {ctx_mid}"
            receipt["baseline"] = arm_block(base_a, None, None, gate)
            return 0
        log("baseline held-out B")
        base_b = score_cases(baseline, held, gate, deadline)
        log("baseline dev")
        base_dev = score_cases(baseline, dev, gate, deadline)
        receipt["baseline"] = arm_block(base_a, base_b, base_dev, gate)

        if time.monotonic() > deadline:
            raise TimeCap()
        log("bootstrap")
        student = build_program(dspy)
        optimizer = dspy.BootstrapFewShot(
            metric=metric_factory(deadline),
            max_bootstrapped_demos=4,
            max_labeled_demos=4,
            max_rounds=1,
            max_errors=8,
        )
        compiled = optimizer.compile(student, trainset=[example_of(case, dspy) for case in train])
        receipt["demos"] = demo_counts(compiled)
        if _demos_leave_train(compiled, train, held):
            line = "STAY I1 optimized demos included a held-out case"
            receipt["error"] = "held-out demo leak"
            return 0
        program_path = out_dir / "program.json"
        compiled.save(str(program_path))
        redact_program(program_path)

        log("optimized held-out A")
        opt_a = score_cases(compiled, held, gate, deadline)
        log("optimized held-out B")
        opt_b = score_cases(compiled, held, gate, deadline)
        log("optimized dev")
        opt_dev = score_cases(compiled, dev, gate, deadline)
        receipt["optimized"] = arm_block(opt_a, opt_b, opt_dev, gate)
        decided = probe.verdict(receipt["baseline"]["n_correct"], receipt["optimized"]["n_correct"])
        receipt["verdict_math"] = {key: decided[key] for key in ("noise", "gain", "need", "promote")}
        line = decided["line"]
        receipt["lm_history"] = len(getattr(lm, "history", []) or [])
        return 0
    except TimeCap:
        line = "STAY I1 time-cap before both arms finished two held-out scores"
        receipt["error"] = "time-cap"
        return 0
    except ContextCap as exc:
        line = f"STAY I1 context grew to {exc.ctx}"
        receipt["error"] = str(exc)
        return 0
    except Exception as exc:  # noqa: BLE001 -- record the failure as STAY instead of a fake score
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        receipt["traceback"] = traceback.format_exc()[-2000:]
        line = f"STAY I1 live probe failed {type(exc).__name__}"
        log(receipt["error"])
        return 0
    finally:
        if server is not None:
            server.shutdown()
        receipt["wall_s"] = round(time.monotonic() - t0, 1)
        receipt["finished"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        write_outputs(out_dir, receipt, line)
        print(line, flush=True)


if __name__ == "__main__":
    sys.exit(main())
