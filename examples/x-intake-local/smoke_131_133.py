#!/usr/bin/env python3
"""Operate-or-FAIL smokes for X intake Entries 131-133 (JevAgentHarness, ai-memory, headson). Stdlib only.

Usage: python3 examples/x-intake-local/smoke_131_133.py --entry jah|aimemory|headson

Same contract and receipts as smoke.py next to it (whose helpers it reuses): exit 0 = PASS, 1 = the tool ran but
the check failed, 2 = can't run here (prereq missing; reason recorded). Writes pipelines/smoke/<entry>/latest.json.
Never installs or downloads anything. Every child process starts through `run_isolated` in smoke.py (fresh temp HOME,
env limited to PATH/HOME/TERM/LANG/NO_COLOR plus the variables named below; nothing copied from this process, so no
provider key is ever seen; a timeout SIGKILLs the process group, grandchildren included) under bwrap with no network
when bwrap works. jah and aimemory need a long-running server, so the smoke writes a small stdlib driver into the temp
dir and starts it as the one `run_isolated` child; the driver starts the server, talks to it on 127.0.0.1 inside the
same sandbox and always stops it. No smoke calls a real model, adds a key, or runs `init`-style host setup (`jah init`,
`ai-memory setup`/`install-*`, `hson --explore`). PFY_XINTAKE_TIMEOUT (float seconds, > 0) overrides the 600s
per-command timeout. Any other value (abc, 0, -1, nan, inf) exits 2 before the entry runs.
Real HOME: each entry fingerprints the real-HOME dirs the tool could write (jah: ~/.jah, its default config and log
dir; aimemory: ~/.local/share/ai-memory and ~/.config/ai-memory, its default data and config dirs; headson:
~/.local/state/headson, where explore sessions go) with smoke_128_130.home_sig() before the run and again in a finally,
also on timeout or a crash. Any created, deleted or changed entry (type, permission bits, mtime, size, content, symlink
target) sets checks.real_home_untouched false, lists the dirs in real_home_changed and FAILs (exit 1), even when bwrap
is unavailable. Only those dirs are watched: a write elsewhere in HOME is not seen. checks.body_completed is false and
`exception` names it when the run raised.

  jah       $JAH_BIN, else ~/DEVELOP/pfy-mentat/tmp/jevagentharness/.venv/bin/jah, else PATH (a venv with the
            clone at the pinned commit installed, `pip install .`); the driver runs on system python3. `jah --version` pinned to 0.1.0 ($JAH_VERSION overrides). The driver serves a stub
            OpenAI-compatible upstream (models stub-strong / stub-fast, no key) and a stub Jev System-One endpoint
            (POST /v1/systemone, the wire format Laya serves, Entry 086) on 127.0.0.1, writes two configs into the temp
            dir and runs `jah serve -c` against each, sending a 4-step tool-calling session as an agent would.
            Rules backend: steps must go strong (first step), fast (plain tool output), strong (a traceback, why
            error_signal), strong (the fast tier's final answer redone by the strong tier, finish check). Local Jev
            backend: strong, fast (stub says routine), strong (stub says hard), strong (stub returns HTTP 400:
            decision_error fail-safe). The stub Jev must see model agentdecision-4b, the hard/routine options and no
            Authorization header; no upstream call may carry one; no log file may contain the task or tool text.
  aimemory  $AI_MEMORY_BIN, else ~/DEVELOP/pfy-mentat/tmp/ai-memory/ai-memory, else PATH (the unpacked release
            tarball, ai-memory-linux-x86_64.tar.gz). `ai-memory --version` pinned to 3.1.1 ($AI_MEMORY_VERSION
            overrides). The driver runs `--data-dir <temp> init`, then `serve --transport http` on a free loopback port
            with AI_MEMORY_EMBEDDING_PROVIDER=none (otherwise the first start fetches an ~87 MB embedding model), waits
            for /healthz, and from two temp project dirs: write-page, search (a hit and a miss), read-page, then
            `message send` to the second project and `message pop` twice. The page must be found and read back, also be
            a markdown file under the data dir's wiki/, the first pop must return the message (state claimed, with the
            untrusted-input notice) and the second pop must return nothing (claim once).
  headson   $HSON_BIN, else ~/DEVELOP/pfy-mentat/tmp/headson/hson, else PATH (release tarball
            hson-x86_64-unknown-linux-musl.tar.gz). `hson --version` pinned to 0.17.1 ($HSON_VERSION overrides). On a
            ~300 KB JSON fixture (3000 results, one FAIL): `-c 600 -f json -t strict` must parse, fit 600 bytes, keep
            every top-level key and the first result; a rerun must be byte-identical; `--tail` must keep the last
            result; `--grep FAIL` must keep the FAIL value even past the budget. Fixture unchanged, temp HOME empty.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from smoke import TMP, find_bin, pinned, run_isolated, timeout_reason, write
from smoke_128_130 import as_json, finish, home_sig, timeout_problem, tmo

JAH_PIN = "0.1.0"
AIM_PIN = "3.1.1"
HSON_PIN = "0.17.1"
SYS_PATH = "/usr/local/bin:/usr/bin:/bin"
WATCH = {"jah": (".jah",),
         "aimemory": (".local/share/ai-memory", ".config/ai-memory"),
         "headson": (".local/state/headson",)}
TASK_MARK = "PFYTASK-7731"   # task text; must never show up in a log file
TOOL_MARK = "PFYTOOL-5150"   # tool output text; same
PAGE_MARK = "PFYMARK zeta42"
MSG_MARK = "HANDOFF-q81 take over the router test"


def iso(argv: list[str], tag: str, **kw) -> subprocess.CompletedProcess:
    try:
        return run_isolated(argv, timeout=tmo(), **kw)
    except subprocess.TimeoutExpired as e:
        raise TimeoutError(timeout_reason(tag, float(e.timeout)))


def watch_dirs(entry: str) -> str:
    return ", ".join("~/" + d for d in WATCH[entry])


def home_note(entry: str, r: dict) -> str:
    return f"real HOME {', '.join(r.get('real_home_changed') or ['~/' + d for d in WATCH[entry]])} changed"


def watched(entry: str, body, r: dict) -> int:
    """Run body(r, checks) with the real HOME watched; the finally runs on timeout and on any exception too."""
    real_home = Path.home()
    before = {d: home_sig(real_home / d) for d in WATCH[entry]}
    checks: dict[str, bool] = {}
    code = None
    try:
        code = body(r, checks)
        checks["body_completed"] = True
    except BaseException as e:  # main() turns it into a FAIL; the receipt says what stopped the run
        checks["body_completed"] = False
        r["exception"] = f"{type(e).__name__}: {e}"[:300]
        raise
    finally:
        after = {d: home_sig(real_home / d) for d in WATCH[entry]}
        changed = [f"~/{d}" for d in WATCH[entry] if before[d] != after[d]]
        checks["real_home_untouched"] = not changed
        if changed:
            r["real_home_changed"] = changed
        r["checks"] = checks
    if code is not None:
        if not checks["real_home_untouched"]:
            r["reason"] = f"{r.get('reason', '')}; {home_note(entry, r)}"
            return 1
        return code
    code = finish(r, checks, r.pop("_ok_reason", ""))
    if not checks["real_home_untouched"]:
        r["reason"] += f"; {home_note(entry, r)}"
    return code


def version_of(binary: str, home: str, cwd: str, tag: str) -> str:
    v = iso([binary, "--version"], tag, home=home, cwd=cwd, path=SYS_PATH, bwrap_writable=[cwd])
    m = re.search(r"(\d+\.\d+\.\d+\S*)", v.stdout)
    return m.group(1) if m else ""


def driver_budget() -> float:
    """Seconds the driver may spend in total; a bit under the run_isolated timeout so it can stop its server."""
    return max(1.0, tmo() - 5.0)


def run_driver(r: dict, td: Path, home: Path, python: str, source: str, spec: dict, tag: str,
               extra: dict | None = None) -> dict | None:
    drv, spec_path = td / "driver.py", td / "spec.json"
    drv.write_text(source, encoding="utf-8")
    spec_path.write_text(json.dumps({**spec, "budget_s": driver_budget()}), encoding="utf-8")
    p = iso([python, str(drv), str(spec_path)], tag, home=str(home), cwd=str(td), path=SYS_PATH, extra=extra,
            bwrap_writable=[str(td)])
    out = as_json(p)
    if not isinstance(out, dict):
        r["driver_rc"] = p.returncode
        r["driver_tail"] = (p.stdout + p.stderr).strip()[-800:]
        return None
    return out


# ---------------------------------------------------------------- jah (JevAgentHarness)
JAH_DRIVER = r'''
import json, os, re, socket, subprocess, sys, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

spec = json.load(open(sys.argv[1]))
work, jah = spec["work"], spec["jah"]
deadline = time.monotonic() + float(spec["budget_s"])
up_calls, jev_calls = [], []


class Up(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        model, msgs = body.get("model"), body.get("messages", [])
        last = msgs[-1].get("content") if msgs else ""
        up_calls.append({"model": model, "auth": bool(self.headers.get("Authorization"))})
        if isinstance(last, str) and "ALLDONE" in last:
            msg = {"role": "assistant", "content": "done by " + str(model)}
        else:
            msg = {"role": "assistant", "content": None, "tool_calls": [{"id": "c%d" % len(up_calls),
                   "type": "function", "function": {"name": "bash", "arguments": json.dumps({"cmd": "step %d" % len(msgs)})}}]}
        out = {"id": "x", "object": "chat.completion", "model": model,
               "choices": [{"index": 0, "message": msg, "finish_reason": "stop" if msg["content"] else "tool_calls"}],
               "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}
        b = json.dumps(out).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


class Jev(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        state = str(body.get("state", ""))
        qs = body.get("questions") or {}
        jev_calls.append({"path": self.path, "model": body.get("model"), "auth": bool(self.headers.get("Authorization")),
                          "options": sorted({o for q in qs.values() for o in (q.get("criteria") or {})})})
        if "OUTAGE" in state:
            b, code = b'{"error": "stub outage"}', 400
        else:
            hard = 0.95 if "flaky" in state else 0.05
            ans = {qid: {"probabilities": {o: (hard if o == "hard" else 1.0 - hard)
                                           for o in (q.get("criteria") or {})}} for qid, q in qs.items()}
            b, code = json.dumps({"answers": ans, "usage": {"input_tokens": 100}}).encode(), 200
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


def serve(handler):
    s = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


TOOLS = [{"type": "function", "function": {"name": "bash", "description": "run a command",
          "parameters": {"type": "object", "properties": {"cmd": {"type": "string"}}}}}]


def scenario(name, decision, outputs):
    port = free_port()
    logs = os.path.join(work, name, "logs")
    os.makedirs(logs, exist_ok=True)
    cfg = os.path.join(work, name, "cfg.yaml")
    with open(cfg, "w") as f:
        f.write("listen: {host: 127.0.0.1, port: %d}\nlog_dir: %s\nlog_states: false\nupstreams:\n"
                "  stub: {type: openai, base_url: \"http://127.0.0.1:%d/v1\", key_env: \"\"}\n"
                "tiers:\n  strong: {upstream: stub, model: stub-strong}\n  fast: {upstream: stub, model: stub-fast}\n"
                "router:\n  decision: %s\n  tau: 0.75\n  first_steps_strong: 1\n  verify_finish: true\n"
                "  on_error: strong\nmodels:\n  jah-auto: {policy: route}\ndefault_model: jah-auto\n"
                % (port, logs, UP.server_port, decision))
    res = {"port": port}
    serve_log = open(os.path.join(work, name, "serve.log"), "w")
    proc = subprocess.Popen([jah, "serve", "-c", cfg], stdout=serve_log, stderr=subprocess.STDOUT)
    base = "http://127.0.0.1:%d" % port
    try:
        up = False
        while time.monotonic() < deadline and proc.poll() is None:
            try:
                urllib.request.urlopen(base + "/stats", timeout=1).read()
                up = True
                break
            except Exception:
                time.sleep(0.1)
        res["up"] = up
        if not up:
            return res
        n0 = len(up_calls)
        msgs = [{"role": "system", "content": "You are a coding agent."},
                {"role": "user", "content": "Fix the failing test. " + spec["task_mark"]}]

        def ask():
            req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps(
                {"model": "jah-auto", "messages": msgs, "tools": TOOLS}).encode(), headers={
                "Content-Type": "application/json", "Authorization": "Bearer jah", "X-JAH-Session": "pfy-" + name})
            left = max(1.0, deadline - time.monotonic())
            return json.loads(urllib.request.urlopen(req, timeout=left).read())["choices"][0]["message"]

        m = ask()
        for o in outputs:
            tc = (m.get("tool_calls") or [{"id": "none", "type": "function",
                                           "function": {"name": "bash", "arguments": "{}"}}])[0]
            msgs.append({"role": "assistant", "content": None, "tool_calls": [tc]})
            msgs.append({"role": "tool", "tool_call_id": tc["id"], "content": o})
            m = ask()
        res["final"] = m.get("content")
        res["upstream_models"] = [c["model"] for c in up_calls[n0:]]
        res["stats_tier_share"] = json.loads(urllib.request.urlopen(base + "/stats", timeout=5).read()).get("tier_share")
    finally:
        proc.terminate()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
        serve_log.close()
    steps = []
    p = os.path.join(logs, "steps.jsonl")
    if os.path.exists(p):
        for line in open(p):
            d = json.loads(line)
            steps.append({"step": d.get("step"), "tier": d.get("tier"), "reason": d.get("reason"),
                          "why": (d.get("decision") or {}).get("why"),
                          "call_tiers": [c.get("tier") for c in d.get("calls", [])]})
    res["steps"] = steps
    leak = []
    for root, _, files in os.walk(logs):
        for fn in files:
            t = open(os.path.join(root, fn), errors="replace").read()
            if spec["task_mark"] in t or spec["tool_mark"] in t:
                leak.append(fn)
    res["log_files"] = sorted(os.listdir(logs))
    res["logs_with_prompt_text"] = leak
    res["serve_log_tail"] = open(os.path.join(work, name, "serve.log"), errors="replace").read()[-400:]
    return res


UP = serve(Up)
JEV = serve(Jev)
tm = spec["tool_mark"]
out = {"rules": scenario("rules", "{type: rules}",
                         ["file_a.py file_b.py " + tm, "Traceback (most recent call last):\n  AssertionError: 1 failed",
                          "tests pass ALLDONE"]),
       "jev": scenario("jev", "{type: jev, provider: local, base_url: \"http://127.0.0.1:%d\", model: agentdecision-4b,"
                              " retries: 0, timeout_s: 5}" % JEV.server_port,
                       ["file_a.py file_b.py " + tm, "the test is flaky again", "OUTAGE marker"])}
out["upstream_auth_seen"] = any(c["auth"] for c in up_calls)
out["jev_calls"] = jev_calls
print(json.dumps(out))
'''

RULES_TIERS = ["strong", "fast", "strong", "strong"]
RULES_REASONS = ["first_steps", "routine", "hard", "finish_check"]
JEV_TIERS = ["strong", "fast", "strong", "strong"]
JEV_REASONS = ["first_steps", "routine", "hard", "decision_error"]


def smoke_jah(r: dict) -> int:
    jah = find_bin("JAH_BIN", "jevagentharness/.venv/bin/jah", "jah")
    r["jah"] = jah
    if not jah:
        r["reason"] = "jah not found ($JAH_BIN, tmp/jevagentharness/.venv/bin/jah, PATH); see the handoff"
        return 2
    python = shutil.which("python3", path=SYS_PATH)
    if not python:
        r["reason"] = f"python3 not found in {SYS_PATH} (runs the stdlib driver)"
        return 2
    want = pinned(r, "JAH_VERSION", JAH_PIN)
    return watched("jah", lambda rr, checks: _jah(rr, jah, python, want, checks), r)


def _jah(r: dict, jah: str, python: str, want: str, checks: dict) -> int | None:
    with tempfile.TemporaryDirectory(prefix="pfy-jah-") as tdn:
        td = Path(tdn)
        home, work = td / "home", td / "work"
        home.mkdir()
        work.mkdir()
        have = version_of(jah, str(home), tdn, "jah version")
        r["jah_version"] = have
        if have != want:
            r["reason"] = f"jah --version is {have!r}, not {want} (set $JAH_VERSION)"
            return 2
        out = run_driver(r, td, home, python, JAH_DRIVER,
                         {"work": str(work), "jah": jah, "task_mark": TASK_MARK, "tool_mark": TOOL_MARK}, "jah driver")
        if out is None:
            checks["driver_report"] = False
            return None
        ru, jv = out.get("rules") or {}, out.get("jev") or {}
        r["rules"] = {k: ru.get(k) for k in ("steps", "upstream_models", "final", "stats_tier_share", "log_files")}
        r["jev"] = {k: jv.get(k) for k in ("steps", "upstream_models", "final", "stats_tier_share", "log_files")}
        r["jev_calls"] = (out.get("jev_calls") or [])[:6]
        for name, sc in (("rules", ru), ("jev", jv)):
            if not sc.get("up"):
                r[f"{name}_serve_log_tail"] = sc.get("serve_log_tail")
        rs, js = ru.get("steps") or [], jv.get("steps") or []
        checks["rules_proxy_up"] = bool(ru.get("up"))
        checks["rules_tiers"] = [s.get("tier") for s in rs] == RULES_TIERS
        checks["rules_reasons"] = [s.get("reason") for s in rs] == RULES_REASONS
        checks["rules_traceback_is_error_signal"] = len(rs) == 4 and rs[2].get("why") == "error_signal"
        checks["rules_finish_redone_by_strong"] = (len(rs) == 4 and rs[3].get("call_tiers") == ["fast", "strong"]
                                                   and ru.get("final") == "done by stub-strong")
        checks["rules_upstream_sequence"] = ru.get("upstream_models") == [
            "stub-strong", "stub-fast", "stub-strong", "stub-fast", "stub-strong"]
        checks["jev_proxy_up"] = bool(jv.get("up"))
        checks["jev_tiers"] = [s.get("tier") for s in js] == JEV_TIERS
        checks["jev_reasons"] = [s.get("reason") for s in js] == JEV_REASONS
        calls = out.get("jev_calls") or []
        checks["jev_wire_systemone"] = bool(calls) and all(c.get("path") == "/v1/systemone" and
                                                           c.get("model") == "agentdecision-4b" and
                                                           {"hard", "routine"} <= set(c.get("options") or [])
                                                           for c in calls)
        checks["no_auth_header_anywhere"] = (not out.get("upstream_auth_seen")
                                             and not any(c.get("auth") for c in calls))
        checks["logs_hold_no_prompt_text"] = (bool(ru.get("log_files")) and not ru.get("logs_with_prompt_text")
                                              and not jv.get("logs_with_prompt_text"))
        checks["home_untouched"] = not any(home.iterdir())
    r["_ok_reason"] = ("stub upstream + rules and local-Jev decision backends on loopback: strong/fast/strong/finish-check "
                       "and strong/fast/strong/decision_error routes as documented, System-One wire seen, no auth "
                       "header, no prompt text in logs; temp HOME and the watched real-HOME dir "
                       f"({watch_dirs('jah')}) unchanged")
    return None


# ---------------------------------------------------------------- aimemory (ai-memory)
AIM_DRIVER = r'''
import glob, json, os, socket, subprocess, sys, time, urllib.request

spec = json.load(open(sys.argv[1]))
B, D, work = spec["bin"], spec["data"], spec["work"]
deadline = time.monotonic() + float(spec["budget_s"])
s = socket.socket()
s.bind(("127.0.0.1", 0))
port = s.getsockname()[1]
s.close()
url = "http://127.0.0.1:%d" % port
env = dict(os.environ, AI_MEMORY_SERVER_URL=url, AI_MEMORY_EMBEDDING_PROVIDER="none", NO_COLOR="1")
out = {}


def cli(tag, args, cwd):
    left = max(1.0, deadline - time.monotonic())
    p = subprocess.run([B, "--data-dir", D] + args, cwd=cwd, env=env, capture_output=True, text=True, timeout=left)
    out[tag] = {"rc": p.returncode, "out": p.stdout[-1500:], "err_tail": p.stderr[-300:]}
    return p


proj, projb = os.path.join(work, "proj"), os.path.join(work, "projb")
os.makedirs(proj)
os.makedirs(projb)
cli("init", ["init"], work)
log = open(os.path.join(work, "serve.log"), "w")
srv = subprocess.Popen([B, "--data-dir", D, "serve", "--transport", "http", "--bind", "127.0.0.1:%d" % port],
                       cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT)
try:
    up = False
    while time.monotonic() < deadline and srv.poll() is None:
        try:
            up = urllib.request.urlopen(url + "/healthz", timeout=1).status == 200
            if up:
                break
        except Exception:
            time.sleep(0.1)
    out["healthy"] = up
    if up:
        cli("write", ["write-page", "--path", "notes/router.md", "--kind", "gotcha", "--body",
                      "# Router note\n" + spec["page_mark"] + ": route routine steps to the fast tier."], proj)
        cli("search_hit", ["search", spec["page_mark"].split()[-1]], proj)
        cli("search_miss", ["search", "nosuchwordqq"], proj)
        cli("read", ["read-page", "--path", "notes/router.md"], proj)
        cli("write_b", ["write-page", "--path", "notes/inbox.md", "--body", "# Inbox"], projb)
        cli("send", ["message", "send", "--to-workspace", "default", "--to-project", "projb", "--subject", "handoff",
                     "--json", spec["msg_mark"]], proj)
        cli("pop1", ["message", "pop", "--json"], projb)
        cli("pop2", ["message", "pop", "--json"], projb)
finally:
    srv.terminate()
    try:
        srv.wait(10)
    except subprocess.TimeoutExpired:
        srv.kill()
    log.close()
hits = []
for f in glob.glob(os.path.join(D, "wiki", "**", "*.md"), recursive=True):
    if spec["page_mark"] in open(f, errors="replace").read():
        hits.append(os.path.relpath(f, D))
out["wiki_files_with_mark"] = hits
out["serve_log_tail"] = open(os.path.join(work, "serve.log"), errors="replace").read()[-400:]
print(json.dumps(out))
'''


def _pop(o: dict, tag: str) -> dict:
    try:
        return json.loads((o.get(tag) or {}).get("out") or "")
    except ValueError:
        return {}


def smoke_aimemory(r: dict) -> int:
    b = find_bin("AI_MEMORY_BIN", "ai-memory/ai-memory", "ai-memory")
    r["bin"] = b
    if not b:
        r["reason"] = ("ai-memory not found ($AI_MEMORY_BIN, tmp/ai-memory/ai-memory, PATH); unpack the release tarball,"
                       " see the handoff. Never run install.sh or `ai-memory setup`")
        return 2
    python = shutil.which("python3", path=SYS_PATH)
    if not python:
        r["reason"] = f"python3 not found in {SYS_PATH} (runs the stdlib driver)"
        return 2
    want = pinned(r, "AI_MEMORY_VERSION", AIM_PIN)
    return watched("aimemory", lambda rr, checks: _aimemory(rr, b, python, want, checks), r)


def _aimemory(r: dict, b: str, python: str, want: str, checks: dict) -> int | None:
    with tempfile.TemporaryDirectory(prefix="pfy-aimemory-") as tdn:
        td = Path(tdn)
        home, work, data = td / "home", td / "work", td / "data"
        home.mkdir()
        work.mkdir()
        have = version_of(b, str(home), tdn, "ai-memory version")
        r["aim_version"] = have
        if have != want:
            r["reason"] = f"ai-memory --version is {have!r}, not {want} (set $AI_MEMORY_VERSION)"
            return 2
        o = run_driver(r, td, home, python, AIM_DRIVER,
                       {"bin": b, "data": str(data), "work": str(work), "page_mark": PAGE_MARK, "msg_mark": MSG_MARK},
                       "ai-memory driver")
        if o is None:
            checks["driver_report"] = False
            return None

        def ok(tag: str) -> bool:
            return (o.get(tag) or {}).get("rc") == 0

        def txt(tag: str) -> str:
            return (o.get(tag) or {}).get("out") or ""

        p1, p2 = _pop(o, "pop1"), _pop(o, "pop2")
        m1 = p1.get("message") if isinstance(p1.get("message"), dict) else {}
        r["steps"] = {k: {"rc": (o.get(k) or {}).get("rc"), "out": txt(k)[:300]} for k in
                      ("init", "write", "search_hit", "search_miss", "read", "send", "pop2")}
        r["pop1"] = {"state": m1.get("state"), "body": m1.get("body"), "notice": bool(p1.get("security_notice"))}
        r["wiki_files_with_mark"] = o.get("wiki_files_with_mark")
        if not o.get("healthy"):
            r["serve_log_tail"] = o.get("serve_log_tail")
        checks["init_exit_0"] = ok("init")
        checks["server_healthy"] = bool(o.get("healthy"))
        checks["write_page_ok"] = ok("write") and "notes/router.md" in txt("write")
        checks["search_finds_page"] = ok("search_hit") and "notes/router.md" in txt("search_hit") and \
            "zeta42" in txt("search_hit")
        checks["search_miss_is_empty"] = ok("search_miss") and "notes/router.md" not in txt("search_miss")
        checks["read_page_returns_body"] = ok("read") and PAGE_MARK in txt("read")
        checks["wiki_markdown_on_disk"] = bool(o.get("wiki_files_with_mark"))
        checks["message_sent"] = ok("send") and bool(_pop(o, "send").get("message_id"))
        checks["first_pop_claims_message"] = ok("pop1") and m1.get("body") == MSG_MARK and m1.get("state") == "claimed"
        checks["pop_marks_message_untrusted"] = bool(p1.get("security_notice"))
        checks["second_pop_empty"] = ok("pop2") and "message" in p2 and p2.get("message") is None
        checks["home_untouched"] = not any(home.iterdir())
    r["_ok_reason"] = ("loopback server on a temp data dir, embeddings off: page written, found, read back and on disk as "
                       "markdown; cross-project message claimed exactly once with the untrusted notice; temp HOME and "
                       f"the watched real-HOME dirs ({watch_dirs('aimemory')}) unchanged")
    return None


# ---------------------------------------------------------------- headson
def hs_fixture() -> str:
    rows = [{"id": i, "case": f"case-{i}", "verdict": "FAIL" if i == 1337 else "PASS", "note": "x" * 40}
            for i in range(3000)]
    return json.dumps({"run": "pfy-smoke", "results": rows, "meta": {"model": "fixture"}})


def _hs_parse(cp: subprocess.CompletedProcess):
    try:
        return json.loads(cp.stdout)
    except ValueError:
        return None


def smoke_headson(r: dict) -> int:
    b = find_bin("HSON_BIN", "headson/hson", "hson")
    r["bin"] = b
    if not b:
        r["reason"] = "hson not found ($HSON_BIN, tmp/headson/hson, PATH); unpack the release tarball, see the handoff"
        return 2
    want = pinned(r, "HSON_VERSION", HSON_PIN)
    return watched("headson", lambda rr, checks: _headson(rr, b, want, checks), r)


def _headson(r: dict, b: str, want: str, checks: dict) -> int | None:
    with tempfile.TemporaryDirectory(prefix="pfy-headson-") as tdn:
        td = Path(tdn)
        home = td / "home"
        home.mkdir()
        have = version_of(b, str(home), tdn, "hson version")
        r["hson_version"] = have
        if have != want:
            r["reason"] = f"hson --version is {have!r}, not {want} (set $HSON_VERSION)"
            return 2
        fx = td / "results.json"
        fx.write_text(hs_fixture(), encoding="utf-8")
        sig = hashlib.sha256(fx.read_bytes()).hexdigest()
        kw = {"home": str(home), "cwd": tdn, "path": SYS_PATH, "bwrap_writable": [tdn]}
        base = [b, "-c", "600", "-f", "json", "-t", "strict"]
        a = iso(base + [str(fx)], "hson head", **kw)
        a2 = iso(base + [str(fx)], "hson rerun", **kw)
        tl = iso(base + ["--tail", str(fx)], "hson tail", **kw)
        gp = iso(base + ["--grep", "FAIL", str(fx)], "hson grep", **kw)
        ja, jt, jg = _hs_parse(a), _hs_parse(tl), _hs_parse(gp)
        r["rc"] = {"head": a.returncode, "rerun": a2.returncode, "tail": tl.returncode, "grep": gp.returncode}
        r["bytes"] = {"input": fx.stat().st_size, "head": len(a.stdout.rstrip("\n").encode()),
                      "grep": len(gp.stdout.rstrip("\n").encode())}

        def ids(j) -> list:
            return [x.get("id") for x in (j or {}).get("results", []) if isinstance(x, dict)]

        r["ids"] = {"head": ids(ja)[:8], "tail": ids(jt)[-8:]}
        fails = [x for x in (jg or {}).get("results", []) if isinstance(x, dict) and x.get("verdict") == "FAIL"]
        r["grep_fail_rows"] = fails[:2]   # finding: the forced match keeps the value, not its siblings (no id)
        checks["head_exit_0"] = a.returncode == 0
        checks["head_is_strict_json"] = isinstance(ja, dict)
        checks["head_within_600_bytes"] = len(a.stdout.rstrip("\n").encode()) <= 600
        checks["head_keeps_top_level_keys"] = isinstance(ja, dict) and set(ja) == {"run", "results", "meta"}
        checks["head_keeps_first_result"] = ids(ja)[:1] == [0]
        checks["deterministic_rerun"] = a2.returncode == 0 and a.stdout == a2.stdout
        checks["tail_keeps_last_result"] = tl.returncode == 0 and isinstance(jt, dict) and ids(jt)[-1:] == [2999]
        checks["grep_keeps_fail_value"] = gp.returncode == 0 and isinstance(jg, dict) and bool(fails)
        checks["fixture_untouched"] = hashlib.sha256(fx.read_bytes()).hexdigest() == sig
        checks["home_untouched"] = not any(home.iterdir())
    r["_ok_reason"] = ("strict JSON preview of a ~300 KB fixture within 600 bytes, keys and first row kept, byte-identical "
                       "rerun, --tail keeps the last row, --grep keeps the FAIL value; fixture, temp HOME and the "
                       f"watched real-HOME dir ({watch_dirs('headson')}) unchanged")
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", required=True, choices=["jah", "aimemory", "headson"])
    a = ap.parse_args()
    receipt = {"entry": a.entry, "script": "examples/x-intake-local/smoke_131_133.py",
               "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    fn = {"jah": smoke_jah, "aimemory": smoke_aimemory, "headson": smoke_headson}[a.entry]
    bad = timeout_problem()
    if bad:
        receipt["reason"] = bad
        return write(a.entry, receipt, 2)
    try:
        code = fn(receipt)
    except Exception as e:  # TimeoutError or any crash still writes a FAIL receipt (watched() saved the checks)
        receipt.pop("_ok_reason", None)
        receipt["reason"] = str(e) if isinstance(e, TimeoutError) else f"unexpected {type(e).__name__}: {e}"
        if receipt.get("checks", {}).get("real_home_untouched") is False:
            receipt["reason"] += f"; {home_note(a.entry, receipt)}"
        code = 1
    return write(a.entry, receipt, code)


if __name__ == "__main__":
    sys.exit(main())
