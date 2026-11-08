#!/usr/bin/env python3
"""Offline GraphJin probe. Cache install, a slice of this repo, results.json.

No account, no model, no network. HOME and XDG for the binary stay under
~/.cache/pfy/tools/graphjin/.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import select
import shutil
import socket
import sqlite3
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = Path.home() / ".cache" / "pfy" / "tools" / "graphjin"
BIN = BASE / "bin" / "graphjin"
SLICE_REL = (
    "scripts/catalog_check.py",
    "pfylib/stage_registry.py",
    "examples/x-intake-local/smoke_103_105.py",
    "data/stages/write-guard-mcp.json",
    "data/stages/codebase-memory-mcp.json",
    "sources/entries/104-graphjin.md",
)
CONTENT_REL = "data/stages/write-guard-mcp.json"
BINARY_SHA = "e6f0fd88f99b07e8036ba7db76f24f0fceab697935559d154e823b5951f46805"
TARBALL_SHA = "48c9bebb2b6f6496ac5a749d293f78a40279dcc2e2675dfab4b641c79e417ebc"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def clip(value, limit: int = 500) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    if len(text) <= limit:
        return text
    return text[:limit] + "...(truncated)"


def tool_env() -> dict:
    home = BASE / "home"
    for path in (home, BASE / "config", BASE / "cache", BASE / "tmp", home / "data"):
        path.mkdir(parents=True, exist_ok=True)
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(BASE / "config"),
        "XDG_CACHE_HOME": str(BASE / "cache"),
        "XDG_DATA_HOME": str(home / "data"),
        "TMPDIR": str(BASE / "tmp"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def copy_slice(dest: Path) -> dict:
    if dest.exists():
        shutil.rmtree(dest)
    meta = {}
    for rel in SLICE_REL:
        src = ROOT / rel
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        meta[rel] = target.stat().st_size
    return meta


def fingerprint(root: Path) -> dict:
    out = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            out[rel] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    return out


def seed_db(path: Path) -> None:
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.execute("create table notes(id integer primary key, body text not null)")
    conn.executemany("insert into notes(body) values(?)", [("alpha",), ("beta",)])
    conn.commit()
    conn.close()


def note_rows(path: Path) -> list:
    conn = sqlite3.connect(path)
    rows = conn.execute("select id, body from notes order by id").fetchall()
    conn.close()
    return rows


def write_config(cfg: Path, port: int, db: Path, slice_root: Path, *, read_only: bool, production: bool, with_code: bool, with_db: bool = True) -> None:
    if cfg.exists():
        shutil.rmtree(cfg)
    (cfg / "queries").mkdir(parents=True)
    ro = "true" if read_only else "false"
    prod = "true" if production else "false"
    mode = "prod" if production else "dev"
    code = ""
    code_table = ""
    db_source = ""
    notes_table = ""
    if with_db:
        db_source = f"""
  - name: app
    kind: database
    type: sqlite
    default: true
    path: {db}
    read_only: {ro}
    access:
      read: authenticated
      write: authenticated
      delete: authenticated
      missing_namespace_column: allow
"""
        notes_table = """
  - name: notes
    source: app
"""
    if with_code:
        code = f"""
  - name: repo_code
    kind: code
    path: {slice_root}
    read_only: true
    infer_db_refs: false
    capabilities:
      code.search: true
      code.read: true
      code.write: false
      code.watch: false
"""
        code_table = """
  - name: gj_code
    source: repo_code
    read_only: true
"""
    (cfg / "dev.yml").write_text(
        f"""app_name: pfy graphjin probe
host_port: 127.0.0.1:{port}
web_ui: false
log_level: warn
log_format: simple
mode: {mode}
production: {prod}
secret_key: pfy-probe-not-a-secret
auth:
  type: none
  development: true
sources:
{db_source}
  - name: repo_files
    kind: file
    backend: local
    root: {slice_root}
    read_only: {ro}
    capabilities:
      files.list: true
      files.read: true
      files.write: {"false" if read_only else "true"}
      files.delete: false
{code}
tables:
{notes_table}
  - name: repo_files
    source: repo_files
    read_only: {ro}
{code_table}
agent:
  enabled: false
mcp:
  disable: false
  allow_mutations: true
  allow_raw_queries: true
  allow_config_updates: false
  stdio_user_id: "1"
  stdio_user_role: user
"""
    )
    (cfg / "queries" / "getNotes.graphql").write_text(
        "query getNotes {\n  notes { id body }\n}\n"
    )
    (cfg / "queries" / "repoFiles.graphql").write_text(
        "query repoFiles {\n  repo_files(limit: 20) { key size }\n}\n"
    )


def start_server(cfg: Path, cwd: Path, env: dict) -> tuple[subprocess.Popen, Path]:
    cwd.mkdir(parents=True, exist_ok=True)
    log_path = cwd / "serve.log"
    log = open(log_path, "w")
    proc = subprocess.Popen(
        [str(BIN), "serve", "--path", str(cfg)],
        cwd=cwd,
        stdout=log,
        stderr=subprocess.STDOUT,
        env=env,
    )
    return proc, log_path


def stop_proc(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def wait_listen(proc: subprocess.Popen, port: int, log_path: Path, seconds: float, needles: tuple[str, ...] = ()) -> dict:
    deadline = time.time() + seconds
    while time.time() < deadline and proc.poll() is None:
        if log_path.exists():
            text = log_path.read_text(errors="replace")
            for needle in needles:
                if needle in text:
                    line = next((ANSI.sub("", ln).strip() for ln in text.splitlines() if needle in ln), needle)
                    return {"up": False, "reason": needle, "log_line": clip(line, 400)}
        try:
            OPENER.open(f"http://127.0.0.1:{port}/api/v1/graphql", data=b"{}", timeout=2)
            return {"up": True, "reason": "graphql"}
        except urllib.error.HTTPError:
            return {"up": True, "reason": "graphql-http"}
        except (urllib.error.URLError, OSError, TimeoutError):
            time.sleep(0.2)
    text = log_path.read_text(errors="replace") if log_path.exists() else ""
    return {"up": False, "reason": "timeout", "exit": proc.poll(), "log_tail": clip(text, 700)}


def gql(port: int, query: str) -> dict:
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/v1/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"content-type": "application/json", "X-User-ID": "1", "X-User-Role": "user"},
    )
    try:
        with OPENER.open(req, timeout=30) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read() or b"{}"
        try:
            return json.loads(raw)
        except ValueError:
            return {"errors": [{"message": f"http {exc.code}"}]}
    except (urllib.error.URLError, ValueError, OSError) as exc:
        return {"errors": [{"message": f"transport: {exc}"}]}


def error_text(res: dict) -> str:
    parts = []
    for err in res.get("errors") or []:
        if isinstance(err, dict):
            parts.append(str(err.get("message") or err))
        else:
            parts.append(str(err))
    return " | ".join(parts)


def says_read_only(text: str) -> bool:
    low = text.lower()
    return "read-only" in low or "read_only" in low or "readonly" in low


def list_files(port: int) -> dict:
    res = gql(port, "query { repo_files(limit: 20) { key size } }")
    rows = ((res.get("data") or {}).get("repo_files") or []) if isinstance(res.get("data"), dict) else []
    if not isinstance(rows, list):
        rows = []
    return {
        "error": clip(error_text(res), 300),
        "rows": [{"key": r.get("key"), "size": r.get("size")} for r in rows if isinstance(r, dict)],
    }


def content_match(port: int, slice_root: Path) -> dict:
    res = gql(
        port,
        'query { repo_files(where: { key: { eq: "data/stages/write-guard-mcp.json" } }) { key size text } }',
    )
    rows = ((res.get("data") or {}).get("repo_files") or []) if isinstance(res.get("data"), dict) else []
    disk = (slice_root / CONTENT_REL).read_text(encoding="utf-8")
    text = ""
    if rows and isinstance(rows[0], dict):
        text = rows[0].get("text") or ""
    return {
        "error": clip(error_text(res), 300),
        "rows": len(rows) if isinstance(rows, list) else 0,
        "text_bytes": len(text.encode()),
        "disk_bytes": len(disk.encode()),
        "match": text == disk and bool(text),
    }


def file_insert(port: int) -> dict:
    res = gql(port, 'mutation { repo_files(insert: { key: "evil_probe.txt" }) { key } }')
    return {"error": clip(error_text(res), 300), "body": clip(res, 300), "says_read_only": says_read_only(error_text(res))}


def note_probes(port: int, *, production: bool) -> dict:
    read_q = "query getNotes { notes { id body } }" if production else "query { notes { id body } }"
    read = gql(port, read_q)
    notes = ((read.get("data") or {}).get("notes") or []) if isinstance(read.get("data"), dict) else []
    if not isinstance(notes, list):
        notes = []
    out = {
        "read_rows": [(n.get("id"), n.get("body")) for n in notes if isinstance(n, dict)],
        "read_error": clip(error_text(read), 300),
    }
    if production:
        adhoc = gql(port, "query adhoc { notes { body } }")
        adhoc_notes = ((adhoc.get("data") or {}).get("notes") or []) if isinstance(adhoc.get("data"), dict) else []
        out["adhoc_error"] = clip(error_text(adhoc), 300)
        out["adhoc_rows"] = len(adhoc_notes) if isinstance(adhoc_notes, list) else 0
        out["adhoc_refused"] = bool(adhoc.get("errors")) and out["adhoc_rows"] == 0
    else:
        for name, query in (
            ("insert", 'mutation { notes(insert: {body: "evil"}) { id } }'),
            ("update", 'mutation { notes(where: {id: {eq: 1}}, update: {body: "x"}) { id } }'),
            ("delete", "mutation { notes(where: {id: {eq: 2}}, delete: true) { id } }"),
        ):
            res = gql(port, query)
            text = error_text(res)
            out[name] = {
                "error": clip(text, 300),
                "has_errors": bool(res.get("errors")),
                "says_read_only": says_read_only(text),
            }
    return out


def serve_world(run: Path, env: dict, *, label: str, read_only: bool, production: bool, with_code: bool, with_db: bool = True) -> dict:
    work = run / label
    if work.exists():
        shutil.rmtree(work)
    slice_root = work / "slice"
    sizes = copy_slice(slice_root)
    before = fingerprint(slice_root)
    db = work / "app.db"
    if with_db:
        seed_db(db)
    port = free_port()
    cfg = work / "config"
    write_config(
        cfg, port, db, slice_root,
        read_only=read_only, production=production, with_code=with_code, with_db=with_db,
    )
    t0 = time.perf_counter()
    proc, log_path = start_server(cfg, work / "cwd", env)
    needles = ("cgo-enabled build",) if with_code else ()
    heard = wait_listen(proc, port, log_path, 25, needles)
    startup_s = round(time.perf_counter() - t0, 3)
    result = {"label": label, "startup_s": startup_s, "listen": heard.get("reason"), "up": bool(heard.get("up"))}
    if not heard.get("up"):
        result["log_line"] = heard.get("log_line") or heard.get("log_tail") or ""
        stop_proc(proc)
        return result
    try:
        if with_code:
            code = gql(port, 'query { gj_code(where: { kind: { eq: "symbol" } }, limit: 5) { name path } }')
            result["code_error"] = clip(error_text(code), 400)
            result["code_rows"] = len(((code.get("data") or {}).get("gj_code") or []) if isinstance(code.get("data"), dict) else [])
        files = list_files(port)
        got = {row["key"]: row["size"] for row in files["rows"]}
        result["files_error"] = files["error"]
        result["files_listed"] = len(files["rows"])
        result["files_size_match"] = sum(1 for rel, size in sizes.items() if got.get(rel) == size)
        result["content"] = content_match(port, slice_root)
        result["file_insert"] = file_insert(port)
        if with_db:
            result["notes"] = note_probes(port, production=production)
            result["db_rows"] = note_rows(db)
        if production:
            saved_files = gql(port, "query repoFiles { repo_files(limit: 20) { key size } }")
            rows = ((saved_files.get("data") or {}).get("repo_files") or []) if isinstance(saved_files.get("data"), dict) else []
            result["saved_repo_files"] = {
                "count": len(rows) if isinstance(rows, list) else 0,
                "error": clip(error_text(saved_files), 300),
            }
        result["slice_unchanged"] = fingerprint(slice_root) == before
        result["new_slice_files"] = sorted(set(fingerprint(slice_root)) - set(before))
    finally:
        stop_proc(proc)
    result["cfg"] = str(cfg)
    return result


def read_mcp(proc: subprocess.Popen, timeout: float) -> list:
    buf = b""
    found = []
    deadline = time.time() + timeout
    while time.time() < deadline and proc.poll() is None:
        ready, _, _ = select.select([proc.stdout], [], [], 0.4)
        if not ready:
            if found:
                break
            continue
        chunk = os.read(proc.stdout.fileno(), 65536)
        if not chunk:
            break
        buf += chunk
        while True:
            if buf.startswith(b"Content-Length:"):
                sep = buf.find(b"\r\n\r\n")
                if sep < 0:
                    break
                length = 0
                for line in buf[:sep].decode("ascii", "replace").split("\r\n"):
                    if line.lower().startswith("content-length:"):
                        length = int(line.split(":", 1)[1].strip())
                if len(buf) < sep + 4 + length:
                    break
                body = buf[sep + 4:sep + 4 + length]
                buf = buf[sep + 4 + length:]
                try:
                    found.append(json.loads(body))
                except ValueError:
                    found.append({"_bad": clip(body.decode("utf-8", "replace"), 160)})
                continue
            nl = buf.find(b"\n")
            if nl < 0:
                break
            line = buf[:nl].strip()
            buf = buf[nl + 1:]
            if not line or line.startswith(b"Content-Length:"):
                if line.startswith(b"Content-Length:"):
                    buf = line + b"\r\n" + buf
                continue
            try:
                found.append(json.loads(line))
            except ValueError:
                continue
        if found:
            break
    return found


def send_mcp(proc: subprocess.Popen, obj: dict, framing: str) -> None:
    raw = json.dumps(obj).encode()
    if framing == "content-length":
        proc.stdin.write(f"Content-Length: {len(raw)}\r\n\r\n".encode() + raw)
    else:
        proc.stdin.write(raw + b"\n")
    proc.stdin.flush()


def mcp_once(cfg: Path, env: dict, framing: str) -> dict:
    err_path = cfg.parent / f"mcp-{framing}.err"
    err = open(err_path, "w")
    proc = subprocess.Popen(
        [str(BIN), "mcp", "--path", str(cfg), "--user-id", "1", "--user-role", "user"],
        cwd=cfg.parent,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=err,
        env=env,
        bufsize=0,
    )
    out = {"framing": framing}
    try:
        send_mcp(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "pfy-graphjin-probe", "version": "0"},
            },
        }, framing)
        init_msgs = read_mcp(proc, 10)
        out["initialize_ok"] = any(isinstance(m, dict) and m.get("id") == 1 and "result" in m for m in init_msgs)
        if not out["initialize_ok"]:
            out["initialize"] = clip(init_msgs, 400)
            return out
        send_mcp(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"}, framing)
        send_mcp(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, framing)
        listed = read_mcp(proc, 10)
        names = []
        for msg in listed:
            tools = ((msg.get("result") or {}).get("tools") if isinstance(msg, dict) else None) or []
            if isinstance(tools, list) and tools:
                names = [t.get("name") for t in tools if isinstance(t, dict)]
        out["tools"] = names

        def call(tool: str, arguments: dict, msg_id: int) -> dict:
            send_mcp(proc, {
                "jsonrpc": "2.0",
                "id": msg_id,
                "method": "tools/call",
                "params": {"name": tool, "arguments": arguments},
            }, framing)
            msgs = read_mcp(proc, 15)
            blob = json.dumps(msgs)
            file_count = 0
            for msg in msgs:
                result = msg.get("result") if isinstance(msg, dict) else None
                structured = result.get("structuredContent") if isinstance(result, dict) else None
                rows = ((structured or {}).get("data") or {}).get("repo_files") if isinstance(structured, dict) else None
                if isinstance(rows, list):
                    file_count = len(rows)
            return {
                "tool": tool,
                "says_read_only": says_read_only(blob),
                "file_count": file_count,
                "excerpt": clip(msgs, 400),
            }

        query_tool = next((n for n in names if n and "graphql" in n.lower()), None)
        out["query_tool"] = query_tool
        if query_tool:
            file_call = call(query_tool, {
                "query": "query { repo_files(limit: 20) { key size } }",
            }, 3)
            mutate_call = call(query_tool, {
                "query": 'mutation { notes(insert: {body: "evil"}) { id } }',
            }, 4)
            out["file_count"] = file_call["file_count"]
            out["mutate_says_read_only"] = mutate_call["says_read_only"]
            out["mutate_message"] = "mutations blocked: table app.notes is read-only" if "mutations blocked: table app.notes is read-only" in mutate_call["excerpt"] else clip(mutate_call["excerpt"], 180)
        out["update_tool_present"] = any(n and "update" in n and "config" in n for n in names)
        out["ok"] = True
    finally:
        stop_proc(proc)
        err.close()
        out["stderr_tail"] = clip(err_path.read_text(errors="replace") if err_path.exists() else "", 300)
    return out


def main() -> int:
    if (ROOT / "tmp" / "STOP").exists():
        print("STOP")
        return 0
    t0 = time.perf_counter()
    env = tool_env()
    run = BASE / "probe" / "score"
    if run.exists():
        shutil.rmtree(run)
    run.mkdir(parents=True)
    binary_sha = sha256_file(BIN)
    code = serve_world(run, env, label="code", read_only=True, production=False, with_code=True)
    bare = serve_world(run, env, label="files-no-db", read_only=True, production=False, with_code=False, with_db=False)
    files = serve_world(run, env, label="files-ro", read_only=True, production=False, with_code=False)
    control = serve_world(run, env, label="control", read_only=False, production=False, with_code=False)
    prod = serve_world(run, env, label="prod", read_only=True, production=True, with_code=False)
    mcp = {"status": "SKIPPED", "reason": "read-only file world did not listen"}
    if files.get("up"):
        cfg = Path(files["cfg"])
        line = mcp_once(cfg, env, "line")
        if line.get("ok"):
            mcp = {"status": "ran", "used": "line", "line": line}
        else:
            content = mcp_once(cfg, env, "content-length")
            mcp = {
                "status": "ran" if content.get("ok") else "SKIPPED",
                "used": "content-length" if content.get("ok") else "none",
                "line": line,
                "content_length": content,
            }
    payload = {
        "pin": {
            "version": "v3.21.6",
            "commit": "b8c6bbbafcd95c8ae99bb71eee88508b95a97414",
            "binary_sha256": binary_sha,
            "binary_sha_matches_entry": binary_sha == BINARY_SHA,
            "tarball_sha256": TARBALL_SHA,
            "binary_bytes": BIN.stat().st_size,
        },
        "slice": list(SLICE_REL),
        "code": {k: v for k, v in code.items() if k != "cfg"},
        "files_no_db": {k: v for k, v in bare.items() if k != "cfg"},
        "files_ro": {k: v for k, v in files.items() if k != "cfg"},
        "control": {k: v for k, v in control.items() if k != "cfg"},
        "production": {k: v for k, v in prod.items() if k != "cfg"},
        "mcp": mcp,
        "elapsed_s": round(time.perf_counter() - t0, 3),
    }
    (OUT / "results.json").write_text(json.dumps(payload, indent=2) + "\n")
    summary = {
        "elapsed_s": payload["elapsed_s"],
        "sha_ok": payload["pin"]["binary_sha_matches_entry"],
        "bytes": payload["pin"]["binary_bytes"],
        "code_up": code.get("up"),
        "code_line": code.get("log_line"),
        "bare_files": bare.get("files_listed"),
        "bare_error": bare.get("files_error"),
        "files": files.get("files_listed"),
        "size_match": files.get("files_size_match"),
        "content": (files.get("content") or {}).get("match"),
        "slice_same": files.get("slice_unchanged"),
        "notes": (files.get("notes") or {}).get("read_rows"),
        "db_rows": files.get("db_rows"),
        "ctl_db": control.get("db_rows"),
        "ctl_new": control.get("new_slice_files"),
        "prod_read": (prod.get("notes") or {}).get("read_rows"),
        "prod_adhoc": (prod.get("notes") or {}).get("adhoc_refused"),
        "prod_files": (prod.get("saved_repo_files") or {}).get("count"),
        "mcp": mcp.get("used"),
        "mcp_files": ((mcp.get("line") or {}).get("file_count")),
        "mcp_mutate": ((mcp.get("line") or {}).get("mutate_says_read_only")),
        "mcp_update": ((mcp.get("line") or {}).get("update_tool_present")),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
