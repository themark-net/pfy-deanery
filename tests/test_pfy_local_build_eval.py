#!/usr/bin/env python3
"""Behavior tests for the local-build coding eval. No real model."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

def _bwrap_ok() -> bool:
    if not shutil.which("bwrap"):
        return False
    try:
        proc = subprocess.run(
            ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--unshare-net", "--", "true"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


BWRAP_OK = _bwrap_ok()

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / "tmp" / "local-build-eval-tests"
FIXTURES = ROOT / "eval" / "local-build" / "fixtures"
TASKS = json.loads((ROOT / "eval" / "local-build" / "tasks.json").read_text(encoding="utf-8"))["tasks"]
PROTECTED = {row["id"] for row in TASKS if row.get("protect")}

STUB = r"""#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

argv = sys.argv[1:]
if "--version" in argv or not argv or argv[0] in ("-h", "--help"):
    print("stub-opencode 0")
    raise SystemExit(0)
if argv[0] != "run":
    raise SystemExit(0)
marker = os.environ.get("PFY_STUB_MARKER")
if marker:
    try:
        Path(marker).parent.mkdir(parents=True, exist_ok=True)
        Path(marker).write_text("started\n", encoding="utf-8")
    except OSError:
        pass
root = Path.cwd()
try:
    (root / "tmp").mkdir(parents=True, exist_ok=True)
    (root / "tmp" / "pfy-agent-started").write_text("started\n", encoding="utf-8")
except OSError:
    pass
scenario = os.environ.get("PFY_LOCAL_BUILD_SCENARIO", "noop")
task_id = (root / "task.id").read_text(encoding="utf-8").strip() if (root / "task.id").is_file() else ""
if scenario == "solve":
    allow = [item for item in os.environ.get("PFY_STUB_SOLVE_IDS", "").split(",") if item]
    if allow and task_id not in allow:
        raise SystemExit(0)
    patch = Path(os.environ["PFY_STUB_FIXTURES"]) / task_id / "reference.patch"
    applied = subprocess.run(["git", "apply", str(patch)], cwd=root, capture_output=True, text=True)
    if applied.returncode != 0:
        sys.stderr.write(applied.stderr or applied.stdout or "git apply failed\n")
        raise SystemExit(applied.returncode)
elif scenario == "break":
    target = next(root.joinpath("src").glob("*.py"))
    target.write_text("def broken(:\n", encoding="utf-8")
elif scenario == "delete-tests":
    for path in root.joinpath("tests").glob("test_*.py"):
        if path.name != "test_keep.py":
            path.unlink()
elif scenario == "protect":
    path = root / "tests" / "test_task.py"
    path.write_text(path.read_text(encoding="utf-8") + "\n# touched\n", encoding="utf-8")
elif scenario == "cheat-asserts":
    for path in root.joinpath("tests").glob("test_*.py"):
        lines = []
        for line in path.read_text(encoding="utf-8").splitlines(True):
            if "self.assert" in line and "assertTrue(True)" not in line:
                indent = line[: len(line) - len(line.lstrip())]
                lines.append(indent + "self.assertTrue(True)\n")
            else:
                lines.append(line)
        path.write_text("".join(lines), encoding="utf-8")
raise SystemExit(0)
"""


def _kb(gib: float) -> int:
    return int(round(gib * 1024 * 1024))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        return

    def _send(self, code: int, body: bytes) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/tags"):
            payload = {"models": self.server.tags}
            self._send(200, json.dumps(payload).encode())
            return
        if self.path.startswith("/api/ps"):
            code = getattr(self.server, "ps_code", 200)
            if code != 200:
                self._send(code, b'{"error":"ps"}')
                return
            self._send(200, json.dumps({"models": self.server.ps}).encode())
            return
        if self.path.startswith("/v1/models"):
            self._send(200, json.dumps({"data": [{"id": "fixture:small"}]}).encode())
            return
        self._send(404, b"{}")

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            payload = {}
        self.server.posts.append((self.path, payload))
        if self.path.startswith("/v1/chat/completions"):
            content = "noop"
            if b"pfy-review-v1" in raw:
                content = json.dumps({"verdict": "accept", "reasons": []})
            body = {
                "choices": [{"message": {"role": "assistant", "content": content}, "finish_reason": "stop"}]
            }
            self._send(200, json.dumps(body).encode())
            return
        self._send(200, b'{"ok":true}')


def _serve():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    httpd.tags = [{"name": "fixture:small", "size": 1024 ** 3}]
    httpd.ps = []
    httpd.posts = []
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


class FixtureSelfCheckTests(unittest.TestCase):
    def test_every_fixture_fails_before_the_patch_and_passes_after(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        base = Path(tempfile.mkdtemp(prefix="self-", dir=SCRATCH))
        self.addCleanup(shutil.rmtree, base, True)
        for task in TASKS:
            fixture = FIXTURES / task["id"]
            work = base / task["id"]
            shutil.copytree(fixture, work)
            subprocess.check_call(["git", "-C", str(work), "init", "-b", "main"], stdout=subprocess.DEVNULL)
            before = _unit(work)
            check_before = _check(work, task["check_cmd"])
            self.assertNotEqual(before.returncode, 0, task["id"])
            self.assertNotEqual(check_before, 0, task["id"])
            applied = subprocess.run(
                ["git", "-C", str(work), "apply", "reference.patch"],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(applied.returncode, 0, applied.stderr)
            after = _unit(work)
            check_after = _check(work, task["check_cmd"])
            self.assertEqual(after.returncode, 0, "%s\n%s" % (task["id"], after.stderr))
            self.assertEqual(check_after, 0, task["id"])


def _unit(work: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", "-m", "unittest", "discover", "-s", "tests", "-t", "."],
        cwd=work,
        text=True,
        capture_output=True,
        check=False,
    )


def _check(work: Path, cmd: str) -> int:
    return subprocess.run(["sh", "-c", cmd], cwd=work, text=True, capture_output=True, check=False).returncode


class EvalRunnerTests(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(prefix="eval-", dir=SCRATCH))
        self.mem = self.tmp / "meminfo"
        self.marker = self.tmp / "marker"
        self.stub = self.tmp / "opencode"
        self.stub.write_text(STUB, encoding="utf-8")
        self.stub.chmod(0o755)
        self.write_mem(40, 8, 8)
        self.httpd = _serve()
        self.port = self.httpd.server_address[1]
        self.addCleanup(self.httpd.shutdown)
        self.addCleanup(self.httpd.server_close)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def write_mem(self, available_gib, swap_free_gib, swap_total_gib):
        self.mem.write_text(
            "MemTotal: %d kB\nMemAvailable: %d kB\nSwapTotal: %d kB\nSwapFree: %d kB\n"
            % (_kb(128), _kb(available_gib), _kb(swap_total_gib), _kb(swap_free_gib)),
            encoding="utf-8",
        )

    def env(self, scenario="solve", **extra):
        env = os.environ.copy()
        for key in list(env):
            if key.startswith("PFY_LOCAL_BUILD_") or key.startswith("PFY_STUB_") or key in (
                "PFY_BOT_OPENCODE",
                "PFY_MEMINFO_FILE",
                "LOCAL_OPENAI_BASE_URL",
            ):
                env.pop(key, None)
        env.update(
            {
                "PFY_MEMINFO_FILE": str(self.mem),
                "PFY_BOT_OPENCODE": str(self.stub),
                "PFY_LOCAL_BUILD_SCENARIO": scenario,
                "PFY_STUB_MARKER": str(self.marker),
                "PFY_STUB_FIXTURES": str(FIXTURES),
                "TMPDIR": str(ROOT / "tmp" / "scratch"),
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        if not BWRAP_OK:
            env["PFY_LOCAL_BUILD_UNSAFE_NO_SANDBOX"] = "1"
        env.update(extra)
        return env

    def run_eval(self, scenario="solve", extra=None, env_extra=None, endpoint=None, timeout=180):
        if self.marker.exists():
            self.marker.unlink()
        cmd = [
            str(ROOT / "pfy"),
            "eval-local-build",
            "--model",
            "fixture:small",
            "--endpoint",
            endpoint or ("http://127.0.0.1:%d/v1" % self.port),
            "--timeout",
            "60",
            "--test-timeout",
            "60",
            "--repo",
            str(self.tmp),
        ]
        if extra:
            cmd.extend(extra)
        proc = subprocess.run(
            cmd,
            cwd=ROOT,
            env=self.env(scenario, **(env_extra or {})),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return proc

    def summary(self, proc):
        blob = proc.stdout + proc.stderr
        if "SKIP:" in proc.stdout:
            self.assertIn("summary: ", blob)
        else:
            self.assertIn("summary=", blob)
        text = proc.stdout + "\n" + proc.stderr
        path = None
        for line in text.splitlines():
            if "summary=" in line:
                path = line.split("summary=", 1)[1].strip()
            if line.startswith("summary: "):
                path = line.split("summary: ", 1)[1].strip()
        self.assertTrue(path, text)
        handle = Path(path)
        self.assertTrue(handle.is_file(), path)
        return json.loads(handle.read_text(encoding="utf-8")), handle

    def test_solve_mode_passes_all_eight(self):
        proc = self.run_eval("solve", timeout=180)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data, path = self.summary(proc)
        self.assertEqual(data["passed"], 8, json.dumps(data, indent=2))
        self.assertEqual(data["pass_rate"], 1.0)
        self.assertEqual(len(data["tasks"]), 8)
        for row in data["tasks"]:
            self.assertEqual(row["status"], "PASS", row["id"] + " " + str(row["reason"]))
            self.assertTrue(Path(row["receipt"]).is_file(), row["id"])
        self.assertTrue(path.with_name("summary.md").is_file())

    def test_do_nothing_is_zero_of_eight(self):
        proc = self.run_eval("noop")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data, _path = self.summary(proc)
        self.assertEqual(data["passed"], 0)
        self.assertEqual(data["failed"], 8)
        self.assertTrue(all(row["reason"] == "no-change" for row in data["tasks"]))

    def test_break_tests_is_zero_of_eight(self):
        proc = self.run_eval("break")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data, _path = self.summary(proc)
        self.assertEqual(data["passed"], 0)
        self.assertEqual(data["failed"], 8)

    def test_delete_tests_is_zero_and_the_reason_comes_from_the_receipt(self):
        proc = self.run_eval("delete-tests")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data, _path = self.summary(proc)
        self.assertEqual(data["passed"], 0)
        self.assertEqual(data["failed"], 8)
        by_id = {row["id"]: row for row in data["tasks"]}
        for task_id in ("t01-fix-off-by-one", "t04-fix-mutable-default", "t08-fix-unicode-strip"):
            self.assertEqual(by_id[task_id]["reason"], "protected-path-changed", task_id)
            receipt = json.loads(Path(by_id[task_id]["receipt"]).read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "FAIL")
            self.assertEqual(receipt["reason"], "protected-path-changed")

    def test_protected_edits_fail_the_protected_tasks(self):
        proc = self.run_eval("protect")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data, _path = self.summary(proc)
        by_id = {row["id"]: row for row in data["tasks"]}
        for task_id in PROTECTED:
            self.assertEqual(by_id[task_id]["status"], "FAIL", task_id)
            self.assertEqual(by_id[task_id]["reason"], "protected-path-changed", task_id)

    def test_mixed_stub_reports_five_of_eight(self):
        solved = ["t01-fix-off-by-one", "t02-add-function", "t03-rename-symbol", "t04-fix-mutable-default", "t05-add-cli-flag"]
        failed = ["t06-parse-duration", "t07-remove-dead-code", "t08-fix-unicode-strip"]
        proc = self.run_eval("solve", env_extra={"PFY_STUB_SOLVE_IDS": ",".join(solved)})
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data, _path = self.summary(proc)
        self.assertEqual(data["passed"], 5)
        self.assertEqual(data["failed"], 3)
        by_id = {row["id"]: row for row in data["tasks"]}
        for task_id in failed:
            self.assertEqual(by_id[task_id]["status"], "FAIL", task_id)
            self.assertEqual(by_id[task_id]["reason"], "no-change", task_id)

    def test_missing_opencode_skips(self):
        proc = self.run_eval("solve", env_extra={"PFY_BOT_OPENCODE": "", "PATH": "/usr/bin:/bin"})
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("SKIP: opencode-missing", proc.stdout)
        data, _path = self.summary(proc)
        self.assertEqual(data["skip"], "opencode-missing")
        self.assertEqual(data["passed"], 0)
        self.assertIsNone(data["pass_rate"])
        self.assertEqual(data["tasks"], [])

    def test_ollama_down_skips(self):
        proc = self.run_eval("solve", endpoint="http://127.0.0.1:9/v1")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("SKIP: ollama-unreachable", proc.stdout)
        data, _path = self.summary(proc)
        self.assertEqual(data["skip"], "ollama-unreachable")
        self.assertEqual(data["passed"], 0)

    def test_require_live_turns_skips_into_exit_2(self):
        missing = self.run_eval(
            "solve",
            extra=["--require-live"],
            env_extra={"PFY_BOT_OPENCODE": "", "PATH": "/usr/bin:/bin"},
        )
        self.assertEqual(missing.returncode, 2, missing.stdout + missing.stderr)
        self.assertIn("SKIP: opencode-missing", missing.stdout)
        down = self.run_eval("solve", extra=["--require-live"], endpoint="http://127.0.0.1:9/v1")
        self.assertEqual(down.returncode, 2, down.stdout + down.stderr)
        self.assertIn("SKIP: ollama-unreachable", down.stdout)

    def test_low_memory_blocks_the_first_task_and_stops(self):
        self.write_mem(10, 0, 64)
        proc = self.run_eval("solve")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data, _path = self.summary(proc)
        self.assertEqual(len(data["tasks"]), 1)
        self.assertEqual(data["tasks"][0]["status"], "BLOCKED")
        self.assertEqual(data["tasks"][0]["reason"], "mem")
        self.assertEqual(data["passed"], 0)
        self.assertEqual(data["blocked"], 1)
        self.assertEqual(len(data["not_run"]), 7)
        self.assertNotIn(data["tasks"][0]["id"], data["not_run"])

    def test_a_second_run_writes_a_new_stamp(self):
        first = self.run_eval("noop", extra=["--limit", "1"])
        second = self.run_eval("noop", extra=["--limit", "1"])
        self.assertEqual(first.returncode, 1, first.stdout + first.stderr)
        self.assertEqual(second.returncode, 1, second.stdout + second.stderr)
        _data1, path1 = self.summary(first)
        _data2, path2 = self.summary(second)
        self.assertNotEqual(path1, path2)
        self.assertTrue(path1.is_file())
        self.assertTrue(path2.is_file())

    def test_recover_when_the_stub_comes_back(self):
        down = self.run_eval("solve", extra=["--limit", "1"], endpoint="http://127.0.0.1:9/v1")
        self.assertEqual(down.returncode, 0, down.stdout + down.stderr)
        self.assertIn("SKIP: ollama-unreachable", down.stdout)
        up = self.run_eval("solve", extra=["--limit", "1"])
        self.assertEqual(up.returncode, 0, up.stdout + up.stderr)
        data, _path = self.summary(up)
        self.assertEqual(data["passed"], 1)
        self.assertIsNone(data["skip"])

    def test_every_task_has_a_real_protect_list(self):
        self.assertEqual(len(TASKS), 8)
        self.assertEqual(PROTECTED, {row["id"] for row in TASKS})
        for row in TASKS:
            self.assertIn("tests/*", row["protect"])

    def test_cheat_asserts_scores_zero_on_t01_t04_t08(self):
        proc = self.run_eval("cheat-asserts")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data, _path = self.summary(proc)
        self.assertEqual(data["passed"], 0)
        self.assertEqual(data["failed"], 8)
        by_id = {row["id"]: row for row in data["tasks"]}
        for task_id in ("t01-fix-off-by-one", "t04-fix-mutable-default", "t08-fix-unicode-strip"):
            self.assertEqual(by_id[task_id]["status"], "FAIL", task_id)
            self.assertIn(by_id[task_id]["reason"], ("protected-path-changed", "tests-tampered"))

    def test_ps_error_skips_closed(self):
        self.httpd.ps_code = 500
        proc = self.run_eval("solve", extra=["--limit", "1"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("SKIP: busy-host unknown", proc.stdout)
        data, _path = self.summary(proc)
        self.assertEqual(data["skip"], "busy-host unknown")
        self.assertEqual(data["tasks"], [])


if __name__ == "__main__":
    unittest.main()
