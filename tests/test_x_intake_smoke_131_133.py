"""Entries 131-133 smokes (JevAgentHarness, ai-memory, headson): pins and missing prereqs exit 2, wrong routes, broken
claim-once, budget overruns and real-HOME changes FAIL, timeouts FAIL with the real-HOME check kept.

Each tool is a small Python stub (shebang = this interpreter) that behaves like the real CLI for what the smoke does;
knobs are baked into the stub text because the smoke gives its children a clean env. The jah stub is a tiny fake proxy
(reads the cfg the driver writes, routes, calls the driver's stub upstream and stub Jev, writes steps.jsonl); the
ai-memory stub keeps pages and messages in the data dir and serves /healthz. Parent HOME is a temp dir this test owns;
children get another temp HOME, so a planted real-HOME write uses the parent HOME's absolute path. bwrap is found on the
smoke process PATH, so tests that need a plant to land set PATH to an empty dir (children use a fixed system PATH).
Receipts go to a temp $PFY_SMOKE_RECEIPT_DIR.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "examples/x-intake-local/smoke_131_133.py"
_RECEIPTS = tempfile.TemporaryDirectory(prefix="pfy-xintake-131-receipts-")
RECEIPT_DIR = Path(_RECEIPTS.name)


def tearDownModule() -> None:
    _RECEIPTS.cleanup()


def _write_stub(path: Path, knobs: dict, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!{sys.executable}\nK = {knobs!r}\n" + body, encoding="utf-8")
    path.chmod(0o755)
    return path


COMMON = r'''
import json, os, re, sys, time
if K.get("plant"):
    exec(K["plant"])
'''

JAH_BODY = COMMON + r'''
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
a = sys.argv[1:]
if a[:1] == ["--version"]:
    time.sleep(K.get("sleep_version", 0))
    print("jah " + K.get("version", "0.1.0"))
    sys.exit(0)
if a[:1] != ["serve"] or K.get("no_serve"):
    sys.exit(3)
cfg = open(a[a.index("-c") + 1]).read()
port = int(re.search(r"port: (\d+)", cfg).group(1))
logs = re.search(r"log_dir: (\S+)", cfg).group(1)
urls = re.findall(r'base_url: "([^"]+)"', cfg)
upstream, jev = urls[0], (urls[1] if len(urls) > 1 else None)
os.makedirs(logs, exist_ok=True)
ERR = re.compile(r"Traceback|Error|failed")


def post(url, body, auth=False):
    h = {"Content-Type": "application/json"}
    if auth:
        h["Authorization"] = "Bearer stub-not-a-key"
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(body).encode(), headers=h),
                                             timeout=10).read())


def call(model, msgs, tools):
    return post(upstream + "/chat/completions", {"model": model, "messages": msgs, "tools": tools},
                auth=K.get("send_auth", False))["choices"][0]["message"]


class H(BaseHTTPRequestHandler):
    def log_message(self, *x):
        pass

    def reply(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self.reply({"tier_share": {}})

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        msgs, tools = req["messages"], req.get("tools")
        step = sum(1 for m in msgs if m["role"] == "assistant")
        out = msgs[-1].get("content") or "" if msgs[-1]["role"] == "tool" else ""
        why = None
        if step < 1 or K.get("all_strong"):
            tier, reason = "strong", "first_steps"
        elif jev is None:
            hard = bool(ERR.search(out))
            tier, reason, why = ("strong", "hard", "error_signal") if hard else ("fast", "routine", "no_signal")
        elif K.get("jev_ignore"):
            tier, reason = "fast", "routine"
        else:
            try:
                d = post(jev + "/v1/systemone", {"state": out, "model": "agentdecision-4b", "questions": {
                    "next_step": {"type": "choice", "criteria": {"hard": None, "routine": None}}}})
                p = d["answers"]["next_step"]["probabilities"]["hard"]
                tier, reason = ("strong", "hard") if p >= 0.75 else ("fast", "routine")
            except Exception:
                tier, reason = ("fast" if K.get("on_error_fast") else "strong"), "decision_error"
        m = call("stub-" + tier, msgs, tools)
        calls = [tier]
        if tier == "fast" and not m.get("tool_calls") and not K.get("no_finish"):
            m, tier, reason = call("stub-strong", msgs, tools), "strong", "finish_check"
            calls.append("strong")
        rec = {"step": step, "tier": tier, "reason": reason, "decision": {"why": why},
               "calls": [{"tier": c} for c in calls]}
        if K.get("log_prompt"):
            rec["task"] = msgs[1]["content"]
        with open(os.path.join(logs, "steps.jsonl"), "a") as f:
            f.write(json.dumps(rec) + "\n")
        with open(os.path.join(logs, "decisions.jsonl"), "a") as f:
            f.write(json.dumps({"step": step}) + "\n")
        self.reply({"choices": [{"index": 0, "message": m}]})


HTTPServer(("127.0.0.1", port), H).serve_forever()
'''

AIM_BODY = COMMON + r'''
from http.server import BaseHTTPRequestHandler, HTTPServer
a = sys.argv[1:]
if a[:1] == ["--version"]:
    print("ai-memory " + K.get("version", "3.1.1"))
    sys.exit(0)
D = a[a.index("--data-dir") + 1]
a = a[a.index("--data-dir") + 2:]
cmd, proj = a[0], os.path.basename(os.getcwd())
state_p = os.path.join(D, "state.json")


def load():
    return json.load(open(state_p)) if os.path.exists(state_p) else {"pages": {}, "msgs": []}


def save(s):
    json.dump(s, open(state_p, "w"))


def opt(name):
    return a[a.index(name) + 1] if name in a else None


if cmd == "init":
    for d in ("wiki", "db", "raw"):
        os.makedirs(os.path.join(D, d), exist_ok=True)
    sys.exit(0)
if cmd == "serve":
    if K.get("never_healthy"):
        time.sleep(600)
    host, port = opt("--bind").split(":")

    class H(BaseHTTPRequestHandler):
        def log_message(self, *x):
            pass

        def do_GET(self):
            self.send_response(200 if self.path == "/healthz" else 404)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"ok")

    HTTPServer((host, int(port)), H).serve_forever()
s = load()
if cmd == "write-page":
    path, body = opt("--path"), opt("--body")
    s["pages"].setdefault(proj, {})[path] = body
    if not K.get("no_wiki_file"):
        f = os.path.join(D, "wiki", proj, path)
        os.makedirs(os.path.dirname(f), exist_ok=True)
        open(f, "w").write(body)
    save(s)
    print("wrote %s (page_id=1) under default/%s" % (path, proj))
elif cmd == "search":
    q = a[1]
    hits = [(p, b) for p, b in s["pages"].get(proj, {}).items() if q in b or K.get("search_always_hit")]
    if hits:
        print("%d result(s) for %r:" % (len(hits), q))
        for p, b in hits:
            print("  " + p + "\n    " + b)
    else:
        print("no results for %r" % q)
elif cmd == "read-page":
    p = opt("--path")
    print("path: %s\n\n%s" % (p, s["pages"].get(proj, {}).get(p, "")))
elif cmd == "message" and a[1] == "send":
    s["msgs"].append({"id": str(len(s["msgs"]) + 1), "to": opt("--to-project"), "body": a[-1], "state": "pending"})
    save(s)
    print(json.dumps({"message_id": s["msgs"][-1]["id"]}))
elif cmd == "message" and a[1] == "pop":
    m = next((m for m in s["msgs"] if m["to"] == proj and m["state"] == "pending"), None)
    if m and not K.get("double_pop"):
        m["state"] = "claimed"
    save(s)
    out = dict(m, state="claimed") if m else None
    note = None if (K.get("no_notice") or not m) else "UNTRUSTED cross-project input"
    print(json.dumps({"message": out, "security_notice": note}))
else:
    sys.exit(4)
'''

HSON_BODY = COMMON + r'''
a = sys.argv[1:]
if a[:1] == ["--version"]:
    time.sleep(K.get("sleep_version", 0))
    print("hson " + K.get("version", "0.17.1"))
    sys.exit(0)
time.sleep(K.get("sleep", 0))
src = a[-1]
d = json.load(open(src))
rows = d["results"]
pick = rows[-3:] if ("--tail" in a and not K.get("tail_ignored")) else rows[:3]
out = {"meta": d["meta"], "results": [{"id": x["id"], "verdict": x["verdict"]} for x in pick], "run": d["run"]}
if "--grep" in a and not K.get("no_grep"):
    out["results"].insert(1, {"verdict": "FAIL"})
if K.get("drop_key"):
    out.pop("meta")
if K.get("nondet"):
    out["run"] = str(time.time_ns())
if K.get("over_budget"):
    out["run"] = "y" * 700
if K.get("mutate_fixture"):
    open(src, "a").write(" ")
print("{ not json" if K.get("not_json") else json.dumps(out, indent=2))
'''


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory(prefix="pfy-xintake-131-test-")
        self.base = Path(self._td.name)
        self.home = self.base / "realhome"
        self.home.mkdir()
        self.nobwrap = self.base / "emptypath"
        self.nobwrap.mkdir()

    def tearDown(self) -> None:
        for p in self.base.rglob("*"):  # a seeded 0000 file must stay removable
            if not p.is_symlink():
                p.chmod(0o755 if p.is_dir() else 0o644)
        self._td.cleanup()

    def env(self, *, no_bwrap: bool = False, **extra: str) -> dict[str, str]:
        env = os.environ.copy()
        for key in list(env):
            if key.startswith(("JAH_", "AI_MEMORY_", "HSON_")) or key == "PFY_XINTAKE_TIMEOUT":
                env.pop(key, None)
        env["HOME"] = str(self.home)  # so $PFY_TMP lookups find nothing
        env["PFY_SMOKE_RECEIPT_DIR"] = str(RECEIPT_DIR)
        if no_bwrap:
            env["PATH"] = str(self.nobwrap)
        env.update(extra)
        return env

    def run_entry(self, entry: str, env: dict[str, str]) -> tuple[int, dict]:
        p = subprocess.run([sys.executable, SCRIPT, "--entry", entry], cwd=str(ROOT), env=env,
                           capture_output=True, text=True, timeout=180)
        self.assertNotIn("Traceback", p.stderr + p.stdout)
        receipt = json.loads((RECEIPT_DIR / entry / "latest.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["exit_code"], p.returncode)
        return p.returncode, receipt

    def stub(self, entry: str, **knobs) -> dict[str, str]:
        name, var, body = {"jah": ("jah", "JAH_BIN", JAH_BODY), "aimemory": ("ai-memory", "AI_MEMORY_BIN", AIM_BODY),
                           "headson": ("hson", "HSON_BIN", HSON_BODY)}[entry]
        return {var: str(_write_stub(self.base / "bin" / name, knobs, body))}

    def go(self, entry: str, *, no_bwrap: bool = False, timeout: str = "", **knobs) -> tuple[int, dict]:
        extra = self.stub(entry, **knobs)
        if timeout:
            extra["PFY_XINTAKE_TIMEOUT"] = timeout
        return self.run_entry(entry, self.env(no_bwrap=no_bwrap, **extra))

    def plant_home(self, rel: str) -> str:
        target = self.home / rel
        return f"import pathlib; p = pathlib.Path({str(target)!r}); p.mkdir(parents=True, exist_ok=True); " \
               "(p / 'x').write_text('planted')"

    def assert_failed(self, code: int, r: dict, check: str) -> None:
        self.assertEqual(code, 1, r)
        self.assertFalse(r["checks"][check], r)
        self.assertIn(check, r["reason"])

    def assert_home_changed(self, r: dict, rel: str) -> None:
        self.assertFalse(r["checks"]["real_home_untouched"], r)
        self.assertIn(f"~/{rel}", r["real_home_changed"])
        self.assertIn(f"~/{rel}", r["reason"])


# ---------------------------------------------------------------- headson
class HeadsonTests(Base):
    def test_missing_binary_exits_2(self) -> None:
        code, r = self.run_entry("headson", self.env(HSON_BIN=str(self.base / "nope")))
        self.assertEqual(code, 2)
        self.assertIn("hson not found", r["reason"])

    def test_version_mismatch_exits_2(self) -> None:
        code, r = self.go("headson", version="0.16.0")
        self.assertEqual(code, 2)
        self.assertIn("0.16.0", r["reason"])

    def test_happy_path_passes(self) -> None:
        code, r = self.go("headson")
        self.assertEqual(code, 0, r)
        self.assertTrue(all(r["checks"].values()), r)
        self.assertIn("~/.local/state/headson", r["reason"])

    def test_over_budget_fails(self) -> None:
        self.assert_failed(*self.go("headson", over_budget=True), "head_within_600_bytes")

    def test_dropped_key_fails(self) -> None:
        self.assert_failed(*self.go("headson", drop_key=True), "head_keeps_top_level_keys")

    def test_not_json_fails(self) -> None:
        self.assert_failed(*self.go("headson", not_json=True), "head_is_strict_json")

    def test_nondeterministic_fails(self) -> None:
        self.assert_failed(*self.go("headson", nondet=True), "deterministic_rerun")

    def test_tail_ignored_fails(self) -> None:
        self.assert_failed(*self.go("headson", tail_ignored=True), "tail_keeps_last_result")

    def test_grep_dropped_fails(self) -> None:
        self.assert_failed(*self.go("headson", no_grep=True), "grep_keeps_fail_value")

    def test_fixture_write_fails(self) -> None:
        self.assert_failed(*self.go("headson", mutate_fixture=True), "fixture_untouched")

    def test_temp_home_write_fails(self) -> None:
        plant = "import os; open(os.path.join(os.environ['HOME'], 'x'), 'w').write('x')"
        self.assert_failed(*self.go("headson", plant=plant), "home_untouched")

    def test_real_home_write_fails_without_bwrap(self) -> None:
        code, r = self.go("headson", no_bwrap=True, plant=self.plant_home(".local/state/headson"))
        self.assertEqual(code, 1)
        self.assert_home_changed(r, ".local/state/headson")

    def test_real_home_chmod_only_fails(self) -> None:
        d = self.home / ".local/state/headson"
        d.mkdir(parents=True)
        (d / "s.json").write_text("{}")
        (d / "s.json").chmod(0o644)
        code, r = self.go("headson", no_bwrap=True, plant=f"import os; os.chmod({str(d / 's.json')!r}, 0o600)")
        self.assertEqual(code, 1)
        self.assert_home_changed(r, ".local/state/headson")

    def test_seeded_real_home_untouched_passes(self) -> None:
        d = self.home / ".local/state/headson/sessions"
        d.mkdir(parents=True)
        (d / "old.json").write_text("{}")
        code, r = self.go("headson", no_bwrap=True)
        self.assertEqual(code, 0, r)
        self.assertTrue(r["checks"]["real_home_untouched"])

    def test_timeout_fails_and_keeps_home_check(self) -> None:
        code, r = self.go("headson", no_bwrap=True, timeout="1", sleep_version=5,
                          plant=self.plant_home(".local/state/headson"))
        self.assertEqual(code, 1)
        self.assertIn("hson version timeout after 1s", r["reason"])
        self.assertFalse(r["checks"]["body_completed"])
        self.assert_home_changed(r, ".local/state/headson")


# ---------------------------------------------------------------- jah
class JahTests(Base):
    def test_missing_binary_exits_2(self) -> None:
        code, r = self.run_entry("jah", self.env(JAH_BIN=str(self.base / "nope")))
        self.assertEqual(code, 2)
        self.assertIn("jah not found", r["reason"])

    def test_version_mismatch_exits_2(self) -> None:
        code, r = self.go("jah", version="0.2.0")
        self.assertEqual(code, 2)
        self.assertIn("0.2.0", r["reason"])

    def test_happy_path_passes(self) -> None:
        code, r = self.go("jah")
        self.assertEqual(code, 0, r)
        self.assertTrue(all(r["checks"].values()), r)
        self.assertEqual([s["reason"] for s in r["rules"]["steps"]], ["first_steps", "routine", "hard", "finish_check"])
        self.assertEqual([s["reason"] for s in r["jev"]["steps"]], ["first_steps", "routine", "hard",
                                                                   "decision_error"])

    def test_no_routing_fails(self) -> None:
        self.assert_failed(*self.go("jah", all_strong=True), "rules_tiers")

    def test_missing_finish_check_fails(self) -> None:
        self.assert_failed(*self.go("jah", no_finish=True), "rules_finish_redone_by_strong")

    def test_jev_never_asked_fails(self) -> None:
        self.assert_failed(*self.go("jah", jev_ignore=True), "jev_wire_systemone")

    def test_decision_error_routed_fast_fails(self) -> None:
        self.assert_failed(*self.go("jah", on_error_fast=True), "jev_tiers")

    def test_prompt_text_in_logs_fails(self) -> None:
        self.assert_failed(*self.go("jah", log_prompt=True), "logs_hold_no_prompt_text")

    def test_auth_header_upstream_fails(self) -> None:
        self.assert_failed(*self.go("jah", send_auth=True), "no_auth_header_anywhere")

    def test_proxy_that_never_starts_fails(self) -> None:
        self.assert_failed(*self.go("jah", no_serve=True, timeout="8"), "rules_proxy_up")

    def test_temp_home_write_fails(self) -> None:
        plant = "import os; open(os.path.join(os.environ['HOME'], 'x'), 'w').write('x')"
        self.assert_failed(*self.go("jah", plant=plant), "home_untouched")

    def test_real_home_write_fails_without_bwrap(self) -> None:
        code, r = self.go("jah", no_bwrap=True, plant=self.plant_home(".jah"))
        self.assertEqual(code, 1)
        self.assert_home_changed(r, ".jah")

    def test_timeout_fails_and_keeps_home_check(self) -> None:
        code, r = self.go("jah", no_bwrap=True, timeout="1", sleep_version=5, plant=self.plant_home(".jah"))
        self.assertEqual(code, 1)
        self.assertIn("jah version timeout after 1s", r["reason"])
        self.assert_home_changed(r, ".jah")


# ---------------------------------------------------------------- aimemory
class AiMemoryTests(Base):
    def test_missing_binary_exits_2(self) -> None:
        code, r = self.run_entry("aimemory", self.env(AI_MEMORY_BIN=str(self.base / "nope")))
        self.assertEqual(code, 2)
        self.assertIn("ai-memory not found", r["reason"])

    def test_version_mismatch_exits_2(self) -> None:
        code, r = self.go("aimemory", version="3.0.0")
        self.assertEqual(code, 2)
        self.assertIn("3.0.0", r["reason"])

    def test_happy_path_passes(self) -> None:
        code, r = self.go("aimemory")
        self.assertEqual(code, 0, r)
        self.assertTrue(all(r["checks"].values()), r)

    def test_claimed_twice_fails(self) -> None:
        self.assert_failed(*self.go("aimemory", double_pop=True), "second_pop_empty")

    def test_no_markdown_on_disk_fails(self) -> None:
        self.assert_failed(*self.go("aimemory", no_wiki_file=True), "wiki_markdown_on_disk")

    def test_search_false_positive_fails(self) -> None:
        self.assert_failed(*self.go("aimemory", search_always_hit=True), "search_miss_is_empty")

    def test_missing_untrusted_notice_fails(self) -> None:
        self.assert_failed(*self.go("aimemory", no_notice=True), "pop_marks_message_untrusted")

    def test_server_never_healthy_fails(self) -> None:
        self.assert_failed(*self.go("aimemory", never_healthy=True, timeout="8"), "server_healthy")

    def test_temp_home_write_fails(self) -> None:
        plant = "import os; open(os.path.join(os.environ['HOME'], 'x'), 'w').write('x')"
        self.assert_failed(*self.go("aimemory", plant=plant), "home_untouched")

    def test_real_home_write_fails_without_bwrap(self) -> None:
        code, r = self.go("aimemory", no_bwrap=True, plant=self.plant_home(".config/ai-memory"))
        self.assertEqual(code, 1)
        self.assert_home_changed(r, ".config/ai-memory")
        self.assertNotIn("~/.local/share/ai-memory", r["real_home_changed"])


if __name__ == "__main__":
    unittest.main()
