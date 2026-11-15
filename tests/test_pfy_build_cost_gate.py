"""Cost confirmation before a Deanery model spend.

Drives ./pfy with a fake grok and a fake Ollama. A non-TTY cloud run must
refuse before grok starts. An approved run records the estimate, the choice,
and the actual spend. A cap under the estimate refuses. Local is $0 and does
not ask.

Fail: grok starts with no approval, the receipt omits the choice or the actual,
a low cap still calls grok, or local refuses for cost.
Recover: pass --yes, --approve-cost, or a --max-cost at or above the estimate.
Local needs none of those.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PFY = ROOT / "pfy"
SCRATCH = ROOT / "tmp" / "cost-gate-tests"


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    init = _git(path, "init", "-b", "main")
    if init.returncode != 0:
        raise RuntimeError(init.stderr)
    _git(path, "config", "user.email", "cost-gate@example.com")
    _git(path, "config", "user.name", "cost-gate")
    (path / "README.md").write_text("fixture\n", encoding="utf-8")
    (path / ".gitignore").write_text("tmp/\n", encoding="utf-8")
    _git(path, "add", "README.md", ".gitignore")
    committed = _git(path, "commit", "-m", "init")
    if committed.returncode != 0:
        raise RuntimeError(committed.stderr)
    return path


def _write_exe(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def _drop_worktrees(repo: Path) -> None:
    if not repo.exists():
        return
    proc = _git(repo, "worktree", "list", "--porcelain")
    for line in (proc.stdout or "").splitlines():
        if not line.startswith("worktree "):
            continue
        path = Path(line.split(" ", 1)[1])
        try:
            same = path.resolve() == repo.resolve()
        except OSError:
            same = False
        if same:
            continue
        _git(repo, "worktree", "remove", "--force", str(path))
        shutil.rmtree(path, ignore_errors=True)


GROK_BODY = """#!/usr/bin/env python3
import json, os, sys, urllib.parse
from pathlib import Path
Path(os.environ["PFY_GROK_MARKER"]).write_text("called\\n", encoding="utf-8")
blob = "\\n".join(sys.argv)
if "PFY-CLOUD-REVIEW" in blob:
    print("verdict: accept")
    print("reasons: ok")
    raise SystemExit(0)
root = Path(os.environ["GROK_HOME"]) / "sessions" / urllib.parse.quote(str(Path.cwd().resolve()), safe="") / "sess-cost"
root.mkdir(parents=True, exist_ok=True)
(root / "usage.json").write_text(json.dumps({
    "session": {
        "costUsdTicks": 12500000000,
        "inputTokens": 10,
        "outputTokens": 2,
        "modelCalls": 1,
        "primaryModelId": "grok-4.7",
        "phase": "implement",
    }
}), encoding="utf-8")
Path("kept.py").write_text("value = 1\\n", encoding="utf-8")
raise SystemExit(0)
"""


class CostGateCloud(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.repo = _init_repo(SCRATCH / self.id().replace(".", "_"))
        self.side = SCRATCH / (self.id().replace(".", "_") + "-side")
        self.side.mkdir()
        self.home = self.side / "home"
        self.grok_home = self.side / "grok-home"
        self.home.mkdir()
        self.grok_home.mkdir()
        self.marker = self.side / "grok-called"
        self.grok = _write_exe(self.side / "grok.py", GROK_BODY)
        self.gate = _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n",
        )
        self.receipt_dir = self.side / "receipt"

    def tearDown(self) -> None:
        _drop_worktrees(self.repo)
        shutil.rmtree(self.repo, ignore_errors=True)
        shutil.rmtree(self.side, ignore_errors=True)

    def _env(self) -> dict:
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(self.home),
            "GROK_HOME": str(self.grok_home),
            "TMPDIR": str(SCRATCH),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PFY_GROK_MARKER": str(self.marker),
            "PFY_BUILD_YES": "",
            "CI": "",
            "PFY_COST_HISTORY_ROOT": str(self.side / "no-history"),
            "PFY_MODEL_CHOICE_PATH": str(self.side / "model-choice.json"),
            "PFY_COMPARE_STATE_PATH": str(self.side / "compare-state.json"),
            "GIT_TERMINAL_PROMPT": "0",
        }
        return env

    def _argv(self, *extra: str) -> list[str]:
        return [
            str(PFY),
            "build",
            "add kept value",
            "--repo",
            str(self.repo),
            "--retries",
            "0",
            "--no-review",
            "--timeout",
            "30",
            "--test-cmd",
            "%s %s" % (sys.executable, self.gate),
            "--grok-cmd",
            str(self.grok),
            "--receipt-dir",
            str(self.receipt_dir),
            *extra,
        ]

    def _run(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            self._argv(*extra),
            cwd=self.repo,
            env=self._env(),
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=60,
            check=False,
        )

    def _receipt(self) -> dict:
        path = self.receipt_dir / "receipt.json"
        self.assertTrue(path.is_file(), "receipt missing")
        return json.loads(path.read_text(encoding="utf-8"))

    def test_non_tty_without_approval_refuses_before_grok(self) -> None:
        proc = self._run()
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertNotEqual(proc.returncode, 0, text)
        self.assertFalse(self.marker.exists(), text)
        self.assertIn("model choice:", text)
        self.assertIn("why:", text)
        self.assertIn("local", text)
        self.assertIn("refusing:", text)
        self.assertIn("No model was called", text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "estimate-declined")
        self.assertEqual(payload["choice"]["route"], "cloud")
        self.assertIn("usd", payload["estimate"])
        self.assertEqual(payload["actual"]["source"], "not-run")
        self.assertEqual(payload["actual"]["usd"], 0)

    def test_approve_cost_runs_and_receipt_has_estimate_choice_and_actual(self) -> None:
        proc = self._run("--approve-cost")
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        self.assertTrue(self.marker.exists(), text)
        self.assertIn("model choice: cloud", text)
        self.assertIn("why:", text)
        self.assertIn("$0", text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS", text)
        self.assertEqual(payload["choice"]["route"], "cloud")
        self.assertTrue(payload["choice"]["why"])
        self.assertIn("low", payload["estimate"])
        self.assertIn("high", payload["estimate"])
        self.assertIn("wall_low_s", payload["estimate"])
        self.assertIn("wall_high_s", payload["estimate"])
        self.assertIn("review_prompts", payload["estimate"])
        self.assertEqual(payload["estimate"]["review_prompts"], 0)
        self.assertIn("no review call", text)
        self.assertEqual(payload["estimate"]["alternative"]["route"], "local")
        self.assertEqual(payload["estimate"]["alternative"]["usd"], 0)
        self.assertEqual(payload["actual"]["usd"], 1.25)
        self.assertEqual(payload["actual"]["source"], "usage.json")

    def test_max_cost_below_estimate_refuses_before_grok(self) -> None:
        proc = self._run("--yes", "--max-cost", "0.0001")
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertNotEqual(proc.returncode, 0, text)
        self.assertFalse(self.marker.exists(), text)
        self.assertIn("exceeds", text)
        self.assertIn("--max-cost", text)
        self.assertIn("No model was called", text)
        payload = self._receipt()
        self.assertEqual(payload["reason"], "estimate-declined")
        self.assertEqual(payload["actual"]["source"], "not-run")


class _Tags(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        return

    def _send(self, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        self.server.hits.append(self.path)
        if self.path.startswith("/api/tags"):
            self._send({"models": [{"name": "qwen3.6:35b", "size": 1024}]})
            return
        if self.path.startswith("/api/ps"):
            self._send({"models": []})
            return
        self._send({"ok": True})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        self.server.hits.append(self.path)
        self._send({"ok": True})


class CostGateLocal(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.repo = _init_repo(SCRATCH / self.id().replace(".", "_"))
        self.side = SCRATCH / (self.id().replace(".", "_") + "-side")
        self.side.mkdir()
        self.stub = _write_exe(self.side / "opencode", "#!/bin/sh\necho stub-opencode\n")
        self.mem = self.side / "meminfo"
        self.mem.write_text(
            "MemTotal: 134217728 kB\nMemAvailable: 67108864 kB\n"
            "SwapTotal: 8388608 kB\nSwapFree: 8388608 kB\n",
            encoding="utf-8",
        )
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Tags)
        self.httpd.hits = []
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.httpd.server_address[1]
        self.receipt_dir = self.side / "receipt"

    def tearDown(self) -> None:
        try:
            self.httpd.shutdown()
            self.httpd.server_close()
        except Exception:
            pass
        _drop_worktrees(self.repo)
        shutil.rmtree(self.repo, ignore_errors=True)
        shutil.rmtree(self.side, ignore_errors=True)

    def test_local_shows_zero_and_does_not_require_approval(self) -> None:
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(self.side / "home"),
            "TMPDIR": str(SCRATCH),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PFY_BUILD_YES": "",
            "CI": "",
            "PFY_BOT_OPENCODE": str(self.stub),
            "PFY_MEMINFO_FILE": str(self.mem),
            "PFY_COST_HISTORY_ROOT": str(self.side / "no-history"),
            "PFY_MODEL_CHOICE_PATH": str(self.side / "model-choice.json"),
            "PFY_MODEL_NO_PAID": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
        (self.side / "home").mkdir()
        proc = subprocess.run(
            [
                str(PFY),
                "build",
                "--local",
                "add a note",
                "--repo",
                str(self.repo),
                "--dry-run",
                "--min-free-gb",
                "0",
                "--model",
                "qwen3.6:35b",
                "--endpoint",
                "http://127.0.0.1:%d/v1" % self.port,
                "--receipt-dir",
                str(self.receipt_dir),
            ],
            cwd=self.repo,
            env=env,
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=60,
            check=False,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        self.assertIn("model choice: local", text)
        self.assertIn("qwen3.6:35b", text)
        self.assertIn("why:", text)
        self.assertIn("$0", text)
        self.assertNotIn("Proceed?", text)
        self.assertNotIn("refusing:", text)
        self.assertFalse(any("/api/generate" in hit for hit in self.httpd.hits), self.httpd.hits)
        payload = json.loads((self.receipt_dir / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["choice"]["route"], "local")
        self.assertEqual(payload["estimate"]["usd"], 0)
        self.assertEqual(payload["estimate"]["low"], 0)
        self.assertEqual(payload["estimate"]["high"], 0)
        self.assertEqual(payload["actual"]["usd"], 0)
        self.assertEqual(payload["actual"]["source"], "local")
        self.assertGreater(payload["estimate"]["alternative"]["usd"], 0)
        self.assertIn("review_prompts", payload["estimate"])
        self.assertIn("flake_runs", payload["estimate"])
        self.assertGreaterEqual(payload["estimate"]["flake_runs"], 0)
        self.assertIn("packed review", text)
        self.assertIn("flake-gate re-run", text)


class CostGateCompare(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.side = SCRATCH / self.id().replace(".", "_")
        self.side.mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.side, ignore_errors=True)

    def _env(self) -> dict:
        return {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(self.side / "home"),
            "TMPDIR": str(SCRATCH),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PFY_MODEL_NO_PAID": "1",
            "PFY_BUILD_YES": "",
            "CI": "",
            "XDG_CONFIG_HOME": str(self.side / "config"),
            "XDG_STATE_HOME": str(self.side / "state"),
            "PFY_MODEL_CHOICE_PATH": str(self.side / "model-choice.json"),
            "PFY_COMPARE_STATE_PATH": str(self.side / "compare-state.json"),
        }

    def _run(self, *extra: str) -> subprocess.CompletedProcess:
        (self.side / "home").mkdir(exist_ok=True)
        return subprocess.run(
            [str(PFY), "compare", "catalog-fit", "--against", "grok-4.7", "--last", *extra],
            cwd=ROOT,
            env=self._env(),
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=90,
            check=False,
        )

    def test_paid_compare_does_not_auto_run_off_a_tty(self) -> None:
        proc = self._run()
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertNotEqual(proc.returncode, 0, text)
        self.assertIn("no TTY", text)
        self.assertIn("model choice:", text)
        self.assertIn("$0", text)
        self.assertNotIn("paid cloud call blocked", text)
        self.assertFalse((ROOT / "tmp" / "compare-catalog-fit.json").exists())

    def test_max_cost_below_the_compare_estimate_does_not_call(self) -> None:
        proc = self._run("--yes", "--max-cost", "0.0001")
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertNotEqual(proc.returncode, 0, text)
        self.assertIn("exceeds", text)
        self.assertNotIn("paid cloud call blocked", text)


P_GROK = """#!/usr/bin/env python3
import json, os, urllib.parse
from pathlib import Path
marker = os.environ.get("PFY_GROK_MARKER", "")
if marker:
    Path(marker).write_text("called\\n", encoding="utf-8")
home = Path(os.environ["GROK_HOME"])
encoded = urllib.parse.quote(str(Path.cwd().resolve()), safe="")
sess = home / "sessions" / encoded / "sess-p"
sess.mkdir(parents=True, exist_ok=True)
(sess / "usage.json").write_text(
    json.dumps({"session": {"costUsdTicks": 12500000000}}),
    encoding="utf-8",
)
raise SystemExit(0)
"""


class CostGatePrompt(unittest.TestCase):
    """pfy build -p is a paid grok -p. Same gate, before that binary runs."""

    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.side = SCRATCH / self.id().replace(".", "_")
        if self.side.exists():
            shutil.rmtree(self.side)
        self.side.mkdir(parents=True)
        self.cwd = self.side / "cwd"
        self.cwd.mkdir()
        self.home = self.side / "grok-home"
        self.home.mkdir()
        (self.home / "auth.json").write_text('{"token":"test-not-real-0123456789"}', encoding="utf-8")
        (self.home / "bundled").mkdir()
        self.marker = self.side / "grok-called"
        bindir = self.side / "bin"
        bindir.mkdir()
        grok = bindir / "grok"
        grok.write_text(P_GROK, encoding="utf-8")
        grok.chmod(0o755)
        self.bindir = bindir

    def tearDown(self) -> None:
        shutil.rmtree(self.side, ignore_errors=True)

    def _env(self) -> dict:
        return {
            "PATH": str(self.bindir) + os.pathsep + os.environ.get("PATH", ""),
            "HOME": str(self.side / "home"),
            "GROK_HOME": str(self.home),
            "TMPDIR": str(SCRATCH),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PFY_GROK_MARKER": str(self.marker),
            "PFY_BUILD_YES": "",
            "CI": "",
            "PFY_STATE_DIR": str(self.side / "state"),
            "PFY_COST_HISTORY_ROOT": str(self.side / "no-history"),
            "PFY_JEV_OFFLINE": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }

    def _run(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(PFY), "build", "-p", "add a note", "--cwd", str(self.cwd), *extra],
            cwd=self.cwd,
            env=self._env(),
            text=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=180,
            check=False,
        )

    def _rows(self) -> list:
        receipts = list((self.cwd / "pipelines" / "dogfood" / "build").glob("*/receipt.jsonl"))
        self.assertEqual(len(receipts), 1, receipts)
        return [json.loads(line) for line in receipts[0].read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_non_tty_without_approval_refuses_before_grok(self) -> None:
        proc = self._run()
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertNotEqual(proc.returncode, 0, text)
        self.assertEqual(proc.returncode, 2, text)
        self.assertFalse(self.marker.exists(), text)
        self.assertIn("model choice:", text)
        self.assertIn("why:", text)
        self.assertIn("local", text)
        self.assertIn("refusing:", text)
        self.assertIn("No model was called", text)
        rows = self._rows()
        declined = next(row for row in rows if row.get("reason") == "estimate-declined")
        self.assertEqual(declined["choice"]["route"], "cloud")
        self.assertEqual(declined["actual"]["source"], "not-run")
        self.assertEqual(declined["actual"]["usd"], 0)
        self.assertNotIn("grok_p", [row.get("event") for row in rows])

    def test_approve_cost_runs_and_receipt_has_estimate_choice_and_actual(self) -> None:
        proc = self._run("--approve-cost")
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        self.assertTrue(self.marker.exists(), text)
        row = next(item for item in self._rows() if item.get("event") == "grok_p")
        self.assertEqual(row["choice"]["route"], "cloud")
        self.assertIn("low", row["estimate"])
        self.assertIn("high", row["estimate"])
        self.assertEqual(row["estimate"]["alternative"]["route"], "local")
        self.assertEqual(row["estimate"]["alternative"]["usd"], 0)
        self.assertEqual(row["actual"]["usd"], 1.25)
        self.assertEqual(row["actual"]["source"], "usage.json")

    def test_max_cost_below_estimate_refuses_before_grok(self) -> None:
        proc = self._run("--yes", "--max-cost", "0.0001")
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 2, text)
        self.assertFalse(self.marker.exists(), text)
        self.assertIn("exceeds", text)
        self.assertIn("--max-cost", text)
        self.assertIn("No model was called", text)
        declined = next(row for row in self._rows() if row.get("reason") == "estimate-declined")
        self.assertEqual(declined["actual"]["source"], "not-run")


if __name__ == "__main__":
    unittest.main()
