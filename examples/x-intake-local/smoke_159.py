#!/usr/bin/env python3
"""Operate-or-FAIL smoke for X intake Entry 159 (Skills Manager). Uses smoke.py helpers.

Usage: python3 examples/x-intake-local/smoke_159.py

Exit 0 = the pinned CLI printed its version and help, and `list` either printed
skills or refused because no skill home exists. Nothing is bootstrapped.
Exit 1 = the CLI ran but a check failed, or a real-HOME path changed.
Exit 2 = node or npm/npx is missing, the pinned package cannot be installed
(network or time box), the version pin misses, or the timeout value is bad.

HOME, the npm cache, and the install prefix are a scratch directory under this
worktree's tmp/. The scratch is removed when the smoke exits.

Receipt: $PFY_SMOKE_RECEIPT_DIR/skills-manager/latest.json, else pipelines/smoke/skills-manager/latest.json.
"""
from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from smoke import pinned, run_isolated, timeout_reason, write

PIN_VERSION = "2026.10.27-1"
PIN_COMMIT = "fae0bb864a8b96c1d0ca6278a6b7062e62992a36"
WATCHED = (
    ".skills-manager", ".claude", ".codex", ".grok", ".cursor",
    ".config/opencode", ".npm", ".npm-global",
)
ROOT = Path(__file__).resolve().parents[2]


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


def _sig(home: Path) -> dict:
    out = {}
    for rel in WATCHED:
        path = home / rel
        try:
            if not path.exists():
                out[rel] = None
            elif path.is_dir() and not path.is_symlink():
                names = []
                for child in sorted(path.iterdir(), key=lambda item: item.name):
                    if child.is_dir() and not child.is_symlink() and child.name in {"skills", "plugins"}:
                        names.append((child.name, tuple(sorted(item.name for item in child.iterdir()))))
                    else:
                        names.append(child.name)
                out[rel] = tuple(names)
            else:
                out[rel] = ("leaf", path.stat().st_size)
        except OSError as exc:
            out[rel] = ("error", type(exc).__name__)
    return out


def _under_worktree(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT.resolve())
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


def _install(npm: str, node: str, scratch: Path, version: str, timeout: float, rec: dict) -> str | int:
    prefix = scratch / "prefix"
    cache = scratch / "npm-cache"
    home = scratch / "home"
    tmp = scratch / "tmp"
    for directory in (prefix, cache, home, tmp):
        directory.mkdir(parents=True)
    if not all(_under_worktree(directory) for directory in (prefix, cache, home)):
        rec["reason"] = "skills-manager scratch escaped the worktree"
        return 2
    npmrc = scratch / "npmrc"
    npmrc.write_text("fund=false\naudit=false\nupdate-notifier=false\n", encoding="utf-8")
    (scratch / "package.json").write_text(
        '{"name":"pfy-xintake-159","private":true}\n', encoding="utf-8",
    )
    extra = {
        "npm_config_cache": str(cache),
        "npm_config_prefix": str(prefix),
        "npm_config_userconfig": str(npmrc),
        "npm_config_fund": "false",
        "npm_config_audit": "false",
        "npm_config_update_notifier": "false",
        "TMPDIR": str(tmp),
    }
    path = ":".join(dict.fromkeys([os.path.dirname(node), os.path.dirname(npm), "/usr/bin", "/bin"]))
    cmd = [
        npm, "install", "--ignore-scripts", "--no-fund", "--no-audit", "--no-package-lock",
        "--prefix", str(prefix), f"skills-manager-cli@{version}",
    ]
    rec["checks"]["npm_cache"] = str(cache)
    rec["checks"]["npm_home"] = str(home)
    proc = _call(cmd, str(home), timeout, str(scratch), extra, path)
    if proc == "timeout":
        rec["reason"] = timeout_reason("skills-manager npm install", timeout)
        return 2
    if isinstance(proc, OSError):
        rec["reason"] = f"npm failed to start: {proc}"
        return 2
    if proc.returncode != 0:
        rec["reason"] = "npm install failed or the network is blocked: " + _text(proc)[-400:]
        return 2
    for candidate in (prefix / "bin" / "skills-manager", prefix / "node_modules" / ".bin" / "skills-manager"):
        if _executable(str(candidate)):
            return str(candidate)
    rec["reason"] = "npm install finished without a skills-manager binary"
    return 2


def _run_cli(binary: str, args: list[str], scratch: Path, timeout: float, path: str):
    home = scratch / "home"
    home.mkdir(parents=True, exist_ok=True)
    return _call(
        [binary, *args], str(home), timeout, str(scratch),
        {"TMPDIR": str(scratch / "tmp")}, path,
    )


def body(rec: dict) -> tuple[int, Path | None]:
    version = pinned(rec, "SKILLS_MANAGER_VERSION", PIN_VERSION)
    pinned(rec, "SKILLS_MANAGER_COMMIT", PIN_COMMIT, lower=True)
    command_timeout = _limit(60)
    install_timeout = command_timeout if os.environ.get("PFY_XINTAKE_TIMEOUT") else _limit(180)
    scratch: Path | None = None
    if "SKILLS_MANAGER_BIN" in os.environ:
        binary = os.environ["SKILLS_MANAGER_BIN"]
        if not _executable(binary):
            rec["reason"] = f"skills-manager binary is not executable ({binary})"
            return 2, None
        node = _tool("SKILLS_MANAGER_NODE", "node") or "/usr/bin/node"
        path = os.path.dirname(node) + ":/usr/bin:/bin" if _executable(node) else "/usr/bin:/bin"
    else:
        node = _tool("SKILLS_MANAGER_NODE", "node")
        npm = _tool("SKILLS_MANAGER_NPM", "npm") or _tool("SKILLS_MANAGER_NPX", "npx")
        if not node:
            rec["reason"] = "node is not available; skills-manager smoke cannot run"
            return 2, None
        if not npm:
            rec["reason"] = "npx/npm is not available or the network install cannot start"
            return 2, None
        root = ROOT / "tmp" / "xintake-159"
        root.mkdir(parents=True, exist_ok=True)
        scratch = Path(tempfile.mkdtemp(prefix="skills-manager-", dir=root))
        installed = _install(npm, node, scratch, version, install_timeout, rec)
        if isinstance(installed, int):
            return installed, scratch
        binary = installed
        path = ":".join([os.path.dirname(node), os.path.dirname(binary), "/usr/bin", "/bin"])
    if scratch is None:
        root = ROOT / "tmp" / "xintake-159"
        root.mkdir(parents=True, exist_ok=True)
        scratch = Path(tempfile.mkdtemp(prefix="skills-manager-", dir=root))
    (scratch / "tmp").mkdir(exist_ok=True)
    ran = _run_cli(binary, ["--version"], scratch, command_timeout, path)
    if ran == "timeout":
        rec["reason"] = timeout_reason("skills-manager --version", command_timeout)
        return 2, scratch
    if isinstance(ran, OSError):
        rec["reason"] = f"skills-manager failed to start: {ran}"
        return 2, scratch
    if ran.returncode != 0 or version not in _text(ran):
        rec["reason"] = f"version pin {version} not in skills-manager --version"
        rec["output"] = _text(ran)[-400:]
        return 2, scratch
    help_proc = _run_cli(binary, ["--help"], scratch, command_timeout, path)
    if help_proc == "timeout":
        rec["reason"] = timeout_reason("skills-manager --help", command_timeout)
        return 2, scratch
    if isinstance(help_proc, OSError) or help_proc.returncode != 0 or "skills-manager" not in _text(help_proc).lower():
        rec["reason"] = "skills-manager --help failed"
        rec["failed"] = ["help"]
        return 1, scratch
    hub = scratch / "hub"
    listed = _run_cli(binary, ["list", "--home", str(hub)], scratch, command_timeout, path)
    if listed == "timeout":
        rec["reason"] = timeout_reason("skills-manager list", command_timeout)
        return 2, scratch
    if isinstance(listed, OSError):
        rec["reason"] = f"skills-manager list failed to start: {listed}"
        return 2, scratch
    listing = _text(listed)
    rec["checks"]["list_exit"] = listed.returncode
    refused = listed.returncode == 1 and "No skill home" in listing
    if listed.returncode != 0 and not refused:
        rec["reason"] = "skills-manager list failed: " + listing[-400:]
        rec["failed"] = ["list"]
        return 1, scratch
    rec["checks"]["list"] = "no_skill_home" if refused else "listed"
    return 0, scratch


def main() -> int:
    rec: dict = {"entry": "159-skills-manager", "failed": [], "checks": {}}
    before = _sig(Path.home())
    scratch: Path | None = None
    code = 1
    try:
        code, scratch = body(rec)
    except ValueError as exc:
        rec["reason"] = str(exc)
        code = 2
    finally:
        if _sig(Path.home()) != before:
            rec["reason"] = "real HOME skills-manager paths changed"
            rec["failed"] = ["real_home_unchanged"]
            code = 1
        if scratch is not None:
            shutil.rmtree(scratch, ignore_errors=True)
    return write("skills-manager", rec, code)


if __name__ == "__main__":
    raise SystemExit(main())
