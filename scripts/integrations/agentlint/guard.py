#!/usr/bin/env python3
"""Optional local AgentLint scan of files a pfy build attempt changed.

The caller turns this on with --agentlint or PFY_AGENTLINT=1. This module
does not decide that. A missing binary, a crash, or a timeout warns and
allows. A parsed error denies. A warning does not deny.

The child does not receive an AgentChute license, API URL, or enable flag,
and its cache stays under the directory the caller passes. This scan does
not call login, sync, or update.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

TIMEOUT_S = 8
MAX_BYTES = 1_000_000
_DROPPED_ENV = (
    "AGENTCHUTE_LICENSE_KEY",
    "AGENTCHUTE_API_URL",
    "AGENTCHUTE_ENABLED",
    "AGENTLINT_AGENTCHUTE_CREDENTIALS_FILE",
)


def resolve_bin() -> Path | None:
    """PFY_AGENTLINT_BIN wins, including when it names a missing file."""
    raw = os.environ.get("PFY_AGENTLINT_BIN")
    if raw is not None and raw.strip() != "":
        path = Path(raw)
        if path.is_file() and os.access(path, os.X_OK):
            return path
        return None
    bundled = Path(__file__).resolve().parents[3] / "tmp" / "agentlint-venv" / "bin" / "agentlint"
    if bundled.is_file() and os.access(bundled, os.X_OK):
        return bundled
    found = shutil.which("agentlint")
    if found:
        return Path(found)
    return None


def _child_env(cache: Path, session: str) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key not in _DROPPED_ENV}
    cred = cache / "no-agentchute.json"
    cred.write_text("{}\n", encoding="utf-8")
    env["AGENTLINT_AGENTCHUTE_CREDENTIALS_FILE"] = str(cred)
    env["AGENTCHUTE_ENABLED"] = "false"
    env["AGENTLINT_CACHE_DIR"] = str(cache / "cache")
    env["AGENTLINT_HEARTBEAT_DIR"] = str(cache / "heartbeat")
    env["AGENTLINT_SESSION_ID"] = session
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _read_text(worktree: Path, rel: str) -> str | None:
    root = worktree.resolve()
    try:
        path = (root / rel).resolve()
    except OSError:
        return None
    if path != root and root not in path.parents:
        return None
    if not path.is_file():
        return None
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if size > MAX_BYTES:
        return None
    try:
        blob = path.read_bytes()
    except OSError:
        return None
    if b"\0" in blob[:8192]:
        return None
    return blob.decode("utf-8", "replace")


def _parse(stdout: str, code: int) -> tuple[str, str]:
    """Return (block_bit, warn_bit). 'run' means the process did not parse."""
    raw = (stdout or "").strip()
    if code not in (0, 1):
        return "run", ""
    if not raw or raw == "None":
        return "", ""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return "run", ""
    bits = []
    warns = []
    for item in data.get("violations") or []:
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity") or "")
        rule = str(item.get("rule_id") or "rule")
        message = str(item.get("message") or "").replace("\n", " ")
        piece = "%s: %s" % (rule, message) if message else rule
        if severity == "error" or data.get("blocked") is True and severity != "warning":
            bits.append(piece)
        elif severity == "warning":
            warns.append(piece)
    if data.get("blocked") is True and not bits:
        bits.append("blocked")
    return "; ".join(bits), "; ".join(warns)


def _unreadable_note(worktree: Path, rel: str) -> str:
    """Why a changed path was not sent. Empty when the path is simply absent."""
    root = worktree.resolve()
    try:
        path = (root / rel).resolve()
    except OSError:
        return ""
    if path != root and root not in path.parents:
        return ""
    if not path.is_file():
        return ""
    try:
        size = path.stat().st_size
    except OSError:
        return "agentlint-fallback: skipped unreadable file %s" % rel
    if size > MAX_BYTES:
        return "agentlint-fallback: skipped large file %s" % rel
    try:
        head = path.read_bytes()[:8192]
    except OSError:
        return "agentlint-fallback: skipped unreadable file %s" % rel
    if b"\0" in head:
        return "agentlint-fallback: skipped binary file %s" % rel
    return ""


def scan(worktree: Path, paths: list[str], cache_root: Path) -> tuple[str, str]:
    """Scan changed text files. (block detail, warning). Empty block allows."""
    binary = resolve_bin()
    if binary is None:
        return "", "agentlint-fallback: binary missing; check skipped"
    cache_root.mkdir(parents=True, exist_ok=True)
    blocks: list[str] = []
    warnings: list[str] = []
    try:
        for index, rel in enumerate(paths):
            text = _read_text(worktree, rel)
            if text is None:
                note = _unreadable_note(worktree, rel)
                if note:
                    warnings.append(note)
                continue
            payload = {
                "tool_name": "Write",
                "tool_input": {"file_path": rel, "content": text},
            }
            env = _child_env(cache_root, "pfy-build-%s-%d" % (os.getpid(), index))
            try:
                proc = subprocess.run(
                    [
                        str(binary),
                        "check",
                        "--adapter",
                        "generic",
                        "--event",
                        "pre_tool_use",
                        "--project-dir",
                        str(worktree),
                    ],
                    input=json.dumps(payload),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=TIMEOUT_S,
                    cwd=str(worktree),
                )
            except subprocess.TimeoutExpired:
                warnings.append("agentlint-fallback: timed out on %s; check skipped for that file" % rel)
                continue
            except OSError as exc:
                warnings.append("agentlint-fallback: could not run on %s (%s)" % (rel, exc.strerror or "os error"))
                continue
            block, warn = _parse(proc.stdout or "", proc.returncode)
            if block == "run":
                warnings.append("agentlint-fallback: agentlint failed on %s; check skipped for that file" % rel)
                continue
            if block:
                blocks.append("%s [%s]" % (block, rel))
            if warn:
                warnings.append("agentlint warning: %s [%s]" % (warn, rel))
    finally:
        shutil.rmtree(cache_root, ignore_errors=True)
    detail = "; ".join(blocks)
    if len(detail) > 400:
        detail = detail[:397] + "..."
    return detail, "\n".join(warnings)
