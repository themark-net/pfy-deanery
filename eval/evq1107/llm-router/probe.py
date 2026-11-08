#!/usr/bin/env python3
"""evq1107 llm-router probe.

Offline phase classifies the HiRoute prompt set and builds the hook chain.
It does not call Ollama. The live phase drafts the trivial prompts on the
local model and must run under scripts/model_lock.sh.

Route rule, fixed before the run: complexity simple counts as economy
(HiRoute local). Any other complexity counts as primary. The hook chain is
recorded beside that label. It is not used to change the label.
"""
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CACHE = Path("/home/mark/.cache/pfy/tools/llm-router")
VENV_PY = CACHE / "venv/bin/python"
WHEEL = CACHE / "wheels/llm_routing-15.4.0-py3-none-any.whl"
WHEEL_SHA256 = "72938a98e11bb75311b741afc6a1337f38ef712b891dba319160be1712cf6a41"
PIN = "15.4.0"
MODEL = "qwen2.5-coder:7b-instruct"
GIB = 1024 ** 3
REAL_STATE = Path("/home/mark/.llm-router")
KEY_ENV = (
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "ANTHROPIC_API_KEY",
    "PERPLEXITY_API_KEY",
    "PERPLEXITYAI_API_KEY",
    "MISTRAL_API_KEY",
    "DEEPSEEK_API_KEY",
    "GROQ_API_KEY",
    "TOGETHER_API_KEY",
    "XAI_API_KEY",
    "COHERE_API_KEY",
    "OPENROUTER_API_KEY",
    "HUGGINGFACE_API_KEY",
    "HF_TOKEN",
    "MOONSHOT_API_KEY",
    "MINIMAX_API_KEY",
    "ZHIPU_API_KEY",
    "ARCEE_API_KEY",
)


def isolate():
    """Point the tool at the cache home and drop provider keys from this process."""
    home = CACHE / "home"
    for path in (home, CACHE / "xdg-config", CACHE / "xdg-cache", CACHE / "xdg-data", CACHE / "tmp"):
        path.mkdir(parents=True, exist_ok=True)
    os.environ["HOME"] = str(home)
    os.environ["XDG_CONFIG_HOME"] = str(CACHE / "xdg-config")
    os.environ["XDG_CACHE_HOME"] = str(CACHE / "xdg-cache")
    os.environ["XDG_DATA_HOME"] = str(CACHE / "xdg-data")
    os.environ["TMPDIR"] = str(CACHE / "tmp")
    os.environ["LLM_ROUTER_HOME"] = str(home / ".llm-router")
    os.environ["LLM_ROUTER_DIRECT_EXECUTION"] = "false"
    os.environ["LLM_ROUTER_OLLAMA_MODEL"] = MODEL
    os.environ["PFY_STATE_DIR"] = str(ROOT / "tmp" / "llm-router-hedge")
    dropped = 0
    for name in KEY_ENV:
        if os.environ.pop(name, None) is not None:
            dropped += 1
    return dropped


def reexec_venv():
    if not VENV_PY.is_file():
        raise SystemExit("venv python missing at %s" % VENV_PY)
    # The venv python is a symlink to the system interpreter, so resolving
    # both paths says they are the same binary. sys.prefix is the venv root.
    if Path(sys.prefix).resolve() == (CACHE / "venv").resolve():
        return
    os.execv(str(VENV_PY), [str(VENV_PY), *sys.argv])


def wheel_sha256():
    digest = hashlib.sha256(WHEEL.read_bytes()).hexdigest()
    if digest != WHEEL_SHA256:
        raise SystemExit("wheel sha256 %s != pin" % digest)
    return digest


def load_prompts():
    rows = []
    for line in (HERE / "prompts.jsonl").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    if len(rows) != 20:
        raise SystemExit("expected 20 prompts, got %d" % len(rows))
    return rows


def route_of(complexity):
    return "economy" if complexity == "simple" else "primary"


def token_ok(answer, token):
    if token == "STUB_PREMIUM":
        return "STUB_PREMIUM" in answer
    return re.search(r"(?<!\w)" + re.escape(token) + r"(?!\w)", answer) is not None


def chain_names(specs):
    return ["%s/%s" % (spec.provider, spec.model) for spec in specs]


def classify_rows(prompts):
    from llm_router.classify import HOOK_LIVE_POLICY, classify_signals, reset_low_signal_counters
    from llm_router.classify import low_signal_classifications
    from llm_router.hooks.chain_builder import build_chain

    reset_low_signal_counters()
    warm_started = time.perf_counter()
    classify_signals("warmup")
    warmup_ms = (time.perf_counter() - warm_started) * 1000
    reset_low_signal_counters()

    rows = []
    times = []
    for prompt in prompts:
        started = time.perf_counter()
        signal = classify_signals(prompt["prompt"])
        elapsed_ms = (time.perf_counter() - started) * 1000
        times.append(elapsed_ms)
        live = classify_signals(prompt["prompt"], HOOK_LIVE_POLICY)
        specs = build_chain(signal.complexity.value, "green", signal.task_type.value)
        names = chain_names(specs)
        got = route_of(signal.complexity.value)
        rows.append({
            "id": prompt["id"],
            "kind": prompt["kind"],
            "expect_route": prompt["expect_route"],
            "hedge_task": prompt["hedge_task"],
            "task_type": signal.task_type.value,
            "complexity": signal.complexity.value,
            "confident": bool(signal.confident),
            "score": int(signal.score),
            "hook_live_complexity": live.complexity.value,
            "policy_agree": signal.complexity.value == live.complexity.value,
            "route": got,
            "route_ok": got == prompt["expect_route"],
            "classify_ms": round(elapsed_ms, 3),
            "chain": names,
            "chain_first": names[0] if names else "",
            "chain_leads_ollama": bool(names) and names[0].startswith("ollama/"),
        })
    low, total = low_signal_classifications()
    # The timed pass is one call per prompt. The hook-live pass is a second
    # call, so the counter covers both. Report the timed pass only.
    return rows, {
        "warmup_ms": round(warmup_ms, 3),
        "classify_median_ms": round(statistics.median(times), 3),
        "classify_sum_ms": round(sum(times), 3),
        "classify_max_ms": round(max(times), 3),
        "low_signal_on_timed_pass": sum(1 for row in rows if not row["confident"]),
        "counter_low_signal": low,
        "counter_total": total,
    }


def hedge_rows(rows):
    sys.path.insert(0, str(ROOT))
    from pfylib.hedge import decide

    local = {"engine": "ollama", "base_url": "http://127.0.0.1:11434", "status": "ready"}
    state = ROOT / "tmp" / "llm-router-hedge"
    out = []
    for row in rows:
        decided = decide(row["hedge_task"], local=local, budget=100000, state=state)
        lane = decided.get("lane")
        agree = (row["route"] == "economy" and lane == "local") or (
            row["route"] == "primary" and lane == "cloud"
        )
        row["hedge_lane"] = lane
        row["hedge_ok"] = bool(decided.get("ok"))
        row["hedge_agree"] = agree
        out.append(row)
    return out


def secret_rows():
    from llm_router.decisions.engine import Decision, DecisionEngine
    from llm_router.signals.pii import PiiSignal

    shapes = {
        "clean": "Reply with the single digit 4 and nothing else.",
        "openai_key": "sk-proj-" + ("A" * 24),
        "private_key_block": "-----BEGIN PRIVATE KEY-----\nplaceholder\n-----END PRIVATE KEY-----",
        "github_token": "ghp_" + ("a" * 36),
    }
    signal = PiiSignal()
    # The package docstring says a firing PiiSignal forces local_only.
    # Nothing in llm-routing 15.4.0 constructs PiiSignal or DecisionEngine
    # outside that docstring, so this rule is the probe's, not a shipped route.
    engine = DecisionEngine([
        Decision("secrets_local", "SINGLE", ("pii_secret",), "local_only", 0),
    ])
    rows = []
    for name, text in shapes.items():
        score = signal.evaluate(text)
        choice = engine.choose({"pii_secret": score})
        rows.append({
            "name": name,
            "fires": bool(score.fires),
            "score": score.score,
            "evidence": score.evidence,
            "probe_rule_action": choice.action,
            "expect_fire": name != "clean",
            "production_caller": False,
        })
    return rows


def run_demo():
    binary = CACHE / "venv/bin/llm-router"
    started = time.perf_counter()
    proc = subprocess.run(
        [str(binary), "demo"],
        cwd=str(CACHE / "tmp"),
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
        env=os.environ.copy(),
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    text = proc.stdout + proc.stderr
    return {
        "exit": proc.returncode,
        "ms": round(elapsed_ms, 1),
        "prints_table": "Complexity" in text and "Model" in text,
        "tail": [line.rstrip() for line in text.strip().splitlines()][-6:],
    }


def cache_bytes():
    proc = subprocess.run(["du", "-sb", str(CACHE)], check=False, capture_output=True, text=True)
    try:
        return int(proc.stdout.split()[0])
    except (IndexError, ValueError):
        return None


def offline():
    import llm_router

    if getattr(llm_router, "__version__", "") != PIN:
        raise SystemExit("llm_router version %r is not %s" % (getattr(llm_router, "__version__", ""), PIN))
    prompts = load_prompts()
    rows, timing = classify_rows(prompts)
    rows = hedge_rows(rows)
    secrets = secret_rows()
    demo = run_demo()
    route_ok = sum(1 for row in rows if row["route_ok"])
    hedge_agree = sum(1 for row in rows if row["hedge_agree"])
    ollama_first = sum(1 for row in rows if row["chain_leads_ollama"])
    policy_agree = sum(1 for row in rows if row["policy_agree"])
    secret_ok = sum(1 for row in secrets if row["expect_fire"] == row["fires"])
    summary = {
        "version": PIN,
        "wheel_sha256": wheel_sha256(),
        "wheel_bytes": WHEEL.stat().st_size,
        "cache_bytes": cache_bytes(),
        "prompts": len(rows),
        "route_ok": route_ok,
        "hedge_agree": hedge_agree,
        "ollama_first": ollama_first,
        "policy_agree": policy_agree,
        "secret_ok": secret_ok,
        "secret_rows": len(secrets),
        "real_state_absent": not REAL_STATE.exists(),
        "provider_keys_dropped": int(os.environ.get("PFY_LLM_ROUTER_KEYS_DROPPED") or "0"),
        "direct_execution_env": os.environ.get("LLM_ROUTER_DIRECT_EXECUTION"),
        **timing,
        "demo": demo,
    }
    payload = {"summary": summary, "rows": rows, "secrets": secrets}
    if (HERE / "results.json").is_file():
        previous = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
        if "live" in previous:
            payload["live"] = previous["live"]
    (HERE / "results.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print("route %d/20 hedge %d/20 ollama_first %d/20 median %.3f ms" % (
        route_ok, hedge_agree, ollama_first, timing["classify_median_ms"]))
    print("secrets %d/%d demo %s real_state_absent %s" % (
        secret_ok, len(secrets), demo["exit"], summary["real_state_absent"]))


def mem_available_bytes():
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise SystemExit("MemAvailable missing")


def ollama_bin():
    found = shutil.which("ollama")
    if found:
        return found
    fallback = Path("/usr/local/bin/ollama")
    if fallback.is_file():
        return str(fallback)
    raise SystemExit("ollama not on PATH")


def model_bytes():
    listed = subprocess.run([ollama_bin(), "list"], check=False, capture_output=True, text=True)
    size = None
    for line in (listed.stdout or "").splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 3 and parts[0] == MODEL:
            try:
                size = float(parts[2])
            except ValueError:
                size = None
            break
    if size is None:
        size = 4.7
    return int((size + 0.3) * 1_000_000_000)


def ollama_ps_names():
    shown = subprocess.run([ollama_bin(), "ps"], check=False, capture_output=True, text=True)
    names = []
    for line in (shown.stdout or "").splitlines()[1:]:
        parts = line.split()
        if parts:
            names.append(parts[0])
    return names


def wait_for_memory(need):
    deadline = time.time() + 30 * 60
    while True:
        avail = mem_available_bytes()
        if avail >= need:
            return avail, False
        if time.time() >= deadline:
            return avail, True
        time.sleep(30)


def ollama_chat(prompt, keep, n_predict):
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0, "num_predict": n_predict},
    }
    if keep:
        body["keep_alive"] = keep
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        status = exc.code
    elapsed_ms = (time.perf_counter() - started) * 1000
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload = {}
    message = payload.get("message") or {}
    content = message.get("content") or ""
    return status, elapsed_ms, content.replace("\n", " ")[:180]


def live():
    if os.environ.get("PFY_MODEL_LOCK_HELD") != "1":
        raise SystemExit("live phase requires scripts/model_lock.sh")
    results_path = HERE / "results.json"
    if not results_path.is_file():
        raise SystemExit("run the offline phase first")
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    by_id = {row["id"]: row for row in payload["rows"]}
    prompts = {row["id"]: row for row in load_prompts()}
    # Draft the ten trivial prompts. Those are the ones HiRoute sent to the
    # local model. Misrouted hard prompts stay in the route count only.
    targets = [row for row in payload["rows"] if row["kind"] == "trivial"]
    need = model_bytes() + 25 * GIB
    loaded = MODEL in ollama_ps_names()
    if loaded:
        avail = mem_available_bytes()
        busy = False
        keep = ""
    else:
        avail, busy = wait_for_memory(need)
        keep = "" if busy else "2m"
    meta = {
        "model": MODEL,
        "model_was_loaded": loaded,
        "keep_alive": keep or None,
        "mem_available_bytes": avail,
        "mem_need_bytes": need,
        "host_busy": busy,
        "ollama_ps": ollama_ps_names(),
    }
    drafts = []
    if not busy:
        for row in targets:
            prompt = prompts[row["id"]]
            status, elapsed_ms, content = ollama_chat(prompt["prompt"], keep, 16)
            drafts.append({
                "id": row["id"],
                "http_status": status,
                "answer_ms": round(elapsed_ms, 1),
                "check_ok": token_ok(content, prompt["expect_token"]) if status == 200 else False,
                "answer_excerpt": content,
                "classifier_route": by_id[row["id"]]["route"],
            })
            print("%s %s %.0f ms %s" % (row["id"], status, elapsed_ms, drafts[-1]["check_ok"]))
    check_ok = sum(1 for row in drafts if row["check_ok"])
    meta["drafts"] = len(drafts)
    meta["check_ok"] = check_ok
    payload["live"] = {"meta": meta, "drafts": drafts}
    results_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if busy:
        print("HOST-BUSY")
    else:
        print("drafts %d/%d" % (check_ok, len(drafts)))


def main():
    # Count key removals once, before re-exec. The venv process inherits the
    # cleaned environment, so a second isolate() would report zero.
    if "PFY_LLM_ROUTER_KEYS_DROPPED" not in os.environ:
        os.environ["PFY_LLM_ROUTER_KEYS_DROPPED"] = str(isolate())
    else:
        isolate()
    reexec_venv()
    if len(sys.argv) == 1:
        offline()
        return
    if len(sys.argv) == 2 and sys.argv[1] == "live":
        live()
        return
    raise SystemExit("usage: probe.py [live]")


if __name__ == "__main__":
    main()
