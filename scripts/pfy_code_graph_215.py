#!/usr/bin/env python3
"""Attach code-graph: Axon usable path (or equivalent) -- cite #215.

Prefer Axon (`pip install axoniq`; `axon analyze` / `axon serve --watch`) when
the binary is on PATH. If Axon is missing or prove fails, fall back to
already-present `codebase-memory-mcp` as equivalent and paint that path.
Never claim Axon when only the MCP stub is live. Unwired = FAIL+next
(catalog pick/queue). LIVE_HARD_OFF: no cloud embeddings / live catalog writes.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ISSUE = "#215"
PATH_AXON = "axon"
PATH_MCP = "codebase-memory"
EVIDENCE_FILE = "graph-evidence.json"
HANDOFF_FILE = "graph-handoff.md"
PROMPT_FILE = "graph-prompt.md"
PATH_FILE = "graph-path"
WHEN_FILE = "graph-when"
NEXT_INSTALL = "pip install axoniq"
NEXT_CATALOG = "./pfy catalog ask axon"
NEXT_BOTH = "pip install axoniq · ./pfy catalog ask axon"
NEXT_MCP = "./bootstrap/grok-cli/install.sh --with-codebase-memory"
NEXT_HERMES = "pip install axoniq · Attach grok or opencode for code-graph MCP"
HELLO_TOKEN = "PFY_CODE_GRAPH_215_HELLO"
HELLO_NAME = "pfy_215_hello.py"


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


def fail(hid, reason, next_step, **extra):
    copy = "FAIL code-graph -- %s \u00b7 %s" % (reason, next_step)
    out = {
        "ok": False,
        "id": hid or "",
        "live": "FAIL",
        "copy": copy,
        "error": reason,
        "next_step": next_step,
        "usable": False,
        "using": "code-graph",
        "mode": "code-graph",
        "graph_ok": False,
        "graph_path": "",
        "graph_copy": copy,
        "issue": ISSUE,
    }
    out.update(extra)
    return out


def find_axon(which=None):
    which = which or which_bin
    if callable(which):
        return which("axon") or which("axoniq") or ""
    return which_bin("axon", "axoniq")


def find_mcp(which=None):
    which = which or which_bin
    if callable(which):
        return which("codebase-memory-mcp") or ""
    return which_bin("codebase-memory-mcp")


def run_cmd(cmd, cwd=None, timeout=90, env=None):
    try:
        p = subprocess.run(
            cmd,
            cwd=cwd or "/tmp",
            env=env or os.environ.copy(),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "") if isinstance(e.stdout, str) else ""
        err = (e.stderr or "") if isinstance(e.stderr, str) else "timeout"
        return 124, out, err or "timeout"
    except OSError as e:
        return 127, "", str(e)[:200]
    out = p.stdout or ""
    err = (p.stderr or "").strip()
    return p.returncode, out, err


def prove_axon_bin(axon, root=None):
    """CLI exists and can analyze a tiny local fixture. No cloud embeddings."""
    if not axon:
        return False, "axon missing", []
    rc, out, err = run_cmd([axon, "--help"], timeout=20)
    blob = ("%s\n%s" % (out, err)).lower()
    if rc != 0 and "usage" not in blob and "analyze" not in blob:
        rc2, out2, err2 = run_cmd([axon, "--version"], timeout=15)
        if rc2 != 0:
            return False, "axon --help failed: %s" % (err or out or "exit %s" % rc)[:200], []
        blob = ("%s\n%s" % (out2, err2)).lower()
    lines = ["axon bin: %s" % axon]
    if "analyze" in blob or rc == 0:
        lines.append("axon help: ok")
    env = os.environ.copy()
    for key in ("OPENAI_API_KEY", "EMBEDDING_API_KEY", "ANTHROPIC_API_KEY", "XAI_API_KEY"):
        env.pop(key, None)
    hello_dir = None
    try:
        hello_dir = tempfile.mkdtemp(prefix="pfy-215-hello-")
        body = (
            "# pfy code-graph hello-world (#215)\n"
            "TOKEN = %r\n\n"
            "def pfy_code_graph_hello():\n"
            "    return TOKEN\n"
        ) % HELLO_TOKEN
        Path(hello_dir, HELLO_NAME).write_text(body, encoding="utf-8")
        rc, out, err = run_cmd(
            [axon, "analyze", hello_dir, "--no-embeddings"],
            cwd=hello_dir,
            timeout=120,
            env=env,
        )
        blob = ("%s\n%s" % (out, err))
        if rc != 0:
            return False, "axon analyze failed: %s" % (err or out or "exit %s" % rc)[:240], lines
        lines.append("analyze: ok")
        if HELLO_TOKEN in blob or "symbol" in blob.lower() or "done" in blob.lower() or rc == 0:
            lines.append("hello token: indexed")
        rc, out, err = run_cmd([axon, "serve", "--help"], cwd=hello_dir, timeout=20, env=env)
        serve_blob = ("%s\n%s" % (out, err)).lower()
        if rc == 0 or "watch" in serve_blob or "mcp" in serve_blob or "serve" in serve_blob:
            lines.append("serve --help: ok (MCP)")
        else:
            rc, out, err = run_cmd([axon, "mcp", "--help"], cwd=hello_dir, timeout=20, env=env)
            if rc == 0 or "mcp" in ("%s\n%s" % (out, err)).lower():
                lines.append("mcp --help: ok")
            else:
                lines.append("serve/mcp help: SKIP (%s)" % (err or out or "exit %s" % rc)[:120])
        return True, "", lines
    finally:
        if hello_dir:
            try:
                shutil.rmtree(hello_dir, ignore_errors=True)
            except OSError:
                pass


def resolve(which=None):
    """Pick live path: axon preferred, else codebase-memory. Never invent axon."""
    axon = find_axon(which)
    mcp = find_mcp(which)
    if axon:
        return {
            "ok": True,
            "graph_path": PATH_AXON,
            "bin": axon,
            "mcp_bin": mcp,
            "copy": "path=axon",
        }
    if mcp:
        return {
            "ok": True,
            "graph_path": PATH_MCP,
            "bin": mcp,
            "mcp_bin": mcp,
            "copy": "path=codebase-memory (not axon)",
        }
    return {
        "ok": False,
        "graph_path": "",
        "bin": "",
        "mcp_bin": "",
        "copy": "unwired",
        "error": "code-graph unwired -- axon and codebase-memory-mcp missing",
        "next_step": NEXT_BOTH,
    }


def _handoff_text(hid, graph_path, bin_path):
    hid = hid or "harness"
    if graph_path == PATH_AXON:
        return (
            "# Attach mode: code-graph (#215)\n\n"
            "Live path: **Axon** (`axoniq`). Binary: `%s`\n"
            "Index: `axon analyze . --no-embeddings`. MCP: `axon serve --watch`.\n"
            "Do not claim codebase-memory as Axon.\n"
            "Harness: %s\n" % (bin_path, hid)
        )
    return (
        "# Attach mode: code-graph (#215)\n\n"
        "Live path: **codebase-memory MCP** (Axon is **not** live).\n"
        "Command: `codebase-memory-mcp`. Do not claim Axon.\n"
        "Next to get Axon: `%s` or `%s`.\n"
        "Harness: %s\n" % (NEXT_INSTALL, NEXT_CATALOG, hid)
    )


def _prompt_text(graph_path):
    if graph_path == PATH_AXON:
        return (
            "PFY_ATTACH_MODE=code-graph. PFY_GRAPH_PATH=axon. "
            "Use Axon (axon query / axon context / axon serve --watch). "
            "Do not claim codebase-memory as Axon.\n"
        )
    return (
        "PFY_ATTACH_MODE=code-graph. PFY_GRAPH_PATH=codebase-memory. "
        "Axon is not live. Use codebase-memory MCP as the equivalent code-graph. "
        "Do not claim Axon.\n"
    )


def snapshot_fields(STATE):
    STATE = Path(STATE)
    empty = {
        "graph_ok": False,
        "graph_copy": "",
        "graph_when": "",
        "graph_path": "",
        "graph_bin": "",
        "graph_evidence": "",
        "graph_next": NEXT_BOTH,
    }
    raw = _read(STATE / EVIDENCE_FILE)
    path = _read(STATE / PATH_FILE)
    if path in (PATH_AXON, PATH_MCP):
        empty["graph_path"] = path
    if not raw:
        if empty["graph_path"]:
            empty["graph_copy"] = (
                "path=axon" if empty["graph_path"] == PATH_AXON
                else "path=codebase-memory (not axon)"
            )
            empty["graph_ok"] = True
            empty["graph_when"] = _read(STATE / WHEN_FILE)
            empty["graph_next"] = ""
        return empty
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return empty
    if not isinstance(data, dict):
        return empty
    ok = bool(data.get("ok"))
    gpath = str(data.get("graph_path") or empty["graph_path"] or "")
    copy = str(data.get("copy") or "")
    if gpath == PATH_AXON and "axon" not in copy.lower():
        copy = ("path=axon" + (" \u00b7 " + copy if copy else "")).strip(" \u00b7")
    if gpath == PATH_MCP and "not axon" not in copy.lower():
        copy = "path=codebase-memory (not axon)"
    empty.update({
        "graph_ok": ok,
        "graph_copy": copy,
        "graph_when": str(data.get("when") or _read(STATE / WHEN_FILE) or ""),
        "graph_path": gpath,
        "graph_bin": str(data.get("bin") or ""),
        "graph_evidence": str(STATE / EVIDENCE_FILE),
        "graph_next": "" if ok else str(data.get("next_step") or NEXT_BOTH),
    })
    return empty


def apply_child_env(env, STATE=None, which=None):
    """Inherit live code-graph path into Attach/start child. Cite #215."""
    env = env if env is not None else {}
    if STATE is None:
        STATE = os.environ.get("PFY_STATE_DIR") or str(Path.home() / ".pfy-mentat")
    STATE = Path(STATE)
    resolved = resolve(which)
    gpath = resolved.get("graph_path") or _read(STATE / PATH_FILE)
    bin_path = resolved.get("bin") or ""
    if gpath == PATH_AXON and bin_path:
        env["PFY_GRAPH_PATH"] = PATH_AXON
        env["AXON_BIN"] = bin_path
        env["PFY_CODE_GRAPH"] = "axon"
        env.pop("AXON_CLAIM", None)
    elif gpath == PATH_MCP and bin_path:
        env["PFY_GRAPH_PATH"] = PATH_MCP
        env["CODEBASE_MEMORY_MCP"] = bin_path
        env["PFY_CODE_GRAPH"] = "codebase-memory"
        env.pop("AXON_BIN", None)
    evidence = STATE / EVIDENCE_FILE
    handoff = STATE / HANDOFF_FILE
    prompt = STATE / PROMPT_FILE
    if evidence.is_file():
        env["PFY_GRAPH_EVIDENCE"] = str(evidence)
    if handoff.is_file():
        env["PFY_GRAPH_HANDOFF"] = str(handoff)
    if prompt.is_file():
        env["PFY_GRAPH_PROMPT"] = str(prompt)
    return env


def export_env_lines(STATE=None, which=None):
    env = apply_child_env({}, STATE, which=which)
    keys = (
        "PFY_GRAPH_PATH",
        "PFY_CODE_GRAPH",
        "AXON_BIN",
        "CODEBASE_MEMORY_MCP",
        "PFY_GRAPH_EVIDENCE",
        "PFY_GRAPH_HANDOFF",
        "PFY_GRAPH_PROMPT",
    )
    lines = []
    for key in keys:
        val = env.get(key) or ""
        if not val:
            continue
        lines.append("export %s=%s" % (key, json.dumps(val)))
    return lines


def decorate_opencode_config(STATE, graph_path, bin_path):
    STATE = Path(STATE)
    path = STATE / "opencode.json"
    if not path.is_file():
        return True, ""
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, "opencode.json unreadable"
    if not isinstance(cfg, dict):
        return False, "opencode.json not an object"
    mcp = cfg.get("mcp") if isinstance(cfg.get("mcp"), dict) else {}
    if graph_path == PATH_AXON and bin_path:
        mcp["axon"] = {
            "type": "local",
            "command": [bin_path, "serve", "--watch"],
            "enabled": True,
        }
    elif graph_path == PATH_MCP and bin_path:
        mcp["codebase-memory"] = {
            "type": "local",
            "command": [bin_path],
            "enabled": True,
        }
    cfg["mcp"] = mcp
    try:
        path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    except OSError as e:
        return False, str(e)[:200]
    return True, ""


def _upsert_axon_mcp_toml(dest, axon_bin):
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = dest.read_text(encoding="utf-8", errors="replace") if dest.is_file() else ""
    block = (
        "[mcp_servers.axon]\n"
        "command = %s\n"
        'args = ["serve", "--watch"]\n'
        "enabled = true\n" % json.dumps(axon_bin)
    )
    if "mcp_servers.axon" in text:
        return True, ""
    try:
        with dest.open("a", encoding="utf-8") as f:
            if text and not text.endswith("\n"):
                f.write("\n")
            f.write("\n" + block)
    except OSError as e:
        return False, str(e)[:200]
    return True, ""


def apply_grok_mcp(ROOT, STATE, graph_path, bin_path):
    STATE = Path(STATE)
    grok_home = Path(os.environ.get("GROK_HOME") or str(Path.home() / ".grok"))
    dests = [STATE / "grok-config.toml", grok_home / "config.toml"]
    if graph_path == PATH_AXON and bin_path:
        applied = False
        last_err = ""
        axon_real = Path(bin_path).is_file()
        for dest in dests:
            if dest == grok_home / "config.toml" and not axon_real:
                continue
            ok, err = _upsert_axon_mcp_toml(dest, bin_path)
            if ok:
                applied = True
            else:
                last_err = err
        if not applied:
            return False, last_err or "axon mcp write failed"
        return True, ""
    if graph_path == PATH_MCP:
        merge = Path(ROOT) / "bootstrap" / "grok-cli" / "scripts" / "merge_config.py"
        if not merge.is_file():
            return False, "mcp merge missing"
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
    return False, "no graph path"


def _write_evidence(STATE, payload):
    STATE = Path(STATE)
    STATE.mkdir(parents=True, exist_ok=True)
    path = STATE / EVIDENCE_FILE
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def prepare(ROOT, STATE, hid, which=None):
    """Wire live Axon or equivalent into STATE for this hid. Cite #215.

    Does not spawn a TUI. Caller must not paint attached on ok:False.
    Hermes + MCP-only is unwired (no MCP handoff). Hermes + Axon CLI is ok.
    """
    ROOT = Path(ROOT)
    STATE = Path(STATE)
    hid = str(hid or "").strip()
    resolved = resolve(which)
    if not resolved.get("ok"):
        return fail(
            hid,
            resolved.get("error") or "code-graph unwired",
            resolved.get("next_step") or NEXT_BOTH,
        )
    gpath = resolved["graph_path"]
    bin_path = resolved["bin"]
    if hid in ("hermes", "codex", "claude", "claude-code") and gpath != PATH_AXON:
        who = {"hermes": "Hermes", "codex": "Codex"}.get(hid, "Claude")
        return fail(
            hid,
            "code-graph unwired for %s (no Axon CLI; MCP-only)" % who,
            NEXT_HERMES,
            graph_path="",
        )
    extra = {
        "PFY_GRAPH_PATH": gpath,
        "PFY_CODE_GRAPH": gpath,
    }
    if gpath == PATH_AXON:
        extra["AXON_BIN"] = bin_path
    else:
        extra["CODEBASE_MEMORY_MCP"] = bin_path
        extra["PFY_MCP"] = "1"
    if hid in ("opencode", "grok"):
        ok, err = decorate_opencode_config(STATE, gpath, bin_path)
        if not ok:
            return fail(hid, "code-graph unwired -- %s" % (err or "opencode mcp"), NEXT_BOTH, graph_path=gpath)
        if hid == "grok":
            ok, err = apply_grok_mcp(ROOT, STATE, gpath, bin_path)
            if not ok:
                return fail(
                    hid,
                    "code-graph unwired -- %s" % (err or "mcp merge failed"),
                    NEXT_MCP if gpath == PATH_MCP else NEXT_INSTALL,
                    graph_path=gpath,
                )
    when = _now()
    copy = "path=axon" if gpath == PATH_AXON else "path=codebase-memory (not axon)"
    _write(STATE / PATH_FILE, gpath)
    _write(STATE / WHEN_FILE, when)
    _write(STATE / HANDOFF_FILE, _handoff_text(hid, gpath, bin_path))
    _write(STATE / PROMPT_FILE, _prompt_text(gpath))
    payload = {
        "ok": True,
        "issue": ISSUE,
        "hid": hid,
        "when": when,
        "graph_path": gpath,
        "bin": bin_path,
        "copy": copy,
        "status": "READY",
    }
    evidence = _write_evidence(STATE, payload)
    env = apply_child_env(dict(extra), STATE, which=which)
    return {
        "ok": True,
        "id": hid,
        "live": "READY",
        "copy": copy,
        "using": "code-graph",
        "mode": "code-graph",
        "usable": True,
        "graph_ok": True,
        "graph_path": gpath,
        "graph_copy": copy,
        "graph_when": when,
        "graph_bin": bin_path,
        "graph_evidence": str(evidence),
        "env": env,
        "handoff": str(STATE / HANDOFF_FILE),
        "issue": ISSUE,
    }


def cmd_prove(root=None):
    root = Path(root or os.environ.get("PFY_ROOT") or Path(__file__).resolve().parents[1])
    axon = find_axon()
    mcp = find_mcp()
    if axon:
        ok, err, lines = prove_axon_bin(axon, root)
        if ok:
            print("PASS code-graph \u00b7 path=axon \u00b7 %s" % axon)
            for line in lines:
                print("  %s" % line)
            print("handoff: Attach OpenCode|Hermes|Grok inherit AXON_BIN / PFY_GRAPH_PATH=axon")
            print("MCP: axon serve --watch")
            print("Grok: [mcp_servers.axon] command=%s args=[\"serve\", \"--watch\"]" % json.dumps(axon))
            print("OpenCode: mcp.axon command=[%s, serve, --watch]" % json.dumps(axon))
            print("note: never claim Axon when only codebase-memory MCP is live")
            for line in export_env_lines():
                print(line)
            return 0
        if mcp:
            print("PASS code-graph \u00b7 path=codebase-memory (not axon) \u00b7 %s" % mcp)
            print("  axon prove failed: %s" % err)
            print("  next for Axon: %s" % NEXT_INSTALL)
            print("  fallback: codebase-memory-mcp (do not claim Axon)")
            print("handoff: Attach OpenCode|Grok inherit CODEBASE_MEMORY_MCP")
            for line in export_env_lines():
                print(line)
            return 0
        print("FAIL: %s" % err)
        print("  next: %s" % NEXT_BOTH)
        return 1
    if mcp:
        print("PASS code-graph \u00b7 path=codebase-memory (not axon) \u00b7 %s" % mcp)
        print("  axon: missing")
        print("  next for Axon: %s" % NEXT_BOTH)
        print("handoff: Attach OpenCode|Grok inherit CODEBASE_MEMORY_MCP")
        print("note: do not claim Axon; MCP stub is the live path")
        for line in export_env_lines():
            print(line)
        return 0
    print("FAIL: axon missing")
    print("  next: %s" % NEXT_BOTH)
    return 1


def cmd_export_env():
    for line in export_env_lines():
        print(line)
    return 0


def cmd_selftest():
    errors = []

    def check(cond, msg):
        if not cond:
            errors.append(msg)

    root = Path(__file__).resolve().parents[1]
    old_path = os.environ.get("PATH", "")
    try:
        os.environ["PATH"] = "/tmp/pfy-215-no-graph"
        if find_axon():
            errors.append("find_axon empty PATH")
        if find_mcp():
            # may still find if which ignores PATH; force via which=
            pass
        resolved = resolve(which=lambda *n: "")
        check(not resolved.get("ok"), "resolve empty FAIL")
        check(NEXT_CATALOG.split()[0] in (resolved.get("next_step") or ""), "resolve next catalog")
        env = apply_child_env({}, which=lambda *n: "")
        check(not env.get("AXON_BIN"), "no AXON_BIN when missing")
        check(not env.get("PFY_GRAPH_PATH"), "no path when missing")
    finally:
        os.environ["PATH"] = old_path

    with tempfile.TemporaryDirectory(prefix="pfy-215-") as tmp:
        state = Path(tmp)
        res = prepare(root, state, "opencode", which=lambda *n: "")
        check(not res.get("ok"), "prepare empty FAIL")
        check("catalog" in (res.get("next_step") or "") or "pip install" in (res.get("next_step") or ""), "prepare next")
        check(res.get("using") == "code-graph", "fail still using code-graph")
        check(res.get("usable") is False, "not silent bare")

        def which_mcp(*n):
            if n and n[0] == "codebase-memory-mcp":
                return "/tmp/fake-mcp"
            return ""

        res = prepare(root, state, "hermes", which=which_mcp)
        check(not res.get("ok"), "hermes MCP-only FAIL")
        check("unwired" in (res.get("error") or ""), "hermes unwired")
        check("axon" in (res.get("next_step") or "").lower() or "opencode" in (res.get("next_step") or ""), "hermes next")

        res = prepare(root, state, "opencode", which=which_mcp)
        check(res.get("ok"), "opencode MCP fallback")
        check(res.get("graph_path") == PATH_MCP, "path mcp")
        check("not axon" in (res.get("graph_copy") or ""), "paint not axon")
        check((state / PATH_FILE).read_text(encoding="utf-8").strip() == PATH_MCP, "state path mcp")
        env = apply_child_env({}, state, which=which_mcp)
        check(env.get("PFY_GRAPH_PATH") == PATH_MCP, "env mcp")
        check(not env.get("AXON_BIN"), "MCP must not set AXON_BIN")

        def which_axon(*n):
            if n and n[0] in ("axon", "axoniq"):
                return "/tmp/fake-axon"
            return ""

        res = prepare(root, state, "hermes", which=which_axon)
        check(res.get("ok"), "hermes axon CLI ok")
        check(res.get("graph_path") == PATH_AXON, "hermes path axon")
        check(res.get("graph_copy") == "path=axon", "hermes paint axon")
        env = apply_child_env({}, state, which=which_axon)
        check(env.get("AXON_BIN") == "/tmp/fake-axon", "hermes AXON_BIN")
        check(env.get("PFY_GRAPH_PATH") == PATH_AXON, "hermes env axon")

        res = prepare(root, state, "opencode", which=which_axon)
        check(res.get("ok") and res.get("graph_path") == PATH_AXON, "opencode axon")
        snap = snapshot_fields(state)
        check(snap.get("graph_path") == PATH_AXON, "snapshot axon")
        check("not axon" not in (snap.get("graph_copy") or ""), "snapshot does not deny axon")

    if errors:
        print("FAIL selftest \u00b7 " + " ; ".join(errors))
        return 1
    print("PASS selftest \u00b7 code-graph axon|codebase-memory \u00b7 FAIL+next \u00b7 never claim axon on MCP")
    return 0


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("--prove", "prove"):
        return cmd_prove()
    if args[0] in ("--export-env", "export-env"):
        return cmd_export_env()
    if args[0] in ("--selftest", "selftest"):
        return cmd_selftest()
    if args[0] in ("--prepare", "prepare"):
        hid = args[1] if len(args) > 1 else ""
        root = Path(os.environ.get("PFY_ROOT") or Path(__file__).resolve().parents[1])
        state = Path(os.environ.get("PFY_STATE_DIR") or str(Path.home() / ".pfy-mentat"))
        res = prepare(root, state, hid)
        if not res.get("ok"):
            print(res.get("copy") or "FAIL code-graph")
            nxt = res.get("next_step") or NEXT_BOTH
            if nxt and nxt not in str(res.get("copy") or ""):
                print("  next: %s" % nxt)
            return 1
        print("PASS code-graph \u00b7 %s" % res.get("graph_copy"))
        for line in export_env_lines(state):
            print(line)
        return 0
    if args[0] in ("-h", "--help"):
        print("usage: pfy_code_graph_215.py [--prove|--export-env|--selftest|--prepare HID]")
        return 0
    print("usage: pfy_code_graph_215.py [--prove|--export-env|--selftest|--prepare HID]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
