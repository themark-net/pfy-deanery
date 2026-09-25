"""Loop paint: toolsets for one agent + live local/cloud hedge (ADR-0017).

The operator window's front door shows:

  * where work runs (local compute vs cloud credits)
  * which agent receives the toolsets (grok, OpenCode, Hermes, Codex, Claude, Gab)
  * each toolset's status for that agent (wired / partial / not wired)

Launch session writes the enabled toolsets into the selected agent.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import hedge, registry, toolsets

MODULES_FILE = "loop-modules.json"
TASKS = hedge.TASKS
WIZARD_MODE = {
    "orchestration": "orchestration",
    "code-graph": "code-graph",
    "catalog-ask": "catalog",
}
TASK_HELP = {
    "bulk": "Cheap bulk work. Stays on this machine when local is ON.",
    "interactive": "Normal work. Local first; cloud only if local is down and budget remains.",
    "hard": "Hard review. May spend a cloud credit even if local is up.",
}
AGENTS = (
    ("grok", "grok"),
    ("opencode", "OpenCode"),
    ("hermes", "Hermes"),
    ("codex", "Codex"),
    ("claude", "Claude"),
    ("gab", "Gab"),
)
_AGENT_IDS = frozenset(a[0] for a in AGENTS)
_IMPL_KEY = {"claude": "claude-code"}


def story(hedge_frag: dict) -> dict:
    """Plain-language Loop copy so the window can say what is happening."""
    h = hedge_frag or {}
    local_ready = bool(h.get("local_ready"))
    engine = str(h.get("local_engine") or "none")
    lane = str(h.get("lane") or "")
    rem = h.get("remaining") or 0
    profile = str(h.get("profile") or "(unset)")
    cloud_on = lane == "cloud" or (rem > 0 and profile != "local-only")
    if lane == "cloud":
        cloud_lane = "SPENDING"
        cloud_meaning = "This session is using a cloud credit."
    elif cloud_on:
        cloud_lane = "STANDBY"
        cloud_meaning = "Credits remain. Cloud stays idle unless work is hard or local is down."
    else:
        cloud_lane = "OFF"
        cloud_meaning = "No cloud budget. Set PFY_CLOUD_BUDGET to allow paid work."
    if local_ready:
        local_meaning = "A model is answering on this machine. Cheap work stays here."
    else:
        local_meaning = "No local model is up. Click Launch env (or ./pfy up) before a local session."
    nxt = str(h.get("next_step") or "").strip()
    if not h.get("ok"):
        route = "Not ready to run a session."
        nxt = nxt or "Launch env or set PFY_CLOUD_BUDGET."
    elif lane == "local":
        extra = " (%s)" % engine if engine and engine != "none" else ""
        route = "This session will run on your machine%s." % extra
    elif lane == "cloud":
        route = "This session will spend one cloud credit."
    else:
        route = str(h.get("copy") or "").strip() or "Lane not chosen yet."
    return {
        "local_meaning": local_meaning,
        "cloud_meaning": cloud_meaning,
        "cloud_lane": cloud_lane,
        "route": route,
        "next_step": nxt,
        "task_help": TASK_HELP.get(str(h.get("task") or "interactive"), TASK_HELP["interactive"]),
    }


def _state(state: Path | None) -> Path:
    return registry.state_dir(state)


def modules_path(state: Path | None = None) -> Path:
    return _state(state) / MODULES_FILE


def normalize_agent(raw: str) -> str:
    s = str(raw or "").strip().lower().replace("_", "-")
    if s in ("claude-code",):
        return "claude"
    if s in ("open",):
        return "opencode"
    return s if s in _AGENT_IDS else "grok"


def load_selection(state: Path | None = None) -> dict:
    path = modules_path(state)
    empty = {"enabled": [], "task": "interactive", "agent": "grok"}
    if not path.is_file():
        return empty
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty
    if not isinstance(data, dict):
        return empty
    enabled = [str(x) for x in (data.get("enabled") or []) if str(x).strip()]
    task = str(data.get("task") or "interactive").strip().lower()
    if task not in TASKS:
        task = "interactive"
    return {"enabled": enabled, "task": task, "agent": normalize_agent(data.get("agent"))}


def save_selection(sel: dict, state: Path | None = None) -> Path:
    path = modules_path(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "enabled": list(sel.get("enabled") or []),
        "task": sel.get("task") or "interactive",
        "agent": normalize_agent(sel.get("agent")),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _best_status(impl: dict) -> str:
    """Harness-agnostic: implemented if any cell is, else partial, else stub."""
    cells = [str((c or {}).get("status") or "stub") for c in impl.values()]
    if "implemented" in cells:
        return "implemented"
    if "partial" in cells:
        return "partial"
    return "stub"


def paint_word(status: str, stub: bool = False) -> str:
    if stub or status == "stub":
        return "not wired"
    if status == "implemented":
        return "wired"
    return status or "not wired"


def agent_cell(impl: dict, agent: str) -> dict:
    """Status of one toolset for one agent. Missing cell is not wired."""
    key = _IMPL_KEY.get(agent, agent)
    cell = (impl or {}).get(key) or {}
    status = str(cell.get("status") or "stub")
    how = str(cell.get("how") or "")
    stub = (not cell) or status == "stub"
    if stub and not how:
        how = "not wired for this agent"
    return {"status": status, "how": how, "stub": stub, "paint": paint_word(status, stub)}


def _module_row(t: dict, enabled: set[str], agent: str = "grok") -> dict:
    tid = str(t.get("id") or "")
    impl = t.get("implementation") or {}
    status = _best_status(impl)
    how = next((str((c or {}).get("how") or "") for c in impl.values() if (c or {}).get("how")), "")
    cell = agent_cell(impl, agent)
    return {
        "id": tid,
        "title": str(t.get("title") or tid),
        "status": status,
        "how": how,
        "lanes": list(t.get("lanes") or []),
        "catalog_tool": t.get("catalog_tool"),
        "enabled": tid in enabled,
        "stub": status == "stub",
        "wizard_mode": WIZARD_MODE.get(tid),
        "agent_status": cell["status"],
        "agent_how": cell["how"],
        "agent_stub": cell["stub"],
        "agent_paint": cell["paint"],
    }


def plan_line(agent: str, modules: list) -> tuple[str, bool]:
    """Button sentence and whether Launch may run."""
    label = dict(AGENTS).get(agent, agent)
    blockers = [m for m in modules if m.get("enabled") and m.get("agent_stub")]
    ready = [str(m.get("id") or "") for m in modules if m.get("enabled") and not m.get("agent_stub")]
    if blockers:
        b = blockers[0]
        how = str(b.get("agent_how") or "not wired for this agent")
        return ("%s is not wired for %s. %s" % (b.get("id") or "toolset", label, how), False)
    if not ready:
        return ("Open %s with no toolsets yet" % label, False)
    return ("Open %s with %s" % (label, ", ".join(ready)), True)


def toggle(tid: str, on: bool, *, state: Path | None = None, root_dir: Path | None = None) -> dict:
    """Enable/disable a module. Stub modules cannot be enabled."""
    t = registry.toolset(tid, root_dir)
    if t is None:
        return {
            "ok": False, "live": "FAIL", "id": tid,
            "error": "unknown module %r" % tid,
            "next_step": "pick one of: %s" % ", ".join(registry.toolset_ids(root_dir)),
            "copy": "FAIL module -- unknown %s" % tid,
        }
    sel = load_selection(state)
    cell = agent_cell(t.get("implementation") or {}, sel["agent"])
    status = cell["status"]
    if on and cell["stub"]:
        return {
            "ok": False, "live": "STUB", "id": tid, "status": status,
            "agent": sel["agent"],
            "error": "toolset %s is not wired for %s" % (tid, sel["agent"]),
            "next_step": cell["how"],
            "copy": "STUB %s for %s — %s" % (tid, sel["agent"], cell["how"]),
        }
    have = [x for x in sel["enabled"] if x != tid]
    if on:
        have.append(tid)
    sel["enabled"] = have
    save_selection(sel, state)
    return {
        "ok": True, "live": "READY", "id": tid, "on": on, "status": status,
        "enabled": have, "task": sel["task"],
        "wizard_mode": WIZARD_MODE.get(tid) if on else None,
        "agent": sel["agent"],
        "copy": "READY toolset %s %s for %s" % (tid, "on" if on else "off", sel["agent"]),
    }


def set_task(task: str, *, state: Path | None = None) -> dict:
    task = str(task or "").strip().lower()
    if task not in TASKS:
        return {
            "ok": False, "live": "FAIL", "error": "unknown task %r" % task,
            "next_step": "use %s" % "|".join(TASKS),
            "copy": "FAIL task -- use %s" % "|".join(TASKS),
        }
    sel = load_selection(state)
    sel["task"] = task
    save_selection(sel, state)
    return {"ok": True, "live": "READY", "task": task, "enabled": sel["enabled"], "agent": sel["agent"], "copy": "READY task %s" % task}


def set_agent(agent: str, *, state: Path | None = None) -> dict:
    raw = str(agent or "").strip().lower().replace("_", "-")
    if raw == "claude-code":
        raw = "claude"
    elif raw == "open":
        raw = "opencode"
    if raw not in _AGENT_IDS:
        return {
            "ok": False, "live": "FAIL", "error": "unknown agent %r" % (agent or ""),
            "next_step": "use %s" % "|".join(a[0] for a in AGENTS),
            "copy": "FAIL agent -- use %s" % "|".join(a[0] for a in AGENTS),
        }
    sel = load_selection(state)
    sel["agent"] = raw
    save_selection(sel, state)
    return {"ok": True, "live": "READY", "agent": raw, "enabled": sel["enabled"], "copy": "READY agent %s" % raw}


def fields(
    *,
    state: Path | None = None,
    root_dir: Path | None = None,
    local: dict | None = None,
) -> dict:
    """Snapshot fragment for Loop: modules + hedge for the selected task class."""
    sel = load_selection(state)
    enabled = set(sel["enabled"])
    agent = sel["agent"]
    modules = [_module_row(t, enabled, agent) for t in registry.toolset_rows(root_dir)]
    plan, launch_ready = plan_line(agent, modules)
    # Reuse one detector pass for all three task classes so the split is comparable.
    local = dict(local) if local is not None else hedge.detect_local(root_dir)
    routes = {task: hedge.decide(task, local=local, state=state, root_dir=root_dir) for task in TASKS}
    chosen = routes[sel["task"]]
    local_ok = str(local.get("status") or "").lower() == "ready"
    gab_key = bool(str(os.environ.get("GAB_API_KEY") or "").strip())
    hedge_frag = {
        "task": sel["task"],
        "lane": chosen.get("lane"),
        "ok": bool(chosen.get("ok")),
        "live": chosen.get("live") or "FAIL",
        "reason": chosen.get("reason") or chosen.get("copy") or "",
        "next_step": chosen.get("next_step") or "",
        "copy": chosen.get("copy") or "",
        "local_engine": chosen.get("local_engine") or local.get("engine") or "none",
        "local_status": chosen.get("local_status") or local.get("status") or "missing",
        "local_base_url": chosen.get("local_base_url") or local.get("base_url") or "",
        "local_ready": local_ok,
        "budget": chosen.get("budget", 0),
        "spent": chosen.get("spent", 0),
        "remaining": chosen.get("remaining", 0),
        "cost": chosen.get("cost", 1),
        "profile": chosen.get("profile") or "(unset)",
        "gab_key": gab_key,
        "routes": {
            t: {"lane": r.get("lane"), "ok": bool(r.get("ok")), "reason": r.get("reason") or ""}
            for t, r in routes.items()
        },
    }
    hedge_frag.update(story(hedge_frag))
    return {
        "modules": modules,
        "modules_enabled": list(sel["enabled"]),
        "modules_task": sel["task"],
        "modules_agent": agent,
        "agents": [{"id": i, "label": lab} for i, lab in AGENTS],
        "plan": plan,
        "launch_ready": launch_ready,
        "task_help": TASK_HELP,
        "hedge": hedge_frag,
    }


def apply_enabled(*, hid: str, state: Path | None = None, root_dir: Path | None = None, yes: bool = True) -> list[dict]:
    """Apply each enabled module onto ``hid`` using the hedge-chosen lane. Honest FAIL/STUB kept."""
    sel = load_selection(state)
    local = hedge.detect_local(root_dir)
    out = []
    for tid in sel["enabled"]:
        t = registry.toolset(tid, root_dir)
        if t is None:
            out.append({"toolset": tid, "live": "FAIL", "copy": "unknown module"})
            continue
        lanes = list(t.get("lanes") or ["local"])
        if "cloud" in lanes and "local" not in lanes:
            lane = "cloud"
        else:
            rec = hedge.decide("interactive" if "local" in lanes else "hard", local=local, state=state, root_dir=root_dir)
            lane = rec.get("lane") if rec.get("ok") else (lanes[0] if lanes else "local")
            if lane not in lanes:
                lane = lanes[0]
        p = toolsets.plan(tid, hid, lane, root_dir=root_dir, state=state)
        if p.get("ok") and yes:
            p = toolsets.apply(p, yes=True, state=state, root_dir=root_dir)
        out.append({"toolset": tid, "harness": hid, "lane": lane, "live": p.get("live"), "copy": p.get("copy"), "ok": p.get("ok")})
    return out
