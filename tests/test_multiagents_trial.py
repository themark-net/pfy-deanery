"""Entry 194 trial: solo vs coder/reviewer on local Ollama, priced at $0.

Fail: a paid or unpriced worker still calls a model, a missing tag is pulled,
a run record omits tokens or cost or seconds, or --apply writes a checkout
that is not under this worktree's tmp/.
Recover: refuse before the call, leave the tree as it was, and write the
reason. A graded local run records pass/fail, token counts, $0, and seconds.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples" / "multiagents-trial" / "trial.py"
TASK = ROOT / "examples" / "eval-harness" / "tasks" / "001-is-palindrome"
GOOD = "def is_palindrome(s: str) -> bool:\n    return s == s[::-1]\n"
BAD = "def is_palindrome(s: str) -> bool:\n    return False\n"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        return

    def _read(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def _send(self, code: int, obj: dict) -> None:
        raw = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = urlparse(self.path).path
        self.server.hits.append(("GET", path, None))
        if path == "/api/tags":
            names = [{"name": name} for name in self.server.tags]
            self._send(200, {"models": names})
            return
        self._send(500, {"error": "unexpected", "path": path})

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read()
        prior = sum(1 for hit in self.server.hits if hit[1] == "/api/chat")
        self.server.hits.append(("POST", path, body.get("model")))
        if path != "/api/chat":
            self._send(500, {"error": "unexpected", "path": path})
            return
        if self.server.drop_tokens:
            self._send(200, {"message": {"role": "assistant", "content": BAD}, "done": True})
            return
        text = BAD
        if not self.server.always_bad and prior >= 2:
            time.sleep(0.15)
            text = GOOD
        self._send(
            200,
            {
                "model": body.get("model"),
                "message": {"role": "assistant", "content": text},
                "prompt_eval_count": 12 + prior,
                "eval_count": 8,
                "done": True,
            },
        )


class TrialCase(unittest.TestCase):
    def setUp(self):
        self.base = ROOT / "tmp" / "multiagents-trial-tests" / ("%s-%s" % (os.getpid(), id(self)))
        self.base.mkdir(parents=True)
        self.server = None
        self.outside = None
        self.task_hash = _hash_tree(TASK)

    def tearDown(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        shutil.rmtree(self.base, ignore_errors=True)
        if self.outside is not None:
            shutil.rmtree(self.outside, ignore_errors=True)

    def start_server(self, tags=("qwen3.6:35b",), drop_tokens=False, always_bad=False):
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.tags = list(tags)
        server.drop_tokens = drop_tokens
        server.always_bad = always_bad
        server.hits = []
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        self.server = server
        self.host = "http://127.0.0.1:%d" % server.server_address[1]
        return server

    def make_repo(self, under_tmp=True) -> Path:
        if under_tmp:
            repo = self.base / "repo"
            repo.mkdir()
        else:
            self.outside = Path(tempfile.mkdtemp(prefix="ma-repo-"))
            repo = self.outside
        (repo / "keep.txt").write_text("keep\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "keep.txt"], cwd=repo, check=True)
        subprocess.run(
            ["git", "-c", "user.email=trial@example.com", "-c", "user.name=Trial", "commit", "-q", "-m", "init"],
            cwd=repo,
            check=True,
        )
        return repo

    def invoke(self, args=None, host="server", max_cost="0", timeout=20):
        cmd = [
            sys.executable,
            str(SCRIPT),
            "--task",
            str(TASK),
            "--out",
            str(self.base / "out.json"),
            "--scratch",
            str(self.base / "scratch"),
        ]
        if max_cost is not None:
            cmd.extend(["--max-cost", max_cost])
        cmd.extend(args or [])
        env = os.environ.copy()
        for key in list(env):
            up = key.upper()
            if up.endswith("_API_KEY") or up in {"OPENAI_BASE_URL", "ANTHROPIC_API_KEY", "XAI_API_KEY"}:
                env.pop(key, None)
        if host == "server":
            env["OLLAMA_HOST"] = self.host
        elif host is not None:
            env["OLLAMA_HOST"] = host
        else:
            env.pop("OLLAMA_HOST", None)
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = self.base / "out.json"
        rec = json.loads(out.read_text(encoding="utf-8")) if out.exists() else None
        return proc, rec

    def assert_tree_kept(self, repo: Path):
        self.assertEqual((repo / "keep.txt").read_text(encoding="utf-8"), "keep\n")
        self.assertFalse((repo / "solution.py").exists())
        proc = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(proc.stdout, "")
        self.assertEqual(_hash_tree(TASK), self.task_hash)


def _hash_tree(path: Path) -> str:
    digest = hashlib.sha256()
    for file in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(file.relative_to(path).as_posix().encode())
        digest.update(file.read_bytes())
    return digest.hexdigest()


def _grade(code: str) -> list:
    sys.dont_write_bytecode = True
    ns: dict = {}
    exec(compile(code, "solution.py", "exec"), ns, ns)  # noqa: S102
    import importlib.util

    spec = importlib.util.spec_from_file_location("task_tests_trial", TASK / "test_task.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return list(mod.run_tests(ns))


class MultiagentsTrialTest(TrialCase):
    def test_local_review_beats_solo_and_records_cost(self):
        self.start_server()
        repo = self.make_repo(under_tmp=False)
        proc, rec = self.invoke(["--repo", str(repo)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIsNotNone(rec)
        self.assertEqual(rec["address"], "sdk@litellm/ollama/qwen3.6:35b")
        self.assertEqual(rec["model"], "qwen3.6:35b")
        self.assertTrue(rec["local"])
        self.assertTrue(rec["priced"])
        self.assertEqual(rec["cost_usd"], 0)
        self.assertEqual(rec["max_cost_usd"], 0)
        self.assertFalse(rec["applied"])
        self.assertTrue(str(rec["host"]).startswith("http://127.0.0.1:"))
        chats = [hit for hit in self.server.hits if hit[1] == "/api/chat"]
        self.assertGreaterEqual(len(chats), 3)
        self.assertTrue(all(hit[2] == "qwen3.6:35b" for hit in chats))
        self.assertFalse(any(hit[1] == "/api/pull" for hit in self.server.hits))
        solo = rec["arms"]["solo"]
        review = rec["arms"]["review"]
        self.assertFalse(solo["pass"])
        self.assertTrue(review["pass"])
        self.assertEqual(solo["calls"], 1)
        self.assertEqual(review["calls"], 2)
        for arm in (solo, review):
            self.assertGreater(arm["tokens_in"], 0)
            self.assertGreater(arm["tokens_out"], 0)
            self.assertIn("tokens_cached", arm)
            self.assertEqual(arm["cost_usd"], 0)
            self.assertGreaterEqual(arm["seconds"], 0)
        self.assertGreaterEqual(review["seconds"], 0.1)
        self.assertEqual(rec["comparison"]["winner"], "review")
        self.assert_tree_kept(repo)

    def test_failed_task_still_records_and_leaves_tree(self):
        self.start_server(always_bad=True)
        repo = self.make_repo(under_tmp=False)
        proc, rec = self.invoke(["--repo", str(repo)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(rec["arms"]["solo"]["pass"])
        self.assertFalse(rec["arms"]["review"]["pass"])
        self.assertEqual(rec["comparison"]["winner"], "neither")
        self.assertEqual(rec["cost_usd"], 0)
        self.assertGreater(rec["arms"]["review"]["tokens_in"], 0)
        self.assertFalse(rec["applied"])
        self.assert_tree_kept(repo)

    def test_paid_and_unpriced_workers_refused(self):
        self.start_server()
        repo = self.make_repo(under_tmp=False)
        cases = (
            ("claude@haiku", "paid"),
            ("codex@gpt-6-luna", "paid"),
            ("sdk@gpt-4o", "paid"),
            ("sdk@litellm/openai/gpt-4o-mini", "paid"),
            ("sdk@litellm/anthropic/claude-3", "paid"),
            ("sdk@litellm/xai/grok-4", "paid"),
            ("sdk@litellm/openrouter/foo", "paid"),
            ("sdk@litellm/modal/foo", "paid"),
            ("sdk@litellm/mysterybox/some-model", "unpriced"),
        )
        for worker, needle in cases:
            with self.subTest(worker=worker):
                self.server.hits.clear()
                proc, rec = self.invoke(["--repo", str(repo), "--worker", worker])
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn(needle, (rec or {}).get("refused", "").lower())
                self.assertFalse(rec["priced"])
                self.assertIsNone(rec["cost_usd"])
                self.assertFalse(any(hit[1] == "/api/chat" for hit in self.server.hits))
                self.assertFalse(any(hit[1] == "/api/pull" for hit in self.server.hits))
                self.assert_tree_kept(repo)

    def test_unpriced_response_stops(self):
        self.start_server(drop_tokens=True)
        repo = self.make_repo(under_tmp=False)
        proc, rec = self.invoke(["--repo", str(repo)])
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("unpriced", rec["refused"].lower())
        self.assertFalse(rec["priced"])
        self.assertIsNone(rec["cost_usd"])
        self.assertNotIn("review", rec.get("arms") or {})
        chats = [hit for hit in self.server.hits if hit[1] == "/api/chat"]
        self.assertEqual(len(chats), 1)
        self.assertFalse(any(hit[1] == "/api/pull" for hit in self.server.hits))
        self.assert_tree_kept(repo)

    def test_missing_tag_does_not_pull(self):
        self.start_server(tags=("qwen2.5:14b", "qwen3.6:35b-draft"))
        repo = self.make_repo(under_tmp=False)
        proc, rec = self.invoke(["--repo", str(repo)])
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("refusing to pull", rec["refused"])
        paths = [hit[1] for hit in self.server.hits]
        self.assertIn("/api/tags", paths)
        self.assertNotIn("/api/chat", paths)
        self.assertNotIn("/api/pull", paths)
        self.assert_tree_kept(repo)

    def test_tags_down_refuses_without_pull(self):
        repo = self.make_repo(under_tmp=False)
        proc, rec = self.invoke(["--repo", str(repo)], host="http://127.0.0.1:1", timeout=8)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("refusing to pull", rec["refused"])
        self.assertIn("cannot list", rec["refused"])
        self.assert_tree_kept(repo)

    def test_nonlocal_host_refused(self):
        repo = self.make_repo(under_tmp=False)
        proc, rec = self.invoke(["--repo", str(repo)], host="http://192.0.2.1:11434", timeout=5)
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("non-local", rec["refused"])
        self.assert_tree_kept(repo)

    def test_apply_outside_tmp_refused(self):
        self.start_server()
        repo = self.make_repo(under_tmp=False)
        proc, rec = self.invoke(["--repo", str(repo), "--apply"])
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("apply", rec["refused"])
        self.assertFalse(any(hit[1] == "/api/chat" for hit in self.server.hits))
        self.assert_tree_kept(repo)

    def test_apply_under_tmp_writes_winner(self):
        self.start_server()
        repo = self.make_repo(under_tmp=True)
        proc, rec = self.invoke(["--repo", str(repo), "--apply"])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(rec["applied"])
        self.assertEqual((repo / "keep.txt").read_text(encoding="utf-8"), "keep\n")
        solution = (repo / "solution.py").read_text(encoding="utf-8")
        self.assertEqual(_grade(solution), [])
        self.assertEqual(_hash_tree(TASK), self.task_hash)

    def test_max_cost_required_and_negative_refused(self):
        self.start_server()
        repo = self.make_repo(under_tmp=False)
        missing, rec = self.invoke(["--repo", str(repo)], max_cost=None)
        self.assertEqual(missing.returncode, 2, missing.stderr)
        self.assertIn("max-cost", rec["refused"])
        self.assertFalse(any(hit[1] == "/api/chat" for hit in self.server.hits))
        self.server.hits.clear()
        negative, rec2 = self.invoke(["--repo", str(repo)], max_cost="-1")
        self.assertEqual(negative.returncode, 2, negative.stderr)
        self.assertIn("max-cost", rec2["refused"])
        self.assertFalse(any(hit[1] == "/api/chat" for hit in self.server.hits))
        self.assert_tree_kept(repo)


if __name__ == "__main__":
    unittest.main()
