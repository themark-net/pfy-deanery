#!/usr/bin/env python3
"""Operate-or-FAIL smokes for X intake Entries 103-105 (BugPatrol, GraphJin, anti-slop). Stdlib only.

Usage: python3 examples/x-intake-local/smoke_103_105.py --entry bugpatrol|graphjin|antislop

Same contract and receipts as smoke.py next to it (whose helpers it reuses): exit 0 = PASS, 1 = the tool ran but
the check failed, 2 = can't run here (prereq missing; reason recorded). Writes pipelines/smoke/<entry>/latest.json.
Never installs or downloads anything; every scratch file goes to a fresh tempfile directory that is removed.
Tool subprocesses get a fresh temp HOME. PFY_XINTAKE_TIMEOUT (float seconds, > 0) overrides the tool timeouts
(defaults: 120s bugpatrol explore, 60s graphjin startup); Empty keeps the defaults. Any other set value (abc, 0, -1, nan, inf) exits 2 before the entry runs.

  bugpatrol  $BUGPATROL_BIN or ~/DEVELOP/pfy-mentat/tmp/bugpatrol/node_modules/.bin/bugpatrol (npm --prefix install),
             plus Node 22+ from $BUGPATROL_NODE, ~/DEVELOP/pfy-mentat/tmp/bugpatrol/node/bin/node, or PATH; and git.
             Starts an in-process stdlib fake OpenAI-compatible server on 127.0.0.1 and runs `bugpatrol explore`
             on a throwaway CLI-platform repo whose explorer uses `via: custom` pointed at it. Every model call must
             land on that local endpoint (never a paid provider; provider keys are stripped from the env), a model
             that never calls a tool must raise 0 candidates, and the same config with no endpoint must be refused.
  graphjin   $GRAPHJIN_BIN or ~/DEVELOP/pfy-mentat/tmp/graphjin/graphjin, then PATH. The v3.21.6 linux_amd64 binary
             is pinned by sha256; $GRAPHJIN_SHA256 overrides the pin, and a mismatch exits 2 without exec. On a
             throwaway SQLite db: with the source `read_only: true`, a read returns the seeded rows while insert,
             update, and delete are refused and the file is unchanged; a control run with `read_only: false` must
             let the insert through (so the refusal is really read_only); and with `production: true` a saved
             query runs while an ad-hoc query is refused (allow-list).
  antislop   $ANTISLOP_DIR or ~/DEVELOP/pfy-mentat/tmp/anti-slop (a clone). Every skills/*/SKILL.md must open with
             YAML frontmatter whose `name` is lowercase-hyphen, at most 64 chars, and equal to its folder, with a
             non-empty `description` of at most 1024 chars; the core `antislop` skill must be present. The
             validator is first run on two synthetic bad skills and must reject both. Read-only: nothing is
             copied into any harness skill folder.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from smoke import TMP, find_bin, node_version_env, pinned, run, scrub_env, timeout_reason, write

# graphjin_3.21.6_linux_amd64.tar.gz -> `graphjin` binary (tarball sha256 checked against upstream checksums.txt)
GRAPHJIN_V3216_SHA256 = "e6f0fd88f99b07e8036ba7db76f24f0fceab697935559d154e823b5951f46805"


def xintake_timeout(default: float) -> float:
    """Seconds from PFY_XINTAKE_TIMEOUT when that value is a float > 0; otherwise default."""
    raw = (os.environ.get("PFY_XINTAKE_TIMEOUT") or "").strip()
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def timeout_problem() -> str | None:
    """PFY_XINTAKE_TIMEOUT must be a finite number of seconds > 0 when set; xintake_timeout() would quietly use the default instead."""
    raw = os.environ.get("PFY_XINTAKE_TIMEOUT", "")
    if not raw or not raw.strip():
        return None
    raw = raw.strip()
    try:
        v = float(raw)
    except ValueError:
        v = math.nan
    if math.isfinite(v) and v > 0:
        return None
    return f"PFY_XINTAKE_TIMEOUT={raw[:40]!r} is not a number of seconds > 0"


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def clean_env(home: str, **extra: str) -> dict:
    env = scrub_env(os.environ)
    env.update(HOME=home, **extra)
    return env


# ---------------------------------------------------------------- bugpatrol

class FakeOpenAI(BaseHTTPRequestHandler):
    calls: list = []

    def log_message(self, *a):  # quiet
        pass

    def do_GET(self):
        self._send({"ok": True})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            body = {}
        FakeOpenAI.calls.append({"path": self.path, "auth": self.headers.get("Authorization"),
                                 "model": body.get("model"), "tools": len(body.get("tools") or [])})
        self._send({"id": "pfy-smoke", "object": "chat.completion", "model": body.get("model"),
                    "choices": [{"index": 0, "finish_reason": "stop",
                                 "message": {"role": "assistant", "content": "done"}}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})

    def _send(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


def node_major(node: str) -> int:
    try:
        with tempfile.TemporaryDirectory(prefix="pfy-node-ver-") as home:
            out = subprocess.run(
                [node, "--version"], capture_output=True, text=True, timeout=30, env=node_version_env(home),
            ).stdout.strip()
        return int(out.lstrip("v").split(".")[0])
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0


def smoke_bugpatrol(r: dict) -> int:
    b = find_bin("BUGPATROL_BIN", "bugpatrol/node_modules/.bin/bugpatrol", "bugpatrol")
    r["bin"] = b
    if not b:
        r["reason"] = ("no bugpatrol. Operator: npm install --prefix ~/DEVELOP/pfy-mentat/tmp/bugpatrol bugpatrol@0.3.0 "
                       "(Apache-2.0; needs Node 22+, e.g. the official node-v22 linux-x64 tarball unpacked to "
                       "~/DEVELOP/pfy-mentat/tmp/bugpatrol/node). Not `npx bugpatrol` in a product checkout, no "
                       "`skills add`, no GitHub, no fixer, no paid provider key")
        return 2
    node = None
    for c in (os.environ.get("BUGPATROL_NODE"), str(TMP / "bugpatrol/node/bin/node"), shutil.which("node")):
        if c and os.path.isfile(c) and os.access(c, os.X_OK) and node_major(c) >= 22:
            node = c
            break
    r["node"] = node
    if not node:
        r["reason"] = "no Node 22+ (set $BUGPATROL_NODE or unpack node-v22 to ~/DEVELOP/pfy-mentat/tmp/bugpatrol/node)"
        return 2
    if not shutil.which("git"):
        r["reason"] = "git not on PATH"
        return 2
    js = os.path.realpath(b)
    FakeOpenAI.calls = []
    srv = ThreadingHTTPServer(("127.0.0.1", 0), FakeOpenAI)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    endpoint = f"http://127.0.0.1:{srv.server_address[1]}/v1/chat/completions"
    model = "pfy-local-smoke"

    def cfg(with_endpoint: bool) -> str:
        use = f"{{ runtime: model, via: custom, model: {model}" + (f", endpoint: {endpoint} }}" if with_endpoint else " }")
        return ("version: 1\napp:\n  platform: cli\n  source: .\n  setup: []\n  connect: { cli: { timeoutMs: 60000 } }\n"
                "  instructions: .bugpatrol/instructions.md\nagents:\n  explorer:\n    maxSteps: 2\n"
                f"    use: {use}\n  judge:\n    use: {use}\n  fixer:\n    enabled: false\n  github:\n    enabled: false\n")

    try:
        with tempfile.TemporaryDirectory(prefix="pfy-bugpatrol-") as d, \
                tempfile.TemporaryDirectory(prefix="pfy-bugpatrol-home-") as home:
            g = ["git", "-c", "user.email=smoke@localhost", "-c", "user.name=smoke"]
            run(["git", "init", "-q"], cwd=d)
            run(g + ["commit", "-q", "--allow-empty", "-m", "init"], cwd=d)
            run(["git", "remote", "add", "origin", "https://example.invalid/pfy-smoke.git"], cwd=d)
            Path(d, ".bugpatrol").mkdir()
            Path(d, ".bugpatrol/instructions.md").write_text("A CLI. Run `echo hello` once, report nothing, stop.\n")
            env = clean_env(home, BUGPATROL_MODEL_API_KEY="pfy-local-dummy",
                            PATH=os.path.dirname(node) + os.pathsep + os.environ.get("PATH", ""))

            def explore() -> subprocess.CompletedProcess | None:
                limit = xintake_timeout(120)
                try:
                    return subprocess.run([node, js, "explore", "--steps", "2"], cwd=d, capture_output=True,
                                          text=True, timeout=limit, env=env)
                except subprocess.TimeoutExpired:
                    r["reason"] = timeout_reason("bugpatrol explore", limit)
                    return None

            Path(d, ".bugpatrol/bugpatrol.yml").write_text(cfg(False))
            neg = explore()
            if neg is None:
                return 1
            r["no_endpoint_rc"] = neg.returncode
            r["no_endpoint_output"] = (neg.stdout + neg.stderr)[-300:]
            if neg.returncode == 0 or FakeOpenAI.calls:
                r["reason"] = "custom model with no endpoint was not refused"
                return 1
            Path(d, ".bugpatrol/bugpatrol.yml").write_text(cfg(True))
            p = explore()
            if p is None:
                return 1
    finally:
        srv.shutdown()
        srv.server_close()
    out = p.stdout + p.stderr
    r["rc"] = p.returncode
    r["output"] = out[-600:]
    r["calls"] = FakeOpenAI.calls[:10]
    r["call_count"] = len(FakeOpenAI.calls)
    if p.returncode != 0:
        r["reason"] = f"explore exited {p.returncode} against the local endpoint"
        return 1
    if not FakeOpenAI.calls:
        r["reason"] = "explore ran but never called the local custom endpoint"
        return 1
    bad = [c for c in FakeOpenAI.calls if not (c["path"].endswith("/chat/completions") and c["model"] == model
                                              and c["auth"] == "Bearer pfy-local-dummy")]
    if bad:
        r["reason"] = f"unexpected model call shape: {bad[:3]}"
        return 1
    if not any(c["tools"] for c in FakeOpenAI.calls):
        r["reason"] = "no call offered tools (explorer tool loop shape changed?)"
        return 1
    m = re.search(r"(\d+) candidate\(s\) raised", out)
    if not m:
        r["reason"] = "no candidate summary in output (CLI output shape changed?)"
        return 1
    r["candidates"] = int(m.group(1))
    if r["candidates"] != 0:
        r["reason"] = "candidates raised by a model that never called a tool (false positive)"
        return 1
    return 0


# ---------------------------------------------------------------- graphjin

def gql(port: int, query: str) -> dict:
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/v1/graphql", data=json.dumps({"query": query}).encode(),
                                 headers={"content-type": "application/json", "X-User-ID": "1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read() or b"{}")
        except ValueError:
            return {"errors": [f"http {e.code}"]}
    except (urllib.error.URLError, ValueError, OSError) as e:
        return {"errors": [f"transport: {e}"]}


def graphjin_world(b: str, read_only: bool, production: bool, r: dict, tag: str) -> tuple[dict, list] | None:
    """Start graphjin on a fresh seeded SQLite db, run the probes, stop it. Returns (results, rows) or None."""
    import sqlite3
    with tempfile.TemporaryDirectory(prefix="pfy-graphjin-") as d, \
            tempfile.TemporaryDirectory(prefix="pfy-graphjin-home-") as home:
        db = os.path.join(d, "app.db")
        c = sqlite3.connect(db)
        c.execute("create table notes(id integer primary key, body text not null)")
        c.executemany("insert into notes(body) values(?)", [("alpha",), ("beta",)])
        c.commit()
        c.close()
        port = free_port()
        cfgdir = Path(d, "config")
        (cfgdir / "queries").mkdir(parents=True)
        (cfgdir / "queries/getNotes.graphql").write_text("query getNotes {\n  notes { id body }\n}\n")
        (cfgdir / "dev.yml").write_text(
            f'app_name: pfy smoke\nhost_port: 127.0.0.1:{port}\nweb_ui: false\nlog_level: "warn"\n'
            f"production: {'true' if production else 'false'}\nsecret_key: pfy-smoke-not-a-secret\n"
            "auth:\n  type: none\n  development: true\nsources:\n  - name: app\n    kind: database\n"
            f"    default: true\n    type: sqlite\n    path: {db}\n    read_only: {'true' if read_only else 'false'}\n"
            "    access:\n      read: authenticated\n      write: authenticated\n      delete: authenticated\n"
            "      missing_namespace_column: allow\n")
        log = open(os.path.join(d, "serve.log"), "w")
        try:
            proc = subprocess.Popen([b, "serve", "--path", str(cfgdir)], cwd=d, stdout=log, stderr=subprocess.STDOUT,
                                    env=clean_env(home))
        except Exception:
            log.close()
            raise
        try:
            deadline = time.time() + xintake_timeout(60)
            up = False
            while time.time() < deadline and proc.poll() is None:
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2):
                        up = True
                        break
                except (urllib.error.URLError, OSError):
                    time.sleep(0.5)
            if not up:
                log.flush()
                r[f"{tag}_log"] = Path(d, "serve.log").read_text(errors="replace")[-600:]
                r["reason"] = f"graphjin did not come up ({tag})"
                return None
            q = "query getNotes { notes { id body } }" if production else "query { notes { id body } }"
            res = {"read": gql(port, q)}
            if production:
                res["adhoc"] = gql(port, "query adhoc { notes { body } }")
            res["insert"] = gql(port, 'mutation { notes(insert: {body: "evil"}) { id } }')
            res["update"] = gql(port, 'mutation { notes(where: {id: {eq: 1}}, update: {body: "x"}) { id } }')
            res["delete"] = gql(port, "mutation { notes(where: {id: {eq: 2}}, delete: true) { id } }")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
            log.close()
        c = sqlite3.connect(db)
        rows = c.execute("select id, body from notes order by id").fetchall()
        c.close()
    return res, rows


def smoke_graphjin(r: dict) -> int:
    b = find_bin("GRAPHJIN_BIN", "graphjin/graphjin", "graphjin")
    r["bin"] = b
    if not b:
        r["reason"] = ("no graphjin binary. Operator: download graphjin_3.21.6_linux_amd64.tar.gz and checksums.txt "
                       "from https://github.com/dosco/graphjin/releases/tag/v3.21.6, verify, and extract `graphjin` "
                       f"to ~/DEVELOP/pfy-mentat/tmp/graphjin/graphjin (binary sha256 {GRAPHJIN_V3216_SHA256}). "
                       "Not the .deb, not `npm install -g`, never pointed at a real product database")
        return 2
    expect = pinned(r, "GRAPHJIN_SHA256", GRAPHJIN_V3216_SHA256, lower=True)
    digest = sha256_file(b)
    r["sha256"] = digest
    if digest != expect:
        r["reason"] = f"sha256 mismatch: graphjin binary is {digest}, expected {expect}"
        return 2
    seeded = [(1, "alpha"), (2, "beta")]

    ro = graphjin_world(b, read_only=True, production=False, r=r, tag="read_only")
    if ro is None:
        return 1
    res, rows = ro
    r["read_only"] = {k: v for k, v in res.items()}
    r["read_only_rows"] = rows
    got = [(n.get("id"), n.get("body")) for n in ((res["read"].get("data") or {}).get("notes") or [])]
    if got != seeded:
        r["reason"] = f"read under read_only did not return the seeded rows: {res['read']}"
        return 1
    allowed = [k for k in ("insert", "update", "delete") if not res[k].get("errors")]
    if allowed or rows != seeded:
        r["reason"] = f"write allowed under read_only: {allowed or 'db changed'}"
        return 1

    ctl = graphjin_world(b, read_only=False, production=False, r=r, tag="control")
    if ctl is None:
        return 1
    res, rows = ctl
    r["control_insert"] = res["insert"]
    if res["insert"].get("errors") or not any(body == "evil" for _, body in rows):
        r["reason"] = "control run (read_only false) refused the insert too; the read_only check proves nothing"
        return 1

    prod = graphjin_world(b, read_only=False, production=True, r=r, tag="production")
    if prod is None:
        return 1
    res, rows = prod
    r["production"] = {"saved": res["read"], "adhoc": res["adhoc"], "insert": res["insert"]}
    saved = [(n.get("id"), n.get("body")) for n in ((res["read"].get("data") or {}).get("notes") or [])]
    if saved != seeded:
        r["reason"] = f"saved query did not run in production: {res['read']}"
        return 1
    if not res["adhoc"].get("errors") or (res["adhoc"].get("data") or {}).get("notes"):
        r["reason"] = "ad-hoc query ran in production (allow-list not enforced)"
        return 1
    if rows != seeded:
        r["reason"] = "ad-hoc mutation changed the db in production (allow-list not enforced)"
        return 1
    return 0


# ---------------------------------------------------------------- antislop

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def frontmatter(text: str) -> dict | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    out: dict = {}
    for ln in lines[1:]:
        if ln.strip() == "---":
            return out
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", ln)
        if m:
            v = m.group(2).strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            out[m.group(1)] = v
    return None  # unterminated


def skill_problems(folder: str, text: str) -> list[str]:
    fm = frontmatter(text)
    if fm is None:
        return ["no YAML frontmatter block"]
    p = []
    name, desc = fm.get("name", ""), fm.get("description", "")
    if not name:
        p.append("missing name")
    elif not NAME_RE.match(name) or len(name) > 64:
        p.append(f"invalid name {name!r}")
    elif name != folder:
        p.append(f"name {name!r} != folder {folder!r}")
    if not desc:
        p.append("missing description")
    elif len(desc) > 1024:
        p.append("description over 1024 chars")
    return p


def smoke_antislop(r: dict) -> int:
    d = None
    for c in (os.environ.get("ANTISLOP_DIR"), str(TMP / "anti-slop")):
        if c and os.path.isdir(os.path.join(c, "skills")):
            d = c
            break
    r["dir"] = d
    if not d:
        r["reason"] = ("no anti-slop clone. Operator: git clone https://github.com/miqdadbadjuber/anti-slop "
                       "~/DEVELOP/pfy-mentat/tmp/anti-slop (MIT). Do not run `npx antislop-ai` or copy skills into "
                       "any harness skill folder for this smoke")
        return 2
    selftest = {"Bad_Name": "---\nname: Bad_Name\ndescription: x\n---\n", "no-desc": "---\nname: no-desc\n---\n"}
    if any(not skill_problems(f, t) for f, t in selftest.items()):
        r["reason"] = "validator accepted a synthetic bad skill (smoke bug)"
        return 1
    if shutil.which("git") and os.path.isdir(os.path.join(d, ".git")):
        r["commit"] = run(["git", "-C", d, "rev-parse", "HEAD"], timeout=30).stdout.strip()
    skills = sorted(Path(d, "skills").glob("*/SKILL.md"))
    r["skills"] = {}
    for s in skills:
        r["skills"][s.parent.name] = skill_problems(s.parent.name, s.read_text(errors="replace")) or "ok"
    if not skills:
        r["reason"] = "no skills/*/SKILL.md found"
        return 1
    bad = {k: v for k, v in r["skills"].items() if v != "ok"}
    if bad:
        r["reason"] = f"invalid skill frontmatter: {bad}"
        return 1
    if "antislop" not in r["skills"]:
        r["reason"] = "core `antislop` skill missing"
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", required=True, choices=["bugpatrol", "graphjin", "antislop"])
    a = ap.parse_args()
    receipt = {"entry": a.entry, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "host": os.uname().nodename}
    bad = timeout_problem()
    if bad:
        receipt["reason"] = bad
        return write(a.entry, receipt, 2)
    code = {"bugpatrol": smoke_bugpatrol, "graphjin": smoke_graphjin, "antislop": smoke_antislop}[a.entry](receipt)
    return write(a.entry, receipt, code)


if __name__ == "__main__":
    sys.exit(main())
