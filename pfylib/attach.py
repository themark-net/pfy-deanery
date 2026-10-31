"""One harness-parameterised Attach (T-0121) -- replaces the four ``pfy_attach_usable_*`` clones.

The per-harness differences (binary names, session id, label, install hint,
config dir) live in ``data/harnesses.json[].attach`` and are read through
:func:`pfylib.registry.attach_profile`. Everything else -- FreeToken-first
re-probe, child ``LOCAL_OPENAI_BASE_URL`` / ``OPENAI_BASE_URL``, OpenContext
(#205) and attach-mode (#208) child env, models list + one smoke before any
READY paint, honest FAIL+next -- is the shared body below, byte-for-byte what
``scripts/pfy_attach_usable_{196,202,220,221}.py`` did before they became shims.

Public API
    profile(hid)                       per-harness table row (flat dict)
    prepare(hid, *, mode, lane, env)   AttachPlan: what attach would hand the child (no spawn, no writes)
    open_session(hid, **deps)          the board's ``open_enterable_<x>_session`` body -> dict
    open_opencode_session(**deps)      OpenCode enterable (config, skills, tools env) -> dict
    run(plan, base=None)               CLI prove (models + smoke) -> exit code
    live_session_reach(hid, STATE)     board status chip
    selftest(hid) / main(hid, argv)    ``--selftest`` / ``--prove`` / ``--plan`` entry used by the shims

Helpers from ``pfy_attach_usable_193`` (prove) and ``pfy_enterable_162_a``
(terminal spawn / focus / pid resolve) are imported through ``_legacy`` -- not copied.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import _legacy, registry

NEXT_UP = "Launch env or ./pfy up"
FT_MODELS = "http://127.0.0.1:1919/v1/models"
FT_HEALTH = "http://127.0.0.1:1919/health"
FT_BASE = "http://127.0.0.1:1919/v1"
AGENTS_FILE = "attach-agents.md"  # pfy_attach_mode_208.AGENTS_FILE; the PFY_ATTACH_AGENTS brief
LANE = "local"


# --------------------------------------------------------------- profile ---

def profile(hid: str, root_dir: Path | None = None) -> dict | None:
    """Flat per-harness attach row; accepts the registry id or the session id (``claude`` -> ``claude-code``)."""
    prof = registry.attach_profile(hid, root_dir)
    if prof is None:
        for other in registry.attach_harness_ids(root_dir):
            cand = registry.attach_profile(other, root_dir)
            if cand and cand["session_id"] == hid:
                prof = cand
                break
    if prof is None:
        return None
    sid, label = prof["session_id"], prof["label"]
    prof.update(
        {
            "session_file": "%s-session-reach" % sid,
            "terminal_pid_file": "%s-terminal.pid" % sid,
            "attach_base_file": "%s-attach-base" % sid,
            "log_file": "sidecar-%s.log" % sid,
            "session_reach_ok": "terminal \u00b7 %s \u00b7 models \u00b7 smoke" % label,
            "stub_line": "./pfy start %s" % sid,
            "missing_error": "%s missing" % sid,
            "start_verb": "start %s" % sid,
        }
    )
    return prof


def _require(hid: str, root_dir: Path | None = None) -> dict:
    prof = profile(hid, root_dir)
    if prof is None:
        raise KeyError("no attach profile for harness %r (data/harnesses.json[].attach); have: %s" % (hid, ", ".join(registry.attach_harness_ids(root_dir))))
    return prof


# ------------------------------------------------------------- state files ---

def read_session_reach(hid: str, STATE) -> str:
    path = Path(STATE) / _require(hid)["session_file"]
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()[:80]
    except OSError:
        return ""


def write_session_reach(hid: str, STATE, text: str) -> None:
    STATE = Path(STATE)
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / _require(hid)["session_file"]).write_text((text or "").strip()[:80] + "\n", encoding="utf-8")


def clear_session_reach(hid: str, STATE) -> None:
    STATE = Path(STATE)
    prof = _require(hid)
    for name in (prof["session_file"], prof["terminal_pid_file"], prof["attach_base_file"]):
        path = STATE / name
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass


def write_terminal_pid(hid: str, STATE, pid: int) -> None:
    STATE = Path(STATE)
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / _require(hid)["terminal_pid_file"]).write_text(str(int(pid)) + "\n", encoding="utf-8")


def read_terminal_pid(hid: str, STATE):
    path = Path(STATE) / _require(hid)["terminal_pid_file"]
    if not path.is_file():
        return 0
    try:
        return int(path.read_text(encoding="utf-8", errors="replace").strip())
    except (ValueError, OSError):
        return 0


def live_session_reach(hid: str, STATE, pid_alive=None) -> str:
    """Session reach only if the enterable pid is still alive (#196/#202/#220/#221)."""
    reach = read_session_reach(hid, STATE)
    if not reach or reach in ("FAIL", "SKIP"):
        return reach if reach in ("FAIL", "SKIP") else ""
    pid = read_terminal_pid(hid, STATE)
    alive = False
    if pid and callable(pid_alive):
        alive = bool(pid_alive(pid))
    elif pid:
        try:
            os.kill(int(pid), 0)
            alive = True
        except OSError:
            alive = False
    if not alive:
        clear_session_reach(hid, STATE)
        return ""
    return reach


def fail_not_usable(hid: str, STATE, sid, reason, next_step, engine, status, base="", model=""):
    clear_session_reach(hid, STATE)
    copy = "FAIL attach -- %s \u00b7 %s" % (reason, next_step)
    return {
        "ok": False,
        "id": sid,
        "live": "FAIL",
        "copy": copy,
        "error": reason,
        "session_reach": "FAIL",
        "next_step": next_step,
        "next_steps": [{"id": "next", "label": next_step, "value": next_step}],
        "engine": engine,
        "detect_status": status or "missing",
        "base_url": base,
        "model": model,
        "usable": False,
    }


# ------------------------------------------------------------------ probes ---

def _probe_freetoken(base, det):
    """Explicit :1919 FreeToken probe -- wins over parent Ollama pin / detect lag (#171/#181)."""
    engine = str((det or {}).get("engine") or "").strip() or "none"
    status = str((det or {}).get("status") or "").strip().lower()
    try:
        ft_ok = False
        for path in (FT_MODELS, FT_HEALTH):
            try:
                req = urllib.request.Request(path, method="GET")
                with urllib.request.urlopen(req, timeout=1) as r:
                    if 200 <= int(getattr(r, "status", 200) or 200) < 300:
                        ft_ok = True
                        break
            except Exception:
                continue
        if ft_ok:
            base = FT_BASE
            engine = "freetoken"
            status = "ready"
            if isinstance(det, dict):
                det = dict(det)
                det["engine"] = "freetoken"
                det["status"] = "ready"
                det["base_url"] = "http://127.0.0.1:1919"
    except Exception:
        pass
    if base:
        b = str(base).rstrip("/")
        if not b.endswith("/v1"):
            b = b + "/v1"
        base = b
    return base, det, engine, status


def inspect_models(base_url):
    """CLI/prove inspect -- strip trailing /v1 like #187/#193."""
    if not base_url:
        return []
    base = _legacy.attach_prove().openai_compat_root(base_url)
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
        for m in d.get("data") or []:
            name = (m.get("id") or m.get("name") or "") if isinstance(m, dict) else str(m)
            name = str(name).strip()
            if name and name not in seen:
                seen.add(name)
                ids.append(name)
        for m in d.get("models") or []:
            name = (m.get("name") or m.get("model") or m.get("id") or "") if isinstance(m, dict) else str(m)
            name = str(name).strip()
            if name and name not in seen:
                seen.add(name)
                ids.append(name)
    return ids


def find_bin(hid: str, which_bin, root_dir: Path | None = None) -> str:
    """``detect`` names via the caller's ``which_bin``, then ``attach.bin_fallbacks`` (Codex: ``~/.local/bin/codex``)."""
    prof = _require(hid, root_dir)
    found = which_bin(*prof["binaries"]) if callable(which_bin) else ""
    if found:
        return found
    for fb in prof["bin_fallbacks"]:
        cand = Path(fb).expanduser()
        try:
            if cand.is_file() and os.access(str(cand), os.X_OK):
                return str(cand)
        except OSError:
            pass
    return ""


# --------------------------------------------------------------- child env ---

def _apply_opencontext_env(env, root_dir=None):
    """Handoff OpenContext store env into the Attach child. Cite #205."""
    mod = _legacy.optional("pfy_opencontext_205", root_dir)
    if mod is None:
        return env
    return mod.apply_child_env(env)


def _apply_attach_mode_env(env, STATE=None, root_dir=None):
    """Handoff attach mode into the Attach child. Cite #208."""
    mod = _legacy.optional("pfy_attach_mode_208", root_dir)
    if mod is None:
        return env
    return mod.apply_child_env(env, STATE)


def child_env(env: dict, base: str, STATE, root_dir: Path | None = None) -> dict:
    """Mutate ``env`` exactly as the four scripts did before spawning the terminal."""
    env["LOCAL_OPENAI_BASE_URL"] = base
    env["OPENAI_BASE_URL"] = base
    env["OPENAI_API_KEY"] = env.get("OPENAI_API_KEY") or "local"
    _apply_opencontext_env(env, root_dir)
    _apply_attach_mode_env(env, STATE, root_dir)
    return env


# -------------------------------------------------------------------- plan ---

@dataclass
class AttachPlan:
    """What Attach would hand the child for one harness: binary, state files, env delta, brief."""

    harness: str
    hid: str
    label: str
    issue: int | None
    script: str
    binaries: tuple
    bin_fallbacks: tuple
    next_install: str | None
    config_dir_env: str | None
    session_file: str
    terminal_pid_file: str
    attach_base_file: str
    log_file: str
    session_reach_ok: str
    stub_line: str
    mode: str
    lane: str
    root: str
    state: str
    base_url: str
    env: dict = field(default_factory=dict)
    brief: str | None = None
    ok: bool = True
    error: str = ""
    next_step: str = ""

    def as_dict(self) -> dict:
        d = asdict(self)
        d["binaries"] = list(self.binaries)
        d["bin_fallbacks"] = list(self.bin_fallbacks)
        return d


def prepare(
    hid: str,
    *,
    mode: str | None = None,
    lane: str = LANE,
    env: dict | None = None,
    base: str = "",
    state: Path | None = None,
    root_dir: Path | None = None,
) -> AttachPlan:
    """Compute the attach handoff without spawning or writing.

    ``env`` is the parent environment to derive from (default ``os.environ``);
    ``plan.env`` holds only the keys attach sets or overrides on it. ``base`` is
    the local OpenAI-compatible endpoint; at run time it comes from the
    FreeToken-first probe. ``mode`` other than the state's current attach mode is
    a FAIL with the ``--prepare`` next step (the mode files are written by
    ``pfy_attach_mode_208``, never here).
    """
    prof = _require(hid, root_dir)
    STATE = registry.state_dir(state)
    ROOT = registry.root(root_dir)
    m208 = _legacy.optional("pfy_attach_mode_208", root_dir)
    current = m208.current_mode(STATE) if m208 else "bare"
    plan = AttachPlan(
        harness=prof["id"],
        hid=prof["session_id"],
        label=prof["label"],
        issue=prof["issue"],
        script=prof["script"],
        binaries=prof["binaries"],
        bin_fallbacks=prof["bin_fallbacks"],
        next_install=prof["next_install"],
        config_dir_env=prof["config_dir_env"],
        session_file=prof["session_file"],
        terminal_pid_file=prof["terminal_pid_file"],
        attach_base_file=prof["attach_base_file"],
        log_file=str(STATE / prof["log_file"]),
        session_reach_ok=prof["session_reach_ok"],
        stub_line=prof["stub_line"],
        mode=current,
        lane=lane,
        root=str(ROOT),
        state=str(STATE),
        base_url=base or os.environ.get("LOCAL_OPENAI_BASE_URL") or "",
    )
    if lane != LANE:
        plan.ok = False
        plan.error = "attach is local-lane only (lane %r)" % lane
        plan.next_step = "cloud lane is `./pfy start gab` (#228) or `./pfy hedge decide`"
        return plan
    if mode is not None and m208 is not None:
        sel = m208.normalize_mode(mode)
        if sel not in m208.MODES:
            plan.ok = False
            plan.error = "unknown mode %s" % (sel or "(empty)")
            plan.next_step = m208.NEXT_SELECT
            return plan
        if sel != current:
            plan.ok = False
            plan.mode = sel
            plan.error = "mode %s not prepared in state (current: %s)" % (sel, current)
            plan.next_step = "python3 scripts/pfy_attach_mode_208.py --prepare %s %s" % (prof["session_id"], sel)
            return plan
    parent = dict(env) if env is not None else dict(os.environ)
    child = child_env(dict(parent), plan.base_url, STATE, root_dir)
    plan.env = {k: v for k, v in child.items() if parent.get(k) != v}
    agents = STATE / AGENTS_FILE
    plan.brief = child.get("PFY_ATTACH_AGENTS") or (str(agents) if agents.is_file() else None)
    return plan


# ---------------------------------------------------------------- session ---

def open_session(
    hid: str,
    *,
    ROOT,
    STATE,
    which_bin,
    live_openai_base,
    inspect_models,
    record_sidecar_pid,
    record_last_verb,
    pid_alive,
    active_harness_setter=None,
    stub_line="",
    root_dir: Path | None = None,
):
    """Attach <harness> + open/focus enterable terminal (#196/#202/#220/#221).

    Re-probes FreeToken-first detect immediately before open (#171/#181).
    ok=True with session_reach only when a real enterable surface is up
    against the live detect base AND models list + one smoke succeed.
    Child env inherits LOCAL_OPENAI_BASE_URL / OPENAI_BASE_URL.
    Missing binary is FAIL+next (never a silent stub success).
    """
    prof = _require(hid, root_dir)
    prove = _legacy.attach_prove(root_dir)
    term = _legacy.enterable_helpers(root_dir)
    ROOT = Path(ROOT)
    STATE = Path(STATE)
    sid = prof["session_id"]
    reach_ok = prof["session_reach_ok"]
    stub = stub_line or prof["stub_line"]
    bin_path = find_bin(hid, which_bin, root_dir)
    if not bin_path:
        clear_session_reach(hid, STATE)
        out = {
            "ok": False,
            "id": sid,
            "live": "FAIL",
            "copy": stub,
            "error": prof["missing_error"],
            "session_reach": "FAIL",
            "usable": False,
        }
        if prof["next_install"]:
            out["next_step"] = prof["next_install"]
        return out
    base, det = live_openai_base()
    base, det, engine, status = _probe_freetoken(base, det)
    next_step = NEXT_UP
    if not base or status != "ready":
        reason = "no local engine" if status != "ready" else "no live local endpoint"
        return fail_not_usable(hid, STATE, sid, reason, next_step, engine, status, base=base)

    attach_base_path = STATE / prof["attach_base_file"]
    prev_base = ""
    try:
        if attach_base_path.is_file():
            prev_base = attach_base_path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        prev_base = ""

    term_pid = read_terminal_pid(hid, STATE)
    real = term.resolve_enterable_pid(bin_path, term_pid, pid_alive) if term_pid else 0
    if real and pid_alive(real) and prev_base and prev_base != base:
        clear_session_reach(hid, STATE)
        real = 0
        term_pid = 0
    if real and pid_alive(real) and prev_base == base:
        usable_ok, model, usable_err = prove.prove_developer_usable(base, inspect_models)
        if not usable_ok:
            return fail_not_usable(
                hid, STATE, sid, usable_err or "session not usable", next_step,
                engine, status, base=base, model=model,
            )
        focused = term._focus_pid(real)
        write_session_reach(hid, STATE, reach_ok)
        write_terminal_pid(hid, STATE, real)
        if active_harness_setter:
            active_harness_setter(sid)
        record_last_verb(prof["start_verb"])
        return {
            "ok": True,
            "id": sid,
            "live": "READY",
            "pid": real,
            "sidecar": True,
            "session_reach": reach_ok,
            "focused": bool(focused),
            "copy": "attached %s pid %s \u00b7 %s \u00b7 %s" % (sid, real, reach_ok, engine),
            "error": "",
            "base_url": base,
            "engine": engine,
            "model": model,
            "usable": True,
            "models_ok": True,
            "smoke_ok": True,
        }

    env = child_env(os.environ.copy(), base, STATE, root_dir)
    log = STATE / prof["log_file"]
    ok, pid, err = term.spawn_terminal_opencode(bin_path, str(ROOT), env, log, pid_alive)
    if err:
        err = str(err).replace("OpenCode", prof["label"])
    real = term.resolve_enterable_pid(bin_path, pid if ok else 0, pid_alive)
    if real and pid_alive(real):
        usable_ok, smoke_model, usable_err = prove.prove_developer_usable(base, inspect_models)
        if not usable_ok:
            return fail_not_usable(
                hid, STATE, sid, usable_err or "session not usable", next_step,
                engine, status, base=base, model=smoke_model,
            )
        focused = term._focus_pid(real)
        record_sidecar_pid(sid, real)
        write_terminal_pid(hid, STATE, real)
        write_session_reach(hid, STATE, reach_ok)
        if active_harness_setter:
            active_harness_setter(sid)
        else:
            try:
                (STATE / "active-harness").write_text(sid + "\n", encoding="utf-8")
            except OSError:
                pass
        record_last_verb(prof["start_verb"])
        try:
            STATE.mkdir(parents=True, exist_ok=True)
            attach_base_path.write_text(base + "\n", encoding="utf-8")
        except OSError:
            pass
        return {
            "ok": True,
            "id": sid,
            "live": "READY",
            "pid": real,
            "sidecar": True,
            "log": str(log),
            "base_url": base,
            "model": smoke_model,
            "session_reach": reach_ok,
            "focused": bool(focused),
            "copy": "attached %s pid %s \u00b7 %s \u00b7 %s" % (sid, real, reach_ok, engine),
            "error": "",
            "engine": engine,
            "usable": True,
            "models_ok": True,
            "smoke_ok": True,
        }
    clear_session_reach(hid, STATE)
    return {
        "ok": False,
        "id": sid,
        "live": "FAIL",
        "copy": "FAIL open session -- " + (err or "terminal cannot start"),
        "error": err or "terminal cannot start",
        "session_reach": "FAIL",
        "pid": "",
        "log": str(log),
        "base_url": base,
        "usable": False,
        "next_step": next_step,
    }


def _opencode_mode_env(env, STATE=None):
    """Attach-mode child env plus OpenCode config decoration. Cite #208.

    The return value is what the caller must keep. ``decorate_opencode_config``
    is OpenCode-only; the four harnesses do not call it.
    """
    mod = _legacy.optional("pfy_attach_mode_208")
    if mod is None:
        return env
    env = mod.apply_child_env(env, STATE)
    try:
        mod.decorate_opencode_config(STATE)
    except Exception:
        pass
    return env


def open_opencode_session(
    *,
    ROOT,
    STATE,
    which_bin,
    live_openai_base,
    inspect_models,
    write_opencode_config,
    load_tools_state,
    apply_skills_dir,
    grok_home,
    TOOLS_ENV,
    record_sidecar_pid,
    record_last_verb,
    pid_alive,
    active_harness_setter=None,
    stub_line="",
):
    """Attach OpenCode and open or focus an enterable terminal. Cite #162.

    Same contract ``scripts/pfy_enterable_162_b.py`` had before it became a shim.
    A missing binary, a dead terminal, or a failed models-and-smoke prove is
    FAIL. Nothing here paints READY without that prove. The FreeToken probe
    wins over a tools-env pin. Recovery: install the binary, or point the live
    detect base at an endpoint that passes prove, then call again.
    """
    term = _legacy.enterable_helpers()
    prove = _legacy.attach_prove()
    reach_ok = prove.SESSION_REACH_USABLE
    clear_session_reach = term.clear_session_reach
    read_terminal_pid = term.read_terminal_pid
    write_terminal_pid = term.write_terminal_pid
    write_session_reach = term.write_session_reach
    resolve_enterable_pid = term.resolve_enterable_pid
    ROOT = Path(ROOT)
    STATE = Path(STATE)
    hid = "opencode"
    stub = stub_line or "./pfy start opencode"
    bin_path = which_bin("opencode", "opencode-cli")
    if not bin_path:
        clear_session_reach(STATE)
        return {
            "ok": False,
            "id": hid,
            "live": "FAIL",
            "copy": stub,
            "error": "opencode missing",
            "session_reach": "FAIL",
        }
    base, det = live_openai_base()
    base, det, engine, status = _probe_freetoken(base, det)
    next_step = NEXT_UP
    if not base or status != "ready":
        clear_session_reach(STATE)
        reason = "no local engine" if status != "ready" else "no live local endpoint"
        copy = "FAIL attach -- %s \u00b7 %s" % (reason, next_step)
        return {
            "ok": False,
            "id": hid,
            "live": "FAIL",
            "copy": copy,
            "error": reason,
            "session_reach": "FAIL",
            "next_step": next_step,
            "next_steps": [{"id": "next", "label": next_step, "value": next_step}],
            "engine": engine,
            "detect_status": status or "missing",
        }

    attach_base_path = STATE / "opencode-attach-base"
    prev_base = ""
    try:
        if attach_base_path.is_file():
            prev_base = attach_base_path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        prev_base = ""
    term_pid = read_terminal_pid(STATE)
    real = resolve_enterable_pid(bin_path, term_pid, pid_alive) if term_pid else 0
    if real and pid_alive(real) and prev_base and prev_base != base:
        clear_session_reach(STATE)
        try:
            if attach_base_path.is_file():
                attach_base_path.unlink()
        except OSError:
            pass
        real = 0
        term_pid = 0
    if real and pid_alive(real) and prev_base == base:
        usable_ok, model, usable_err = prove.prove_developer_usable(base, inspect_models)
        if not usable_ok:
            return prove.fail_not_usable(
                clear_session_reach,
                STATE, hid, usable_err or "session not usable", next_step,
                engine, status, base=base, model=model,
            )
        focused = term._focus_pid(real)
        write_session_reach(STATE, reach_ok)
        write_terminal_pid(STATE, real)
        if active_harness_setter:
            active_harness_setter("opencode")
        record_last_verb("start opencode")
        return {
            "ok": True,
            "id": hid,
            "live": "READY",
            "pid": real,
            "sidecar": True,
            "session_reach": reach_ok,
            "focused": bool(focused),
            "copy": "attached opencode pid %s \u00b7 %s \u00b7 %s" % (real, reach_ok, engine),
            "error": "",
            "base_url": base,
            "engine": engine,
            "model": model,
            "usable": True,
            "models_ok": True,
            "smoke_ok": True,
        }

    models = inspect_models(prove.openai_compat_root(base))
    cfg_path, model = write_opencode_config(base, models)
    skills = ROOT / "bootstrap" / "grok-cli" / "skills"
    env = os.environ.copy()
    env["LOCAL_OPENAI_BASE_URL"] = base
    env["OPENAI_BASE_URL"] = base
    env["OPENAI_API_KEY"] = env.get("OPENAI_API_KEY") or "local"
    _apply_opencontext_env(env)
    env["OPENCODE_CONFIG"] = str(cfg_path)
    tst = load_tools_state()
    dest, _enabled = apply_skills_dir(tst)
    if dest is not None:
        env["OPENCODE_SKILLS"] = str(dest)
    elif skills.is_dir():
        env["OPENCODE_SKILLS"] = str(skills)
    _opencode_mode_env(env, STATE)
    env["TOOLS_MODE"] = str(tst.get("tools_mode") or "split")
    env["WRITE_GUARD_MODE"] = "enforce" if tst.get("write_guard") else "off"
    env["PFY_MCP"] = "1" if tst.get("mcp") else "0"
    tools_env = Path(TOOLS_ENV) if TOOLS_ENV else None
    if tools_env and tools_env.is_file():
        for line in tools_env.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.strip()
            if s.startswith("export "):
                s = s[7:].strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            env[k.strip()] = v.strip().strip("'\"")
    env["LOCAL_OPENAI_BASE_URL"] = base
    env["OPENAI_BASE_URL"] = base
    env["GROK_HOME"] = str(grok_home())
    log = STATE / "sidecar-opencode.log"
    ok, pid, err = term.spawn_terminal_opencode(bin_path, str(ROOT), env, log, pid_alive)
    real = resolve_enterable_pid(bin_path, pid if ok else 0, pid_alive)
    if real and pid_alive(real):
        usable_ok, smoke_model, usable_err = prove.prove_developer_usable(base, inspect_models)
        if not usable_ok:
            return prove.fail_not_usable(
                clear_session_reach,
                STATE, hid, usable_err or "session not usable", next_step,
                engine, status, base=base, model=smoke_model or model,
            )
        if smoke_model:
            model = smoke_model
        focused = term._focus_pid(real)
        record_sidecar_pid("opencode", real)
        write_terminal_pid(STATE, real)
        write_session_reach(STATE, reach_ok)
        if active_harness_setter:
            active_harness_setter("opencode")
        else:
            try:
                (STATE / "active-harness").write_text("opencode\n", encoding="utf-8")
            except OSError:
                pass
        record_last_verb("start opencode")
        try:
            STATE.mkdir(parents=True, exist_ok=True)
            attach_base_path.write_text(base + "\n", encoding="utf-8")
        except OSError:
            pass
        return {
            "ok": True,
            "id": hid,
            "live": "READY",
            "pid": real,
            "sidecar": True,
            "log": str(log),
            "base_url": base,
            "model": model,
            "session_reach": reach_ok,
            "focused": bool(focused),
            "copy": "attached opencode pid %s \u00b7 %s \u00b7 %s" % (real, reach_ok, engine),
            "error": "",
            "engine": engine,
            "usable": True,
            "models_ok": True,
            "smoke_ok": True,
        }
    clear_session_reach(STATE)
    try:
        if attach_base_path.is_file():
            attach_base_path.unlink()
    except OSError:
        pass
    return {
        "ok": False,
        "id": hid,
        "live": "FAIL",
        "copy": "FAIL open session -- " + (err or "terminal cannot start"),
        "error": err or "terminal cannot start",
        "session_reach": "FAIL",
        "pid": "",
        "log": str(log),
        "base_url": base,
        "model": model,
        "usable": False,
    }


# -------------------------------------------------------------------- CLI ---

def prove_cli(base, root_dir: Path | None = None) -> int:
    """CLI prove: models list + one smoke. Exit 0 only when usable."""
    next_step = NEXT_UP
    base = str(base or "").strip()
    if not base:
        print("FAIL attach -- no live local endpoint \u00b7 %s" % next_step)
        print("  equiv: ./pfy models")
        return 1
    ok, model, err = _legacy.attach_prove(root_dir).prove_developer_usable(base, inspect_models)
    if not ok:
        print("FAIL attach -- %s \u00b7 %s" % (err or "session not usable", next_step))
        print("  equiv: ./pfy models")
        return 1
    print("PASS prove \u00b7 %s \u00b7 models \u00b7 smoke" % (model or "local"))
    return 0


def run(plan: AttachPlan, base: str | None = None) -> int:
    """Prove the plan's endpoint (models + smoke); exit 0 only when usable, 1 otherwise."""
    if not plan.ok:
        print("FAIL attach -- %s \u00b7 %s" % (plan.error, plan.next_step))
        return 1
    return prove_cli(base if base is not None else plan.base_url, Path(plan.root))


def selftest(hid: str, root_dir: Path | None = None) -> int:
    """Missing binary and missing engine are FAIL+next, never ok:True (#220/#221 selftest, all harnesses)."""
    import tempfile

    prof = _require(hid, root_dir)
    root = registry.root(root_dir)
    errors = []

    def check(cond, msg):
        if not cond:
            errors.append(msg)

    deps = dict(
        ROOT=root,
        live_openai_base=lambda: ("", {"engine": "none", "status": "missing"}),
        inspect_models=lambda b: [],
        record_sidecar_pid=lambda *a: None,
        record_last_verb=lambda *a: None,
        pid_alive=lambda p: False,
    )
    with tempfile.TemporaryDirectory(prefix="pfy-%s-" % (prof["issue"] or prof["session_id"])) as tmp:
        state = Path(tmp)
        missing = open_session(hid, STATE=state, which_bin=lambda *a: "", **deps)
        check(missing.get("ok") is False, "missing bin not ok")
        check(missing.get("usable") is False, "missing bin usable false")
        check(missing.get("session_reach") == "FAIL", "missing bin reach FAIL")
        check((missing.get("error") or "") == prof["missing_error"], "missing error")
        if prof["next_install"]:
            check(prof["next_install"] in (missing.get("next_step") or ""), "missing next install")
        check(missing.get("live") == "FAIL", "missing live FAIL")

        fake = "/tmp/fake-%s-%s" % (prof["session_id"], prof["issue"] or "")
        noeng = open_session(hid, STATE=state, which_bin=lambda *a: fake, **deps)
        check(noeng.get("ok") is False, "no engine not ok")
        check(noeng.get("usable") is False, "no engine usable false")
        check("no local engine" in (noeng.get("error") or ""), "no engine error")
        check("Launch env" in (noeng.get("next_step") or ""), "no engine next")
        check(noeng.get("session_reach") == "FAIL", "no engine reach FAIL")

        plan = prepare(hid, state=state, root_dir=root_dir, env={}, base=FT_BASE)
        check(plan.ok, "prepare ok")
        check(plan.env.get("OPENAI_BASE_URL") == FT_BASE, "prepare base env")
        check(plan.env.get("PFY_ATTACH_MODE") == "bare", "prepare bare mode")

    if errors:
        print("FAIL selftest \u00b7 " + " ; ".join(errors))
        return 1
    print("PASS selftest \u00b7 Attach %s FAIL+next \u00b7 never silent stub" % prof["label"])
    return 0


def main(hid: str, argv: list[str] | None = None, prog: str = "pfylib.attach") -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["--prove"]:
        return prove_cli(args[1] if len(args) > 1 else os.environ.get("LOCAL_OPENAI_BASE_URL") or "")
    if args[:1] in (["--selftest"], ["selftest"]):
        return selftest(hid)
    if args[:1] == ["--plan"]:
        plan = prepare(hid, mode=args[1] if len(args) > 1 else None)
        print(json.dumps(plan.as_dict(), indent=2, sort_keys=True))
        return 0 if plan.ok else 1
    print("usage: %s --prove [BASE] | --selftest | --plan [MODE]" % prog, file=sys.stderr)
    return 2
