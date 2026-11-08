#!/usr/bin/env python3
"""Offline H2 probe for the pinned agent-skill-manager CLI.

Measures whether a planted SKILL.md is blocked before it is copied into a
project skills directory, and whether one clean skill lands in two provider
dirs. The child env is a redirected home under the tool cache. The cache
is $XDG_CACHE_HOME/pfy/tools/asm-agent-skill-manager, or
$HOME/.cache/pfy/tools/asm-agent-skill-manager when XDG_CACHE_HOME is unset.
No hosted model and no registry fetch.
"""

from __future__ import annotations

import hashlib
import json
import os
import pwd
import re
import shutil
import subprocess
import time
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
FIXTURES = OUT_DIR / "fixtures"


def cache_dir() -> Path:
    """Tool files under XDG_CACHE_HOME, or $HOME/.cache when that is unset."""
    xdg = os.environ.get("XDG_CACHE_HOME", "").strip()
    base = Path(xdg) if xdg else Path.home() / ".cache"
    return base / "pfy" / "tools" / "asm-agent-skill-manager"


def asm_bin() -> Path:
    override = os.environ.get("ASM_BIN", "").strip()
    if override:
        return Path(override)
    return cache_dir() / "prefix" / "node_modules" / ".bin" / "asm"


PIN_SHA256 = "78fde253af3e216098a6d471dd90341d4aace1bc839816d1080a6fc1432661dd"
CATEGORIES = ("Shell commands", "Code execution", "Credentials", "External URLs")
PLANTED_CATEGORIES = ("Shell commands", "Credentials", "External URLs")
PLANTED_TOKENS = ("bash -c", "child_process", "API_KEY=", "https://example.invalid")


def real_home() -> Path:
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def watched_paths() -> list[Path]:
    home = real_home()
    return [
        home / ".grok" / "skills",
        home / ".claude",
        home / ".codex" / "skills",
        home / ".config" / "opencode",
    ]


def snap(paths: list[Path]) -> dict[str, tuple[int, int] | None]:
    out: dict[str, tuple[int, int] | None] = {}
    for path in paths:
        if not path.exists():
            out[str(path)] = None
            continue
        st = path.stat()
        out[str(path)] = (st.st_mtime_ns, st.st_size)
    return out


def child_env() -> dict[str, str]:
    # Minimal env so a host credential is not passed through.
    root = cache_dir()
    return {
        "HOME": str(root / "home"),
        "XDG_CONFIG_HOME": str(root / "config"),
        "XDG_CACHE_HOME": str(root / "cache"),
        "TMPDIR": str(root / "tmp"),
        "npm_config_cache": str(root / "npm"),
        "npm_config_userconfig": str(root / "npmrc"),
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "CI": "1",
        "NO_COLOR": "1",
        "ASM_SKIP_POSTINSTALL": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
    }


def run(args: list[str], cwd: Path) -> tuple[int, str, str, float]:
    started = time.perf_counter()
    proc = subprocess.run(
        [str(asm_bin()), *args],
        cwd=cwd,
        env=child_env(),
        text=True,
        capture_output=True,
        timeout=60,
    )
    wall = time.perf_counter() - started
    return proc.returncode, proc.stdout, proc.stderr, wall


def last_json(text: str) -> dict | list | None:
    start = text.rfind("{")
    while start >= 0:
        try:
            value = json.loads(text[start:])
            if isinstance(value, (dict, list)):
                return value
        except json.JSONDecodeError:
            pass
        start = text.rfind("{", 0, start)
    return None


def risk_label(stderr: str) -> str:
    match = re.search(r"Risk:\s+(.+)", stderr)
    if not match:
        return ""
    line = match.group(1)
    if "High Risk" in line:
        return "high"
    if "Medium Risk" in line:
        return "medium"
    if "Safe" in line:
        return "safe"
    return line.strip()


def categories(stderr: str) -> list[str]:
    found = re.findall(r"\[([A-Za-z ]+)\]", stderr)
    seen: list[str] = []
    for name in found:
        if name in CATEGORIES and name not in seen:
            seen.append(name)
    return seen


def file_has(path: Path, token: str) -> bool:
    if not path.is_file():
        return False
    return token in path.read_text(encoding="utf-8")


def install_record(source: Path, provider: str, cwd: Path) -> dict:
    code, out, err, wall = run(
        [
            "install",
            str(source),
            "-p",
            provider,
            "-s",
            "project",
            "-y",
            "--json",
            "--no-color",
        ],
        cwd,
    )
    payload = last_json(out)
    if not isinstance(payload, dict):
        payload = {}
    raw_path = payload.get("path")
    # An empty receipt path must not become ".", or a SKILL.md in the
    # working directory would count as a landed install.
    if isinstance(raw_path, str) and raw_path:
        skill_md = Path(raw_path) / "SKILL.md"
        landed = skill_md.is_file()
        path_text = raw_path
    else:
        landed = False
        path_text = ""
    text = out + "\n" + err
    return {
        "exit": code,
        "wall_s": round(wall, 4),
        "success": payload.get("success"),
        "path": path_text,
        "landed": landed,
        "risk": risk_label(text),
        "categories": categories(text),
        "resolution_source": payload.get("resolutionSource"),
        "provider": payload.get("provider"),
    }


def main() -> int:
    root = cache_dir()
    work = root / "tmp" / "asm-probe"
    tarball = root / "agent-skill-manager-2.24.0.tgz"
    for path in (root / "home", root / "config", root / "cache", root / "tmp"):
        path.mkdir(parents=True, exist_ok=True)
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    before = snap(watched_paths())
    results: dict = {
        "asm_bin": str(asm_bin()),
        "tarball_sha256_ok": False,
        "binary_version": "",
    }
    if not asm_bin().is_file():
        results["error"] = "asm binary missing"
        (OUT_DIR / "results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        return 2
    if tarball.is_file():
        digest = hashlib.sha256(tarball.read_bytes()).hexdigest()
        results["tarball_sha256"] = digest
        results["tarball_sha256_ok"] = digest == PIN_SHA256

    code, out, err, wall = run(["--version"], work)
    version_text = (out + err).strip()
    results["binary_version_raw"] = version_text
    results["version_wall_s"] = round(wall, 4)
    results["version_exit"] = code
    match = re.search(r"v([0-9.]+)\s+\(([0-9a-f]+)\)", version_text)
    if match:
        results["binary_version"] = match.group(1)
        results["binary_commit"] = match.group(2)

    planted = FIXTURES / "planted"
    clean = FIXTURES / "clean"
    local_code, local_out, local_err, local_wall = run(
        ["audit", "security", str(planted), "--json", "--no-color"],
        work,
    )
    local_payload = last_json(local_out)
    results["local_audit_before_copy"] = {
        "exit": local_code,
        "wall_s": round(local_wall, 4),
        "scanned": isinstance(local_payload, dict) and "verdict" in local_payload,
        "stderr_tail": local_err.strip().splitlines()[-1] if local_err.strip() else "",
        "stdout_tail": local_out.strip().splitlines()[-1] if local_out.strip() else "",
    }

    planted_proj = work / "planted-proj"
    planted_proj.mkdir()
    planted_install = install_record(planted, "grok", planted_proj)
    # Same rule as landed: an empty receipt must not read a SKILL.md from cwd.
    if planted_install["landed"]:
        planted_md = Path(planted_install["path"]) / "SKILL.md"
    else:
        planted_md = None
    planted_install["planted_tokens_present"] = {
        token: planted_md is not None and file_has(planted_md, token)
        for token in PLANTED_TOKENS
    }
    # A block is a refused copy. A landed file is not a block. A missing file
    # counts only when the CLI itself exits non-zero or reports success false.
    refused = (not planted_install["landed"]) and (
        planted_install["exit"] != 0 or planted_install["success"] is False
    )
    planted_install["blocked"] = refused
    results["planted_install"] = planted_install

    audit_code, audit_out, audit_err, audit_wall = run(
        ["audit", "security", "planted", "--json", "--no-color"],
        planted_proj,
    )
    audit_payload = last_json(audit_out)
    if not isinstance(audit_payload, dict):
        audit_payload = {}
    blob = json.dumps(audit_payload)
    results["audit_after_install"] = {
        "exit": audit_code,
        "wall_s": round(audit_wall, 4),
        "verdict": audit_payload.get("verdict"),
        "total_files": audit_payload.get("totalFiles"),
        "total_lines": audit_payload.get("totalLines"),
        "verdict_reason": audit_payload.get("verdictReason"),
        "tokens_named": [token for token in PLANTED_TOKENS if token in blob or token in audit_err],
    }

    clean_proj = work / "clean-proj"
    clean_proj.mkdir()
    grok = install_record(clean, "grok", clean_proj)
    opencode = install_record(clean, "opencode", clean_proj)
    results["clean_installs"] = {"grok": grok, "opencode": opencode}
    landed_providers = sum(1 for row in (grok, opencode) if row["landed"])
    safe_providers = sum(1 for row in (grok, opencode) if row["landed"] and row["risk"] == "safe")
    results["providers_landed"] = f"{landed_providers}/2"
    results["clean_safe"] = f"{safe_providers}/2"
    preview_named = sum(1 for name in PLANTED_CATEGORIES if name in planted_install["categories"])
    results["preview_categories"] = f"{preview_named}/3"
    if planted_install["landed"] and planted_install["risk"] == "high":
        results["high_risk_blocked"] = "0/1"
    elif planted_install["blocked"]:
        results["high_risk_blocked"] = "1/1"
    else:
        results["high_risk_blocked"] = "unknown"
    audit_named = len(results["audit_after_install"]["tokens_named"])
    results["audit_tokens"] = f"{audit_named}/4"

    after = snap(watched_paths())
    results["real_homes_unchanged"] = before == after
    (OUT_DIR / "results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    if not results["real_homes_unchanged"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
