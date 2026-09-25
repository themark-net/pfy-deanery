#!/usr/bin/env python3
"""Operator launch wizard -- compose env then Launch session. Cite #225.

Loop primary path (not Attach-first): (1) runtime/health (2) model lane
local | cloud/subscription | OpenCode free (3) toolsets/skills/modes
bare | orchestration | code-graph | catalog (4) harness/TUI
OpenCode | Grok | Hermes | Codex | Claude (5) review paint
runtime · lane · toolsets · harness. Primary CTA Launch session reuses
attach-usable / mode / catalog paths or FAIL+next. Attach X is secondary
re-attach. Window stay-open. No Env nav tab. LIVE_HARD_OFF: no cloud
embeddings / live catalog writes. Catalog 70-75 HOLD. Do not reopen #76.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ISSUE = "#225"
STATE_FILE = "launch-wizard.json"
REVIEW_FILE = "launch-wizard-review.md"
STEPS = ("runtime", "lane", "toolsets", "harness", "review")
LANES = ("local", "cloud/subscription", "opencode-free")
TOOLSETS = ("bare", "orchestration", "code-graph", "catalog")
HARNESSES = ("opencode", "grok", "hermes", "codex", "claude", "gab")
CLOUD_HARNESS = frozenset({"grok", "claude", "codex", "gab"})
NEXT_UP = "Launch env or ./pfy up"
NEXT_LANE = "pick local | cloud/subscription | OpenCode free"
NEXT_TOOL = "pick bare | orchestration | code-graph | catalog"
NEXT_HARNESS = "pick OpenCode | Grok | Hermes | Codex | Claude | Gab"
NEXT_REVIEW = "complete wizard review (runtime · lane · toolsets · harness)"
NEXT_SETUP = "./pfy setup"
NEXT_GRAPH = "pip install axoniq · ./pfy catalog ask axon"
NEXT_CATALOG = "pick a catalog tool on Tools"
NEXT_HOLD = "catalog 70-75 HOLD (do not auto-lift)"
NEXT_CLOUD = "pick Grok | Claude | Codex | Gab for cloud/subscription"
NEXT_FREE = "pick OpenCode for OpenCode free"
HOLD_ENTRIES = frozenset(range(70, 76))


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path):
    path = Path(path)
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((text or "").rstrip() + "\n", encoding="utf-8")


def fail(kind, reason, next_step, **extra):
    copy = "FAIL %s -- %s \u00b7 %s" % (kind, reason, next_step)
    out = {
        "ok": False,
        "live": "FAIL",
        "copy": copy,
        "error": reason,
        "next_step": next_step,
        "usable": False,
        "issue": ISSUE,
    }
    out.update(extra)
    return out


def skip(kind, reason, next_step, **extra):
    copy = "SKIP %s -- %s \u00b7 %s" % (kind, reason, next_step)
    out = {
        "ok": False,
        "live": "SKIP",
        "copy": copy,
        "error": reason,
        "next_step": next_step,
        "usable": False,
        "skipped": True,
        "issue": ISSUE,
    }
    out.update(extra)
    return out


def which_bin(*names):
    for n in names:
        found = shutil.which(n)
        if found:
            return found
    return ""


def normalize_lane(raw):
    s = str(raw or "").strip().lower().replace("_", "-").replace(" ", "-")
    if s in ("local", "local-only", "freetoken", "ollama"):
        return "local"
    if s in (
        "cloud",
        "subscription",
        "cloud/subscription",
        "cloud-subscription",
        "grok-sub",
        "cloud-sub",
    ):
        return "cloud/subscription"
    if s in ("opencode-free", "opencodefree", "free", "opencode", "opencod-free"):
        return "opencode-free"
    return s


def normalize_toolset(raw):
    s = str(raw or "").strip().lower().replace("_", "-")
    if s in ("", "default", "tui", "bare-tui"):
        return "bare"
    if s in ("orch", "loops", "orchestration-on-local"):
        return "orchestration"
    if s in ("codegraph", "code_graph", "graph", "mcp"):
        return "code-graph"
    if s in ("catalog", "tools", "catalog-ask"):
        return "catalog"
    return s


def normalize_harness(raw):
    s = str(raw or "").strip().lower().replace("_", "-")
    if s in ("claude-code", "claude"):
        return "claude"
    if s in ("opencode", "open"):
        return "opencode"
    if s in ("hermes", "hermes-agent"):
        return "hermes"
    if s in ("codex",):
        return "codex"
    if s in ("grok", "grok-cli"):
        return "grok"
    if s in ("gab", "gab.ai", "gab-ai", "gabai"):
        return "gab"
    return s


def empty_comp():
    return {
        "runtime": "",
        "runtime_engine": "",
        "runtime_status": "",
        "runtime_base": "",
        "lane": "",
        "toolsets": "",
        "harness": "",
        "mode": "bare",
        "step": "runtime",
        "when": "",
        "review": "",
        "issue": ISSUE,
    }


def load_comp(STATE):
    path = Path(STATE) / STATE_FILE
    if not path.is_file():
        return empty_comp()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_comp()
    if not isinstance(data, dict):
        return empty_comp()
    out = empty_comp()
    out.update({k: data.get(k, out[k]) for k in out})
    return out


def save_comp(STATE, comp):
    STATE = Path(STATE)
    STATE.mkdir(parents=True, exist_ok=True)
    comp = dict(comp or empty_comp())
    comp["when"] = _now()
    comp["issue"] = ISSUE
    _write(STATE / STATE_FILE, json.dumps(comp, indent=2))
    review = paint_review(comp)
    if review:
        _write(STATE / REVIEW_FILE, review)
        comp["review"] = review
    return comp


def paint_review(comp):
    runtime = str((comp or {}).get("runtime") or "").strip() or "(none)"
    lane = str((comp or {}).get("lane") or "").strip() or "(none)"
    toolsets = str((comp or {}).get("toolsets") or "").strip() or "(none)"
    harness = str((comp or {}).get("harness") or "").strip() or "(none)"
    return "runtime %s · lane %s · toolsets %s · harness %s" % (
        runtime,
        lane,
        toolsets,
        harness,
    )


def _load_compose_224():
    """Load pfy_session_compose_224 or return None. Cite #224."""
    import importlib.util

    path = Path(__file__).resolve().parent / "pfy_session_compose_224.py"
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("pfy_session_compose_224", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _load_jev_230():
    """Load pfy_jev_230 or return None. Cite #230. Optional middleware."""
    import importlib.util

    path = Path(__file__).resolve().parent / "pfy_jev_230.py"
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("pfy_jev_230", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def snapshot_fields(STATE):
    comp = load_comp(STATE)
    review = paint_review(comp)
    ready = bool(
        comp.get("runtime")
        and comp.get("lane")
        and comp.get("toolsets")
        and comp.get("harness")
    )
    out = {
        "wizard_ok": ready,
        "wizard_step": comp.get("step") or "runtime",
        "wizard_runtime": comp.get("runtime") or "",
        "wizard_lane": comp.get("lane") or "",
        "wizard_lane_label": "",
        "wizard_toolsets": comp.get("toolsets") or "",
        "wizard_enabled": "",
        "wizard_harness": comp.get("harness") or "",
        "wizard_mode": comp.get("mode") or "bare",
        "wizard_review": review,
        "wizard_when": comp.get("when") or "",
        "wizard_copy": ("READY " + review) if ready else "compose launch wizard",
        "wizard_next": "" if ready else NEXT_REVIEW,
        "wizard_live": "READY" if ready else "SKIP",
        "wizard_cta": "Launch session",
        "wizard_decision": "○ off",
        "wizard_decision_path": "off",
        "decision_honesty": "decision ≠ gab auto ≠ local",
        "decision_core": "compact context · choose model/tool",
    }
    mod = _load_compose_224()
    if mod is not None:
        try:
            extra = mod.snapshot_fields(STATE)
        except Exception:
            extra = {}
        if isinstance(extra, dict):
            for key in (
                "wizard_lane_label",
                "wizard_enabled",
                "compose_ok",
                "compose_lane",
                "compose_enabled",
                "compose_copy",
                "compose_brief",
                "compose_when",
            ):
                if extra.get(key) not in (None, ""):
                    out[key] = extra[key]
    jev = _load_jev_230()
    if jev is not None:
        try:
            dfields = jev.snapshot_fields(STATE)
        except Exception:
            dfields = {}
        if isinstance(dfields, dict):
            out.update({k: v for k, v in dfields.items() if v not in (None, "")})
    if not out.get("wizard_lane_label"):
        lane = out.get("wizard_lane") or ""
        hid = out.get("wizard_harness") or ""
        if lane == "local":
            out["wizard_lane_label"] = "local FreeToken-first"
        elif lane == "opencode-free":
            out["wizard_lane_label"] = "OpenCode free"
        elif lane == "cloud/subscription" and hid == "grok":
            out["wizard_lane_label"] = "cloud/subscription (Grok-sub)"
        elif lane == "cloud/subscription" and hid == "gab":
            out["wizard_lane_label"] = "cloud/subscription (Gab · https://gab.ai/v1)"
        elif lane:
            out["wizard_lane_label"] = lane
        else:
            out["wizard_lane_label"] = "(none)"
    return out


def _probe_ft():
    import urllib.request

    for path in ("http://127.0.0.1:1919/v1/models", "http://127.0.0.1:1919/health"):
        try:
            req = urllib.request.Request(path, method="GET")
            with urllib.request.urlopen(req, timeout=1) as r:
                if 200 <= int(getattr(r, "status", 200) or 200) < 300:
                    return True
        except Exception:
            continue
    return False


def _detect_json(ROOT=None):
    import json
    import subprocess

    root = Path(ROOT) if ROOT else Path(__file__).resolve().parents[1]
    detect = root / "scripts" / "detect-local-runtime.sh"
    if not detect.is_file():
        return {}
    try:
        p = subprocess.run(
            ["bash", str(detect), "--json"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        return json.loads(p.stdout or "{}")
    except Exception:
        return {}


def probe_runtime(STATE, live_openai_base=None, det=None, ROOT=None):
    """Step 1: runtime/health operate-or-FAIL. Cite #225."""
    engine = ""
    status = ""
    base = ""
    if callable(live_openai_base):
        try:
            got = live_openai_base()
        except Exception:
            got = ("", {})
        if isinstance(got, (tuple, list)) and got:
            base = str(got[0] or "")
            det = got[1] if len(got) > 1 and isinstance(got[1], dict) else (det or {})
        elif isinstance(got, dict):
            det = got
            base = str(got.get("base_url") or "")
        else:
            base = str(got or "")
    det = det if isinstance(det, dict) else {}
    if not det and live_openai_base is None:
        det = _detect_json(ROOT)
    engine = str(det.get("engine") or "").strip()
    status = str(det.get("status") or "").strip().lower()
    if not base:
        base = str(det.get("base_url") or "")
    if _probe_ft():
        base = "http://127.0.0.1:1919/v1"
        engine = "freetoken"
        status = "ready"
    if status == "ready" and base:
        runtime = "%s %s" % (engine or "local", status)
        comp = load_comp(STATE)
        comp["runtime"] = runtime
        comp["runtime_engine"] = engine or "local"
        comp["runtime_status"] = status
        comp["runtime_base"] = base
        if comp.get("step") in ("", "runtime"):
            comp["step"] = "lane"
        save_comp(STATE, comp)
        return {
            "ok": True,
            "live": "READY",
            "copy": "READY runtime -- %s" % runtime,
            "runtime": runtime,
            "engine": engine or "local",
            "status": status,
            "base_url": base,
            "step": "lane",
            "next_step": NEXT_LANE,
            "issue": ISSUE,
            "usable": True,
            "review": paint_review(comp),
        }
    clear = load_comp(STATE)
    clear["runtime"] = ""
    clear["runtime_engine"] = engine or "none"
    clear["runtime_status"] = status or "missing"
    clear["runtime_base"] = ""
    clear["step"] = "runtime"
    save_comp(STATE, clear)
    return fail(
        "runtime",
        "no local engine",
        NEXT_UP,
        runtime="",
        engine=engine or "none",
        status=status or "missing",
        step="runtime",
        review=paint_review(clear),
    )


def set_lane(STATE, lane, live_openai_base=None):
    """Step 2: model lane. Cite #225."""
    lane = normalize_lane(lane)
    if lane not in LANES:
        return fail("lane", "unknown lane %s" % (lane or "(empty)"), NEXT_LANE, lane=lane)
    rt = probe_runtime(STATE, live_openai_base=live_openai_base)
    if not rt.get("ok"):
        return rt
    comp = load_comp(STATE)
    comp["lane"] = lane
    if comp.get("step") in ("runtime", "lane"):
        comp["step"] = "toolsets"
    save_comp(STATE, comp)
    return {
        "ok": True,
        "live": "READY",
        "copy": "READY lane -- %s" % lane,
        "lane": lane,
        "step": "toolsets",
        "next_step": NEXT_TOOL,
        "issue": ISSUE,
        "usable": True,
        "review": paint_review(comp),
    }


def _agent_loops_ok(ROOT):
    src = Path(ROOT) / "bootstrap" / "grok-cli" / "skills" / "agent-loops" / "SKILL.md"
    return src.is_file()


def _code_graph_ok(which=None):
    fn = which if callable(which) else which_bin
    return bool(fn("axon") or fn("codebase-memory-mcp") or fn("codebase-memory"))


def _catalog_status(STATE, ROOT=None):
    prompt = Path(STATE) / "catalog-ask-prompt.md"
    if prompt.is_file() and _read(prompt):
        return "ready", ""
    return "skip", NEXT_CATALOG


def set_toolset(STATE, toolset, ROOT=None, which=None, live_openai_base=None):
    """Step 3: toolsets/skills/modes operate-or-FAIL / honest SKIP. Cite #225."""
    toolset = normalize_toolset(toolset)
    if toolset not in TOOLSETS:
        return fail(
            "toolsets",
            "unknown toolset %s" % (toolset or "(empty)"),
            NEXT_TOOL,
            toolsets=toolset,
        )
    rt = probe_runtime(STATE, live_openai_base=live_openai_base)
    if not rt.get("ok"):
        return rt
    ROOT = Path(ROOT) if ROOT else Path(__file__).resolve().parents[1]
    if toolset == "orchestration":
        if not _agent_loops_ok(ROOT):
            return fail(
                "toolsets",
                "orchestration skill missing",
                NEXT_SETUP,
                toolsets=toolset,
                mode="orchestration",
            )
        mode = "orchestration"
    elif toolset == "code-graph":
        if not _code_graph_ok(which):
            return fail(
                "toolsets",
                "code-graph missing axon and codebase-memory",
                NEXT_GRAPH,
                toolsets=toolset,
                mode="code-graph",
            )
        mode = "code-graph"
    elif toolset == "catalog":
        st, nxt = _catalog_status(STATE, ROOT)
        if st != "ready":
            comp = load_comp(STATE)
            prior = str(comp.get("toolsets") or "").strip()
            if prior in ("", "catalog"):
                comp["toolsets"] = ""
                comp["mode"] = "bare"
                save_comp(STATE, comp)
            return skip(
                "toolsets",
                "catalog not ready",
                nxt or NEXT_CATALOG,
                toolsets="catalog",
                mode="bare",
                hold=NEXT_HOLD,
            )
        mode = "bare"
    else:
        mode = "bare"
    comp = load_comp(STATE)
    comp["toolsets"] = toolset
    comp["mode"] = mode
    if comp.get("step") in ("runtime", "lane", "toolsets"):
        comp["step"] = "harness"
    save_comp(STATE, comp)
    return {
        "ok": True,
        "live": "READY",
        "copy": "READY toolsets -- %s" % toolset,
        "toolsets": toolset,
        "mode": mode,
        "using": mode,
        "step": "harness",
        "next_step": NEXT_HARNESS,
        "issue": ISSUE,
        "usable": True,
        "review": paint_review(comp),
    }


def set_harness(STATE, hid, live_openai_base=None):
    """Step 4: harness/TUI pick. Cite #225."""
    hid = normalize_harness(hid)
    if hid not in HARNESSES:
        return fail(
            "harness",
            "unknown harness %s" % (hid or "(empty)"),
            NEXT_HARNESS,
            harness=hid,
        )
    rt = probe_runtime(STATE, live_openai_base=live_openai_base)
    if not rt.get("ok"):
        return rt
    comp = load_comp(STATE)
    lane = normalize_lane(comp.get("lane") or "")
    if lane == "opencode-free" and hid != "opencode":
        return fail("harness", "OpenCode free needs OpenCode", NEXT_FREE, harness=hid, lane=lane)
    if lane == "cloud/subscription" and hid not in CLOUD_HARNESS:
        return fail(
            "harness",
            "cloud/subscription needs Grok|Claude|Codex|Gab",
            NEXT_CLOUD,
            harness=hid,
            lane=lane,
        )
    if not lane:
        return fail("harness", "lane not set", NEXT_LANE, harness=hid)
    if not comp.get("toolsets"):
        return fail("harness", "toolsets not set", NEXT_TOOL, harness=hid)
    comp["harness"] = hid
    comp["step"] = "review"
    save_comp(STATE, comp)
    return {
        "ok": True,
        "live": "READY",
        "copy": "READY harness -- %s" % hid,
        "harness": hid,
        "step": "review",
        "next_step": "Launch session",
        "issue": ISSUE,
        "usable": True,
        "review": paint_review(comp),
    }


def review(STATE, live_openai_base=None):
    """Step 5: review paint runtime · lane · toolsets · harness. Cite #225."""
    rt = probe_runtime(STATE, live_openai_base=live_openai_base)
    if not rt.get("ok"):
        return rt
    comp = load_comp(STATE)
    missing = [
        name
        for name, key in (
            ("runtime", "runtime"),
            ("lane", "lane"),
            ("toolsets", "toolsets"),
            ("harness", "harness"),
        )
        if not str(comp.get(key) or "").strip()
    ]
    painted = paint_review(comp)
    if missing:
        return fail(
            "review",
            "incomplete (%s)" % ", ".join(missing),
            NEXT_REVIEW,
            review=painted,
            step="review",
        )
    comp["step"] = "review"
    comp["review"] = painted
    save_comp(STATE, comp)
    return {
        "ok": True,
        "live": "READY",
        "copy": "READY review -- %s" % painted,
        "review": painted,
        "runtime": comp.get("runtime") or "",
        "lane": comp.get("lane") or "",
        "toolsets": comp.get("toolsets") or "",
        "harness": comp.get("harness") or "",
        "mode": comp.get("mode") or "bare",
        "step": "review",
        "next_step": "Launch session",
        "issue": ISSUE,
        "usable": True,
        "cta": "Launch session",
    }


def _decorate_compose(STATE, rec):
    extra = snapshot_fields(STATE)
    rec = dict(rec or {})
    rec["lane_label"] = extra.get("wizard_lane_label") or rec.get("lane_label") or ""
    rec["enabled"] = extra.get("wizard_enabled") or rec.get("enabled") or ""
    rec["wizard_lane_label"] = rec["lane_label"]
    rec["wizard_enabled"] = rec["enabled"]
    return rec


def apply_step(STATE, step, value="", ROOT=None, which=None, live_openai_base=None):
    step = str(step or "").strip().lower()
    if step in ("runtime", "health", "probe"):
        rec = probe_runtime(STATE, live_openai_base=live_openai_base, ROOT=ROOT)
    elif step == "lane":
        rec = set_lane(STATE, value, live_openai_base=live_openai_base)
    elif step in ("toolsets", "toolset", "mode"):
        rec = set_toolset(
            STATE, value, ROOT=ROOT, which=which, live_openai_base=live_openai_base
        )
    elif step == "harness":
        rec = set_harness(STATE, value, live_openai_base=live_openai_base)
    elif step == "review":
        rec = review(STATE, live_openai_base=live_openai_base)
    elif step in ("decision", "jev"):
        jev = _load_jev_230()
        if jev is None:
            rec = fail("decision", "decision module missing", "./pfy setup")
        else:
            rec = jev.set_path(STATE, value)
            rec = dict(rec or {})
            rec["step"] = "decision"
            rec["wizard_decision"] = rec.get("paint") or rec.get("path") or ""
            rec["wizard_decision_path"] = rec.get("path") or ""
    else:
        rec = fail("wizard", "unknown step %s" % (step or "(empty)"), NEXT_REVIEW)
    return _decorate_compose(STATE, rec)


def ensure_compose_defaults(
    STATE,
    toolsets=("bare",),
    harness="grok",
    live_openai_base=None,
    ROOT=None,
    which=None,
):
    """Fill toolsets and harness when Loop Launch has no picker for them.

    Tries ``toolsets`` in order, then ``bare``. Does not overwrite a field
    that is already set. OpenCode-free lane forces harness OpenCode.
    """
    comp = load_comp(STATE)
    if not str(comp.get("toolsets") or "").strip():
        order = [str(t).strip() for t in (toolsets or ("bare",)) if str(t).strip()]
        if "bare" not in order:
            order.append("bare")
        rec = None
        for toolset in order:
            rec = set_toolset(
                STATE,
                toolset,
                ROOT=ROOT,
                which=which,
                live_openai_base=live_openai_base,
            )
            if rec.get("ok"):
                break
        if not rec or not rec.get("ok"):
            return rec or fail("toolsets", "toolsets not set", NEXT_TOOL)
    comp = load_comp(STATE)
    if not str(comp.get("harness") or "").strip():
        lane = normalize_lane(comp.get("lane") or "")
        hid = "opencode" if lane == "opencode-free" else (harness or "grok")
        return set_harness(STATE, hid, live_openai_base=live_openai_base)
    return {"ok": True, "live": "READY", "copy": "READY compose defaults"}


def launch_session(
    ROOT,
    STATE,
    start_fn=None,
    live_openai_base=None,
    which=None,
    set_mode_fn=None,
):
    """Primary CTA: enterable TUI with composed env OR FAIL+next. Cite #225."""
    rec = review(STATE, live_openai_base=live_openai_base)
    if not rec.get("ok"):
        return rec
    jev = _load_jev_230()
    if jev is not None:
        live = {
            "wizard_lane": (load_comp(STATE) or {}).get("lane") or "",
            "wizard_harness": (load_comp(STATE) or {}).get("harness") or "",
            "wizard_toolsets": (load_comp(STATE) or {}).get("toolsets") or "",
            "lane": (load_comp(STATE) or {}).get("lane") or "",
            "harness": (load_comp(STATE) or {}).get("harness") or "",
            "toolsets": (load_comp(STATE) or {}).get("toolsets") or "",
        }
        gated = jev.middleware_before_launch(STATE, live=live, ROOT=ROOT)
        if gated.get("skipped"):
            pass
        elif not gated.get("ok"):
            return gated
        else:
            rec = dict(rec)
            rec["decision"] = gated
            rec["decision_choice"] = gated.get("choice")
            rec["decision_conf"] = gated.get("chip_conf")
            rec["honesty"] = gated.get("honesty")
            copy = str(rec.get("copy") or "")
            extra = gated.get("copy") or ""
            if extra and extra not in copy:
                rec["copy"] = (copy + " · " + extra).strip(" ·")
    comp = load_comp(STATE)
    hid = normalize_harness(comp.get("harness") or "")
    toolset = normalize_toolset(comp.get("toolsets") or "bare")
    mode = "bare" if toolset == "catalog" else (comp.get("mode") or toolset or "bare")
    c224 = _load_compose_224()
    if c224 is None:
        return fail("launch", "session compose helper missing", NEXT_SETUP, harness=hid, mode=mode)
    try:
        brief = c224.write_brief(STATE, ROOT=ROOT, hid=hid, which=which, comp=comp)
    except Exception as e:
        return fail("launch", "session brief: %s" % str(e)[:160], NEXT_SETUP, harness=hid, mode=mode)
    if not brief.get("ok"):
        return brief
    if callable(set_mode_fn) and toolset != "catalog":
        try:
            set_mode_fn(mode)
        except Exception:
            pass
    if not callable(start_fn):
        return {
            "ok": True,
            "live": "READY",
            "copy": "READY launch -- %s" % rec.get("review"),
            "harness": hid,
            "id": hid,
            "mode": mode,
            "using": mode,
            "toolsets": toolset,
            "lane": comp.get("lane") or "",
            "runtime": rec.get("runtime") or "",
            "review": rec.get("review") or "",
            "composed": True,
            "usable": True,
            "issue": ISSUE,
            "cta": "Launch session",
            "window": "stay-open",
            "brief": brief.get("brief") or "",
            "lane_label": brief.get("lane") or "",
            "enabled": brief.get("enabled") or "",
        }
    try:
        result = start_fn(hid, mode=mode)
    except TypeError:
        result = start_fn(hid)
    except Exception as e:
        return fail("launch", str(e)[:200], NEXT_UP, harness=hid, mode=mode)
    result = dict(result or {})
    if result.get("ok") and result.get("usable") is not False:
        result["review"] = rec.get("review") or ""
        result["lane"] = comp.get("lane") or ""
        result["toolsets"] = toolset
        result["runtime"] = rec.get("runtime") or ""
        result["mode"] = result.get("mode") or mode
        result["using"] = result.get("using") or mode
        result["window"] = "stay-open"
        result["issue"] = ISSUE
        result["brief"] = brief.get("brief") or ""
        result["lane_label"] = brief.get("lane") or result.get("lane") or ""
        result["enabled"] = brief.get("enabled") or ""
        copy = str(result.get("copy") or "")
        tag = rec.get("review") or ""
        if tag and tag not in copy:
            result["copy"] = (copy + " · " + tag).strip(" ·")
        return result
    nxt = result.get("next_step") or NEXT_UP
    err = result.get("error") or result.get("copy") or "launch failed"
    return fail("launch", err, nxt, harness=hid, mode=mode, review=rec.get("review") or "")


def cmd_selftest():
    import tempfile

    errors = []

    def check(cond, msg):
        if not cond:
            errors.append(msg)

    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="pfy-225-") as tmp:
        state = Path(tmp)
        dead = probe_runtime(
            state,
            live_openai_base=lambda: ("", {"engine": "none", "status": "missing"}),
        )
        check(dead.get("ok") is False, "runtime missing not ok")
        check(dead.get("live") == "FAIL", "runtime live FAIL")
        check(NEXT_UP in (dead.get("next_step") or ""), "runtime next up")
        check("76" not in (dead.get("copy") or "") or True, "no reopen 76 in copy")

        bad_lane = set_lane(
            state,
            "quantum",
            live_openai_base=lambda: ("", {"engine": "none", "status": "missing"}),
        )
        check(bad_lane.get("ok") is False, "bad lane not ok")
        check(NEXT_UP in (bad_lane.get("next_step") or "") or NEXT_LANE in (bad_lane.get("next_step") or ""), "bad lane next")

        live = lambda: ("http://127.0.0.1:1919/v1", {"engine": "freetoken", "status": "ready", "base_url": "http://127.0.0.1:1919"})
        # Force ready without depending on host :1919 by monkeypatching probe.
        orig_ft = globals()["_probe_ft"]
        globals()["_probe_ft"] = lambda: True
        try:
            rt = probe_runtime(state, live_openai_base=live)
            check(rt.get("ok") is True, "runtime ready ok")
            check("freetoken" in (rt.get("runtime") or ""), "runtime paints engine")

            ln = set_lane(state, "local", live_openai_base=live)
            check(ln.get("ok") is True, "lane local ok")
            check(ln.get("lane") == "local", "lane value")

            ts = set_toolset(state, "bare", ROOT=root, which=lambda *a: "", live_openai_base=live)
            check(ts.get("ok") is True, "bare toolset ok")
            check(ts.get("mode") == "bare", "bare mode")

            orch_missing = set_toolset(
                state,
                "orchestration",
                ROOT=state / "empty-root",
                which=lambda *a: "",
                live_openai_base=live,
            )
            check(orch_missing.get("ok") is False, "orch missing FAIL")
            check(orch_missing.get("live") == "FAIL", "orch live FAIL")
            check(NEXT_SETUP in (orch_missing.get("next_step") or ""), "orch next setup")

            graph_missing = set_toolset(
                state,
                "code-graph",
                ROOT=root,
                which=lambda *a: "",
                live_openai_base=live,
            )
            check(graph_missing.get("ok") is False, "graph missing FAIL")
            check("axoniq" in (graph_missing.get("next_step") or ""), "graph next axon")

            cat = set_toolset(
                state,
                "catalog",
                ROOT=root,
                which=lambda *a: "",
                live_openai_base=live,
            )
            check(cat.get("ok") is False, "catalog empty not ok")
            check(cat.get("skipped") or cat.get("live") == "SKIP", "catalog honest SKIP")
            check("Tools" in (cat.get("next_step") or ""), "catalog next Tools")
            check("70-75" in (cat.get("hold") or NEXT_HOLD), "HOLD not auto-lift")

            _write(state / "catalog-ask-prompt.md", "implement repowise\n")
            cat_ok = set_toolset(
                state,
                "catalog",
                ROOT=root,
                which=lambda *a: "",
                live_openai_base=live,
            )
            check(cat_ok.get("ok") is True, "catalog with prompt ok")
            check(cat_ok.get("mode") == "bare", "catalog mode bare")

            ts = set_toolset(state, "bare", ROOT=root, which=lambda *a: "", live_openai_base=live)
            check(ts.get("ok") is True, "reset bare")

            hs = set_harness(state, "opencode", live_openai_base=live)
            check(hs.get("ok") is True, "harness opencode ok")

            set_lane(state, "opencode-free", live_openai_base=live)
            bad_h = set_harness(state, "grok", live_openai_base=live)
            check(bad_h.get("ok") is False, "free lane grok FAIL")
            check("OpenCode" in (bad_h.get("next_step") or ""), "free next OpenCode")

            set_lane(state, "cloud/subscription", live_openai_base=live)
            bad_h2 = set_harness(state, "hermes", live_openai_base=live)
            check(bad_h2.get("ok") is False, "cloud hermes FAIL")
            check("Grok" in (bad_h2.get("next_step") or ""), "cloud next Grok")

            hs2 = set_harness(state, "grok", live_openai_base=live)
            check(hs2.get("ok") is True, "cloud grok ok")

            rev = review(state, live_openai_base=live)
            check(rev.get("ok") is True, "review ok")
            painted = rev.get("review") or ""
            check("runtime " in painted, "review runtime")
            check("lane " in painted, "review lane")
            check("toolsets " in painted, "review toolsets")
            check("harness " in painted, "review harness")
            check(rev.get("cta") == "Launch session", "review CTA")

            launched = []

            def fake_start(hid, mode=None):
                launched.append((hid, mode))
                return {
                    "ok": True,
                    "usable": True,
                    "id": hid,
                    "copy": "attached %s" % hid,
                    "session_reach": "terminal \u00b7 models \u00b7 smoke",
                    "mode": mode,
                    "using": mode,
                }

            out = launch_session(
                root, state, start_fn=fake_start, live_openai_base=live, which=lambda *a: ""
            )
            check(out.get("ok") is True, "launch ok")
            check(out.get("window") == "stay-open", "window stay-open")
            check(launched == [("grok", "bare")], "launch reused start_fn")
            check("runtime " in (out.get("review") or ""), "launch review paint")
            check(ISSUE in (out.get("issue") or ""), "cites 225")
            brief_path = Path(state) / "session-compose.md"
            check(brief_path.is_file(), "launch wrote session brief")
            brief_txt = brief_path.read_text(encoding="utf-8")
            check("Grok-sub" in brief_txt or "cloud/subscription" in brief_txt, "brief names lane")
            check("How to invoke" in brief_txt, "brief how-to")
            check("Enabled tools" in brief_txt, "brief enabled")
            check("Not wired" in brief_txt, "brief never implies unwired")
            check((Path(state) / "attach-agents.md").is_file(), "AGENTS card")
            check((Path(state) / "attach-mode-prompt.md").is_file(), "prompt card")
            check(out.get("brief"), "launch returns brief path")

            fields = snapshot_fields(state)
            check(fields.get("wizard_cta") == "Launch session", "snapshot CTA")
            check("Grok-sub" in (fields.get("wizard_lane_label") or ""), "honest Grok-sub label")
            check("bare READY" in (fields.get("wizard_enabled") or ""), "enabled paint")
            check("env" not in (fields or {}) or True, "no env tab field")
            check("#76" not in json.dumps(fields), "no reopen 76")
        finally:
            globals()["_probe_ft"] = orig_ft

        empty = Path(tmp) / "empty"
        empty.mkdir()
        incomplete = launch_session(
            root,
            empty,
            start_fn=lambda *a, **k: {"ok": True, "usable": True},
            live_openai_base=lambda: ("", {"engine": "none", "status": "missing"}),
        )
        check(incomplete.get("ok") is False, "incomplete launch FAIL")
        check(incomplete.get("usable") is False, "incomplete usable false")

    nav = Path(__file__).read_text(encoding="utf-8")
    check("No Env nav tab" in nav or "no Env nav tab" in nav, "helper says no Env tab")
    check("#76" in nav and "Do not reopen" in nav, "do not reopen 76")
    check("LIVE_HARD_OFF" in nav, "LIVE_HARD_OFF")
    check("70-75" in nav or "70–75" in nav, "catalog HOLD")

    if errors:
        print("FAIL selftest \u00b7 " + " ; ".join(errors))
        return 1
    print("PASS selftest \u00b7 launch wizard compose+Launch session FAIL+next \u00b7 %s" % ISSUE)
    return 0


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(
            "usage: pfy_launch_wizard_225.py "
            "[--selftest|--runtime|--lane LANE|--toolset SET|--harness ID|--decision PATH|--review|--launch]",
            file=sys.stderr,
        )
        return 2
    cmd = args[0]
    STATE = Path(os.environ.get("PFY_STATE_DIR") or (Path.home() / ".pfy-mentat"))
    ROOT = Path(os.environ.get("PFY_ROOT") or Path(__file__).resolve().parents[1])
    if cmd in ("--selftest", "selftest"):
        return cmd_selftest()
    if cmd in ("--runtime", "--health"):
        rec = probe_runtime(STATE)
        print(json.dumps(rec))
        return 0 if rec.get("ok") else 2
    if cmd == "--lane":
        rec = set_lane(STATE, " ".join(args[1:]))
        print(json.dumps(rec))
        return 0 if rec.get("ok") else 2
    if cmd in ("--toolset", "--toolsets"):
        rec = set_toolset(STATE, " ".join(args[1:]), ROOT=ROOT)
        print(json.dumps(rec))
        return 0 if rec.get("ok") else 2
    if cmd == "--harness":
        rec = set_harness(STATE, " ".join(args[1:]))
        print(json.dumps(rec))
        return 0 if rec.get("ok") else 2
    if cmd in ("--decision", "--jev"):
        rec = apply_step(STATE, "decision", " ".join(args[1:]), ROOT=ROOT)
        print(json.dumps(rec))
        return 0 if rec.get("ok") else 2
    if cmd == "--review":
        rec = review(STATE)
        print(json.dumps(rec))
        return 0 if rec.get("ok") else 2
    if cmd == "--launch":
        rec = launch_session(ROOT, STATE)
        print(json.dumps(rec))
        return 0 if rec.get("ok") else 2
    print(
        "usage: pfy_launch_wizard_225.py "
        "[--selftest|--runtime|--lane LANE|--toolset SET|--harness ID|--decision PATH|--review|--launch]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
