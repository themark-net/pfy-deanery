#!/usr/bin/env python3
"""Adapter, checker, and score contracts for the skill-up catch-up trial.

Subprocess tests only. No real model. The skill-up binary test skips when
tmp/skill-up/skill-up is absent or is not the pinned v0.14.0 sha.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "eval" / "catchup-1107" / "skill-up" / "engine_local.py"
RUN = ROOT / "eval" / "catchup-1107" / "skill-up" / "run_eval.py"
CASES = ROOT / "eval" / "catchup-1107" / "skill-up" / "cases"
SCRIPTS = CASES / "evals" / "fixtures" / "scripts"
SEEDS = CASES / "evals" / "fixtures" / "repos"
BIN = ROOT / "tmp" / "skill-up" / "skill-up"
BIN_SHA = "5b1bdd0a30f57653c8f6a3a679e992b29982fe18709b2556d53a6f9ea1c85ab6"

STUB = r"""#!/usr/bin/env python3
import json, os, sys, time
from pathlib import Path
log = os.environ.get("STUB_LOG", "")
cfg = {}
cfg_path = os.environ.get("OPENCODE_CONFIG", "")
if cfg_path and Path(cfg_path).is_file():
    cfg = json.loads(Path(cfg_path).read_text())
skill_hits = []
for p in ((cfg.get("skills") or {}).get("paths") or []):
    rootp = Path(p)
    if rootp.is_dir():
        for f in rootp.rglob("SKILL.md"):
            skill_hits.append(f.read_text(encoding="utf-8")[:400])
if log:
    rec = {
        "home": os.environ.get("HOME"),
        "xdg": os.environ.get("XDG_CONFIG_HOME"),
        "config": cfg,
        "argv": sys.argv,
        "skill_hits": skill_hits,
    }
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
mode = os.environ.get("STUB_MODE", "ok")
if mode == "sleep":
    time.sleep(30)
    print("woke")
elif mode == "garbage":
    print("not-json-at-all")
else:
    print(json.dumps({"type": "text", "part": {"type": "text", "text": "stub-final"}}))
"""

FIXES = {
    "span-off-by-one": ("src/span.py", "def inclusive_count(start, end):\n    return end - start + 1\n", "check_span.py"),
    "greet-arg-check": (
        "src/greet.py",
        "def greet(name):\n"
        "    if name is None or not str(name).strip():\n"
        "        raise ValueError('name')\n"
        "    return 'Hello, ' + str(name).strip()\n",
        "check_greet.py",
    ),
    "clamp-hidden": (
        "src/clamp.py",
        "def clamp(value, low, high):\n"
        "    if low > high:\n"
        "        raise ValueError('range')\n"
        "    return min(max(value, low), high)\n",
        "check_clamp.py",
    ),
    "last-two": ("src/seq.py", "def last_two(items):\n    return list(items[-2:])\n", "check_last_two.py"),
    "inclusive-range": (
        "src/range_check.py",
        "def in_range(n, low, high):\n    return low <= n <= high\n",
        "check_in_range.py",
    ),
}


def _run(cmd, cwd, env=None):
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)


class CheckerTests(unittest.TestCase):
    def test_seeded_bugs_fail_and_fixes_pass(self):
        for name, (rel, good, script) in FIXES.items():
            seed = SEEDS / name
            bad = _run([sys.executable, str(SCRIPTS / script)], seed)
            self.assertNotEqual(bad.returncode, 0, "%s seed should fail, stdout=%s" % (name, bad.stdout))
            with tempfile.TemporaryDirectory() as td:
                dest = Path(td)
                (dest / Path(rel).parent).mkdir(parents=True)
                (dest / rel).write_text(good, encoding="utf-8")
                ok = _run([sys.executable, str(SCRIPTS / script)], dest)
            self.assertEqual(ok.returncode, 0, "%s fix should pass, stdout=%s stderr=%s" % (name, ok.stdout, ok.stderr))


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.stub_dir = self.root / "bin"
        self.stub_dir.mkdir()
        stub = self.stub_dir / "opencode"
        stub.write_text(STUB, encoding="utf-8")
        stub.chmod(0o755)
        self.log = self.root / "stub.jsonl"
        self.marker = self.root / "marker"
        self.skill = self.root / "demo-skill"
        self.skill.mkdir()
        (self.skill / "SKILL.md").write_text(
            "---\nname: demo-skill\ndescription: Use when editing Python.\n---\n\nUNIQUE_SKILL_SENTINEL\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def _env(self, **extra):
        env = {
            "PATH": str(self.stub_dir) + os.pathsep + "/usr/bin:/bin",
            "HOME": str(Path.home()),
            "STUB_LOG": str(self.log),
            "SKILLUP_MEM_GATE_KIB": "0",
            "SKILLUP_OLLAMA_URL": "http://127.0.0.1:9",
            "SKILLUP_LOAD_MARKER": str(self.marker),
            "SKILLUP_MODEL": "qwen3.6:35b",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        env.update(extra)
        return env

    def _session(self, workspace, variant, timeout=30):
        path = self.root / ("session-%s.json" % variant)
        path.write_text(json.dumps({
            "case_id": "span-off-by-one",
            "variant": variant,
            "workspace": str(workspace),
            "messages": [{"role": "user", "content": "Fix the function."}],
            "max_turns": 4,
            "timeout_seconds": timeout,
        }), encoding="utf-8")
        return path

    def _adapt(self, session, env):
        return _run([sys.executable, str(ENGINE), str(session), "--skills-dir", str(self.skill)], self.root, env)

    def _result(self, proc):
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertIn("exit_code", data)
        self.assertIn("final_message", data)
        return data

    def test_with_skill_installs_and_without_does_not(self):
        for variant, present in (("with_skill", True), ("without_skill", False)):
            self.log.write_text("", encoding="utf-8")
            ws = self.root / variant
            ws.mkdir()
            proc = self._adapt(self._session(ws, variant), self._env())
            data = self._result(proc)
            self.assertEqual(data["exit_code"], 0)
            self.assertIn("stub-final", data["final_message"])
            lines = [json.loads(ln) for ln in self.log.read_text(encoding="utf-8").splitlines() if ln.strip()]
            self.assertEqual(len(lines), 1)
            self.assertNotEqual(lines[0]["home"], str(Path.home()))
            self.assertNotIn(".config/opencode", lines[0]["xdg"])
            skills = Path(lines[0]["config"]["skills"]["paths"][0])
            found = list(skills.rglob("SKILL.md"))
            if present:
                self.assertTrue(found)
                self.assertIn("UNIQUE_SKILL_SENTINEL", found[0].read_text(encoding="utf-8"))
            else:
                self.assertEqual(found, [])

    def test_timeout_kills_sleeper(self):
        ws = self.root / "slow"
        ws.mkdir()
        started = time.monotonic()
        proc = self._adapt(self._session(ws, "without_skill", timeout=3), self._env(STUB_MODE="sleep"))
        elapsed = time.monotonic() - started
        data = self._result(proc)
        self.assertEqual(data["exit_code"], 124)
        self.assertLess(elapsed, 15, "sleeper was not killed")

    def test_garbage_stdout_still_returns_session_result(self):
        ws = self.root / "garbage"
        ws.mkdir()
        proc = self._adapt(self._session(ws, "without_skill"), self._env(STUB_MODE="garbage"))
        data = self._result(proc)
        self.assertEqual(data["exit_code"], 0)
        self.assertIn("not-json-at-all", data["final_message"])

    def test_host_busy_does_not_call_the_model(self):
        hits = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                return

            def do_GET(self):
                hits.append(self.path)
                raw = b'{"models":[]}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                hits.append("POST " + self.path)
                self.send_response(200)
                self.end_headers()

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            ws = self.root / "busy"
            ws.mkdir()
            env = self._env(
                PATH="/usr/bin:/bin",
                SKILLUP_MEM_GATE_KIB="100",
                SKILLUP_MEM_AVAILABLE_KIB="1",
                SKILLUP_OLLAMA_URL="http://127.0.0.1:%s" % port,
            )
            proc = self._adapt(self._session(ws, "without_skill"), env)
            data = self._result(proc)
        finally:
            server.shutdown()
        self.assertIn("HOST-BUSY", data["final_message"])
        self.assertEqual(data["exit_code"], 1)
        self.assertFalse(any(p.startswith("/v1/") or p.startswith("/api/chat") for p in hits))

    def test_loaded_model_skips_the_preload_gate(self):
        bodies = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                return

            def do_GET(self):
                raw = json.dumps({"models": [{"name": "qwen3.6:35b"}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0") or "0")
                bodies.append(json.loads(self.rfile.read(length).decode()))
                raw = json.dumps({"choices": [{"message": {"content": "pong-loaded"}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            ws = self.root / "resident"
            ws.mkdir()
            env = self._env(
                PATH="/usr/bin:/bin",
                SKILLUP_MEM_GATE_KIB="100",
                SKILLUP_MEM_AVAILABLE_KIB="1",
                SKILLUP_OLLAMA_URL="http://127.0.0.1:%s" % port,
                SKILLUP_LOAD_MARKER=str(self.root / "no-such-marker"),
            )
            proc = self._adapt(self._session(ws, "without_skill"), env)
            data = self._result(proc)
        finally:
            server.shutdown()
        self.assertNotIn("HOST-BUSY", data["final_message"])
        self.assertIn("pong-loaded", data["final_message"])
        self.assertEqual(len(bodies), 1)
        self.assertNotIn("keep_alive", bodies[0])

    def test_fallback_keep_alive_only_when_we_load(self):
        bodies = []

        class Handler(BaseHTTPRequestHandler):
            loaded = False

            def log_message(self, fmt, *args):
                return

            def do_GET(self):
                models = [{"name": "qwen3.6:35b"}] if self.loaded else []
                raw = json.dumps({"models": models}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0") or "0")
                bodies.append(json.loads(self.rfile.read(length).decode()))
                raw = json.dumps({"choices": [{"message": {"content": "pong-from-stub"}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        try:
            ws = self.root / "chat"
            ws.mkdir()
            env = self._env(
                PATH="/usr/bin:/bin",
                SKILLUP_OLLAMA_URL="http://127.0.0.1:%s" % port,
            )
            proc = self._adapt(self._session(ws, "without_skill"), env)
            data = self._result(proc)
            self.assertIn("direct chat-completions", data["final_message"])
            self.assertIn("pong-from-stub", data["final_message"])
            self.assertEqual(bodies[-1].get("keep_alive"), "2m")
            self.assertEqual(bodies[-1].get("temperature"), 0)
            self.assertEqual(bodies[-1].get("reasoning_effort"), "none")
            bodies.clear()
            Handler.loaded = True
            fresh = self.root / "marker-loaded"
            env["SKILLUP_LOAD_MARKER"] = str(fresh)
            proc = self._adapt(self._session(ws, "without_skill"), env)
            data = self._result(proc)
            self.assertNotIn("keep_alive", bodies[-1])
        finally:
            server.shutdown()

    def test_keep_alive_matches_our_expires_at_only(self):
        bodies = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                return

            def do_GET(self):
                raw = json.dumps({
                    "models": [{"name": "qwen3.6:35b", "expires_at": "exp-ours"}],
                }).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0") or "0")
                bodies.append(json.loads(self.rfile.read(length).decode()))
                raw = json.dumps({"choices": [{"message": {"content": "pong-exp"}}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        marker = self.root / "expires-marker"
        marker.write_text("qwen3.6:35b\nexp-ours\n", encoding="utf-8")
        try:
            ws = self.root / "exp"
            ws.mkdir()
            env = self._env(
                PATH="/usr/bin:/bin",
                SKILLUP_OLLAMA_URL="http://127.0.0.1:%s" % port,
                SKILLUP_LOAD_MARKER=str(marker),
            )
            proc = self._adapt(self._session(ws, "without_skill"), env)
            data = self._result(proc)
            self.assertIn("pong-exp", data["final_message"])
            self.assertEqual(bodies[-1].get("keep_alive"), "2m")
            bodies.clear()
            marker.write_text("qwen3.6:35b\nexp-theirs\n", encoding="utf-8")
            proc = self._adapt(self._session(ws, "without_skill"), env)
            data = self._result(proc)
            self.assertNotIn("keep_alive", bodies[-1])
        finally:
            server.shutdown()


class ScoreTests(unittest.TestCase):
    def _write(self, root, iteration, rows):
        dest = root / ("iteration-%s" % iteration)
        dest.mkdir(parents=True)
        cases = []
        for cid, cfg, status in rows:
            cases.append({"case_id": cid, "configuration": cfg, "status": status})
        (dest / "result.json").write_text(json.dumps({"case_results": cases}), encoding="utf-8")
        (dest / "report.xml").write_text("<testsuite/>", encoding="utf-8")

    def _score(self, root):
        proc = _run([sys.executable, str(RUN), "--score", str(root)], root)
        self.assertIn(proc.returncode, (0, 2), proc.stderr + proc.stdout[:400])
        return proc.returncode, json.loads(proc.stdout)

    def test_stable_pass_fail_promotes_and_error_or_flake_stays(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "stable"
            rows = []
            for cid in ("a", "b", "c", "d", "e"):
                rows.append((cid, "with_skill", "PASS"))
                rows.append((cid, "without_skill", "FAIL"))
            self._write(root, 1, rows)
            self._write(root, 2, rows)
            code, data = self._score(root)
            self.assertEqual(code, 0)
            self.assertEqual(data["decision"], "PROMOTE")
            self.assertEqual(data["flake_count"], 0)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "flake"
            base = []
            for cid in ("a", "b", "c", "d", "e"):
                base.append((cid, "with_skill", "PASS"))
                base.append((cid, "without_skill", "PASS"))
            flipped = []
            for cid, cfg, status in base:
                flipped.append((cid, cfg, "FAIL" if cid == "a" and cfg == "with_skill" else status))
            self._write(root, 1, base)
            self._write(root, 2, flipped)
            code, data = self._score(root)
            self.assertEqual(data["flake_count"], 1)
            self.assertEqual(data["decision"], "PROMOTE")
            self.assertEqual(code, 0)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "wild"
            one = [("a", "with_skill", "PASS"), ("a", "without_skill", "PASS")]
            two = [("a", "with_skill", "FAIL"), ("a", "without_skill", "FAIL")]
            self._write(root, 1, one)
            self._write(root, 2, two)
            code, data = self._score(root)
            self.assertEqual(code, 2)
            self.assertEqual(data["decision"], "STAY")
            self.assertGreater(data["flake_rate"], 0.2)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "err"
            rows = [("a", "with_skill", "ERROR"), ("a", "without_skill", "FAIL")]
            self._write(root, 1, rows)
            self._write(root, 2, rows)
            code, data = self._score(root)
            self.assertEqual(code, 2)
            self.assertEqual(data["decision"], "STAY")
            self.assertIn("error", data["decision_reason"])


class BinaryTests(unittest.TestCase):
    def test_skill_up_grades_the_seeded_bug(self):
        if not BIN.is_file():
            self.skipTest("skill-up v0.14.0 binary is absent (tmp/skill-up/skill-up); CI skips this test")
        have = hashlib.sha256(BIN.read_bytes()).hexdigest()
        if have != BIN_SHA:
            self.skipTest("skill-up binary sha %s is not the pinned v0.14.0; CI skips this test" % have)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            stub_dir = root / "bin"
            stub_dir.mkdir()
            stub = stub_dir / "opencode"
            stub.write_text(STUB, encoding="utf-8")
            stub.chmod(0o755)
            skill = root / "demo-skill"
            skill.mkdir()
            (skill / "SKILL.md").write_text(
                "---\nname: demo-skill\ndescription: Use when editing Python.\n---\n\nUNIQUE_SKILL_SENTINEL\n",
                encoding="utf-8",
            )
            home, xdg, tmp, out = root / "home", root / "xdg", root / "tmp", root / "out"
            for d in (home, xdg, tmp, out):
                d.mkdir()
            env = os.environ.copy()
            for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
                env.pop(key, None)
            env.update({
                "PATH": str(stub_dir) + os.pathsep + env.get("PATH", "/usr/bin:/bin"),
                "HOME": str(home),
                "XDG_CONFIG_HOME": str(xdg),
                "TMPDIR": str(tmp),
                "NO_PROXY": "*",
                "SKILLUP_ENGINE_BIN": str(ENGINE),
                "SKILLUP_SKILL_DIR": str(skill),
                "SKILLUP_MEM_GATE_KIB": "0",
                "SKILLUP_OLLAMA_URL": "http://127.0.0.1:9",
                "SKILLUP_LOAD_MARKER": str(root / "marker"),
                "STUB_LOG": str(root / "stub.jsonl"),
                "PYTHONDONTWRITEBYTECODE": "1",
            })
            proc = _run(
                [str(BIN), "run", str(CASES / "evals" / "eval.yaml"),
                 "--baseline", "--iteration", "1", "--include-case-name", "span-off-by-one",
                 "--format", "json", "--format", "junit", "--output-dir", str(out), "--parallelism", "1"],
                CASES,
                env,
            )
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            results = list(out.rglob("result.json"))
            self.assertTrue(results, proc.stdout + proc.stderr)
            blob = results[0].read_text(encoding="utf-8")
            self.assertIn("inclusive_count(1, 3)", blob)
            self.assertTrue(list(out.rglob("report.xml")))
            lines = [json.loads(ln) for ln in (root / "stub.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
            self.assertEqual(len(lines), 2, lines)
            hits = ["\n".join(ln.get("skill_hits") or []) for ln in lines]
            self.assertEqual(sum(1 for h in hits if "UNIQUE_SKILL_SENTINEL" in h), 1, hits)
            self.assertEqual(sum(1 for h in hits if not h.strip()), 1, hits)


if __name__ == "__main__":
    unittest.main()
