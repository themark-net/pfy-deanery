#!/usr/bin/env python3
"""One bake-off task via `opencode run` against the shared MCP server.

Config, cache, and state stay under ./tmp. This does not read or write
~/.config/opencode. The scored driver name is `opencode run`.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from schema import server_name

HERE = Path(__file__).resolve().parent


def _normalize(name: str) -> str:
    """Map opencode's bakeoff_<tool> name back to the server tool name."""
    short = server_name(name or "")
    if short.startswith("bakeoff_"):
        short = short[len("bakeoff_") :]
    return short


def _write_config(config_home: Path, model: str, base_url: str, num_ctx: int, log_path: Path, task_id: str) -> None:
    python = os.environ.get("BAKEOFF_PYTHON") or sys.executable
    server = str(HERE / "mcp_server.py")
    config_home.mkdir(parents=True, exist_ok=True)
    body = {
        "$schema": "https://opencode.ai/config.json",
        "model": f"ollama/{model}",
        "provider": {
            "ollama": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "Ollama",
                "options": {"baseURL": base_url, "apiKey": "no-key"},
                "models": {
                    model: {
                        "name": model,
                        "limit": {"context": int(num_ctx), "output": 2048},
                    }
                },
            }
        },
        "mcp": {
            "bakeoff": {
                "type": "local",
                "command": [python, server, "--log", str(log_path), "--task-id", task_id],
                "enabled": True,
            }
        },
        "permission": {"bash": "deny", "edit": "deny", "webfetch": "deny", "read": "deny"},
    }
    dest = config_home / "opencode" / "opencode.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def _parse_events(text: str) -> tuple[str, list[dict]]:
    chunks: list[str] = []
    calls: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        part = event.get("part") if isinstance(event.get("part"), dict) else event
        if not isinstance(part, dict):
            continue
        if part.get("type") == "text" and isinstance(part.get("text"), str):
            chunks.append(part["text"])
        if part.get("type") == "tool" or event.get("type") == "tool_use":
            raw_name = part.get("tool") or part.get("name") or ""
            state = part.get("state") if isinstance(part.get("state"), dict) else {}
            args = state.get("input") if isinstance(state.get("input"), dict) else {}
            calls.append(
                {
                    "name": _normalize(str(raw_name)),
                    "wire_name": raw_name,
                    "arguments": args,
                }
            )
    final = chunks[-1] if chunks else ""
    return final, calls


def run_task(task: dict, system: str, model: str, base_url: str, num_ctx: int, log_path: Path, out_path: Path) -> dict:
    binary = shutil.which("opencode") or str(Path.home() / ".local" / "bin" / "opencode")
    if not Path(binary).exists():
        return {
            "ok": False,
            "final_text": "",
            "assistant_text": "",
            "client_calls": [],
            "error": "FAIL: opencode binary missing",
            "driver": "opencode run",
        }
    log_path = log_path.resolve()
    out_path = out_path.resolve()
    config_home = out_path.parent / "opencode-config" / task["id"]
    data_home = Path(os.environ.get("BAKEOFF_OPENCODE_DATA") or (out_path.parent / "opencode-data"))
    cache_home = Path(os.environ.get("BAKEOFF_OPENCODE_CACHE") or (out_path.parent / "opencode-cache"))
    state_home = out_path.parent / "opencode-state" / task["id"]
    for path in (data_home, cache_home, state_home, log_path.parent):
        path.mkdir(parents=True, exist_ok=True)
    _write_config(config_home, model, base_url, num_ctx, log_path, task["id"])
    # Same rule as run.child_tmpdir: scratch stays under the repo tmp, never a
    # hardcoded /tmp that ignores the caller TMPDIR.
    from run import child_tmpdir

    home = os.environ.get("HOME") or str(Path.home())
    env = {
        "HOME": home,
        "PATH": f"{home}/.local/bin:/usr/local/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "USER": os.environ.get("USER", "mark"),
        "LOGNAME": os.environ.get("LOGNAME", "mark"),
        "TMPDIR": child_tmpdir(),
        "XDG_CONFIG_HOME": str(config_home),
        "XDG_DATA_HOME": str(data_home),
        "XDG_CACHE_HOME": str(cache_home),
        "XDG_STATE_HOME": str(state_home),
        "OPENAI_BASE_URL": base_url,
        "OPENAI_API_KEY": "no-key",
    }
    message = system + "\n\n" + task["prompt"]
    proc = subprocess.run(
        [binary, "run", "--pure", "--format", "json", "--model", f"ollama/{model}", "--auto", message],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    final, calls = _parse_events(proc.stdout or "")
    error = None
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "")[-400:]
        error = f"FAIL: opencode exit {proc.returncode} {tail}"
    return {
        "ok": error is None,
        "final_text": final,
        "assistant_text": final,
        "client_calls": calls,
        "error": error,
        "driver": "opencode run",
        "returncode": proc.returncode,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-file", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--system", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--num-ctx", type=int, required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    bundle = json.loads(Path(args.task_file).read_text(encoding="utf-8"))
    task = next(item for item in bundle["tasks"] if item["id"] == args.task_id)
    result = run_task(
        task, args.system, args.model, args.base_url, args.num_ctx, Path(args.log), out
    )
    out.write_text(json.dumps(result), encoding="utf-8")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
