#!/usr/bin/env python3
"""Operate-or-FAIL smoke for X intake Entry 161 (agentgg). Uses smoke.py helpers.

Usage: python3 examples/x-intake-local/smoke_161.py

Exit 0 = --help and --version matched the pin, and a time-boxed Ollama scan of
a tiny fixture finished. No hosted app, no API key, no --live-validate.
Exit 1 = the CLI ran but help failed, the scan ran and failed, or a real-HOME
path changed.
Exit 2 = node or npm is missing, the install cannot finish, no local Ollama
model is already running, an OpenAI-compatible port is up but would need a key,
or the timeout value is bad.

HOME and the npm cache stay under this worktree's tmp/xintake-161/. The scratch
directory is removed when the smoke exits.

Receipt: $PFY_SMOKE_RECEIPT_DIR/agentgg/latest.json, else pipelines/smoke/agentgg/latest.json.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from smoke import pinned, run_isolated, timeout_reason, write

PIN_VERSION = "0.1.29"
PIN_COMMIT = "20cca9c1896ef4fee26c93a8730c0f46e4ca44d6"
WATCHED = (".agentgg", ".npm", ".npm-global", ".grok", ".config/agentgg")
ROOT = Path(__file__).resolve().parents[2]
OLLAMA_TAGS = "http://127.0.0.1:11434/api/tags"
OPENAI_MODELS = "http://127.0.0.1:8080/v1/models"


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
                out[rel] = tuple(sorted(child.name for child in path.iterdir()))
            else:
                out[rel] = ("leaf", path.stat().st_size)
        except OSError as exc:
            out[rel] = ("error", type(exc).__name__)
    return out


def _under_worktree(path: Path) -> bool:
    try:
        resolved = path.resolve()
        resolved.relative_to((ROOT / "tmp").resolve())
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


def _local_url(raw: str) -> bool:
    return raw.startswith("http://127.0.0.1:") or raw.startswith("http://localhost:")


def _get_json(url: str, timeout: float) -> dict | None:
    if not _local_url(url):
        return None
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return None
            payload = json.loads(response.read().decode("utf-8", "replace"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _ollama(timeout: float, rec: dict) -> tuple[str, str] | int | None:
    """(base, model) when a local Ollama already has a model. 2 when a scan
    would need a key or a pull. None when nothing local is answering.
    """
    override = os.environ.get("AGENTGG_PROBE_URL", "").strip()
    if override:
        if not _local_url(override):
            rec["reason"] = "AGENTGG_PROBE_URL is not a loopback URL; hosted app not used"
            return 2
        tags_url = override.rstrip("/") + "/api/tags"
        openai_url = override.rstrip("/") + "/v1/models"
    else:
        tags_url = OLLAMA_TAGS
        openai_url = OPENAI_MODELS
    tags = _get_json(tags_url, timeout)
    if tags is not None:
        local = []
        cloud = 0
        for item in tags.get("models") or []:
            if not isinstance(item, dict) or not item.get("name"):
                continue
            name = str(item["name"])
            if item.get("remote_host") or item.get("remote_model") or name.endswith(":cloud"):
                cloud += 1
                continue
            try:
                size = int(item.get("size"))
            except (TypeError, ValueError):
                size = 2**62
            local.append((size, name))
        local.sort()
        rec["checks"]["ollama_local_models"] = [name for _size, name in local]
        rec["checks"]["ollama_cloud_skipped"] = cloud
        if not local:
            rec["reason"] = (
                "Ollama is up but no local model is installed"
                + ("; remote cloud models were skipped" if cloud else "")
                + "; not pulling one and not calling a hosted model"
            )
            return 2
        base = tags_url[: -len("/api/tags")]
        rec["checks"]["ollama_model"] = local[0][1]
        return base, local[0][1]
    models = _get_json(openai_url, timeout)
    if models is not None:
        rec["checks"]["openai_compatible"] = openai_url
        rec["reason"] = (
            "a local OpenAI-compatible endpoint answered but agentgg's openai provider "
            "needs an API key; this smoke does not set one, and --live-validate was not used"
        )
        return 2
    return None


def _install(npm: str, node: str, scratch: Path, version: str, timeout: float, rec: dict) -> str | int:
    prefix = scratch / "prefix"
    cache = scratch / "npm-cache"
    home = scratch / "home"
    tmp = scratch / "tmp"
    for directory in (prefix, cache, home, tmp):
        directory.mkdir(parents=True, exist_ok=True)
    if not all(_under_worktree(directory) for directory in (prefix, cache, home)):
        rec["reason"] = "agentgg scratch escaped the worktree tmp/"
        return 2
    npmrc = scratch / "npmrc"
    npmrc.write_text("fund=false\naudit=false\nupdate-notifier=false\n", encoding="utf-8")
    (scratch / "package.json").write_text('{"name":"pfy-xintake-161","private":true}\n', encoding="utf-8")
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
        "--prefix", str(prefix), f"agentgg@{version}",
    ]
    rec["checks"]["npm_cache"] = str(cache)
    rec["checks"]["npm_home"] = str(home)
    proc = _call(cmd, str(home), timeout, str(scratch), extra, path)
    if proc == "timeout":
        rec["reason"] = timeout_reason("agentgg npm install", timeout)
        return 2
    if isinstance(proc, OSError):
        rec["reason"] = f"npm failed to start: {proc}"
        return 2
    if proc.returncode != 0:
        rec["reason"] = "npm install failed or the network is blocked: " + _text(proc)[-400:]
        return 2
    for candidate in (prefix / "bin" / "agentgg", prefix / "node_modules" / ".bin" / "agentgg"):
        if _executable(str(candidate)):
            return str(candidate)
    rec["reason"] = "npm install finished without an agentgg binary"
    return 2


def _run(binary: str, args: list[str], scratch: Path, timeout: float, path: str, extra: dict | None = None):
    home = scratch / "home"
    home.mkdir(parents=True, exist_ok=True)
    env = {"TMPDIR": str(scratch / "tmp")}
    env.update(extra or {})
    return _call([binary, *args], str(home), timeout, str(scratch), env, path)


def _fixture(scratch: Path) -> tuple[Path, Path]:
    repo = scratch / "fixture"
    repo.mkdir()
    (repo / "demo.py").write_text("# synthetic fixture. No secret and no finding.\n", encoding="utf-8")
    agent = scratch / "agent.md"
    agent.write_text(
        "---\n"
        "slug: pfy-smoke\n"
        "name: pfy-smoke\n"
        "description: Synthetic smoke agent. The only file is a comment. Report no finding.\n"
        "where:\n"
        "  extensions:\n"
        "    - .py\n"
        "  maxTurnsPerBatch: 1\n"
        "---\n"
        "Read the seeded file. If it only holds a fixture comment, report no finding.\n",
        encoding="utf-8",
    )
    return repo, agent


def body(rec: dict, made: list[Path]) -> tuple[int, Path | None]:
    version = pinned(rec, "AGENTGG_VERSION", PIN_VERSION)
    pinned(rec, "AGENTGG_COMMIT", PIN_COMMIT, lower=True)
    command_timeout = _limit(20)
    install_timeout = command_timeout if os.environ.get("PFY_XINTAKE_TIMEOUT") else _limit(240)
    scan_timeout = command_timeout if os.environ.get("PFY_XINTAKE_TIMEOUT") else _limit(90)
    root = ROOT / "tmp" / "xintake-161"
    root.mkdir(parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix="agentgg-", dir=root))
    made.append(scratch)
    (scratch / "tmp").mkdir(exist_ok=True)
    if "AGENTGG_BIN" in os.environ:
        binary = os.environ["AGENTGG_BIN"]
        if not _executable(binary):
            rec["reason"] = f"agentgg binary is not executable ({binary})"
            return 2, scratch
        node = _tool("AGENTGG_NODE", "node") or "/usr/bin/node"
        path = (os.path.dirname(node) + ":/usr/bin:/bin") if _executable(node) else "/usr/bin:/bin"
    else:
        node = _tool("AGENTGG_NODE", "node")
        npm = _tool("AGENTGG_NPM", "npm")
        if not node:
            rec["reason"] = "node is not available; agentgg smoke cannot run"
            return 2, scratch
        if not npm:
            rec["reason"] = "npm is not available or the network install cannot start"
            return 2, scratch
        installed = _install(npm, node, scratch, version, install_timeout, rec)
        if isinstance(installed, int):
            return installed, scratch
        binary = installed
        path = ":".join([os.path.dirname(node), os.path.dirname(binary), "/usr/bin", "/bin"])
    ran = _run(binary, ["--version"], scratch, command_timeout, path)
    if ran == "timeout":
        rec["reason"] = timeout_reason("agentgg --version", command_timeout)
        return 2, scratch
    if isinstance(ran, OSError):
        rec["reason"] = f"agentgg failed to start: {ran}"
        return 2, scratch
    if ran.returncode != 0 or version not in _text(ran):
        rec["reason"] = f"version pin {version} not in agentgg --version"
        rec["output"] = _text(ran)[-400:]
        return 2, scratch
    help_proc = _run(binary, ["--help"], scratch, command_timeout, path)
    if help_proc == "timeout":
        rec["reason"] = timeout_reason("agentgg --help", command_timeout)
        return 2, scratch
    if isinstance(help_proc, OSError) or help_proc.returncode != 0 or "agentgg" not in _text(help_proc).lower():
        rec["reason"] = "agentgg --help failed"
        rec["failed"] = ["help"]
        return 1, scratch
    rec["checks"]["help"] = "ok"
    found = _ollama(min(command_timeout, 3), rec)
    if isinstance(found, int):
        return found, scratch
    if found is None:
        rec["reason"] = (
            "no local Ollama or OpenAI-compatible endpoint is already running; "
            "--help and --version succeeded; scan not run; hosted app and --live-validate not used"
        )
        rec["checks"]["scan"] = "not_run"
        return 2, scratch
    base, model = found
    repo, agent = _fixture(scratch)
    out = scratch / "out"
    scan = _run(
        binary,
        [
            "scan", str(repo), "-o", str(out),
            "--provider", "ollama", "--base-url", base, "--model", model,
            "-t", str(agent), "--no-recon", "--max-turns", "1", "--max-batches", "1",
            "--no-summary",
        ],
        scratch, scan_timeout, path,
    )
    joined = " ".join([
        "scan", str(repo), "--provider", "ollama", "--base-url", base, "--model", model,
        "-t", str(agent),
    ])
    rec["checks"]["scan_model"] = model
    if scan == "timeout":
        rec["reason"] = timeout_reason("agentgg scan", scan_timeout)
        rec["checks"]["scan"] = "timeout"
        return 2, scratch
    if isinstance(scan, OSError):
        rec["reason"] = f"agentgg scan failed to start: {scan}"
        return 2, scratch
    output = _text(scan)
    if "--live-validate" in output:
        rec["reason"] = "agentgg scan mentioned --live-validate; this smoke does not enable it"
        rec["failed"] = ["live_validate"]
        return 1, scratch
    if scan.returncode != 0:
        rec["reason"] = "agentgg scan failed: " + output[-400:]
        rec["failed"] = ["scan"]
        rec["checks"]["scan"] = "failed"
        return 1, scratch
    rec["checks"]["scan"] = "finished"
    rec["checks"]["command"] = joined
    return 0, scratch


def main() -> int:
    rec: dict = {"entry": "161-agentgg", "failed": [], "checks": {}}
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
            rec["reason"] = "real HOME agentgg paths changed"
            rec["failed"] = ["real_home_unchanged"]
            code = 1
        for path in made:
            shutil.rmtree(path, ignore_errors=True)
    return write("agentgg", rec, code)


if __name__ == "__main__":
    raise SystemExit(main())
