#!/usr/bin/env python3
"""Throwaway-HOME trial of the jcode v0.99.1 release binary.

No curl|bash, no cloud key, no model start. A local stub speaks
OpenAI chat completions. Sessions are created on the debug socket.
"""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BIN = os.environ["JCODE_BIN"]
ROOT = Path(os.environ.get("JCODE_TRIAL_ROOT", "/tmp/jcode-trial/run"))
N = 4
PROMPT = "Answer with the tool result only."


def tree_pids(root_pid: int) -> list[int]:
    ppid_of: dict[int, int] = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            text = (entry / "status").read_text()
        except OSError:
            continue
        ppid = None
        for line in text.splitlines():
            if line.startswith("PPid:"):
                ppid = int(line.split()[1])
                break
        if ppid is not None:
            ppid_of[int(entry.name)] = ppid
    kids: dict[int, list[int]] = {}
    for pid, ppid in ppid_of.items():
        kids.setdefault(ppid, []).append(pid)
    out = []
    stack = [root_pid]
    while stack:
        pid = stack.pop()
        out.append(pid)
        stack.extend(kids.get(pid, []))
    return out


def pss_bytes(pids: list[int]) -> int:
    total = 0
    for pid in pids:
        path = Path(f"/proc/{pid}/smaps_rollup")
        try:
            text = path.read_text()
        except OSError:
            continue
        for line in text.splitlines():
            if line.startswith("Pss:"):
                total += int(line.split()[1]) * 1024
                break
    return total


def mb(n: int) -> float:
    return round(n / (1024 * 1024), 3)


class Stub(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        return

    def _send(self, body: bytes, code: int = 200, content_type: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/").endswith("/models"):
            payload = {"object": "list", "data": [{"id": "stub", "object": "model", "owned_by": "local"}]}
            self._send(json.dumps(payload).encode())
            return
        self._send(b'{"ok":true}')

    def do_POST(self) -> None:  # noqa: N802
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n)
        try:
            req = json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            req = {"_raw": raw[:500].decode("utf-8", "replace")}
        rec = {
            "path": self.path.split("?")[0],
            "stream": bool(req.get("stream")) if isinstance(req, dict) else False,
            "auth_present": bool(self.headers.get("Authorization")),
            "tool_names": [],
        }
        tools = req.get("tools") if isinstance(req, dict) else None
        if isinstance(tools, list):
            for tool in tools[:12]:
                fn = tool.get("function") if isinstance(tool, dict) else None
                if isinstance(fn, dict) and isinstance(fn.get("name"), str):
                    rec["tool_names"].append(fn["name"])
        messages = req.get("messages") if isinstance(req, dict) else None
        roles = []
        tool_output_marker = False
        if isinstance(messages, list):
            for msg in messages:
                if not isinstance(msg, dict):
                    continue
                roles.append(str(msg.get("role")))
                if msg.get("role") == "tool" and "PFY-OK" in json.dumps(msg.get("content")):
                    tool_output_marker = True
        rec["roles"] = roles
        rec["tool_output_marker"] = tool_output_marker
        rec["saw_tool_result"] = "tool" in roles
        self.server.hits.append(rec)  # type: ignore[attr-defined]
        name, args = pick_tool(tools if isinstance(tools, list) else [])
        if rec["saw_tool_result"]:
            message = {"role": "assistant", "content": "PFY-OK-JCODE"}
            finish = "stop"
        else:
            message = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_stub_1",
                        "type": "function",
                        "function": {"name": name, "arguments": args},
                    }
                ],
            }
            finish = "tool_calls"
        if req.get("stream"):
            self._send_stream(message, finish)
            return
        body = {
            "id": "chatcmpl-stub",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": message, "finish_reason": finish}],
        }
        self._send(json.dumps(body).encode())

    def _send_stream(self, message: dict, finish: str) -> None:
        chunks = []
        if message.get("tool_calls"):
            call = message["tool_calls"][0]
            delta = {
                "role": "assistant",
                "tool_calls": [
                    {
                        "index": 0,
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["function"]["name"],
                            "arguments": call["function"]["arguments"],
                        },
                    }
                ],
            }
        else:
            delta = {"role": "assistant", "content": message.get("content") or ""}
        for i, item in enumerate((delta, {})):
            piece = {
                "id": "chatcmpl-stub",
                "object": "chat.completion.chunk",
                "choices": [
                    {
                        "index": 0,
                        "delta": item,
                        "finish_reason": finish if i else None,
                    }
                ],
            }
            chunks.append(b"data: " + json.dumps(piece).encode() + b"\n\n")
        chunks.append(b"data: [DONE]\n\n")
        body = b"".join(chunks)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def pick_tool(tools: list) -> tuple[str, str]:
    chosen = None
    for tool in tools:
        fn = tool.get("function") if isinstance(tool, dict) else None
        if not isinstance(fn, dict):
            continue
        name = fn.get("name")
        if not isinstance(name, str):
            continue
        params = fn.get("parameters") if isinstance(fn.get("parameters"), dict) else {}
        props = params.get("properties") if isinstance(params.get("properties"), dict) else {}
        required = params.get("required") if isinstance(params.get("required"), list) else []
        keys = list(required) or list(props)
        payload: dict[str, str] = {}
        for key in keys:
            if not isinstance(key, str):
                continue
            low = key.lower()
            if any(part in low for part in ("command", "cmd", "input", "script")):
                payload[key] = "printf PFY-OK"
            elif "path" in low or "file" in low:
                payload[key] = "README.md"
            else:
                payload[key] = "PFY-OK"
        if chosen is None or any(part in name.lower() for part in ("bash", "shell", "exec")):
            chosen = (name, json.dumps(payload))
            if any(part in name.lower() for part in ("bash", "shell", "exec")):
                break
    if chosen is None:
        return "bash", json.dumps({"command": "printf PFY-OK"})
    return chosen


def debug_cmd(sock_path: str, cmd: str, session_id: str | None = None, timeout: float = 45) -> dict:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect(sock_path)
    req: dict = {"type": "debug_command", "id": 1, "command": cmd}
    if session_id:
        req["session_id"] = session_id
    sock.sendall((json.dumps(req) + "\n").encode())
    data = b""
    deadline = time.time() + timeout
    lines = []
    while time.time() < deadline:
        try:
            chunk = sock.recv(1 << 20)
        except socket.timeout:
            break
        if not chunk:
            break
        data += chunk
        while b"\n" in data:
            line, data = data.split(b"\n", 1)
            if not line.strip():
                continue
            try:
                resp = json.loads(line)
            except json.JSONDecodeError:
                lines.append(line[:200].decode("utf-8", "replace"))
                continue
            lines.append({"type": resp.get("type"), "ok": resp.get("ok"), "keys": sorted(resp.keys())})
            if resp.get("type") in (None, "debug_response") or "ok" in resp:
                sock.close()
                resp["_lines"] = lines[-4:]
                return resp
    sock.close()
    return {"ok": False, "error": "timeout", "_lines": lines[-4:]}


def wait_socket(path: Path, timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.exists():
            return True
        time.sleep(0.1)
    return False


def home_snap() -> dict:
    home = Path.home()
    out = {}
    for rel in (".jcode", ".config/jcode", ".local/bin/jcode"):
        path = home / rel
        if not path.exists():
            out[rel] = None
            continue
        st = path.stat()
        out[rel] = {"mtime_ns": st.st_mtime_ns, "is_dir": path.is_dir()}
    return out


def outside_fds(pid: int, allowed: list[str]) -> list[str]:
    found = []
    fd_dir = Path(f"/proc/{pid}/fd")
    try:
        fds = list(fd_dir.iterdir())
    except OSError:
        return found
    home = str(Path.home())
    for fd in fds:
        try:
            target = os.readlink(fd)
        except OSError:
            continue
        if target.startswith(("socket:", "pipe:", "anon_inode")):
            continue
        if any(target.startswith(prefix) for prefix in allowed):
            continue
        redacted = target.replace(home, "~") if home and target.startswith(home) else target
        # Drop other absolute home-looking prefixes without embedding the name.
        if redacted.startswith("/home/"):
            parts = redacted.split("/")
            redacted = "operator-home/" + "/".join(parts[3:])
        found.append(redacted)
    return sorted(set(found))[:20]


def nonloop_peers(pid: int) -> list[str]:
    try:
        out = subprocess.run(
            ["ss", "-tpn"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    peers = []
    for line in out.splitlines():
        if f"pid={pid}" not in line:
            continue
        if "127.0.0.1" in line or "[::1]" in line or "127.0.0.1" in line:
            # still record non-loopback only
            pass
        cols = line.split()
        if len(cols) < 5:
            continue
        peer = cols[4]
        if peer.startswith(("127.", "[::1]")):
            continue
        peers.append(peer)
    return peers


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    home = ROOT / "home"
    run = ROOT / "run"
    work = ROOT / "work"
    for path in (home, run, work):
        path.mkdir(exist_ok=True)
    (work / "README.md").write_text("# Fixture\n\nOne line.\n")
    before = home_snap()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Stub)
    httpd.hits = []  # type: ignore[attr-defined]
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}/v1"
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "TMPDIR": str(ROOT / "tmp"),
        "JCODE_HOME": str(home),
        "JCODE_RUNTIME_DIR": str(run),
        "JCODE_NO_TELEMETRY": "1",
        "DO_NOT_TRACK": "1",
        "JCODE_NO_BROWSER": "1",
        "JCODE_DEBUG_CONTROL": "1",
        "JCODE_TEMP_SERVER": "1",
        "JCODE_SERVER_OWNER_PID": str(os.getpid()),
        "JCODE_NON_INTERACTIVE": "1",
    }
    (ROOT / "tmp").mkdir(exist_ok=True)
    log_path = ROOT / "server.log"
    add = subprocess.run(
        [
            BIN,
            "--no-update",
            "--no-selfdev",
            "provider",
            "add",
            "localstub",
            "--base-url",
            base,
            "--model",
            "stub",
            "--no-api-key",
            "--auth",
            "none",
            "--set-default",
            "--json",
            "--overwrite",
        ],
        cwd=str(work),
        env=env,
        capture_output=True,
        text=True,
        timeout=40,
    )
    (ROOT / "provider-add.out").write_text(add.stdout[-2000:] + "\n" + add.stderr[-2000:])
    result: dict = {
        "provider_add_rc": add.returncode,
        "base_is_loopback": True,
        "auth": "none",
        "telemetry_env": "JCODE_NO_TELEMETRY=1",
    }
    server_log = open(log_path, "w")
    server = subprocess.Popen(
        [
            BIN,
            "--no-update",
            "--no-selfdev",
            "--provider-profile",
            "localstub",
            "-m",
            "stub",
            "--tools",
            "bash,read",
            "serve",
            "--socket",
            str(run / "bench.sock"),
            "--debug-socket",
        ],
        cwd=str(work),
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=server_log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    dbg = run / "bench-debug.sock"
    main_sock = run / "bench.sock"
    try:
        ready = wait_socket(dbg, 25) or wait_socket(main_sock, 2)
        result["debug_socket_ready"] = dbg.exists()
        result["main_socket_ready"] = main_sock.exists()
        result["server_alive"] = server.poll() is None
        if not dbg.exists():
            # Some builds put the debug socket beside the runtime dir root.
            candidates = list(run.rglob("*.sock")) + list(home.rglob("*.sock"))
            result["sockets"] = [p.name for p in candidates]
            result["server_log_tail"] = log_path.read_text(errors="replace")[-1500:]
            result["ok"] = False
            print(json.dumps(result, indent=2))
            return 2
        # One session, one turn, then three more.
        created = debug_cmd(str(dbg), f"create_session:{work}")
        result["create_1"] = {k: created.get(k) for k in ("ok", "error")}
        output = created.get("output")
        sid = None
        if isinstance(output, str):
            try:
                sid = json.loads(output).get("session_id")
            except json.JSONDecodeError:
                result["create_output_prefix"] = output[:180]
        elif isinstance(output, dict):
            sid = output.get("session_id")
        result["session_id_present"] = bool(sid)
        ids = [sid] if sid else []
        time.sleep(0.4)
        pids = tree_pids(server.pid)
        result["pss_idle_one_mb"] = mb(pss_bytes(pids))
        turns: list[dict] = []

        def one(session: str) -> None:
            try:
                turned = debug_cmd(str(dbg), f"message:{PROMPT}", session, timeout=50)
            except Exception as exc:  # noqa: BLE001
                turns.append({"ok": False, "error": type(exc).__name__})
                return
            text = turned.get("output")
            turns.append(
                {
                    "ok": bool(turned.get("ok")),
                    "error": turned.get("error"),
                    "output_prefix": (text if isinstance(text, str) else str(text))[:120],
                }
            )

        if sid:
            t0 = time.time()
            one(sid)
            result["first_turn_wall_s"] = round(time.time() - t0, 3)
        time.sleep(0.4)
        pids = tree_pids(server.pid)
        result["pss_after_one_turn_mb"] = mb(pss_bytes(pids))
        for _ in range(N - 1):
            made = debug_cmd(str(dbg), f"create_session:{work}", timeout=30)
            out = made.get("output")
            extra = None
            if isinstance(out, str):
                try:
                    extra = json.loads(out).get("session_id")
                except json.JSONDecodeError:
                    extra = None
            if extra:
                ids.append(extra)
        result["sessions_created"] = len([item for item in ids if item])
        time.sleep(0.4)
        pids = tree_pids(server.pid)
        result["pss_one_turn_plus_idle_mb"] = mb(pss_bytes(pids))
        t1 = time.time()
        threads = [threading.Thread(target=one, args=(session,)) for session in ids[1:]]
        for item in threads:
            item.start()
        for item in threads:
            item.join()
        result["extra_turns_wall_s"] = round(time.time() - t1, 3)
        result["turns"] = turns
        time.sleep(0.4)
        pids = tree_pids(server.pid)
        result["pss_after_n_turns_mb"] = mb(pss_bytes(pids))
        result["proc_count_after"] = len(pids)
        result["n"] = N
        if result["sessions_created"] >= N:
            result["extra_session_pss_mb"] = round(
                (result["pss_after_n_turns_mb"] - result["pss_after_one_turn_mb"]) / (N - 1), 3
            )
            result["extra_idle_session_pss_mb"] = round(
                (result["pss_one_turn_plus_idle_mb"] - result["pss_after_one_turn_mb"]) / (N - 1), 3
            )
        hits = list(httpd.hits)  # type: ignore[attr-defined]
        result["stub_hits"] = len(hits)
        result["stub_paths"] = sorted({h["path"] for h in hits})
        result["auth_header_seen"] = any(h["auth_present"] for h in hits)
        result["tool_names_offered"] = sorted({name for h in hits for name in h["tool_names"]})[:20]
        result["tool_result_seen"] = any(h["saw_tool_result"] for h in hits)
        result["tool_output_marker"] = any(h["tool_output_marker"] for h in hits)
        result["stream_used"] = any(h["stream"] for h in hits)
        result["hit_role_tails"] = [h["roles"][-3:] for h in hits[:8]]
        result["fds_outside"] = outside_fds(server.pid, [
            str(ROOT),
            str(Path(BIN).resolve().parent),
            "/usr",
            "/lib",
            "/lib64",
            "/proc",
            "/dev",
            "/etc",
            "/sys",
            "/tmp",
        ])
        result["nonloop_peers"] = nonloop_peers(server.pid)
        after = home_snap()
        result["real_home_markers_changed"] = before != after
        result["ok"] = bool(sid) and result["provider_add_rc"] == 0
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1
    finally:
        try:
            os.killpg(server.pid, signal.SIGTERM)
        except OSError:
            pass
        try:
            server.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(server.pid, signal.SIGKILL)
            except OSError:
                pass
        httpd.shutdown()
        server_log.close()


if __name__ == "__main__":
    raise SystemExit(main())
