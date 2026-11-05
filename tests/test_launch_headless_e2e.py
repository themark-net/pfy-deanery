"""Headless ./pfy launch detaches one harness and never adopts a foreign pid.

Temp HOME and PFY_STATE_DIR only. DISPLAY and WAYLAND_DISPLAY are unset.
The fake engine is the only model endpoint. A grok process started before
launch stands in for someone else's session and must still be alive after
status and stop. Host Ollama on :11434 is not probed.

How this fails and how we recover: a launch that still says "no DISPLAY"
stays red until the headless spawn path runs. A launch that records the
pre-existing grok fails the ownership check. A stop that signals that grok
fails the same-starttime guard. A second spawn that leaves the previous
harness alive fails the replacement check; recover by stopping only the
owned pid after the new session is recorded. A smoke failure after a new
headless spawn must reap that spawn and leave the pre-existing grok alive.
Recover by signalling the recorded pid only when its start time still
matches, or a descendant of that spawn, then clearing the session files
and returning FAIL with the smoke reason and a next step.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PFY = ROOT / "pfy"
MODEL = "tiny-local"
HOST_PORTS = (11434, 11435, 1919, 8080, 9292)
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
HIDDEN = {
    "ollama",
    "ft",
    "freetoken",
    "llama-server",
    "llama-swap",
    "shimmy",
    "grok",
    "opencode",
    "opencode-cli",
    "hermes",
    "hermes-agent",
    "claude",
    "codex",
    "gemini",
    "gemini-cli",
    "tmux",
    "screen",
    *TERMINAL_NAMES,
}


def _proc_start(pid):
    raw = Path("/proc/%d/stat" % int(pid)).read_text(encoding="utf-8", errors="replace")
    end = raw.rfind(")")
    return raw[end + 1 :].split()[19]


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


def _session_leader(pid):
    try:
        return os.getsid(int(pid)) == int(pid)
    except OSError:
        return False


def _environ(pid):
    try:
        raw = Path("/proc/%d/environ" % int(pid)).read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\x00", b"\n").decode("utf-8", "replace")


def _stdout_path(pid):
    try:
        return os.readlink("/proc/%d/fd/1" % int(pid))
    except OSError:
        return ""


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
    return str(int(pid)) in path.read_text(encoding="utf-8", errors="replace").split()


class _Engine(ThreadingHTTPServer):
    allow_reuse_address = True


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
        path = self.path.split("?", 1)[0]
        if path == "/health":
            self._send(200, '{"status":"ok"}')
            return
        if path in ("/v1/models", "/api/tags"):
            body = {"data": [{"id": MODEL}], "models": [{"name": MODEL}]}
            self._send(200, json.dumps(body))
            return
        self._send(404, "{}")

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        if getattr(self.server, "mode", "") == "empty":
            message = {"role": "assistant", "content": ""}
        else:
            message = {"role": "assistant", "content": "PFY_ATTACH_SMOKE_OK"}
        body = {
            "choices": [{
                "finish_reason": "stop",
                "message": message,
            }]
        }
        self._send(200, json.dumps(body))


GROK_SHIM = """#!/bin/sh
if [ -n "${PFY_TEST_PIDS:-}" ]; then
  echo $$ >> "$PFY_TEST_PIDS"
fi
trap 'kill "$child" 2>/dev/null; exit 0' TERM INT
sleep 300 &
child=$!
wait "$child"
"""

MUX_STUB = """#!/bin/sh
printf '%s\\n' "$*" >> "$PFY_TEST_MUX_ARGV"
last=""
for arg in "$@"; do
  last=$arg
done
if [ -f "$last" ]; then
  setsid "$last" </dev/null >>"$PFY_TEST_CHILD_LOG" 2>&1 &
  echo $! > "$PFY_TEST_SPAWN_PID"
fi
exit 0
"""

DAEMON_STUB = """#!/bin/sh
printf '%s\\n' "$0 $*" >> "$PFY_TEST_DAEMON_ARGV"
exit 0
"""

TERMINAL_SHIM = """#!/bin/sh
echo $$ > "$PFY_TEST_TERMINAL_PID"
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
case "$cmd" in
  *" "*) sh -c "$cmd" & ;;
  "") exit 1 ;;
  *) "$cmd" & ;;
esac
wait
"""


class LaunchHeadlessE2E(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pfy-headless-")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.state = self.root / "state"
        self.bindir = self.root / "bin"
        self.realbin = self.root / "real"
        for path in (self.home, self.state, self.bindir, self.realbin):
            path.mkdir()
        self._mirror_system_bins()
        self.pids_path = self.root / "pids"
        self.daemon_log = self.root / "daemon-argv"
        self.block_log = self.root / "curl-blocked"
        self.mux_log = self.root / "mux-argv"
        self.spawn_pid_path = self.root / "spawn.pid"
        self.child_log = self.root / "child.log"
        self.term_pid_path = self.root / "terminal.pid"
        self._write(self.bindir / "grok", GROK_SHIM)
        self._write(self.bindir / "_daemon", DAEMON_STUB)
        for name in ("ollama", "ft", "freetoken"):
            os.symlink(self.bindir / "_daemon", self.bindir / name)
        curl = shutil.which("curl") or "/usr/bin/curl"
        self._write(
            self.bindir / "curl",
            """#!/bin/bash
url=""
for a in "$@"; do
  case "$a" in
    http://*|https://*) url="$a" ;;
  esac
done
case "$url" in
  *127.0.0.1:11434*|*localhost:11434*|*127.0.0.1:11435*|*127.0.0.1:1919*|*127.0.0.1:8080*|*127.0.0.1:9292*)
    printf '%s\\n' "$url" >> "$PFY_TEST_BLOCKED"
    exit 1
    ;;
esac
exec CURLBIN "$@"
""".replace("CURLBIN", curl),
        )
        self.engine = _Engine(("127.0.0.1", 0), _Handler)
        self.engine.daemon_threads = True
        self.port = self.engine.server_address[1]
        self.base = "http://127.0.0.1:%d" % self.port
        threading.Thread(target=self.engine.serve_forever, daemon=True).start()
        self.addCleanup(self._stop_engine)
        self.foreign = subprocess.Popen(
            [str(self.bindir / "grok")],
            cwd=str(self.home),
            env={
                "PATH": self._path(),
                "HOME": str(self.home),
                "PFY_TEST_PIDS": str(self.pids_path),
                "LANG": "C.UTF-8",
            },
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.addCleanup(self._kill_our_processes)
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and not _alive(self.foreign.pid):
            time.sleep(0.02)
        self.assertTrue(_alive(self.foreign.pid), "pre-existing grok did not stay up")

    def _mirror_system_bins(self):
        for base in ("/bin", "/usr/bin"):
            if not os.path.isdir(base):
                continue
            for name in os.listdir(base):
                if name in HIDDEN or (self.realbin / name).exists():
                    continue
                src = os.path.join(base, name)
                if os.path.isfile(src) and os.access(src, os.X_OK):
                    os.symlink(src, self.realbin / name)

    def _write(self, path, text):
        path.write_text(text, encoding="utf-8")
        path.chmod(0o755)
        return path

    def _path(self):
        return "%s:%s" % (self.bindir, self.realbin)

    def _env(self, extra=None):
        env = {
            "PATH": self._path(),
            "HOME": str(self.home),
            "PFY_STATE_DIR": str(self.state),
            "PFY_TEST_OPENAI_BASE": self.base,
            "LOCAL_OPENAI_BASE_URL": self.base,
            "PFY_TEST_PIDS": str(self.pids_path),
            "PFY_TEST_DAEMON_ARGV": str(self.daemon_log),
            "PFY_TEST_BLOCKED": str(self.block_log),
            "PFY_TEST_MUX_ARGV": str(self.mux_log),
            "PFY_TEST_SPAWN_PID": str(self.spawn_pid_path),
            "PFY_TEST_CHILD_LOG": str(self.child_log),
            "PFY_TEST_TERMINAL_PID": str(self.term_pid_path),
            "GROK_HOME": str(self.home / ".grok"),
            "XDG_CONFIG_HOME": str(self.home / ".config"),
            "TMPDIR": os.environ.get("TMPDIR") or str(ROOT / "tmp"),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        env.pop("DISPLAY", None)
        env.pop("WAYLAND_DISPLAY", None)
        if extra:
            env.update(extra)
        return env

    def _install_mux(self, name):
        stub = self._write(self.bindir / "_mux", MUX_STUB)
        link = self.bindir / name
        if link.exists() or link.is_symlink():
            link.unlink()
        os.symlink(stub, link)

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

    def _assert_no_daemon(self):
        text = self.daemon_log.read_text(encoding="utf-8") if self.daemon_log.is_file() else ""
        self.assertNotIn("serve", text, text)
        if self.block_log.is_file():
            blocked = self.block_log.read_text(encoding="utf-8")
            for port in HOST_PORTS:
                self.assertNotIn(":%d" % port, blocked, blocked)

    def _assert_foreign_not_recorded(self):
        self.assertTrue(_alive(self.foreign.pid), "pre-existing grok was signalled")
        for path in self.state.iterdir():
            if not path.is_file():
                continue
            if path.name.endswith(".pid") or path.suffix == ".pid":
                self.assertFalse(
                    _pid_in_file(path, self.foreign.pid),
                    "foreign pid recorded in %s" % path.name,
                )

    def _assert_owns_spawn(self, pid, spawned=0):
        self.assertGreater(int(pid), 1)
        self.assertNotEqual(int(pid), self.foreign.pid)
        self.assertTrue(_alive(pid), "recorded harness is not alive")
        self.assertEqual(_proc_start(pid), (self.state / "headless-session.start").read_text(encoding="utf-8").strip())
        self.assertGreater(int(_proc_start(pid)), int(_proc_start(self.foreign.pid)))
        self.assertIn(str(self.port), _environ(pid), "harness was not pointed at the live engine")
        owned = _session_leader(pid) or (spawned and _descends_from(pid, spawned))
        self.assertTrue(owned, "pid %s is not the setsid child of this launch" % pid)
        if spawned:
            self.assertEqual(int(pid), int(spawned))

    def _launch_ok(self, args, env):
        proc = self._run(args, env, 45)
        blob = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, blob[-2500:])
        self.assertNotIn("no DISPLAY", blob)
        body = _json_object(proc.stdout)
        self.assertTrue(body.get("ok"), blob[-2500:])
        self.assertEqual(body.get("live"), "READY", blob[-2500:])
        self._assert_no_daemon()
        return body, blob

    def test_headless_flag_prefers_tmux_and_stop_spares_the_foreign_grok(self):
        self._install_mux("tmux")
        self._install_mux("screen")
        env = self._env()
        body, blob = self._launch_ok(["launch", "--headless"], env)
        pid = int(body.get("pid") or 0)
        name = (self.state / "headless-session.name").read_text(encoding="utf-8").strip()
        harness = (self.state / "headless-session.harness").read_text(encoding="utf-8").strip()
        recorded = int((self.state / "headless-session.pid").read_text(encoding="utf-8").strip())
        self.assertEqual(recorded, pid, blob[-1500:])
        self.assertEqual(harness, "grok")
        self.assertTrue(name.startswith("pfy-grok-") and len(name) > len("pfy-grok-"), name)
        self.assertEqual(body.get("session"), name)
        self.assertTrue(body.get("headless"), blob[-1500:])
        spawned = int(self.spawn_pid_path.read_text(encoding="utf-8").strip())
        self._assert_owns_spawn(pid, spawned)
        mux = self.mux_log.read_text(encoding="utf-8")
        self.assertIn("new-session", mux)
        self.assertIn("-d", mux)
        self.assertIn("-s", mux)
        self.assertIn(name, mux)
        self.assertNotIn("-dmS", mux)
        self._assert_foreign_not_recorded()

        status = self._run(["launch", "status"], env, 20)
        status_blob = (status.stdout or "") + (status.stderr or "")
        self.assertEqual(status.returncode, 0, status_blob[-1500:])
        status_body = _json_object(status.stdout)
        self.assertTrue(status_body.get("ok"), status_blob[-1500:])
        self.assertEqual(status_body.get("live"), "READY")
        self.assertEqual(status_body.get("session"), name)
        self.assertEqual(int(status_body.get("pid") or 0), pid)
        self.assertEqual(status_body.get("harness"), "grok")

        stopped = self._run(["launch", "stop"], env, 20)
        stop_blob = (stopped.stdout or "") + (stopped.stderr or "")
        self.assertEqual(stopped.returncode, 0, stop_blob[-1500:])
        stop_body = _json_object(stopped.stdout)
        self.assertTrue(stop_body.get("ok"), stop_blob[-1500:])
        self.assertIn(str(stop_body.get("live") or ""), ("STOPPED", "FAIL"))
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and _alive(pid):
            time.sleep(0.05)
        self.assertFalse(_alive(pid), "stop left the recorded harness alive")
        self.assertTrue(_alive(self.foreign.pid), "stop signalled the pre-existing grok")
        self.assertFalse((self.state / "headless-session.pid").exists(), stop_blob[-1500:])

        after = self._run(["launch", "status"], env, 20)
        after_blob = (after.stdout or "") + (after.stderr or "")
        self.assertNotEqual(after.returncode, 0, after_blob[-1500:])
        after_body = _json_object(after.stdout)
        self.assertFalse(after_body.get("ok"), after_blob[-1500:])
        self.assertFalse(after_body.get("session"), after_blob[-1500:])
        self.assertTrue(_alive(self.foreign.pid))

    def test_screen_is_used_when_tmux_is_absent(self):
        self._install_mux("screen")
        env = self._env()
        body, _blob = self._launch_ok(["launch", "--headless"], env)
        pid = int(body.get("pid") or 0)
        name = (self.state / "headless-session.name").read_text(encoding="utf-8").strip()
        spawned = int(self.spawn_pid_path.read_text(encoding="utf-8").strip())
        self._assert_owns_spawn(pid, spawned)
        mux = self.mux_log.read_text(encoding="utf-8")
        self.assertIn("-dmS", mux)
        self.assertIn(name, mux)
        self.assertNotIn("new-session", mux)
        self._assert_foreign_not_recorded()
        self._run(["launch", "stop"], env, 20)
        self.assertTrue(_alive(self.foreign.pid))

    def test_bare_launch_without_display_setsid_falls_back(self):
        env = self._env()
        body, _blob = self._launch_ok(["launch"], env)
        pid = int(body.get("pid") or 0)
        self.assertEqual(body.get("session"), (self.state / "headless-session.name").read_text(encoding="utf-8").strip())
        self.assertTrue(str(body.get("session") or "").startswith("pfy-grok-"))
        self._assert_owns_spawn(pid)
        self.assertTrue(_session_leader(pid))
        self.assertIn(str(self.state), _stdout_path(pid))
        self.assertFalse(self.mux_log.exists())
        self._assert_foreign_not_recorded()
        status = self._run(["launch", "status"], env, 20)
        self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
        self.assertEqual(int(_json_object(status.stdout).get("pid") or 0), pid)
        self._run(["launch", "stop"], env, 20)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and _alive(pid):
            time.sleep(0.05)
        self.assertFalse(_alive(pid))
        self.assertTrue(_alive(self.foreign.pid))

    def test_display_keeps_the_gui_terminal(self):
        self._install_mux("tmux")
        shim = self._write(self.bindir / "_terminal", TERMINAL_SHIM)
        for name in TERMINAL_NAMES:
            os.symlink(shim, self.bindir / name)
        env = self._env({"DISPLAY": ":99"})
        body, blob = self._launch_ok(["launch"], env)
        self.assertFalse(body.get("headless"), blob[-1500:])
        self.assertFalse((self.state / "headless-session.name").exists(), blob[-1500:])
        self.assertFalse(self.mux_log.exists())
        self.assertTrue(self.term_pid_path.is_file(), blob[-1500:])
        terminal = int(self.term_pid_path.read_text(encoding="utf-8").strip())
        reported = int(body.get("pid") or 0)
        self.assertTrue(_descends_from(reported, terminal) or reported == terminal, blob[-1500:])
        self.assertNotEqual(reported, self.foreign.pid)
        self._assert_foreign_not_recorded()

    def test_headless_flag_wins_when_display_is_set(self):
        self._install_mux("tmux")
        shim = self._write(self.bindir / "_terminal", TERMINAL_SHIM)
        for name in TERMINAL_NAMES:
            os.symlink(shim, self.bindir / name)
        env = self._env({"DISPLAY": ":99"})
        body, _blob = self._launch_ok(["launch", "--headless"], env)
        pid = int(body.get("pid") or 0)
        self.assertTrue(body.get("headless"))
        self.assertTrue((self.state / "headless-session.name").is_file())
        self.assertFalse(self.term_pid_path.exists())
        self.assertIn("new-session", self.mux_log.read_text(encoding="utf-8"))
        spawned = int(self.spawn_pid_path.read_text(encoding="utf-8").strip())
        self._assert_owns_spawn(pid, spawned)
        self._assert_foreign_not_recorded()
        self._run(["launch", "stop"], env, 20)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and _alive(pid):
            time.sleep(0.05)
        self.assertFalse(_alive(pid))
        self.assertTrue(_alive(self.foreign.pid))

    def test_stop_clears_a_mismatched_starttime_without_signalling(self):
        (self.state / "headless-session.pid").write_text("%d\n" % self.foreign.pid, encoding="utf-8")
        (self.state / "headless-session.start").write_text("1\n", encoding="utf-8")
        (self.state / "headless-session.name").write_text("pfy-grok-foreign\n", encoding="utf-8")
        (self.state / "headless-session.harness").write_text("grok\n", encoding="utf-8")
        env = self._env()
        stopped = self._run(["launch", "stop"], env, 20)
        self.assertTrue(_alive(self.foreign.pid), (stopped.stdout or "") + (stopped.stderr or ""))
        self.assertFalse((self.state / "headless-session.pid").exists())
        self.assertFalse((self.state / "headless-session.name").exists())
        status = self._run(["launch", "status"], env, 20)
        self.assertNotEqual(status.returncode, 0, status.stdout + status.stderr)
        body = _json_object(status.stdout)
        self.assertFalse(body.get("ok"))
        self.assertFalse(body.get("session"))
        self.assertTrue(_alive(self.foreign.pid))

    def test_second_launch_reuses_the_live_headless_session(self):
        self._install_mux("tmux")
        env = self._env()
        first, _blob = self._launch_ok(["launch", "--headless"], env)
        pid = int(first.get("pid") or 0)
        name = (self.state / "headless-session.name").read_text(encoding="utf-8").strip()
        again, blob = self._launch_ok(["launch", "--headless"], env)
        self.assertEqual(int(again.get("pid") or 0), pid, blob[-1500:])
        self.assertEqual(again.get("session"), name)
        self.assertTrue(_alive(pid))
        started = [
            line for line in self.mux_log.read_text(encoding="utf-8").splitlines()
            if "new-session" in line
        ]
        self.assertEqual(len(started), 1, self.mux_log.read_text(encoding="utf-8"))
        self._assert_foreign_not_recorded()

    def test_replacement_spawn_stops_only_the_previous_owned_session(self):
        self._install_mux("tmux")
        env = self._env()
        first, _blob = self._launch_ok(["launch", "--headless"], env)
        pid1 = int(first.get("pid") or 0)
        name1 = (self.state / "headless-session.name").read_text(encoding="utf-8").strip()
        claims = [path for path in self.state.glob("*-terminal.pid") if path.is_file()]
        self.assertTrue(claims, "launch recorded no terminal pid")
        for path in list(self.state.glob("*-terminal.pid")) + list(self.state.glob("*-terminal.start")):
            path.unlink()
        second, blob = self._launch_ok(["launch", "--headless"], env)
        pid2 = int(second.get("pid") or 0)
        name2 = (self.state / "headless-session.name").read_text(encoding="utf-8").strip()
        self.assertNotEqual(pid2, pid1, blob[-1500:])
        self.assertNotEqual(name2, name1)
        self.assertTrue(name2.startswith("pfy-grok-"))
        spawned = int(self.spawn_pid_path.read_text(encoding="utf-8").strip())
        self._assert_owns_spawn(pid2, spawned)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and _alive(pid1):
            time.sleep(0.05)
        self.assertFalse(_alive(pid1), "previous owned harness kept running after replacement")
        self.assertTrue(_alive(pid2))
        self.assertTrue(_alive(self.foreign.pid), "replacement signalled the pre-existing grok")
        self._assert_foreign_not_recorded()
        status = self._run(["launch", "status"], env, 20)
        status_body = _json_object(status.stdout)
        self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
        self.assertEqual(status_body.get("session"), name2)
        self.assertEqual(int(status_body.get("pid") or 0), pid2)
        self._run(["launch", "stop"], env, 20)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and _alive(pid2):
            time.sleep(0.05)
        self.assertFalse(_alive(pid2))
        self.assertTrue(_alive(self.foreign.pid))

    def _assert_failed_smoke_reaped_our_spawn(self):
        """FAIL names the smoke reason, the new harness is gone, the pretender lives."""
        before = set(_pid_list(self.pids_path))
        self.engine.mode = "empty"
        env = self._env()
        proc = self._run(["launch"], env, 45)
        blob = (proc.stdout or "") + (proc.stderr or "")
        body = _json_object(proc.stdout)
        self.assertNotEqual(proc.returncode, 0, blob[-2500:])
        self.assertFalse(body.get("ok"), blob[-2500:])
        self.assertEqual(body.get("live"), "FAIL")
        self.assertEqual(body.get("error"), "smoke empty completion", blob[-2500:])
        self.assertIn("./pfy up", body.get("next_step") or "", blob[-2500:])
        self._assert_no_daemon()
        spawned = [pid for pid in _pid_list(self.pids_path) if pid not in before and pid != self.foreign.pid]
        self.assertTrue(spawned, "launch did not spawn a harness before smoke failed\n%s" % blob[-2500:])
        for pid in spawned:
            self.assertTrue(_wait_dead(pid), "spawned harness %s still alive after FAIL" % pid)
        self._assert_foreign_not_recorded()
        for name in ("headless-session.pid", "headless-session.name", "headless-spawn.pid", "sidecar-grok.pid", "grok-terminal.pid"):
            self.assertFalse((self.state / name).exists(), "%s still recorded after FAIL" % name)
        for path in list(self.state.iterdir()):
            if path.is_file() and path.name.endswith(".pid"):
                self.assertFalse(_pid_in_file(path, self.foreign.pid), path.name)
                for pid in spawned:
                    self.assertFalse(_pid_in_file(path, pid), path.name)

    def test_smoke_failure_after_spawn_reaps_only_our_session(self):
        """Smoke FAIL after a setsid spawn reaps that pid and spares a pretender.

        The pretender is a grok started before launch. It must still be alive
        and absent from pid files. The harness this launch started must be
        gone, the headless record cleared, and the FAIL must name the smoke
        reason and a next step.
        """
        self._assert_failed_smoke_reaped_our_spawn()

    def test_smoke_failure_after_tmux_spawn_reaps_the_recorded_session(self):
        """Smoke FAIL after tmux detaches still reaps the recorded pid only.

        The mux stub reparents the harness, so a parent walk from this process
        does not find it. Ownership is the headless pid and start time.
        """
        self._install_mux("tmux")
        self._install_mux("screen")
        self._assert_failed_smoke_reaped_our_spawn()


if __name__ == "__main__":
    unittest.main()
