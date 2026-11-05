"""Launch session owns the process it spawned, and the smoke accepts a reasoning reply.

Drives ./pfy launch in a temp HOME and PFY_STATE_DIR. The fake engine is the
only model endpoint. A grok process started before launch stands in for the
operator session and must still be alive at the end.

How this fails and how we recover: a terminal that exits immediately and
leaves no harness child is FAIL "terminal exited", and no pid file is written.
A smoke failure after that terminal is up must reap the spawn and leave a
pre-existing grok alive. Recover by signalling only the pid this launch
started when its start time still matches, or a descendant of that spawn,
then clearing pid files and returning FAIL with the smoke reason and a next step.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
PFY = ROOT / "pfy"
REASON_MODEL = "reason-first"
CODER_MODEL = "coder-second"
MISSING_MODEL = "not-listed"
TERMINAL_NAMES = (
    "xdg-terminal-exec",
    "kitty",
    "alacritty",
    "wezterm",
    "xterm",
    "konsole",
    "gnome-terminal",
    "xfce4-terminal",
)


def _proc_start(pid):
    """Start time from /proc/<pid>/stat field 22 (clock ticks since boot)."""
    raw = Path("/proc/%d/stat" % int(pid)).read_text(encoding="utf-8", errors="replace")
    end = raw.rfind(")")
    fields = raw[end + 1 :].split()
    return fields[19]


def _ppid(pid):
    try:
        text = Path("/proc/%d/status" % int(pid)).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    for line in text.splitlines():
        if line.startswith("PPid:"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return int(parts[1])
            return 0
    return 0


def _descends_from(pid, ancestor):
    """True when pid is a strict descendant of ancestor."""
    try:
        cur = int(pid)
        ancestor = int(ancestor)
    except (TypeError, ValueError):
        return False
    seen = set()
    while cur > 1 and cur not in seen:
        seen.add(cur)
        cur = _ppid(cur)
        if cur == ancestor:
            return True
    return False


def _alive(pid):
    try:
        os.kill(int(pid), 0)
    except OSError:
        return False
    return True


def _wait_dead(pid, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline and _alive(pid):
        time.sleep(0.05)
    return not _alive(pid)


def _pid_list(path):
    if not path.is_file():
        return []
    found = []
    for token in path.read_text(encoding="utf-8", errors="replace").split():
        if token.isdigit():
            found.append(int(token))
    return found


def _json_object(text):
    for line in reversed((text or "").splitlines()):
        s = line.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                data = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                return data
    return {}


def _pid_in_file(path, pid):
    if not path.is_file():
        return False
    want = str(int(pid))
    return want in path.read_text(encoding="utf-8", errors="replace").split()


class _Engine(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, server_address, handler):
        super().__init__(server_address, handler)
        self.models = [REASON_MODEL, CODER_MODEL]
        self.mode = "reason"
        self.posts = []


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        return

    def _send(self, code, body):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self._send(200, '{"status":"ok"}')
            return
        if path == "/v1/models":
            self._send(200, json.dumps({"data": [{"id": name} for name in self.server.models]}))
            return
        if path == "/api/tags":
            self._send(200, json.dumps({"models": [{"name": name} for name in self.server.models]}))
            return
        self._send(404, "{}")

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        self.server.posts.append(payload)
        model = str(payload.get("model") or "")
        if self.server.mode == "empty":
            message = {"role": "assistant", "content": "", "reasoning": "", "reasoning_content": ""}
        elif model == REASON_MODEL:
            message = {
                "role": "assistant",
                "content": "",
                "reasoning": "PFY_ATTACH_SMOKE_OK",
                "reasoning_content": "",
            }
        else:
            message = {
                "role": "assistant",
                "content": "PFY_ATTACH_SMOKE_OK",
                "reasoning": "",
                "reasoning_content": "",
            }
        body = {"choices": [{"finish_reason": "length", "message": message}]}
        self._send(200, json.dumps(body))


TERMINAL_SHIM = """#!/bin/sh
# Fake terminal. Runs the harness command as a child and stays the parent.
echo $$ > "${PFY_TEST_TERMINAL_PID}"
if [ "${PFY_TEST_TERMINAL_EXIT:-}" = "1" ]; then
  exit 0
fi
cmd=""
prev=""
for arg in "$@"; do
  if [ "$prev" = "-e" ] || [ "$prev" = "--" ]; then
    cmd=$arg
    break
  fi
  prev=$arg
done
if [ -z "$cmd" ]; then
  for arg in "$@"; do
    cmd=$arg
  done
fi
if [ -z "$cmd" ]; then
  exit 1
fi
case "$cmd" in
  *" "*)
    sh -c "$cmd" &
    ;;
  *)
    "$cmd" &
    ;;
esac
wait
"""

GROK_SHIM = """#!/bin/sh
# Stays named grok (no exec) so a cmdline scan can see this process.
echo $$ >> "${PFY_TEST_PIDS}"
sleep 300
"""


class LaunchSessionE2E(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pfy-launch-e2e-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.state = self.root / "state"
        self.bindir = self.root / "bin"
        self.home.mkdir()
        self.state.mkdir()
        self.bindir.mkdir()
        self.term_pid_path = self.root / "terminal.pid"
        self.pids_path = self.root / "pids"
        self._write_bin("grok", GROK_SHIM)
        shim = self._write_bin("_terminal", TERMINAL_SHIM)
        for name in TERMINAL_NAMES:
            os.symlink(shim, self.bindir / name)
        self.engine = _Engine(("127.0.0.1", 0), _Handler)
        self.engine.daemon_threads = True
        self.port = self.engine.server_address[1]
        self.base = "http://127.0.0.1:%d" % self.port
        self._thread = threading.Thread(target=self.engine.serve_forever, daemon=True)
        self._thread.start()
        self.addCleanup(self._stop_engine)
        self.foreign = subprocess.Popen(
            [str(self.bindir / "grok")],
            cwd=str(self.home),
            env=self._env(),
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.addCleanup(self._kill_our_processes)
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and not _alive(self.foreign.pid):
            time.sleep(0.02)
        self.assertTrue(_alive(self.foreign.pid), "pre-existing grok did not stay up")

    def _write_bin(self, name, text):
        path = self.bindir / name
        path.write_text(text, encoding="utf-8")
        path.chmod(0o755)
        return path

    def _env(self, extra=None, terminal_exit=False):
        env = {
            "PATH": "%s:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" % self.bindir,
            "HOME": str(self.home),
            "PFY_STATE_DIR": str(self.state),
            "PFY_TEST_OPENAI_BASE": self.base,
            "LOCAL_OPENAI_BASE_URL": self.base,
            "DISPLAY": ":99",
            "PFY_TEST_TERMINAL_PID": str(self.term_pid_path),
            "PFY_TEST_PIDS": str(self.pids_path),
            "GROK_HOME": str(self.home / ".grok"),
            "XDG_CONFIG_HOME": str(self.home / ".config"),
            "TMPDIR": os.environ.get("TMPDIR") or str(ROOT / "tmp"),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        if terminal_exit:
            env["PFY_TEST_TERMINAL_EXIT"] = "1"
        if extra:
            env.update(extra)
        return env

    def _stop_engine(self):
        try:
            self.engine.shutdown()
        except Exception:
            pass
        try:
            self.engine.server_close()
        except Exception:
            pass

    def _our_pids(self):
        marker = str(self.bindir)
        found = []
        proc = Path("/proc")
        if not proc.is_dir():
            return found
        for entry in proc.iterdir():
            if not entry.name.isdigit():
                continue
            try:
                cmd = (entry / "cmdline").read_bytes().replace(b"\x00", b" ").decode("utf-8", "replace")
            except OSError:
                continue
            if marker in cmd:
                found.append(int(entry.name))
        return found

    def _kill_our_processes(self):
        pids = set(self._our_pids())
        if getattr(self, "foreign", None) is not None:
            pids.add(self.foreign.pid)
        for pid in list(pids):
            try:
                pgid = os.getpgid(pid)
            except OSError:
                continue
            if pgid <= 1 or pgid == os.getpgrp():
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
                continue
            try:
                os.killpg(pgid, signal.SIGKILL)
            except OSError:
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
        foreign = getattr(self, "foreign", None)
        if foreign is not None:
            try:
                foreign.wait(timeout=1)
            except Exception:
                pass

    def _run(self, args, env, timeout):
        try:
            return subprocess.run(
                [str(PFY), *args],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            self._kill_our_processes()
            out = (exc.stdout or "") + (exc.stderr or "")
            self.fail("timeout %s\n%s" % (args, out[-2000:]))

    def _compose(self, env):
        steps = (
            ["launch", "runtime"],
            ["launch", "lane", "local"],
            ["launch", "toolset", "bare"],
            ["launch", "harness", "grok"],
        )
        for args in steps:
            proc = self._run(args, env, 30)
            blob = (proc.stdout or "") + (proc.stderr or "")
            self.assertEqual(proc.returncode, 0, "%s\n%s" % (args, blob[-2000:]))
            body = _json_object(proc.stdout)
            self.assertTrue(body.get("ok"), "%s\n%s" % (args, blob[-2000:]))

    def _launch(self, extra=None, terminal_exit=False, mode="reason"):
        self.engine.mode = mode
        self.engine.posts.clear()
        env = self._env(extra, terminal_exit=terminal_exit)
        self._compose(env)
        proc = self._run(["launch"], env, 45)
        return proc, _json_object(proc.stdout)

    def _assert_foreign_untouched(self):
        self.assertTrue(_alive(self.foreign.pid), "pre-existing grok was signalled")
        self.assertFalse(_pid_in_file(self.state / "sidecar-grok.pid", self.foreign.pid))
        self.assertFalse(_pid_in_file(self.state / "grok-terminal.pid", self.foreign.pid))

    def test_launch_owns_its_pid_and_accepts_a_reasoning_reply(self):
        proc, body = self._launch()
        blob = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, blob[-2000:])
        self.assertTrue(body.get("ok"), blob[-2000:])
        reported = int(body.get("pid") or 0)
        self.assertGreater(reported, 1)
        self.assertNotEqual(reported, self.foreign.pid)
        terminal = int(self.term_pid_path.read_text(encoding="utf-8").strip())
        self.assertTrue(
            _descends_from(reported, terminal),
            "reported pid %s does not descend from terminal %s" % (reported, terminal),
        )
        self.assertEqual(body.get("smoke_field"), "reasoning", blob[-2000:])
        self.assertTrue(self.engine.posts, "smoke never called the engine")
        self.assertGreaterEqual(int(self.engine.posts[-1].get("max_tokens") or 0), 256)
        self.assertEqual(self.engine.posts[-1].get("model"), REASON_MODEL)
        self._assert_foreign_untouched()

    def test_pfy_ollama_model_wins_when_it_is_on_the_live_list(self):
        proc, body = self._launch(extra={
            "PFY_OLLAMA_MODEL": CODER_MODEL,
            "LOCAL_CODER_MODEL": REASON_MODEL,
        })
        blob = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, blob[-2000:])
        self.assertTrue(body.get("ok"), blob[-2000:])
        self.assertTrue(self.engine.posts, blob[-2000:])
        self.assertEqual(self.engine.posts[-1].get("model"), CODER_MODEL)
        self.assertEqual(body.get("model"), CODER_MODEL)
        self.assertEqual(body.get("smoke_field"), "content")
        self._assert_foreign_untouched()

    def test_local_coder_model_beats_the_recorded_pin(self):
        (self.state / "pinned-model").write_text(REASON_MODEL + "\n", encoding="utf-8")
        proc, body = self._launch(extra={"LOCAL_CODER_MODEL": CODER_MODEL})
        blob = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, blob[-2000:])
        self.assertEqual(self.engine.posts[-1].get("model"), CODER_MODEL, blob[-2000:])
        self.assertEqual(body.get("model"), CODER_MODEL)
        self._assert_foreign_untouched()

    def test_recorded_state_model_is_used_when_env_is_unset(self):
        (self.state / "pinned-model").write_text(CODER_MODEL + "\n", encoding="utf-8")
        proc, body = self._launch()
        blob = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, blob[-2000:])
        self.assertEqual(self.engine.posts[-1].get("model"), CODER_MODEL, blob[-2000:])
        self.assertEqual(body.get("model"), CODER_MODEL)
        self.assertEqual(body.get("smoke_field"), "content")
        self._assert_foreign_untouched()

    def test_model_missing_from_the_live_list_names_the_pull(self):
        proc, body = self._launch(extra={"PFY_OLLAMA_MODEL": MISSING_MODEL})
        blob = (proc.stdout or "") + (proc.stderr or "")
        self.assertNotEqual(proc.returncode, 0, blob[-2000:])
        self.assertFalse(body.get("ok"))
        self.assertIn("model %s not on live endpoint" % MISSING_MODEL, blob)
        self.assertIn("./pfy models pull %s" % MISSING_MODEL, blob)
        self._assert_foreign_untouched()

    def test_empty_completion_fails(self):
        proc, body = self._launch(mode="empty")
        blob = (proc.stdout or "") + (proc.stderr or "")
        self.assertNotEqual(proc.returncode, 0, blob[-2000:])
        self.assertFalse(body.get("ok"))
        self.assertIn("smoke empty completion", blob)
        self._assert_foreign_untouched()

    def test_terminal_that_exits_is_not_a_foreign_pid(self):
        proc, body = self._launch(terminal_exit=True)
        blob = (proc.stdout or "") + (proc.stderr or "")
        self.assertNotEqual(proc.returncode, 0, blob[-2000:])
        self.assertFalse(body.get("ok"))
        self.assertIn("terminal exited", blob)
        self.assertFalse((self.state / "sidecar-grok.pid").exists(), blob[-2000:])
        self.assertFalse((self.state / "grok-terminal.pid").exists(), blob[-2000:])
        self._assert_foreign_untouched()

    def test_reuse_requires_the_recorded_start_time(self):
        proc, body = self._launch()
        blob = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, blob[-2000:])
        first = int(body.get("pid") or 0)
        self.assertTrue(_descends_from(first, int(self.term_pid_path.read_text().strip())))
        start = _proc_start(first)
        recorded = [
            path for path in self.state.iterdir()
            if path.is_file() and path.read_text(encoding="utf-8", errors="replace").strip() == start
        ]
        self.assertTrue(recorded, "spawn start time was not recorded in the state dir")
        for path in recorded:
            path.write_text("0\n", encoding="utf-8")
        first_terminal = self.term_pid_path.read_text(encoding="utf-8")
        proc, body = self._launch()
        blob = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, blob[-2000:])
        second = int(body.get("pid") or 0)
        terminal = int(self.term_pid_path.read_text(encoding="utf-8").strip())
        self.assertNotEqual(self.term_pid_path.read_text(encoding="utf-8"), first_terminal)
        self.assertNotEqual(second, first)
        self.assertNotEqual(second, self.foreign.pid)
        self.assertTrue(_descends_from(second, terminal), "new pid %s terminal %s" % (second, terminal))
        self.assertTrue(_alive(first), "earlier session was signalled after a start-time mismatch")
        self._assert_foreign_untouched()

    def test_smoke_failure_after_spawn_reaps_only_our_terminal(self):
        """Smoke FAIL after a new GUI spawn reaps that spawn and spares a pretender.

        The pretender is a grok started before launch. It must still be alive
        and absent from pid files. The harness and terminal this launch started
        must be gone, and the FAIL must name the smoke reason and a next step.
        """
        before = set(_pid_list(self.pids_path))
        proc, body = self._launch(mode="empty")
        blob = (proc.stdout or "") + (proc.stderr or "")
        self.assertNotEqual(proc.returncode, 0, blob[-2000:])
        self.assertFalse(body.get("ok"))
        self.assertEqual(body.get("live"), "FAIL")
        self.assertEqual(body.get("error"), "smoke empty completion")
        self.assertIn("./pfy up", body.get("next_step") or "", blob[-2000:])
        spawned = [pid for pid in _pid_list(self.pids_path) if pid not in before and pid != self.foreign.pid]
        self.assertTrue(spawned, "launch did not spawn a harness before smoke failed\n%s" % blob[-2000:])
        self.assertTrue(self.term_pid_path.is_file(), blob[-2000:])
        terminal = int(self.term_pid_path.read_text(encoding="utf-8").strip())
        self.assertNotEqual(terminal, self.foreign.pid)
        self.assertTrue(_wait_dead(terminal), "spawned terminal %s still alive after FAIL" % terminal)
        for pid in spawned:
            self.assertNotEqual(pid, self.foreign.pid)
            self.assertTrue(_wait_dead(pid), "spawned harness %s still alive after FAIL" % pid)
        self._assert_foreign_untouched()
        for name in ("sidecar-grok.pid", "grok-terminal.pid", "headless-session.pid", "headless-spawn.pid"):
            path = self.state / name
            self.assertFalse(path.exists(), "%s still recorded after FAIL" % name)
            self.assertFalse(_pid_in_file(path, self.foreign.pid))
        for path in self.state.iterdir():
            if path.is_file() and path.name.endswith(".pid"):
                self.assertFalse(_pid_in_file(path, self.foreign.pid), path.name)
                for pid in spawned:
                    self.assertFalse(_pid_in_file(path, pid), path.name)


if __name__ == "__main__":
    unittest.main()
