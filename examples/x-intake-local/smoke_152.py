#!/usr/bin/env python3
"""Operate-or-FAIL smoke for X intake Entry 152 (Kanzo, local kanban board + MCP server). Stdlib only, self-contained.

Usage: python3 examples/x-intake-local/smoke_152.py

Exit 0 = PASS, 1 = the tool ran but a check failed, 2 = can't run here (prereq missing; reason recorded).
Receipt: $PFY_SMOKE_RECEIPT_DIR/latest.json, else pipelines/smoke/kanzo/latest.json. Never installs or downloads
anything, never starts the web board, never runs `sync`, `update` or `service`.

Binary: $KANZO_BIN, else ~/DEVELOP/pfy-mentat/tmp/kanzo/bin/kanzo, else `kanzo` on PATH. `--version` must print
`kanzo $KANZO_VERSION` (default 0.2.1) or the smoke exits 2.
Flow (temp data folder via --home, temp HOME, clean env without KANZO_HOME, timeout $PFY_XINTAKE_TIMEOUT default
60 s, bwrap --unshare-net when it works): `init --home`, then `mcp --home` over stdio driven one request at a time
(initialize, tools/list, create_project, create_task, list_tasks; replies matched by id because Kanzo answers
concurrently), then `export -f json` and `export` (Markdown). Checks: each step exits 0, the agent tool list has the
core task tools, the created task shows up in list_tasks and in both exports with status todo, nothing is written to
the temp HOME (all data stays under --home), and the real ~/kanzo is unchanged.
"""
from __future__ import annotations

import json
import os
import select
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIN = os.environ.get("KANZO_VERSION", "0.2.1")
SYS_PATH = "/usr/local/bin:/usr/bin:/bin"
WATCHED = ["kanzo", ".config/kanzo", ".local/share/kanzo"]
CORE_TOOLS = {"create_project", "create_task", "list_tasks", "next_task", "update_task", "add_comment"}
TITLE = "pfy smoke task"


def receipt_dir() -> Path:
    env = os.environ.get("PFY_SMOKE_RECEIPT_DIR")
    return Path(env) if env else ROOT / "pipelines/smoke/kanzo"


def finish(code: int, rec: dict) -> int:
    rec["status"] = {0: "PASS", 1: "FAIL", 2: "SKIP"}[code]
    rec["exit"] = code
    rec["at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    d = receipt_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / "latest.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": rec["status"], "reason": rec.get("reason"), "failed": rec.get("failed", [])}))
    return code


def find_bin() -> str | None:
    env = os.environ.get("KANZO_BIN")
    if env:
        return env if os.access(env, os.X_OK) else None
    local = Path.home() / "DEVELOP/pfy-mentat/tmp/kanzo/bin/kanzo"
    if os.access(local, os.X_OK):
        return str(local)
    return shutil.which("kanzo")


def bwrap_ok() -> bool:
    if not shutil.which("bwrap"):
        return False
    p = subprocess.run(["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--unshare-net", "true"],
                       capture_output=True)
    return p.returncode == 0


def home_sig(home: Path) -> dict:
    sig = {}
    for rel in WATCHED:
        p = home / rel
        if p.is_dir():
            sig[rel] = sorted((str(q.relative_to(p)), q.stat().st_size, q.stat().st_mtime_ns) for q in p.rglob("*"))
        elif p.exists():
            sig[rel] = [p.stat().st_size, p.stat().st_mtime_ns]
        else:
            sig[rel] = None
    return sig


def wrap(cmd: list[str], tmp: Path, sandbox: bool) -> list[str]:
    if not sandbox:
        return cmd
    return ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--bind", str(tmp), str(tmp),
            "--unshare-net", "--die-with-parent", *cmd]


def child_env(tmp: Path) -> dict:
    return {"PATH": SYS_PATH, "HOME": str(tmp / "home"), "TMPDIR": str(tmp / "t"), "LANG": "C.UTF-8",
            "NO_COLOR": "1", "TERM": "dumb"}


def run(binary: str, args: list[str], tmp: Path, sandbox: bool, timeout: float) -> subprocess.CompletedProcess:
    return subprocess.run(wrap([binary, *args], tmp, sandbox), env=child_env(tmp), capture_output=True, text=True,
                          timeout=timeout, start_new_session=True, stdin=subprocess.DEVNULL, cwd=str(tmp))


class Mcp:
    """Minimal stdio JSON-RPC client: one request at a time, replies matched by id."""

    def __init__(self, cmd: list[str], env: dict, cwd: str, timeout: float):
        self.p = subprocess.Popen(cmd, env=env, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, start_new_session=True)
        self.deadline = time.monotonic() + timeout
        self.buf = b""
        self.next_id = 1

    def send(self, msg: dict) -> None:
        self.p.stdin.write((json.dumps(msg) + "\n").encode())
        self.p.stdin.flush()

    def call(self, method: str, params: dict | None = None) -> dict:
        rid = self.next_id
        self.next_id += 1
        self.send({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}})
        while True:
            while b"\n" in self.buf:
                line, self.buf = self.buf.split(b"\n", 1)
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if isinstance(msg, dict) and msg.get("id") == rid:
                    return msg
            left = self.deadline - time.monotonic()
            if left <= 0:
                raise TimeoutError(f"no reply to {method}")
            r, _, _ = select.select([self.p.stdout], [], [], left)
            if not r:
                raise TimeoutError(f"no reply to {method}")
            chunk = os.read(self.p.stdout.fileno(), 65536)
            if not chunk:
                raise EOFError(f"server closed before replying to {method}")
            self.buf += chunk

    def close(self) -> int | None:
        try:
            self.p.stdin.close()
            return self.p.wait(timeout=max(1.0, min(10.0, self.deadline - time.monotonic())))
        except (OSError, subprocess.TimeoutExpired):
            self.p.kill()
            self.p.wait()
            return None


def tool_text(reply: dict) -> tuple[bool, str]:
    res = reply.get("result") or {}
    text = " ".join(c.get("text", "") for c in res.get("content", []) if isinstance(c, dict))
    return ("error" not in reply and not res.get("isError")), text


def body(rec: dict, binary: str, tmp: Path, sandbox: bool, timeout: float) -> int:
    outs: dict = {}

    def check(name: str, ok: bool) -> None:
        rec["checks"][name] = bool(ok)
        if not ok:
            rec["failed"].append(name)

    (tmp / "t").mkdir()
    (tmp / "home").mkdir()
    data = str(tmp / "data")
    try:
        v = run(binary, ["--version"], tmp, sandbox, timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        rec["reason"] = f"--version failed: {e}"
        return 2
    rec["version_output"] = (v.stdout + v.stderr).strip()[:200]
    if rec["version_output"].split()[-1:] != [PIN]:
        rec["reason"] = f"version pin {PIN} not in --version output"
        return 2
    try:
        p = run(binary, ["init", "--home", data], tmp, sandbox, timeout)
        outs["init"] = p.stdout + p.stderr
        check("init_ok", p.returncode == 0)
        check("init_made_db", (tmp / "data" / "kanzo.db").is_file())
        if rec["failed"]:
            return 1
        mcp = Mcp(wrap([binary, "mcp", "--home", data], tmp, sandbox), child_env(tmp), str(tmp), timeout)
        try:
            init = mcp.call("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                           "clientInfo": {"name": "pfy-smoke-152", "version": "0"}})
            rec["server_info"] = (init.get("result") or {}).get("serverInfo")
            mcp.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            tools = mcp.call("tools/list")
            names = {t.get("name") for t in (tools.get("result") or {}).get("tools", [])}
            rec["missing_tools"] = sorted(CORE_TOOLS - names)
            ok_p, outs["create_project"] = tool_text(mcp.call("tools/call", {
                "name": "create_project", "arguments": {"slug": "smoke", "name": "Smoke"}}))
            ok_t, outs["create_task"] = tool_text(mcp.call("tools/call", {
                "name": "create_task", "arguments": {"title": TITLE, "project": "smoke"}}))
            ok_l, outs["list_tasks"] = tool_text(mcp.call("tools/call", {
                "name": "list_tasks", "arguments": {"project": "smoke"}}))
        except (TimeoutError, EOFError, OSError) as e:
            mcp.close()
            rec["failed"].append(f"mcp: {e}")
            return 1
        rec["checks"]["mcp_exit"] = mcp.close()
        check("mcp_clean_exit_on_eof", rec["checks"]["mcp_exit"] == 0)
        check("mcp_core_tools", not rec["missing_tools"])
        check("mcp_create_project_ok", ok_p)
        check("mcp_create_task_ok", ok_t and "smoke#1" in outs["create_task"])
        check("mcp_list_shows_task", ok_l and TITLE in outs["list_tasks"])
        j = run(binary, ["export", "-f", "json", "--home", data], tmp, sandbox, timeout)
        m = run(binary, ["export", "--home", data], tmp, sandbox, timeout)
    except subprocess.TimeoutExpired as e:
        rec["failed"].append(f"timed out: {e.cmd[-3:] if e.cmd else ''}")
        return 1
    outs["export_md"] = m.stdout
    check("export_json_ok", j.returncode == 0)
    check("export_md_ok", m.returncode == 0)
    try:
        board = json.loads(j.stdout)
        tasks = [t for pr in board.get("projects", []) if pr.get("slug") == "smoke" for t in pr.get("tasks", [])]
    except (ValueError, AttributeError, TypeError):
        tasks = []
    check("export_json_has_task", any(t.get("title") == TITLE and t.get("status") == "todo" for t in tasks))
    check("export_md_has_task", TITLE in m.stdout)
    leaked = sorted(str(q.relative_to(tmp / "home")) for q in (tmp / "home").rglob("*"))
    rec["temp_home_writes"] = leaked[:20]
    check("data_only_under_home_flag", not leaked)
    if rec["failed"]:
        rec["tail"] = {k: v[-400:] for k, v in outs.items()}
    return 1 if rec["failed"] else 0


def main() -> int:
    rec: dict = {"entry": "152-kanzo", "pin": PIN, "failed": [], "checks": {}}
    try:
        timeout = float(os.environ.get("PFY_XINTAKE_TIMEOUT", "60"))
        if timeout <= 0:
            raise ValueError
    except ValueError:
        rec["reason"] = "bad PFY_XINTAKE_TIMEOUT"
        return finish(2, rec)
    binary = find_bin()
    if not binary:
        rec["reason"] = "kanzo not staged (set KANZO_BIN or stage tmp/kanzo/bin/kanzo)"
        return finish(2, rec)
    rec["binary"] = binary
    sandbox = bwrap_ok()
    rec["sandbox"] = "bwrap --unshare-net" if sandbox else "none (network reachable)"
    real_home = Path.home()
    before = home_sig(real_home)
    code = 1
    try:
        with tempfile.TemporaryDirectory(prefix="pfy-smoke-152-") as td:
            code = body(rec, binary, Path(td), sandbox, timeout)
    except Exception as e:  # any crash is a FAIL with a receipt, never a traceback without one
        rec["failed"].append(f"exception: {e!r}")
        code = 1
    finally:
        # Real-HOME check runs on every path (PASS, FAIL, SKIP, timeout, exception).
        after = home_sig(real_home)
        rec["real_home_changed"] = [k for k in WATCHED if before[k] != after[k]]
        rec["checks"]["real_home_unchanged"] = not rec["real_home_changed"]
    if rec["real_home_changed"]:
        rec["failed"].append("real_home_unchanged")
        code = 1
    return finish(code, rec)


if __name__ == "__main__":
    sys.exit(main())
