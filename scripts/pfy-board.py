#!/usr/bin/env python3
"""Local operator board. Independent poller — not a daemon, not a supervisor.

Serves the shared GUI at gui/operator/frontend/index.html.
POST /start spawns OpenCode/Hermes/Grok/Codex/Claude/Gab enterable session (Grok #202; Codex #220; Claude #221; Gab #228). start_monitor_sidecar remains a separate monitor role. local-only never auto-calls cloud.
POST /stage runs ./pfy stage (env-stage).
POST /env runs ./pfy env (inference + env-stage). No harness exec.
POST /models/pull runs ./pfy models pull <name>.
POST /models/recommend ranks host-fit models not yet pulled (#207).
POST /models/try pulls a recommended model FreeToken-first (#207).
POST /eval runs a live-endpoint chat/completions probe against LOCAL_OPENAI_BASE_URL.
POST /tools toggles skills, MCP, write-guard, extra tools.
POST /catalog/ask asks the attached TUI to implement a catalog tool for next launch (#209).
POST /catalog/queue opens a real GitHub issue with Design->DevBot DoD (#214).
POST /start with mode orchestration starts a multi-step local loop (#213).
POST /start with mode code-graph hands Axon (or codebase-memory equivalent) (#215).
POST /wizard composes Loop launch wizard steps (#225). Decision toggle is wizard step decision (#230).
POST /launch Launch session: enterable TUI with composed env or FAIL+next (#225/#224). Applies enabled Loop modules first (pfylib.loop_paint).
POST /module toggles a catalog toolset on Loop (stub modules cannot be enabled).
POST /loop/task sets hedge task class bulk|interactive|hard.
POST /decision/smoke Mark-free CUA-S1-FORMS Choice (#230).
POST /space-invaders runs session Space Invaders via Attach OpenCode (#155).
"""
from __future__ import annotations
import json, os, shutil, socket, subprocess, sys, urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PFY = ROOT / "scripts" / "pfy"
DETECT = ROOT / "scripts" / "detect-local-runtime.sh"
REG = ROOT / "data" / "harnesses.json"
STATE = Path(os.environ.get("PFY_STATE_DIR", str(Path.home() / ".pfy-mentat")))
HOST = os.environ.get("PFY_BOARD_HOST", "127.0.0.1")
PORT = int(os.environ.get("PFY_BOARD_PORT", "8765"))
REFRESH_MS = int(os.environ.get("PFY_BOARD_REFRESH_MS", "2000"))
DETECT_ORDER = [
    ("freetoken", "FreeToken", ":1919"),
    ("llama-swap", "llama-swap", ":9292"),
    ("llama.cpp", "llama-server", ":8080"),
    ("ollama", "Ollama", ":11434"),
]
PS_MATCH = {
    "freetoken": ("ft", "freetoken"), "llama-swap": ("llama-swap",),
    "llama.cpp": ("llama-server",), "llama-server": ("llama-server",),
    "ollama": ("ollama",), "shimmy": ("shimmy",), "grok": ("grok",),
    "opencode": ("opencode", "opencode-cli"), "hermes": ("hermes", "hermes-agent"),
    "claude": ("claude",), "claude-code": ("claude",), "codex": ("codex",), "gemini": ("gemini", "gemini-cli"),
    "exo": ("exo.sh", "exo"),
}
STUB_ALWAYS = {"continue", "agent-cage"}
NO_SPAWN = {"llama-swap", "llama.cpp", "llama-server", "shimmy"}
SIDECAR_OK = {"grok", "opencode", "hermes", "codex", "claude", "claude-code", "gab"}
ISSUE_BASE = "https://github.com/themark-net/pfy-mentat/issues/"
GROK_USE = "pfy harness use grok"
FRONTEND_DIR = ROOT / "gui" / "operator" / "frontend"
FRONTEND = FRONTEND_DIR / "index.html"
ORG_CANDIDATES = (
    STATE / "org-messages.jsonl", STATE / "org-messages.json",
    ROOT / "data" / "org-messages.jsonl", ROOT / "data" / "org-messages.json",
    ROOT / ".pfy" / "org-messages.jsonl", ROOT / ".pfy" / "org-messages.json",
)
ENGINE_ALIAS = {"ft": "freetoken", "llama-server": "llama.cpp", "freetoken": "freetoken"}
ALLOWED_LIVE = frozenset({"ready", "partial", "stub", "detected-stub", "missing", "skip"})

def honest_live(value):
    v = str(value or "").strip().lower()
    if v in ALLOWED_LIVE:
        return v
    return "missing"

def _run(argv, timeout=20.0):
    try:
        p = subprocess.run(argv, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)
    return p.returncode, (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")

def load_registry():
    if not REG.is_file():
        return {"harnesses": [], "default_harness": "grok"}
    return json.loads(REG.read_text(encoding="utf-8"))

def detector_json():
    if not DETECT.is_file():
        return {"engine": "none", "status": "missing", "base_url": ""}
    _rc, out = _run(["bash", str(DETECT), "--json"], timeout=8.0)
    for raw in out.splitlines():
        s = raw.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                d = json.loads(s)
            except json.JSONDecodeError:
                break
            if isinstance(d, dict):
                return {"engine": d.get("engine") or "none", "status": d.get("status") or "missing", "base_url": d.get("base_url") or ""}
    return {"engine": "none", "status": "missing", "base_url": ""}

def pfy_status_stdout():
    rc, out = _run(["bash", str(PFY), "status"], timeout=25.0)
    return out if out.strip() else f"(pfy status empty, exit {rc})"

def parse_status(text):
    active, usage, chips = "", [], []
    runtime = {"engine": "", "status": "", "base_url": ""}
    in_usage = in_table = False
    for line in text.splitlines():
        if line.startswith("active harness:"):
            active = line.split(":", 1)[1].strip(); in_usage = False; continue
        if line.startswith("local runtime:"):
            for part in line.split(":", 1)[1].split():
                if "=" in part:
                    k, v = part.split("=", 1); runtime[k] = v
            in_usage = False; continue
        if line.startswith("usage:"):
            in_usage = True; in_table = False; continue
        stripped = line.strip()
        if stripped.startswith("ID") and "STATUS" in line:
            in_table = True; in_usage = False; continue
        if in_table:
            if stripped.startswith("----") or stripped.startswith("next:") or stripped.startswith("override:"):
                if stripped.startswith("next:") or stripped.startswith("override:"):
                    in_table = False
                continue
            if not stripped:
                in_table = False; continue
            parts = stripped.split(None, 3)
            if len(parts) >= 3:
                chips.append({"id": parts[0], "live": honest_live(parts[1]), "role": parts[2], "name": parts[3] if len(parts) > 3 else ""})
            continue
        if in_usage:
            if not stripped:
                in_usage = False; continue
            usage.append(line.rstrip())
    return {"active": active, "runtime": runtime, "usage": usage, "chips": chips}

def local_usage_info():
    """Run bash scripts/pfy usage and parse -- cite #165."""
    import importlib.util
    path = ROOT / "scripts" / "pfy_usage_165.py"
    empty = {
        "ok": False, "engine": "", "endpoint": "", "models": [],
        "tok_path": "SKIP", "vram": "SKIP",
        "fail": "FAIL: no local engine up",
        "next_step": "Launch env or ./pfy up", "lines": [],
    }
    if not path.is_file():
        return empty
    try:
        spec = importlib.util.spec_from_file_location("pfy_usage_165", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.collect_usage(ROOT, _run)
    except Exception as e:
        empty = dict(empty)
        empty["error"] = str(e)[:200]
        return empty

def process_table():
    rc, out = _run(["ps", "-eo", "pid,args"], timeout=5.0)
    if rc != 0:
        rc, out = _run(["ps", "ax", "-o", "pid,args"], timeout=5.0)
    rows = []
    for line in out.splitlines()[1:]:
        s = line.strip()
        if not s:
            continue
        pid, _, args = s.partition(" ")
        low = args.lower()
        if "pfy-board.py" in low or "pfy-gui.py" in low or "pfy-operator" in low:
            continue
        hit = ""
        for hid, needles in PS_MATCH.items():
            for n in needles:
                tok = n.lower()
                if tok in low.split() or f"/{tok}" in low or low.endswith(tok):
                    hit = hid; break
            if hit:
                break
        if hit:
            rows.append({"pid": pid, "id": hit, "args": args.strip()[:180]})
    return rows

def last_verb():
    p = STATE / "last-verb"
    if not p.is_file():
        return {"verb": "(none)", "when": ""}
    verb, when = "(none)", ""
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("verb:"):
            verb = line.split(":", 1)[1].strip() or "(none)"
        elif line.startswith("when:"):
            when = line.split(":", 1)[1].strip()
    return {"verb": verb, "when": when}

def active_harness(default):
    p = STATE / "active-harness"
    if p.is_file():
        v = p.read_text(encoding="utf-8", errors="replace").strip()
        if v:
            return v
    return default

def deploy_profile():
    envp = ROOT / ".env"
    if envp.is_file():
        for line in envp.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith("DEPLOY_PROFILE="):
                return line.split("=", 1)[1].strip().strip("'\"")
    return os.environ.get("DEPLOY_PROFILE", "")

def inspect_models(base_url):
    if not base_url:
        return []
    base = base_url.rstrip("/")
    # FreeToken-first bases often already end with /v1; paths add /v1/models. Cite #193.
    if base.endswith("/v1"):
        base = base[:-3].rstrip("/") or base
    ids, seen = [], set()
    for path in ("/v1/models", "/api/tags"):
        try:
            req = urllib.request.Request(base + path, method="GET")
            with urllib.request.urlopen(req, timeout=2) as r:
                d = json.loads(r.read().decode() or "{}")
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        for key in ("data", "models"):
            for m in d.get(key) or []:
                name = (m.get("id") or m.get("name") or m.get("model") if isinstance(m, dict) else str(m)) or ""
                name = str(name).strip()
                if name and name not in seen:
                    seen.add(name); ids.append(name)
    return ids

def org_messages():
    for path in ORG_CANDIDATES:
        if not path.is_file():
            continue
        raw = path.read_text(encoding="utf-8", errors="replace").strip()
        if not raw:
            continue
        items = []
        if path.suffix == ".jsonl":
            for line in raw.splitlines():
                try:
                    items.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        else:
            try:
                loaded = json.loads(raw)
            except json.JSONDecodeError:
                continue
            items = loaded if isinstance(loaded, list) else (loaded.get("messages") or loaded.get("items") or [loaded])
        out = []
        for it in items:
            if not isinstance(it, dict):
                continue
            who = str(it.get("from") or it.get("who") or "")
            whom = str(it.get("to") or it.get("whom") or "")
            if who or whom:
                out.append({"from": who, "to": whom, "pr": it.get("pr") or "", "issue": it.get("issue") or "",
                            "state": str(it.get("state") or it.get("status") or ""),
                            "text": str(it.get("text") or it.get("summary") or "")[:240]})
        return out
    return []

def one_liner(hid, rec):
    if hid in STUB_ALWAYS:
        return GROK_USE
    if hid == "llama-swap":
        return "llama-swap"
    if hid in ("llama.cpp", "llama-server"):
        return "llama-server"
    if hid == "shimmy":
        return "shimmy"
    if hid == "freetoken":
        return "ft serve --model $PFY_FT_MODEL"
    if hid == "ollama":
        return "ollama serve"
    if hid == "grok":
        return "curl -fsSL https://x.ai/cli/install.sh | bash"
    setup = str(rec.get("setup") or "").strip()
    return (setup.splitlines()[0] if setup else f"./pfy start {hid}")

def now_state(active, live, procs, verb):
    ids = {r["id"] for r in procs}
    mapped = "llama.cpp" if active == "llama-server" else active
    if mapped in STUB_ALWAYS or live in ("stub", "detected-stub", "missing"):
        return "blocked"
    if mapped in ids or active in ids:
        return "running"
    v = verb.get("verb") or ""
    return "blocked" if v.startswith("start") or v.startswith("up") else "idle"

def rsf_inference(det):
    st = (det.get("status") or "").strip().lower()
    if st == "ready":
        return "READY"
    if st == "partial":
        return "FAIL"
    return "SKIP"

def rsf_env_stage(verb, usage):
    if isinstance(usage, dict):
        blob = " ".join(str(x) for x in (usage.get("lines") or [])).lower()
        if not blob:
            blob = " ".join(str(usage.get(k) or "") for k in ("fail", "next_step", "engine")).lower()
    else:
        blob = " ".join(usage or []).lower()
    v = (verb.get("verb") or "").strip()
    if "fail" in blob or "error" in blob:
        return "FAIL"
    if "honest skip" in blob or "skip: env-stage" in blob:
        return "SKIP"
    if v.startswith(("start", "up", "stage", "gui", "board", "env", "launch-env")):
        return "READY"
    return "SKIP"

def rsf_attach(active, live_active):
    if active in STUB_ALWAYS:
        return "FAIL"
    live = (live_active or "").lower()
    if live == "ready":
        return "READY"
    if live in ("stub", "detected-stub"):
        return "FAIL"
    return "SKIP"

def tape_steps(det, verb, usage, active, live_active):
    return [
        {"id": "inference", "label": "inference", "live": rsf_inference(det)},
        {"id": "env-stage", "label": "env-stage", "live": rsf_env_stage(verb, usage)},
        {"id": "harness-attach", "label": "harness attach", "live": rsf_attach(active, live_active)},
    ]
def snapshot():
    reg = load_registry()
    harnesses = list(reg.get("harnesses") or [])
    default = str(reg.get("default_harness") or "grok")
    det = detector_json()
    status_text = pfy_status_stdout()
    parsed = parse_status(status_text)
    parsed_chips = {c["id"]: c for c in parsed["chips"]}
    chips = []
    for h in harnesses:
        hid = str(h.get("id") or "")
        if not hid:
            continue
        parsed_row = parsed_chips.get(hid)
        live = honest_live(parsed_row.get("live") if parsed_row else "missing")
        issue = h.get("github_issue")
        rec = {
            "id": hid, "name": h.get("name") or hid, "role": h.get("role") or "",
            "live": live, "issue_url": f"{ISSUE_BASE}{issue}" if issue not in (None, "") else "",
            "one_liner": one_liner(hid, h),
            "startable": live == "ready" and hid in SIDECAR_OK,
        }
        if hid in STUB_ALWAYS:
            rec["startable"] = False
            rec["one_liner"] = GROK_USE
        if hid == "grok":
            rec["live"] = grok_path_live()
            rec["startable"] = rec["live"] == "ready"
        chips.append(rec)
    procs = process_table()
    verb = last_verb()
    active = parsed.get("active") or active_harness(default)
    live_active = next((c["live"] for c in chips if c["id"] == active), "missing")
    host = socket.gethostname()
    is_nimo = "nimo" in host.lower()
    profile = deploy_profile()
    base = det.get("base_url") or (parsed.get("runtime") or {}).get("base_url") or ""
    if base == "(none)":
        base = ""
    eng = det.get("engine") or ""
    eng_norm = ENGINE_ALIAS.get(eng, eng)
    ready_h = any(c["role"] == "harness" and c["live"] == "ready" for c in chips)
    modes = []
    order = []
    for hid, label, port in DETECT_ORDER:
        live = honest_live(next((c["live"] for c in chips if c["id"] == hid), "missing"))
        order.append({"id": hid, "label": label, "port": port, "live": live, "winner": eng_norm == hid,
                      "one_liner": one_liner(hid, next((h for h in harnesses if h.get("id") == hid), {}))})
    winner = next((o for o in order if o["winner"]), None)
    engine_live = honest_live((winner["live"] if winner else "") or det.get("status") or "missing")
    msgs = org_messages()
    nimo_note = ""
    usage_info = local_usage_info()
    tape = tape_steps(det, verb, usage_info.get("lines") or parsed.get("usage") or [], active, live_active)
    tape_outcome = " then ".join(f"{t['label']} {t['live']}" for t in tape)
    env_stage_live = next((t["live"] for t in tape if t["id"] == "env-stage"), "SKIP")
    blocked_reason = GROK_USE if active in STUB_ALWAYS else ""
    try:
        import importlib.util as _ilu
        _up = ROOT / "scripts" / "pfy_usage_165.py"
        _sr = dict(parsed.get("runtime") or {})
        if _up.is_file():
            _sp = _ilu.spec_from_file_location("pfy_usage_165", _up)
            _um = _ilu.module_from_spec(_sp); _sp.loader.exec_module(_um)
            _sr = _um.enrich_status_runtime(_sr, usage_info)
        else:
            _sr = dict(_sr)
            _sr["tok_path"] = usage_info.get("tok_path") or "SKIP"
            _sr["vram"] = usage_info.get("vram") or "SKIP"
    except Exception:
        _sr = dict(parsed.get("runtime") or {})
        _sr["tok_path"] = usage_info.get("tok_path") or "SKIP"
        _sr["vram"] = usage_info.get("vram") or "SKIP"
    models = list(usage_info.get("models") or []) or (inspect_models(base) if base else [])
    if usage_info.get("endpoint"):
        base = usage_info.get("endpoint") or base
    return {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "host": host, "root": str(ROOT), "profile": profile, "local_only": profile == "local-only",
        "is_nimo": is_nimo,
        "detector": det, "status_runtime": _sr, "usage": usage_info,
        "chips": chips, "active": active, "last_verb": verb, "now": now_state(active, live_active, procs, verb),
        "processes": procs, "detect_order": order, "engine_live": engine_live,
        "models": models,
        "models_note": "",
        "org_messages": msgs, "agent_lane_collapsed": not msgs,
        "honest": {"modes": modes, "note_nimo": nimo_note},
        "grok_chip_note": "",
        "midline": "",
        "tape": tape, "tape_outcome": tape_outcome, "env_stage_live": env_stage_live,
        "blocked_copy": GROK_USE, "blocked_reason": blocked_reason,
        "status_stdout": status_text, "no_daemon": True,
        "active_stub": active in STUB_ALWAYS, "refresh_ms": REFRESH_MS,
        "sidecar_ok": sorted(SIDECAR_OK),
        "sidecar_pid": sidecar_pid_live(),
        "session_reach": _session_reach_live(),
        "grok_path": grok_path_live(),
        "monitor_note": last_monitor_note(),
        "monitor_pid": monitor_pid_live(),
        "tools": load_tools_state(),
        **attach_mode_fields(),
        **recommend_fields(models, eng, det, base),
        **catalog_fields(active),
        **orchestration_fields(),
        **code_graph_fields(),
        **wizard_fields(),
        **loop_paint_fields(det),
    }

def html_page():
    if FRONTEND.is_file():
        return FRONTEND.read_text(encoding="utf-8")
    return (
        "<!DOCTYPE html><html><body>error: gui/operator/frontend/index.html missing</body></html>"
    )



def frontend_static(path: str):
    """Serve sibling assets from gui/operator/frontend (app-core-*.js, app-ui.js, …)."""
    name = (path or "").lstrip("/")
    if not name or "/" in name or "\\" in name or ".." in name or name.startswith("."):
        return None
    if not name.endswith((".js", ".css", ".map", ".svg", ".png", ".ico", ".woff2")):
        return None
    fp = (FRONTEND_DIR / name).resolve()
    try:
        fp.relative_to(FRONTEND_DIR.resolve())
    except ValueError:
        return None
    if not fp.is_file():
        return None
    ctype = {
        ".js": "application/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".map": "application/json; charset=utf-8",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".ico": "image/x-icon",
        ".woff2": "font/woff2",
    }.get(fp.suffix.lower(), "application/octet-stream")
    return fp, ctype


def run_stage():
    """Run product env-stage (./pfy stage). Not --lab. Honest skip is PASS."""
    if not PFY.is_file():
        return {"ok": False, "live": "FAIL", "copy": "FAIL env-stage", "error": "scripts/pfy missing"}
    rc, out = _run(["bash", str(PFY), "stage"], timeout=90.0)
    ok = rc == 0
    live = "PASS" if ok else "FAIL"
    copy = "PASS env-stage" if ok else "FAIL env-stage"
    return {
        "ok": ok, "live": live, "copy": copy,
        "error": "" if ok else ((out or "env-stage failed")[-400:]),
        "stdout": (out or "")[-800:],
    }

def test_model():
    # Live-endpoint eval: OpenAI-compat chat/completions on detector base_url.
    # Same completion path as examples/opencode-ollama/smoke.sh, against LOCAL_OPENAI_BASE_URL.
    # Not eval-integration-change. PASS only if the endpoint returns a completion.
    det = detector_json()
    st = str(det.get("status") or "").strip().lower()
    eng = str(det.get("engine") or "none").strip().lower()
    base = str(det.get("base_url") or os.environ.get("LOCAL_OPENAI_BASE_URL") or "").strip()
    if base == "(none)":
        base = ""
    live = st == "ready" and eng not in ("", "none") and bool(base)
    if not live:
        return {"ok": True, "live": "SKIP", "copy": "SKIP eval", "error": ""}
    models = inspect_models(base)
    name = ""
    if models:
        name = str(models[0]).strip()
    if not name:
        name = (
            os.environ.get("LOCAL_CODER_MODEL")
            or os.environ.get("PFY_FT_MODEL")
            or os.environ.get("PFY_OLLAMA_MODEL")
            or os.environ.get("PFY_LLAMA_MODEL")
            or ""
        ).strip()
    if not name:
        return {"ok": False, "live": "FAIL", "copy": "FAIL eval", "error": "no model on live endpoint"}
    root = base.rstrip("/")
    if root.endswith("/v1"):
        url = root + "/chat/completions"
    else:
        url = root + "/v1/chat/completions"
    payload = json.dumps({
        "model": name,
        "messages": [{"role": "user", "content": "Reply with exactly: PFY_EVAL_OK"}],
        "max_tokens": 32,
        "temperature": 0,
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode() or "{}")
    except Exception as e:
        return {"ok": False, "live": "FAIL", "copy": "FAIL eval", "error": str(e)[:400]}
    text = ""
    try:
        choice = (data.get("choices") or [{}])[0]
        if not isinstance(choice, dict):
            choice = {}
        msg = choice.get("message") or {}
        if isinstance(msg, dict):
            text = msg.get("content") or ""
        if not text:
            text = choice.get("text") or ""
    except Exception:
        text = ""
    if len(str(text).strip()) < 2:
        return {"ok": False, "live": "FAIL", "copy": "FAIL eval", "error": "empty completion"}
    return {"ok": True, "live": "PASS", "copy": "PASS eval", "stdout": str(text).strip()[:400]}

def pull_model(name):
    # #173: FreeToken-first via ./pfy models pull (detect spine); no engine → FAIL+next.
    name = (name or "").strip()
    if not name:
        return {"ok": False, "live": "FAIL", "copy": "FAIL pull", "error": "no name",
                "next_step": "Launch env or ./pfy up"}
    if not PFY.is_file():
        return {"ok": False, "live": "FAIL", "copy": "FAIL pull", "error": "scripts/pfy missing",
                "next_step": "Launch env or ./pfy up"}
    rc, out = _run(["bash", str(PFY), "models", "pull", name], timeout=180.0)
    blob = (out or "")
    low = blob.lower()
    nxt = "Launch env or ./pfy up"
    if rc != 0 or "fail: no local engine" in low or "no local engine to pull" in low:
        err = (blob or "pull failed")[-400:]
        return {
            "ok": False, "live": "FAIL", "copy": "FAIL pull — " + nxt,
            "error": err, "stdout": blob[-800:], "next_step": nxt,
        }
    if "honest skip" in low or "has no pull" in low:
        return {"ok": True, "live": "SKIP", "copy": "SKIP pull", "stdout": blob[-800:]}
    return {"ok": True, "live": "PASS", "copy": "PASS pull", "stdout": blob[-800:]}

def recommend_models():
    """Ranked host-fit models beyond already-pulled. Cite #207."""
    mod, err = _load_recommend_207()
    if mod is None:
        return {"ok": False, "live": "FAIL", "copy": "FAIL recommend -- module missing",
                "error": err or "missing", "ranked": [], "next_step": "./pfy setup", "usable": False}
    return mod.recommend(ROOT, STATE)

def try_recommended_model(name=""):
    """One try/pull of a recommended model via FreeToken-first pull. Cite #207."""
    mod, err = _load_recommend_207()
    if mod is None:
        return {"ok": False, "live": "FAIL", "copy": "FAIL try -- module missing",
                "error": err or "missing", "ranked": [], "next_step": "./pfy setup", "usable": False}
    return mod.try_model(ROOT, STATE, name, pull_fn=pull_model)

def catalog_browse():
    """Usable catalog subset (not scores-only). Cite #209."""
    mod, err = _load_catalog_209()
    if mod is None:
        return {"ok": False, "live": "FAIL", "copy": "FAIL catalog -- module missing",
                "error": err or "missing", "catalog": [], "next_step": "./pfy setup", "usable": False}
    return mod.browse(ROOT, STATE)

def catalog_ask(name=""):
    """Ask attached TUI to implement for next launch. Cite #209."""
    mod, err = _load_catalog_209()
    if mod is None:
        return {"ok": False, "live": "FAIL", "copy": "FAIL ask -- module missing",
                "error": err or "missing", "next_step": "./pfy setup", "usable": False}
    return mod.ask_implement(ROOT, STATE, name, active=active_harness("grok"), pid_alive=pid_alive)

def catalog_queue(name=""):
    """Queue catalog tool as a real GitHub issue (Design->DevBot). Cite #214."""
    live, err = _load_live_org_214()
    if live is not None:
        return live.queue_org(ROOT, STATE, name)
    if err:
        return {"ok": False, "live": "FAIL", "copy": "FAIL queue -- module missing",
                "error": err, "next_step": "./pfy setup", "usable": False, "mock": False}
    mod, err = _load_catalog_209()
    if mod is None:
        return {"ok": False, "live": "FAIL", "copy": "FAIL queue -- module missing",
                "error": err or "missing", "next_step": "./pfy setup", "usable": False}
    return mod.queue_org(ROOT, STATE, name)

def catalog_status():
    """Queued catalog items + status (open/closed/PR). Cite #214."""
    live, err = _load_live_org_214()
    if live is not None:
        return live.queue_status(STATE)
    mod, err = _load_catalog_209()
    if mod is None:
        return {"ok": False, "live": "FAIL", "copy": "FAIL catalog-status -- module missing",
                "error": err or "missing", "queue": [], "next_step": "./pfy setup", "usable": False}
    return mod.queue_status(STATE)

def launch_env():
    """Same path as bare ./pfy before the window: inference then env-stage. No harness exec.

    Always record_last_verb so LOOP last/timestamp refresh even when already up.
    Honest skip / already-up paints SKIP (never silent). Cite #159 enrich.
    """
    def _enrich_env(res):
        try:
            import importlib.util
            path = ROOT / "scripts" / "pfy_verify_159.py"
            if not path.is_file():
                out = dict(res or {})
                out["ok"] = False
                out["live"] = "FAIL"
                out["copy"] = "FAIL env · verify module missing"
                out["error"] = str(path)
                return out
            spec = importlib.util.spec_from_file_location("pfy_verify_159", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            enriched = mod.enrich_launch_env(res, live_openai_base, STATE, ROOT)
            emod, eerr = _load_enterable_162()
            if emod is None:
                out = dict(enriched or {})
                steps = list(out.get("next_steps") or [])
                reason = "SKIP enterable session · module missing"
                steps.append({"id": "enterable", "label": reason, "value": reason})
                out["next_steps"] = steps
                out["session_reach"] = "SKIP"
                out["enterable"] = False
                what = str(out.get("what") or "")
                if "enterable" not in what.lower():
                    out["what"] = (what + " · " + reason).strip(" ·")
                return out
            return emod.arm_launch_env_session(enriched, open_enterable_opencode_session)
        except Exception as e:
            out = dict(res or {})
            out["ok"] = False
            out["live"] = "FAIL"
            out["copy"] = "FAIL env · enrich"
            out["error"] = str(e)[:400]
            return out
    if not PFY.is_file():
        record_last_verb("env")
        return _enrich_env({"ok": False, "live": "FAIL", "copy": "FAIL env", "error": "scripts/pfy missing"})
    rc, out = _run(["bash", str(PFY), "env"], timeout=120.0)
    blob = out or ""
    low = blob.lower()
    # Always stamp the click so LOOP last + when move even if tape was already READY.
    record_last_verb("env")
    if rc != 0:
        return _enrich_env({
            "ok": False, "live": "FAIL", "copy": "FAIL env",
            "error": (blob or "env failed")[-400:],
            "stdout": blob[-800:],
        })
    # #191: ready engine is PASS even if an earlier cascade candidate printed honest skip.
    if "status: ready" in low:
        return _enrich_env({
            "ok": True, "live": "PASS", "copy": "PASS env",
            "error": "",
            "stdout": blob[-800:],
        })
    # Stage-only skip (no ready engine line): paint SKIP, not a fake PASS.
    if (
        "skip: env-stage" in low
        or "env-stage.sh missing" in low
    ):
        return _enrich_env({"ok": True, "live": "SKIP", "copy": "SKIP env", "stdout": blob[-800:]})
    return _enrich_env({
        "ok": True, "live": "PASS", "copy": "PASS env",
        "error": "",
        "stdout": blob[-800:],
    }
)

def which_bin(*names):
    for n in names:
        found = shutil.which(n)
        if found:
            return found
    return ""


def _load_enterable_162():
    """Load pfy_enterable_162 or return (None, error). Cite #162."""
    import importlib.util
    path = ROOT / "scripts" / "pfy_enterable_162.py"
    if not path.is_file():
        return None, str(path)
    try:
        spec = importlib.util.spec_from_file_location("pfy_enterable_162", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, ""
    except Exception as e:
        return None, str(e)[:400]

def _load_attach_196():
    """Load pfy_attach_usable_196 or return (None, error). Cite #196."""
    import importlib.util
    path = ROOT / "scripts" / "pfy_attach_usable_196.py"
    if not path.is_file():
        return None, str(path)
    try:
        spec = importlib.util.spec_from_file_location("pfy_attach_usable_196", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, ""
    except Exception as e:
        return None, str(e)[:400]

def _load_attach_202():
    """Load pfy_attach_usable_202 or return (None, error). Cite #202."""
    import importlib.util
    path = ROOT / "scripts" / "pfy_attach_usable_202.py"
    if not path.is_file():
        return None, str(path)
    try:
        spec = importlib.util.spec_from_file_location("pfy_attach_usable_202", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, ""
    except Exception as e:
        return None, str(e)[:400]

def _load_attach_220():
    """Load pfy_attach_usable_220 or return (None, error). Cite #220."""
    import importlib.util
    path = ROOT / "scripts" / "pfy_attach_usable_220.py"
    if not path.is_file():
        return None, str(path)
    try:
        spec = importlib.util.spec_from_file_location("pfy_attach_usable_220", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, ""
    except Exception as e:
        return None, str(e)[:400]

def _load_attach_221():
    """Load pfy_attach_usable_221 or return (None, error). Cite #221."""
    import importlib.util
    path = ROOT / "scripts" / "pfy_attach_usable_221.py"
    if not path.is_file():
        return None, str(path)
    try:
        spec = importlib.util.spec_from_file_location("pfy_attach_usable_221", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, ""
    except Exception as e:
        return None, str(e)[:400]

def _load_attach_mode_208():
    """Load pfy_attach_mode_208 or return (None, error). Cite #208."""
    import importlib.util
    path = ROOT / "scripts" / "pfy_attach_mode_208.py"
    if not path.is_file():
        return None, str(path)
    try:
        spec = importlib.util.spec_from_file_location("pfy_attach_mode_208", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, ""
    except Exception as e:
        return None, str(e)[:400]

def _load_recommend_207():
    """Load pfy_recommend_models_207 or return (None, error). Cite #207."""
    import importlib.util
    path = ROOT / "scripts" / "pfy_recommend_models_207.py"
    if not path.is_file():
        return None, str(path)
    try:
        spec = importlib.util.spec_from_file_location("pfy_recommend_models_207", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, ""
    except Exception as e:
        return None, str(e)[:400]

def _load_launch_225():
    """Load pfy_launch_wizard_225 or return (None, error). Cite #225."""
    import importlib.util
    path = ROOT / "scripts" / "pfy_launch_wizard_225.py"
    if not path.is_file():
        return None, str(path)
    try:
        spec = importlib.util.spec_from_file_location("pfy_launch_wizard_225", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, ""
    except Exception as e:
        return None, str(e)[:400]

def _load_catalog_209():
    """Load pfy_catalog_ask_queue_209 or return (None, error). Cite #209."""
    import importlib.util
    path = ROOT / "scripts" / "pfy_catalog_ask_queue_209.py"
    if not path.is_file():
        return None, str(path)
    try:
        spec = importlib.util.spec_from_file_location("pfy_catalog_ask_queue_209", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, ""
    except Exception as e:
        return None, str(e)[:400]

def _load_live_org_214():
    """Load pfy_live_org_queue_214 or return (None, error). Cite #214."""
    import importlib.util
    path = ROOT / "scripts" / "pfy_live_org_queue_214.py"
    if not path.is_file():
        return None, str(path)
    try:
        spec = importlib.util.spec_from_file_location("pfy_live_org_queue_214", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, ""
    except Exception as e:
        return None, str(e)[:400]

def _load_orchestration_213():
    """Load pfy_orchestration_213 or return (None, error). Cite #213."""
    import importlib.util
    path = ROOT / "scripts" / "pfy_orchestration_213.py"
    if not path.is_file():
        return None, str(path)
    try:
        spec = importlib.util.spec_from_file_location("pfy_orchestration_213", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, ""
    except Exception as e:
        return None, str(e)[:400]

def _load_code_graph_215():
    """Load pfy_code_graph_215 or return (None, error). Cite #215."""
    import importlib.util
    path = ROOT / "scripts" / "pfy_code_graph_215.py"
    if not path.is_file():
        return None, str(path)
    try:
        spec = importlib.util.spec_from_file_location("pfy_code_graph_215", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, ""
    except Exception as e:
        return None, str(e)[:400]

def attach_mode_fields():
    mod, err = _load_attach_mode_208()
    if mod is None:
        return {"attach_mode": "bare", "using": "bare", "attach_mode_when": "", "attach_mode_live": ""}
    try:
        return mod.snapshot_fields(STATE)
    except Exception:
        return {"attach_mode": "bare", "using": "bare", "attach_mode_when": "", "attach_mode_live": ""}

def set_attach_mode(mode):
    """Select one attach mode (bare|orchestration|code-graph). Cite #208."""
    mod, err = _load_attach_mode_208()
    if mod is None:
        return {"ok": False, "live": "FAIL", "copy": "FAIL mode -- module missing", "error": err or "missing", "usable": False, "next_step": "./pfy setup"}
    STATE.mkdir(parents=True, exist_ok=True)
    return mod.set_mode(STATE, mode)

def recommend_fields(models, eng, det, base):
    """Snapshot recommend/try fields. Cite #207. Never invent a best list."""
    empty = {
        "recommend_ok": False, "recommend": [], "recommend_ranked": [],
        "recommend_copy": "", "recommend_next": "Launch env or ./pfy up",
        "recommend_top": "", "recommend_host": {}, "pinned_model": "",
        "model_handoff": "",
    }
    mod, err = _load_recommend_207()
    if mod is None:
        empty["recommend_copy"] = "FAIL recommend -- module missing"
        empty["recommend_next"] = "./pfy setup"
        return empty
    try:
        st = str((det or {}).get("status") or "")
        return mod.snapshot_fields(
            STATE, ROOT, pulled=list(models or []), engine=eng or "",
            status=st, base=base or "",
        )
    except Exception as e:
        empty["recommend_copy"] = "FAIL recommend -- %s" % str(e)[:160]
        return empty

def orchestration_fields():
    """Snapshot last loop/monitor evidence. Cite #213. Not slogan-only."""
    empty = {
        "loop_ok": False, "loop_copy": "", "loop_when": "", "loop_model": "",
        "loop_steps": 0, "loop_hid": "", "loop_status": "", "loop_evidence": "",
        "loop_next": "Attach OpenCode | Hermes | Grok | Codex | Claude",
    }
    mod, err = _load_orchestration_213()
    if mod is None:
        empty["loop_copy"] = "FAIL orchestration -- module missing"
        empty["loop_next"] = "./pfy setup"
        return empty
    try:
        return mod.snapshot_fields(STATE)
    except Exception as e:
        empty["loop_copy"] = "FAIL orchestration -- %s" % str(e)[:160]
        return empty

def code_graph_fields():
    """Snapshot live code-graph path (axon vs codebase-memory). Cite #215."""
    empty = {
        "graph_ok": False, "graph_copy": "", "graph_when": "", "graph_path": "",
        "graph_bin": "", "graph_evidence": "", "graph_next": "pip install axoniq · ./pfy catalog ask axon",
    }
    mod, err = _load_code_graph_215()
    if mod is None:
        empty["graph_copy"] = "FAIL code-graph -- module missing"
        empty["graph_next"] = "./pfy setup"
        return empty
    try:
        return mod.snapshot_fields(STATE)
    except Exception as e:
        empty["graph_copy"] = "FAIL code-graph -- %s" % str(e)[:160]
        return empty

def loop_paint_fields(det=None):
    """Loop front door: catalog modules + live local/cloud hedge. Not a harness picker."""
    local = None
    if isinstance(det, dict):
        local = {
            "engine": det.get("engine") or "none",
            "base_url": det.get("base_url") or "",
            "status": det.get("status") or "missing",
        }
    empty = {
        "modules": [], "modules_enabled": [], "modules_task": "interactive",
        "hedge": {
            "ok": False, "live": "FAIL", "lane": None, "local_ready": False,
            "local_engine": "none", "local_status": "missing", "local_base_url": "",
            "budget": 0, "spent": 0, "remaining": 0, "reason": "", "next_step": "",
            "copy": "", "routes": {}, "gab_key": False, "profile": "(unset)", "task": "interactive",
        },
    }
    try:
        from pfylib import loop_paint
        return loop_paint.fields(state=STATE, root_dir=ROOT, local=local)
    except Exception as e:
        empty["hedge"]["reason"] = str(e)[:160]
        empty["hedge"]["copy"] = "FAIL loop paint -- %s" % str(e)[:160]
        return empty


def toggle_loop_module(tid, on=True):
    try:
        from pfylib import loop_paint
        rec = loop_paint.toggle(str(tid or ""), bool(on), state=STATE, root_dir=ROOT)
    except Exception as e:
        return {"ok": False, "live": "FAIL", "copy": "FAIL module -- %s" % str(e)[:160], "error": str(e)[:160]}
    mode = rec.get("wizard_mode")
    if rec.get("ok") and rec.get("on") and mode:
        wiz = wizard_apply("toolsets", mode)
        rec["wizard"] = {"ok": wiz.get("ok"), "copy": wiz.get("copy")}
    return rec


def set_loop_task(task):
    try:
        from pfylib import loop_paint
        return loop_paint.set_task(str(task or ""), state=STATE)
    except Exception as e:
        return {"ok": False, "live": "FAIL", "copy": "FAIL task -- %s" % str(e)[:160], "error": str(e)[:160]}


def set_loop_agent(agent):
    try:
        from pfylib import loop_paint
        return loop_paint.set_agent(str(agent or ""), state=STATE)
    except Exception as e:
        return {"ok": False, "live": "FAIL", "copy": "FAIL agent -- %s" % str(e)[:160], "error": str(e)[:160]}


def _loop_agent():
    try:
        from pfylib import loop_paint
        return loop_paint.load_selection(STATE).get("agent") or "grok"
    except Exception:
        return "grok"


def _loop_toolset_order():
    """Session mode from enabled Loop modules. Later module wins, then bare."""
    try:
        from pfylib import loop_paint
        enabled = list(loop_paint.load_selection(STATE).get("enabled") or [])
    except Exception:
        return ["bare"]
    modes = []
    for tid in enabled:
        mode = loop_paint.WIZARD_MODE.get(str(tid))
        if mode in ("orchestration", "code-graph") and mode not in modes:
            modes.append(mode)
    return list(reversed(modes)) + ["bare"]


def _apply_loop_modules_before_launch():
    """Write enabled modules into the session Launch will spawn (proof, not a harness picker)."""
    try:
        from pfylib import loop_paint
    except Exception as e:
        return [{"live": "FAIL", "copy": "pfylib.loop_paint missing: %s" % str(e)[:120]}]
    hid = _loop_agent()
    if hid == "claude":
        hid = "claude-code"
    return loop_paint.apply_enabled(hid=hid, state=STATE, root_dir=ROOT, yes=True)


def wizard_fields():
    """Snapshot Loop launch wizard compose. Cite #225."""
    empty = {
        "wizard_ok": False, "wizard_step": "runtime", "wizard_runtime": "",
        "wizard_lane": "", "wizard_lane_label": "", "wizard_toolsets": "",
        "wizard_enabled": "", "wizard_harness": "",
        "wizard_mode": "bare", "wizard_review": "", "wizard_when": "",
        "wizard_copy": "compose launch wizard", "wizard_next": "complete wizard review (runtime · lane · toolsets · harness)",
        "wizard_live": "SKIP", "wizard_cta": "Launch session",
        "wizard_decision": "○ off", "wizard_decision_path": "off",
        "decision_honesty": "decision ≠ gab auto ≠ local",
        "decision_core": "compact context · choose model/tool",
    }
    mod, err = _load_launch_225()
    if mod is None:
        empty["wizard_copy"] = "FAIL wizard -- module missing"
        empty["wizard_next"] = "./pfy setup"
        return empty
    try:
        return mod.snapshot_fields(STATE)
    except Exception as e:
        empty["wizard_copy"] = "FAIL wizard -- %s" % str(e)[:160]
        return empty

def wizard_apply(step, value=""):
    """Apply one Loop wizard step. Cite #225."""
    mod, err = _load_launch_225()
    if mod is None:
        return {"ok": False, "live": "FAIL", "copy": "FAIL wizard -- module missing", "error": err or "missing", "usable": False, "next_step": "./pfy setup"}
    STATE.mkdir(parents=True, exist_ok=True)
    return mod.apply_step(
        STATE, step, value=value, ROOT=ROOT, which=which_bin,
        live_openai_base=live_openai_base,
    )


def _load_jev_230():
    """Load pfy_jev_230 or return (None, error). Cite #230."""
    import importlib.util
    path = ROOT / "scripts" / "pfy_jev_230.py"
    if not path.is_file():
        return None, str(path)
    try:
        spec = importlib.util.spec_from_file_location("pfy_jev_230", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, ""
    except Exception as e:
        return None, str(e)[:400]


def decision_smoke(path=None):
    """Mark-free CUA-S1-FORMS (or mini-jev) Choice smoke. Cite #230."""
    mod, err = _load_jev_230()
    if mod is None:
        return {"ok": False, "live": "FAIL", "copy": "FAIL decision -- module missing",
                "error": err or "missing", "next_step": "./pfy setup", "usable": False}
    return mod.attach_usable(ROOT, STATE, path=path or "cua-s1-forms")


def _load_gab_228():
    """Load pfy_gab_228 or return (None, error). Cite #228."""
    import importlib.util
    path = ROOT / "scripts" / "pfy_gab_228.py"
    if not path.is_file():
        return None, str(path)
    try:
        spec = importlib.util.spec_from_file_location("pfy_gab_228", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, ""
    except Exception as e:
        return None, str(e)[:400]

def open_enterable_gab_session(model=None):
    """Attach Gab cloud lane (https://gab.ai/v1, model=auto|pin). Cite #228."""
    mod, err = _load_gab_228()
    if mod is None:
        return {
            "ok": False, "id": "gab", "live": "FAIL",
            "copy": "FAIL gab -- module missing",
            "error": err or "missing", "usable": False,
            "session_reach": "FAIL", "next_step": "./pfy setup",
        }
    model = str(model or "").strip() or "auto"
    res = mod.attach_usable(ROOT, STATE, model=model)
    res = dict(res or {})
    res["id"] = "gab"
    if res.get("ok") and res.get("usable") is not False:
        try:
            (STATE / "active-harness").write_text("gab\n", encoding="utf-8")
            record_last_verb("attach-gab")
        except Exception:
            pass
    return res

def gab_local_sync(pulled=None):
    """Gab open-weight → Ollama recommend sync. Cite #228."""
    mod, err = _load_gab_228()
    if mod is None:
        return {"ok": False, "live": "FAIL", "copy": "FAIL sync -- module missing",
                "error": err or "missing", "rows": [], "next_step": "./pfy setup"}
    return mod.local_sync(ROOT, STATE, pulled=pulled, fixture_only=True)

def gab_pull(tag, confirm_tight=False, opt_in_huge=False):
    """Gated ollama pull for Gab→local recommend row. Cite #228."""
    mod, err = _load_gab_228()
    if mod is None:
        return {"ok": False, "live": "FAIL", "copy": "FAIL pull -- module missing",
                "error": err or "missing", "next_step": "./pfy setup"}
    return mod.pull_gated(
        tag, ROOT=ROOT, STATE=STATE,
        confirm_tight=confirm_tight, opt_in_huge=opt_in_huge,
        pull_fn=pull_model, fixture_only=True,
    )


def launch_wizard_session():
    """Primary CTA Launch session -- reuse attach-usable/mode/catalog. Cite #225."""
    mod, err = _load_launch_225()
    if mod is None:
        return {"ok": False, "live": "FAIL", "copy": "FAIL launch -- module missing", "error": err or "missing", "usable": False, "next_step": "./pfy setup", "session_reach": "FAIL"}
    STATE.mkdir(parents=True, exist_ok=True)
    try:
        from pfylib import loop_paint
        snap = loop_paint.fields(state=STATE, root_dir=ROOT)
    except Exception:
        snap = {}
    if snap and not snap.get("launch_ready"):
        plan = snap.get("plan") or "Choose an agent and a toolset"
        return {
            "ok": False, "live": "FAIL", "copy": plan, "error": plan,
            "usable": False, "next_step": plan, "session_reach": "FAIL",
            "modules_applied": [],
        }
    filled = mod.ensure_compose_defaults(
        STATE,
        toolsets=_loop_toolset_order(),
        harness=(snap or {}).get("modules_agent") or _loop_agent(),
        live_openai_base=live_openai_base,
        ROOT=ROOT,
        which=which_bin,
    )
    if not filled.get("ok"):
        filled["modules_applied"] = []
        return filled
    applied = _apply_loop_modules_before_launch()

    def _start(hid, mode=None):
        return start_sidecar(hid, mode=mode)

    result = mod.launch_session(
        ROOT, STATE, start_fn=_start, live_openai_base=live_openai_base,
        which=which_bin, set_mode_fn=set_attach_mode,
    )
    if isinstance(result, dict):
        result["modules_applied"] = applied
    return result

def catalog_fields(active=""):
    """Snapshot catalog browse + live queue status. Cite #214. Never dump scores-only."""
    empty = {
        "catalog_ok": False, "catalog": [], "catalog_copy": "",
        "catalog_next": "pick a catalog tool on Tools", "catalog_queue": [],
        "catalog_pending": {}, "catalog_busy": False, "catalog_prompt": "",
        "catalog_attached": "", "catalog_hold": "catalog 70-75 HOLD (do not auto-lift)",
    }
    live, _lerr = _load_live_org_214()
    if live is not None:
        try:
            return live.snapshot_fields(STATE, ROOT, active=active or "", pid_alive=pid_alive)
        except Exception as e:
            empty["catalog_copy"] = "FAIL catalog -- %s" % str(e)[:160]
            return empty
    mod, err = _load_catalog_209()
    if mod is None:
        empty["catalog_copy"] = "FAIL catalog -- module missing"
        empty["catalog_next"] = "./pfy setup"
        return empty
    try:
        return mod.snapshot_fields(STATE, ROOT, active=active or "", pid_alive=pid_alive)
    except Exception as e:
        empty["catalog_copy"] = "FAIL catalog -- %s" % str(e)[:160]
        return empty

def _session_reach_live():
    oc, hm, gk, cx, cl = "", "", "", "", ""
    mod, err = _load_enterable_162()
    if mod is not None:
        try:
            if hasattr(mod, "live_session_reach"):
                oc = mod.live_session_reach(STATE, pid_alive) or ""
            else:
                oc = mod.read_session_reach(STATE) or ""
        except Exception:
            oc = ""
    hmod, _herr = _load_attach_196()
    if hmod is not None:
        try:
            if hasattr(hmod, "live_session_reach"):
                hm = hmod.live_session_reach(STATE, pid_alive) or ""
        except Exception:
            hm = ""
    gmod, _gerr = _load_attach_202()
    if gmod is not None:
        try:
            if hasattr(gmod, "live_session_reach"):
                gk = gmod.live_session_reach(STATE, pid_alive) or ""
        except Exception:
            gk = ""
    cmod, _cerr = _load_attach_220()
    if cmod is not None:
        try:
            if hasattr(cmod, "live_session_reach"):
                cx = cmod.live_session_reach(STATE, pid_alive) or ""
        except Exception:
            cx = ""
    clmod, _clerr = _load_attach_221()
    if clmod is not None:
        try:
            if hasattr(clmod, "live_session_reach"):
                cl = clmod.live_session_reach(STATE, pid_alive) or ""
        except Exception:
            cl = ""
    try:
        cur = active_harness("grok")
    except Exception:
        cur = ""
    if cur in ("claude", "claude-code") and cl:
        return cl
    if cur == "codex" and cx:
        return cx
    if cur == "grok" and gk:
        return gk
    if cur == "hermes" and hm:
        return hm
    if cur == "opencode" and oc:
        return oc
    return cl or cx or gk or hm or oc or ""

def open_enterable_opencode_session():
    """Attach + open/focus enterable OpenCode terminal. Cite #162."""
    mod, err = _load_enterable_162()
    stub = opencode_stub_line()
    if mod is None:
        return {
            "ok": False, "id": "opencode", "live": "FAIL", "copy": stub,
            "error": err or "enterable module missing", "session_reach": "FAIL",
        }
    def _set_active(hid):
        (STATE / "active-harness").write_text(str(hid) + "\n", encoding="utf-8")
    return mod.open_enterable_opencode_session(
        ROOT=ROOT, STATE=STATE, which_bin=which_bin,
        live_openai_base=live_openai_base, inspect_models=inspect_models,
        write_opencode_config=write_opencode_config, load_tools_state=load_tools_state,
        apply_skills_dir=apply_skills_dir, grok_home=grok_home, TOOLS_ENV=TOOLS_ENV,
        record_sidecar_pid=record_sidecar_pid, record_last_verb=record_last_verb,
        pid_alive=pid_alive, active_harness_setter=_set_active, stub_line=stub,
    )


def open_enterable_hermes_session():
    """Attach Hermes + prove models list + smoke. Cite #196."""
    mod, err = _load_attach_196()
    stub = hermes_stub_line()
    if mod is None:
        return {
            "ok": False, "id": "hermes", "live": "FAIL", "copy": stub,
            "error": err or "hermes attach module missing", "session_reach": "FAIL",
            "usable": False,
        }
    def _set_active(hid):
        (STATE / "active-harness").write_text(str(hid) + "\n", encoding="utf-8")
    return mod.open_enterable_hermes_session(
        ROOT=ROOT, STATE=STATE, which_bin=which_bin,
        live_openai_base=live_openai_base, inspect_models=inspect_models,
        record_sidecar_pid=record_sidecar_pid, record_last_verb=record_last_verb,
        pid_alive=pid_alive, active_harness_setter=_set_active, stub_line=stub,
    )


def open_enterable_grok_session():
    """Attach Grok + prove models list + smoke. Cite #202."""
    mod, err = _load_attach_202()
    stub = grok_stub_line()
    if mod is None:
        return {
            "ok": False, "id": "grok", "live": "FAIL", "copy": stub,
            "error": err or "grok attach module missing", "session_reach": "FAIL",
            "usable": False,
        }
    def _set_active(hid):
        (STATE / "active-harness").write_text(str(hid) + "\n", encoding="utf-8")
    return mod.open_enterable_grok_session(
        ROOT=ROOT, STATE=STATE, which_bin=which_bin,
        live_openai_base=live_openai_base, inspect_models=inspect_models,
        record_sidecar_pid=record_sidecar_pid, record_last_verb=record_last_verb,
        pid_alive=pid_alive, active_harness_setter=_set_active, stub_line=stub,
    )


def open_enterable_codex_session():
    """Attach Codex + prove models list + smoke. Cite #220."""
    mod, err = _load_attach_220()
    stub = codex_stub_line()
    if mod is None:
        return {
            "ok": False, "id": "codex", "live": "FAIL", "copy": stub,
            "error": err or "codex attach module missing", "session_reach": "FAIL",
            "usable": False,
        }
    def _set_active(hid):
        (STATE / "active-harness").write_text(str(hid) + "\n", encoding="utf-8")
    return mod.open_enterable_codex_session(
        ROOT=ROOT, STATE=STATE, which_bin=which_bin,
        live_openai_base=live_openai_base, inspect_models=inspect_models,
        record_sidecar_pid=record_sidecar_pid, record_last_verb=record_last_verb,
        pid_alive=pid_alive, active_harness_setter=_set_active, stub_line=stub,
    )


def open_enterable_claude_session():
    """Attach Claude + prove models list + smoke. Cite #221."""
    mod, err = _load_attach_221()
    stub = claude_stub_line()
    if mod is None:
        return {
            "ok": False, "id": "claude", "live": "FAIL", "copy": stub,
            "error": err or "claude attach module missing", "session_reach": "FAIL",
            "usable": False,
        }
    def _set_active(hid):
        (STATE / "active-harness").write_text(str(hid) + "\n", encoding="utf-8")
    return mod.open_enterable_claude_session(
        ROOT=ROOT, STATE=STATE, which_bin=which_bin,
        live_openai_base=live_openai_base, inspect_models=inspect_models,
        record_sidecar_pid=record_sidecar_pid, record_last_verb=record_last_verb,
        pid_alive=pid_alive, active_harness_setter=_set_active, stub_line=stub,
    )


def pid_alive(pid):
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def live_openai_base():
    """Fresh FreeToken-first detect at call time (#171). Ready detect base only.

    Do not fall back to shell LOCAL_OPENAI_BASE_URL (often a stale Ollama Launch pin).
    """
    det = detector_json()
    status = str(det.get("status") or "").strip().lower()
    base = str(det.get("base_url") or "").strip()
    if base == "(none)":
        base = ""
    # Ready + non-empty detect base wins — FreeToken before Ollama when both up.
    if status == "ready" and base:
        b = base.rstrip("/")
        if not b.endswith("/v1"):
            b = b + "/v1"
        return b, det
    return "", det


def write_opencode_config(base, models):
    STATE.mkdir(parents=True, exist_ok=True)
    name = ""
    if models:
        name = str(models[0]).strip()
    if not name:
        name = (os.environ.get("LOCAL_CODER_MODEL") or os.environ.get("PFY_FT_MODEL") or os.environ.get("PFY_OLLAMA_MODEL") or "local").strip() or "local"
    opts = {}
    opts["baseURL"] = base
    opts["apiKey"] = "local"
    localp = {}
    localp["name"] = "local"
    localp["options"] = opts
    localp["models"] = {name: {"name": name}}
    localp["npm"] = "@ai-sdk/openai-compatible"
    cfg = {"provider": {"local": localp}, "model": "local/" + name}
    tst = load_tools_state()
    tools_name = local_tools_model()
    if (tst.get("tools_mode") or "") == "local_tools" and tools_name:
        name = tools_name
        localp["models"][name] = {"name": name}
        cfg["model"] = "local/" + name
    mcp = {}
    if tst.get("mcp"):
        mcp["codebase-memory"] = {"type": "local", "command": ["codebase-memory-mcp"], "enabled": True}
    if tst.get("write_guard"):
        wg = write_guard_root()
        src = str((wg / "src") if wg else "")
        mcp["write-guard"] = {
            "type": "local",
            "command": ["python3", "-m", "write_guard", "serve"],
            "enabled": True,
            "environment": {
                "WRITE_GUARD_MODE": "enforce",
                "WRITE_GUARD_ROOTS": str(ROOT),
                "PYTHONPATH": src,
            },
        }
    if mcp:
        cfg["mcp"] = mcp
    path = STATE / "opencode.json"
    path.write_text(json.dumps(cfg, indent=2) + chr(10), encoding="utf-8")
    gen = ROOT / "examples" / "opencode-ollama" / ".generated" / "opencode.json"
    try:
        gen.parent.mkdir(parents=True, exist_ok=True)
        gen.write_text(json.dumps(cfg, indent=2) + chr(10), encoding="utf-8")
    except OSError:
        pass
    return path, name

def record_sidecar_pid(hid, pid):
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / ("sidecar-%s.pid" % hid)).write_text(str(pid) + chr(10), encoding="utf-8")

def sidecar_pid_live():
    for hid in ("opencode", "grok", "hermes", "codex", "claude"):
        path = STATE / ("sidecar-%s.pid" % hid)
        if not path.is_file():
            continue
        try:
            pid = int(path.read_text(encoding="utf-8", errors="replace").strip())
        except ValueError:
            continue
        if pid_alive(pid):
            return pid
    return ""

def record_last_verb(verb):
    STATE.mkdir(parents=True, exist_ok=True)
    when = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (STATE / "last-verb").write_text("verb: %s\nwhen: %s\n" % (verb, when), encoding="utf-8")

def opencode_stub_line():
    rec = next((h for h in (load_registry().get("harnesses") or []) if h.get("id") == "opencode"), {}) or {}
    return one_liner("opencode", rec)


def hermes_stub_line():
    rec = next((h for h in (load_registry().get("harnesses") or []) if h.get("id") == "hermes"), {}) or {}
    return one_liner("hermes", rec)


def grok_stub_line():
    rec = next((h for h in (load_registry().get("harnesses") or []) if h.get("id") == "grok"), {}) or {}
    return one_liner("grok", rec)


def codex_stub_line():
    rec = next((h for h in (load_registry().get("harnesses") or []) if h.get("id") == "codex"), {}) or {}
    return one_liner("codex", rec)


def claude_stub_line():
    rec = next((h for h in (load_registry().get("harnesses") or []) if h.get("id") == "claude-code"), {}) or {}
    return one_liner("claude-code", rec) or "npm install -g @anthropic-ai/claude-code"

def grok_path_live():
    return "ready" if which_bin("grok") else "missing"

def monitor_pid_live():
    path = STATE / "sidecar-grok.pid"
    if not path.is_file():
        return ""
    try:
        pid = int(path.read_text(encoding="utf-8", errors="replace").strip())
    except ValueError:
        return ""
    return pid if pid_alive(pid) else ""

def last_monitor_note():
    paths = (
        STATE / "monitor-note",
        ROOT / "examples" / "opencode-ollama" / ".generated" / "monitor-brief.md",
    )
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            continue
        for line in text.splitlines():
            s = line.strip().lstrip("#").strip()
            if not s:
                continue
            if s.lower().startswith("generated"):
                continue
            return s[:240]
    return ""

def write_monitor_note(text):
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / "monitor-note").write_text((text or "").strip()[:240] + "\n", encoding="utf-8")

def start_monitor_sidecar():
    """Separate monitor-role sidecar. Attach Grok uses open_enterable_grok_session (#202)."""
    stub = grok_stub_line()
    profile = deploy_profile()
    if profile == "local-only":
        return {
            "ok": False, "id": "grok", "live": "FAIL", "copy": "local-only",
            "error": "local-only never auto-calls cloud", "role": "monitor",
        }
    bin_path = which_bin("grok")
    if not bin_path:
        return {
            "ok": False, "id": "grok", "live": "FAIL", "copy": stub,
            "error": "grok missing", "role": "monitor",
        }
    brief = ROOT / "examples" / "opencode-ollama" / ".generated" / "monitor-brief.md"
    note = last_monitor_note()
    if not note:
        note = "review / hard DoD"
        if brief.is_file():
            note = last_monitor_note() or note
    log = STATE / "sidecar-grok.log"
    env = os.environ.copy()
    if brief.is_file():
        env["PFY_MONITOR_BRIEF"] = str(brief)
    with log.open("ab") as f:
        proc = subprocess.Popen(
            [bin_path],
            cwd=str(ROOT),
            env=env,
            stdout=f,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    if not pid_alive(proc.pid):
        err = ""
        try:
            err = log.read_text(encoding="utf-8", errors="replace")[-400:]
        except Exception:
            err = "grok exited"
        return {
            "ok": False, "id": "grok", "live": "FAIL", "copy": stub,
            "error": err or "grok exited", "pid": proc.pid, "log": str(log),
            "role": "monitor",
        }
    record_sidecar_pid("grok", proc.pid)
    record_last_verb("start grok")
    write_monitor_note("monitor pid %s · %s" % (proc.pid, note))
    return {
        "ok": True, "id": "grok", "live": "READY", "pid": proc.pid,
        "sidecar": True, "log": str(log), "role": "monitor",
        "note": last_monitor_note(),
    }

SKILL_IDS = ("one-shot", "investigate", "agent-loops", "hermes-feedback")
SKILLS_ROOT = ROOT / "bootstrap" / "grok-cli" / "skills"
TOOLS_FILE = STATE / "tools.json"
MCP_FRAGMENT = ROOT / "bootstrap" / "grok-cli" / "config" / "config.fragment.toml"
WRITE_GUARD_DIR = ROOT / "harness" / "write-guard-mcp"
WRITE_GUARD_ALT = ROOT / "tools" / "write-guard-mcp"
TOOLS_ENV = ROOT / "examples" / "opencode-ollama" / ".generated" / "tools-model.env"
MERGE_PY = ROOT / "bootstrap" / "grok-cli" / "scripts" / "merge_config.py"
WG_OVERLAY = ROOT / "harness" / "agent-cage" / "overlays" / "write-guard" / "mcp-servers.write-guard.yaml"
OPENCODE_JSON = STATE / "opencode.json"
STATE_GROK = STATE / "grok-config.toml"

def default_tools_state():
    skills = {}
    for sid in SKILL_IDS:
        skills[sid] = (SKILLS_ROOT / sid / "SKILL.md").is_file()
    return {
        "skills": skills,
        "mcp": False,
        "write_guard": False,
        "tools_mode": "split",
    }

def load_tools_state():
    base = default_tools_state()
    if TOOLS_FILE.is_file():
        try:
            raw = json.loads(TOOLS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raw = {}
        if isinstance(raw, dict):
            sk = raw.get("skills") if isinstance(raw.get("skills"), dict) else {}
            for sid in SKILL_IDS:
                if sid in sk:
                    base["skills"][sid] = bool(sk[sid])
            if "mcp" in raw:
                base["mcp"] = bool(raw.get("mcp"))
            if "write_guard" in raw:
                base["write_guard"] = bool(raw.get("write_guard"))
            mode = str(raw.get("tools_mode") or "").strip()
            if mode in ("split", "local_tools"):
                base["tools_mode"] = mode
    return base

def save_tools_state(st):
    STATE.mkdir(parents=True, exist_ok=True)
    TOOLS_FILE.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")

def apply_skills_dir(st):
    dest = STATE / "opencode-skills"
    dest.mkdir(parents=True, exist_ok=True)
    for child in list(dest.iterdir()):
        try:
            child.unlink()
        except OSError:
            pass
    enabled = []
    for sid in SKILL_IDS:
        if not st.get("skills", {}).get(sid):
            continue
        src = SKILLS_ROOT / sid
        if not (src / "SKILL.md").is_file():
            continue
        link = dest / sid
        try:
            link.symlink_to(src)
        except OSError:
            return None, "cannot link " + sid
        enabled.append(sid)
    return dest, enabled

def local_tools_model():
    name = (os.environ.get("LOCAL_TOOLS_MODEL") or "").strip()
    if name:
        return name
    if TOOLS_ENV.is_file():
        for line in TOOLS_ENV.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.strip()
            if s.startswith("export LOCAL_TOOLS_MODEL="):
                return s.split("=", 1)[1].strip().strip("'\"")
            if s.startswith("LOCAL_TOOLS_MODEL="):
                return s.split("=", 1)[1].strip().strip("'\"")
    return ""


def grok_home():
    return Path(os.environ.get("GROK_HOME") or str(Path.home() / ".grok"))

def grok_config_path():
    return grok_home() / "config.toml"

def write_guard_root():
    if WRITE_GUARD_DIR.is_dir():
        return WRITE_GUARD_DIR
    if WRITE_GUARD_ALT.is_dir():
        return WRITE_GUARD_ALT
    return None

def upsert_env_file(path, updates):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    seen = set()
    out = []
    for line in lines:
        s = line.strip()
        key = ""
        raw = s[7:].strip() if s.startswith("export ") else s
        if raw and not raw.startswith("#") and "=" in raw:
            key = raw.split("=", 1)[0].strip()
        if key in updates:
            out.append("%s=%s" % (key, updates[key]))
            seen.add(key)
        else:
            out.append(line)
    for key, val in updates.items():
        if key not in seen:
            out.append("%s=%s" % (key, val))
    path.write_text("\n".join(out) + "\n", encoding="utf-8")

def patch_toml_section_enabled(path, section, enabled):
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    header = "[" + section + "]"
    if header not in text:
        return False
    parts = text.split(header, 1)
    body = parts[1]
    nxt = body.find("\n[")
    chunk, rest = (body[:nxt], body[nxt:]) if nxt >= 0 else (body, "")
    if "enabled = true" in chunk or "enabled = false" in chunk:
        chunk = chunk.replace("enabled = true", "enabled = " + ("true" if enabled else "false"), 1)
        if enabled:
            chunk = chunk.replace("enabled = false", "enabled = true", 1)
        else:
            chunk = chunk.replace("enabled = true", "enabled = false", 1)
    else:
        chunk = chunk.rstrip() + "\nenabled = " + ("true" if enabled else "false") + "\n"
    path.write_text(parts[0] + header + chunk + rest, encoding="utf-8")
    return True

def apply_mcp(want):
    if want:
        if not MCP_FRAGMENT.is_file():
            return False, "mcp recipe missing"
        if not MERGE_PY.is_file():
            return False, "mcp merge missing"
        STATE.mkdir(parents=True, exist_ok=True)
        targets = [STATE_GROK, grok_config_path()]
        last_err = ""
        applied = False
        for dest in targets:
            dest.parent.mkdir(parents=True, exist_ok=True)
            rc, out = _run(["python3", str(MERGE_PY), "--config", str(dest), "--no-backup"], timeout=20.0)
            if rc != 0:
                last_err = (out or "mcp merge failed")[-300:]
                continue
            text = dest.read_text(encoding="utf-8", errors="replace") if dest.is_file() else ""
            if "mcp_servers.codebase-memory" not in text:
                last_err = "mcp not in config"
                continue
            applied = True
        if not applied:
            return False, last_err or "mcp merge failed"
        return True, ""
    for dest in (STATE_GROK, grok_config_path()):
        patch_toml_section_enabled(dest, "mcp_servers.codebase-memory", False)
    return True, ""

def apply_write_guard(want):
    wg = write_guard_root()
    if want:
        if wg is None or not (wg / "src" / "write_guard").is_dir():
            return False, "write-guard missing"
        if not WG_OVERLAY.is_file():
            return False, "write-guard overlay missing"
        STATE.mkdir(parents=True, exist_ok=True)
        overlay = WG_OVERLAY.read_text(encoding="utf-8")
        overlay = overlay.replace("enabled: false", "enabled: true").replace("WRITE_GUARD_MODE: audit", "WRITE_GUARD_MODE: enforce")
        overlay = overlay.replace("PYTHONPATH: /workspace/.venvs/write-guard-smoke/lib/python3.12/site-packages", "PYTHONPATH: " + str(wg / "src"))
        overlay = overlay.replace("WRITE_GUARD_ROOTS: /workspace", "WRITE_GUARD_ROOTS: " + str(ROOT))
        (STATE / "mcp-servers.write-guard.yaml").write_text(overlay, encoding="utf-8")
        cage = Path.home() / ".agentcage"
        try:
            cage.mkdir(parents=True, exist_ok=True)
            (cage / "mcp-servers.write-guard.yaml").write_text(overlay, encoding="utf-8")
        except OSError:
            pass
        gpath = grok_config_path()
        block = (
            "\n[mcp_servers.write-guard]\n"
            'command = "python3"\n'
            'args = ["-m", "write_guard", "serve"]\n'
            "enabled = true\n"
        )
        for dest in (STATE_GROK, gpath):
            dest.parent.mkdir(parents=True, exist_ok=True)
            cur = dest.read_text(encoding="utf-8") if dest.is_file() else ""
            if "[mcp_servers.write-guard]" not in cur:
                dest.write_text(cur.rstrip() + block + "\n", encoding="utf-8")
            else:
                patch_toml_section_enabled(dest, "mcp_servers.write-guard", True)
        env = os.environ.copy()
        env["PYTHONPATH"] = str(wg / "src") + os.pathsep + env.get("PYTHONPATH", "")
        env["WRITE_GUARD_MODE"] = "enforce"
        env["WRITE_GUARD_ROOTS"] = str(ROOT)
        policy = wg / "policy.default.yaml"
        if policy.is_file():
            env["WRITE_GUARD_POLICY"] = str(policy)
        probe = ROOT / "README.md"
        if not probe.is_file():
            probe = wg / "README.md"
        try:
            p = subprocess.run(
                ["python3", "-m", "write_guard", "check", "--path", str(probe), "--op", "write", "--mode", "enforce"],
                cwd=str(ROOT), capture_output=True, text=True, timeout=20.0, env=env,
            )
            rc, out = p.returncode, (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
        except (OSError, subprocess.TimeoutExpired) as e:
            rc, out = 1, str(e)
        if rc != 0:
            return False, (out or "write-guard check failed")[-300:]
        upsert_env_file(TOOLS_ENV, {"WRITE_GUARD_MODE": "enforce", "WRITE_GUARD_ROOTS": str(ROOT)})
        (STATE / "write-guard-mode").write_text("enforce\n", encoding="utf-8")
        return True, ""
    for dest in (STATE_GROK, grok_config_path()):
        patch_toml_section_enabled(dest, "mcp_servers.write-guard", False)
    upsert_env_file(TOOLS_ENV, {"WRITE_GUARD_MODE": "off"}) if TOOLS_ENV.parent.is_dir() or TOOLS_ENV.is_file() else None
    (STATE / "write-guard-mode").write_text("off\n", encoding="utf-8")
    yml = STATE / "mcp-servers.write-guard.yaml"
    if yml.is_file():
        yml.write_text(yml.read_text(encoding="utf-8").replace("enabled: true", "enabled: false"), encoding="utf-8")
    return True, ""

def apply_extra_tools(want):
    name = local_tools_model()
    mode = "local_tools" if want else "split"
    if want and not name:
        return False, "no local tools model"
    STATE.mkdir(parents=True, exist_ok=True)
    updates = {"TOOLS_MODE": mode}
    if name:
        updates["LOCAL_TOOLS_MODEL"] = name
    upsert_env_file(TOOLS_ENV, updates)
    text = TOOLS_ENV.read_text(encoding="utf-8") if TOOLS_ENV.is_file() else ""
    if ("TOOLS_MODE=" + mode) not in text.replace("export ", ""):
        return False, "tools-model.env not applied"
    if want and "LOCAL_TOOLS_MODEL=" not in text.replace("export ", ""):
        return False, "LOCAL_TOOLS_MODEL not applied"
    (STATE / "tools-mode").write_text(mode + "\n", encoding="utf-8")
    return True, ""

def set_tool(tid, on):
    tid = (tid or "").strip()
    st = load_tools_state()
    want = bool(on)
    if tid in SKILL_IDS:
        skill = SKILLS_ROOT / tid / "SKILL.md"
        if want and not skill.is_file():
            return {"ok": False, "live": "FAIL", "copy": "FAIL " + tid, "error": tid + " missing", "id": tid}
        st["skills"][tid] = want
        dest, enabled = apply_skills_dir(st)
        if dest is None:
            return {"ok": False, "live": "FAIL", "copy": "FAIL " + tid, "error": enabled, "id": tid}
        save_tools_state(st)
        copy = ("ON " if want else "OFF ") + tid
        return {"ok": True, "live": "PASS", "copy": copy, "id": tid, "on": want, "tools": st}
    if tid == "mcp":
        ok, err = apply_mcp(want)
        if not ok:
            return {"ok": False, "live": "FAIL", "copy": "FAIL mcp", "error": err, "id": tid}
        st["mcp"] = want
        save_tools_state(st)
        (STATE / "mcp-on").write_text("1\n" if want else "0\n", encoding="utf-8")
        return {"ok": True, "live": "PASS", "copy": ("ON " if want else "OFF ") + "mcp", "id": tid, "on": want, "tools": st}
    if tid in ("write-guard", "write_guard"):
        ok, err = apply_write_guard(want)
        if not ok:
            return {"ok": False, "live": "FAIL", "copy": "FAIL write-guard", "error": err, "id": "write-guard"}
        st["write_guard"] = want
        save_tools_state(st)
        return {"ok": True, "live": "PASS", "copy": ("ON " if want else "OFF ") + "write-guard", "id": "write-guard", "on": want, "tools": st}
    if tid in ("extra-tools", "local_tools", "tools_mode"):
        ok, err = apply_extra_tools(want)
        if not ok:
            return {"ok": False, "live": "FAIL", "copy": "FAIL extra tools", "error": err, "id": "extra-tools"}
        st["tools_mode"] = "local_tools" if want else "split"
        save_tools_state(st)
        copy = "ON extra tools" if want else "OFF extra tools"
        return {"ok": True, "live": "PASS", "copy": copy, "id": "extra-tools", "on": want, "tools": st}
    return {"ok": False, "live": "FAIL", "copy": "FAIL tools", "error": "unknown toggle", "id": tid}

def start_sidecar(hid, mode=None):
    """Spawn grok/opencode/hermes/codex/claude/gab sidecar. Grok #202; Hermes #196; OpenCode #171/#193; Codex #220; Claude #221; Gab #228. Mode handoff (#208)."""
    hid = (hid or "").strip()
    if not hid:
        hid = active_harness("grok")
    cur = active_harness("grok")
    if cur in STUB_ALWAYS:
        return {
            "ok": False, "id": hid, "live": "FAIL", "copy": GROK_USE,
            "error": f"{cur} is active — no grok/opencode fallback",
        }
    if hid in STUB_ALWAYS:
        return {
            "ok": False, "id": hid, "live": "FAIL", "copy": GROK_USE,
            "error": f"{hid} is not startable from the window",
        }
    if hid not in SIDECAR_OK:
        return {
            "ok": False, "id": hid, "live": "FAIL", "copy": GROK_USE,
            "error": f"{hid} is not a sidecar",
        }
    if hid == "claude-code":
        hid = "claude"
    STATE.mkdir(parents=True, exist_ok=True)
    if hid == "gab":
        # Cloud lane: key/auto prove; no local attach-mode MCP. Cite #228.
        result = open_enterable_gab_session()
        result = dict(result or {})
        result["mode"] = (mode or "bare")
        result["using"] = result["mode"]
        return result
    mmod, merr = _load_attach_mode_208()
    if mmod is None:
        return {
            "ok": False, "id": hid, "live": "FAIL", "copy": "FAIL mode -- module missing",
            "error": merr or "pfy_attach_mode_208 missing", "usable": False,
            "session_reach": "FAIL", "next_step": "./pfy setup",
        }
    prepared = mmod.prepare(ROOT, STATE, hid, mode=mode, which=which_bin)
    if not prepared.get("ok"):
        return prepared
    cmod, _cerr = _load_catalog_209()
    if cmod is not None:
        try:
            cmod.apply_child_env(os.environ, STATE)
        except Exception:
            pass
    using = prepared.get("mode") or "bare"
    started = None
    graph = None
    if using == "code-graph":
        graph = {
            "graph_ok": bool(prepared.get("graph_ok")),
            "graph_copy": prepared.get("graph_copy") or "",
            "graph_path": prepared.get("graph_path") or "",
            "graph_when": prepared.get("graph_when") or "",
        }
        if not prepared.get("graph_ok") and not prepared.get("graph_path"):
            gmod, gerr = _load_code_graph_215()
            if gmod is None:
                return {
                    "ok": False, "id": hid, "live": "FAIL",
                    "copy": "FAIL code-graph -- module missing",
                    "error": gerr or "pfy_code_graph_215 missing", "usable": False,
                    "session_reach": "FAIL", "next_step": "./pfy setup",
                    "mode": using, "using": using, "graph_ok": False,
                }
    if using == "orchestration":
        omod, oerr = _load_orchestration_213()
        if omod is None:
            return {
                "ok": False, "id": hid, "live": "FAIL",
                "copy": "FAIL orchestration -- module missing",
                "error": oerr or "pfy_orchestration_213 missing", "usable": False,
                "session_reach": "FAIL", "next_step": "./pfy setup",
                "mode": using, "using": using, "loop_ok": False,
            }
        started = omod.start_loop(
            ROOT, STATE, hid,
            live_openai_base=live_openai_base,
            inspect_models_fn=inspect_models,
        )
        if not started.get("ok"):
            return started
    if hid == "grok":
        result = open_enterable_grok_session()
    elif hid == "opencode":
        result = open_enterable_opencode_session()
    elif hid == "hermes":
        result = open_enterable_hermes_session()
    elif hid == "codex":
        result = open_enterable_codex_session()
    elif hid == "claude":
        result = open_enterable_claude_session()
    elif hid == "gab":
        result = open_enterable_gab_session()
    else:
        result = None
    if result is not None:
        result = dict(result)
        result["mode"] = using
        result["using"] = using
        if result.get("ok") and result.get("usable") is not False:
            mmod.mark_live(STATE, using)
            copy = str(result.get("copy") or "")
            tag = "using: %s" % using
            if tag not in copy:
                result["copy"] = (copy + " · " + tag).strip(" ·")
            if started and started.get("loop_copy"):
                lc = started.get("loop_copy")
                if lc and lc not in str(result.get("copy") or ""):
                    result["copy"] = (result.get("copy") + " · " + lc).strip(" ·")
                result["loop_ok"] = True
                result["loop_copy"] = lc
                result["loop_when"] = started.get("loop_when") or ""
                result["loop_model"] = started.get("loop_model") or ""
                result["loop_steps"] = started.get("loop_steps") or 0
                result["loop_status"] = started.get("loop_status") or ""
                result["loop_evidence"] = started.get("loop_evidence") or ""
            if graph and graph.get("graph_copy"):
                gc = graph.get("graph_copy")
                if gc and gc not in str(result.get("copy") or ""):
                    result["copy"] = (result.get("copy") + " · " + gc).strip(" ·")
                result["graph_ok"] = True
                result["graph_copy"] = gc
                result["graph_path"] = graph.get("graph_path") or ""
                result["graph_when"] = graph.get("graph_when") or ""
        return result
    log = STATE / f"sidecar-{hid}.log"
    with log.open("ab") as f:
        proc = subprocess.Popen(
            ["bash", str(PFY), "start", hid],
            cwd=str(ROOT),
            stdout=f,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    return {"ok": True, "id": hid, "live": "READY", "pid": proc.pid, "sidecar": True, "log": str(log)}


def run_space_invaders():
    """Session proof: Attach OpenCode required, then workspace/space-invaders. Cite #155."""
    import importlib.util
    path = ROOT / "scripts" / "pfy_space_invaders.py"
    if not path.is_file():
        return {
            "ok": False, "live": "FAIL",
            "copy": "FAIL Space Invaders · module missing",
            "error": str(path), "path": "",
        }
    spec = importlib.util.spec_from_file_location("pfy_space_invaders", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run(
        root=ROOT,
        state=STATE,
        which_bin=which_bin,
        write_opencode_config=write_opencode_config,
        live_openai_base=live_openai_base,
        inspect_models=inspect_models,
        record_last_verb=record_last_verb,
        active_harness=active_harness,
        pid_alive=pid_alive,
    )

def _load_verify_159():
    """Load pfy_verify_159 or return (None, error). Cite #159."""
    import importlib.util
    path = ROOT / "scripts" / "pfy_verify_159.py"
    if not path.is_file():
        return None, str(path)
    try:
        spec = importlib.util.spec_from_file_location("pfy_verify_159", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod, ""
    except Exception as e:
        return None, str(e)[:400]

def open_space_invaders_game():
    mod, err = _load_verify_159()
    if mod is None:
        return {"ok": False, "live": "FAIL", "copy": "FAIL Open game · module missing", "error": err}
    try:
        return mod.open_game(ROOT)
    except Exception as e:
        return {"ok": False, "live": "FAIL", "copy": "FAIL Open game", "error": str(e)[:400]}

def open_space_invaders_folder():
    mod, err = _load_verify_159()
    if mod is None:
        return {"ok": False, "live": "FAIL", "copy": "FAIL Open folder · module missing", "error": err}
    try:
        return mod.open_folder(ROOT)
    except Exception as e:
        return {"ok": False, "live": "FAIL", "copy": "FAIL Open folder", "error": str(e)[:400]}

def space_invaders_task():
    mod, err = _load_verify_159()
    if mod is None:
        return {"ok": False, "live": "FAIL", "copy": "FAIL Copy TASK · module missing", "error": err, "task_text": ""}
    try:
        return mod.task_payload(ROOT)
    except Exception as e:
        return {"ok": False, "live": "FAIL", "copy": "FAIL Copy TASK", "error": str(e)[:400], "task_text": ""}

def space_invaders_artifact():
    mod, err = _load_verify_159()
    if mod is None:
        return {"ok": False, "live": "FAIL", "copy": "FAIL artifact · module missing", "error": err}
    try:
        return mod.artifact_get(ROOT)
    except Exception as e:
        return {"ok": False, "live": "FAIL", "copy": "FAIL artifact", "error": str(e)[:400]}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("[pfy] " + (fmt % args) + "\n")
    def _send(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if ctype.startswith("text/html"):
            self.send_header("X-Pfy-UI", "session")
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send(200, html_page().encode("utf-8"), "text/html; charset=utf-8"); return
        asset = frontend_static(path)
        if asset:
            fp, ctype = asset
            self._send(200, fp.read_bytes(), ctype); return
        if path == "/snapshot":
            self._send(200, json.dumps(snapshot(), indent=2).encode("utf-8"), "application/json; charset=utf-8"); return
        if path == "/usage":
            self._send(200, json.dumps(local_usage_info(), indent=2).encode("utf-8"), "application/json; charset=utf-8"); return
        if path == "/space-invaders/artifact":
            result = space_invaders_artifact()
            code = 200 if result.get("ok") else 404
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8"); return
        self._send(404, b"not found\n", "text/plain; charset=utf-8")
    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/start":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode() or "{}")
            except json.JSONDecodeError:
                body = {}
            hid = str((body or {}).get("id") or "")
            mode = (body or {}).get("mode")
            result = start_sidecar(hid, mode=mode)
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path == "/mode":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode() or "{}")
            except json.JSONDecodeError:
                body = {}
            mode = str((body or {}).get("mode") or "")
            result = set_attach_mode(mode)
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path == "/stage":
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)
            result = run_stage()
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path == "/env":
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)
            result = launch_env()
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path == "/models/recommend":
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)
            result = recommend_models()
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path == "/models/try":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode() or "{}")
            except json.JSONDecodeError:
                body = {}
            name = str((body or {}).get("name") or "")
            result = try_recommended_model(name)
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path == "/models/pull":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode() or "{}")
            except json.JSONDecodeError:
                body = {}
            name = str((body or {}).get("name") or "")
            result = pull_model(name)
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path == "/eval":
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)
            result = test_model()
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path == "/catalog/ask":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode() or "{}")
            except json.JSONDecodeError:
                body = {}
            name = str((body or {}).get("name") or (body or {}).get("id") or "")
            result = catalog_ask(name)
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path == "/catalog/queue":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode() or "{}")
            except json.JSONDecodeError:
                body = {}
            name = str((body or {}).get("name") or (body or {}).get("id") or "")
            result = catalog_queue(name)
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path == "/tools":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode() or "{}")
            except json.JSONDecodeError:
                body = {}
            tid = str((body or {}).get("id") or "")
            on = (body or {}).get("on")
            result = set_tool(tid, on)
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path == "/space-invaders":
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)
            result = run_space_invaders()
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path == "/space-invaders/open-game":
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)
            result = open_space_invaders_game()
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path == "/space-invaders/open-folder":
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)
            result = open_space_invaders_folder()
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path in ("/space-invaders/copy-task", "/space-invaders/task"):
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)
            result = space_invaders_task()
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path in ("/module", "/modules"):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode() or "{}")
            except json.JSONDecodeError:
                body = {}
            tid = str((body or {}).get("id") or (body or {}).get("module") or "")
            on = (body or {}).get("on")
            if on is None:
                on = str((body or {}).get("value") or "on").lower() not in ("0", "off", "false", "no")
            result = toggle_loop_module(tid, bool(on))
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path in ("/loop/task", "/hedge/task"):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode() or "{}")
            except json.JSONDecodeError:
                body = {}
            result = set_loop_task(str((body or {}).get("task") or (body or {}).get("value") or ""))
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path == "/loop/agent":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode() or "{}")
            except json.JSONDecodeError:
                body = {}
            result = set_loop_agent(str((body or {}).get("agent") or (body or {}).get("id") or ""))
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path == "/wizard":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode() or "{}")
            except json.JSONDecodeError:
                body = {}
            step = str((body or {}).get("step") or "")
            value = str((body or {}).get("value") or (body or {}).get("id") or "")
            result = wizard_apply(step, value)
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path in ("/launch", "/launch-session"):
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)
            result = launch_wizard_session()
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path in ("/decision/smoke", "/decision"):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode() or "{}")
            except json.JSONDecodeError:
                body = {}
            dpath = str((body or {}).get("path") or (body or {}).get("value") or "cua-s1-forms")
            result = decision_smoke(dpath)
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path in ("/gab/sync", "/models/gab-sync"):
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)
            result = gab_local_sync()
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path in ("/gab/pull", "/models/gab-pull"):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode() or "{}")
            except json.JSONDecodeError:
                body = {}
            tag = str((body or {}).get("tag") or (body or {}).get("name") or "")
            confirm = bool((body or {}).get("confirm") or (body or {}).get("confirm_tight"))
            opt_in = bool((body or {}).get("opt_in_huge"))
            result = gab_pull(tag, confirm_tight=confirm, opt_in_huge=opt_in)
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        if path == "/gab/cloud":
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                body = json.loads(raw.decode() or "{}")
            except json.JSONDecodeError:
                body = {}
            model = str((body or {}).get("model") or "auto")
            mod, err = _load_gab_228()
            if mod is None:
                result = {"ok": False, "live": "FAIL", "copy": "FAIL gab -- module missing", "error": err or "missing"}
            else:
                result = mod.cloud_lane(STATE, model=model, ROOT=ROOT)
            code = 200 if result.get("ok") else 400
            self._send(code, json.dumps(result).encode("utf-8"), "application/json; charset=utf-8")
            return
        self._send(405, b"POST disabled for this path\n", "text/plain; charset=utf-8")

def main():
    args = sys.argv[1:]
    if args[:1] == ["--snapshot"]:
        print(json.dumps(snapshot()))
        return 0
    if args[:1] == ["--start"]:
        hid = args[1] if len(args) > 1 else ""
        mode = args[2] if len(args) > 2 else None
        result = start_sidecar(hid, mode=mode)
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] == ["--mode"]:
        mode = args[1] if len(args) > 1 else ""
        result = set_attach_mode(mode)
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] == ["--stage"]:
        result = run_stage()
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] == ["--env"]:
        result = launch_env()
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] == ["--wizard"]:
        step = args[1] if len(args) > 1 else "runtime"
        value = " ".join(args[2:]).strip()
        result = wizard_apply(step, value)
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] in (["--launch"], ["--launch-session"]):
        result = launch_wizard_session()
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] == ["--pull"]:
        name = args[1] if len(args) > 1 else ""
        result = pull_model(name)
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] == ["--recommend"]:
        result = recommend_models()
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] == ["--try"]:
        name = args[1] if len(args) > 1 else ""
        result = try_recommended_model(name)
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] in (["--decision"], ["--decision-smoke"]):
        dpath = "cua-s1-forms"
        if "--path" in args:
            i = args.index("--path")
            if i + 1 < len(args):
                dpath = args[i + 1]
        elif len(args) > 1 and not args[1].startswith("-"):
            dpath = args[1]
        result = decision_smoke(dpath)
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] in (["--gab-sync"], ["--gab-local-sync"]):
        result = gab_local_sync()
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] == ["--gab-pull"]:
        tag = args[1] if len(args) > 1 else ""
        confirm = "--confirm" in args
        opt_in = "--opt-in-huge" in args
        result = gab_pull(tag, confirm_tight=confirm, opt_in_huge=opt_in)
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] == ["--gab-cloud"]:
        model = "auto"
        if "--model" in args:
            i = args.index("--model")
            if i + 1 < len(args):
                model = args[i + 1]
        elif len(args) > 1 and not args[1].startswith("-"):
            model = args[1]
        mod, err = _load_gab_228()
        if mod is None:
            result = {"ok": False, "copy": "FAIL gab -- module missing", "error": err or "missing"}
        else:
            result = mod.cloud_lane(STATE, model=model, ROOT=ROOT)
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] == ["--eval"]:
        result = test_model()
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] in (["--catalog"], ["--browse"]):
        result = catalog_browse()
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] == ["--ask"]:
        name = " ".join(args[1:]).strip()
        result = catalog_ask(name)
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] == ["--queue"]:
        name = " ".join(args[1:]).strip()
        result = catalog_queue(name)
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] == ["--catalog-status"]:
        result = catalog_status()
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] == ["--tool"]:
        tid = args[1] if len(args) > 1 else ""
        onraw = args[2] if len(args) > 2 else "1"
        on = str(onraw).strip().lower() in ("1", "true", "on", "yes")
        result = set_tool(tid, on)
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] == ["--space-invaders"]:
        result = run_space_invaders()
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] == ["--open-game"]:
        result = open_space_invaders_game()
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] == ["--open-folder"]:
        result = open_space_invaders_folder()
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] in (["--copy-task"], ["--task"]):
        result = space_invaders_task()
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if args[:1] == ["--artifact"]:
        result = space_invaders_artifact()
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if HOST not in ("127.0.0.1", "localhost"):
        print("error: operator HTTP binds loopback only", file=sys.stderr); return 2
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print("native window")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
