"""Hedge policy: spend local compute first, cloud credits only when local can't (ADR-0017).

Inputs
  task    ``bulk`` | ``hard`` | ``interactive``
  local   ``{"engine","base_url","status"}`` from ``scripts/detect-local-runtime.sh``
          (``status == "ready"`` is the only value that counts as available)
  budget  ``PFY_CLOUD_BUDGET`` -- integer **credits** the operator allows for cloud
          lanes in this ledger period. Unit is operator-defined; by default one
          cloud decision costs ``PFY_CLOUD_TASK_COST`` credits (default 1).
          Unset/0 means: no cloud spend unless nothing else can run -- and then
          it still FAILs, because 0 remaining is 0.
  ledger  ``$PFY_STATE_DIR/hedge-ledger.json`` -- append-only spend entries.
  profile ``DEPLOY_PROFILE=local-only`` forbids cloud outright (ADR-0006/0011).

Rules (deterministic, offline)
  1. ``hard``  -> cloud if budget remains, else local if ready, else FAIL.
  2. others    -> local if ready, else cloud if budget remains, else FAIL.
  3. FAIL always carries a next step; the policy never fakes a lane.

``llamacpp-nommap`` is a named local server lane (start / health / stop).
It is not one of the spend lanes in ``LANES``. The default model stays
``qwen3.6:35b`` on Ollama. ``qwen3-coder-next`` is opt-in via this lane.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import registry

TASKS = ("bulk", "hard", "interactive")
LANES = ("local", "cloud")
LEDGER_FILE = "hedge-ledger.json"
DEFAULT_TASK_COST = 1


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _int_env(key: str, default: int) -> int:
    raw = str(os.environ.get(key) or "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def budget_from_env() -> int:
    return _int_env("PFY_CLOUD_BUDGET", 0)


def task_cost() -> int:
    return max(1, _int_env("PFY_CLOUD_TASK_COST", DEFAULT_TASK_COST))


def profile() -> str:
    return str(os.environ.get("DEPLOY_PROFILE") or "").strip().lower()


# ---------------------------------------------------------------- detect ---

def detect_local(root_dir: Path | None = None, *, timeout: float = 6.0) -> dict:
    """Run scripts/detect-local-runtime.sh; any failure is an honest ``missing``."""
    script = registry.root(root_dir) / "scripts" / "detect-local-runtime.sh"
    missing = {"engine": "none", "base_url": "", "status": "missing"}
    if not script.is_file():
        return dict(missing, error="detector missing")
    try:
        p = subprocess.run(["bash", str(script)], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return dict(missing, error=str(e)[:120])
    try:
        data = json.loads((p.stdout or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        return dict(missing, error="detector output not JSON")
    if not isinstance(data, dict):
        return missing
    return {
        "engine": str(data.get("engine") or "none"),
        "base_url": str(data.get("base_url") or ""),
        "status": str(data.get("status") or "missing"),
    }


# ---------------------------------------------------------------- ledger ---

def ledger_path(state: Path | None = None) -> Path:
    return registry.state_dir(state) / LEDGER_FILE


def load_ledger(state: Path | None = None) -> dict:
    path = ledger_path(state)
    empty = {"version": 1, "entries": [], "spent": 0}
    if not path.is_file():
        return empty
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(empty, error="ledger unreadable; treating as empty")
    if not isinstance(data, dict):
        return empty
    entries = [e for e in (data.get("entries") or []) if isinstance(e, dict)]
    spent = sum(int(e.get("amount") or 0) for e in entries if e.get("lane") == "cloud")
    return {"version": 1, "entries": entries, "spent": spent}


def save_ledger(ledger: dict, state: Path | None = None) -> Path:
    path = ledger_path(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated": _now(),
        "spent": int(ledger.get("spent") or 0),
        "entries": list(ledger.get("entries") or []),
    }
    text = json.dumps(payload, indent=2) + "\n"
    # Temp file + replace so a symlink at path is swapped, not followed.
    fd, tmpname = tempfile.mkstemp(prefix=".hedge-ledger-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmpname, path)
    except Exception:
        try:
            os.unlink(tmpname)
        except OSError:
            pass
        raise
    return path


def record(amount: int, *, lane: str = "cloud", task: str = "", note: str = "", state: Path | None = None, budget: int | None = None) -> dict:
    """Append a spend entry; returns remaining budget. Local entries cost 0 credits."""
    if lane not in LANES:
        return {"ok": False, "live": "FAIL", "error": "unknown lane %r" % lane, "next_step": "lane must be local|cloud"}
    amount = max(0, int(amount)) if lane == "cloud" else 0
    ledger = load_ledger(state)
    ledger["entries"].append({"when": _now(), "lane": lane, "task": task, "amount": amount, "note": note})
    ledger["spent"] = int(ledger.get("spent") or 0) + amount
    save_ledger(ledger, state)
    budget = budget_from_env() if budget is None else int(budget)
    remaining = max(0, budget - ledger["spent"])
    return {
        "ok": True,
        "live": "READY",
        "lane": lane,
        "amount": amount,
        "spent": ledger["spent"],
        "budget": budget,
        "remaining": remaining,
        "ledger": str(ledger_path(state)),
        "copy": "READY hedge record · %s %d · spent %d / budget %d · remaining %d" % (lane, amount, ledger["spent"], budget, remaining),
    }


def reset_ledger(state: Path | None = None) -> Path:
    return save_ledger({"entries": [], "spent": 0}, state)


# ---------------------------------------------------------------- decide ---

def decide(
    task: str,
    *,
    local: dict | None = None,
    budget: int | None = None,
    state: Path | None = None,
    cost: int | None = None,
    deploy_profile: str | None = None,
    root_dir: Path | None = None,
) -> dict:
    """Pick ``local`` or ``cloud`` for one task, or FAIL with a next step."""
    task = str(task or "").strip().lower()
    if task not in TASKS:
        return {
            "ok": False,
            "live": "FAIL",
            "lane": None,
            "task": task,
            "reason": "unknown task class %r" % task,
            "next_step": "use --task %s" % "|".join(TASKS),
            "copy": "FAIL hedge -- unknown task class %r · use %s" % (task, "|".join(TASKS)),
        }
    local = dict(local) if local is not None else detect_local(root_dir)
    local_ok = str(local.get("status") or "").lower() == "ready"
    budget = budget_from_env() if budget is None else max(0, int(budget))
    cost = task_cost() if cost is None else max(1, int(cost))
    prof = profile() if deploy_profile is None else str(deploy_profile).lower()
    ledger = load_ledger(state)
    spent = int(ledger.get("spent") or 0)
    remaining = max(0, budget - spent)
    cloud_ok = remaining >= cost and prof != "local-only"

    base = {
        "task": task,
        "local_engine": local.get("engine") or "none",
        "local_status": local.get("status") or "missing",
        "local_base_url": local.get("base_url") or "",
        "budget": budget,
        "spent": spent,
        "remaining": remaining,
        "cost": cost,
        "profile": prof or "(unset)",
        "ledger": str(ledger_path(state)),
    }

    def ready(lane: str, reason: str) -> dict:
        return dict(
            base,
            ok=True,
            live="READY",
            lane=lane,
            reason=reason,
            next_step="",
            copy="READY hedge · lane=%s · %s · remaining %d/%d" % (lane, reason, remaining, budget),
        )

    def fail(reason: str, next_step: str) -> dict:
        return dict(
            base,
            ok=False,
            live="FAIL",
            lane=None,
            reason=reason,
            next_step=next_step,
            copy="FAIL hedge -- %s · %s" % (reason, next_step),
        )

    local_word = "local ready (%s)" % base["local_engine"] if local_ok else "local %s" % base["local_status"]
    if task == "hard":
        if cloud_ok:
            return ready("cloud", "hard task; cloud within budget; %s as hedge" % local_word)
        if local_ok:
            why = "profile local-only" if prof == "local-only" else "no cloud budget (remaining %d < cost %d)" % (remaining, cost)
            return ready("local", "hard task but %s; hedging on %s" % (why, local_word))
        return fail(
            "hard task; %s; cloud unavailable (%s)" % (local_word, "profile local-only" if prof == "local-only" else "remaining %d < cost %d" % (remaining, cost)),
            "./pfy up (start local runtime) or set PFY_CLOUD_BUDGET",
        )
    if local_ok:
        return ready("local", "%s task; %s" % (task, local_word))
    if cloud_ok:
        return ready("cloud", "%s task; local %s; spending cloud credits" % (task, base["local_status"]))
    return fail(
        "%s task; local %s; cloud unavailable (%s)" % (task, base["local_status"], "profile local-only" if prof == "local-only" else "remaining %d < cost %d" % (remaining, cost)),
        "./pfy up (start local runtime) or set PFY_CLOUD_BUDGET",
    )


def decide_and_record(task: str, **kw) -> dict:
    """decide(); if the lane is cloud, debit one task cost into the ledger."""
    state = kw.get("state")
    rec = decide(task, **kw)
    if rec.get("ok") and rec.get("lane") == "cloud":
        r = record(int(rec.get("cost") or 1), lane="cloud", task=task, note="decide_and_record", state=state, budget=rec.get("budget"))
        rec["recorded"] = r.get("amount")
        rec["spent"] = r.get("spent")
        rec["remaining"] = r.get("remaining")
    return rec


# ------------------------------------------------------- llamacpp-nommap ---

LLAMACPP_NOMMAP = "llamacpp-nommap"
DEFAULT_OLLAMA_MODEL = "qwen3.6:35b"
NOMMAP_OPT_IN_MODEL = "qwen3-coder-next"
NOMMAP_SCRIPT_REL = Path("pipelines/dogfood/local-bench-4/run_nommap_server.sh")
_GIB = 1024 ** 3
NOMMAP_HEADROOM_BYTES = 25 * _GIB


def _fmt_gib(n: int) -> str:
    return "%.3f GiB" % (n / float(_GIB))


def mem_available_bytes(meminfo_text: str | None = None) -> int | None:
    """Bytes of MemAvailable. ``meminfo_text`` injects a fake /proc/meminfo."""
    if meminfo_text is None:
        try:
            meminfo_text = Path("/proc/meminfo").read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
    for line in meminfo_text.splitlines():
        if not line.startswith("MemAvailable:"):
            continue
        parts = line.split()
        if len(parts) < 2:
            return None
        try:
            return int(parts[1]) * 1024
        except ValueError:
            return None
    return None


def _lane_fail(reason: str, next_step: str) -> dict:
    return {
        "ok": False,
        "exit_code": 2,
        "lane": LLAMACPP_NOMMAP,
        "started": False,
        "reason": reason,
        "next_step": next_step,
    }


def start_llamacpp_nommap(
    model_path: str | os.PathLike | None,
    *,
    port: int = 18080,
    ctx: int = 4096,
    meminfo_text: str | None = None,
    root_dir: Path | None = None,
    popen=None,
) -> dict:
    """Start the no-mmap llama-server lane, or return exit code 2.

    Refuses when MemAvailable < model file size + 25 GiB. Does not spawn
    on that refusal. ``meminfo_text`` is a fake MemAvailable reading for tests.
    ``popen`` defaults to ``subprocess.Popen`` and is the only spawn path.
    """
    if not model_path:
        return _lane_fail(
            "llamacpp-nommap needs a GGUF path. Default model stays %s on Ollama. %s is opt-in on this lane."
            % (DEFAULT_OLLAMA_MODEL, NOMMAP_OPT_IN_MODEL),
            "pass the %s GGUF path. Do not load it while another model is resident." % NOMMAP_OPT_IN_MODEL,
        )
    path = Path(model_path)
    if not path.is_file():
        return _lane_fail(
            "model path is not a file: %s" % path,
            "pass a GGUF file for %s. %s stays on Ollama and is not started here."
            % (NOMMAP_OPT_IN_MODEL, DEFAULT_OLLAMA_MODEL),
        )
    script = registry.root(root_dir) / NOMMAP_SCRIPT_REL
    if not script.is_file():
        return _lane_fail(
            "nommap launcher missing: %s" % script,
            "restore %s" % NOMMAP_SCRIPT_REL,
        )
    avail = mem_available_bytes(meminfo_text)
    size = path.stat().st_size
    need = size + NOMMAP_HEADROOM_BYTES
    if avail is None:
        return _lane_fail(
            "MemAvailable unreadable; refusing %s" % LLAMACPP_NOMMAP,
            "inject or read MemAvailable before starting the lane",
        )
    if avail < need:
        return _lane_fail(
            "MemAvailable %s < model %s + 25 GiB (need %s); refusing %s"
            % (_fmt_gib(avail), _fmt_gib(size), _fmt_gib(need), LLAMACPP_NOMMAP),
            "free memory until MemAvailable covers the GGUF plus 25 GiB, then start one model",
        )
    argv = ["bash", str(script), str(path), str(int(port)), str(int(ctx))]
    spawn = popen or subprocess.Popen
    proc = spawn(argv, start_new_session=True)
    return {
        "ok": True,
        "exit_code": 0,
        "lane": LLAMACPP_NOMMAP,
        "started": True,
        "reason": "",
        "next_step": "",
        "model_path": str(path),
        "port": int(port),
        "base_url": "http://127.0.0.1:%d" % int(port),
        "pid": getattr(proc, "pid", None),
        "proc": proc,
        "argv": argv,
    }


def health_llamacpp_nommap(base_url: str, *, timeout: float = 2.0) -> dict:
    """GET ``{base}/v1/models``. ``base_url`` has no ``/v1`` suffix."""
    import urllib.error
    import urllib.request

    base = str(base_url or "").strip().rstrip("/")
    if not base:
        return _lane_fail("no base_url for health", "pass the lane base_url (http://127.0.0.1:<port>)")
    url = base + "/v1/models"
    req = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read(65536).decode("utf-8", "replace")
            status = resp.status
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return _lane_fail(
            "GET %s failed: %s" % (url, exc),
            "start llamacpp-nommap or point --base-url at an OpenAI-compatible /v1/models",
        )
    ok = 200 <= int(status) < 300
    if not ok:
        return _lane_fail("GET %s returned HTTP %s" % (url, status), "fix the endpoint, then retry health")
    return {
        "ok": True,
        "exit_code": 0,
        "lane": LLAMACPP_NOMMAP,
        "url": url,
        "status": int(status),
        "body": raw[:500],
        "reason": "",
        "next_step": "",
    }


def stop_llamacpp_nommap(proc, *, timeout: float = 5.0) -> dict:
    """Terminate a process this lane started. No-op when ``proc`` is already gone."""
    if proc is None:
        return {"ok": True, "exit_code": 0, "lane": LLAMACPP_NOMMAP, "stopped": False, "reason": "no process"}
    poll = getattr(proc, "poll", None)
    if callable(poll) and poll() is not None:
        return {
            "ok": True,
            "exit_code": 0,
            "lane": LLAMACPP_NOMMAP,
            "stopped": True,
            "returncode": proc.returncode,
            "reason": "already exited",
        }
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=timeout)
    return {
        "ok": True,
        "exit_code": 0,
        "lane": LLAMACPP_NOMMAP,
        "stopped": True,
        "returncode": proc.poll() if callable(poll) else getattr(proc, "returncode", None),
        "reason": "",
    }
