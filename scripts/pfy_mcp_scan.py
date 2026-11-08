#!/usr/bin/env python3
"""Advisory install check for package exposure and MCP host configs.

Exit 0 when the scanner reports no findings and the local MCP pass is clean.
Exit 1 when a package finding, a git-selector server, or a secret-like env key is present.
Exit 2 when the root is refused, a config or the scanner output is unreadable, or the
binary is missing. Local advisories are still printed when the binary is missing.

The root is required. $HOME and the real home config directories are refused.
Pass an explicit fixture or worktree path. Env values are never printed. If the
scanner echoes one, stdout and the receipt replace it with [redacted].

Binary lookup: PFY_BUMBLEBEE_BIN, then PATH, then
~/.cache/pfy/tools/bumblebee/bumblebee. A set but unusable PFY_BUMBLEBEE_BIN
does not fall through. The child gets a scratch HOME, not the caller HOME.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

MCP_NAMES = {
    "mcp.json",
    ".mcp.json",
    "claude_desktop_config.json",
    "mcp_config.json",
    "mcp_settings.json",
    "cline_mcp_settings.json",
    "claude.json",
}
SKIP_DIRS = {".git", "node_modules", "__pycache__"}
SECRET_TOP = {".grok", ".claude", ".codex", ".config", ".local"}
MAX_MCP_BYTES = 1_000_000
GIT_MARKERS = ("github:", "gitlab:", "git+", "git@", "git://")
SECRET_KEY_PARTS = ("token", "secret", "password", "passwd", "credential", "private_key", "api_key", "apikey")


def cache_executable() -> Path | None:
    home = os.environ.get("HOME") or str(Path.home())
    root = os.environ.get("PFY_TOOL_CACHE") or str(Path(home) / ".cache" / "pfy")
    path = Path(root) / "tools" / "bumblebee" / "bumblebee"
    if path.is_file() and os.access(path, os.X_OK):
        return path
    return None


def find_binary() -> Path | None:
    """PFY_BUMBLEBEE_BIN wins. A set but unusable value does not fall through."""
    if "PFY_BUMBLEBEE_BIN" in os.environ:
        path = Path(os.environ["PFY_BUMBLEBEE_BIN"])
        if path.is_file() and os.access(path, os.X_OK):
            return path
        return None
    found = shutil.which("bumblebee")
    if found:
        return Path(found)
    return cache_executable()


def caller_home() -> Path:
    return Path(os.environ.get("HOME") or str(Path.home())).expanduser().resolve()


def refuse_reason(root: Path) -> str | None:
    home = caller_home()
    if root == home:
        return "refusing to scan $HOME; pass an explicit fixture or worktree path"
    try:
        rel = root.relative_to(home)
    except ValueError:
        return None
    if rel.parts and rel.parts[0] in SECRET_TOP:
        return (
            "refusing to scan a home config directory (%s); pass an explicit fixture path"
            % rel.parts[0]
        )
    return None


def secret_key(name: str) -> bool:
    lowered = name.lower()
    if any(part in lowered for part in SECRET_KEY_PARTS):
        return True
    return lowered == "auth" or lowered.startswith("auth_") or lowered.endswith("_auth")


def git_selector(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in GIT_MARKERS)


def display_source(root: Path, raw: str) -> str:
    if not raw:
        return ""
    path = Path(raw)
    if path.is_absolute():
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            return path.name
    return path.as_posix()


def iter_mcp_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        kept = []
        for name in dirnames:
            child = Path(dirpath) / name
            if name in SKIP_DIRS or child.is_symlink():
                continue
            kept.append(name)
        dirnames[:] = kept
        for name in filenames:
            path = Path(dirpath) / name
            if path.is_symlink():
                continue
            if name in MCP_NAMES or (name == "settings.json" and path.parent.name == ".gemini"):
                yield path


def server_items(doc: dict) -> list[tuple[str, dict]]:
    for key in ("mcpServers", "servers"):
        block = doc.get(key)
        if isinstance(block, dict):
            return [(str(name), item) for name, item in block.items() if isinstance(item, dict)]
    found = []
    for name, item in doc.items():
        if not isinstance(item, dict):
            continue
        if any(field in item for field in ("command", "url", "args", "type")):
            found.append((str(name), item))
    return found


def command_bits(item: dict) -> list[str]:
    bits = []
    for field in ("command", "url"):
        value = item.get(field)
        if isinstance(value, str):
            bits.append(value)
    args = item.get("args")
    if isinstance(args, list):
        bits.extend(value for value in args if isinstance(value, str))
    return bits


def read_mcp(path: Path) -> tuple[dict | None, str | None]:
    """Return (doc, error). The error is a fixed phrase and never includes file bytes."""
    try:
        if path.stat().st_size > MAX_MCP_BYTES:
            return None, "mcp config is larger than 1MB"
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None, "mcp config is not readable"
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None, "mcp config is not readable json"
    if not isinstance(data, dict):
        return {}, None
    return data, None


def local_advisories(root: Path) -> tuple[list[dict], list[str], str | None]:
    """Findings, secret values to redact, and a fixed error phrase."""
    findings = []
    secrets: list[str] = []
    errors: list[str] = []
    for path in iter_mcp_files(root):
        doc, error = read_mcp(path)
        source = display_source(root, str(path))
        if error:
            errors.append("%s (%s)" % (error, source))
            continue
        for server, item in server_items(doc or {}):
            if any(git_selector(bit) for bit in command_bits(item)):
                findings.append({
                    "kind": "git-selector",
                    "server": server,
                    "source": source,
                })
            env = item.get("env")
            if not isinstance(env, dict):
                continue
            for key, value in env.items():
                if not isinstance(key, str) or not secret_key(key):
                    continue
                if not isinstance(value, str) or not value.strip():
                    continue
                findings.append({
                    "kind": "plaintext-env",
                    "server": server,
                    "key": key,
                    "source": source,
                })
                if len(value) >= 8:
                    secrets.append(value)
    return findings, secrets, errors[0] if errors else None


def package_findings(root: Path, rows: list[dict]) -> list[dict]:
    found = []
    for row in rows:
        if not isinstance(row, dict) or row.get("record_type") != "finding":
            continue
        item = {
            "kind": "package-exposure",
            "package": str(row.get("package_name") or ""),
            "version": str(row.get("version") or ""),
            "severity": str(row.get("severity") or ""),
            "catalog_id": str(row.get("catalog_id") or ""),
            "source": display_source(root, str(row.get("source_file") or "")),
        }
        found.append(item)
    return found


def parse_ndjson(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        if not isinstance(data, dict):
            raise json.JSONDecodeError("record is not an object", line, 0)
        rows.append(data)
    return rows


def redact(text: str, secrets: list[str]) -> str:
    for secret in sorted({item for item in secrets if len(item) >= 8}, key=len, reverse=True):
        text = text.replace(secret, "[redacted]")
    return text


def sort_findings(findings: list[dict]) -> list[dict]:
    return sorted(
        findings,
        key=lambda row: (
            row.get("kind", ""),
            row.get("source", ""),
            row.get("server", ""),
            row.get("package", ""),
            row.get("key", ""),
            row.get("version", ""),
        ),
    )


def flag_line(row: dict) -> str:
    parts = ["FLAG", row.get("kind", "finding")]
    for key in ("server", "package", "version", "severity", "catalog_id", "key", "source"):
        value = row.get(key)
        if value:
            parts.append("%s=%s" % (key, value))
    return " ".join(parts)


def write_receipt(path: str, payload: dict, secrets: list[str]) -> None:
    if not path:
        return
    text = redact(json.dumps(payload, indent=2) + "\n", secrets)
    dest = Path(path)
    dest.write_text(text, encoding="utf-8")


def finish(code: int, lines: list[str], secrets: list[str], out: str, payload: dict) -> int:
    rendered = [redact(line, secrets) for line in lines]
    try:
        write_receipt(out, payload, secrets)
    except OSError:
        rendered.append("ERROR receipt was not written")
        rendered.append("Next: pass a writable --out file, or omit --out")
        print("\n".join(rendered))
        return 2
    print("\n".join(rendered))
    return code


def run_scanner(binary: Path, root: Path, catalog: str) -> tuple[list[dict] | None, str]:
    """Return (rows, error). rows is None when the scanner output cannot be used.

    The child HOME is a scratch directory that disappears with the scan, so a
    scanner bug cannot read or write the caller home.
    """
    with tempfile.TemporaryDirectory(prefix="pfy-mcp-scan-") as tmp:
        base = Path(tmp)
        for name in ("home", "config", "cache", "data", "tmp", "npm"):
            (base / name).mkdir()
        ndjson = base / "scan.ndjson"
        env = dict(os.environ)
        env["HOME"] = str(base / "home")
        env["XDG_CONFIG_HOME"] = str(base / "config")
        env["XDG_CACHE_HOME"] = str(base / "cache")
        env["XDG_DATA_HOME"] = str(base / "data")
        env["TMPDIR"] = str(base / "tmp")
        env["npm_config_cache"] = str(base / "npm")
        cmd = [
            str(binary),
            "scan",
            "--profile",
            "deep",
            "--root",
            str(root),
            "--output",
            "file",
            "--output-file",
            str(ndjson),
        ]
        if catalog:
            cmd.extend(["--exposure-catalog", catalog])
        try:
            proc = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None, "bumblebee did not finish"
        raw = ndjson.read_text(encoding="utf-8") if ndjson.is_file() else ""
        if not raw.strip():
            if proc.returncode != 0:
                return None, "bumblebee exited %s with no records" % proc.returncode
            return [], ""
        try:
            return parse_ndjson(raw), ""
        except json.JSONDecodeError:
            return None, "bumblebee output is not ndjson"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pfy_mcp_scan")
    parser.add_argument("--root", required=True, help="explicit fixture or worktree directory")
    parser.add_argument("--catalog", default="", help="bumblebee exposure catalog file or directory")
    parser.add_argument("--out", default="", help="receipt JSON path")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser()
    try:
        root = root.resolve()
    except OSError:
        root = root.absolute()
    if not root.is_dir():
        return finish(
            2,
            ["ERROR root is not a directory", "Next: pass an explicit fixture or worktree directory"],
            [],
            args.out,
            {"verdict": "ERROR", "root": str(root), "findings": []},
        )
    reason = refuse_reason(root)
    if reason:
        return finish(
            2,
            ["ERROR " + reason, "Next: pass an explicit fixture or worktree path that is not $HOME"],
            [],
            args.out,
            {"verdict": "ERROR", "root": str(root), "findings": []},
        )

    findings, secrets, parse_error = local_advisories(root)
    if parse_error:
        lines = [flag_line(row) for row in sort_findings(findings)]
        lines.append("ERROR " + parse_error)
        lines.append("Next: fix the MCP JSON, then run the scan again")
        return finish(
            2,
            lines,
            secrets,
            args.out,
            {"verdict": "ERROR", "root": str(root), "findings": sort_findings(findings)},
        )

    catalog = str(args.catalog or "").strip()
    if catalog and not Path(catalog).expanduser().exists():
        return finish(
            2,
            ["ERROR exposure catalog is missing", "Next: pass --catalog that exists, or omit it"],
            secrets,
            args.out,
            {"verdict": "ERROR", "root": str(root), "findings": sort_findings(findings)},
        )

    binary = find_binary()
    if binary is None:
        lines = [flag_line(row) for row in sort_findings(findings)]
        lines.append("ERROR bumblebee is missing")
        lines.append(
            "Next: set PFY_BUMBLEBEE_BIN or install the pinned binary at "
            "~/.cache/pfy/tools/bumblebee/bumblebee"
        )
        return finish(
            2,
            lines,
            secrets,
            args.out,
            {"verdict": "ERROR", "root": str(root), "findings": sort_findings(findings)},
        )

    rows, scan_error = run_scanner(binary, root, catalog)
    if rows is None:
        lines = [flag_line(row) for row in sort_findings(findings)]
        lines.append("ERROR " + scan_error)
        lines.append("Next: rerun with a readable bumblebee, or set PFY_BUMBLEBEE_BIN")
        return finish(
            2,
            lines,
            secrets,
            args.out,
            {"verdict": "ERROR", "root": str(root), "findings": sort_findings(findings)},
        )

    findings.extend(package_findings(root, rows))
    findings = sort_findings(findings)
    if findings:
        lines = [flag_line(row) for row in findings]
        lines.append("FLAGGED %s" % len(findings))
        verdict = "FLAGGED"
        code = 1
    else:
        lines = ["CLEAN root=%s findings=0" % root]
        verdict = "CLEAN"
        code = 0
    return finish(
        code,
        lines,
        secrets,
        args.out,
        {"verdict": verdict, "root": str(root), "findings": findings},
    )


if __name__ == "__main__":
    raise SystemExit(main())
