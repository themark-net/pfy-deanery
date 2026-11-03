#!/usr/bin/env python3
"""Operate-or-FAIL smoke for X intake Entry 156 (SysKnife). Uses smoke.py helpers.

Usage: python3 examples/x-intake-local/smoke_156.py

Exit 0 = --version, --help, and --dry-run of a typed plan all completed, and nothing ran.
Exit 1 = the binary ran but a check failed (including a real-HOME write).
Exit 2 = can't run here. No staged binary and no cargo, a bad timeout, no bubblewrap
for the dry-run, the planner or daemon is unreachable, or the time box fired.

Receipt: $PFY_SMOKE_RECEIPT_DIR/sysknife/latest.json, else pipelines/smoke/sysknife/latest.json.
Does not download a release binary, does not pass --yes or --dangerously-skip-approval,
and does not use root. A build runs only when cargo and a pinned clone are already staged.
That build keeps CARGO_HOME and the target directory under this worktree's tmp/.
"""
from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from smoke import find_bin, pinned, run_isolated, timeout_reason, write

PIN_COMMIT = "1b3aab98b878128a267368cd47b51c921cd31219"
PIN_VERSION = "0.30.0"
WATCHED = (".sysknife", ".config/sysknife", ".local/share/sysknife", ".local/bin/sysknife")
BANNED = ("--yes", "--dangerously-skip-approval")


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


def _explicit(env_name: str, tmp_rel: str, name: str) -> tuple[str | None, str | None]:
    """(path, error). A set env var that is not executable does not fall through to PATH."""
    if env_name in os.environ:
        path = os.environ[env_name]
        if _executable(path):
            return path, None
        return None, f"{env_name} is not an executable file ({path})"
    return find_bin(env_name, tmp_rel, name), None


def _sig(home: Path) -> dict:
    out = {}
    for rel in WATCHED:
        path = home / rel
        if path.is_symlink():
            out[rel] = ("symlink", os.readlink(path))
        elif path.is_dir():
            files = sorted(
                (str(item.relative_to(path)), item.stat().st_size)
                for item in path.rglob("*")
                if item.is_file() and not item.is_symlink()
            )
            out[rel] = ("dir", files)
        elif path.exists():
            out[rel] = ("file", path.stat().st_size)
        else:
            out[rel] = None
    return out


def _call(cmd: list[str], home: str, timeout: float, scratch: str) -> subprocess.CompletedProcess | str | OSError:
    try:
        return run_isolated(
            cmd, home=home, cwd=scratch, timeout=timeout, bwrap_writable=[scratch], kill_on_exit=True,
        )
    except subprocess.TimeoutExpired:
        return "timeout"
    except OSError as exc:
        return exc


def _text(proc: subprocess.CompletedProcess) -> str:
    return (proc.stdout or "") + "\n" + (proc.stderr or "")


def _build(cargo: str, repo: Path, commit: str, scratch: Path, timeout: float, rec: dict) -> str | int:
    if not (repo / "Cargo.toml").is_file() or not (repo / ".git").is_dir():
        rec["reason"] = f"pinned sysknife clone is not staged at {repo}"
        return 2
    home = str(scratch / "home")
    rev = _call(["git", "-C", str(repo), "rev-parse", "HEAD"], home, min(timeout, 30), str(scratch))
    if rev == "timeout":
        rec["reason"] = timeout_reason("sysknife rev-parse", min(timeout, 30))
        return 2
    if isinstance(rev, OSError):
        rec["reason"] = f"git rev-parse failed: {rev}"
        return 2
    got = (rev.stdout or "").strip().lower()
    if rev.returncode != 0 or got != commit:
        rec["reason"] = f"sysknife clone is {got or 'unreadable'}, pin is {commit}"
        return 2
    target = scratch / "target"
    cargo_home = scratch / "cargo-home"
    cmd = [
        cargo, "build", "-p", "sysknife-cli", "--bin", "sysknife", "--locked",
        "--manifest-path", str(repo / "Cargo.toml"),
    ]
    try:
        built = run_isolated(
            cmd, home=home, cwd=str(scratch), timeout=timeout, kill_on_exit=True,
            path=os.path.dirname(cargo) + ":/usr/bin:/bin",
            extra={"CARGO_HOME": str(cargo_home), "CARGO_TARGET_DIR": str(target)},
            bwrap_writable=None,
        )
    except subprocess.TimeoutExpired:
        rec["reason"] = timeout_reason("sysknife cargo build", timeout)
        return 2
    except OSError as exc:
        rec["reason"] = f"cargo failed to start: {exc}"
        return 2
    binary = target / "debug" / "sysknife"
    rec["checks"]["cargo_build"] = built.returncode
    if built.returncode != 0 or not _executable(str(binary)):
        rec["reason"] = "cargo build did not produce sysknife within the time box: " + _text(built)[-400:]
        return 2
    return str(binary)


def body(rec: dict, scratch: Path | None) -> tuple[int, Path | None]:
    commit = pinned(rec, "SYSKNIFE_COMMIT", PIN_COMMIT, lower=True)
    version = pinned(rec, "SYSKNIFE_VERSION", PIN_VERSION)
    timeout = _limit(120)
    binary, err = _explicit("SYSKNIFE_BIN", "sysknife/sysknife", "sysknife")
    if err:
        rec["reason"] = err
        return 2, scratch
    if binary is None:
        cargo, cargo_err = _explicit("CARGO_BIN", "cargo/bin/cargo", "cargo")
        if cargo_err:
            rec["reason"] = cargo_err
            return 2, scratch
        if not cargo:
            rec["reason"] = (
                "sysknife is not staged and cargo is not available; "
                "not downloading a release binary and not building"
            )
            return 2, scratch
        scratch = Path(tempfile.mkdtemp(prefix="sysknife-", dir=_scratch_root()))
        repo = Path(os.environ["SYSKNIFE_DIR"]) if os.environ.get("SYSKNIFE_DIR") else (
            Path.home() / "DEVELOP/pfy-mentat/tmp/sysknife"
        )
        built = _build(cargo, repo, commit, scratch, timeout, rec)
        if isinstance(built, int):
            return built, scratch
        binary = built
    if scratch is None:
        scratch = Path(tempfile.mkdtemp(prefix="sysknife-", dir=_scratch_root()))
    home = scratch / "home"
    home.mkdir(parents=True, exist_ok=True)
    home_s = str(home)
    scratch_s = str(scratch)
    version_proc = _call([binary, "--version"], home_s, timeout, scratch_s)
    if version_proc == "timeout":
        rec["reason"] = timeout_reason("sysknife --version", timeout)
        return 2, scratch
    if isinstance(version_proc, OSError):
        rec["reason"] = f"sysknife failed to start: {version_proc}"
        return 2, scratch
    if version_proc.returncode != 0 or version not in _text(version_proc):
        rec["reason"] = f"version pin {version} not in sysknife --version output"
        rec["output"] = _text(version_proc)[-400:]
        return 2, scratch
    help_proc = _call([binary, "--help"], home_s, timeout, scratch_s)
    if help_proc == "timeout":
        rec["reason"] = timeout_reason("sysknife --help", timeout)
        return 2, scratch
    if isinstance(help_proc, OSError) or help_proc.returncode != 0 or "--dry-run" not in _text(help_proc):
        rec["reason"] = "sysknife --help did not show --dry-run"
        rec["failed"] = ["help"]
        return 1, scratch
    if shutil.which("bwrap") is None:
        rec["reason"] = (
            "sysknife --help ok; --dry-run skipped because bubblewrap is unavailable, "
            "so the planner would not be network-isolated. No system change."
        )
        return 2, scratch
    secs = str(int(max(1, min(timeout, 20))))
    args = ["--dry-run", "--non-interactive", "--json", "--timeout", secs, "check", "disk", "usage"]
    if any(flag in args for flag in BANNED):
        rec["reason"] = "smoke refused to arm execution flags"
        return 1, scratch
    rec["dry_run_argv"] = args
    dry = _call([binary, *args], home_s, timeout, scratch_s)
    if dry == "timeout":
        rec["reason"] = timeout_reason("sysknife --dry-run", timeout)
        return 2, scratch
    if isinstance(dry, OSError):
        rec["reason"] = f"sysknife --dry-run failed to start: {dry}"
        return 2, scratch
    out = _text(dry)
    rec["checks"]["dry_run_exit"] = dry.returncode
    if dry.returncode != 0:
        rec["reason"] = (
            "sysknife --help ok; --dry-run did not return a plan "
            "(planner, daemon, or usage). No --yes and no system change. " + out[-400:]
        )
        return 2, scratch
    if "action" not in out and "dry_run" not in out and "dry-run" not in out.lower():
        rec["reason"] = "sysknife --dry-run exited 0 without a typed plan"
        rec["failed"] = ["dry_run_plan"]
        return 1, scratch
    rec["checks"]["dry_run"] = "plan"
    return 0, scratch


def _scratch_root() -> str:
    root = Path(__file__).resolve().parents[2] / "tmp" / "xintake-156"
    root.mkdir(parents=True, exist_ok=True)
    return str(root)


def main() -> int:
    rec: dict = {"entry": "156-sysknife", "failed": [], "checks": {}}
    before = _sig(Path.home())
    scratch: Path | None = None
    code = 1
    try:
        code, scratch = body(rec, scratch)
    except ValueError as exc:
        rec["reason"] = str(exc)
        code = 2
    finally:
        if _sig(Path.home()) != before:
            rec["reason"] = "real HOME sysknife paths changed"
            rec["failed"] = ["real_home_unchanged"]
            code = 1
        if scratch is not None:
            shutil.rmtree(scratch, ignore_errors=True)
    return write("sysknife", rec, code)


if __name__ == "__main__":
    raise SystemExit(main())
