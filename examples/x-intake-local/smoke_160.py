#!/usr/bin/env python3
"""Operate-or-FAIL smoke for X intake Entry 160 (agentplay). Uses smoke.py helpers.

Usage: python3 examples/x-intake-local/smoke_160.py

Exit 0 = the pinned CLI printed its version and help, and `import` accepted one
synthetic agentplay/v1 map (then `list` showed that session). No browser.
Exit 1 = the CLI ran but a check failed, or a real-HOME path changed.
Exit 2 = Python is too old, pip or the network is missing, the venv or the
wheel cannot be installed, the version pin misses, or the timeout value is bad.

pip installs `agentplay==<pin>` with no extra deps. The venv, pip cache, and
HOME stay under this worktree's tmp/xintake-160/. The scratch directory is
removed when the smoke exits. `view` is never started. The published wheel
sha256 is recorded; this smoke checks the version string, not the file hash.

Receipt: $PFY_SMOKE_RECEIPT_DIR/agentplay/latest.json, else pipelines/smoke/agentplay/latest.json.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from smoke import pinned, run_isolated, timeout_reason, write

PIN_VERSION = "0.2.6"
PIN_COMMIT = "ff5f83e37063a38ec55ab7dd2b0fcdc435f4a72c"
# Published wheel sha256 for agentplay-0.2.6-py3-none-any.whl. The smoke pins
# the version pip installs and checks `--version`. It does not re-hash the wheel.
PIN_SHA256 = "b595890785649cb9fa8d83957fadcfbb1cfc47117bb1d60e21ebfdb0938ba4ee"
SESSION_ID = "local:claude-code:pfy-smoke-160"
WATCHED = (
    ".agentplay", ".claude", ".codex", ".cursor", ".grok",
    ".config/opencode", ".local/share/opencode", ".cache/pip",
)
ROOT = Path(__file__).resolve().parents[2]
MIN_PY = (3, 11)


def _limit(default: float) -> float:
    raw = os.environ.get("PFY_XINTAKE_TIMEOUT", "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError("PFY_XINTAKE_TIMEOUT is not a positive number") from exc
    if not math.isfinite(value) or value <= 0:
        raise ValueError("PFY_XINTAKE_TIMEOUT is not a positive number")
    return value


def _executable(path: str | None) -> bool:
    return bool(path) and os.path.isfile(path) and os.access(path, os.X_OK)


def _tool(env_name: str, which_name: str) -> str | None:
    if env_name in os.environ:
        path = os.environ[env_name]
        return path if _executable(path) else None
    found = shutil.which(which_name)
    return found if _executable(found) else None


def _py_ok(python: str) -> bool:
    with tempfile.TemporaryDirectory(prefix="agentplay-py-") as home:
        try:
            proc = run_isolated(
                [python, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
                home=home, timeout=15, path="/usr/bin:/bin", kill_on_exit=True,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
    if proc.returncode != 0:
        return False
    parts = (proc.stdout or "").strip().split(".")
    try:
        return (int(parts[0]), int(parts[1])) >= MIN_PY
    except (IndexError, ValueError):
        return False


def _sig(home: Path) -> dict:
    out = {}
    for rel in WATCHED:
        path = home / rel
        try:
            if not path.exists():
                out[rel] = None
            elif path.is_dir() and not path.is_symlink():
                out[rel] = tuple(sorted(child.name for child in path.iterdir()))
            else:
                out[rel] = ("leaf", path.stat().st_size)
        except OSError as exc:
            out[rel] = ("error", type(exc).__name__)
    return out


def _under_worktree(path: Path) -> bool:
    try:
        path.resolve().relative_to((ROOT / "tmp").resolve())
    except ValueError:
        return False
    return True


def _call(cmd: list[str], home: str, timeout: float, cwd: str, extra: dict, path: str):
    try:
        return run_isolated(
            cmd, home=home, cwd=cwd, timeout=timeout, path=path, extra=extra,
            bwrap_writable=None, kill_on_exit=True,
        )
    except subprocess.TimeoutExpired:
        return "timeout"
    except OSError as exc:
        return exc


def _text(proc: subprocess.CompletedProcess) -> str:
    return (proc.stdout or "") + "\n" + (proc.stderr or "")


def _synthetic() -> dict:
    return {
        "schema": "agentplay/v1",
        "session": {
            "id": SESSION_ID,
            "agentTool": "claude-code",
            "startedAt": "2026-11-04T00:00:00Z",
            "durationMs": 1000,
            "models": ["none"],
            "pathMode": "relative",
            "outcome": "unknown",
        },
        "totals": {
            "calls": 2, "requests": 1, "subagents": 0, "errors": 1,
            "filesTouched": 1, "costUsd": 0, "tokens": 10, "userTurns": 1,
            "retries": 1, "compactions": 0,
        },
        "files": [{"id": 0, "path": "src/demo.py", "reads": 1, "edits": 1}],
        "events": [
            {"seq": 1, "t": 10, "kind": "read", "tool": "Read"},
            {"seq": 2, "t": 40, "kind": "verify", "tool": "Bash", "verb": "pytest",
             "err": True, "errClass": "exit_code", "exitCode": 1},
        ],
    }


def _install(python: str, scratch: Path, version: str, timeout: float, rec: dict) -> str | int:
    venv = scratch / "venv"
    cache = scratch / "pip-cache"
    home = scratch / "home"
    tmp = scratch / "tmp"
    for directory in (cache, home, tmp):
        directory.mkdir(parents=True, exist_ok=True)
    if not all(_under_worktree(directory) for directory in (venv, cache, home, scratch)):
        rec["reason"] = "agentplay scratch escaped the worktree tmp/"
        return 2
    path = ":".join(dict.fromkeys([os.path.dirname(python), "/usr/bin", "/bin"]))
    extra = {"PIP_CACHE_DIR": str(cache), "TMPDIR": str(tmp), "PIP_DISABLE_PIP_VERSION_CHECK": "1"}
    made = _call([python, "-m", "venv", str(venv)], str(home), timeout, str(scratch), extra, path)
    if made == "timeout":
        rec["reason"] = timeout_reason("agentplay venv", timeout)
        return 2
    if isinstance(made, OSError) or made.returncode != 0:
        rec["reason"] = "python venv failed; pip is not available in a virtualenv here"
        return 2
    pip = venv / "bin" / "pip"
    if not _executable(str(pip)):
        rec["reason"] = "pip/network unavailable: venv has no pip"
        return 2
    installed = _call(
        [str(pip), "install", "--disable-pip-version-check", "--no-deps", f"agentplay=={version}"],
        str(home), timeout, str(scratch), extra, path,
    )
    if installed == "timeout":
        rec["reason"] = timeout_reason("agentplay pip install", timeout)
        return 2
    if isinstance(installed, OSError):
        rec["reason"] = f"pip failed to start: {installed}"
        return 2
    if installed.returncode != 0:
        rec["reason"] = "pip/network unavailable: " + _text(installed)[-400:]
        return 2
    binary = venv / "bin" / "agentplay"
    if not _executable(str(binary)):
        rec["reason"] = "pip install finished without an agentplay binary"
        return 2
    rec["checks"]["venv"] = str(venv)
    rec["checks"]["pip_cache"] = str(cache)
    return str(binary)


def _run(binary: str, args: list[str], scratch: Path, timeout: float, path: str):
    home = scratch / "home"
    home.mkdir(parents=True, exist_ok=True)
    (home / ".agentplay").mkdir(exist_ok=True)
    extra = {
        "AGENTPLAY_NO_NETWORK": "1",
        "DO_NOT_TRACK": "1",
        "AGENTPLAY_HOME": str(home / ".agentplay"),
        "TMPDIR": str(scratch / "tmp"),
    }
    return _call([binary, *args], str(home), timeout, str(scratch), extra, path)


def body(rec: dict, made: list[Path]) -> tuple[int, Path | None]:
    version = pinned(rec, "AGENTPLAY_VERSION", PIN_VERSION)
    pinned(rec, "AGENTPLAY_COMMIT", PIN_COMMIT, lower=True)
    pinned(rec, "AGENTPLAY_SHA256", PIN_SHA256, lower=True)
    rec["checks"]["wheel_sha256_pin"] = PIN_SHA256
    command_timeout = _limit(30)
    install_timeout = command_timeout if os.environ.get("PFY_XINTAKE_TIMEOUT") else _limit(120)
    root = ROOT / "tmp" / "xintake-160"
    root.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="agentplay-", dir=root))
    made.append(scratch)
    (scratch / "tmp").mkdir(exist_ok=True)
    if "AGENTPLAY_BIN" in os.environ:
        binary = os.environ["AGENTPLAY_BIN"]
        if not _executable(binary):
            rec["reason"] = f"agentplay binary is not executable ({binary})"
            return 2, scratch
        path = os.path.dirname(binary) + ":/usr/bin:/bin"
    else:
        python = _tool("AGENTPLAY_PYTHON", "python3")
        if not python:
            rec["reason"] = "python3 is not available; agentplay smoke cannot run"
            return 2, scratch
        if not _py_ok(python):
            rec["reason"] = "python is older than 3.11; the pinned agentplay wheel cannot run"
            return 2, scratch
        installed = _install(python, scratch, version, install_timeout, rec)
        if isinstance(installed, int):
            return installed, scratch
        binary = installed
        path = os.path.dirname(binary) + ":/usr/bin:/bin"
    ran = _run(binary, ["--version"], scratch, command_timeout, path)
    if ran == "timeout":
        rec["reason"] = timeout_reason("agentplay --version", command_timeout)
        return 2, scratch
    if isinstance(ran, OSError):
        rec["reason"] = f"agentplay failed to start: {ran}"
        return 2, scratch
    if ran.returncode != 0 or version not in _text(ran):
        rec["reason"] = f"version pin {version} not in agentplay --version"
        rec["output"] = _text(ran)[-400:]
        return 2, scratch
    help_proc = _run(binary, ["--help"], scratch, command_timeout, path)
    if help_proc == "timeout":
        rec["reason"] = timeout_reason("agentplay --help", command_timeout)
        return 2, scratch
    if isinstance(help_proc, OSError) or help_proc.returncode != 0:
        rec["reason"] = "agentplay --help failed"
        rec["failed"] = ["help"]
        return 1, scratch
    help_text = _text(help_proc).lower()
    if "agentplay" not in help_text:
        rec["reason"] = "agentplay --help did not identify the tool"
        rec["failed"] = ["help"]
        return 1, scratch
    rec["checks"]["help"] = "ok"
    if "import" not in help_text:
        rec["reason"] = "agentplay --help has no import command; synthetic session was not parsed"
        rec["checks"]["parse"] = "unsupported"
        return 2, scratch
    if " view" in help_text or help_text.startswith("view"):
        rec["checks"]["view_available"] = True
    session = scratch / "synthetic-session.json"
    session.write_text(json.dumps(_synthetic()), encoding="utf-8")
    imported = _run(binary, ["import", str(session)], scratch, command_timeout, path)
    if imported == "timeout":
        rec["reason"] = timeout_reason("agentplay import", command_timeout)
        return 2, scratch
    if isinstance(imported, OSError) or imported.returncode != 0:
        detail = imported if isinstance(imported, OSError) else _text(imported)[-400:]
        rec["reason"] = f"agentplay import of the synthetic map failed: {detail}"
        rec["failed"] = ["import"]
        return 1, scratch
    listed = _run(binary, ["list", "--json"], scratch, command_timeout, path)
    if listed == "timeout":
        rec["reason"] = timeout_reason("agentplay list", command_timeout)
        return 2, scratch
    if isinstance(listed, OSError) or listed.returncode != 0 or SESSION_ID not in _text(listed):
        rec["reason"] = "agentplay list did not show the imported synthetic session"
        rec["failed"] = ["list"]
        return 1, scratch
    rec["checks"]["parse"] = "imported"
    rec["checks"]["browser"] = "not_opened"
    return 0, scratch


def main() -> int:
    rec: dict = {"entry": "160-agentplay", "failed": [], "checks": {}}
    before = _sig(Path.home())
    made: list[Path] = []
    code = 1
    try:
        code, _scratch = body(rec, made)
    except ValueError as exc:
        rec["reason"] = str(exc)
        code = 2
    finally:
        if _sig(Path.home()) != before:
            rec["reason"] = "real HOME agentplay paths changed"
            rec["failed"] = ["real_home_unchanged"]
            code = 1
        for path in made:
            shutil.rmtree(path, ignore_errors=True)
    return write("agentplay", rec, code)


if __name__ == "__main__":
    raise SystemExit(main())
