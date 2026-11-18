"""Phase 2: plan `pfy launch <harness> --model ollama:<tag>|llamacpp:<alias>`.

Delegates to `ollama launch` when that subcommand exists. llamacpp sources
use the ADR-0014 spine and, for Claude Code, the local LiteLLM gateway.
Grok is a subscription exec with no model rewiring. A TTY picker offers a
local default of qwen3.6:35b and shows cloud estimates or a subscription
label before a choice is accepted. Child-process env only: this never
writes model or base-URL into harness config and never prompts for a paid
vendor key. Claude Code and Codex only accept a local source.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO
from urllib.parse import urlparse

LOCAL_DEFAULT = "ollama:qwen3.6:35b"
HARNESS_BIN = {"claude-code": "claude", "codex": "codex", "opencode": "opencode", "grok": "grok"}
DEFAULT_LITELLM = "http://127.0.0.1:4000"
# Shown-before-choose estimate only; local price table, no live fetch.
ESTIMATE_PROMPT_TOKENS = 2000
ESTIMATE_COMPLETION_TOKENS = 500
SPINE_NEXT = "start llama-swap or llama-server"
LITELLM_NEXT = "start the local LiteLLM gateway (config/litellm/local-only.yaml)"


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


@dataclass
class MenuOption:
    key: str
    kind: str  # local | cloud | subscription
    harness: str = ""
    model: str = ""
    label: str = ""
    cost_label: str = ""
    selectable: bool = True
    reason: str = ""

    def line(self) -> str:
        mark = "" if self.selectable else "  [not selectable] "
        extra = self.cost_label or self.reason
        tail = ("  " + extra) if extra else ""
        return f"{mark}{self.key}) {self.label}{tail}"


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


def _http_ok(url: str, timeout: float = 0.4) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= int(getattr(resp, "status", 200)) < 300
    except (urllib.error.URLError, socket.timeout, TimeoutError, OSError, ValueError):
        return False


def _normalize_host(raw: str, default: str) -> str:
    text = (raw or default).strip() or default
    if "://" not in text:
        text = "http://" + text
    return text.rstrip("/")


def ollama_host() -> str:
    return _normalize_host(os.environ.get("OLLAMA_HOST") or "", "127.0.0.1:11434")


def ollama_is_up(timeout: float = 0.4) -> bool:
    base = ollama_host()
    return _http_ok(base + "/api/tags", timeout=timeout) or _http_ok(base + "/v1/models", timeout=timeout)


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


def litellm_host() -> str:
    for key in ("LITELLM_BASE_URL", "LITELLM_PROXY_API_BASE"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            return _normalize_host(raw, DEFAULT_LITELLM)
    return DEFAULT_LITELLM


def _strip_v1(url: str) -> str:
    text = url.rstrip("/")
    if text.endswith("/v1"):
        return text[: -len("/v1")]
    return text


def litellm_is_up(timeout: float = 0.4) -> bool:
    base = litellm_host()
    root = _strip_v1(base)
    return any(
        _http_ok(u, timeout=timeout)
        for u in (base + "/models", root + "/v1/models", root + "/models", root + "/health")
    )


def llamacpp_spine() -> dict[str, str]:
    """Ready llama-swap / llama-server (or a test pin). Does not probe a public host."""
    test = (os.environ.get("PFY_TEST_OPENAI_BASE") or "").strip()
    if test:
        base = _normalize_host(test, test)
        engine = (os.environ.get("PFY_LOCAL_RUNTIME") or "llama-server").strip() or "llama-server"
        if _http_ok(base + "/v1/models") or _http_ok(base + "/health") or _http_ok(base + "/api/tags"):
            return {"engine": engine, "base_url": base, "status": "ready"}
        return {"engine": engine, "base_url": base, "status": "partial"}
    from . import hedge

    data = hedge.detect_local()
    engine = str(data.get("engine") or "none")
    status = str(data.get("status") or "missing")
    base = str(data.get("base_url") or "")
    if status == "ready" and engine in ("llama-swap", "llama-server", "llama.cpp", "llamacpp", "openai-compat"):
        return {"engine": engine, "base_url": base, "status": "ready"}
    return {"engine": engine, "base_url": base, "status": status or "missing"}


def parse_model(spec: str) -> tuple[str, str]:
    text = (spec or "").strip()
    if not text:
        raise LaunchError("missing --model", next_step="pass --model ollama:<tag> or llamacpp:<alias>")
    if ":" not in text:
        raise LaunchError(
            "paid source refused: Claude Code and Codex only take a local ollama:<tag> or llamacpp:<alias> model",
            next_step="use --model ollama:<tag> or llamacpp:<alias>",
        )
    kind, rest = text.split(":", 1)
    return kind, rest


def refuse_paid(harness: str, spec: str) -> None:
    if harness == "grok":
        return
    kind, rest = parse_model(spec)
    if kind == "ollama":
        if not rest.strip():
            raise LaunchError("missing ollama tag", next_step="pass --model ollama:<tag>")
        return
    if kind == "llamacpp":
        if not rest.strip():
            raise LaunchError("missing llamacpp alias", next_step="pass --model llamacpp:<alias>")
        return
    raise LaunchError(
        "paid source refused: Claude Code and Codex only take a local ollama:<tag> or llamacpp:<alias> model",
        next_step="use --model ollama:<tag> or llamacpp:<alias>",
    )


def _anthropic_base_from_ollama() -> str:
    host = ollama_host()
    parsed = urlparse(host)
    if parsed.path in ("", "/"):
        return host
    return f"{parsed.scheme}://{parsed.netloc}"


def plan_launch(harness: str, model: str, *, dry_run: bool, passthrough: list[str] | None = None) -> LaunchPlan:
    hid = (harness or "").strip()
    extra = list(passthrough or [])
    if hid == "grok":
        return LaunchPlan(
            harness="grok",
            model="subscription",
            argv=["grok", *extra],
            env={},
            dry_run=dry_run,
            delegate="",
        )
    if hid not in HARNESS_BIN:
        raise LaunchError(
            f"unknown harness {hid!r}",
            next_step="use claude-code or grok, or a reserved ./pfy launch wizard subcommand",
            code=2,
        )
    refuse_paid(hid, model)
    kind, tag = parse_model(model)
    if hid != "claude-code":
        raise LaunchError(
            f"{hid} launch beyond paid-source refusal is not in this Phase 2 slice",
            next_step="use: pfy launch claude-code --model ollama:<tag>|llamacpp:<alias> --yes --dry-run --json, or pfy launch grok --yes --dry-run --json",
            code=3,
        )
    if kind == "ollama":
        if not ollama_is_up():
            raise LaunchError(
                "Ollama is down; pfy launch needs a running local daemon",
                next_step="ollama serve",
            )
        if ollama_launch_available():
            return LaunchPlan(
                harness=hid,
                model=model,
                argv=["ollama", "launch", "claude-code", "--model", tag, *extra],
                env={},
                dry_run=dry_run,
                delegate="ollama launch",
            )
        return LaunchPlan(
            harness=hid,
            model=model,
            argv=[HARNESS_BIN[hid], *extra],
            env={
                "ANTHROPIC_BASE_URL": _anthropic_base_from_ollama(),
                "ANTHROPIC_AUTH_TOKEN": "ollama",
            },
            dry_run=dry_run,
            delegate="",
        )
    # llamacpp:<alias>
    spine = llamacpp_spine()
    if spine.get("status") != "ready":
        raise LaunchError(
            "llama-swap / llama-server is down; llamacpp sources need the local spine",
            next_step=SPINE_NEXT,
        )
    if not litellm_is_up():
        raise LaunchError(
            "LiteLLM is down; Claude Code needs the local Anthropic gateway",
            next_step=LITELLM_NEXT,
        )
    return LaunchPlan(
        harness=hid,
        model=model,
        argv=[HARNESS_BIN[hid], *extra],
        env={
            "ANTHROPIC_BASE_URL": _strip_v1(litellm_host()),
            "ANTHROPIC_AUTH_TOKEN": "litellm",
        },
        dry_run=dry_run,
        delegate="litellm",
    )


def estimate_label(model: str, root: Path | None = None) -> str:
    """Local price table only. Never opens a network socket."""
    from . import model_choice

    try:
        priced = model_choice.quote(
            model,
            ESTIMATE_PROMPT_TOKENS,
            ESTIMATE_COMPLETION_TOKENS,
            root=root,
        )
    except (model_choice.UnknownModelPrice, model_choice.PriceCoverageError, ValueError, KeyError, TypeError):
        return "estimate unavailable"
    return "estimate $%s" % priced["cost_text"]


def harness_options() -> list[MenuOption]:
    return [
        MenuOption(key="1", kind="local", harness="claude-code", label="claude-code  (local models only)"),
        MenuOption(key="2", kind="subscription", harness="grok", model="subscription", label="grok  (subscription)", cost_label="subscription"),
    ]


def model_options(harness: str, *, root: Path | None = None, aliases: list[str] | None = None) -> list[MenuOption]:
    hid = (harness or "").strip()
    rows: list[MenuOption] = []
    n = 1
    ollama_up = ollama_is_up()
    local_reason = "" if ollama_up else "Ollama is down; next: ollama serve"
    rows.append(MenuOption(
        key=str(n),
        kind="local",
        harness=hid,
        model=LOCAL_DEFAULT,
        label=LOCAL_DEFAULT + "  [local default]",
        selectable=bool(ollama_up) and hid != "grok",
        reason=local_reason if hid != "grok" else "grok uses a subscription, not a local model",
    ))
    n += 1
    spine = llamacpp_spine()
    names = list(aliases or [])
    if not names:
        names = ["default"]
    for alias in names:
        spec = "llamacpp:" + alias
        ok = spine.get("status") == "ready" and hid != "grok"
        reason = ""
        if hid == "grok":
            reason = "grok uses a subscription, not a local model"
        elif not ok:
            reason = SPINE_NEXT
        rows.append(MenuOption(
            key=str(n),
            kind="local",
            harness=hid,
            model=spec,
            label=spec + "  [local]",
            selectable=ok,
            reason=reason,
        ))
        n += 1
    rows.append(MenuOption(
        key=str(n),
        kind="subscription",
        harness="grok" if hid == "grok" else hid,
        model="subscription",
        label="grok  [subscription]",
        cost_label="subscription",
        selectable=hid == "grok",
        reason="" if hid == "grok" else "subscription is the Grok harness; Claude Code and Codex stay local-only",
    ))
    n += 1
    from . import model_choice

    for name in model_choice.priced_cloud_models(root):
        rows.append(MenuOption(
            key=str(n),
            kind="cloud",
            harness=hid,
            model=name if ":" in name else "cloud:" + name,
            label=name + "  [cloud]",
            cost_label=estimate_label(name, root=root),
            selectable=False,
            reason="paid source refused: Claude Code and Codex only take a local model",
        ))
        n += 1
    return rows


def _pick(options: list[MenuOption], raw: str) -> MenuOption:
    text = (raw or "").strip()
    if not text:
        raise LaunchError("no selection", next_step="pick a listed number or name", code=2)
    for opt in options:
        if text == opt.key or text == opt.harness or text == opt.model or text == opt.label.split()[0]:
            return opt
    raise LaunchError("unknown selection %r" % text, next_step="pick a listed number or name", code=2)


def _print_menu(title: str, options: list[MenuOption], out: TextIO) -> None:
    out.write(title + "\n")
    for opt in options:
        out.write(opt.line() + "\n")
    out.flush()



def require_cloud_cap(*, yes: bool, max_usd: float | None, estimate: str = "") -> None:
    """11/11: --yes without a covering --max-usd does not run a cloud source."""
    if max_usd is None:
        raise LaunchError(
            "cloud source needs --max-usd; estimate was shown before the choice"
            + ((" (" + estimate + ")") if estimate else ""),
            next_step="re-run with --max-usd covering the printed estimate (a bare --yes does not run)",
            code=1,
        )
    if yes and max_usd is None:  # pragma: no cover — guarded above
        raise LaunchError("--yes requires --max-usd", code=1)


def run_selector(
    *,
    stdin: TextIO,
    stdout: TextIO,
    isatty: bool,
    harness: str = "",
    max_usd: float | None = None,
    yes: bool = False,
    root: Path | None = None,
    aliases: list[str] | None = None,
) -> tuple[str, str]:
    """Interactive harness x model picker. Non-TTY must use flags instead."""
    if not isatty:
        raise LaunchError(
            "non-TTY falls back to flags",
            next_step="pass --harness and --model (pfy launch grok needs no --model)",
            code=2,
        )
    hid = (harness or "").strip()
    if not hid:
        hopts = harness_options()
        _print_menu("Harness:", hopts, stdout)
        stdout.write("choose harness: ")
        stdout.flush()
        chosen_h = _pick(hopts, stdin.readline())
        if not chosen_h.selectable:
            raise LaunchError(chosen_h.reason or "harness is not selectable", code=1)
        hid = chosen_h.harness
        if hid == "grok":
            return "grok", "subscription"
    if hid == "grok":
        return "grok", "subscription"
    mopts = model_options(hid, root=root, aliases=aliases)
    _print_menu("Model / source:", mopts, stdout)
    stdout.write("choose model (estimates and subscription labels are shown above): ")
    stdout.flush()
    chosen = _pick(mopts, stdin.readline())
    if chosen.kind == "cloud":
        require_cloud_cap(yes=yes, max_usd=max_usd, estimate=chosen.cost_label)
        if not chosen.selectable:
            raise LaunchError(
                chosen.reason or "paid source refused",
                next_step="pick a local ollama:<tag> or llamacpp:<alias> source",
                code=1,
            )
    if not chosen.selectable:
        raise LaunchError(
            chosen.reason or "option is not selectable",
            next_step="pick a selectable local source, or grok for a subscription",
            code=1,
        )
    return hid, chosen.model


def stdin_is_tty() -> bool:
    hook = (os.environ.get("PFY_LAUNCH_ISTTY") or "").strip()
    if hook == "1":
        return True
    if hook == "0":
        return False
    try:
        return bool(sys.stdin.isatty())
    except Exception:
        return False


def emit(obj: dict, as_json: bool, stream=None) -> None:
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


def _fail(exc: LaunchError, as_json: bool) -> int:
    emit(exc.to_json(), as_json)
    if not as_json:
        print(exc.reason, file=sys.stderr)
        if exc.next_step:
            print("next: " + exc.next_step, file=sys.stderr)
    return int(exc.code)


def cmd_launch(args: Any) -> int:
    as_json = bool(getattr(args, "json", False))
    hid = (getattr(args, "harness", None) or "").strip()
    model = (getattr(args, "model", None) or "").strip()
    dry_run = bool(getattr(args, "dry_run", False))
    yes = bool(getattr(args, "yes", False))
    max_usd = getattr(args, "max_usd", None)
    extra = list(getattr(args, "passthrough", None) or [])
    needs_pick = (not hid) or (hid != "grok" and not model)
    if needs_pick:
        try:
            hid, model = run_selector(
                stdin=sys.stdin,
                stdout=sys.stderr if as_json else sys.stdout,
                isatty=stdin_is_tty(),
                harness=hid,
                max_usd=max_usd,
                yes=yes,
            )
        except LaunchError as exc:
            return _fail(exc, as_json)
    try:
        plan = plan_launch(hid, model, dry_run=dry_run, passthrough=extra)
    except LaunchError as exc:
        return _fail(exc, as_json)
    emit(plan.to_json(), as_json)
    if plan.dry_run:
        return 0
    if not yes:
        emit(
            {"ok": False, "reason": "refusing to exec without --yes", "next_step": "re-run with --yes or --dry-run"},
            as_json,
        )
        return 1
    return _fail(
        LaunchError(
            "live exec is not in this Phase 2 slice",
            next_step="use --dry-run --json, or a later gated live-smoke slice",
            code=3,
        ),
        as_json,
    )
