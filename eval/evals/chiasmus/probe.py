#!/usr/bin/env python3
"""Pin check for chiasmus Python impact names.

Uses the already installed npm tree at $CHIASMUS_DIR (default: the tool
cache). Does not install, does not start chiasmus-http, and does not call
chiasmus_solve or chiasmus_search. CHIASMUS_HOME and CHIASMUS_CACHE_DIR
are a temp directory. The real home paths the server would otherwise
write are stamped before and after.

Exit 0: package is 0.1.40, impact("connect") is the bare name main, and
a file-qualified target is not a graph node.
Exit 1: the server ran and the pin or the names disagree.
Exit 2: node, the server, or the package is missing.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path

PIN = "0.1.40"
GIT = "e3e8aa54d200f97507514d205b3bfb156aa70150"
OUT = Path(__file__).resolve().parent / "results.json"

# Two files define main. Only a.py calls connect. A file-qualified pin
# would name a.py's main and leave b.py's main out of the impact set.
A_PY = "def connect():\n    return 1\n\n\ndef main():\n    return connect()\n"
B_PY = "def main():\n    return 0\n"


def tool_dir() -> Path:
    raw = os.environ.get("CHIASMUS_DIR", "").strip()
    if raw:
        return Path(raw)
    return Path.home() / ".cache" / "pfy" / "tools" / "chiasmus"


def du_bytes(path: Path, allocated: bool = False) -> int | None:
    if not path.exists():
        return None
    argv = ["du", "-s", "--block-size=1", str(path)] if allocated else ["du", "-sb", str(path)]
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return None
    return int(proc.stdout.split()[0])


def stamp(path: Path) -> str:
    """absent, or a content hash. The hash does not include the absolute path."""
    if not path.exists():
        return "absent"
    digest = hashlib.sha256()
    if path.is_file():
        digest.update(path.read_bytes())
        return digest.hexdigest()
    for item in sorted(path.rglob("*")):
        rel = item.relative_to(path).as_posix()
        digest.update(rel.encode())
        digest.update(b"\0")
        if item.is_file() and not item.is_symlink():
            digest.update(item.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


class Mcp:
    def __init__(self, argv: list[str], cwd: Path, env: dict[str, str]) -> None:
        self.proc = subprocess.Popen(
            argv,
            cwd=str(cwd),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.err: list[str] = []
        threading.Thread(target=self._read_err, daemon=True).start()
        self.n = 0

    def _read_err(self) -> None:
        assert self.proc.stderr is not None
        self.err.extend(self.proc.stderr)

    def req(self, method: str, params: dict | None = None) -> dict:
        self.n += 1
        assert self.proc.stdin is not None and self.proc.stdout is not None
        self.proc.stdin.write(
            json.dumps({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params or {}})
            + "\n"
        )
        self.proc.stdin.flush()
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError("server closed stdout: " + "".join(self.err)[-400:])
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if message.get("id") == self.n:
                return message

    def notify(self, method: str) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method}) + "\n")
        self.proc.stdin.flush()

    def init(self) -> dict:
        reply = self.req(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "pfy-probe", "version": "0"},
            },
        )
        self.notify("notifications/initialized")
        return (reply.get("result") or {}).get("serverInfo") or {}

    def call(self, name: str, args: dict) -> dict:
        reply = self.req("tools/call", {"name": name, "arguments": args})
        result = reply.get("result") or {}
        text = "".join(
            part.get("text", "")
            for part in result.get("content", [])
            if isinstance(part, dict)
        )
        try:
            body = json.loads(text)
        except json.JSONDecodeError:
            body = text
        return {"is_error": bool(result.get("isError")), "body": body}

    def stop(self) -> None:
        if self.proc.stdin is not None:
            try:
                self.proc.stdin.close()
            except OSError:
                pass
        try:
            self.proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=5)


def split_atoms(body: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    quoted = False
    escape = False
    for ch in body:
        if escape:
            buf.append(ch)
            escape = False
            continue
        if ch == "\\" and quoted:
            escape = True
            continue
        if ch == "'":
            quoted = not quoted
            continue
        if ch == "," and not quoted:
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return parts


def npm_latest() -> str:
    try:
        proc = subprocess.run(
            ["npm", "view", "chiasmus", "version"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def main_vs_tag() -> str:
    url = "https://api.github.com/repos/yogthos/chiasmus/compare/v0.1.40...main"
    try:
        proc = subprocess.run(
            ["curl", "-fsSL", "--max-time", "20", url],
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if proc.returncode != 0:
        return ""
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return ""
    status = data.get("status")
    return status if isinstance(status, str) else ""


def server_env(home: Path, chome: Path, cache: Path, tmp: Path) -> dict[str, str]:
    return {
        "HOME": str(home),
        "PATH": "/usr/bin:/bin",
        "CHIASMUS_HOME": str(chome),
        "CHIASMUS_CACHE_DIR": str(cache),
        "XDG_CONFIG_HOME": str(home / "xdg-config"),
        "XDG_CACHE_HOME": str(home / "xdg-cache"),
        "XDG_DATA_HOME": str(home / "xdg-data"),
        "TMPDIR": str(tmp),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "NODE_NO_WARNINGS": "1",
    }


def main() -> int:
    base = tool_dir()
    pkg = base / "node_modules" / "chiasmus"
    server = pkg / "dist" / "mcp-server.js"
    node = shutil.which("node", path="/usr/bin:/bin") or shutil.which("node")
    if node is None or not server.is_file() or not (pkg / "package.json").is_file():
        print("missing chiasmus server or node", flush=True)
        return 2
    package = json.loads((pkg / "package.json").read_text(encoding="utf-8"))
    version = package.get("version")
    home = Path.home()
    before = {
        "chiasmus_home": stamp(home / ".chiasmus"),
        "chiasmus_cache": stamp(home / ".cache" / "chiasmus"),
    }
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="pfy-chiasmus-probe-") as raw:
        td = Path(raw)
        proj = td / "proj"
        proj.mkdir()
        (proj / "a.py").write_text(A_PY, encoding="utf-8")
        (proj / "b.py").write_text(B_PY, encoding="utf-8")
        for name in ("home", "chome", "ccache", "tmp"):
            (td / name).mkdir()
        env = server_env(td / "home", td / "chome", td / "ccache", td / "tmp")
        mcp = Mcp([node, str(server)], proj, env)
        try:
            info = mcp.init()
            files = [str(proj / "a.py"), str(proj / "b.py")]
            facts = mcp.call("chiasmus_graph", {"files": files, "analysis": "facts", "cache": False})
            impact = mcp.call(
                "chiasmus_graph",
                {"files": files, "analysis": "impact", "target": "connect", "cache": False},
            )
            qualified = mcp.call(
                "chiasmus_graph",
                {"files": files, "analysis": "impact", "target": "a.py:main", "cache": False},
            )
        finally:
            mcp.stop()
    after = {
        "chiasmus_home": stamp(home / ".chiasmus"),
        "chiasmus_cache": stamp(home / ".cache" / "chiasmus"),
    }
    program = ""
    body = facts.get("body")
    if isinstance(body, dict):
        result = body.get("result")
        if isinstance(result, str):
            program = result
        elif isinstance(result, dict):
            program = str(result.get("program") or result.get("facts") or "")
    defines = defines_from_facts(program)
    impact_names = _names(impact)
    qualified_names = _names(qualified)
    bare = all("/" not in row["name"] and ":" not in row["name"] for row in defines)
    two_mains = sorted(row["file"] for row in defines if row["name"] == "main") == ["a.py", "b.py"]
    home_same = before == after
    payload = {
        "pin": version,
        "git": GIT,
        "npm_latest": npm_latest(),
        "main_vs_tag": main_vs_tag(),
        "node": _node_version(node),
        "install_bytes": du_bytes(base / "node_modules"),
        "install_allocated_bytes": du_bytes(base / "node_modules", allocated=True),
        "package_bytes": du_bytes(pkg),
        "ten_commit_repeated": False,
        "prior_results": "eval/ev1107/chiasmus/results.json",
        "prior_agreement": _prior_field("chiasmus_agreement"),
        "prior_cbm_agreement": _prior_field("cbm_agreement"),
        "server_version": info.get("version"),
        "defines": defines,
        "impact_connect": impact_names,
        "impact_file_target": qualified_names,
        "bare_names": bare,
        "same_name_two_files": two_mains,
        "file_qualified": False,
        "real_home_unchanged": home_same,
        "wall_s": round(time.perf_counter() - started, 3),
        "facts_error": bool(facts.get("is_error")),
        "impact_error": bool(impact.get("is_error")),
    }
    # file_qualified stays false unless impact names the file.
    payload["file_qualified"] = any(
        isinstance(name, str) and (name.endswith("/main") or "a.py" in name)
        for name in impact_names
    )
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        "pin", payload["pin"],
        "impact", impact_names,
        "qualified_target", qualified_names,
        "bare", bare,
        "home", home_same,
        flush=True,
    )
    if version != PIN or payload["server_version"] != PIN:
        return 1
    if not bare or not two_mains or impact_names != ["main"] or qualified_names != []:
        return 1
    if not home_same:
        return 1
    return 0


def defines_from_facts(program: str) -> list[dict]:
    """Keep fixture labels only. An absolute path is not stored."""
    rows = []
    for raw in program.splitlines():
        line = raw.strip()
        if not line.startswith("defines(") or not line.endswith(")."):
            continue
        atoms = split_atoms(line[len("defines(") : -2])
        if len(atoms) != 4:
            continue
        file_atom = atoms[0].replace("\\", "/")
        if file_atom.endswith("/a.py"):
            label = "a.py"
        elif file_atom.endswith("/b.py"):
            label = "b.py"
        else:
            continue
        rows.append({"file": label, "name": atoms[1], "kind": atoms[2], "line": int(atoms[3])})
    return rows


def _prior_field(key: str) -> str:
    path = Path(__file__).resolve().parents[3] / "eval" / "ev1107" / "chiasmus" / "results.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    value = data.get(key)
    return value if isinstance(value, str) else ""


def _names(reply: dict) -> list:
    body = reply.get("body")
    if not isinstance(body, dict):
        return []
    result = body.get("result")
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and isinstance(result.get("impact"), list):
        return result["impact"]
    return []


def _node_version(node: str) -> str:
    proc = subprocess.run([node, "--version"], capture_output=True, text=True, check=False)
    return (proc.stdout or "").strip()


if __name__ == "__main__":
    raise SystemExit(main())
