"""Phase 2 first slice: plan `pfy launch <harness> --model ollama:<tag>`.

Delegates to `ollama launch` when that subcommand exists. Otherwise it only
sets child-process env. It never writes model or base-URL into harness config
and never prompts for a paid key. Claude Code and Codex only accept a local
source (`ollama:<tag>` in this slice).
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

LOCAL_SOURCES = ("ollama:", "llamacpp:")
PAID_HARNESSES = frozenset({"claude-code", "codex"})
HARNESS_BIN = {"claude-code": "claude", "codex": "codex", "opencode": "opencode", "grok": "grok"}
# This slice implements the ollama: path for Claude Code. Codex is accepted
# only far enough to refuse a paid source.


@dataclass
class LaunchPlan:
    harness: str
    model: str
    argv: list[str]
    env: dict[str, str]
    dry_run: bool
    delegate: str = ""
    next_step: str = ""
    reason: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "harness": self.harness,
            "model": self.model,
            "argv": list(self.argv),
            "env": dict(self.env),
            "dry_run": self.dry_run,
            "delegate": self.delegate,
            "next_step": self.next_step,
            "reason": self.reason,
        }


class LaunchError(Exception):
    def __init__(self, reason: str, next_step: str = "", code: int = 1, extra: dict | None = None):
        super().__init__(reason)
        self.reason = reason
        self.next_step = next_step
        self.code = code
        self.extra = extra or {}

    def to_json(self) -> dict[str, Any]:
        rec = {"ok": False, "reason": self.reason, "next_step": self.next_step}
        rec.update(self.extra)
        return rec


def ollama_host() -> str:
    raw = (os.environ.get("OLLAMA_HOST") or "127.0.0.1:11434").strip()
    if "://" not in raw:
        raw = "http://" + raw
    return raw.rstrip("/")


def _ollama_tags_url() -> str:
    return ollama_host() + "/api/tags"


def ollama_is_up(timeout: float = 0.4) -> bool:
    url = _ollama_tags_url()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= int(getattr(resp, "status", 200)) < 300
    except (urllib.error.URLError, socket.timeout, TimeoutError, OSError, ValueError):
        return False


def ollama_launch_available() -> bool:
    binary = shutil.which("ollama")
    if not binary:
        return False
    import subprocess

    try:
        proc = subprocess.run(
            [binary, "launch", "--help"],
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return proc.returncode == 0


def parse_model(spec: str) -> tuple[str, str]:
    text = (spec or "").strip()
    if not text:
        raise LaunchError("missing --model", next_step="pass --model ollama:<tag>")
    if ":" not in text:
        raise LaunchError(
            "paid source refused: Claude Code and Codex only take a local ollama:<tag> model",
            next_step="use --model ollama:<tag> (for example ollama:qwen3.6:35b)",
        )
    kind, rest = text.split(":", 1)
    return kind, rest


def refuse_paid(harness: str, spec: str) -> None:
    kind, rest = parse_model(spec)
    if kind in ("ollama", "llamacpp"):
        if kind == "ollama" and not rest.strip():
            raise LaunchError("missing ollama tag", next_step="pass --model ollama:<tag>")
        if kind == "llamacpp":
            raise LaunchError(
                "llamacpp:<alias> is not in this Phase 2 slice",
                next_step="use --model ollama:<tag> for now",
                code=3,
            )
        return
    raise LaunchError(
            "paid source refused: Claude Code and Codex only take a local ollama:<tag> model",
            next_step="use --model ollama:<tag> (for example ollama:qwen3.6:35b)",
        )


def _anthropic_base() -> str:
    host = ollama_host()
    parsed = urlparse(host)
    if parsed.path in ("", "/"):
        return host
    return f"{parsed.scheme}://{parsed.netloc}"


def plan_launch(harness: str, model: str, *, dry_run: bool, passthrough: list[str] | None = None) -> LaunchPlan:
    hid = (harness or "").strip()
    if hid not in HARNESS_BIN and hid not in PAID_HARNESSES:
        raise LaunchError(
            f"unknown harness {hid!r}",
            next_step="use claude-code (this slice) or a reserved ./pfy launch wizard subcommand",
            code=2,
        )
    refuse_paid(hid, model)
    kind, tag = parse_model(model)
    if hid != "claude-code":
        # Paid refuse already ran. Remaining Codex/OpenCode/Grok exec is a later slice.
        raise LaunchError(
            f"{hid} launch beyond paid-source refusal is not in this Phase 2 slice",
            next_step="use: pfy launch claude-code --model ollama:<tag> --yes --dry-run --json",
            code=3,
        )
    if kind != "ollama":
        raise LaunchError(
            "claude-code only accepts ollama:<tag> in this slice",
            next_step="use --model ollama:<tag>",
        )
    if not ollama_is_up():
        raise LaunchError(
            "Ollama is down; pfy launch needs a running local daemon",
            next_step="ollama serve",
        )
    extra = list(passthrough or [])
    if ollama_launch_available():
        argv = ["ollama", "launch", "claude-code", "--model", tag, *extra]
        return LaunchPlan(
            harness=hid,
            model=model,
            argv=argv,
            env={},
            dry_run=dry_run,
            delegate="ollama launch",
        )
    binary = HARNESS_BIN[hid]
    env = {
        "ANTHROPIC_BASE_URL": _anthropic_base(),
        "ANTHROPIC_AUTH_TOKEN": "ollama",
    }
    return LaunchPlan(
        harness=hid,
        model=model,
        argv=[binary, *extra],
        env=env,
        dry_run=dry_run,
        delegate="",
    )


def emit(obj: dict, as_json: bool, stream=None) -> None:
    import sys

    out = stream or sys.stdout
    if as_json:
        print(json.dumps(obj, sort_keys=False), file=out)
        return
    if obj.get("reason"):
        print(obj["reason"], file=out)
    if obj.get("next_step"):
        print("next: " + str(obj["next_step"]), file=out)
    if obj.get("argv"):
        print("argv: " + " ".join(str(a) for a in obj["argv"]), file=out)


def cmd_launch(args: Any) -> int:
    as_json = bool(getattr(args, "json", False))
    try:
        plan = plan_launch(
            args.harness,
            args.model or "",
            dry_run=bool(getattr(args, "dry_run", False)),
            passthrough=list(getattr(args, "passthrough", None) or []),
        )
    except LaunchError as exc:
        emit(exc.to_json(), as_json)
        if not as_json:
            import sys

            print(exc.reason, file=sys.stderr)
            if exc.next_step:
                print("next: " + exc.next_step, file=sys.stderr)
        return int(exc.code)
    emit(plan.to_json(), as_json)
    if plan.dry_run:
        return 0
    if not getattr(args, "yes", False):
        emit(
            {"ok": False, "reason": "refusing to exec without --yes", "next_step": "re-run with --yes or --dry-run"},
            as_json,
        )
        return 1
    # Exec is a later slice plus the gated live smoke. This slice is dry-run first.
    raise LaunchError(
        "live exec is not in this Phase 2 slice",
        next_step="use --dry-run --json, or wait for the gated live-smoke slice",
        code=3,
    )
