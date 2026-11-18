"""Entries 140-142 smokes (Chiasmus, Tracekit, Charlotte): pins and missing prereqs exit 2, wrong solver answers, a
leaky policy, an unverifiable or over-trusting bundle, a page tool that leaks detail or breaks the form, misplaced
writes and real-HOME changes FAIL, timeouts FAIL with the real-HOME check kept. Every one of the 46 checks the smoke
records has a test here that turns it false (body_completed and real_home_untouched through the timeout and plant tests).

Each tool is a small Python stub (shebang = this interpreter) that behaves like the real thing for what the smoke does;
knobs are baked into the stub text because the smoke gives its children a clean env. Chiasmus and Charlotte are Node
MCP servers, so the stub is a fake `node` that answers `--version` and speaks newline-delimited JSON-RPC on stdio
(Chiasmus: a tiny Z3/Prolog/call-graph imitation over the fixtures; Charlotte: reads the fixture page, keeps element
ids, runs the form on click, ignores stdin EOF like 0.8.0 and cleans its fake profile dir on exit). Tracekit is Python,
so the stub is a fake venv: bin/python puts a fake `tracekit` package (policy, approvals, a hash-chained bundle with a
witness file) first on sys.path and execs this interpreter, and bin/tracekit is a fake `verify`. Parent HOME is a temp
dir this test owns; children get another temp HOME, so a planted real-HOME write uses the parent HOME's absolute path.
bwrap is found on the smoke process PATH, so tests that need a plant to land set PATH to an empty dir (children use a
fixed system PATH). Receipts go to a temp $PFY_SMOKE_RECEIPT_DIR.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "examples/x-intake-local/smoke_140_142.py"
_RECEIPTS = tempfile.TemporaryDirectory(prefix="pfy-xintake-140-receipts-")
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
a = sys.argv[1:]
if a == ["--version"]:
    time.sleep(K.get("sleep_version", 0))
    print("v" + K.get("node", "24.14.1"))
    sys.exit(0)
time.sleep(K.get("sleep_server", 0))


def serve(handle):
    for line in sys.stdin:
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if "id" not in m:
            continue
        res = handle(m["method"], m.get("params") or {})
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": m["id"], "result": res}) + "\n")
        sys.stdout.flush()


def text(obj):
    return {"content": [{"type": "text", "text": json.dumps(obj)}]}
'''

# fake node for chiasmus: `node --version`, `node mcp-server.js` (MCP on stdio)
CHI_NODE = COMMON + r'''
TOOLS = ["chiasmus_craft", "chiasmus_formalize", "chiasmus_graph", "chiasmus_lint", "chiasmus_map", "chiasmus_review",
         "chiasmus_skills", "chiasmus_solve", "chiasmus_verify"]
home = os.environ["HOME"] + "/.chiasmus" if K.get("db_to_home") else os.environ.get("CHIASMUS_HOME")
if home and not K.get("no_db"):
    os.makedirs(home, exist_ok=True)
    open(os.path.join(home, "chiasmus.db"), "w").write("db")


def graph(files):
    defs, calls = [], {}
    for f in files:
        cur = None
        for line in open(f):
            m = re.match(r"def (\w+)", line)
            if m:
                cur = m.group(1)
                defs.append(cur)
                calls[cur] = set()
            elif cur:
                calls[cur] |= set(re.findall(r"(\w+)\(", line))
    return defs, calls


def reach(calls, a, b, seen=None):
    seen = seen or set()
    for c in calls.get(a, ()):
        if c == b or (c not in seen and reach(calls, c, b, seen | {c})):
            return True
    return False


def call(name, args):
    if name == "chiasmus_verify" and args["solver"] == "z3":
        if "(< x 5)" in args["input"]:
            core = re.findall(r":named (\w+)", args["input"])
            return {"status": "unsat", "unsatCore": core[:1] if K.get("short_core") else core}
        return {"status": "sat", "model": {"x": "20" if K.get("bad_model") else "11"}}
    if name == "chiasmus_verify":
        edges = {}
        for x, y in re.findall(r"edge\((\w+), (\w+)\)", args["input"]):
            edges.setdefault(x, set()).add(y)
        x, y = re.match(r"reach\((\w+), (\w+)\)", args["query"]).groups()
        ok = (reach(edges, x, y) or K.get("prolog_always_true")) and not K.get("prolog_never_true")
        return {"status": "success", "answers": [{"bindings": {}, "formatted": "true"}] if ok else []}
    if name == "chiasmus_graph":
        defs, calls = graph(args["files"])
        if args["analysis"] == "dead-code":
            called = set().union(*calls.values())
            dead = [d for d in defs if d not in called]
            return {"analysis": "dead-code", "result": defs if K.get("all_dead") else dead}
        if args["analysis"] == "reachability":
            ok = (reach(calls, args["from"], args["to"]) or K.get("reach_always")) and not K.get("reach_never")
            return {"analysis": "reachability", "result": {"reachable": bool(ok)}}
        if args["analysis"] == "impact":
            res = sorted(d for d in defs if reach(calls, d, args["target"]))
            return {"analysis": "impact", "result": res[:1] if K.get("short_impact") else res}
    if name == "chiasmus_lint":
        bal = args["input"].count("(") - args["input"].count(")")
        errs = [] if bal == 0 or K.get("lint_silent") else ["Unbalanced parentheses: %d unclosed" % bal]
        return {"spec": args["input"], "fixes": [], "errors": errs}
    if name == "chiasmus_skills":
        return [] if K.get("no_skills") else [{"template": {"name": "policy-contradiction"}}]
    return {"error": "unknown"}


def handle(method, p):
    if method == "initialize":
        return {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                "serverInfo": {"name": "chiasmus", "version": K.get("server_version", "0.1.40")}}
    if method == "tools/list":
        names = TOOLS[:-1] if K.get("fewer_tools") else TOOLS + ["chiasmus_search"] if K.get("more_tools") else TOOLS
        return {"tools": [{"name": t} for t in names]}
    if method == "tools/call":
        if K.get("die_on_graph") and p["name"] == "chiasmus_graph":
            sys.exit(3)
        if K.get("mutate_fixture") and p["name"] == "chiasmus_graph":
            open(p["arguments"]["files"][0], "a").write("\n")
        return text(call(p["name"], p["arguments"]))
    return {}


serve(handle)
'''

# fake node for charlotte: `node --version`, `node index.js --profile core --no-sandbox` (MCP on stdio)
CH_NODE = COMMON + r'''
import signal
TOOLS = ["charlotte_click", "charlotte_find", "charlotte_navigate", "charlotte_observe", "charlotte_submit",
         "charlotte_tools", "charlotte_type"]
assert os.environ.get("PUPPETEER_EXECUTABLE_PATH"), "no chrome"
prof = os.path.join(os.environ.get("TMPDIR", "/tmp"), "puppeteer_dev_chrome_profile-stub")
os.makedirs(prof, exist_ok=True)
if K.get("chrome_home"):
    os.makedirs(os.path.join(os.environ["HOME"], ".config/google-chrome"), exist_ok=True)


def bye(*_):
    if not K.get("leave_profile"):
        os.rmdir(prof)
    sys.exit(0)


signal.signal(signal.SIGTERM, signal.SIG_IGN if K.get("ignore_term") else bye)
page = {}
EL = [{"id": "inp-78124e", "type": "text_input", "label": "Order number", "value": ""},
      {"id": "btn-08d93f", "type": "button", "label": "Look up"}, {"id": "lnk-de8dfd", "type": "link", "label": "Help"}]


def snap(detail):
    s = {"title": page["title"], "interactive_summary": {"total": 3}}
    if detail == "minimal":
        if K.get("leak_ids"):
            s["interactive"] = EL
        if K.get("leak_text"):
            s["text"] = page["body"]
        return s
    s["interactive"] = [dict(e, id=e["id"] + ("x" if K.get("unstable_ids") and detail == "full" else "")) for e in EL]
    if K.get("swap_labels"):
        s["interactive"][0]["label"] = "Look up"
    if detail == "full":
        s["text"] = ("" if K.get("full_no_text") else page["body"]) + (" Result for " + page.get("q", "") if page.get("submitted") else "")
    return s


def call(name, a):
    if name == "charlotte_navigate":
        html = open(a["url"][len("file://"):]).read()
        page.update(title=re.search(r"<title>(.*?)</title>", html).group(1),
                    body=re.sub(r"<[^>]+>", " ", html.split("<body>")[1]))
        return snap("minimal")
    if name == "charlotte_observe":
        return snap(a.get("detail", "summary"))
    if name == "charlotte_find":
        return {"elements": [e for e in EL if a["text"] in e["label"]][: 0 if K.get("find_nothing") else 9]}
    if name == "charlotte_type":
        page["q"] = a["text"]
        return snap("summary")
    if name == "charlotte_click":
        if a["element_id"] not in [e["id"] for e in EL]:
            if K.get("bad_id_ok"):
                return snap("summary")
            if K.get("die_on_bad"):
                sys.exit(3)
            return {"error": {"code": "ELEMENT_NOT_FOUND"}}
        if a["element_id"].startswith("btn-") and not K.get("no_submit"):
            page["submitted"] = True
        return snap("summary")
    return {}


def handle(method, p):
    if method == "initialize":
        return {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}},
                "serverInfo": {"name": "charlotte", "version": K.get("server_version", "0.8.0")}}
    if method == "tools/list":
        return {"tools": [{"name": t} for t in (TOOLS + ["charlotte_screenshot"] if K.get("more_tools") else TOOLS)]}
    if method == "tools/call":
        if K.get("mutate_fixture") and p["name"] == "charlotte_navigate":
            open(p["arguments"]["url"][len("file://"):], "a").write("x")
        return text(call(p["name"], p["arguments"]))
    return {}


serve(handle)
if K.get("exit_on_eof"):
    bye()
while True:   # 0.8.0 keeps running after stdin EOF
    time.sleep(0.1)
'''

# fake tracekit package (put first on sys.path by the fake bin/python)
TK_INIT = r'''
import os, time
K = __K__
__version__ = K.get("module_version", "1.4.1")
if K.get("plant"):
    exec(K["plant"])
time.sleep(K.get("sleep_import", 0))
'''
TK_CORE = r'''
import hashlib, json, os, re, secrets, zipfile
from tracekit import K


def sig(key, prev, ev):
    return hashlib.sha256((key + prev + json.dumps(ev, sort_keys=True, separators=(",", ":"))).encode()).hexdigest()


def policy(cmd):
    if K.get("allow_all"):
        return "allow", []
    if "rm -rf" in cmd or "| sh" in cmd:
        return "deny", [] if K.get("no_rules") else ["TK-D001"]
    if K.get("deny_safe") and cmd in ("ls", "git status"):
        return "deny", ["TK-D999"]
    if cmd.count('"') % 2:
        return "ask", ["TK-SHELL-PARSE"]
    return "allow", []
'''
TK_SERVICE = r'''
import os, secrets
from tracekit.core import K


class SignerService:
    def __init__(self, data, witnesses=(), **kw):
        os.makedirs(os.path.join(data, "store"), exist_ok=True)
        self.data, self.vkey, self.events = data, "log-" + secrets.token_hex(8), []
        if K.get("signer_home"):
            os.makedirs(os.path.expanduser("~/.tracekit-signer"), exist_ok=True)

    def close(self):
        pass
'''
TK_CLIENT = r'''
from tracekit.core import K, policy


class Run:
    def __init__(self, svc):
        self.svc, self.run_id, self.approved = svc, "run1", {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.svc.events.append({"type": "run.final"})

    def decide(self, cid, tool, args):
        d, rules = policy(args["command"])
        self.svc.events.append({"type": "decision", "call": cid, "decision": d, "args": args})
        return {"decision": d, "rule_ids": rules}

    def call(self, what, tool_call_id):
        return {"approval_id": "apr-" + tool_call_id}

    def approval_consume(self, cid, tool, args, approval_id_hint=None):
        if approval_id_hint:
            ok = self.approved.get(approval_id_hint) == args or K.get("any_args")
            if not ok and not K.get("no_gap_record"):
                self.svc.events.append({"type": "approval.binding_mismatch", "call": cid})
            return {"ok": bool(ok)}
        return {"ok": True}

    def complete(self, cid):
        self.svc.events.append({"type": "complete", "call": cid})


class Client:
    def __init__(self, path):
        self.svc = SERVICES[path]

    def run(self, agent):
        self.r = Run(self.svc)
        return self.r

    def approval_decide(self, d):
        cid = d["approval_id"][4:]
        ev = [e for e in self.svc.events if e.get("call") == cid and e["type"] == "decision"][-1]
        self.r.approved[d["approval_id"]] = ev["args"]

    def close(self):
        pass


SERVICES = {}
'''
TK_DEMO = r'''
import json, os, secrets, zipfile
from tracekit.core import K, sig
from tracekit.sdk import client as C


class Witness:
    def __init__(self):
        self.vkey = "wit-" + secrets.token_hex(8)


class _Srv:
    def shutdown(self):
        pass

    def server_close(self):
        pass


def _serve(d, service):
    path = os.path.join(d, "signer.sock")
    C.SERVICES[path] = service
    SVC[0] = service
    return path, _Srv()


SVC = [None]


def export_final(store, run_id, witness, out):
    if K.get("export_fails"):
        raise RuntimeError("export failed")
    svc = SVC[0]
    prev, lines = "", []
    seps = None if K.get("spaced_json") else (",", ":")
    for i, ev in enumerate(svc.events):
        s = sig(svc.vkey, prev, ev)
        lines.append(json.dumps({"seq": i, "prev": prev, "event": ev, "sig": s}, separators=seps))
        prev = s
    files = {"runs/run1.jsonl": ("\n".join(lines) + "\n").encode(),
             "checkpoints/w.json": json.dumps({"log": svc.vkey, "witness": witness.vkey}).encode()}
    import hashlib
    man = {"files": {n: hashlib.sha256(v).hexdigest() for n, v in files.items()}}
    with zipfile.ZipFile(out, "w") as z:
        for n, v in files.items():
            z.writestr(n, v)
        z.writestr("manifest.json", json.dumps(man))
'''
TK_CLI = r'''
import hashlib, json, sys, time, zipfile
sys.path.insert(0, __PKG__)
from tracekit import K
from tracekit.core import sig
a = sys.argv[1:]
if a == ["--version"]:
    time.sleep(K.get("sleep_version", 0))
    print("tracekit " + K.get("cli_version", "1.4.1"))
    sys.exit(0)
assert a[0] == "verify"
trust = json.load(open(a[a.index("--trust") + 1]))
z = zipfile.ZipFile(a[-1])
files = {n: z.read(n) for n in z.namelist()}
man = json.loads(files["manifest.json"])
checks = []


def add(name, ok, detail=""):
    checks.append({"check": name, "status": "pass" if ok else "fail", "detail": detail})


add("manifest", all(hashlib.sha256(files[n]).hexdigest() == h for n, h in man["files"].items()))
cp = json.loads(files["checkpoints/w.json"])
add("checkpoint", cp["log"] in trust["logs"])
add("witness quorum", cp["witness"] in [w["vkey"] for w in trust["witnesses"]] or K.get("skip_quorum"))
recs = [json.loads(l) for l in files["runs/run1.jsonl"].decode().splitlines() if l]
prev, sig_ok, chain_ok = "", True, True
for i, r in enumerate(recs):
    sig_ok &= r["sig"] == sig(cp["log"], r["prev"], r["event"]) or bool(K.get("skip_sig"))
    chain_ok &= (r["seq"] == i and r["prev"] == prev) or bool(K.get("skip_sig"))
    prev = r["sig"]
add("signatures", sig_ok and not (K.get("reject_good") and a[-1].endswith("run.tkb")))
add("run chain", chain_ok)
gaps = [r["event"]["type"] for r in recs if r["event"]["type"] == "approval.binding_mismatch"]
checks.append({"check": "gaps", "status": "warn" if gaps else "pass", "detail": " ".join(gaps)})
bad = any(c["status"] == "fail" for c in checks) and not K.get("verify_always_ok")
print(json.dumps({"exit_code": int(bad), "integrity": "FAILED" if bad else "VERIFIED", "checks": checks}))
sys.exit(1 if bad else 0)
'''


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory(prefix="pfy-xintake-140-test-")
        self.base = Path(self._td.name)
        self.home = self.base / "realhome"
        self.home.mkdir()
        self.nobwrap = self.base / "emptypath"
        self.nobwrap.mkdir()

    def tearDown(self) -> None:
        for p in self.base.rglob("*"):
            if not p.is_symlink():
                p.chmod(0o755 if p.is_dir() else 0o644)
        self._td.cleanup()

    def env(self, *, no_bwrap: bool = False, **extra: str) -> dict[str, str]:
        env = os.environ.copy()
        for key in list(env):
            if key.startswith(("CHIASMUS_", "TRACEKIT_", "CHARLOTTE_")) or key == "PFY_XINTAKE_TIMEOUT":
                env.pop(key, None)
        env["HOME"] = str(self.home)  # so $PFY_TMP lookups find nothing
        env["PFY_SMOKE_RECEIPT_DIR"] = str(RECEIPT_DIR)
        env["PATH"] = str(self.nobwrap) if no_bwrap else env.get("PATH", "/usr/bin:/bin")
        env.update(extra)
        return env

    def run_entry(self, entry: str, env: dict[str, str]) -> tuple[int, dict]:
        p = subprocess.run([sys.executable, SCRIPT, "--entry", entry], cwd=str(ROOT), env=env,
                           capture_output=True, text=True, timeout=180)
        self.assertNotIn("Traceback", p.stderr + p.stdout)
        receipt = json.loads((RECEIPT_DIR / entry / "latest.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["exit_code"], p.returncode)
        return p.returncode, receipt

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


TEMP_HOME_PLANT = "import os; open(os.path.join(os.environ['HOME'], 'x'), 'w').write('x')"


# ---------------------------------------------------------------- chiasmus
class ChiasmusTests(Base):
    def stub(self, version: str = "0.1.40", **knobs) -> dict[str, str]:
        pkg = self.base / "chi/node_modules/chiasmus"
        (pkg / "dist").mkdir(parents=True, exist_ok=True)
        (pkg / "dist/mcp-server.js").write_text("// stub\n")
        (pkg / "package.json").write_text(json.dumps({"version": version}))
        node = _write_stub(self.base / "bin/node", knobs, CHI_NODE)
        return {"CHIASMUS_DIR": str(self.base / "chi"), "CHIASMUS_NODE": str(node)}

    def go(self, *, no_bwrap: bool = False, timeout: str = "", version: str = "0.1.40", **knobs) -> tuple[int, dict]:
        extra = self.stub(version, **knobs)
        if timeout:
            extra["PFY_XINTAKE_TIMEOUT"] = timeout
        return self.run_entry("chiasmus", self.env(no_bwrap=no_bwrap, **extra))

    def test_missing_package_exits_2(self) -> None:
        code, r = self.run_entry("chiasmus", self.env(CHIASMUS_DIR=str(self.base / "nope")))
        self.assertEqual(code, 2)
        self.assertIn("chiasmus not found", r["reason"])

    def test_version_mismatch_exits_2(self) -> None:
        code, r = self.go(version="0.1.39")
        self.assertEqual(code, 2)
        self.assertIn("0.1.39", r["reason"])

    def test_old_node_exits_2(self) -> None:
        code, r = self.go(node="20.19.2")
        self.assertEqual(code, 2)
        self.assertIn("Node 22+", r["reason"])

    def test_happy_path_passes(self) -> None:
        code, r = self.go()
        self.assertEqual(code, 0, r)
        self.assertTrue(all(r["checks"].values()), r)
        self.assertIn("~/.chiasmus", r["reason"])

    def test_server_version_mismatch_fails(self) -> None:
        self.assert_failed(*self.go(server_version="0.1.41"), "server_version_pinned")

    def test_missing_tool_fails(self) -> None:
        self.assert_failed(*self.go(fewer_tools=True), "exact_9_tools")

    def test_short_unsat_core_fails(self) -> None:
        self.assert_failed(*self.go(short_core=True), "z3_unsat_core")

    def test_bad_model_fails(self) -> None:
        self.assert_failed(*self.go(bad_model=True), "z3_sat_model_in_range")

    def test_prolog_always_true_fails(self) -> None:
        self.assert_failed(*self.go(prolog_always_true=True), "prolog_refutes_reverse")

    def test_all_dead_fails(self) -> None:
        self.assert_failed(*self.go(all_dead=True), "dead_code_found")

    def test_reach_always_fails(self) -> None:
        self.assert_failed(*self.go(reach_always=True), "reachability_false")

    def test_short_impact_fails(self) -> None:
        self.assert_failed(*self.go(short_impact=True), "impact_is_callers")

    def test_silent_lint_fails(self) -> None:
        self.assert_failed(*self.go(lint_silent=True), "lint_flags_parens")

    def test_no_skills_fails(self) -> None:
        self.assert_failed(*self.go(no_skills=True), "skills_template_found")

    def test_no_db_fails(self) -> None:
        self.assert_failed(*self.go(no_db=True), "skill_db_in_temp_home")

    def test_db_in_home_fails(self) -> None:
        code, r = self.go(db_to_home=True)
        self.assertEqual(code, 1, r)
        self.assertFalse(r["checks"]["home_untouched"])
        self.assertFalse(r["checks"]["skill_db_in_temp_home"])

    def test_fixture_write_fails(self) -> None:
        self.assert_failed(*self.go(mutate_fixture=True), "fixtures_untouched")

    def test_temp_home_write_fails(self) -> None:
        self.assert_failed(*self.go(plant=TEMP_HOME_PLANT), "home_untouched")

    def test_real_home_write_fails_without_bwrap(self) -> None:
        code, r = self.go(no_bwrap=True, plant=self.plant_home(".chiasmus"))
        self.assertEqual(code, 1)
        self.assert_home_changed(r, ".chiasmus")

    def test_real_home_cache_write_fails_without_bwrap(self) -> None:
        code, r = self.go(no_bwrap=True, plant=self.plant_home(".cache/chiasmus"))
        self.assertEqual(code, 1)
        self.assert_home_changed(r, ".cache/chiasmus")

    def test_seeded_real_home_untouched_passes(self) -> None:
        (self.home / ".chiasmus").mkdir()
        (self.home / ".chiasmus/config.json").write_text("{}")
        code, r = self.go(no_bwrap=True)
        self.assertEqual(code, 0, r)

    def test_timeout_fails_and_keeps_home_check(self) -> None:
        code, r = self.go(no_bwrap=True, timeout="1", sleep_version=5, plant=self.plant_home(".chiasmus"))
        self.assertEqual(code, 1)
        self.assertIn("node version timeout after 1s", r["reason"])
        self.assertFalse(r["checks"]["body_completed"])
        self.assert_home_changed(r, ".chiasmus")

    def test_driver_timeout_fails(self) -> None:
        code, r = self.go(timeout="3", sleep_server=10)
        self.assertEqual(code, 1)
        self.assertIn("chiasmus driver timeout after 3s", r["reason"])

    def test_crashing_server_fails_driver_report(self) -> None:
        code, r = self.go(die_on_graph=True)
        self.assert_failed(code, r, "driver_report")
        self.assertIn("server closed stdout", r["driver_tail"])

    def test_prolog_never_true_fails(self) -> None:
        code, r = self.go(prolog_never_true=True)
        self.assert_failed(code, r, "prolog_proves_reach")
        self.assertTrue(r["checks"]["prolog_refutes_reverse"], r)

    def test_reach_never_fails(self) -> None:
        code, r = self.go(reach_never=True)
        self.assert_failed(code, r, "reachability_true")
        self.assertTrue(r["checks"]["reachability_false"], r)

    def test_extra_tool_fails(self) -> None:
        self.assert_failed(*self.go(more_tools=True), "exact_9_tools")

    def test_bad_node_override_exits_2(self) -> None:
        extra = self.stub()
        extra["CHIASMUS_NODE"] = str(self.base / "no-such-node")
        code, r = self.run_entry("chiasmus", self.env(**extra))
        self.assertEqual(code, 2, r)
        self.assertIn("$CHIASMUS_NODE", r["reason"])
        self.assertNotIn("checks", r)

    def test_non_numeric_timeout_exits_2(self) -> None:
        for bad in ("abc", "0", "-1", "nan"):
            with self.subTest(timeout=bad):
                code, r = self.go(timeout=bad)
                self.assertEqual(code, 2, r)
                self.assertIn("PFY_XINTAKE_TIMEOUT", r["reason"])
                self.assertNotIn("checks", r)

    def test_early_exit_2_with_real_home_change_fails(self) -> None:
        code, r = self.go(no_bwrap=True, node="20.19.2", plant=self.plant_home(".chiasmus"))
        self.assertEqual(code, 1, r)
        self.assertIn("Node 22+", r["reason"])
        self.assert_home_changed(r, ".chiasmus")


# ---------------------------------------------------------------- tracekit
class TracekitTests(Base):
    def stub(self, **knobs) -> dict[str, str]:
        venv = self.base / "venv"
        pkg = self.base / "fakepkg"
        t = pkg / "tracekit"
        (t / "signer").mkdir(parents=True, exist_ok=True)
        (t / "sdk").mkdir(parents=True, exist_ok=True)
        (t / "__init__.py").write_text(TK_INIT.replace("__K__", repr(knobs)))
        (t / "core.py").write_text(TK_CORE)
        (t / "signer/__init__.py").write_text("")
        (t / "signer/service.py").write_text(TK_SERVICE)
        (t / "sdk/__init__.py").write_text("")
        (t / "sdk/client.py").write_text(TK_CLIENT)
        (t / "demo_server.py").write_text(TK_DEMO)
        (venv / "bin").mkdir(parents=True, exist_ok=True)
        py = venv / "bin/python"
        py.write_text(f"#!/bin/sh\nPYTHONPATH={pkg} PYTHONDONTWRITEBYTECODE=1 exec {sys.executable} \"$@\"\n")
        py.chmod(0o755)
        cli = venv / "bin/tracekit"
        cli.write_text(f"#!{sys.executable}\n" + TK_CLI.replace("__PKG__", repr(str(pkg))))
        cli.chmod(0o755)
        return {"TRACEKIT_VENV": str(venv)}

    def go(self, *, no_bwrap: bool = False, timeout: str = "", **knobs) -> tuple[int, dict]:
        extra = self.stub(**knobs)
        if timeout:
            extra["PFY_XINTAKE_TIMEOUT"] = timeout
        return self.run_entry("tracekit", self.env(no_bwrap=no_bwrap, **extra))

    def test_missing_venv_exits_2(self) -> None:
        code, r = self.run_entry("tracekit", self.env(TRACEKIT_VENV=str(self.base / "nope")))
        self.assertEqual(code, 2)
        self.assertIn("tracekit venv not found", r["reason"])

    def test_cli_version_mismatch_exits_2(self) -> None:
        code, r = self.go(cli_version="1.4.0")
        self.assertEqual(code, 2)
        self.assertIn("1.4.0", r["reason"])

    def test_env_pin_override_accepts_other_version(self) -> None:
        code, r = self.run_entry("tracekit", self.env(TRACEKIT_VERSION="1.5.0",
                                                      **self.stub(cli_version="1.5.0", module_version="1.5.0")))
        self.assertEqual(code, 0, r)
        self.assertEqual(r["expected"]["TRACEKIT_VERSION"]["source"], "env")

    def test_happy_path_passes(self) -> None:
        code, r = self.go()
        self.assertEqual(code, 0, r)
        self.assertTrue(all(r["checks"].values()), r)
        self.assertEqual(r["verify"]["flipped"]["failed"], ["signatures"])

    def test_module_version_mismatch_fails(self) -> None:
        self.assert_failed(*self.go(module_version="1.4.0"), "module_version_pinned")

    def test_allow_all_policy_fails(self) -> None:
        code, r = self.go(allow_all=True)
        self.assert_failed(code, r, "destructive_calls_denied")
        self.assertFalse(r["checks"]["unparsable_call_held"])

    def test_approval_not_bound_fails(self) -> None:
        self.assert_failed(*self.go(any_args=True), "approval_bound_to_args")

    def test_no_gap_record_fails(self) -> None:
        self.assert_failed(*self.go(no_gap_record=True), "arg_swap_signed_as_gap")

    def test_verifier_skipping_signatures_fails(self) -> None:
        code, r = self.go(skip_sig=True)
        self.assert_failed(code, r, "flipped_decision_fails_signatures")
        self.assertFalse(r["checks"]["dropped_record_fails"])

    def test_verifier_skipping_quorum_fails(self) -> None:
        self.assert_failed(*self.go(skip_quorum=True), "other_witness_fails_quorum")

    def test_verifier_always_ok_fails(self) -> None:
        code, r = self.go(verify_always_ok=True)
        self.assertEqual(code, 1)
        for c in ("flipped_decision_fails_signatures", "dropped_record_fails", "other_witness_fails_quorum"):
            self.assertFalse(r["checks"][c], r)

    def test_temp_home_write_fails(self) -> None:
        self.assert_failed(*self.go(plant=TEMP_HOME_PLANT), "home_untouched")

    def test_real_home_write_fails_without_bwrap(self) -> None:
        code, r = self.go(no_bwrap=True, plant=self.plant_home(".tracekit-client"))
        self.assertEqual(code, 1)
        self.assert_home_changed(r, ".tracekit-client")

    def test_real_home_data_write_fails_without_bwrap(self) -> None:
        code, r = self.go(no_bwrap=True, plant=self.plant_home(".local/share/tracekit"))
        self.assertEqual(code, 1)
        self.assert_home_changed(r, ".local/share/tracekit")

    def test_driver_error_fails_driver_report(self) -> None:
        code, r = self.go(export_fails=True)
        self.assert_failed(code, r, "driver_report")
        self.assertIn("export failed", r["driver_tail"])

    def test_safe_call_denied_fails(self) -> None:
        code, r = self.go(deny_safe=True)
        self.assert_failed(code, r, "safe_calls_allowed")
        self.assertTrue(r["checks"]["destructive_calls_denied"], r)

    def test_denial_without_rule_fails(self) -> None:
        code, r = self.go(no_rules=True)
        self.assert_failed(code, r, "destructive_calls_denied")
        self.assertTrue(r["checks"]["safe_calls_allowed"], r)

    def test_good_bundle_rejected_fails(self) -> None:
        code, r = self.go(reject_good=True)
        self.assert_failed(code, r, "bundle_verifies")
        self.assertTrue(r["checks"]["flipped_decision_fails_signatures"], r)

    def test_untamperable_layout_fails_tamper_copies(self) -> None:
        code, r = self.go(spaced_json=True)
        self.assert_failed(code, r, "tamper_copies_made")
        self.assertNotIn("flipped", r["verify"])
        self.assertTrue(r["checks"]["dropped_record_fails"], r)

    def test_signer_in_temp_home_fails(self) -> None:
        self.assert_failed(*self.go(signer_home=True), "home_untouched")

    def test_timeout_fails_and_keeps_home_check(self) -> None:
        code, r = self.go(no_bwrap=True, timeout="2", sleep_import=6, plant=self.plant_home(".tracekit-signer"))
        self.assertEqual(code, 1)
        self.assertIn("timeout after 2s", r["reason"])
        self.assertFalse(r["checks"]["body_completed"])
        self.assert_home_changed(r, ".tracekit-signer")


# ---------------------------------------------------------------- charlotte
class CharlotteTests(Base):
    def stub(self, version: str = "0.8.0", chrome: bool = True, **knobs) -> dict[str, str]:
        pkg = self.base / "ch/node_modules/@ticktockbent/charlotte"
        (pkg / "dist").mkdir(parents=True, exist_ok=True)
        (pkg / "dist/index.js").write_text("// stub\n")
        (pkg / "package.json").write_text(json.dumps({"version": version}))
        node = _write_stub(self.base / "bin/node", knobs, CH_NODE)
        extra = {"CHARLOTTE_DIR": str(self.base / "ch"), "CHARLOTTE_NODE": str(node)}
        if chrome:
            extra["CHARLOTTE_CHROME"] = str(_write_stub(self.base / "bin/chrome", {}, "pass\n"))
        return extra

    def go(self, *, no_bwrap: bool = False, timeout: str = "", version: str = "0.8.0", **knobs) -> tuple[int, dict]:
        extra = self.stub(version, **knobs)
        if timeout:
            extra["PFY_XINTAKE_TIMEOUT"] = timeout
        return self.run_entry("charlotte", self.env(no_bwrap=no_bwrap, **extra))

    def test_missing_package_exits_2(self) -> None:
        code, r = self.run_entry("charlotte", self.env(CHARLOTTE_DIR=str(self.base / "nope")))
        self.assertEqual(code, 2)
        self.assertIn("charlotte not found", r["reason"])

    def test_version_mismatch_exits_2(self) -> None:
        code, r = self.go(version="0.7.0")
        self.assertEqual(code, 2)
        self.assertIn("0.7.0", r["reason"])

    def test_old_node_exits_2(self) -> None:
        code, r = self.go(node="18.20.0")
        self.assertEqual(code, 2)
        self.assertIn("Node 20+", r["reason"])

    def test_happy_path_passes(self) -> None:
        code, r = self.go()
        self.assertEqual(code, 0, r)
        self.assertTrue(all(r["checks"].values()), r)
        self.assertEqual(r["stopped"], "term")

    def test_exit_on_eof_passes(self) -> None:
        code, r = self.go(exit_on_eof=True)
        self.assertEqual(code, 0, r)
        self.assertEqual(r["stopped"], "eof")

    def test_server_version_mismatch_fails(self) -> None:
        self.assert_failed(*self.go(server_version="0.8.1"), "server_version_pinned")

    def test_extra_tool_fails(self) -> None:
        self.assert_failed(*self.go(more_tools=True), "exact_7_core_tools")

    def test_minimal_with_ids_fails(self) -> None:
        self.assert_failed(*self.go(leak_ids=True), "navigate_minimal")

    def test_minimal_with_text_fails(self) -> None:
        self.assert_failed(*self.go(leak_text=True), "navigate_minimal")

    def test_wrong_labels_fail(self) -> None:
        self.assert_failed(*self.go(swap_labels=True), "observe_lists_form")

    def test_find_nothing_fails(self) -> None:
        code, r = self.go(find_nothing=True)
        self.assert_failed(code, r, "find_returns_button_id")
        self.assertFalse(r["checks"]["server_survives_error"])

    def test_no_submit_fails(self) -> None:
        self.assert_failed(*self.go(no_submit=True), "submit_handler_ran")

    def test_full_without_body_text_fails(self) -> None:
        code, r = self.go(full_no_text=True)
        self.assert_failed(code, r, "full_has_body_text")
        self.assertTrue(r["checks"]["submit_handler_ran"], r)

    def test_bad_node_override_exits_2(self) -> None:
        extra = self.stub()
        extra["CHARLOTTE_NODE"] = str(self.base / "no-such-node")
        code, r = self.run_entry("charlotte", self.env(**extra))
        self.assertEqual(code, 2, r)
        self.assertIn("$CHARLOTTE_NODE", r["reason"])

    def test_bad_chrome_override_exits_2(self) -> None:
        extra = self.stub()
        not_exec = self.base / "chrome-not-exec"
        not_exec.write_text("")
        extra["CHARLOTTE_CHROME"] = str(not_exec)
        code, r = self.run_entry("charlotte", self.env(**extra))
        self.assertEqual(code, 2, r)
        self.assertIn("$CHARLOTTE_CHROME", r["reason"])

    def test_missing_chrome_exits_2(self) -> None:
        # In process, because the runner may have a system Chrome on the fixed PATH (nimo and ubuntu-latest do).
        sys.path.insert(0, str(ROOT / "examples/x-intake-local"))
        import smoke_140_142 as m
        extra = self.stub(chrome=False)
        env = {k: v for k, v in os.environ.items() if not k.startswith("CHARLOTTE_")}
        env.update(extra)
        r: dict = {}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(m, "TMP", self.base), \
                mock.patch.object(m.shutil, "which", return_value=None):
            code = m.smoke_charlotte(r)
        self.assertEqual(code, 2, r)
        self.assertIsNone(r["chrome"])
        self.assertIn("no Chrome/Chromium", r["reason"])

    def test_unstable_ids_fail(self) -> None:
        self.assert_failed(*self.go(unstable_ids=True), "ids_stable")

    def test_bad_id_accepted_fails(self) -> None:
        self.assert_failed(*self.go(bad_id_ok=True), "bad_id_is_error")

    def test_crash_on_bad_id_fails(self) -> None:
        code, r = self.go(die_on_bad=True)
        self.assertEqual(code, 1, r)
        self.assertFalse(r["checks"]["driver_report"], r)

    def test_ignored_term_fails(self) -> None:
        code, r = self.go(ignore_term=True)
        self.assert_failed(code, r, "server_stopped")
        self.assertEqual(r["stopped"], "kill")

    def test_left_profile_fails(self) -> None:
        self.assert_failed(*self.go(leave_profile=True), "no_profile_left")

    def test_fixture_write_fails(self) -> None:
        self.assert_failed(*self.go(mutate_fixture=True), "fixture_untouched")

    def test_chrome_in_home_fails(self) -> None:
        self.assert_failed(*self.go(chrome_home=True), "home_untouched")

    def test_real_home_write_fails_without_bwrap(self) -> None:
        code, r = self.go(no_bwrap=True, plant=self.plant_home(".cache/puppeteer"))
        self.assertEqual(code, 1)
        self.assert_home_changed(r, ".cache/puppeteer")

    def test_timeout_fails_and_keeps_home_check(self) -> None:
        code, r = self.go(no_bwrap=True, timeout="1", sleep_version=5, plant=self.plant_home(".cache/puppeteer"))
        self.assertEqual(code, 1)
        self.assertIn("node version timeout after 1s", r["reason"])
        self.assertFalse(r["checks"]["body_completed"])
        self.assert_home_changed(r, ".cache/puppeteer")


if __name__ == "__main__":
    unittest.main()
