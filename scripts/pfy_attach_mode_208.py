#!/usr/bin/env python3
"""Attach mode select + handoff -- cite #208.

Modes: bare | orchestration | code-graph.
One mode at a time. Painted Attach must operate-or-FAIL.
Unwired mode = FAIL+next (never a silent bare session claiming that mode).
LIVE_HARD_OFF: no cloud embeddings / live catalog writes.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MODES = ("bare", "orchestration", "code-graph")
DEFAULT_MODE = "bare"
MODE_FILE = "attach-mode"
MODE_WHEN_FILE = "attach-mode-when"
MODE_LIVE_FILE = "attach-mode-live"
HANDOFF_FILE = "attach-mode-handoff.md"
PROMPT_FILE = "attach-mode-prompt.md"
AGENTS_FILE = "attach-agents.md"
ENV_FILE = "attach-mode.env"
ATTACH_BASES = (
    "opencode-attach-base",
    "hermes-attach-base",
    "grok-attach-base",
    "codex-attach-base",
    "claude-attach-base",
)
NEXT_SELECT = "select bare | orchestration | code-graph on Attach"
NEXT_SETUP = "./pfy setup"
NEXT_MCP = "./bootstrap/grok-cli/install.sh --with-codebase-memory"
NEXT_HERMES_GRAPH = "pip install axoniq · Attach grok or opencode for code-graph MCP"
NEXT_GRAPH = "pip install axoniq · ./pfy catalog ask axon"


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_mode(raw):
    s = str(raw or "").strip().lower().replace("_", "-")
    if s in ("", "default", "tui", "bare-tui"):
        return DEFAULT_MODE
    if s in ("orch", "loops", "orchestration-on-local"):
        return "orchestration"
    if s in ("codegraph", "code_graph", "graph", "mcp"):
        return "code-graph"
    return s


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


def fail(hid, reason, next_step, mode=""):
    copy = "FAIL mode -- %s \u00b7 %s" % (reason, next_step)
    return {
        "ok": False,
        "id": hid or "",
        "live": "FAIL",
        "copy": copy,
        "error": reason,
        "session_reach": "FAIL",
        "usable": False,
        "next_step": next_step,
        "mode": mode,
        "using": mode or "(none)",
    }


def _read(path):
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((text or "").rstrip() + "\n", encoding="utf-8")


def current_mode(STATE):
    raw = _read(Path(STATE) / MODE_FILE)
    mode = normalize_mode(raw)
    if mode in MODES:
        return mode
    return DEFAULT_MODE


def live_mode(STATE):
    raw = normalize_mode(_read(Path(STATE) / MODE_LIVE_FILE))
    return raw if raw in MODES else ""


def snapshot_fields(STATE):
    STATE = Path(STATE)
    mode = current_mode(STATE)
    return {
        "attach_mode": mode,
        "using": mode,
        "attach_mode_when": _read(STATE / MODE_WHEN_FILE),
        "attach_mode_live": live_mode(STATE),
    }


def set_mode(STATE, mode):
    """Persist one selected mode. Replaces any previous selection. Cite #208."""
    STATE = Path(STATE)
    mode = normalize_mode(mode)
    if mode not in MODES:
        return fail("", "unknown mode %s" % (mode or "(empty)"), NEXT_SELECT, mode=mode)
    prev = current_mode(STATE)
    when = _now()
    _write(STATE / MODE_FILE, mode)
    _write(STATE / MODE_WHEN_FILE, when)
    if prev != mode:
        live = live_mode(STATE)
        if live and live != mode:
            _invalidate_reuse(STATE)
    return {
        "ok": True,
        "mode": mode,
        "using": mode,
        "when": when,
        "copy": "using: %s" % mode,
        "live": "READY",
    }


def mark_live(STATE, mode):
    mode = normalize_mode(mode)
    if mode not in MODES:
        return
    _write(Path(STATE) / MODE_LIVE_FILE, mode)


def _invalidate_reuse(STATE):
    """Force re-spawn when selected mode != live handed-off mode. Cite #208."""
    STATE = Path(STATE)
    live = STATE / MODE_LIVE_FILE
    try:
        if live.is_file():
            live.unlink()
    except OSError:
        pass
    for name in ATTACH_BASES:
        path = STATE / name
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass


def reuse_ok(STATE, mode):
    mode = normalize_mode(mode)
    live = live_mode(STATE)
    if not live:
        return mode == DEFAULT_MODE
    return live == mode


def _skills_root(ROOT):
    return Path(ROOT) / "bootstrap" / "grok-cli" / "skills"


def _agent_loops_skill(ROOT):
    src = _skills_root(ROOT) / "agent-loops"
    if (src / "SKILL.md").is_file():
        return src
    return None


def _link_skill(dest_dir, src, name):
    dest_dir.mkdir(parents=True, exist_ok=True)
    link = dest_dir / name
    try:
        if link.exists() or link.is_symlink():
            link.unlink()
    except OSError:
        pass
    try:
        link.symlink_to(src)
        return True, ""
    except OSError as e:
        return False, str(e)[:200]


def _handoff_text(mode, hid):
    hid = hid or "harness"
    if mode == "bare":
        return (
            "# Attach mode: bare (#208)\n\n"
            "This session is a **bare TUI**. Local endpoint is pinned "
            "(FreeToken-first). No orchestration loop and no code-graph MCP "
            "are claimed.\n"
            "Harness: %s\n" % hid
        )
    if mode == "orchestration":
        return (
            "# Attach mode: orchestration (#208)\n\n"
            "You manage agents using the **local model** at "
            "`LOCAL_OPENAI_BASE_URL` / `OPENAI_BASE_URL`.\n"
            "Use first-party `/agent-loops` (eight exits before the loop). "
            "Do not pretend this is a bare TUI.\n"
            "Harness: %s\n" % hid
        )
    return (
        "# Attach mode: code-graph (#208/#215)\n\n"
        "Prefer **Axon** (`axon analyze` / `axon serve --watch`) when live.\n"
        "If Axon is not live, use **codebase-memory MCP** as equivalent and "
        "do not claim Axon.\n"
        "Harness: %s\n" % hid
    )


def _prompt_text(mode):
    if mode == "bare":
        return "PFY_ATTACH_MODE=bare. Bare TUI on the local endpoint. No orchestration. No code-graph.\n"
    if mode == "orchestration":
        return (
            "PFY_ATTACH_MODE=orchestration. Manage agents with the local model. "
            "Load /agent-loops. Write the eight exits before iterating.\n"
        )
    return (
        "PFY_ATTACH_MODE=code-graph. Prefer Axon when PFY_GRAPH_PATH=axon. "
        "If PFY_GRAPH_PATH=codebase-memory, Axon is not live — do not claim Axon.\n"
    )


def _load_session_compose_224():
    """Load pfy_session_compose_224 or return None. Cite #224."""
    path = Path(__file__).resolve().parent / "pfy_session_compose_224.py"
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("pfy_session_compose_224_208", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _write_handoff_files(STATE, mode, hid):
    STATE = Path(STATE)
    handoff = _handoff_text(mode, hid)
    prompt = _prompt_text(mode)
    agents = handoff
    c224 = _load_session_compose_224()
    if c224 is not None:
        try:
            handoff, prompt, agents = c224.merge_into_handoff(STATE, handoff, prompt)
        except Exception:
            agents = handoff
    _write(STATE / HANDOFF_FILE, handoff)
    _write(STATE / PROMPT_FILE, prompt)
    _write(STATE / AGENTS_FILE, agents)
    env_lines = [
        "PFY_ATTACH_MODE=%s" % mode,
        "PFY_ATTACH_HANDOFF=%s" % (STATE / HANDOFF_FILE),
        "PFY_ATTACH_PROMPT=%s" % (STATE / PROMPT_FILE),
        "PFY_ATTACH_AGENTS=%s" % (STATE / AGENTS_FILE),
    ]
    brief = STATE / "session-compose.md"
    if brief.is_file():
        env_lines.append("PFY_SESSION_BRIEF=%s" % brief)
    card = STATE / "session-compose-prompt.md"
    if card.is_file():
        env_lines.append("PFY_SESSION_PROMPT=%s" % card)
    _write(STATE / ENV_FILE, "\n".join(env_lines))
    return env_lines


def _env_from_state(STATE, extra=None):
    STATE = Path(STATE)
    env = {}
    mode = current_mode(STATE)
    env["PFY_ATTACH_MODE"] = mode
    handoff = STATE / HANDOFF_FILE
    prompt = STATE / PROMPT_FILE
    agents = STATE / AGENTS_FILE
    if handoff.is_file():
        env["PFY_ATTACH_HANDOFF"] = str(handoff)
    if prompt.is_file():
        env["PFY_ATTACH_PROMPT"] = str(prompt)
    if agents.is_file():
        env["PFY_ATTACH_AGENTS"] = str(agents)
    if extra:
        env.update(extra)
    return env


def apply_child_env(env, STATE=None):
    """Inherit selected attach mode into Attach/start child env. Cite #208."""
    env = env if env is not None else {}
    if STATE is None:
        STATE = os.environ.get("PFY_STATE_DIR") or str(Path.home() / ".pfy-mentat")
    STATE = Path(STATE)
    extra = _env_from_state(STATE)
    for key, val in extra.items():
        if val:
            env[key] = val
    mode = extra.get("PFY_ATTACH_MODE") or current_mode(STATE)
    if mode == "orchestration":
        skills_dir = Path(env.get("OPENCODE_SKILLS") or (STATE / "opencode-skills"))
        src = STATE / "attach-skills" / "agent-loops"
        if not (src / "SKILL.md").is_file():
            src = STATE / "opencode-skills" / "agent-loops"
        if (src / "SKILL.md").is_file() or src.is_dir():
            _link_skill(skills_dir, src.resolve() if src.exists() else src, "agent-loops")
            env["OPENCODE_SKILLS"] = str(skills_dir)
            env["PFY_ATTACH_SKILL"] = "agent-loops"
        env = _apply_orchestration_213_env(env, STATE)
    if mode == "code-graph":
        env = _apply_code_graph_215_env(env, STATE)
    env = _apply_session_compose_224_env(env, STATE)
    return env


def _apply_session_compose_224_env(env, STATE):
    """Session compose brief into child env. Cite #224."""
    mod = _load_session_compose_224()
    if mod is None:
        return env
    try:
        return mod.apply_child_env(env, STATE)
    except Exception:
        return env


def _apply_orchestration_213_env(env, STATE):
    """Loop card/evidence into orchestration child. Cite #213."""
    path = Path(__file__).resolve().parent / "pfy_orchestration_213.py"
    if not path.is_file():
        return env
    try:
        spec = importlib.util.spec_from_file_location("pfy_orchestration_213_208", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.apply_child_env(env, STATE)
    except Exception:
        return env


def _load_code_graph_215():
    path = Path(__file__).resolve().parent / "pfy_code_graph_215.py"
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("pfy_code_graph_215_208", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _apply_code_graph_215_env(env, STATE):
    """Graph path/evidence into code-graph child. Cite #215."""
    mod = _load_code_graph_215()
    if mod is None:
        return env
    try:
        return mod.apply_child_env(env, STATE)
    except Exception:
        return env


def decorate_opencode_config(STATE):
    """Inject live code-graph MCP (Axon preferred) into STATE opencode.json. Cite #215."""
    STATE = Path(STATE)
    if current_mode(STATE) != "code-graph":
        return True, ""
    mod = _load_code_graph_215()
    if mod is None:
        return True, ""
    try:
        resolved = mod.resolve()
        if not resolved.get("ok"):
            return True, ""
        return mod.decorate_opencode_config(
            STATE, resolved.get("graph_path") or "", resolved.get("bin") or ""
        )
    except Exception as e:
        return False, str(e)[:200]


def _apply_grok_mcp(ROOT, STATE):
    merge = Path(ROOT) / "bootstrap" / "grok-cli" / "scripts" / "merge_config.py"
    if not merge.is_file():
        return False, "mcp merge missing"
    grok_home = Path(os.environ.get("GROK_HOME") or str(Path.home() / ".grok"))
    dests = [Path(STATE) / "grok-config.toml", grok_home / "config.toml"]
    applied = False
    last_err = ""
    for dest in dests:
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            p = subprocess.run(
                ["python3", str(merge), "--config", str(dest), "--no-backup"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            last_err = str(e)[:200]
            continue
        if p.returncode != 0:
            last_err = ((p.stdout or "") + (p.stderr or "") or "mcp merge failed")[-300:]
            continue
        text = dest.read_text(encoding="utf-8", errors="replace") if dest.is_file() else ""
        if "mcp_servers.codebase-memory" not in text:
            last_err = "mcp not in config"
            continue
        applied = True
    if not applied:
        return False, last_err or "mcp merge failed"
    return True, ""


def prepare(ROOT, STATE, hid, mode=None, which=None):
    """Write mode handoff into STATE (skills/AGENTS/prompts/env). Cite #208.

    Returns ok:True only when this hid can actually carry the mode.
    Does not spawn a TUI. Caller must not paint attached on ok:False.
    """
    ROOT = Path(ROOT)
    STATE = Path(STATE)
    hid = str(hid or "").strip()
    which = which or which_bin
    if mode is None or str(mode).strip() == "":
        mode = current_mode(STATE)
    else:
        sel = set_mode(STATE, mode)
        if not sel.get("ok"):
            sel["id"] = hid
            return sel
        mode = sel["mode"]
    mode = normalize_mode(mode)
    if mode not in MODES:
        return fail(hid, "unknown mode %s" % (mode or "(empty)"), NEXT_SELECT, mode=mode)

    extra = {}
    if mode == "orchestration":
        src = _agent_loops_skill(ROOT)
        if src is None:
            return fail(
                hid,
                "orchestration unwired -- agent-loops skill missing",
                NEXT_SETUP,
                mode=mode,
            )
        ok, err = _link_skill(STATE / "opencode-skills", src, "agent-loops")
        if not ok:
            return fail(hid, "cannot link agent-loops: %s" % err, NEXT_SETUP, mode=mode)
        ok, err = _link_skill(STATE / "attach-skills", src, "agent-loops")
        if not ok:
            return fail(hid, "cannot link agent-loops: %s" % err, NEXT_SETUP, mode=mode)
        extra["PFY_ATTACH_SKILL"] = "agent-loops"
        extra["OPENCODE_SKILLS"] = str(STATE / "opencode-skills")
        grok_home = Path(os.environ.get("GROK_HOME") or str(Path.home() / ".grok"))
        gdest = grok_home / "skills"
        if not (gdest / "agent-loops" / "SKILL.md").is_file():
            _link_skill(gdest, src, "agent-loops")

    elif mode == "code-graph":
        gmod = _load_code_graph_215()
        if gmod is None:
            return fail(
                hid,
                "code-graph unwired -- pfy_code_graph_215 missing",
                NEXT_SETUP,
                mode=mode,
            )
        wired = gmod.prepare(ROOT, STATE, hid, which=which)
        if not wired.get("ok"):
            nxt = wired.get("next_step") or NEXT_GRAPH
            return fail(
                hid,
                wired.get("error") or "code-graph unwired",
                nxt,
                mode=mode,
            )
        extra.update(wired.get("env") or {})
        extra["PFY_GRAPH_PATH"] = wired.get("graph_path") or ""
        extra["PFY_GRAPH_COPY"] = wired.get("graph_copy") or ""

    if not reuse_ok(STATE, mode):
        _invalidate_reuse(STATE)

    _write_handoff_files(STATE, mode, hid)
    env = _env_from_state(STATE, extra)
    env_lines = ["%s=%s" % (k, env[k]) for k in sorted(env)]
    _write(STATE / ENV_FILE, "\n".join(env_lines))
    out = {
        "ok": True,
        "id": hid,
        "mode": mode,
        "using": mode,
        "env": env,
        "handoff": str(STATE / HANDOFF_FILE),
        "copy": "using: %s" % mode,
        "live": "READY",
    }
    if mode == "code-graph":
        gpath = extra.get("PFY_GRAPH_PATH") or ""
        gcopy = extra.get("PFY_GRAPH_COPY") or (
            "path=axon" if gpath == "axon" else "path=codebase-memory (not axon)" if gpath else ""
        )
        if gcopy and gcopy not in out["copy"]:
            out["copy"] = "using: %s \u00b7 %s" % (mode, gcopy)
        out["graph_ok"] = True
        out["graph_path"] = gpath
        out["graph_copy"] = gcopy
        out["graph_when"] = extra.get("PFY_GRAPH_WHEN") or ""
    return out


def export_env_lines(STATE=None):
    if STATE is None:
        STATE = os.environ.get("PFY_STATE_DIR") or str(Path.home() / ".pfy-mentat")
    env = _env_from_state(STATE)
    path = Path(STATE) / ENV_FILE
    if path.is_file():
        lines = []
        for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
            s = raw.strip()
            if s.startswith("export "):
                s = s[7:].strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, v = s.split("=", 1)
            lines.append("export %s=%s" % (k.strip(), v.strip()))
        if lines:
            return lines
    return ["export %s=%s" % (k, env[k]) for k in sorted(env) if env[k]]


def cmd_prepare(hid, mode, root=None, state=None):
    root = Path(root or os.environ.get("PFY_ROOT") or Path(__file__).resolve().parents[1])
    state = Path(state or os.environ.get("PFY_STATE_DIR") or str(Path.home() / ".pfy-mentat"))
    res = prepare(root, state, hid, mode=mode)
    if not res.get("ok"):
        print(res.get("copy") or "FAIL mode")
        nxt = res.get("next_step") or NEXT_SELECT
        if nxt and nxt not in str(res.get("copy") or ""):
            print("  next: %s" % nxt)
        return 1
    extra = ""
    if res.get("graph_copy"):
        extra = " \u00b7 %s" % res.get("graph_copy")
    print("PASS mode \u00b7 using: %s%s" % (res.get("mode"), extra))
    for line in export_env_lines(state):
        print(line)
    return 0


def cmd_selftest():
    import tempfile

    root = Path(__file__).resolve().parents[1]
    errors = []

    def check(cond, msg):
        if not cond:
            errors.append(msg)

    check(normalize_mode("") == "bare", "empty -> bare")
    check(normalize_mode("orchestration") == "orchestration", "orch")
    check(normalize_mode("code_graph") == "code-graph", "graph alias")

    with tempfile.TemporaryDirectory(prefix="pfy-208-") as tmp:
        state = Path(tmp)
        bad = set_mode(state, "quantum")
        check(not bad.get("ok"), "unknown mode must FAIL")
        check("select bare" in (bad.get("next_step") or ""), "unknown next")

        ok = set_mode(state, "bare")
        check(ok.get("ok") and ok.get("using") == "bare", "set bare")
        snap = snapshot_fields(state)
        check(snap.get("using") == "bare", "snapshot using bare")

        res = prepare(root, state, "opencode", mode="bare")
        check(res.get("ok") and res.get("mode") == "bare", "bare prepare")
        check((state / HANDOFF_FILE).is_file(), "bare handoff file")
        check("bare TUI" in (state / HANDOFF_FILE).read_text(encoding="utf-8"), "bare text")
        env = apply_child_env({}, state)
        check(env.get("PFY_ATTACH_MODE") == "bare", "bare env")

        res = prepare(root, state, "grok", mode="orchestration")
        skill = _agent_loops_skill(root)
        if skill is None:
            check(not res.get("ok"), "orch FAIL without skill")
            check(NEXT_SETUP in (res.get("next_step") or ""), "orch next setup")
        else:
            check(res.get("ok"), "orch prepare with in-repo skill")
            check((state / "opencode-skills" / "agent-loops" / "SKILL.md").is_file(), "orch skill link")
            check("agent-loops" in (state / PROMPT_FILE).read_text(encoding="utf-8"), "orch prompt")

        with tempfile.TemporaryDirectory(prefix="pfy-208-noskill-") as empty:
            res = prepare(empty, state, "grok", mode="orchestration")
            check(not res.get("ok"), "orch FAIL empty root")
            check("unwired" in (res.get("error") or ""), "orch unwired copy")

        res = prepare(
            root, state, "hermes", mode="code-graph",
            which=lambda *n: "/tmp/fake-mcp" if n and n[0] == "codebase-memory-mcp" else "",
        )
        check(not res.get("ok"), "hermes code-graph MCP-only FAIL")
        check("unwired" in (res.get("error") or ""), "hermes not silent bare")
        check(
            "axon" in (res.get("next_step") or "").lower()
            or "opencode" in (res.get("next_step") or ""),
            "hermes graph next",
        )

        old_path = os.environ.get("PATH", "")
        try:
            os.environ["PATH"] = "/tmp/pfy-208-no-mcp"
            res = prepare(root, state, "opencode", mode="code-graph", which=lambda *n: "")
            check(not res.get("ok"), "code-graph FAIL without axon/mcp")
            nxt = res.get("next_step") or ""
            check("catalog" in nxt or "pip install" in nxt, "code-graph next catalog/install")
        finally:
            os.environ["PATH"] = old_path

        res = prepare(
            root, state, "opencode", mode="code-graph",
            which=lambda *n: "/tmp/fake-mcp" if n and n[0] == "codebase-memory-mcp" else "",
        )
        check(res.get("ok"), "code-graph MCP fallback")
        check(res.get("graph_path") == "codebase-memory", "mcp path")
        check("not axon" in (res.get("graph_copy") or ""), "do not claim axon")

        res = prepare(
            root, state, "hermes", mode="code-graph",
            which=lambda *n: "/tmp/fake-axon" if n and n[0] in ("axon", "axoniq") else "",
        )
        check(res.get("ok"), "hermes axon CLI ok")
        check(res.get("graph_path") == "axon", "hermes axon path")

        again = set_mode(state, "bare")
        check(again.get("ok") and current_mode(state) == "bare", "one mode replaces")
        check(current_mode(state) != "orchestration", "not two modes")

        env2 = apply_child_env({"KEEP": "1"}, state)
        check(env2.get("KEEP") == "1", "apply preserves")
        check(env2.get("PFY_ATTACH_MODE") == "bare", "apply sets mode")

    if errors:
        print("FAIL selftest · " + " ; ".join(errors))
        return 1
    print("PASS selftest · mode bare|orchestration|code-graph · FAIL+next")
    return 0


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print("usage: pfy_attach_mode_208.py [--selftest|--set MODE|--prepare HID [MODE]|--export-env]")
        return 0
    if args[0] in ("--selftest", "selftest"):
        return cmd_selftest()
    if args[0] in ("--export-env", "export-env"):
        for line in export_env_lines():
            print(line)
        return 0
    if args[0] in ("--set", "set"):
        mode = args[1] if len(args) > 1 else ""
        state = Path(os.environ.get("PFY_STATE_DIR") or str(Path.home() / ".pfy-mentat"))
        res = set_mode(state, mode)
        print(res.get("copy") or res.get("error") or "")
        return 0 if res.get("ok") else 1
    if args[0] in ("--prepare", "prepare"):
        hid = args[1] if len(args) > 1 else ""
        mode = args[2] if len(args) > 2 else None
        return cmd_prepare(hid, mode)
    print("usage: pfy_attach_mode_208.py [--selftest|--set MODE|--prepare HID [MODE]|--export-env]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
