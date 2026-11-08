#!/usr/bin/env python3
"""ev1107 HiRoute probe. Hedge phase calls no model. Live phase must run under scripts/model_lock.sh.

The grant file is read into a request header and never printed.
"""
import json
import os
import re
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CACHE = Path("/home/mark/.cache/pfy/tools/hiroute")
GRANT = CACHE / "grant.token"
DIAG = CACHE / "home/.local/state/hiroute/diagnostics/daemon/current.jsonl"
GATEWAY_FILE = CACHE / "home/.local/state/hiroute/gateway-listener.json"
DECISION_LOG = CACHE / "decision-events.jsonl"
MODEL = "qwen2.5-coder:7b-instruct"
ALIAS = "hiroute-eval-difficulty-route"
GIB = 1024 ** 3


def load_prompts():
    rows = []
    for line in (HERE / "prompts.jsonl").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def gateway():
    data = json.loads(GATEWAY_FILE.read_text(encoding="utf-8"))
    applied = data.get("applied") or {}
    host = applied.get("address") or "127.0.0.1"
    port = int(applied["port"])
    if host != "127.0.0.1":
        raise SystemExit("gateway is not loopback")
    return "http://%s:%d" % (host, port)


def grant():
    token = GRANT.read_text(encoding="utf-8").strip()
    if not token:
        raise SystemExit("grant file is empty")
    return token


def scrub(text):
    text = re.sub(r"hr_[A-Za-z0-9_\-]{6,}", "<grant>", text)
    text = re.sub(r"(?i)(authorization|x-hiroute-token|bearer)\s*[:=]?\s*\S+", r"\1=<redacted>", text)
    return text[:500]


def post_responses(base, token, prompt, timeout):
    body = json.dumps({
        "model": ALIAS,
        "input": prompt,
        "stream": False,
        "max_output_tokens": 64,
    }).encode("utf-8")
    req = urllib.request.Request(
        base + "/v1/responses",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-HiRoute-Token": token,
        },
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        status = exc.code
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        payload = {"_unparsed": scrub(raw.decode("utf-8", errors="replace"))}
    return status, elapsed_ms, payload


def collect_text(obj, out):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in ("text", "content", "output_text") and isinstance(value, str):
                out.append(value)
            else:
                collect_text(value, out)
    elif isinstance(obj, list):
        for item in obj:
            collect_text(item, out)


def token_ok(answer, token):
    if token == "STUB_PREMIUM":
        return "STUB_PREMIUM" in answer
    return re.search(r"(?<!\w)" + re.escape(token) + r"(?!\w)", answer) is not None


def diag_from(offset):
    if not DIAG.is_file():
        return []
    data = DIAG.read_bytes()
    if offset > len(data):
        offset = 0
    chunk = data[offset:]
    events = []
    for line in chunk.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def route_from(events):
    native = None
    outcome = None
    for event in events:
        body = event.get("event") or {}
        if "attempt_begin" in body:
            native = body["attempt_begin"].get("native_model")
        if "attempt_end" in body:
            outcome = body["attempt_end"].get("outcome")
            native = body["attempt_end"].get("native_model") or native
        if "request_end" in body and outcome is None:
            outcome = body["request_end"].get("outcome")
    if native == "premium-stub":
        route = "primary"
    elif native == MODEL:
        route = "economy"
    else:
        route = None
    return route, native, outcome


def decision_lines():
    if not DECISION_LOG.is_file():
        return []
    rows = []
    for line in DECISION_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def mem_available_bytes():
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            kb = int(line.split()[1])
            return kb * 1024
    raise SystemExit("MemAvailable missing")


def model_bytes():
    listed = subprocess.run(
        ["/usr/local/bin/ollama", "list"],
        check=False,
        capture_output=True,
        text=True,
    )
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
        size = 6.0
    # ollama prints decimal GB. Round up so the floor is not short.
    return int((size + 0.3) * 1_000_000_000)


def ollama_ps_names():
    shown = subprocess.run(
        ["/usr/local/bin/ollama", "ps"],
        check=False,
        capture_output=True,
        text=True,
    )
    names = []
    for line in (shown.stdout or "").splitlines()[1:]:
        parts = line.split()
        if parts:
            names.append(parts[0])
    return names


def model_loaded():
    return MODEL in ollama_ps_names()


def wait_for_memory(need):
    deadline = time.time() + 30 * 60
    while True:
        avail = mem_available_bytes()
        if avail >= need:
            return avail, False
        if time.time() >= deadline:
            return avail, True
        time.sleep(30)


def kill_ours_on(port):
    shown = subprocess.run(["ss", "-ltnp"], check=False, capture_output=True, text=True)
    pids = set(re.findall(r"pid=(\d+)", shown.stdout or ""))
    # ss mixes every listener. Match the port line only.
    for line in (shown.stdout or "").splitlines():
        if "127.0.0.1:%d" % port not in line:
            continue
        for pid in re.findall(r"pid=(\d+)", line):
            pids = {pid}
    for pid in pids:
        cwd = os.readlink("/proc/%s/cwd" % pid) if Path("/proc/%s/cwd" % pid).exists() else ""
        if cwd != str(ROOT):
            continue
        cmdline = Path("/proc/%s/cmdline" % pid).read_bytes().replace(b"\0", b" ").decode("utf-8", errors="replace")
        if "python" not in cmdline:
            continue
        os.kill(int(pid), 15)
        for _ in range(50):
            if not Path("/proc/%s" % pid).exists():
                return True
            time.sleep(0.05)
        os.kill(int(pid), 9)
        return True
    return False


def start_adapter(keep_alive):
    kill_ours_on(44564)
    env = os.environ.copy()
    env["PFY_MODEL_LOCK_HELD"] = "1"
    env["HIROUTE_DECISION_MODEL"] = MODEL
    if keep_alive:
        env["HIROUTE_KEEP_ALIVE"] = keep_alive
    else:
        env.pop("HIROUTE_KEEP_ALIVE", None)
    log = open(CACHE / "decision-adapter.log", "a", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, str(CACHE / "py/decision_adapter.py")],
        env=env,
        stdout=log,
        stderr=log,
        cwd=str(ROOT),
    )
    for _ in range(50):
        try:
            urllib.request.urlopen("http://127.0.0.1:44564/health", timeout=0.2)
        except urllib.error.HTTPError:
            return proc
        except Exception:
            if proc.poll() is not None:
                raise SystemExit("decision adapter exited %s" % proc.returncode)
            time.sleep(0.05)
    # No /health route. A refused connection means it is not up. A 404 means it is.
    return proc


def hedge_one(task):
    # ./pfy is a shell wrapper. --state belongs to pfylib and is not a pfy command.
    # PFY_STATE_DIR keeps the ledger out of ~/.pfy-mentat. No --record, so nothing is written.
    env = os.environ.copy()
    env["PFY_STATE_DIR"] = str(HERE / "hedge-state")
    proc = subprocess.run(
        [
            str(ROOT / "pfy"),
            "hedge", "decide",
            "--task", task,
            "--local", "ready",
            "--budget", "100000",
            "--json",
        ],
        cwd=str(ROOT),
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "lane": None, "error": scrub(proc.stdout + proc.stderr)}


def phase_hedge():
    rows = []
    for prompt in load_prompts():
        decided = hedge_one(prompt["hedge_task"])
        rows.append({
            "id": prompt["id"],
            "kind": prompt["kind"],
            "hedge_task": prompt["hedge_task"],
            "hedge_lane": decided.get("lane"),
            "hedge_ok": bool(decided.get("ok")),
            "hedge_reason": decided.get("reason"),
        })
        print("%s hedge %s" % (prompt["id"], decided.get("lane")))
    (HERE / "hedge.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def run_one(base, token, prompt, timeout, hedge_lane=None):
    before = DIAG.stat().st_size if DIAG.is_file() else 0
    decisions_before = len(decision_lines())
    status, client_ms, payload = post_responses(base, token, prompt["prompt"], timeout)
    texts = []
    collect_text(payload, texts)
    answer = "\n".join(texts)
    route, native, outcome = route_from(diag_from(before))
    new_decisions = decision_lines()[decisions_before:]
    decision = new_decisions[-1] if new_decisions else {}
    decision_ms = decision.get("decision_ms")
    answer_ms = None
    if isinstance(decision_ms, int):
        answer_ms = max(0, client_ms - decision_ms)
    route_ok = route == prompt["expect_route"]
    check_ok = token_ok(answer, prompt["expect_token"]) if answer else False
    return {
        "id": prompt["id"],
        "kind": prompt["kind"],
        "expect_route": prompt["expect_route"],
        "route": route,
        "native_model": native,
        "upstream_outcome": outcome,
        "http_status": status,
        "route_ok": route_ok,
        "check_ok": check_ok,
        "decision_ms": decision_ms,
        "answer_ms": answer_ms,
        "client_ms": client_ms,
        "decision_parse_ok": decision.get("parse_ok"),
        "probabilities": decision.get("probabilities"),
        "hedge_lane": hedge_lane,
        "hedge_agree": (route == "economy" and hedge_lane == "local") or (route == "primary" and hedge_lane == "cloud"),
        "answer_excerpt": scrub(answer)[:180],
    }


def summarize(rows, meta):
    decided = [row["decision_ms"] for row in rows if isinstance(row.get("decision_ms"), int)]
    route_hits = sum(1 for row in rows if row.get("route_ok"))
    check_hits = sum(1 for row in rows if row.get("check_ok"))
    agree = sum(1 for row in rows if row.get("hedge_agree"))
    median = statistics.median(decided) if decided else None
    promote = (
        route_hits >= 16
        and median is not None
        and median < 2000
        and len(rows) == 20
        and len(decided) == 20
    )
    if meta.get("host_busy"):
        verdict = "STAY I0 HOST-BUSY MemAvailable stayed under model size + 25 GiB"
    elif promote:
        verdict = "PROMOTE I2 routing %d/20 and decision median %d ms" % (route_hits, median)
    else:
        shown = "none" if median is None else "%d ms" % median
        verdict = "STAY I0 routing %d/20 decision median %s" % (route_hits, shown)
    summary = {
        "prompts": len(rows),
        "route_ok": route_hits,
        "check_ok": check_hits,
        "hedge_agree": agree,
        "decision_median_ms": median,
        "decision_samples": len(decided),
        "promote": promote,
        "verdict": verdict,
        **meta,
    }
    return summary


def phase_live():
    if os.environ.get("PFY_MODEL_LOCK_HELD") != "1":
        raise SystemExit("live phase requires scripts/model_lock.sh")
    need = model_bytes() + 25 * GIB
    loaded = model_loaded()
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
    (HERE / "live-meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    if busy:
        summary = summarize([], meta)
        (HERE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        (HERE / "results.jsonl").write_text("", encoding="utf-8")
        print(summary["verdict"])
        return
    proc = start_adapter(keep)
    rows = []
    try:
        base = gateway()
        token = grant()
        hedge = {}
        hedge_path = HERE / "hedge.jsonl"
        if hedge_path.is_file():
            for line in hedge_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    item = json.loads(line)
                    hedge[item["id"]] = item.get("hedge_lane")
        for prompt in load_prompts():
            row = run_one(base, token, prompt, timeout=120, hedge_lane=hedge.get(prompt["id"]))
            rows.append(row)
            (HERE / "results.jsonl").write_text(
                "".join(json.dumps(item) + "\n" for item in rows),
                encoding="utf-8",
            )
            print("%s route=%s ok=%s decision_ms=%s http=%s" % (
                row["id"], row["route"], row["route_ok"], row["decision_ms"], row["http_status"],
            ), flush=True)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    summary = summarize(rows, meta)
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(summary["verdict"])


def phase_wire():
    """One premium request. The constant decider must still be the complex stub. No Ollama."""
    base = gateway()
    token = grant()
    status, elapsed, payload = post_responses(
        base, token, "Reply with the single word ping.", timeout=20,
    )
    texts = []
    collect_text(payload, texts)
    answer = "\n".join(texts)
    print("http", status, "ms", elapsed, "has_stub", "STUB_PREMIUM" in answer)
    if status != 200 or "STUB_PREMIUM" not in answer:
        err = payload.get("error") if isinstance(payload, dict) else None
        print("error", json.dumps(err)[:300] if err else scrub(json.dumps(payload)[:300]))
        raise SystemExit(1)


def main():
    phase = sys.argv[1] if len(sys.argv) > 1 else "live"
    if phase == "hedge":
        phase_hedge()
    elif phase == "live":
        phase_live()
    elif phase == "wire":
        phase_wire()
    else:
        raise SystemExit("usage: probe.py hedge|wire|live")


if __name__ == "__main__":
    main()
