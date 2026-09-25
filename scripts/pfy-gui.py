#!/usr/bin/env python3
"""Native operator window. scripts/pfy prefers a current Tauri binary; else this file.

Order here: WebKit2 (gi) → stdlib tk. pywebview only if PFY_GUI_DEV=1 and it imports.
Print native window (webkit) or native window (tk). Never STUB. Never exit 2.
"""
from __future__ import annotations
import importlib.util, os, socket, sys, threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ("ready", "partial", "stub", "detected-stub", "missing", "skip")
GROK_USE = "pfy harness use grok"
BLOCKED = frozenset({"continue", "agent-cage"})
FG, BG, SIDE, PANE, CLOUD, MUTED = "#e8edf4", "#0e1116", "#121821", "#151a22", "#1a2740", "#8b97a8"
CHIP = {"ready":"#3dd68c","partial":"#e6c15a","stub":"#e8875b","detected-stub":"#c984f0","missing":"#7d8796","skip":"#7d8796","implemented":"#3dd68c","wired":"#3dd68c","not wired":"#e8875b","on":"#3dd68c","off":"#7d8796"}

def honest(v):
    s = (v or "").strip().lower()
    return s if s in LIVE else "missing"

def module_paint_status(m):
    """Operator chrome: per-agent paint when present, else implemented→wired."""
    if m.get("agent_paint"):
        return m["agent_paint"]
    if m.get("agent_stub") or m.get("stub"):
        return "not wired"
    st = m.get("agent_status") or m.get("status") or ""
    if st == "implemented":
        return "wired"
    return st

def loop_text(s, env_live, att, reach, verb, when):
    """Loop body: local compute | cloud orchestration | catalog modules, with why/how."""
    h = s.get("hedge") or {}
    try:
        from pfylib import loop_paint
        st = loop_paint.story(h)
    except Exception:
        st = {}
    local_ready = bool(h.get("local_ready"))
    cloud_lane = st.get("cloud_lane") or "OFF"
    if not st.get("cloud_lane"):
        rem = h.get("remaining") or 0
        profile = h.get("profile") or "(unset)"
        lane = h.get("lane") or ""
        cloud_on = lane == "cloud" or (rem > 0 and profile != "local-only")
        if lane == "cloud":
            cloud_lane = "SPENDING"
        elif cloud_on:
            cloud_lane = "STANDBY"
        else:
            cloud_lane = "OFF"
    loc_reason = ""
    routes = h.get("routes") or {}
    if isinstance(routes.get("interactive"), dict):
        loc_reason = str(routes["interactive"].get("reason") or "")
    cloud_reason = ""
    if isinstance(routes.get("hard"), dict):
        cloud_reason = str(routes["hard"].get("reason") or "")
    task = s.get("modules_task") or h.get("task") or "interactive"
    task_help = (s.get("task_help") or {}).get(task) or st.get("task_help") or ""
    lines = [
        "LOOP",
        "Run gathered catalog tools on this machine or on cloud credits.",
        "HOW TO  1 where work runs  2 which agent  3 toolsets for that agent  4 open that agent",
        "        Start local model only brings up the endpoint.",
        "PLAN      %s" % (s.get("plan") or "Open %s with no toolsets yet" % (s.get("modules_agent") or "grok")),
        "AGENT     %s" % (s.get("modules_agent") or "grok"),
        "LOCAL COMPUTE",
        "  why       your machine — preferred when a model is answering",
        "  lane      %s" % ("ON" if local_ready else "OFF"),
        "  engine    %s" % (h.get("local_engine") or "none"),
        "  status    %s" % (h.get("local_status") or "missing"),
        "  endpoint  %s" % (h.get("local_base_url") or "(none)"),
    ]
    if loc_reason:
        lines.append("  %s" % loc_reason)
    meaning = st.get("local_meaning") or h.get("local_meaning") or ""
    if meaning:
        lines.append("  meaning   %s" % meaning)
    lines += [
        "CLOUD ORCHESTRATION",
        "  why       paid credits — only if local cannot, or work is hard",
        "  lane      %s" % cloud_lane,
        "  budget    %s · spent %s · left %s" % (h.get("budget", 0), h.get("spent", 0), h.get("remaining", 0)),
        "  profile   %s · gab key %s" % (h.get("profile") or "(unset)", "ready" if h.get("gab_key") else "missing"),
    ]
    if cloud_reason:
        lines.append("  %s" % cloud_reason)
    cmean = st.get("cloud_meaning") or h.get("cloud_meaning") or ""
    if cmean:
        lines.append("  meaning   %s" % cmean)
    route = st.get("route") or h.get("route") or str(h.get("copy") or "").strip()
    if route:
        lines.append("this session  %s" % route)
    nxt = st.get("next_step") or h.get("next_step") or ""
    if nxt and not h.get("ok", True):
        lines.append("next      %s" % nxt)
    copy = str(h.get("copy") or "").strip()
    if copy and copy != route:
        lines.append("live      %s" % copy)
    lines += ["WORK CLASS  %s" % task]
    if task_help:
        lines.append("  %s" % task_help)
    lines.append("TOOLSETS")
    lines.append("  why       status is for the selected agent — ON means included in Open")
    mods = list(s.get("modules") or [])
    if not mods:
        lines.append("  (none)")
    else:
        for m in mods:
            mark = "ON" if m.get("enabled") else ("STUB" if m.get("stub") else "off")
            lines.append("  %-16s %-12s %s" % (m.get("id") or "", module_paint_status(m), mark))
    enabled = " · ".join(str(x) for x in (s.get("modules_enabled") or []) if x) or "(none)"
    lines += [
        "enabled   %s" % enabled,
        "env       %s" % env_live,
        "session   %s" % reach,
        "attached  %s" % att,
        "NEXT      Open the agent named in PLAN. That window is the proof.",
    ]
    proof = str(s.get("loop_copy") or "").strip()
    if proof:
        extra = str(s.get("loop_when") or "").strip()
        lines.append("proof     %s%s" % (proof, ("  " + extra) if extra else ""))
    lines.append("last      %s%s" % (verb, ("  " + when) if when else ""))
    return "\n".join(lines)

def stopped_exit(error):
    state = Path(os.environ.get("PFY_STATE_DIR", str(Path.home() / ".pfy-mentat")))
    state.mkdir(parents=True, exist_ok=True)
    artifact = state / "gui-stopped-exit.txt"
    artifact.write_text(f"STOPPED_EXIT\nerror: {error}\n", encoding="utf-8")
    print(f"STOPPED_EXIT: {error}", file=sys.stderr)
    print(f"artifact: {artifact}", file=sys.stderr)
    return 1

def load_board():
    path = ROOT / "scripts" / "pfy-board.py"
    spec = importlib.util.spec_from_file_location("pfy_board", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def port_open(host, port):
    s = socket.socket(); s.settimeout(0.3)
    try:
        s.connect((host, port)); return True
    except OSError:
        return False
    finally:
        s.close()

def leftover_dump(body, hdr=""):
    """True when HTML is the old consultant board, not the current session."""
    h = (hdr or "").strip().lower()
    b = body or ""
    low = b.lower()
    if h == "session" and ('data-pfy-ui="session"' in b or "data-pfy-ui=session" in b) and "pfy board" not in low:
        return False
    if "pfy board" in low or "start via cli" in low:
        return True
    if "127.0.0.1:8765" in b and "<title>pfy</title>" not in low:
        return True
    return False

def occupant_html(host, port):
    import urllib.request
    try:
        req = urllib.request.Request(f"http://{host}:{port}/", method="GET")
        with urllib.request.urlopen(req, timeout=0.4) as r:
            hdr = (r.headers.get("X-Pfy-UI") or "")
            body = r.read(16000).decode("utf-8", "replace")
        return hdr, body
    except Exception:
        return "", ""

def bind_http(board, host, port):
    from http.server import ThreadingHTTPServer
    httpd = ThreadingHTTPServer((host, port), board.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd

def ensure_http(board):
    """Serve current frontend. Never reuse a leftover listener just because the port answered."""
    host = getattr(board, "HOST", os.environ.get("PFY_BOARD_HOST", "127.0.0.1"))
    preferred = int(getattr(board, "PORT", os.environ.get("PFY_BOARD_PORT", "8765")))
    if host not in ("127.0.0.1", "localhost"):
        host = "127.0.0.1"
    from http.server import ThreadingHTTPServer
    httpd = None
    chosen = None
    tried = [preferred] + [p for p in range(preferred + 1, preferred + 16)]
    for port in tried:
        if port_open(host, port):
            continue
        try:
            httpd = bind_http(board, host, port)
            chosen = port
            break
        except OSError:
            continue
    if httpd is None:
        httpd = ThreadingHTTPServer((host, 0), board.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        chosen = httpd.server_address[1]
    return httpd, f"http://{host}:{chosen}/"

def run_webkit(url) -> bool:
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        ok = False
        for ver in ("4.1", "4.0"):
            try:
                gi.require_version("WebKit2", ver); ok = True; break
            except ValueError:
                continue
        if not ok:
            return False
        from gi.repository import Gtk, WebKit2
        win = Gtk.Window(title="pfy"); win.set_default_size(1280, 800)
        win.connect("destroy", Gtk.main_quit)
        view = WebKit2.WebView()
        try:
            stg = view.get_settings()
            stg.set_enable_javascript(True)
            stg.set_javascript_can_access_clipboard(True)
        except Exception:
            pass
        view.load_uri(url); win.add(view); win.show_all()
    except Exception:
        return False
    print("native window (webkit)", flush=True)
    Gtk.main()
    return True

def run_pywebview(url) -> bool:
    try:
        import webview
        webview.create_window("pfy", url, width=1280, height=800)
    except Exception:
        return False
    print("native window (pywebview)", flush=True)
    webview.start()
    return True

class Win:
    def __init__(self, board, root):
        self.board, self.root = board, root
        self.busy = False; self.msg = ""; self.view = "loop"; self.snap = {}; self.pending_user = False
        tk = sys.modules["tkinter"]; ttk = sys.modules["tkinter.ttk"]
        root.title("pfy"); root.geometry("1280x800"); root.configure(bg=BG); root.minsize(960, 640)
        st = ttk.Style()
        try: st.theme_use("clam")
        except tk.TclError: pass
        st.configure("TFrame", background=BG); st.configure("TLabel", background=BG, foreground=FG)
        st.configure("M.TLabel", background=BG, foreground=MUTED)
        st.configure("H.TLabel", background=BG, foreground=FG, font=("sans-serif", 13, "bold"))
        st.configure("F.TLabel", background=BG, foreground="#e8875b", font=("sans-serif", 11, "bold"))
        st.configure("Ok.TLabel", background=BG, foreground="#3dd68c", font=("sans-serif", 11, "bold"))
        outer = ttk.Frame(root); outer.pack(fill="both", expand=True)
        side = tk.Frame(outer, bg=SIDE, width=168); side.pack(side="left", fill="y"); side.pack_propagate(False)
        tk.Label(side, text="pfy", bg=SIDE, fg=FG, font=("sans-serif", 16, "bold")).pack(anchor="w", padx=14, pady=(14, 8))
        self.nav = {}
        for k, lab in (("loop","Loop"),("engine","Engine"),("stage","Stage"),("attach","Attach"),("tools","Tools"),("org","Org")):
            b = tk.Button(side, text=lab, bg=SIDE, fg=FG, bd=0, highlightthickness=0, anchor="w", padx=14, pady=8,
                          command=lambda x=k: self.set_view(x))
            b.pack(fill="x"); self.nav[k] = b
        self.nav["org"].pack_forget()
        right = ttk.Frame(outer); right.pack(side="left", fill="both", expand=True)
        head = ttk.Frame(right); head.pack(fill="x", padx=12, pady=(8, 2))
        ttk.Label(head, text="pfy", style="H.TLabel").pack(side="left")
        self.meta = ttk.Label(head, text="polling…", style="M.TLabel"); self.meta.pack(side="left", padx=12)
        self.fail = ttk.Label(right, text="", style="F.TLabel"); self.fail.pack(anchor="w", padx=12, pady=(4,0))
        self.body = ttk.Label(right, text="", justify="left", wraplength=1040); self.body.pack(anchor="w", padx=12, pady=8)
        self.acts = ttk.Frame(right); self.acts.pack(fill="x", padx=12, pady=6)
        self.bgrok = ttk.Button(self.acts, text="Attach grok", command=lambda: self.attach("grok"))
        self.bopen = ttk.Button(self.acts, text="Attach opencode", command=lambda: self.attach("opencode"))
        self.bhermes = ttk.Button(self.acts, text="Attach hermes", command=lambda: self.attach("hermes"))
        self.bcodex = ttk.Button(self.acts, text="Attach codex", command=lambda: self.attach("codex"))
        self.bclaude = ttk.Button(self.acts, text="Attach claude", command=lambda: self.attach("claude"))
        self.bgab = ttk.Button(self.acts, text="Attach gab", command=lambda: self.attach("gab"))
        self.bbare = ttk.Button(self.acts, text="bare", command=lambda: self.set_mode("bare"))
        self.borch = ttk.Button(self.acts, text="orchestration", command=lambda: self.set_mode("orchestration"))
        self.bgraph = ttk.Button(self.acts, text="code-graph", command=lambda: self.set_mode("code-graph"))
        self.bsi = ttk.Button(self.acts, text="Space Invaders", command=self.space_invaders)
        self.brefresh = ttk.Button(self.acts, text="Refresh status", command=self.refresh_now)
        self.bcopy = ttk.Button(self.acts, text="Copy stub one-liner", command=self.copy_stub)
        self.bstage = ttk.Button(self.acts, text="Run stage", command=self.run_stage)
        self.benv = ttk.Button(self.acts, text="Launch env", command=self.launch_env)
        self.bpull = ttk.Button(self.acts, text="Pull", command=self.pull_model)
        self.btest = ttk.Button(self.acts, text="Test model", command=self.test_model)
        self.tool_btns = {}
        for tid, lab in (("one-shot","one-shot"),("investigate","investigate"),("agent-loops","agent-loops"),("hermes-feedback","hermes-feedback"),("mcp","mcp"),("write-guard","write-guard"),("extra-tools","extra tools")):
            self.tool_btns[tid] = ttk.Button(self.acts, text=lab, command=lambda x=tid: self.toggle_tool(x))
        self.toolst = ttk.Label(self.acts, text="", style="M.TLabel")
        self.pullname = ttk.Entry(self.acts, width=22)
        self.sst = ttk.Label(self.acts, text="", style="M.TLabel")
        self.est = ttk.Label(self.acts, text="", style="M.TLabel")
        self.pst = ttk.Label(self.acts, text="", style="M.TLabel")
        self.rst = ttk.Label(self.acts, text="", style="M.TLabel")
        self.tst = ttk.Label(self.acts, text="", style="M.TLabel")
        self.ast = ttk.Label(self.acts, text="", style="Ok.TLabel")
        self.cst = ttk.Label(self.acts, text="", style="M.TLabel")
        self.sist = ttk.Label(self.acts, text="", style="M.TLabel")
        self.bsiopen = ttk.Button(self.acts, text="Open game", command=self.open_si_game)
        self.bsifold = ttk.Button(self.acts, text="Open folder", command=self.open_si_folder)
        self.bsitask = ttk.Button(self.acts, text="Copy TASK", command=self.copy_si_task)
        self.bcopyep = ttk.Button(self.acts, text="Copy endpoint", command=self.copy_endpoint)
        self.bcopyst = ttk.Button(self.acts, text="Copy ./pfy status", command=self.copy_pfy_status)
        self.siabs = ttk.Label(self.acts, text="", style="M.TLabel")
        self.sirel = ttk.Label(self.acts, text="", style="M.TLabel")
        self.sitask = ttk.Label(self.acts, text="", style="M.TLabel")
        self.ewhat = ttk.Label(self.acts, text="", style="M.TLabel")
        self.siopenst = ttk.Label(self.acts, text="", style="M.TLabel")
        self._last_env = {}
        self._last_si = {}
        self._session_reach = ""
        self._attach_mode = "bare"
        self.breco = ttk.Button(self.acts, text="Recommend", command=self.recommend_models)
        self.btry = ttk.Button(self.acts, text="Try recommended", command=self.try_recommended)
        self.recst = ttk.Label(self.acts, text="", style="M.TLabel")
        self.tryst = ttk.Label(self.acts, text="", style="M.TLabel")
        self.catname = ttk.Entry(self.acts, width=22)
        self.bask = ttk.Button(self.acts, text="Ask TUI implement", command=self.catalog_ask)
        self.bqueue = ttk.Button(self.acts, text="Queue for org", command=self.catalog_queue)
        self.bcatcopy = ttk.Button(self.acts, text="Copy prompt", command=self.copy_catalog_prompt)
        self.catst = ttk.Label(self.acts, text="", style="M.TLabel")
        self.bsess = ttk.Button(self.acts, text="Launch session", command=self.launch_session)
        self.bbulk = ttk.Button(self.acts, text="Bulk — stay on this machine", command=lambda: self.set_loop_task("bulk"))
        self.binteractive = ttk.Button(self.acts, text="Interactive — local first", command=lambda: self.set_loop_task("interactive"))
        self.bhard = ttk.Button(self.acts, text="Hard — allow cloud", command=lambda: self.set_loop_task("hard"))
        self.bagents = {}
        for aid, label in (("grok", "grok"), ("opencode", "OpenCode"), ("hermes", "Hermes"), ("codex", "Codex"), ("claude", "Claude"), ("gab", "Gab")):
            self.bagents[aid] = ttk.Button(self.acts, text=label, command=lambda a=aid: self.set_loop_agent(a))
        self.blocal = ttk.Button(self.acts, text="local", command=lambda: self.wizard_step("lane", "local"))
        self.bcloud = ttk.Button(self.acts, text="cloud/subscription", command=lambda: self.wizard_step("lane", "cloud/subscription"))
        self.bofree = ttk.Button(self.acts, text="OpenCode free", command=lambda: self.wizard_step("lane", "opencode-free"))
        self.bcatalog = ttk.Button(self.acts, text="catalog", command=lambda: self.wizard_step("toolsets", "catalog"))
        self.bhopenc = ttk.Button(self.acts, text="OpenCode", command=lambda: self.wizard_step("harness", "opencode"))
        self.bhgrok = ttk.Button(self.acts, text="Grok", command=lambda: self.wizard_step("harness", "grok"))
        self.bhhermes = ttk.Button(self.acts, text="Hermes", command=lambda: self.wizard_step("harness", "hermes"))
        self.bhcodex = ttk.Button(self.acts, text="Codex", command=lambda: self.wizard_step("harness", "codex"))
        self.bhclaude = ttk.Button(self.acts, text="Claude", command=lambda: self.wizard_step("harness", "claude"))
        self.bhgab = ttk.Button(self.acts, text="Gab", command=lambda: self.wizard_step("harness", "gab"))
        self.bdecoff = ttk.Button(self.acts, text="decision off", command=lambda: self.wizard_step("decision", "off"))
        self.bdeccua = ttk.Button(self.acts, text="CUA-S1-FORMS", command=lambda: self.wizard_step("decision", "cua-s1-forms"))
        self.bdects = ttk.Button(self.acts, text="TypeSafe", command=lambda: self.wizard_step("decision", "typesafe"))
        self.bdecmj = ttk.Button(self.acts, text="mini-jev", command=lambda: self.wizard_step("decision", "mini-jev"))
        self.chips = ttk.Frame(right); self.chips.pack(fill="both", expand=True, padx=12, pady=(0,10))

    def set_view(self, k):
        self.view = k; self.render()

    def paint_attach(self, text, fail=False):
        self.msg = text
        self.ast.configure(text=text, style="F.TLabel" if fail else "Ok.TLabel")

    def set_mode(self, mode):
        mode = (mode or "bare").strip() or "bare"
        self._attach_mode = mode
        if self.board and hasattr(self.board, "set_attach_mode"):
            try:
                res = self.board.set_attach_mode(mode)
            except Exception as e:
                res = {"ok": False, "error": str(e), "copy": "FAIL mode"}
            if res.get("ok"):
                self._attach_mode = res.get("mode") or mode
                self.paint_attach("using: "+self._attach_mode, False)
            else:
                nxt = res.get("next_step") or "select bare | orchestration | code-graph on Attach"
                detail = res.get("copy") or res.get("error") or "mode"
                self.paint_attach("FAIL mode — %s · %s" % (detail, nxt), True)
        else:
            self.paint_attach("using: "+self._attach_mode, False)
        self.render()

    def set_loop_agent(self, agent):
        self.paint_attach("agent "+agent+"…", False)
        def work():
            try:
                if self.board and hasattr(self.board, "set_loop_agent"):
                    res = self.board.set_loop_agent(agent)
                else:
                    res = {"ok": True, "copy": "READY agent %s" % agent, "agent": agent}
            except Exception as e:
                res = {"ok": False, "copy": "FAIL agent", "error": str(e)}
            self.root.after(0, lambda r=res: self.done_loop_cmd(r))
        threading.Thread(target=work, daemon=True).start()

    def set_loop_task(self, task):
        self.paint_attach("task "+task+"…", False)
        def work():
            try:
                if self.board and hasattr(self.board, "set_loop_task"):
                    res = self.board.set_loop_task(task)
                else:
                    res = {"ok": True, "copy": "READY task %s" % task, "task": task}
            except Exception as e:
                res = {"ok": False, "copy": "FAIL task", "error": str(e)}
            self.root.after(0, lambda r=res: self.done_loop_cmd(r))
        threading.Thread(target=work, daemon=True).start()

    def toggle_loop_module(self, tid, on):
        self.paint_attach("module "+tid+"…", False)
        def work():
            try:
                if self.board and hasattr(self.board, "toggle_loop_module"):
                    res = self.board.toggle_loop_module(tid, bool(on))
                else:
                    res = {"ok": True, "copy": "READY module %s %s" % (tid, "on" if on else "off")}
            except Exception as e:
                res = {"ok": False, "copy": "FAIL module", "error": str(e)}
            self.root.after(0, lambda r=res: self.done_loop_cmd(r))
        threading.Thread(target=work, daemon=True).start()

    def done_loop_cmd(self, res):
        ok = bool(res.get("ok"))
        live = str(res.get("live") or "")
        fail = (not ok) and live != "STUB"
        self.paint_attach(res.get("copy") or ("READY" if ok else "FAIL"), fail)
        if self.board is None:
            self.render()
        else:
            self.refresh(user=True)

    def wizard_step(self, step, value=""):
        self.paint_attach("wizard "+step+"…", False)
        def work():
            try:
                if self.board and hasattr(self.board, "wizard_apply"):
                    res = self.board.wizard_apply(step, value)
                else:
                    res = {"ok": False, "copy": "FAIL wizard", "error": "no board"}
            except Exception as e:
                res = {"ok": False, "copy": "FAIL wizard", "error": str(e)}
            self.root.after(0, lambda r=res: self.done_wizard(r, step))
        threading.Thread(target=work, daemon=True).start()

    def done_wizard(self, res, step=""):
        skip = str((res or {}).get("live") or "").upper() == "SKIP" or bool((res or {}).get("skipped"))
        if res.get("ok"):
            if res.get("mode"):
                self._attach_mode = res.get("mode")
            self.paint_attach(res.get("copy") or ("READY "+step), False)
        else:
            nxt = res.get("next_step") or "Launch env or ./pfy up"
            detail = res.get("copy") or res.get("error") or "wizard"
            if nxt and nxt not in str(detail):
                detail = "%s · %s" % (detail, nxt)
            self.paint_attach(detail if skip else ("FAIL wizard — %s" % detail), not skip)
        self.refresh()

    def launch_session(self):
        self.paint_attach("Launch session…", False)
        def work():
            try:
                if self.board and hasattr(self.board, "launch_wizard_session"):
                    res = self.board.launch_wizard_session()
                else:
                    res = {"ok": False, "copy": "FAIL launch", "error": "no board", "next_step": "complete wizard review (runtime · lane · toolsets · harness)"}
            except Exception as e:
                res = {"ok": False, "copy": "FAIL launch", "error": str(e)}
            self.root.after(0, lambda r=res: self.done_launch_session(r))
        threading.Thread(target=work, daemon=True).start()

    def done_launch_session(self, res):
        reach = str((res or {}).get("session_reach") or "").strip()
        if reach:
            self._session_reach = reach
        skip = str((res or {}).get("live") or "").upper() == "SKIP" or bool((res or {}).get("skipped"))
        if res.get("ok") and res.get("usable") is not False:
            pid = res.get("pid")
            hid = res.get("id") or res.get("harness") or ""
            msg = res.get("copy") or ("attached " + hid)
            if pid and ("pid" not in msg):
                msg += " pid %s" % pid
            if reach and reach not in msg:
                msg += " · " + reach
            self.paint_attach(msg, False)
        else:
            nxt = res.get("next_step") or "complete wizard review (runtime · lane · toolsets · harness)"
            detail = res.get("error") or res.get("copy") or "launch"
            if nxt and nxt not in str(detail):
                detail = "%s · %s" % (detail, nxt)
            self.paint_attach(detail if skip else ("FAIL Launch session — %s" % detail), not skip)
            if not reach:
                self._session_reach = "FAIL"
        self.refresh()

    def attach(self, hid):
        self.paint_attach("attaching "+hid+"…", False)
        mode = self._attach_mode or "bare"
        def work():
            try: snap = self.board.snapshot() if self.board else {}
            except Exception as e: snap, err = {}, str(e)
            else: err = ""
            active = str(snap.get("active") or "")
            if active in BLOCKED:
                res = {"ok": False, "copy": GROK_USE, "error": f"{active} is active — no grok/opencode fallback"}
            else:
                try:
                    if self.board:
                        res = self.board.start_sidecar(hid, mode=mode)
                    else:
                        res = {"ok": False, "copy": GROK_USE, "error": "no board"}
                except TypeError:
                    try: res = self.board.start_sidecar(hid) if self.board else {"ok": False, "copy": GROK_USE, "error": "no board"}
                    except Exception as e: res = {"ok": False, "copy": GROK_USE, "error": str(e) or err}
                except Exception as e: res = {"ok": False, "copy": GROK_USE, "error": str(e) or err}
            self.root.after(0, lambda: self.done(hid, res))
        threading.Thread(target=work, daemon=True).start()

    def done(self, hid, res):
        reach = str((res or {}).get("session_reach") or "").strip()
        if reach:
            self._session_reach = reach
        if res.get("ok") and res.get("usable") is not False:
            pid = res.get("pid")
            kind = "monitor" if res.get("role") == "monitor" else hid
            msg = f"attached {kind}" + (f" pid {pid}" if pid else "")
            if reach:
                msg += " · " + reach
            self.paint_attach(msg, False)
        else:
            nxt = res.get("next_step") or ""
            detail = res.get("error") or res.get("copy") or GROK_USE
            if nxt and nxt not in str(detail):
                detail = f"{detail} · {nxt}"
            self.paint_attach(f"FAIL Attach {hid} — {detail}", True)
            if hid in ("opencode", "hermes", "grok", "codex", "claude", "claude-code") and not reach:
                self._session_reach = "FAIL"
        self.refresh()


    def paint_si(self, text, fail=False):
        self.msg = text
        style = "F.TLabel" if fail else "Ok.TLabel"
        self.sist.configure(text=text, style=style)
        self.ast.configure(text=text, style=style)

    def space_invaders(self):
        self.paint_si("Space Invaders…", False)
        def work():
            try:
                res = self.board.run_space_invaders() if self.board else {"ok": False, "copy": "FAIL Space Invaders · no board", "error": "no board"}
            except Exception as e:
                res = {"ok": False, "copy": "FAIL Space Invaders", "error": str(e)}
            self.root.after(0, lambda: self.done_si(res))
        threading.Thread(target=work, daemon=True).start()

    def done_si(self, res):
        self._last_si = res or {}
        if res.get("ok"):
            self.paint_si(res.get("copy") or ("PASS Space Invaders · " + str(res.get("path") or "")), False)
            self.siabs.configure(text="abs " + str(res.get("abs_path") or ""))
            self.sirel.configure(text="rel " + str(res.get("rel") or res.get("path") or ""))
            preview = str(res.get("task_text") or res.get("task_md") or "")
            if len(preview) > 240:
                preview = preview[:240] + "…"
            self.sitask.configure(text=preview)
        else:
            self.paint_si(res.get("copy") or ("FAIL Space Invaders · " + str(res.get("error") or "")), True)
        self.refresh(user=True)

    def paint_copy(self, text, fail=False):
        self.msg = text
        style = "F.TLabel" if fail else "Ok.TLabel"
        self.cst.configure(text=text, style=style)
        self.ast.configure(text=text, style=style)

    def stub_line(self):
        s = self.snap or {}
        if s.get("active_stub") or str(s.get("active") or "") in BLOCKED:
            return s.get("blocked_copy") or GROK_USE
        chips = s.get("chips") or []
        active_id = s.get("active")
        active = next((c for c in chips if c.get("id") == active_id), None)
        stubish = ("stub", "detected-stub", "missing")
        def is_stubish(c):
            return honest(c.get("live")) in stubish
        c = active if active and is_stubish(active) else next(
            (x for x in chips if is_stubish(x) and (x.get("one_liner") or x.get("startable") is False)),
            None,
        )
        if not c:
            return ""
        return c.get("one_liner") or ("./pfy start " + str(c.get("id") or ""))

    def copy_stub(self):
        self.paint_copy("copying…", False)
        line = self.stub_line()
        if not line:
            self.paint_copy("FAIL no stub one-liner", True)
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(line)
            try:
                self.root.update_idletasks()
            except Exception:
                pass
            self.paint_copy("PASS copied", False)
        except Exception:
            self.paint_copy("FAIL clipboard — select the one-liner", True)

    def _clip(self, text, paint, ok_msg, fail_msg):
        if not text:
            paint(fail_msg, True)
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            try:
                self.root.update_idletasks()
            except Exception:
                pass
            paint(ok_msg, False)
        except Exception:
            paint(fail_msg, True)

    def paint_si_open(self, text, fail=False):
        self.siopenst.configure(text=text, style="F.TLabel" if fail else "Ok.TLabel")
        self.msg = text

    def open_si_game(self):
        self.paint_si_open("opening game…", False)
        def work():
            try:
                res = self.board.open_space_invaders_game() if self.board else {"ok": False, "copy": "FAIL Open game · no board", "error": "no board"}
            except Exception as e:
                res = {"ok": False, "copy": "FAIL Open game", "error": str(e)}
            self.root.after(0, lambda: self.done_si_open(res))
        threading.Thread(target=work, daemon=True).start()

    def done_si_open(self, res):
        cur = dict(getattr(self, "_last_si", {}) or {})
        cur.update(res or {})
        self._last_si = cur
        if res.get("ok"):
            self.paint_si_open(res.get("copy") or "PASS Open game", False)
            if res.get("abs_path"):
                self.siabs.configure(text="abs " + str(res.get("abs_path") or ""))
            if res.get("rel") or res.get("path"):
                self.sirel.configure(text="rel " + str(res.get("rel") or res.get("path") or ""))
        else:
            self.paint_si_open(res.get("copy") or ("FAIL Open game · " + str(res.get("error") or "")), True)
        self.refresh(user=True)

    def open_si_folder(self):
        self.paint_si_open("opening folder…", False)
        def work():
            try:
                res = self.board.open_space_invaders_folder() if self.board else {"ok": False, "copy": "FAIL Open folder · no board", "error": "no board"}
            except Exception as e:
                res = {"ok": False, "copy": "FAIL Open folder", "error": str(e)}
            self.root.after(0, lambda: self.done_si_open(res))
        threading.Thread(target=work, daemon=True).start()

    def copy_si_task(self):
        self.paint_si_open("copying TASK…", False)
        def work():
            try:
                res = self.board.space_invaders_task() if self.board else {"ok": False, "copy": "FAIL Copy TASK · no board", "error": "no board", "task_text": ""}
            except Exception as e:
                res = {"ok": False, "copy": "FAIL Copy TASK", "error": str(e), "task_text": ""}
            self.root.after(0, lambda: self.done_si_task(res))
        threading.Thread(target=work, daemon=True).start()

    def done_si_task(self, res):
        text = str((res or {}).get("task_text") or (res or {}).get("value") or "")
        preview = text if len(text) <= 240 else text[:240] + "…"
        cur = dict(getattr(self, "_last_si", {}) or {})
        cur.update(res or {})
        if text:
            cur["task_text"] = text
        self._last_si = cur
        if preview:
            self.sitask.configure(text=preview)
        if not (res or {}).get("ok"):
            self.paint_si_open((res or {}).get("copy") or "FAIL Copy TASK", True)
            self.refresh(user=True)
            return
        self._clip(text, self.paint_si_open, res.get("copy") or "PASS Copy TASK", "FAIL clipboard — select TASK")
        self.refresh(user=True)

    def copy_endpoint(self):
        # #175: FreeToken-first live base — not Launch env pin
        nxt = "Launch env or ./pfy up"
        val = ""
        try:
            if self.board is not None and hasattr(self.board, "live_openai_base"):
                base, _det = self.board.live_openai_base()
                val = str(base or "").strip()
        except Exception:
            val = ""
        if not val:
            s = getattr(self, "snap", None) or {}
            u = s.get("usage") if isinstance(s.get("usage"), dict) else {}
            if u and u.get("ok") is False:
                nxt = str(u.get("next_step") or nxt)
                self.paint_env("FAIL copy · next: " + nxt, True)
                return
            if u and u.get("ok") is not False:
                val = str(u.get("endpoint") or "").strip()
            if not val or val == "(none)":
                d = s.get("detector") or {}
                sr = s.get("status_runtime") or {}
                st = str(d.get("status") or sr.get("status") or "").strip().lower()
                base = str(d.get("base_url") or sr.get("base_url") or sr.get("endpoint") or "").strip()
                if st == "ready" and base and base != "(none)":
                    val = base
                    if not val.rstrip("/").endswith("/v1"):
                        val = val.rstrip("/") + "/v1"
        if not val or val == "(none)":
            self.paint_env("FAIL copy · next: " + nxt, True)
            return
        self._clip(val, self.paint_env, "PASS copied", "FAIL copy")

    def copy_pfy_status(self):
        res = self._last_env or {}
        val = "./pfy status"
        for s in (res.get("next_steps") or []):
            if (s or {}).get("id") == "status" and s.get("value"):
                val = str(s.get("value"))
                break
        self._clip(val, self.paint_env, "PASS Copy ./pfy status", "FAIL clipboard — select status")

    def paint_stage(self, text, fail=False):
        self.sst.configure(text=text, style="F.TLabel" if fail else "Ok.TLabel")

    def paint_eval(self, text, fail=False):
        self.tst.configure(text=text, style="F.TLabel" if fail else "Ok.TLabel")

    def test_model(self):
        self.paint_eval("testing…", False)
        self.meta.configure(text="refreshing…")
        try:
            self.btest.configure(state="disabled")
        except Exception:
            pass
        def work():
            try:
                if self.board is None:
                    res = {"ok": False, "copy": "FAIL eval", "error": "no board"}
                else:
                    res = self.board.test_model()
            except Exception as e:
                res = {"ok": False, "copy": "FAIL eval", "error": str(e)}
            self.root.after(0, lambda r=res: self.done_eval(r))
        threading.Thread(target=work, daemon=True).start()

    def done_eval(self, res):
        try:
            self.btest.configure(state="normal")
        except Exception:
            pass
        if res.get("ok"):
            copy = res.get("copy") or "PASS eval"
            if str(copy).startswith("SKIP"):
                self.tst.configure(text=copy, style="M.TLabel")
            elif str(copy).startswith("FAIL"):
                self.paint_eval(copy, True)
            else:
                self.paint_eval(copy, False)
        else:
            self.paint_eval("FAIL " + (res.get("copy") or res.get("error") or "eval"), True)
        self.refresh(user=True)

    def paint_pull(self, text, fail=False):
        self.pst.configure(text=text, style="F.TLabel" if fail else "Ok.TLabel")

    def pull_model(self):
        try:
            name = (self.pullname.get() or "").strip()
        except Exception:
            name = ""
        if not name:
            self.paint_pull("FAIL pull", True)
            return
        self.paint_pull("pulling…", False)
        self.meta.configure(text="refreshing…")
        try:
            self.bpull.configure(state="disabled")
        except Exception:
            pass
        def work():
            try:
                if self.board is None:
                    res = {"ok": False, "copy": "FAIL pull", "error": "no board"}
                else:
                    res = self.board.pull_model(name)
            except Exception as e:
                res = {"ok": False, "copy": "FAIL pull", "error": str(e)}
            self.root.after(0, lambda r=res: self.done_pull(r))
        threading.Thread(target=work, daemon=True).start()

    def done_pull(self, res):
        try:
            self.bpull.configure(state="normal")
        except Exception:
            pass
        # #173: no false success — FAIL paints fail; SKIP muted; PASS ok
        if res.get("ok"):
            copy = res.get("copy") or "PASS pull"
            if str(copy).startswith("SKIP"):
                self.pst.configure(text=copy, style="M.TLabel")
            elif str(copy).startswith("FAIL"):
                self.paint_pull(copy, True)
            else:
                self.paint_pull(copy, False)
        else:
            nxt = res.get("next_step") or "Launch env or ./pfy up"
            copy = res.get("copy") or res.get("error") or "pull"
            msg = str(copy)
            if "Launch env" not in msg and "./pfy up" not in msg:
                msg = msg + " · next: " + nxt
            self.paint_pull("FAIL " + msg if not msg.startswith("FAIL") else msg, True)
        self.refresh(user=True)

    def paint_recommend(self, text, fail=False):
        self.recst.configure(text=text, style="F.TLabel" if fail else "Ok.TLabel")

    def paint_try(self, text, fail=False):
        self.tryst.configure(text=text, style="F.TLabel" if fail else "Ok.TLabel")

    def recommend_models(self):
        self.paint_recommend("ranking…", False)
        self.meta.configure(text="refreshing…")
        try:
            self.breco.configure(state="disabled")
        except Exception:
            pass
        def work():
            try:
                if self.board is None:
                    res = {"ok": False, "copy": "FAIL recommend", "error": "no board", "ranked": []}
                else:
                    res = self.board.recommend_models()
            except Exception as e:
                res = {"ok": False, "copy": "FAIL recommend", "error": str(e), "ranked": []}
            self.root.after(0, lambda r=res: self.done_recommend(r))
        threading.Thread(target=work, daemon=True).start()

    def done_recommend(self, res):
        try:
            self.breco.configure(state="normal")
        except Exception:
            pass
        if res.get("ok"):
            copy = res.get("copy") or "PASS recommend"
            if res.get("honesty") or (res.get("gab_sync") or {}).get("honesty"):
                copy = copy + " · " + (res.get("honesty") or res["gab_sync"]["honesty"])
            self.paint_recommend(copy, False)
        else:
            nxt = res.get("next_step") or "Launch env or ./pfy up"
            copy = res.get("copy") or res.get("error") or "recommend"
            msg = str(copy)
            if nxt not in msg:
                msg = msg + " · next: " + nxt
            self.paint_recommend("FAIL " + msg if not msg.startswith("FAIL") else msg, True)
        self.refresh(user=True)

    def try_recommended(self):
        try:
            name = (self.pullname.get() or "").strip()
        except Exception:
            name = ""
        self.paint_try("trying…", False)
        self.meta.configure(text="refreshing…")
        try:
            self.btry.configure(state="disabled")
        except Exception:
            pass
        def work():
            try:
                if self.board is None:
                    res = {"ok": False, "copy": "FAIL try", "error": "no board"}
                else:
                    res = self.board.try_recommended_model(name)
            except Exception as e:
                res = {"ok": False, "copy": "FAIL try", "error": str(e)}
            self.root.after(0, lambda r=res: self.done_try(r))
        threading.Thread(target=work, daemon=True).start()

    def done_try(self, res):
        try:
            self.btry.configure(state="normal")
        except Exception:
            pass
        if res.get("ok"):
            self.paint_try(res.get("copy") or "PASS try", False)
        else:
            nxt = res.get("next_step") or "Launch env or ./pfy up (engine pin) · Attach re-probe · TUI reload"
            copy = res.get("copy") or res.get("error") or "try"
            msg = str(copy)
            if "engine pin" not in msg.lower() and nxt not in msg:
                msg = msg + " · next: " + nxt
            self.paint_try("FAIL " + msg if not msg.startswith("FAIL") else msg, True)
        self.refresh(user=True)

    def paint_env(self, text, fail=False):
        self.est.configure(text=text, style="F.TLabel" if fail else "Ok.TLabel")

    def launch_env(self):
        self.paint_env("launching env…", False)
        self.meta.configure(text="refreshing…")
        try:
            self.benv.configure(state="disabled")
        except Exception:
            pass
        def work():
            try:
                if self.board is None:
                    res = {"ok": False, "copy": "FAIL env", "error": "no board"}
                else:
                    res = self.board.launch_env()
            except Exception as e:
                res = {"ok": False, "copy": "FAIL env", "error": str(e)}
            self.root.after(0, lambda r=res: self.done_env(r))
        threading.Thread(target=work, daemon=True).start()

    def done_env(self, res):
        try:
            self.benv.configure(state="normal")
        except Exception:
            pass
        self._last_env = res or {}
        reach = str((res or {}).get("session_reach") or "").strip()
        if reach:
            self._session_reach = reach
        what = str((res or {}).get("what") or "")
        if what:
            self.ewhat.configure(text=what)
        if res.get("ok"):
            copy = res.get("copy") or ("SKIP env" if str(res.get("live") or "") == "SKIP" else "PASS env")
            if str(copy).startswith("SKIP"):
                self.est.configure(text=copy, style="M.TLabel")
            else:
                self.paint_env(copy, False)
        else:
            self.paint_env("FAIL " + (res.get("copy") or res.get("error") or "env"), True)
        self.refresh(user=True)

    def run_stage(self):
        self.paint_stage("running env-stage…", False)
        self.meta.configure(text="refreshing…")
        try:
            self.bstage.configure(state="disabled")
        except Exception:
            pass
        def work():
            try:
                if self.board is None:
                    res = {"ok": False, "copy": "FAIL env-stage", "error": "no board"}
                else:
                    res = self.board.run_stage()
            except Exception as e:
                res = {"ok": False, "copy": "FAIL env-stage", "error": str(e)}
            self.root.after(0, lambda r=res: self.done_stage(r))
        threading.Thread(target=work, daemon=True).start()

    def done_stage(self, res):
        try:
            self.bstage.configure(state="normal")
        except Exception:
            pass
        if res.get("ok"):
            copy = res.get("copy") or "PASS env-stage"
            if str(copy).startswith("SKIP"):
                self.sst.configure(text=copy, style="M.TLabel")
            else:
                self.paint_stage(copy, False)
        else:
            self.paint_stage("FAIL " + (res.get("copy") or res.get("error") or "env-stage"), True)
        self.refresh(user=True)

    def paint_refresh(self, text, fail=False, skip=False):
        style = "M.TLabel" if skip else ("F.TLabel" if fail else "Ok.TLabel")
        self.rst.configure(text=text, style=style)

    def refresh_now(self):
        if self.busy:
            self.paint_refresh("SKIP refresh", fail=False, skip=True)
        else:
            self.paint_refresh("refreshing…", False)
        self.refresh(user=True)

    def refresh(self, user=False):
        if self.board is None:
            if user:
                self.meta.configure(text="FAIL refresh")
                self.fail.configure(text="FAIL  " + GROK_USE)
                self.paint_refresh("FAIL refresh", True)
            return
        if self.busy:
            if user:
                self.pending_user = True
                self.meta.configure(text="refreshing…")
                try:
                    self.brefresh.configure(state="disabled")
                except Exception:
                    pass
            return
        self.busy = True
        if user:
            self.meta.configure(text="refreshing…")
            self.paint_refresh("refreshing…", False)
            try:
                self.brefresh.configure(state="disabled")
            except Exception:
                pass
        def work():
            try:
                snap = self.board.snapshot()
            except Exception as e:
                snap = {"error": str(e)}
            # User Refresh: force /usage parity with HTML postRefreshUsage (#165)
            if user and isinstance(snap, dict) and not snap.get("error"):
                try:
                    uinfo = self.board.local_usage_info()
                    if isinstance(uinfo, dict):
                        snap = dict(snap)
                        snap["usage"] = uinfo
                        sr = dict(snap.get("status_runtime") or {})
                        if uinfo.get("engine"):
                            sr["engine"] = uinfo.get("engine")
                        if uinfo.get("endpoint"):
                            sr["endpoint"] = uinfo.get("endpoint")
                            sr["base_url"] = uinfo.get("endpoint")
                        sr["tok_path"] = uinfo.get("tok_path") or "SKIP"
                        sr["vram"] = uinfo.get("vram") or "SKIP"
                        snap["status_runtime"] = sr
                        if uinfo.get("models"):
                            snap["models"] = list(uinfo.get("models") or [])
                        if not uinfo.get("ok"):
                            snap["engine_live"] = "missing"
                except Exception:
                    pass
            self.root.after(0, lambda s=snap, u=user: self.apply(s, user=u))
        threading.Thread(target=work, daemon=True).start()

    def apply(self, s, user=False):
        pending = self.pending_user
        self.pending_user = False
        self.busy = False
        try:
            self.brefresh.configure(state="normal")
        except Exception:
            pass
        self.snap = s or {}
        self.render()
        if user:
            err = self.snap.get("error") and not (self.snap.get("chips") or [])
            if err:
                self.paint_refresh("FAIL refresh", True)
                self.meta.configure(text="FAIL refresh")
            else:
                ts = self.snap.get("ts") or ""
                host = self.snap.get("host") or ""
                if ts:
                    line = "PASS refresh · " + " · ".join(x for x in (host, ts) if x)
                    self.paint_refresh(line, False)
                    self.meta.configure(text=" · ".join(x for x in (host, self.snap.get("profile") or "", ts) if x))
                else:
                    self.paint_refresh("PASS refresh · refreshed", False)
                    cur = str(self.meta.cget("text") or "")
                    if "refreshed" not in cur:
                        self.meta.configure(text=(cur + " · refreshed").strip(" ·"))
        if pending:
            self.refresh(user=True)

    def paint_tools(self, text, fail=False):
        self.toolst.configure(text=text, style="F.TLabel" if fail else "Ok.TLabel")
        self.msg = text

    def tool_on(self, tid):
        tools = (self.snap or {}).get("tools") or {}
        if tid == "mcp":
            return bool(tools.get("mcp"))
        if tid == "write-guard":
            return bool(tools.get("write_guard"))
        if tid == "extra-tools":
            return (tools.get("tools_mode") or "") == "local_tools"
        return bool((tools.get("skills") or {}).get(tid))

    def toggle_tool(self, tid):
        want = not self.tool_on(tid)
        self.paint_tools("toggling…", False)
        def work():
            try:
                if self.board is None:
                    res = {"ok": False, "copy": "FAIL tools", "error": "no board"}
                else:
                    res = self.board.set_tool(tid, want)
            except Exception as e:
                res = {"ok": False, "copy": "FAIL tools", "error": str(e)}
            self.root.after(0, lambda r=res: self.done_tool(r))
        threading.Thread(target=work, daemon=True).start()

    def done_tool(self, res):
        if res.get("ok"):
            self.paint_tools(res.get("copy") or "PASS tools", False)
        else:
            self.paint_tools("FAIL " + (res.get("copy") or res.get("error") or "tools"), True)
        self.refresh(user=True)

    def paint_catalog(self, text, fail=False):
        self.catst.configure(text=text, style="F.TLabel" if fail else "Ok.TLabel")
        self.msg = text

    def catalog_ask(self):
        try:
            name = (self.catname.get() or "").strip()
        except Exception:
            name = ""
        self.paint_catalog("asking…", False)
        def work():
            try:
                if self.board is None:
                    res = {"ok": False, "copy": "FAIL ask", "error": "no board"}
                else:
                    res = self.board.catalog_ask(name)
            except Exception as e:
                res = {"ok": False, "copy": "FAIL ask", "error": str(e)}
            self.root.after(0, lambda r=res: self.done_catalog(r, "ask"))
        threading.Thread(target=work, daemon=True).start()

    def catalog_queue(self):
        try:
            name = (self.catname.get() or "").strip()
        except Exception:
            name = ""
        self.paint_catalog("queueing…", False)
        def work():
            try:
                if self.board is None:
                    res = {"ok": False, "copy": "FAIL queue", "error": "no board"}
                else:
                    res = self.board.catalog_queue(name)
            except Exception as e:
                res = {"ok": False, "copy": "FAIL queue", "error": str(e)}
            self.root.after(0, lambda r=res: self.done_catalog(r, "queue"))
        threading.Thread(target=work, daemon=True).start()

    def done_catalog(self, res, kind="ask"):
        if res.get("ok"):
            self.paint_catalog(res.get("copy") or ("PASS " + kind), False)
            prompt = res.get("prompt") or ""
            if prompt:
                self._catalog_prompt = prompt
        else:
            nxt = res.get("next_step") or ""
            copy = res.get("copy") or res.get("error") or kind
            msg = str(copy)
            if nxt and nxt not in msg:
                msg = msg + " · next: " + nxt
            live = str(res.get("live") or "")
            if live == "SKIP" or msg.startswith("SKIP"):
                self.catst.configure(text=msg if msg.startswith("SKIP") else ("SKIP " + msg), style="M.TLabel")
                self.msg = msg
            else:
                self.paint_catalog("FAIL " + msg if not (msg.startswith("FAIL") or msg.startswith("SKIP")) else msg, True)
        self.refresh(user=True)

    def copy_catalog_prompt(self):
        prompt = str(getattr(self, "_catalog_prompt", "") or (self.snap or {}).get("catalog_prompt") or "")
        if not prompt:
            self.paint_catalog("FAIL no prompt — Ask TUI implement first", True)
            return
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(prompt)
            self.paint_catalog("PASS copied", False)
        except Exception:
            self.paint_catalog("FAIL clipboard — select the prompt", True)

    def pack_acts(self, names):
        forget = [self.bgrok, self.bopen, self.bhermes, self.bcodex, self.bclaude, self.bgab, self.bbare, self.borch, self.bgraph, self.bsi, self.bsiopen, self.bsifold, self.bsitask, self.bcopyep, self.bcopyst, self.brefresh, self.bcopy, self.bstage, self.benv, self.bpull, self.btest, self.breco, self.btry, self.pullname, self.sst, self.est, self.pst, self.rst, self.tst, self.ast, self.cst, self.sist, self.siabs, self.sirel, self.sitask, self.ewhat, self.siopenst, self.toolst, self.recst, self.tryst, self.catname, self.bask, self.bqueue, self.bcatcopy, self.catst, self.bsess, self.bbulk, self.binteractive, self.bhard, self.blocal, self.bcloud, self.bofree, self.bcatalog, self.bhopenc, self.bhgrok, self.bhhermes, self.bhcodex, self.bhclaude, self.bhgab, self.bdecoff, self.bdeccua, self.bdects, self.bdecmj]
        forget.extend(self.tool_btns.values())
        forget.extend(self.bagents.values())
        for w in forget:
            try: w.pack_forget()
            except Exception: pass
        order = {
            "grok": self.bgrok, "open": self.bopen, "hermes": self.bhermes, "codex": self.bcodex, "claude": self.bclaude, "gab": self.bgab,
            "bare": self.bbare, "orch": self.borch, "graph": self.bgraph,
            "sess": self.bsess, "bulk": self.bbulk, "interactive": self.binteractive, "hard": self.bhard,
            "agrok": self.bagents["grok"], "aopen": self.bagents["opencode"], "ahermes": self.bagents["hermes"],
            "acodex": self.bagents["codex"], "aclaude": self.bagents["claude"], "agab": self.bagents["gab"],
            "local": self.blocal, "cloud": self.bcloud, "ofree": self.bofree, "catalog": self.bcatalog,
            "hopenc": self.bhopenc, "hgrok": self.bhgrok, "hhermes": self.bhhermes, "hcodex": self.bhcodex, "hclaude": self.bhclaude, "hgab": self.bhgab,
            "decoff": self.bdecoff, "deccua": self.bdeccua, "dects": self.bdects, "decmj": self.bdecmj,
            "si": self.bsi, "refresh": self.brefresh,
            "copy": self.bcopy, "stage": self.bstage, "env": self.benv,
            "pull": self.bpull, "pullname": self.pullname, "pst": self.pst,
            "test": self.btest, "tst": self.tst, "rst": self.rst,
            "reco": self.breco, "try": self.btry, "recst": self.recst, "tryst": self.tryst,
            "catname": self.catname, "ask": self.bask, "queue": self.bqueue, "catcopy": self.bcatcopy, "catst": self.catst,
            "sst": self.sst, "est": self.est, "ast": self.ast, "cst": self.cst, "sist": self.sist,
            "siopen": self.bsiopen, "sifold": self.bsifold, "sitask": self.bsitask,
            "copyep": self.bcopyep, "copyst": self.bcopyst,
            "siabs": self.siabs, "sirel": self.sirel, "sitxt": self.sitask, "ewhat": self.ewhat, "siopenst": self.siopenst,
        }
        for n in names:
            w = order[n]
            w.pack(side="left", padx=(0, 8))

    def render(self):
        tk = sys.modules["tkinter"]; s = self.snap
        if s.get("error") and not s.get("chips"):
            self.meta.configure(text=str(s.get("error"))); return
        self.meta.configure(text=" · ".join(x for x in (s.get("host") or "", s.get("profile") or "", s.get("ts") or "") if x))
        d, r = s.get("detector") or {}, s.get("status_runtime") or {}
        eng_live = honest(s.get("engine_live") or d.get("status"))
        engine = d.get("engine") or r.get("engine") or "none"
        chips = s.get("chips") or []
        grok = next((c for c in chips if c.get("id")=="grok"), {}) or {}
        tape = s.get("tape") or []
        stub = bool(s.get("active_stub")) or str(s.get("active") or "") in BLOCKED
        self.bgrok.configure(state="disabled" if stub else "normal")
        self.bopen.configure(state="disabled" if stub else "normal")
        self.bhermes.configure(state="disabled" if stub else "normal")
        self.bcodex.configure(state="disabled" if stub else "normal")
        self.bclaude.configure(state="disabled" if stub else "normal")
        self.bgab.configure(state="disabled" if stub else "normal")
        self.bsi.configure(state="disabled" if stub else "normal")
        self.fail.configure(text=(f"FAIL  {s.get('blocked_copy') or GROK_USE}") if stub else "")
        show_org = (not s.get("agent_lane_collapsed", True)) and bool(s.get("org_messages"))
        if show_org: self.nav["org"].pack(fill="x")
        else:
            self.nav["org"].pack_forget()
            if self.view == "org": self.view = "loop"
        for k,b in self.nav.items():
            b.configure(bg="#243041" if k==self.view else SIDE)
        attached = s.get("active") or "(none)"; verb = (s.get("last_verb") or {}).get("verb") or "(none)"
        if verb in ("env", "launch-env"):
            verb = "Launch env"
        if verb in ("launch", "launch-session"):
            verb = "Launch session"
        when = (s.get("last_verb") or {}).get("when") or ""
        pid = s.get("sidecar_pid") or ""
        att = attached + (f" pid {pid}" if pid else "")
        stage = next((t for t in tape if t.get("id")=="env-stage"), {}) or {}
        inf = next((t for t in tape if t.get("id")=="inference"), {}) or {}
        lives = [str(inf.get("live") or "SKIP").upper(), str(stage.get("live") or "SKIP").upper()]
        if "FAIL" in lives:
            env_live = "FAIL"
        elif "READY" in lives:
            env_live = "READY"
        else:
            env_live = "SKIP"
        if self.view == "loop":
            reach = str(s.get("session_reach") or "").strip() or "(none)"
            if reach == "(none)":
                reach = str(getattr(self, "_session_reach", "") or "").strip() or "(none)"
            txt = loop_text(s, env_live, att, reach, verb, when)
            what = str((getattr(self, "_last_env", {}) or {}).get("what") or "")
            if what:
                txt += "\nwhat       " + what
            if stub: txt += f"\nFAIL       {s.get('blocked_copy') or GROK_USE}"
            if self.msg: txt += "\n" + self.msg
            self.pack_acts(["bulk", "interactive", "hard", "agrok", "aopen", "ahermes", "acodex", "aclaude", "agab", "sess", "env", "copyep", "copyst", "est", "ast"])
        elif self.view == "engine":
            u = s.get("usage") if isinstance(s.get("usage"), dict) else {}
            sr = s.get("status_runtime") or {}
            # When usage present and not ok: do NOT fall back to detector (#165)
            if u and u.get("ok") is False:
                engine = u.get("engine") or "none"
                endpoint = u.get("endpoint") or "(none)"
                models = list(u.get("models") or [])
                tok = u.get("tok_path") or "SKIP"
                vram = u.get("vram") or "SKIP"
                live_show = "missing"
            else:
                engine = (u.get("engine") if u else None) or d.get("engine") or r.get("engine") or "none"
                endpoint = (u.get("endpoint") if u else None) or sr.get("endpoint") or sr.get("base_url") or d.get("base_url") or "(none)"
                if not endpoint:
                    endpoint = "(none)"
                models = (u.get("models") if u else None) or s.get("models") or []
                tok = (u.get("tok_path") if u else None) or sr.get("tok_path") or "SKIP"
                vram = (u.get("vram") if u else None) or sr.get("vram") or "SKIP"
                live_show = eng_live
            if not tok:
                tok = "SKIP"
            if not vram:
                vram = "SKIP"
            if not endpoint:
                endpoint = "(none)"
            mtxt = " · ".join(str(x) for x in models) if models else "(none)"
            txt = (
                f"ENGINE\nThis tab is the local model — not the coding session. Loop → Launch session opens that.\nengine     {engine}\nendpoint   {endpoint}\nlive       {live_show}"
                f"\ngrok       {honest(grok.get('live'))}\nmodels     {mtxt}"
                f"\ntok_path   {tok}\nvram       {vram}"
            )
            reco = list(s.get("recommend") or [])
            rtxt = " · ".join(str(x) for x in reco[:5]) if reco else "(none)"
            txt += f"\nrecommend  {rtxt}"
            txt += f"\nmiddleware {s.get('decision_core') or 'compact context · choose model/tool'}"
            txt += f"\nchip       {s.get('decision_honesty') or 'decision ≠ gab auto ≠ local'}"
            if s.get("recommend_ok") is False:
                rc = s.get("recommend_copy") or "FAIL recommend"
                rn = s.get("recommend_next") or "Launch env or ./pfy up"
                txt += f"\n{rc}"
                if rn and rn not in str(rc):
                    txt += f"\nnext       {rn}"
            else:
                nxt = s.get("recommend_next") or ""
                if nxt:
                    txt += f"\nnext       {nxt}"
            pin = s.get("pinned_model") or ""
            if pin:
                txt += f"\npinned     {pin}"
            if u and not u.get("ok"):
                fail = u.get("fail") or "FAIL: no local engine up"
                nxt = u.get("next_step") or "Launch env or ./pfy up"
                txt += f"\n{fail}\nnext       {nxt}"
            self.pack_acts(["refresh", "copyep", "est", "test", "pullname", "pull", "reco", "try", "tst", "pst", "rst", "recst", "tryst"])
        elif self.view == "stage":
            sl = stage.get("live") or "SKIP"
            txt = f"STAGE\nEnvironment check. SKIP means a piece is missing — not a fake pass.\nenv-stage   {sl}"
            self.pack_acts(["stage", "sst"])
        elif self.view == "attach":
            reach = str(s.get("session_reach") or "").strip() or getattr(self, "_session_reach", "") or "(none)"
            using = str(s.get("using") or s.get("attach_mode") or getattr(self, "_attach_mode", "") or "bare")
            mode_when = str(s.get("attach_mode_when") or "")
            graph_ev = str(s.get("graph_copy") or "").strip() or "(none)"
            graph_when = str(s.get("graph_when") or "")
            txt = f"ATTACH\nOpen an agent with no toolsets loaded. Loop writes toolsets into the agent you pick there.\nNOW     attached {attached} · last {verb}\nsession {reach}\nusing: {using}" + (f"  {mode_when}" if mode_when else "") + f"\ngraph      {graph_ev}" + (f"  {graph_when}" if graph_when else "")
            si = getattr(self, "_last_si", {}) or {}
            abs_p = str(si.get("abs_path") or "")
            rel_p = str(si.get("rel") or si.get("path") or "")
            task_p = str(si.get("task_text") or si.get("task_md") or "")
            if abs_p or rel_p or task_p:
                if abs_p:
                    txt += "\nabs       " + abs_p
                if rel_p:
                    txt += "\nrel       " + rel_p
                if task_p:
                    prev = task_p if len(task_p) <= 320 else task_p[:320] + "…"
                    txt += "\nTASK      " + prev.replace("\n", " / ")
                txt += "\nnote      Session proof: Attach OpenCode + disk artifact — not a board-hosted game"
            if stub: txt += f"\nFAIL    {s.get('blocked_copy') or GROK_USE}"
            if self.msg: txt += "\n" + self.msg
            # Buttons only (no path labels in the side pack — they clipped off-screen)
            self.pack_acts(["bare", "orch", "graph", "si", "siopen", "sifold", "sitask", "grok", "open", "hermes", "codex", "claude", "gab", "copy", "ast", "sist", "cst"])
        elif self.view == "tools":
            tools = s.get("tools") or {}
            skills = tools.get("skills") or {}
            def onoff(v):
                return "on" if v else "off"
            extra = onoff((tools.get("tools_mode") or "") == "local_tools")
            txt = (
                "TOOLS\nSkills on/off for the next session, plus the scored catalog. Loop starts the session.\n"
                f"one-shot         {onoff(skills.get('one-shot'))}\n"
                f"investigate      {onoff(skills.get('investigate'))}\n"
                f"agent-loops      {onoff(skills.get('agent-loops'))}\n"
                f"hermes-feedback  {onoff(skills.get('hermes-feedback'))}\n"
                f"mcp              {onoff(tools.get('mcp'))}\n"
                f"write-guard      {onoff(tools.get('write_guard'))}\n"
                f"extra tools      {extra}"
            )
            cats = list(s.get("catalog") or [])
            txt += "\nCATALOG"
            if not cats:
                txt += "\n(none)"
            else:
                for row in cats[:12]:
                    txt += "\n%s  %s  %s" % (row.get("name") or "", row.get("stage") or "-", row.get("status") or "")
                if len(cats) > 12:
                    txt += "\n… %d more" % (len(cats) - 12)
            qrows = list(s.get("catalog_queue") or [])
            txt += "\nQUEUE"
            if not qrows:
                txt += "\n(none)"
            else:
                for q in qrows[:8]:
                    extra = q.get("pr_url") or q.get("issue_url") or ""
                    txt += "\n%s  %s  %s%s" % (
                        q.get("name") or q.get("id") or "",
                        q.get("kind") or "",
                        q.get("status") or "",
                        ("  " + extra) if extra else "",
                    )
            att = s.get("catalog_attached") or s.get("active") or "(none)"
            txt += "\nattached   " + str(att)
            if s.get("catalog_ok") is False:
                txt += "\n" + (s.get("catalog_copy") or "FAIL catalog")
            if self.msg: txt += "\n" + self.msg
            self.pack_acts(["catname", "ask", "queue", "catcopy", "catst"])
            for w in self.tool_btns.values():
                w.pack(side="left", padx=(0, 8))
            self.toolst.pack(side="left", padx=(0, 8))
        else:
            rows = s.get("org_messages") or []
            txt = "no org loop" if not rows else "ORG\n" + "\n".join(f"{m.get('from')} → {m.get('to')}  {m.get('state') or ''}" for m in rows)
            self.pack_acts([])
        self.body.configure(text=txt)
        for c in self.chips.winfo_children(): c.destroy()
        if self.view == "loop":
            for m in list(s.get("modules") or []):
                tid = str(m.get("id") or "")
                status = module_paint_status(m)
                on = bool(m.get("enabled"))
                stub_mod = bool(m.get("stub"))
                fr = tk.Frame(self.chips, bg="#18202c", highlightbackground=("#4d8dff" if on else "#243041"), highlightthickness=1, padx=8, pady=6)
                fr.pack(side="left", padx=4, pady=4, anchor="n")
                tk.Label(fr, text=tid, bg="#18202c", fg=FG, font=("sans-serif", 10, "bold")).pack(anchor="w")
                tk.Label(fr, text=status, bg="#18202c", fg=CHIP.get(status, CHIP["missing"]), font=("sans-serif", 9, "bold")).pack(anchor="w")
                tk.Label(fr, text=("ON" if on else ("STUB" if stub_mod else "off")), bg="#18202c", fg=MUTED).pack(anchor="w")
                if not (stub_mod and not on):
                    fr.bind("<Button-1>", lambda e, x=tid, nxt=not on: self.toggle_loop_module(x, nxt))
        if self.view == "attach":
            for c in chips:
                hid, live, role, name = c.get("id") or "", honest(c.get("live")), c.get("role") or "", c.get("name") or ""
                fr = tk.Frame(self.chips, bg="#18202c", highlightbackground="#243041", highlightthickness=1, padx=8, pady=6)
                fr.pack(side="left", padx=4, pady=4, anchor="n")
                tk.Label(fr, text=hid, bg="#18202c", fg=FG, font=("sans-serif", 10, "bold")).pack(anchor="w")
                tk.Label(fr, text=live, bg="#18202c", fg=CHIP.get(live, CHIP["missing"]), font=("sans-serif", 9, "bold")).pack(anchor="w")
                tk.Label(fr, text=f"{role} · {name}", bg="#18202c", fg=MUTED).pack(anchor="w")
                if hid in BLOCKED:
                    tk.Label(fr, text=GROK_USE, bg="#111823", fg=FG, font=("monospace", 9)).pack(anchor="w", pady=(4,0))

    def poll(self, ms=2000):
        self.refresh()
        def tick():
            self.refresh(); self.root.after(ms, tick)
        self.root.after(ms, tick)

def selftest_snap():
    return {"ts":"selftest","host":"selftest","profile":"","detector":{"engine":"none","status":"missing","base_url":""},
            "engine_live":"missing","usage":[],"chips":[{"id":"grok","live":"missing","role":"harness","name":"Grok CLI"},
            {"id":"continue","live":"stub","role":"harness","name":"Continue"}],
            "tape":[{"id":"inference","label":"inference","live":"SKIP"},{"id":"env-stage","label":"env-stage","live":"SKIP"},
                    {"id":"harness-attach","label":"harness attach","live":"SKIP"}],
            "detect_order":[],"active":"grok","active_stub":False,"blocked_copy":GROK_USE,
            "attach_mode":"orchestration","using":"orchestration","attach_mode_when":"","attach_mode_live":"",
            "loop_ok":True,"loop_copy":"started 2/8 · grok · local-test","loop_when":"selftest",
            "graph_ok":True,"graph_copy":"path=axon","graph_when":"selftest","graph_path":"axon",
            "last_verb":{"verb":"gui","when":""},"now":"idle","processes":[],"agent_lane_collapsed":True,
            "tools":{"skills":{"one-shot":True,"investigate":True,"agent-loops":True,"hermes-feedback":True},"mcp":False,"write_guard":False,"tools_mode":"split"},
            "catalog":[{"name":"repowise","stage":"I1","status":"ready","github":"https://github.com/repowise-dev/repowise","notes":"usable","category":"Coding"}],
            "catalog_ok":True,"catalog_queue":[{"name":"repowise","kind":"queue","status":"open","issue_url":"https://github.com/themark-net/pfy-mentat/issues/214"}],"catalog_attached":"grok","catalog_prompt":"",
            "modules_task":"interactive","modules_enabled":["jev"],
            "modules":[
                {"id":"jev","title":"Jev","status":"implemented","enabled":True,"stub":False},
                {"id":"orchestration","title":"orchestration","status":"implemented","enabled":False,"stub":False},
                {"id":"code-graph","title":"code-graph","status":"partial","enabled":False,"stub":False},
            ],
            "hedge":{"task":"interactive","lane":"local","ok":True,"live":"READY","copy":"READY hedge local",
                     "local_ready":True,"local_engine":"freetoken","local_status":"ready","local_base_url":"http://127.0.0.1:1919/v1",
                     "budget":0,"spent":0,"remaining":0,"profile":"(unset)","gab_key":False,
                     "routes":{"bulk":{"lane":"local","ok":True,"reason":"local ready"},
                               "interactive":{"lane":"local","ok":True,"reason":"local ready"},
                               "hard":{"lane":"local","ok":True,"reason":"no budget; local hedge"}}},
            "wizard_ok":True,"wizard_step":"review","wizard_runtime":"freetoken ready","wizard_lane":"local","wizard_lane_label":"local FreeToken-first","wizard_toolsets":"bare","wizard_enabled":"bare READY · orchestration READY · code-graph SKIP · catalog SKIP","wizard_harness":"grok","wizard_review":"runtime freetoken ready · lane local · toolsets bare · harness grok","wizard_cta":"Launch session","wizard_decision":"● local CUA-S1-FORMS · FreeToken-first","wizard_decision_path":"cua-s1-forms","decision_chip":"decision · typed Choice","decision_conf":"conf ok","decision_honesty":"decision ≠ gab auto ≠ local","decision_core":"compact context · choose model/tool"}

def selftest_fresh_bind():
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import urlparse
    import urllib.request
    class Dump(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass
        def do_GET(self):
            b = b"<!DOCTYPE html><html><head><title>pfy board</title></head><body>127.0.0.1:8765 start via CLI nimo honest-state</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
    class Ours(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass
        def do_GET(self):
            b = b'<!DOCTYPE html><html data-pfy-ui="session"><head><title>pfy</title></head><body>LOOP Attach grok</body></html>'
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("X-Pfy-UI", "session")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
    dump = ThreadingHTTPServer(("127.0.0.1", 0), Dump)
    threading.Thread(target=dump.serve_forever, daemon=True).start()
    dport = dump.server_address[1]
    class Board:
        HOST = "127.0.0.1"
        PORT = dport
        Handler = Ours
    httpd, url = ensure_http(Board)
    try:
        got = urlparse(url).port
        if got == dport:
            return False
        with urllib.request.urlopen(url, timeout=1) as r:
            body = r.read().decode("utf-8", "replace")
            hdr = (r.headers.get("X-Pfy-UI") or "")
        return (
            not leftover_dump(body, hdr)
            and "pfy board" not in body.lower()
            and "start via cli" not in body.lower()
            and "<title>pfy</title>" in body
        )
    finally:
        try:
            httpd.shutdown()
        except Exception:
            pass
        try:
            dump.shutdown()
        except Exception:
            pass

def run_tk(board, selftest=False) -> bool:
    try:
        import tkinter as tk; import tkinter.ttk  # noqa
        root = tk.Tk()
    except Exception:
        return False
    print("native window (tk)", flush=True)
    w = Win(board, root)
    if selftest:
        w.apply(selftest_snap()); root.update_idletasks(); root.update()
        title = root.title()
        has = (
            w.bgrok.cget("text") == "Attach grok"
            and w.bopen.cget("text") == "Attach opencode"
            and w.bhermes.cget("text") == "Attach hermes"
            and w.bcodex.cget("text") == "Attach codex"
            and w.bclaude.cget("text") == "Attach claude"
            and w.bgab.cget("text") == "Attach gab"
            and w.brefresh.cget("text") == "Refresh status"
            and w.bcopy.cget("text") == "Copy stub one-liner"
            and w.bstage.cget("text") == "Run stage"
            and w.benv.cget("text") == "Launch env"
            and w.bsess.cget("text") == "Launch session"
            and w.bbulk.cget("text") == "Bulk — stay on this machine"
            and w.binteractive.cget("text") == "Interactive — local first"
            and w.bhard.cget("text") == "Hard — allow cloud"
            and w.bagents["grok"].cget("text") == "grok"
            and w.bagents["opencode"].cget("text") == "OpenCode"
            and w.bagents["gab"].cget("text") == "Gab"
            and w.blocal.cget("text") == "local"
            and w.bcloud.cget("text") == "cloud/subscription"
            and w.bofree.cget("text") == "OpenCode free"
            and w.bcatalog.cget("text") == "catalog"
            and w.bhopenc.cget("text") == "OpenCode"
            and w.bhgrok.cget("text") == "Grok"
            and w.bhhermes.cget("text") == "Hermes"
            and w.bhcodex.cget("text") == "Codex"
            and w.bhclaude.cget("text") == "Claude"
            and w.bhgab.cget("text") == "Gab"
            and w.bdecoff.cget("text") == "decision off"
            and w.bdeccua.cget("text") == "CUA-S1-FORMS"
            and w.bdects.cget("text") == "TypeSafe"
            and w.bdecmj.cget("text") == "mini-jev"
            and w.bpull.cget("text") == "Pull"
            and w.btest.cget("text") == "Test model"
            and w.breco.cget("text") == "Recommend"
            and w.btry.cget("text") == "Try recommended"
            and w.bask.cget("text") == "Ask TUI implement"
            and w.bqueue.cget("text") == "Queue for org"
            and w.bbare.cget("text") == "bare"
            and w.borch.cget("text") == "orchestration"
            and w.bgraph.cget("text") == "code-graph"
            and "tools" in w.nav
            and "env" not in w.nav
        )
        w.set_view("loop")
        body = w.body.cget("text") or ""
        mod_chrome = ""
        if "TOOLSETS" in body:
            mod_chrome = body.split("TOOLSETS", 1)[1]
            if "\nenabled" in mod_chrome:
                mod_chrome = mod_chrome.split("\nenabled", 1)[0]
        chip_st = []
        for fr in w.chips.winfo_children():
            kids = list(fr.winfo_children())
            if len(kids) >= 2:
                chip_st.append(str(kids[1].cget("text")))
        loop_ok = (
            "LOOP" in body
            and "HOW TO" in body
            and "LOCAL COMPUTE" in body
            and "CLOUD ORCHESTRATION" in body
            and "TOOLSETS" in body
            and "AGENT" in body
            and "PLAN" in body
            and "jev" in body
            and "wired" in body
            and "wired" in mod_chrome
            and "partial" in mod_chrome
            and "implemented" not in mod_chrome
            and "stub" not in mod_chrome
            and "wired" in chip_st
            and "implemented" not in chip_st
            and "stub" not in chip_st
            and "enabled" in body.lower()
            and "env" in body.lower()
            and "started 2/8" in body
            and "harness    " not in body
            and "LOCAL WORKER" not in body
            and "pfy board" not in body.lower()
        )
        w.set_view("attach")
        att_body = w.body.cget("text") or ""
        att_ok = "ATTACH" in att_body and "using:" in att_body.lower() and "graph      " in att_body
        w.set_view("tools")
        tools_body = w.body.cget("text") or ""
        tools_ok = "TOOLS" in tools_body and "CATALOG" in tools_body and "QUEUE" in tools_body and "open" in tools_body.lower()
        w.set_view("loop")
        loop_ok = loop_ok and att_ok and tools_ok
        w.copy_stub()
        copied = (w.cst.cget("text") in ("copied", "PASS copied"))
        try:
            clip = root.clipboard_get()
        except Exception:
            clip = ""
        root.destroy()
        return title == "pfy" and has and loop_ok and copied and bool(clip)
    w.poll(int(os.environ.get("PFY_BOARD_REFRESH_MS", "2000"))); root.mainloop(); return True

def main() -> int:
    if os.environ.get("PFY_GUI_SELFTEST")=="1" or "--selftest" in sys.argv:
        return 0 if run_tk(None, True) and selftest_fresh_bind() else 1
    try: board = load_board()
    except Exception as e:
        return stopped_exit(str(e))
    httpd, url = ensure_http(board)
    try:
        if run_webkit(url): return 0
        if run_tk(board, False): return 0
        if os.environ.get("PFY_GUI_DEV")=="1" and run_pywebview(url): return 0
        return stopped_exit("no already-on-box toolkit opened a native window")
    finally:
        if httpd is not None:
            try: httpd.shutdown()
            except Exception: pass

if __name__ == "__main__":
    raise SystemExit(main())
