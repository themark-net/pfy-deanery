#!/usr/bin/env python3
"""Session compose -- honest lane + enabled tools + in-TUI how-to. Cite #224.

Deepens the #225 launch wizard: Loop/pre-launch paint names the model lane
(local FreeToken-first vs cloud/subscription Grok-sub vs OpenCode free) and
which toolsets are actually enabled. Unwired = honest SKIP/FAIL, never implied.
On Launch, write an in-session brief (AGENTS / skills / prompt card) into STATE
so the harness can invoke only what it received. LIVE_HARD_OFF. Catalog 70-75
HOLD. Do not reopen #76. Do not re-merge #226.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ISSUE = "#224"
BRIEF_FILE = "session-compose.md"
CARD_FILE = "session-compose-prompt.md"
WHEN_FILE = "session-compose-when"
HANDOFF_FILE = "attach-mode-handoff.md"
AGENTS_FILE = "attach-agents.md"
PROMPT_FILE = "attach-mode-prompt.md"
WIZARD_FILE = "launch-wizard.json"
TOOLS_FILE = "tools.json"
SKILL_IDS = ("one-shot", "investigate", "agent-loops", "hermes-feedback")
LANES = ("local", "cloud/subscription", "opencode-free")
TOOLSETS = ("bare", "orchestration", "code-graph", "catalog")
HARNESSES = ("opencode", "grok", "hermes", "codex", "claude", "gab")
CLOUD_HARNESS = frozenset({"grok", "claude", "codex", "gab"})
NEXT_UP = "Launch env or ./pfy up"
NEXT_SETUP = "./pfy setup"
NEXT_GRAPH = "pip install axoniq · ./pfy catalog ask axon"
NEXT_CATALOG = "pick a catalog tool on Tools"
NEXT_HOLD = "catalog 70-75 HOLD (do not auto-lift)"
NEXT_OC = "npm install -g @aicontextlab/cli"
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
        if n == "codebase-memory-mcp":
            home = os.environ.get("HOME") or str(Path.home())
            root = os.environ.get("PFY_TOOL_CACHE") or str(Path(home) / ".cache" / "pfy")
            cached = Path(root) / "bin" / n
            if cached.is_file() and os.access(cached, os.X_OK):
                return str(cached)
    return ""


def normalize_lane(raw):
    s = str(raw or "").strip().lower().replace("_", "-").replace(" ", "-")
    if s in ("local", "local-only", "freetoken", "ollama", "local-freetoken-first"):
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


def lane_label(lane, harness=""):
    """Honest lane paint. Never call OpenCode-free Grok-sub or vice versa."""
    lane = normalize_lane(lane)
    hid = normalize_harness(harness)
    if lane == "local":
        return "local FreeToken-first"
    if lane == "opencode-free":
        return "OpenCode free"
    if lane == "cloud/subscription":
        if hid == "grok":
            return "cloud/subscription (Grok-sub)"
        if hid == "claude":
            return "cloud/subscription (Claude-sub)"
        if hid == "codex":
            return "cloud/subscription (Codex-sub)"
        if hid == "gab":
            return "cloud/subscription (Gab · https://gab.ai/v1)"
        return "cloud/subscription"
    return lane or "(none)"


def harness_lane_note(lane, hid):
    lane = normalize_lane(lane)
    hid = normalize_harness(hid)
    if lane == "local":
        return (
            "Lane is **local FreeToken-first** (`LOCAL_OPENAI_BASE_URL` / "
            "`OPENAI_BASE_URL`). This is not Grok-sub and not OpenCode free."
        )
    if lane == "opencode-free":
        return (
            "Lane is **OpenCode free** (free models in the OpenCode TUI). "
            "Do not claim Grok-sub or a cloud subscription."
        )
    if lane == "cloud/subscription":
        if hid == "grok":
            return (
                "Lane is **cloud/subscription (Grok-sub)**. Grok uses the "
                "subscription model. Do not label this OpenCode free. Local "
                "FreeToken-first is a different lane."
            )
        if hid == "claude":
            return (
                "Lane is **cloud/subscription (Claude-sub)**. Not Grok-sub, "
                "not OpenCode free."
            )
        if hid == "codex":
            return (
                "Lane is **cloud/subscription (Codex-sub)**. Not Grok-sub, "
                "not OpenCode free."
            )
        if hid == "gab":
            return (
                "Lane is **cloud/subscription (Gab)**. Endpoint "
                "`https://gab.ai/v1`, model=auto (cloud router) or pin-by-id. "
                "gab auto ≠ local ranking; Gab does not host GGUF — we pull "
                "open-weight families to Ollama. Key: GAB_API_KEY / Plus. "
                "Docs: https://gab.ai/docs/api-auth"
            )
        return "Lane is **cloud/subscription**. Pick Grok | Claude | Codex | Gab."
    return "Lane not set."


def _agent_loops_ok(ROOT):
    src = Path(ROOT) / "bootstrap" / "grok-cli" / "skills" / "agent-loops" / "SKILL.md"
    return src.is_file()


def _skill_ok(ROOT, sid):
    src = Path(ROOT) / "bootstrap" / "grok-cli" / "skills" / sid / "SKILL.md"
    return src.is_file()


def _code_graph_probe(which=None):
    fn = which if callable(which) else which_bin
    axon = fn("axon")
    mcp = fn("codebase-memory-mcp") or fn("codebase-memory")
    if axon:
        return {
            "id": "code-graph",
            "live": "READY",
            "wired": True,
            "path": "axon",
            "copy": "code-graph READY (axon)",
            "how": "axon analyze . --no-embeddings · axon serve --watch",
            "next": "",
        }
    if mcp:
        return {
            "id": "code-graph",
            "live": "READY",
            "wired": True,
            "path": "codebase-memory",
            "copy": "code-graph READY (codebase-memory, not axon)",
            "how": "codebase-memory MCP (do not claim Axon)",
            "next": "pip install axoniq · ./pfy catalog ask axon",
        }
    return {
        "id": "code-graph",
        "live": "FAIL",
        "wired": False,
        "path": "",
        "copy": "code-graph FAIL -- missing axon and codebase-memory",
        "how": "",
        "next": NEXT_GRAPH,
    }


def _catalog_probe(STATE):
    prompt = Path(STATE) / "catalog-ask-prompt.md"
    if prompt.is_file() and _read(prompt):
        return {
            "id": "catalog",
            "live": "READY",
            "wired": True,
            "copy": "catalog READY (prompt on disk; HOLD 70-75 not auto-lifted)",
            "how": "read PFY_CATALOG_ASK_PROMPT; do not auto-lift catalog 70-75",
            "next": "",
            "hold": NEXT_HOLD,
        }
    return {
        "id": "catalog",
        "live": "SKIP",
        "wired": False,
        "copy": "catalog SKIP -- not ready",
        "how": "",
        "next": NEXT_CATALOG,
        "hold": NEXT_HOLD,
    }


def _opencontext_probe(which=None):
    fn = which if callable(which) else which_bin
    oc = fn("oc")
    if oc:
        return {
            "id": "opencontext",
            "live": "READY",
            "wired": True,
            "copy": "opencontext READY (oc)",
            "how": "./pfy context · oc CLI (not oc ui)",
            "next": "",
        }
    return {
        "id": "opencontext",
        "live": "SKIP",
        "wired": False,
        "copy": "opencontext SKIP -- oc not on PATH",
        "how": "",
        "next": NEXT_OC,
    }


def _load_tools_state(STATE, ROOT):
    base = {sid: _skill_ok(ROOT, sid) for sid in SKILL_IDS}
    path = Path(STATE) / TOOLS_FILE
    if not path.is_file():
        return {"skills": base, "mcp": False, "write_guard": False, "tools_mode": "split"}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"skills": base, "mcp": False, "write_guard": False, "tools_mode": "split"}
    if not isinstance(raw, dict):
        return {"skills": base, "mcp": False, "write_guard": False, "tools_mode": "split"}
    sk = raw.get("skills") if isinstance(raw.get("skills"), dict) else {}
    skills = dict(base)
    for sid in SKILL_IDS:
        if sid in sk:
            skills[sid] = bool(sk[sid]) and _skill_ok(ROOT, sid)
    return {
        "skills": skills,
        "mcp": bool(raw.get("mcp")),
        "write_guard": bool(raw.get("write_guard")),
        "tools_mode": str(raw.get("tools_mode") or "split"),
    }


def load_wizard(STATE):
    path = Path(STATE) / WIZARD_FILE
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def probe_toolsets(STATE, ROOT=None, which=None):
    """Honest READY/SKIP/FAIL for each toolset. Never imply unwired tools."""
    ROOT = Path(ROOT) if ROOT else Path(__file__).resolve().parents[1]
    STATE = Path(STATE)
    items = []
    items.append(
        {
            "id": "bare",
            "live": "READY",
            "wired": True,
            "copy": "bare READY",
            "how": "bare TUI on LOCAL_OPENAI_BASE_URL / OPENAI_BASE_URL",
            "next": "",
        }
    )
    if _agent_loops_ok(ROOT):
        items.append(
            {
                "id": "orchestration",
                "live": "READY",
                "wired": True,
                "copy": "orchestration READY",
                "how": "/agent-loops (write the eight exits before the loop)",
                "next": "",
            }
        )
    else:
        items.append(
            {
                "id": "orchestration",
                "live": "FAIL",
                "wired": False,
                "copy": "orchestration FAIL -- skill missing",
                "how": "",
                "next": NEXT_SETUP,
            }
        )
    items.append(_code_graph_probe(which))
    items.append(_catalog_probe(STATE))
    extras = [_opencontext_probe(which)]
    tools = _load_tools_state(STATE, ROOT)
    skill_rows = []
    for sid in SKILL_IDS:
        on = bool((tools.get("skills") or {}).get(sid))
        if on:
            skill_rows.append(
                {
                    "id": sid,
                    "live": "READY",
                    "wired": True,
                    "copy": "%s READY" % sid,
                    "how": invoke_skill(sid, ""),
                    "next": "",
                }
            )
        else:
            skill_rows.append(
                {
                    "id": sid,
                    "live": "SKIP",
                    "wired": False,
                    "copy": "%s SKIP -- off or skill missing" % sid,
                    "how": "",
                    "next": "toggle %s on Tools" % sid,
                }
            )
    return {
        "toolsets": items,
        "extras": extras,
        "skills": skill_rows,
        "mcp": bool(tools.get("mcp")),
        "write_guard": bool(tools.get("write_guard")),
        "tools_mode": tools.get("tools_mode") or "split",
    }


def invoke_skill(sid, hid):
    hid = normalize_harness(hid)
    slash = "/%s" % sid
    if hid == "grok":
        return "Grok slash %s (GROK_HOME/skills)" % slash
    if hid == "opencode":
        return "OpenCode skill %s (OPENCODE_SKILLS)" % sid
    if hid == "hermes":
        return "Hermes skill %s (attach-skills)" % sid
    if hid == "codex":
        return "Codex: read PFY_ATTACH_AGENTS; skill %s if present" % sid
    if hid == "claude":
        return "Claude: read PFY_ATTACH_AGENTS; skill %s if present" % sid
    return "skill %s" % sid


def invoke_harness(hid, lane):
    hid = normalize_harness(hid)
    lane = normalize_lane(lane)
    if hid == "grok":
        return (
            "Harness is **Grok** (Grok-sub when lane is cloud/subscription). "
            "Slash skills in the Grok TUI (`/agent-loops` only if orchestration "
            "READY). Read `$PFY_ATTACH_AGENTS` and `$PFY_SESSION_BRIEF`. "
            "Do not rewrite repo AGENTS.md."
        )
    if hid == "opencode":
        extra = (
            " OpenCode-free lane uses free models only — not Grok-sub."
            if lane == "opencode-free"
            else ""
        )
        return (
            "Harness is **OpenCode**. Skills from `$OPENCODE_SKILLS`. "
            "Read `$PFY_ATTACH_AGENTS` / `$PFY_SESSION_BRIEF`.%s" % extra
        )
    if hid == "hermes":
        return (
            "Harness is **Hermes**. Skills from attach-skills. "
            "Read `$PFY_ATTACH_AGENTS`. Not Grok-sub unless the lane says so."
        )
    if hid == "codex":
        return (
            "Harness is **Codex**. Read `$PFY_ATTACH_AGENTS` (prompt card). "
            "Do not rewrite repo AGENTS.md. Not Grok-sub, not OpenCode free."
        )
    if hid == "claude":
        return (
            "Harness is **Claude**. Read `$PFY_ATTACH_AGENTS` (prompt card). "
            "Do not rewrite repo AGENTS.md. Not Grok-sub, not OpenCode free."
        )
    return "Harness not set — pick OpenCode | Grok | Hermes | Codex | Claude."


def paint_enabled(probe, selected=""):
    selected = normalize_toolset(selected) if selected else ""
    parts = []
    for row in (probe or {}).get("toolsets") or []:
        mark = " [selected]" if selected and row.get("id") == selected else ""
        live = str(row.get("live") or "SKIP")
        ident = row.get("id") or ""
        if row.get("wired"):
            extra = ""
            if ident == "code-graph" and row.get("path") == "codebase-memory":
                extra = " (not axon)"
            parts.append("%s %s%s%s" % (ident, live, extra, mark))
        else:
            nxt = row.get("next") or ""
            bit = "%s %s%s" % (ident, live, mark)
            if nxt:
                bit += " · %s" % nxt
            parts.append(bit)
    return " · ".join(parts) if parts else "(none)"


def selected_toolset_status(probe, selected):
    selected = normalize_toolset(selected) if selected else ""
    for row in (probe or {}).get("toolsets") or []:
        if row.get("id") == selected:
            return row
    return None


def snapshot_fields(STATE, ROOT=None, which=None):
    """Loop/pre-launch paint. Honest lane + enabled toolsets. Cite #224."""
    ROOT = Path(ROOT) if ROOT else Path(__file__).resolve().parents[1]
    STATE = Path(STATE)
    comp = load_wizard(STATE)
    probe = probe_toolsets(STATE, ROOT=ROOT, which=which)
    lane = normalize_lane(comp.get("lane") or "")
    hid = normalize_harness(comp.get("harness") or "")
    selected = normalize_toolset(comp.get("toolsets") or "") if comp.get("toolsets") else ""
    label = lane_label(lane, hid) if lane else "(none)"
    enabled = paint_enabled(probe, selected)
    sel = selected_toolset_status(probe, selected) if selected else None
    sel_live = (sel or {}).get("live") or ""
    ready = bool(lane and selected and hid)
    copy = (
        "READY %s · %s" % (label, enabled)
        if ready
        else "compose session (lane + toolsets + harness)"
    )
    return {
        "wizard_lane_label": label,
        "wizard_enabled": enabled,
        "compose_ok": ready,
        "compose_lane": label,
        "compose_lane_key": lane,
        "compose_enabled": enabled,
        "compose_selected": selected,
        "compose_selected_live": sel_live,
        "compose_harness": hid,
        "compose_copy": copy,
        "compose_brief": str(STATE / BRIEF_FILE) if (STATE / BRIEF_FILE).is_file() else "",
        "compose_when": _read(STATE / WHEN_FILE) or str(comp.get("when") or ""),
        "compose_cta": "Launch session",
        "issue": ISSUE,
    }


def _enabled_lines(probe, hid, selected=""):
    lines = []
    selected = normalize_toolset(selected) if selected else ""
    for row in (probe or {}).get("toolsets") or []:
        if not row.get("wired"):
            continue
        mark = " (this launch)" if selected and row.get("id") == selected else ""
        how = row.get("how") or ""
        if row.get("id") == "orchestration":
            how = invoke_skill("agent-loops", hid)
        lines.append("- **%s**%s — %s" % (row.get("id"), mark, how))
    for row in (probe or {}).get("skills") or []:
        if not row.get("wired"):
            continue
        if row.get("id") == "agent-loops" and selected == "orchestration":
            continue
        lines.append("- **%s** — %s" % (row.get("id"), invoke_skill(row.get("id"), hid)))
    for row in (probe or {}).get("extras") or []:
        if row.get("wired"):
            lines.append("- **%s** — %s" % (row.get("id"), row.get("how") or "oc CLI"))
    if (probe or {}).get("mcp"):
        lines.append("- **mcp** — codebase-memory in harness config (only if merged)")
    if (probe or {}).get("write_guard"):
        lines.append("- **write-guard** — write-guard MCP (only if merged)")
    if not lines:
        lines.append("- (none wired — bare TUI only if runtime READY)")
    return lines


def _not_wired_lines(probe):
    lines = []
    for group in ("toolsets", "extras", "skills"):
        for row in (probe or {}).get(group) or []:
            if row.get("wired"):
                continue
            nxt = row.get("next") or ""
            live = row.get("live") or "SKIP"
            bit = "- **%s** %s" % (row.get("id"), live)
            if nxt:
                bit += " — %s" % nxt
            if row.get("id") == "catalog":
                bit += " — %s" % NEXT_HOLD
            lines.append(bit)
    if not (probe or {}).get("mcp"):
        lines.append("- **mcp** SKIP — not toggled (do not claim MCP)")
    if not (probe or {}).get("write_guard"):
        lines.append("- **write-guard** SKIP — not toggled")
    return lines


def brief_text(comp, probe, hid=""):
    hid = normalize_harness(hid or (comp or {}).get("harness") or "")
    lane = normalize_lane((comp or {}).get("lane") or "")
    selected = normalize_toolset((comp or {}).get("toolsets") or "") if (comp or {}).get("toolsets") else ""
    runtime = str((comp or {}).get("runtime") or "").strip() or "(none)"
    base = str((comp or {}).get("runtime_base") or "").strip()
    label = lane_label(lane, hid)
    lines = [
        "# Session compose (%s)" % ISSUE,
        "",
        "In-session brief. Only tools listed under **Enabled** are wired.",
        "Do not imply the rest. LIVE_HARD_OFF: no cloud embeddings / live catalog writes.",
        "Catalog 70-75 HOLD. Do not reopen #76.",
        "",
        "## Lane",
        "",
        "- **%s**" % label,
        "- %s" % harness_lane_note(lane, hid),
        "- Runtime: %s%s" % (runtime, (" @ %s" % base) if base else ""),
        "- Harness: %s" % (hid or "(none)"),
        "",
        "## Enabled tools",
        "",
    ]
    lines.extend(_enabled_lines(probe, hid, selected))
    lines.extend(["", "## Not wired (do not claim)", ""])
    lines.extend(_not_wired_lines(probe))
    lines.extend(
        [
            "",
            "## How to invoke in this harness",
            "",
            invoke_harness(hid, lane),
            "",
            "Prompt card: `$PFY_ATTACH_PROMPT` / `$PFY_SESSION_PROMPT`.",
            "AGENTS fragment: `$PFY_ATTACH_AGENTS` (does not rewrite repo AGENTS.md).",
            "Handoff: `$PFY_ATTACH_HANDOFF` / `$PFY_SESSION_BRIEF`.",
            "",
        ]
    )
    if selected == "catalog":
        lines.append("Catalog prompt: `$PFY_CATALOG_ASK_PROMPT`. HOLD 70-75 is not auto-lifted.")
        lines.append("")
    if selected == "code-graph":
        row = selected_toolset_status(probe, "code-graph") or {}
        if row.get("path") == "axon":
            lines.append("Code-graph path=axon. `axon analyze` / `axon serve --watch`.")
        elif row.get("path") == "codebase-memory":
            lines.append("Code-graph path=codebase-memory (not axon). Do not claim Axon.")
        else:
            lines.append("Code-graph is not wired. Do not claim Axon.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def prompt_card(comp, probe, hid=""):
    hid = normalize_harness(hid or (comp or {}).get("harness") or "")
    lane = normalize_lane((comp or {}).get("lane") or "")
    selected = normalize_toolset((comp or {}).get("toolsets") or "") if (comp or {}).get("toolsets") else ""
    label = lane_label(lane, hid)
    enabled = []
    for row in (probe or {}).get("toolsets") or []:
        if row.get("wired"):
            enabled.append(row.get("id"))
    for row in (probe or {}).get("skills") or []:
        if row.get("wired") and row.get("id") not in enabled:
            enabled.append(row.get("id"))
    for row in (probe or {}).get("extras") or []:
        if row.get("wired"):
            enabled.append(row.get("id"))
    names = ", ".join(enabled) if enabled else "(none wired)"
    return (
        "PFY session compose %s. Lane: %s. Harness: %s. "
        "Enabled: %s. Selected toolset: %s. "
        "Read $PFY_SESSION_BRIEF. Do not claim unwired tools. "
        "LIVE_HARD_OFF. Catalog 70-75 HOLD.\n"
        % (ISSUE, label, hid or "(none)", names, selected or "(none)")
    )


def write_brief(STATE, ROOT=None, hid="", which=None, comp=None):
    """Write AGENTS / prompt card / handoff into STATE. Cite #224."""
    ROOT = Path(ROOT) if ROOT else Path(__file__).resolve().parents[1]
    STATE = Path(STATE)
    STATE.mkdir(parents=True, exist_ok=True)
    comp = dict(comp or load_wizard(STATE))
    hid = normalize_harness(hid or comp.get("harness") or "")
    probe = probe_toolsets(STATE, ROOT=ROOT, which=which)
    selected = normalize_toolset(comp.get("toolsets") or "") if comp.get("toolsets") else ""
    if selected:
        row = selected_toolset_status(probe, selected)
        if row is not None and not row.get("wired"):
            live = str(row.get("live") or "FAIL")
            nxt = row.get("next") or NEXT_SETUP
            if live == "SKIP":
                rec = skip("compose", row.get("copy") or "toolset not wired", nxt, toolsets=selected)
            else:
                rec = fail("compose", row.get("copy") or "toolset not wired", nxt, toolsets=selected)
            rec["lane"] = lane_label(comp.get("lane") or "", hid)
            rec["enabled"] = paint_enabled(probe, selected)
            return rec
    text = brief_text(comp, probe, hid)
    card = prompt_card(comp, probe, hid)
    when = _now()
    _write(STATE / BRIEF_FILE, text)
    _write(STATE / CARD_FILE, card)
    _write(STATE / WHEN_FILE, when)
    # Also land on the #208 paths so Launch without prepare still has a card.
    existing_h = _read(STATE / HANDOFF_FILE)
    existing_a = _read(STATE / AGENTS_FILE)
    existing_p = _read(STATE / PROMPT_FILE)
    if text not in existing_h:
        _write(STATE / HANDOFF_FILE, ((existing_h + "\n\n") if existing_h else "") + text)
    if text not in existing_a:
        _write(STATE / AGENTS_FILE, ((existing_a + "\n\n") if existing_a else "") + text)
    if card not in existing_p:
        _write(STATE / PROMPT_FILE, ((existing_p + "\n") if existing_p else "") + card)
    return {
        "ok": True,
        "live": "READY",
        "copy": "READY session compose -- %s" % lane_label(comp.get("lane") or "", hid),
        "brief": str(STATE / BRIEF_FILE),
        "card": str(STATE / CARD_FILE),
        "handoff": str(STATE / HANDOFF_FILE),
        "agents": str(STATE / AGENTS_FILE),
        "prompt": str(STATE / PROMPT_FILE),
        "lane": lane_label(comp.get("lane") or "", hid),
        "enabled": paint_enabled(probe, selected),
        "harness": hid,
        "when": when,
        "usable": True,
        "issue": ISSUE,
    }


def merge_into_handoff(STATE, handoff, prompt):
    """Append compose brief into #208 AGENTS/prompt files. Cite #224."""
    STATE = Path(STATE)
    brief = _read(STATE / BRIEF_FILE)
    card = _read(STATE / CARD_FILE)
    if brief and brief not in (handoff or ""):
        handoff = (handoff or "").rstrip() + "\n\n" + brief
    if card and card not in (prompt or ""):
        prompt = (prompt or "").rstrip() + "\n" + card
    return handoff, prompt, handoff


def apply_child_env(env, STATE=None):
    """Point the child at the session brief. Cite #224."""
    env = env if env is not None else {}
    if STATE is None:
        STATE = os.environ.get("PFY_STATE_DIR") or str(Path.home() / ".pfy-mentat")
    STATE = Path(STATE)
    brief = STATE / BRIEF_FILE
    card = STATE / CARD_FILE
    if brief.is_file():
        env["PFY_SESSION_BRIEF"] = str(brief)
        env.setdefault("PFY_ATTACH_HANDOFF", str(STATE / HANDOFF_FILE if (STATE / HANDOFF_FILE).is_file() else brief))
        env.setdefault("PFY_ATTACH_AGENTS", str(STATE / AGENTS_FILE if (STATE / AGENTS_FILE).is_file() else brief))
    if card.is_file():
        env["PFY_SESSION_PROMPT"] = str(card)
        env.setdefault("PFY_ATTACH_PROMPT", str(STATE / PROMPT_FILE if (STATE / PROMPT_FILE).is_file() else card))
    return env


def cmd_selftest():
    import tempfile

    errors = []

    def check(cond, msg):
        if not cond:
            errors.append(msg)

    root = Path(__file__).resolve().parents[1]
    check(lane_label("local") == "local FreeToken-first", "local label")
    check(lane_label("opencode-free") == "OpenCode free", "opencode-free label")
    check(lane_label("cloud/subscription", "grok") == "cloud/subscription (Grok-sub)", "grok-sub label")
    check("Grok-sub" not in lane_label("opencode-free", "grok"), "free lane not grok-sub")
    check("OpenCode free" not in lane_label("local", "opencode"), "local not opencode-free")
    check("Grok-sub" not in lane_label("cloud/subscription", "claude"), "claude not grok-sub")

    with tempfile.TemporaryDirectory(prefix="pfy-224-") as tmp:
        state = Path(tmp)
        empty_root = state / "empty-root"
        empty_root.mkdir()
        probe = probe_toolsets(state, ROOT=empty_root, which=lambda *a: "")
        ids = {r["id"]: r for r in probe["toolsets"]}
        check(ids["bare"].get("wired") is True, "bare wired")
        check(ids["orchestration"].get("wired") is False, "orch unwired empty root")
        check(ids["orchestration"].get("live") == "FAIL", "orch FAIL")
        check(ids["code-graph"].get("wired") is False, "graph unwired")
        check(ids["code-graph"].get("live") == "FAIL", "graph FAIL")
        check("axon" not in (ids["code-graph"].get("how") or ""), "no axon how when missing")
        check(ids["catalog"].get("live") == "SKIP", "catalog SKIP")
        check(NEXT_HOLD in (ids["catalog"].get("hold") or ""), "HOLD not auto-lift")
        oc = {r["id"]: r for r in probe["extras"]}["opencontext"]
        check(oc.get("wired") is False, "oc SKIP when missing")
        check("READY" not in oc.get("copy"), "oc not implied")

        painted = paint_enabled(probe, "bare")
        check("bare READY" in painted, "paint bare")
        check("orchestration FAIL" in painted, "paint orch FAIL")
        check("code-graph FAIL" in painted, "paint graph FAIL")
        check("catalog SKIP" in painted, "paint catalog SKIP")
        check("[selected]" in painted, "selected mark")

        probe_g = probe_toolsets(
            state, ROOT=empty_root, which=lambda *n: "/tmp/cm" if n and n[0] == "codebase-memory-mcp" else ""
        )
        g = {r["id"]: r for r in probe_g["toolsets"]}["code-graph"]
        check(g.get("path") == "codebase-memory", "mcp path not axon")
        check("not axon" in (g.get("copy") or ""), "honest not axon")

        probe_a = probe_toolsets(
            state, ROOT=empty_root, which=lambda *n: "/tmp/axon" if n and n[0] == "axon" else ""
        )
        a = {r["id"]: r for r in probe_a["toolsets"]}["code-graph"]
        check(a.get("path") == "axon", "axon path")

        orch_ok = probe_toolsets(state, ROOT=root, which=lambda *a: "")
        o = {r["id"]: r for r in orch_ok["toolsets"]}["orchestration"]
        check(o.get("wired") is True, "orch wired in-repo skill")

        _write(
            state / WIZARD_FILE,
            json.dumps(
                {
                    "runtime": "freetoken ready",
                    "runtime_base": "http://127.0.0.1:1919/v1",
                    "lane": "local",
                    "toolsets": "bare",
                    "harness": "grok",
                    "mode": "bare",
                }
            ),
        )
        snap = snapshot_fields(state, ROOT=root, which=lambda *a: "")
        check(snap.get("wizard_lane_label") == "local FreeToken-first", "snap local label")
        check("bare READY" in (snap.get("wizard_enabled") or ""), "snap enabled")
        check("#76" not in json.dumps(snap), "no reopen 76")
        check(snap.get("issue") == ISSUE, "snap cites 224")

        rec = write_brief(state, ROOT=root, hid="grok", which=lambda *a: "")
        check(rec.get("ok") is True, "write brief ok")
        brief = _read(state / BRIEF_FILE)
        check("local FreeToken-first" in brief, "brief lane")
        check("Grok" in brief, "brief harness")
        check("Enabled tools" in brief, "brief enabled section")
        check("Not wired" in brief, "brief not-wired")
        check("How to invoke" in brief, "brief how-to")
        check("LIVE_HARD_OFF" in brief, "brief live hard off")
        check("70-75" in brief, "brief HOLD")
        check("#76" in brief and "Do not reopen" in brief, "brief no 76")
        check("oc ui" not in brief.lower() or "not oc ui" in brief, "no oc ui claim")
        # Unwired axon must not be instructed as live.
        check("Live path: **Axon**" not in brief, "no live axon claim")
        check(_read(state / CARD_FILE), "prompt card")
        check("local FreeToken-first" in _read(state / HANDOFF_FILE), "handoff got brief")
        check("local FreeToken-first" in _read(state / AGENTS_FILE), "agents got brief")
        check("PFY session compose" in _read(state / PROMPT_FILE), "prompt card landed")
        env = apply_child_env({}, state)
        check(env.get("PFY_SESSION_BRIEF"), "child env brief")
        check(env.get("PFY_SESSION_PROMPT"), "child env prompt")

        h, p, a = merge_into_handoff(state, "# Attach mode: bare (#208)\n", "PFY_ATTACH_MODE=bare.\n")
        check("Session compose" in h, "merge handoff")
        check("PFY session compose" in p, "merge prompt")
        check("Session compose" in a, "merge agents")

        spec_path = Path(__file__).resolve().parent / "pfy_attach_mode_208.py"
        if spec_path.is_file():
            import importlib.util as _ilu
            spec = _ilu.spec_from_file_location("pfy_attach_mode_208_224", spec_path)
            m208 = _ilu.module_from_spec(spec)
            spec.loader.exec_module(m208)
            m208.prepare(root, state, "opencode", mode="bare")
            check("Session compose" in _read(state / HANDOFF_FILE), "208 prepare keeps compose")
            check("PFY session compose" in _read(state / PROMPT_FILE), "208 prepare keeps card")
            env2 = m208.apply_child_env({}, state)
            check(env2.get("PFY_SESSION_BRIEF"), "208 child env session brief")

        _write(
            state / WIZARD_FILE,
            json.dumps(
                {
                    "runtime": "freetoken ready",
                    "lane": "opencode-free",
                    "toolsets": "code-graph",
                    "harness": "opencode",
                    "mode": "code-graph",
                }
            ),
        )
        bad = write_brief(state, ROOT=empty_root, hid="opencode", which=lambda *a: "")
        check(bad.get("ok") is False, "unwired selected FAIL/SKIP")
        check(bad.get("usable") is False, "unwired not usable")
        check("Grok-sub" not in (bad.get("lane") or ""), "free not grok-sub on fail")

        _write(
            state / WIZARD_FILE,
            json.dumps(
                {
                    "runtime": "freetoken ready",
                    "lane": "cloud/subscription",
                    "toolsets": "bare",
                    "harness": "grok",
                    "mode": "bare",
                }
            ),
        )
        rec2 = write_brief(state, ROOT=root, hid="grok", which=lambda *a: "")
        check("Grok-sub" in (rec2.get("lane") or ""), "cloud grok-sub")
        check("OpenCode free" not in _read(state / BRIEF_FILE).split("Lane")[1].split("Enabled")[0], "cloud not free")

    src = Path(__file__).read_text(encoding="utf-8")
    check("Do not reopen #76" in src, "no reopen 76")
    check("LIVE_HARD_OFF" in src, "LIVE_HARD_OFF")
    check("70-75" in src, "catalog HOLD")
    check("#226" in src and "re-merge" in src, "do not re-merge 226")
    check(ISSUE == "#224", "cites 224")

    if errors:
        print("FAIL selftest \u00b7 " + " ; ".join(errors))
        return 1
    print("PASS selftest \u00b7 session compose lane+enabled+brief \u00b7 %s" % ISSUE)
    return 0


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(
            "usage: pfy_session_compose_224.py [--selftest|--paint|--brief]",
            file=sys.stderr,
        )
        return 2
    cmd = args[0]
    STATE = Path(os.environ.get("PFY_STATE_DIR") or (Path.home() / ".pfy-mentat"))
    ROOT = Path(os.environ.get("PFY_ROOT") or Path(__file__).resolve().parents[1])
    if cmd in ("--selftest", "selftest"):
        return cmd_selftest()
    if cmd in ("--paint", "--snapshot"):
        rec = snapshot_fields(STATE, ROOT=ROOT)
        print(json.dumps(rec))
        return 0
    if cmd in ("--brief", "--write"):
        rec = write_brief(STATE, ROOT=ROOT)
        print(json.dumps(rec))
        return 0 if rec.get("ok") else 2
    print(
        "usage: pfy_session_compose_224.py [--selftest|--paint|--brief]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
