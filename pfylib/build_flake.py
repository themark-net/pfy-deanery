"""Clean-clone re-runs of a gate that already passed, and a fixed-port scan.

The re-run exports the result tree (not the commit) so a state file the
gate wrote is still there, then runs with a fresh HOME. Port 0 is an
ephemeral bind and is not a warning. A listen backlog under 1024 is not
a port.
"""

from __future__ import annotations

import ast
import os
import shutil
from pathlib import Path

DEFAULT_FLAKE_RUNS = 2


def resolve_flake_runs(flag: int | None, environ: dict | None = None) -> int:
    """Flag, then PFY_BUILD_FLAKE_RUNS, then the default. Below zero is an error."""
    source = os.environ if environ is None else environ
    chosen = flag
    if chosen is None:
        raw = source.get("PFY_BUILD_FLAKE_RUNS")
        if raw is None or str(raw).strip() == "":
            return DEFAULT_FLAKE_RUNS
        try:
            chosen = int(str(raw).strip())
        except ValueError as exc:
            raise ValueError("flake-runs must be zero or greater") from exc
    if int(chosen) < 0:
        raise ValueError("flake-runs must be zero or greater")
    return int(chosen)

_SKIP_ROOT = {".git", "tmp", "__pycache__", ".pytest_cache", ".mypy_cache"}
_SKIP_ANY = {"__pycache__", ".pytest_cache", ".mypy_cache"}
_SERVERS = {
    "HTTPServer",
    "TCPServer",
    "UDPServer",
    "ThreadingTCPServer",
    "ThreadingHTTPServer",
    "ThreadingUDPServer",
}


def fresh_env(home: Path) -> dict[str, str]:
    """A new HOME and no parent secrets. PATH is kept so the gate can start."""
    home.mkdir(parents=True, exist_ok=True)
    tmp = home / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    (home / ".config").mkdir(parents=True, exist_ok=True)
    (home / ".cache").mkdir(parents=True, exist_ok=True)
    (home / ".local" / "share").mkdir(parents=True, exist_ok=True)
    env = {
        "PATH": os.environ.get("PATH") or "/usr/bin:/bin",
        "HOME": str(home),
        "TMPDIR": str(tmp),
        "LANG": os.environ.get("LANG") or "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
    }
    lc_all = os.environ.get("LC_ALL")
    if lc_all:
        env["LC_ALL"] = lc_all
    return env


def export_result_tree(src: Path, dest: Path) -> None:
    """Copy the result tree. Skip VCS metadata, tmp, and bytecode."""
    root = src.resolve()

    def ignore(directory: str, names: list[str]) -> list[str]:
        try:
            here = Path(directory).resolve()
        except OSError:
            here = Path(directory)
        blocked = _SKIP_ROOT if here == root else _SKIP_ANY
        return [name for name in names if name in blocked or name.endswith(".pyc")]

    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest, symlinks=True, ignore=ignore)


def prepare_clean_clone(src: Path, dest: Path, home: Path) -> dict[str, str]:
    export_result_tree(src, dest)
    return fresh_env(home)


def run_clean_clones(src: Path, count: int, scratch: Path, stamp: str, run_one) -> list[dict]:
    """Call run_one(index, dest, env) once per clone. Stop when a row sets stop."""
    rows: list[dict] = []
    scratch.mkdir(parents=True, exist_ok=True)
    for index in range(1, int(count) + 1):
        dest = scratch / ("flake-%s-%d" % (stamp, index))
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        home = dest / "tmp" / "flake-home"
        try:
            env = prepare_clean_clone(src, dest, home)
            row = run_one(index, dest, env)
        finally:
            shutil.rmtree(dest, ignore_errors=True)
        if not isinstance(row, dict):
            row = {"run": index, "exit": None, "ok": False, "tail": "", "stop": ""}
        rows.append(row)
        if row.get("stop"):
            break
    return rows


def flake_verdict(rows: list[dict]) -> str:
    """timeout, interrupted, mem-edge, flaky, or ok."""
    for row in rows:
        stop = row.get("stop") or ""
        if stop in ("timeout", "interrupted", "mem-edge"):
            return stop
    if any(not row.get("ok") for row in rows):
        return "flaky"
    return "ok"


def _int_const(node: ast.AST) -> int | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value
    return None


def _address_port(node: ast.AST) -> int | None:
    if isinstance(node, ast.Tuple) and len(node.elts) >= 2:
        return _int_const(node.elts[1])
    return None


def _call_name(func: ast.AST) -> str:
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def _ports_in_tree(tree: ast.AST) -> list[tuple[str, int, int]]:
    found: list[tuple[str, int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        name = _call_name(node.func)
        if name == "bind" or name in _SERVERS:
            port = _address_port(node.args[0])
            if port is not None and port != 0:
                found.append((name, port, int(getattr(node, "lineno", 0) or 0)))
            continue
        if name == "listen":
            port = _int_const(node.args[0])
            # A small listen() argument is a backlog, not a TCP port.
            if port is not None and port >= 1024:
                found.append(("listen", port, int(getattr(node, "lineno", 0) or 0)))
    return found


def _is_test_py(rel: str) -> bool:
    if not rel.endswith(".py"):
        return False
    parts = [part for part in rel.split("/") if part]
    if not parts:
        return False
    name = parts[-1]
    if name.startswith("test_") or name.endswith("_test.py"):
        return True
    return any(part in ("tests", "test") for part in parts[:-1])


def scan_fixed_ports(root: Path) -> list[dict]:
    """Literal non-zero bind/listen ports in test files. Port 0 is omitted."""
    hits: list[dict] = []
    if not root.is_dir():
        return hits
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in _SKIP_ROOT and name not in _SKIP_ANY]
        for name in filenames:
            full = Path(dirpath) / name
            try:
                rel = full.relative_to(root).as_posix()
            except ValueError:
                continue
            if not _is_test_py(rel) or rel.startswith("tmp/"):
                continue
            try:
                source = full.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            try:
                parsed = ast.parse(source)
            except SyntaxError:
                continue
            for call, port, line in _ports_in_tree(parsed):
                hits.append({"path": rel, "line": line, "port": port, "call": call})
    hits.sort(key=lambda item: (item["path"], item["line"], item["call"]))
    return hits


def port_warning_lines(findings: list[dict]) -> list[str]:
    lines = []
    for item in findings:
        lines.append(
            "fixed listen port %s in %s:%s (%s)"
            % (item.get("port"), item.get("path"), item.get("line"), item.get("call"))
        )
    return lines
