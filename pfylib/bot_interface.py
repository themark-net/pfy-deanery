#!/usr/bin/env python3
"""One-shot local bot. PFY_BOT_INTERFACE=hermes is opt-in. Default is opencode.

Does not exec ~/.local/bin/hermes, does not read ~/.hermes, and does not run
the Hermes installer. Stdlib only.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

EXIT_OK, EXIT_FAIL, EXIT_USAGE = 0, 1, 2
FALLBACK_NOTICE = (
    "notice: PFY_BOT_INTERFACE=hermes was requested but Hermes is missing; "
    "this turn ran opencode and the exit code is opencode's"
)


def repo_root() -> Path:
    raw = os.environ.get("PFY_ROOT") or ""
    if raw:
        return Path(raw).resolve()
    return Path(__file__).resolve().parents[1]


def resolve_interface(env: dict | None = None) -> str:
    """opencode unless the flag is exactly hermes."""
    env = env if env is not None else os.environ
    raw = (env.get("PFY_BOT_INTERFACE") or "").strip().lower()
    if raw in ("", "opencode", "off"):
        return "opencode"
    if raw == "hermes":
        return "hermes"
    raise SystemExit(
        "FAIL: PFY_BOT_INTERFACE must be opencode or hermes\n"
        "  next: unset PFY_BOT_INTERFACE or set it to opencode"
    )


def reasoning_setting(env: dict | None = None) -> str:
    env = env if env is not None else os.environ
    raw = (env.get("PFY_BOT_REASONING") or "off").strip().lower()
    if raw not in ("off", "on"):
        raise SystemExit("FAIL: PFY_BOT_REASONING must be off or on\n  next: set PFY_BOT_REASONING=off")
    return raw


def endpoint(env: dict | None = None) -> str:
    """OpenAI-compatible base. A root form like http://127.0.0.1:11434 gets /v1, as in scripts/pfy."""
    env = env if env is not None else os.environ
    base = (env.get("LOCAL_OPENAI_BASE_URL") or "").strip().rstrip("/") or "http://127.0.0.1:11434/v1"
    if not base.endswith("/v1"):
        base += "/v1"
    return base


def hermes_home(env: dict | None = None, root: Path | None = None) -> Path:
    """Isolated home. Refuses ~/.hermes before any mkdir."""
    env = env if env is not None else os.environ
    root = root or repo_root()
    raw = env.get("PFY_HERMES_HOME") or str(root / "tmp" / "hermes-bot-home")
    resolved = Path(raw).expanduser().resolve()
    forbidden = (Path.home() / ".hermes").resolve()
    if resolved == forbidden or forbidden in resolved.parents:
        raise SystemExit(
            f"FAIL: PFY_HERMES_HOME resolves under ~/.hermes ({resolved})\n"
            "  next: unset PFY_HERMES_HOME"
        )
    return resolved


def probe_model(base_url: str, timeout: float = 3) -> bool:
    """True when a local tags or models endpoint answers. Does not load a model."""
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        root = root[: -len("/v1")]
    urls = [root + "/api/tags", base_url.rstrip("/") + "/models"]
    for url in urls:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            continue
    return False


def _which_opencode(env: dict) -> str:
    explicit = (env.get("PFY_BOT_OPENCODE") or "").strip()
    if explicit:
        return explicit if Path(explicit).exists() else ""
    return shutil.which("opencode") or ""


def _hermes_paths(env: dict, root: Path) -> tuple[Path, Path, Path]:
    python = Path(env.get("PFY_HERMES_PYTHON") or (root / "tmp" / ".venv-hermes" / "bin" / "python"))
    checkout = Path(env.get("PFY_HERMES_CHECKOUT") or (root / "tmp" / "hermes-agent"))
    driver = Path(env.get("PFY_BOT_DRIVER") or Path(__file__).with_name("hermes_bot_driver.py"))
    return python, checkout, driver


def _timeout(env: dict) -> float:
    raw = (env.get("PFY_BOT_TIMEOUT") or "180").strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise SystemExit("FAIL: PFY_BOT_TIMEOUT is not a number") from exc
    if value <= 0:
        raise SystemExit("FAIL: PFY_BOT_TIMEOUT must be > 0")
    return value


def _model(env: dict) -> str:
    return (env.get("PFY_BOT_MODEL") or "qwen3.6:35b").strip()


def _scrub(env: dict, **extra: str) -> dict[str, str]:
    keep = ("PATH", "HOME", "LANG", "LC_ALL", "USER", "LOGNAME", "TERM")
    out = {key: env[key] for key in keep if env.get(key)}
    out.update(extra)
    return out


def _llm_child(model, provider, base, name, env, cmd, timeout, cwd=None):
    """One LLM span around one child. An import failure still runs the child once."""
    try:
        from pfylib.otel import child_env as trace_env
        from pfylib.otel import llm_call, route_for

        box = llm_call(model, provider, route_for(provider, base), name=name)
    except Exception:
        return _run_child(cmd, env, timeout, cwd=cwd)
    with box:
        try:
            token = trace_env(env).get("TRACEPARENT")
            if token:
                env["TRACEPARENT"] = token
        except Exception:
            pass
        return _run_child(cmd, env, timeout, cwd=cwd)


def _run_child(
    cmd: list[str], env: dict, timeout: float, cwd: Path | None = None
) -> tuple[int, str, str, bool]:
    """Run one child with stdin closed. On timeout, kill the process group this call started."""
    proc = subprocess.Popen(
        cmd,
        env=env,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        return proc.returncode or 0, stdout or "", stderr or "", False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.communicate(timeout=2)
        return EXIT_USAGE, "", "timeout", True


def _malformed(calls) -> bool:
    if not isinstance(calls, list):
        return True
    for call in calls:
        if not isinstance(call, dict):
            return True
        if "arguments" in call and not isinstance(call.get("arguments"), dict):
            return True
    return False


def _work(root: Path) -> Path:
    path = root / "tmp" / "bot-interface"
    path.mkdir(parents=True, exist_ok=True)
    return path


def opencode_config(base: str, model: str) -> dict:
    """Provider block so `--model ollama/<model>` resolves to the configured server."""
    return {
        "$schema": "https://opencode.ai/config.json",
        "autoupdate": False,
        "share": "disabled",
        "model": f"ollama/{model}",
        "enabled_providers": ["ollama"],
        "provider": {
            "ollama": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "Ollama (local)",
                "options": {"baseURL": base, "apiKey": "local"},
                "models": {model: {"name": model, "tool_call": True}},
            }
        },
    }


def write_opencode_config(work: Path, base: str, model: str) -> Path:
    """Write the isolated opencode config under work and return the file path."""
    path = work / "opencode" / "config" / "opencode" / "opencode.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(opencode_config(base, model), indent=2) + "\n", encoding="utf-8")
    return path


def run_opencode(prompt: str, env: dict, root: Path, timeout: float, base: str, reasoning: str, model: str) -> int:
    binary = _which_opencode(env)
    if not binary:
        print("FAIL: opencode is missing")
        print("  next: ./pfy attach opencode")
        return EXIT_USAGE
    work = _work(root)
    variant = "none" if reasoning == "off" else "high"
    config = write_opencode_config(work, base, model)
    sandbox = work / "opencode"
    cmd = [binary, "run", "--pure", "--model", f"ollama/{model}", "--variant", variant, prompt]
    child_env = _scrub(
        env,
        OPENAI_BASE_URL=base,
        HOME=str(sandbox / "home"),
        XDG_CONFIG_HOME=str(sandbox / "config"),
        XDG_DATA_HOME=str(sandbox / "data"),
        XDG_CACHE_HOME=str(sandbox / "cache"),
        XDG_STATE_HOME=str(sandbox / "state"),
        OPENCODE_CONFIG=str(config),
        OPENCODE_DISABLE_PROJECT_CONFIG="1",
        OPENCODE_DISABLE_AUTOUPDATE="1",
        OPENCODE_DISABLE_MODELS_FETCH="1",
        OPENCODE_DISABLE_SHARE="1",
        OPENCODE_DISABLE_CLAUDE_CODE="1",
        OPENCODE_DISABLE_EXTERNAL_SKILLS="1",
        OPENCODE_DISABLE_LSP_DOWNLOAD="1",
        PFY_BOT_REASONING=reasoning,
    )
    cwd = sandbox / "cwd"
    for key in ("HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_STATE_HOME"):
        Path(child_env[key]).mkdir(parents=True, exist_ok=True)
    cwd.mkdir(parents=True, exist_ok=True)
    code, stdout, stderr, timed_out = _llm_child(
        model, "ollama", base, "opencode", child_env, cmd, timeout, cwd=cwd
    )
    if timed_out:
        print("FAIL: timeout")
        print("  next: retry or raise PFY_BOT_TIMEOUT")
        return EXIT_USAGE
    if stdout.strip():
        print(stdout.rstrip())
    if code != 0:
        print("FAIL: opencode exited", code)
        if stderr.strip():
            print(stderr.rstrip()[:500])
        return EXIT_FAIL
    return EXIT_OK


def run_hermes(prompt: str, env: dict, root: Path, timeout: float, base: str, reasoning: str, model: str) -> int:
    python, checkout, driver = _hermes_paths(env, root)
    home = hermes_home(env, root)
    if not python.exists() or not checkout.exists() or not driver.exists():
        print("FAIL: Hermes checkout or python is missing")
        print("  next: falling back to opencode")
        print("  turn off: unset PFY_BOT_INTERFACE or set PFY_BOT_INTERFACE=opencode")
        print(FALLBACK_NOTICE, file=sys.stderr)
        return run_opencode(prompt, env, root, timeout, base, reasoning, model)
    home.mkdir(parents=True, exist_ok=True)
    work = _work(root)
    out = work / "hermes-turn.json"
    if out.exists():
        out.unlink()
    cmd = [
        str(python),
        str(driver),
        "--prompt",
        prompt,
        "--out",
        str(out),
        "--base-url",
        base,
        "--model",
        model,
        "--reasoning",
        reasoning,
        "--home",
        str(home),
        "--checkout",
        str(checkout),
    ]
    child_env = _scrub(
        env,
        HERMES_HOME=str(home),
        HERMES_CHECKOUT=str(checkout),
        HERMES_REDACT_SECRETS="true",
        PYTHONNOUSERSITE="1",
        PYTHONDONTWRITEBYTECODE="1",
    )
    code, stdout, stderr, timed_out = _llm_child(
        model, "ollama", base, "hermes", child_env, cmd, timeout
    )
    if timed_out:
        print("FAIL: timeout")
        print("  next: retry or raise PFY_BOT_TIMEOUT")
        return EXIT_USAGE
    if not out.exists():
        print("FAIL: Hermes driver wrote no result")
        if stderr.strip():
            print(stderr.rstrip()[:500])
        return EXIT_FAIL
    try:
        payload = json.loads(out.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("FAIL: malformed tool call")
        return EXIT_FAIL
    calls = payload.get("tool_calls") if isinstance(payload, dict) else None
    if calls is None:
        calls = []
    if _malformed(calls):
        print("FAIL: malformed tool call")
        return EXIT_FAIL
    text = payload.get("final_text") if isinstance(payload, dict) else ""
    if isinstance(text, str) and text.strip():
        print(text.rstrip())
    if code != 0 or not payload.get("ok", True):
        err = payload.get("error") if isinstance(payload, dict) else ""
        print("FAIL: Hermes driver", err or code)
        return EXIT_FAIL
    if stdout.strip():
        print(stdout.rstrip())
    return EXIT_OK


def run_turn(prompt: str, env: dict | None = None, root: Path | None = None) -> int:
    env = dict(os.environ if env is None else env)
    root = root or repo_root()
    if not prompt.strip():
        print("FAIL: prompt is empty")
        print("  next: ./pfy bot \"prompt\"")
        return EXIT_USAGE
    interface = resolve_interface(env)
    reasoning = reasoning_setting(env)
    base = endpoint(env)
    model = _model(env)
    print(f"bot interface: {interface}")
    print(f"reasoning: {reasoning}")
    print(f"endpoint: {base}")
    if interface == "hermes":
        # Refuse a real home before the probe so a bad flag does no I/O there.
        hermes_home(env, root)
        python, checkout, driver = _hermes_paths(env, root)
        if python.exists() and checkout.exists() and driver.exists():
            if not probe_model(base):
                print("FAIL: model server down")
                print("  next: ./pfy up")
                return EXIT_USAGE
            return run_hermes(prompt, env, root, _timeout(env), base, reasoning, model)
        print("FAIL: Hermes checkout or python is missing")
        print("  next: falling back to opencode")
        print("  turn off: unset PFY_BOT_INTERFACE or set PFY_BOT_INTERFACE=opencode")
        print(FALLBACK_NOTICE, file=sys.stderr)
        print("bot interface: opencode")
        interface = "opencode"
    if not probe_model(base):
        print("FAIL: model server down")
        print("  next: ./pfy up")
        return EXIT_USAGE
    return run_opencode(prompt, env, root, _timeout(env), base, reasoning, model)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv in (["-h"], ["--help"]):
        print("usage: pfy bot \"prompt\"")
        print("  PFY_BOT_INTERFACE=hermes selects Hermes. Default is opencode.")
        print("  hermes requested but its checkout or python missing: falls back to opencode,")
        print("  prints a notice on stderr, and exits with opencode's code (0 on success).")
        print("  Hermes runs with no toolsets (no terminal, file, or web tools).")
        print("  turn off: unset PFY_BOT_INTERFACE or set PFY_BOT_INTERFACE=opencode")
        return EXIT_OK
    prompt = " ".join(argv).strip()
    try:
        return run_turn(prompt)
    except SystemExit as exc:
        if exc.code in (0, None):
            return EXIT_OK
        text = str(exc)
        if text and not text.isdigit():
            print(text)
        return EXIT_USAGE


if __name__ == "__main__":
    raise SystemExit(main())
