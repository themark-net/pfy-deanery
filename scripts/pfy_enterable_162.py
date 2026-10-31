#!/usr/bin/env python3
"""Enterable OpenCode session helpers — cite #162."""
from __future__ import annotations

import importlib.util
from pathlib import Path

def _load_b():
    path = Path(__file__).resolve().parent / "pfy_enterable_162_b.py"
    spec = importlib.util.spec_from_file_location("pfy_enterable_162_b", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_b = _load_b()
SESSION_REACH_OK = _b.SESSION_REACH_OK
SESSION_FILE = _b.SESSION_FILE
read_session_reach = _b.read_session_reach
write_session_reach = _b.write_session_reach
clear_session_reach = _b.clear_session_reach
spawn_terminal_opencode = _b.spawn_terminal_opencode
open_enterable_opencode_session = _b.open_enterable_opencode_session
read_terminal_pid = _b.read_terminal_pid

def arm_launch_env_session(res, open_fn) -> dict:
    """After Launch env: open/arm enterable session OR honest SKIP. Cite #162.

    Copy endpoint/status alone does not satisfy #162.
    """
    out = dict(res or {})
    live = str(out.get("live") or "")
    next_steps = list(out.get("next_steps") or [])
    # Strip any prior enterable markers
    next_steps = [s for s in next_steps if (s or {}).get("id") not in ("enterable", "session")]
    if not out.get("ok"):
        out["session_reach"] = "FAIL"
        out["enterable"] = False
        out["next_steps"] = next_steps
        return out
    if live == "SKIP":
        # Env itself skipped — honest about enterable too
        reason = "SKIP enterable session · env skipped"
        next_steps.append({"id": "enterable", "label": reason, "value": reason})
        what = str(out.get("what") or "")
        if "enterable" not in what.lower():
            out["what"] = (what + " · " + reason).strip(" ·")
        out["session_reach"] = "SKIP"
        out["enterable"] = False
        out["next_steps"] = next_steps
        return out
    # Try to open/arm enterable OpenCode session
    try:
        sess = open_fn() if callable(open_fn) else {}
    except Exception as e:
        sess = {"ok": False, "error": str(e)[:300], "session_reach": "FAIL"}
    if sess.get("ok") and sess.get("session_reach"):
        reach = sess.get("session_reach") or SESSION_REACH_OK
        next_steps.insert(0, {
            "id": "enterable",
            "label": "session " + reach,
            "value": reach,
        })
        what = str(out.get("what") or "")
        bit = "session " + reach
        if bit not in what:
            out["what"] = (what + " · " + bit).strip(" ·")
        out["session_reach"] = reach
        out["enterable"] = True
        out["session_pid"] = sess.get("pid") or ""
        out["next_steps"] = next_steps
        # Keep env copy; append session reach
        copy = str(out.get("copy") or "PASS env")
        if "session" not in copy.lower():
            out["copy"] = copy + " · " + bit
        return out
    # Honest SKIP — cannot open enterable surface
    err = str(sess.get("error") or sess.get("copy") or "terminal cannot start")[:200]
    reason = "SKIP enterable session · " + err
    next_steps.append({"id": "enterable", "label": reason, "value": reason})
    what = str(out.get("what") or "")
    if "enterable" not in what.lower() and "session" not in what.lower():
        out["what"] = (what + " · " + reason).strip(" ·")
    out["session_reach"] = "SKIP"
    out["enterable"] = False
    out["next_steps"] = next_steps
    # Downgrade PASS env narrative? Keep env PASS/SKIP but make enterable SKIP explicit.
    copy = str(out.get("copy") or "")
    if copy.startswith("PASS"):
        out["copy"] = copy + " · " + reason
    return out



def live_session_reach(STATE, pid_alive=None) -> str:
    """Return session reach only if enterable terminal pid is still alive. Cite #162."""
    reach = read_session_reach(STATE)
    if not reach or reach in ("FAIL", "SKIP"):
        return reach if reach in ("FAIL", "SKIP") else ""
    try:
        from pathlib import Path as P
        import importlib.util
        path = P(__file__).resolve().parent / "pfy_enterable_162_a.py"
        spec = importlib.util.spec_from_file_location("pfy_enterable_162_a_live", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        pid = mod.read_terminal_pid(STATE)
        alive = False
        if pid and callable(pid_alive):
            alive = bool(pid_alive(pid))
        elif pid:
            import os
            try:
                os.kill(int(pid), 0)
                alive = True
            except OSError:
                alive = False
        if not alive:
            clear_session_reach(STATE)
            return ""
        return reach
    except Exception:
        return ""
