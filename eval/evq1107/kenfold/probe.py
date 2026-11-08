#!/usr/bin/env python3
"""Kenfold probe for gap H1 (repeatable score, memory, context).

Stdio MCP, no API key. Postgres is rootless podman with the pinned
pgvector image. HOME and the podman store stay under
~/.cache/pfy/tools/kenfold/. No embeddings, no chat model, no OAuth.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pwd
import queue
import re
import subprocess
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "results.json"
PIN = "dfc18f9f1a7be98c5af8c0e7e1cbf566c37d51af"
PIN_TAG = "v0.1.1"
IMAGE = "docker.io/pgvector/pgvector:0.8.6-pg18-trixie"
DB_URL = "postgres://kenfold@127.0.0.1:54329/kenfold?sslmode=disable"
CONTAINER = "pfy-evq-kenfold-pg"
PROJECT = "https://github.com/themark-net/pfy-mentat"
WRITER = "grok-build"
READER = "opencode"

REPO_NEEDLES = (
    "dfc18f9f1a7be98c5af8c0e7e1cbf566c37d51af",
    "pgvector/pgvector:0.8.6-pg18-trixie",
    "smoke-codebase-memory",
    "prefer-behavior-and-fail-recover-tests",
    "best-effort-and-bot-budget-build-max",
    "KENFOLD_UPDATE_CHECK",
    "self_pipeline",
    "codebase-memory-mcp",
)
NOVEL = tuple("KF1107_NOVEL_%02d" % i for i in range(1, 9))

OVERLAP_WORDS = ("memory", "context", "rag", "handoff", "vector", "postgres")
H1_NAMES = ("skill-up", "harness2", "Harness Score", "eval-harness (pfy)", "neatroots")


def shaped_secret() -> str:
    """Fixture that matches the aws-access-key rule. Not a real credential."""
    return "note " + ("AK" + "IA") + ("B" * 16) + " end"


def cache_base() -> Path:
    return Path(pwd.getpwuid(os.getuid()).pw_dir) / ".cache" / "pfy" / "tools" / "kenfold"


def real_home() -> Path:
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000.0, 1)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dir_bytes(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [name for name in dirnames if name != "proc"]
        for name in filenames:
            file_path = Path(dirpath) / name
            try:
                total += file_path.lstat().st_size
            except OSError:
                continue
    return total


def home_fingerprint(root: Path) -> list[dict]:
    if not root.exists():
        return []
    rows = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(dirnames + filenames):
            path = Path(dirpath) / name
            try:
                stat = path.lstat()
            except OSError:
                continue
            rows.append({"rel": str(path.relative_to(root)), "mtime_ns": stat.st_mtime_ns, "size": stat.st_size})
    return rows


def run_cmd(cmd: list[str], env: dict, cwd: Path | None = None, timeout: float = 60) -> dict:
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "exit": 124,
            "ms": ms(start),
            "stdout": (exc.stdout or "") if isinstance(exc.stdout, str) else "",
            "stderr": "timeout",
        }
    return {
        "exit": proc.returncode,
        "ms": ms(start),
        "stdout": proc.stdout or "",
        "stderr": proc.stderr or "",
    }


def child_env(home: Path, tmp: Path, password: str, agent: str = "") -> dict:
    env = os.environ.copy()
    for key in list(env):
        upper = key.upper()
        if upper.endswith("_API_KEY") or upper.endswith("_TOKEN") or upper.endswith("_SECRET"):
            env.pop(key, None)
    env["HOME"] = str(home)
    env["XDG_CONFIG_HOME"] = str(home / "xdg-config")
    env["XDG_CACHE_HOME"] = str(home / "xdg-cache")
    env["XDG_DATA_HOME"] = str(home / "xdg-data")
    env["TMPDIR"] = str(tmp)
    env["KENFOLD_UPDATE_CHECK"] = "false"
    env["KENFOLD_DATABASE_URL"] = DB_URL
    env["KENFOLD_DATABASE_PASSWORD"] = password
    env["KENFOLD_STUB_STORE"] = str(tmp / "stub-mem.json")
    env["KENFOLD_AGENT"] = agent
    if "XDG_RUNTIME_DIR" not in env:
        runtime = Path("/run/user") / str(os.getuid())
        if runtime.is_dir():
            env["XDG_RUNTIME_DIR"] = str(runtime)
    return env


def repo_hit(needle: str, rg: str) -> bool:
    cmd = [
        rg,
        "-F",
        "-l",
        "--glob",
        "!.git/**",
        "--glob",
        "!eval/evq1107/kenfold/**",
        "--glob",
        "!data/stages/kenfold.json",
        needle,
    ]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    return proc.returncode == 0 and bool((proc.stdout or "").strip())


def rg_scan(rg: str) -> dict:
    start = time.perf_counter()
    novel = sum(1 for needle in NOVEL if repo_hit(needle, rg))
    known = sum(1 for needle in REPO_NEEDLES if repo_hit(needle, rg))
    return {"rg_novel_hits": novel, "rg_repo_hits": known, "rg_ms": ms(start)}


def overlap_cards() -> list[dict]:
    rows = []
    stages = ROOT / "data" / "stages"
    for path in sorted(stages.glob("*.json")):
        if path.name in ("_registry.json", "kenfold.json"):
            continue
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(card, dict):
            continue
        parts = [str(card.get("name") or ""), str(card.get("uses") or "")]
        for key in ("features", "tags", "catalog_tags"):
            value = card.get(key)
            if isinstance(value, list):
                parts.extend(str(item) for item in value)
        tokens = set(re.findall(r"[a-z0-9]+", " ".join(parts).lower()))
        words = [word for word in OVERLAP_WORDS if word in tokens]
        name = str(card.get("name") or path.stem)
        if not words and name not in H1_NAMES:
            continue
        rows.append(
            {
                "file": path.name,
                "name": name,
                "stage": card.get("integration_stage"),
                "words": words,
                "h1_named": name in H1_NAMES,
            }
        )
    return rows


def skill_up_note() -> dict:
    path = ROOT / "eval" / "catchup-1107" / "skill-up" / "summary.json"
    if not path.is_file():
        return {"present": False}
    data = json.loads(path.read_text(encoding="utf-8"))
    benchmark = (data.get("iterations") or [{}])[0].get("benchmark") or {}
    return {
        "present": True,
        "case_count": len(data.get("case_ids") or []),
        "delta_pass_rate": (benchmark.get("delta") or {}).get("pass_rate"),
        "with_mean": ((benchmark.get("with_skill") or {}).get("pass_rate") or {}).get("mean"),
        "without_mean": ((benchmark.get("without_skill") or {}).get("pass_rate") or {}).get("mean"),
    }


def pin_facts(src: Path, binary: Path) -> dict:
    git_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "HOME": os.environ.get("HOME", "/tmp"),
    }
    head = run_cmd(["git", "-C", str(src), "rev-parse", "HEAD"], git_env)
    tag = run_cmd(["git", "-C", str(src), "describe", "--tags", "--exact-match"], git_env)
    version = {"exit": None, "stdout": ""}
    if binary.is_file():
        version = run_cmd([str(binary), "version"], child_env(src.parent, src.parent, "", ""))
    return {
        "pin_head": (head["stdout"] or "").strip(),
        "pin_head_ok": (head["stdout"] or "").strip() == PIN,
        "pin_tag": (tag["stdout"] or "").strip(),
        "pin_tag_ok": (tag["stdout"] or "").strip() == PIN_TAG,
        "version_line": (version["stdout"] or "").strip().splitlines()[:1],
        "binary_sha256": sha256_file(binary) if binary.is_file() else "",
        "binary_bytes": binary.stat().st_size if binary.is_file() else 0,
        "checkout_bytes": dir_bytes(src),
    }


def load_password(cache: Path) -> str:
    path = cache / "db.pass"
    if path.is_file() and path.stat().st_size > 0:
        return path.read_text(encoding="utf-8").strip()
    import secrets

    value = secrets.token_hex(16)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    path.chmod(0o600)
    return value


def podman_base(podman: str, cache: Path) -> list[str]:
    return [
        podman,
        "--root",
        str(cache / "podman" / "root"),
        "--runroot",
        str(cache / "podman" / "run"),
    ]


def stop_postgres(podman: str, cache: Path, env: dict) -> None:
    base = podman_base(podman, cache)
    run_cmd(base + ["rm", "-f", CONTAINER], env, timeout=60)
    run_cmd(base + ["volume", "rm", "-f", CONTAINER], env, timeout=60)


def start_postgres(podman: str, cache: Path, env: dict, password: str) -> dict:
    base = podman_base(podman, cache)
    env_file = cache / "pg.env"
    env_file.write_text(
        "POSTGRES_USER=kenfold\nPOSTGRES_PASSWORD=%s\nPOSTGRES_DB=kenfold\n" % password,
        encoding="utf-8",
    )
    env_file.chmod(0o600)
    last = "postgres did not become ready"
    for attempt in range(1, 4):
        stop_postgres(podman, cache, env)
        created = run_cmd(base + ["volume", "create", CONTAINER], env, timeout=60)
        if created["exit"] != 0:
            last = (created["stderr"] or created["stdout"] or "volume create failed")[-240:]
            continue
        started = run_cmd(
            base
            + [
                "run",
                "-d",
                "--name",
                CONTAINER,
                "--replace",
                "-p",
                "127.0.0.1:54329:5432",
                "--env-file",
                str(env_file),
                "-v",
                "%s:/var/lib/postgresql" % CONTAINER,
                IMAGE,
            ],
            env,
            timeout=120,
        )
        if started["exit"] != 0:
            last = (started["stderr"] or started["stdout"] or "podman run failed")[-240:]
            continue
        ready = False
        for _ in range(30):
            check = run_cmd(
                base + ["exec", CONTAINER, "pg_isready", "-h", "127.0.0.1", "-U", "kenfold", "-d", "kenfold"],
                env,
                timeout=15,
            )
            if check["exit"] == 0:
                ready = True
                break
            time.sleep(1)
        if ready:
            images = run_cmd(base + ["images", "--format", "{{.Id}} {{.Repository}}:{{.Tag}} {{.Size}}"], env)
            return {"ok": True, "attempts": attempt, "images": (images["stdout"] or "").strip().splitlines()}
        last = "pg_isready did not return 0"
    return {"ok": False, "attempts": 3, "reason": last}


class Mcp:
    """Newline JSON-RPC over a binary pipe. A reader thread owns stdout."""

    def __init__(self, binary: str, env: dict):
        self.proc = subprocess.Popen(
            [binary, "mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            bufsize=0,
        )
        self.lines: queue.Queue[bytes | None] = queue.Queue()
        self._next = 0
        threading.Thread(target=self._read_stdout, daemon=True).start()
        threading.Thread(target=self._drain, daemon=True).start()

    def _read_stdout(self) -> None:
        assert self.proc.stdout is not None
        buf = b""
        while True:
            chunk = self.proc.stdout.read(4096)
            if not chunk:
                self.lines.put(None)
                return
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if line.strip():
                    self.lines.put(line)

    def _drain(self) -> None:
        assert self.proc.stderr is not None
        while self.proc.stderr.read(4096):
            pass

    def _send(self, obj: dict) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write((json.dumps(obj) + "\n").encode())
        self.proc.stdin.flush()

    def _read(self, want: int, deadline: float) -> dict | None:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            try:
                line = self.lines.get(timeout=remaining)
            except queue.Empty:
                return None
            if line is None:
                return None
            try:
                msg = json.loads(line.decode())
            except json.JSONDecodeError:
                continue
            if msg.get("id") == want:
                return msg

    def request(self, method: str, params: dict, timeout: float = 20) -> dict | None:
        self._next += 1
        ident = self._next
        self._send({"jsonrpc": "2.0", "id": ident, "method": method, "params": params})
        return self._read(ident, time.monotonic() + timeout)

    def notify(self, method: str) -> None:
        self._send({"jsonrpc": "2.0", "method": method})

    def close(self) -> int:
        if self.proc.stdin:
            try:
                self.proc.stdin.close()
            except OSError:
                pass
        try:
            return self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            return self.proc.wait(timeout=5)


def tool_body(msg: dict | None) -> dict:
    if not msg:
        return {"missing": True, "is_error": True, "structured": {}}
    result = msg.get("result") or {}
    structured = result.get("structuredContent")
    if not isinstance(structured, dict):
        structured = {}
    return {
        "missing": False,
        "is_error": bool(result.get("isError") or msg.get("error")),
        "structured": structured,
        "raw": json.dumps(msg),
    }


def open_session(binary: str, env: dict) -> Mcp | None:
    session = Mcp(binary, env)
    init = session.request(
        "initialize",
        {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "pfy-kenfold-probe", "version": "0"},
        },
    )
    if not init or not ((init.get("result") or {}).get("serverInfo") or {}).get("name"):
        session.close()
        return None
    session.notify("notifications/initialized")
    return session


def novel_sentence(token: str) -> str:
    return "%s is a throwaway shared-memory token for the kenfold probe." % token


def memory_round(binary: str, home: Path, tmp: Path, password: str) -> dict:
    secret = shaped_secret()
    writer_env = child_env(home, tmp, password, WRITER)
    start = time.perf_counter()
    writer = open_session(binary, writer_env)
    if writer is None:
        return {"mcp_open": False}
    secret_msg = writer.request(
        "tools/call",
        {"name": "remember", "arguments": {"content": secret, "type": "semantic", "project": PROJECT}},
    )
    secret_body = tool_body(secret_msg)
    remembered = 0
    for token in NOVEL:
        msg = writer.request(
            "tools/call",
            {
                "name": "remember",
                "arguments": {"content": novel_sentence(token), "type": "semantic", "project": PROJECT},
            },
        )
        body = tool_body(msg)
        if not body["is_error"] and body["structured"].get("status") == "active":
            remembered += 1
    writer.close()
    remember_ms = ms(start)

    def recall_pass(agent: str, include_repo: bool) -> dict:
        env = child_env(home, tmp, password, agent)
        begin = time.perf_counter()
        session = open_session(binary, env)
        if session is None:
            return {"open": False, "tokens": [], "provenance": 0, "repo": 0, "ms": ms(begin)}
        tokens: list[str] = []
        provenance = 0
        for token in NOVEL:
            msg = session.request(
                "tools/call",
                {
                    "name": "recall",
                    "arguments": {"query": token, "project": PROJECT, "limit": 5},
                },
            )
            body = tool_body(msg)
            memories = body["structured"].get("memories") or []
            hit = False
            attributed = False
            if isinstance(memories, list):
                for row in memories:
                    if not isinstance(row, dict):
                        continue
                    content = str(row.get("content") or "")
                    if token in content:
                        hit = True
                        if row.get("source_agent") == WRITER:
                            attributed = True
            if hit:
                tokens.append(token)
            if attributed:
                provenance += 1
        repo_hits = 0
        if include_repo:
            for needle in REPO_NEEDLES:
                msg = session.request(
                    "tools/call",
                    {
                        "name": "recall",
                        "arguments": {"query": needle, "project": PROJECT, "limit": 5},
                    },
                )
                body = tool_body(msg)
                memories = body["structured"].get("memories") or []
                if isinstance(memories, list) and any(
                    isinstance(row, dict) and needle in str(row.get("content") or "") for row in memories
                ):
                    repo_hits += 1
        session.close()
        return {"open": True, "tokens": tokens, "provenance": provenance, "repo": repo_hits, "ms": ms(begin)}

    first = recall_pass(READER, True)
    second = recall_pass(READER, False)
    agreement = 0
    if first["open"] and second["open"]:
        agreement = len(set(first["tokens"]) & set(second["tokens"]))
    echoed = secret in (secret_body.get("raw") or "")
    return {
        "mcp_open": True,
        "remember_ok": remembered,
        "remember_ms": remember_ms,
        "secret_rejected": bool(secret_body["is_error"]),
        "secret_echoed": echoed,
        "recall_hits": len(first["tokens"]) if first["open"] else 0,
        "recall_tokens": first["tokens"] if first["open"] else [],
        "recall_ms": first["ms"],
        "recall_open": first["open"],
        "provenance_hits": first["provenance"] if first["open"] else 0,
        "repo_recall_hits": first["repo"] if first["open"] else 0,
        "recall_second_hits": len(second["tokens"]) if second["open"] else 0,
        "recall_second_tokens": second["tokens"] if second["open"] else [],
        "recall_second_ms": second["ms"],
        "recall_second_open": second["open"],
        "agreement": agreement,
    }


def blank() -> dict:
    return {
        "server_skipped": False,
        "skip_reason": "",
        "remember_ok": 0,
        "remember_ms": 0,
        "secret_rejected": False,
        "secret_echoed": False,
        "recall_hits": 0,
        "recall_ms": 0,
        "recall_second_hits": 0,
        "recall_second_ms": 0,
        "agreement": 0,
        "provenance_hits": 0,
        "repo_recall_hits": 0,
        "h1_graded_cases": 0,
        "rg_repo_hits": 0,
        "rg_novel_hits": 0,
        "rg_ms": 0,
        "mcp_open": False,
    }


def write_doc(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(doc, indent=2, sort_keys=True) + "\n"
    if shaped_secret() in text:
        raise SystemExit("refusing to write a result that contains the secret fixture")
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(OUT))
    parser.add_argument("--kenfold-bin", default="")
    parser.add_argument("--podman-bin", default="podman")
    parser.add_argument("--rg-bin", default="rg")
    parser.add_argument("--home", default="")
    parser.add_argument("--tmp", default="")
    parser.add_argument("--cache", default="")
    parser.add_argument("--no-server", action="store_true")
    parser.add_argument("--skip-pins", action="store_true")
    parser.add_argument("--skip-home", action="store_true")
    args = parser.parse_args()

    cache = Path(args.cache) if args.cache else cache_base()
    home = Path(args.home) if args.home else (cache / "probe-home")
    tmp = Path(args.tmp) if args.tmp else (cache / "probe-tmp")
    for path in (home, tmp, home / "xdg-config", home / "xdg-cache", home / "xdg-data"):
        path.mkdir(parents=True, exist_ok=True)
    binary = args.kenfold_bin or str(cache / "bin" / "kenfold")
    watched = [real_home() / ".local" / "state" / "kenfold", real_home() / ".cache" / "kenfold"]
    before = [] if args.skip_home else [home_fingerprint(path) for path in watched]

    doc = blank()
    doc["h1_graded_cases"] = 0
    doc.update(rg_scan(args.rg_bin))
    doc["overlap"] = overlap_cards()
    doc["skill_up"] = skill_up_note()
    if not args.skip_pins:
        doc["pins"] = pin_facts(cache / "src" / "kenfold", Path(binary))
    password = "" if args.no_server else load_password(cache)
    base_env = child_env(home, tmp, password, "")
    server: dict = {"ok": True, "skipped": args.no_server}
    try:
        if not args.no_server:
            server = start_postgres(args.podman_bin, cache, base_env, password)
            doc["postgres_attempts"] = server.get("attempts")
            doc["image_lines"] = server.get("images") or []
            if not server.get("ok"):
                doc["server_skipped"] = True
                doc["skip_reason"] = "postgres: " + str(server.get("reason") or "not ready")
                return 0
        migrate = run_cmd([binary, "migrate", "up"], base_env, timeout=60)
        doc["migrate_exit"] = migrate["exit"]
        doc["migrate_ms"] = migrate["ms"]
        if migrate["exit"] != 0:
            doc["server_skipped"] = True
            doc["skip_reason"] = "migrate exited %s" % migrate["exit"]
            return 0
        round_doc = memory_round(binary, home, tmp, password)
        doc.update(round_doc)
        if not round_doc.get("mcp_open"):
            doc["server_skipped"] = True
            doc["skip_reason"] = "mcp initialize failed"
        return 0
    finally:
        if not args.no_server:
            stop_postgres(args.podman_bin, cache, base_env)
        if not args.skip_home:
            after = [home_fingerprint(path) for path in watched]
            doc["real_home_unchanged"] = after == before
        doc["no_server"] = args.no_server
        write_doc(Path(args.out), doc)


if __name__ == "__main__":
    raise SystemExit(main())
