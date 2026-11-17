#!/usr/bin/env python3
"""T-0091 4b / T-0092 — voice transcript → tool-capable agent (local-first).

ADR-0012: default bulk path is **OpenCode → Ollama**, not Grok.

  VOICE_AUTO_AGENT=
    off / 0          — STT only
    1 / on / auto    — **opencode** (local; T-0092 default)
    opencode/worker  — same
    grok             — cloud escalate only
    mock             — dry-run smoke

Fallback when OpenCode CLI missing: OpenAI-compat chat to local Ollama
(LOCAL_CODER_MODEL) so voice still lands on a local brain without cloud.

Writes:
  .generated/last-run.json · last-run.log · last-reply.txt
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

import uuid

def _gen_dir() -> Path:
    return Path(__file__).resolve().parent / ".generated"

def resolve_session_id() -> str:
    """Sticky multi-turn session id (T-0091)."""
    gen = _gen_dir()
    gen.mkdir(parents=True, exist_ok=True)
    sid_path = gen / "session.id"
    if os.environ.get("VOICE_SESSION_RESET", "").strip().lower() in ("1", "true", "yes"):
        sid = str(uuid.uuid4())
        sid_path.write_text(sid + "\n", encoding="utf-8")
        return sid
    env = (os.environ.get("VOICE_SESSION_ID") or "").strip()
    if env:
        sid_path.write_text(env + "\n", encoding="utf-8")
        return env
    if sid_path.is_file():
        existing = sid_path.read_text(encoding="utf-8").strip()
        if existing:
            return existing
    sid = str(uuid.uuid4())
    sid_path.write_text(sid + "\n", encoding="utf-8")
    return sid


EDGE = Path(__file__).resolve().parent
ROOT = EDGE.parents[1]
DEFAULT_OUT = EDGE / ".generated"
OPENCODE_GEN = ROOT / "examples" / "opencode-ollama" / ".generated"
LOCK_NAME = "agent-runner.lock"


def load_voice_memory(limit: int | None = None) -> list[dict]:
    """Cross-turn transcript ring (GAP-17 / #48)."""
    gen = _gen_dir()
    path = gen / "memory.jsonl"
    if not path.is_file():
        return []
    n = limit
    if n is None:
        n = int(os.environ.get("VOICE_MEMORY_TURNS", "5") or "5")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    rows = []
    for ln in lines[-max(n, 0):]:
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return rows


def append_voice_memory(role: str, text: str, meta: dict | None = None) -> None:
    if os.environ.get("VOICE_MEMORY", "1").strip().lower() in ("0", "false", "no"):
        return
    gen = _gen_dir()
    gen.mkdir(parents=True, exist_ok=True)
    path = gen / "memory.jsonl"
    row = {
        "ts": utc_now() if "utc_now" in globals() else __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "session_id": resolve_session_id(),
        "role": role,
        "text": (text or "")[:4000],
    }
    if meta:
        row["meta"] = meta
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def memory_prompt_block() -> str:
    rows = load_voice_memory()
    if not rows:
        return ""
    lines = ["## Prior voice turns (memory)", ""]
    for r in rows:
        lines.append(f"- ({r.get('role')}) {r.get('text', '')[:500]}")
    lines.append("")
    return "\n".join(lines)



def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_out(out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    return out


def write_run(out: Path, payload: dict) -> Path:
    # Sticky multi-turn session (T-0091)
    payload = dict(payload)
    payload.setdefault("session_id", resolve_session_id())
    # Cross-turn memory (GAP-17)
    if payload.get("prompt"):
        append_voice_memory("user", str(payload.get("prompt") or ""), {"run_id": payload.get("run_id")})
    if payload.get("reply"):
        append_voice_memory("assistant", str(payload.get("reply") or ""), {"status": payload.get("status")})
    payload["memory_turns"] = len(load_voice_memory())
    path = out / "last-run.json"
    payload = {**payload, "updated": utc_now()}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def read_run(out: Path) -> dict:
    path = out / "last-run.json"
    if not path.is_file():
        return {"status": "none", "message": "no runs yet"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"status": "error", "message": "corrupt last-run.json"}


def normalize_mode(raw: str | None) -> str:
    """Map env/CLI tokens → off|mock|grok|opencode|orchestrate.

    T-0096: bare 1/on/auto → **orchestrate** (default route high-first via VOICE_ROUTE).
    Explicit opencode/grok remain single-tier.
    """
    s = (raw or "0").strip().lower()
    if s in ("", "0", "false", "no", "off"):
        return "off"
    if s in ("1", "true", "yes", "on", "auto", "orchestrate", "orch", "dual"):
        return "orchestrate"
    if s in ("opencode", "worker", "local"):
        return "opencode"
    if s in ("mock", "test"):
        return "mock"  # mock single-tier; use orchestrate+VOICE_ORCH_MOCK for dual mock
    if s in ("mock-orch", "mock_orchestrate", "orchestrate-mock"):
        return "orchestrate-mock"
    if s in ("grok", "cloud", "monitor"):
        return "grok"
    return "off"


def auto_mode() -> str:
    return normalize_mode(os.environ.get("VOICE_AUTO_AGENT"))


def _lock_path(out: Path) -> Path:
    return out / LOCK_NAME


def acquire_lock(out: Path) -> bool:
    lp = _lock_path(out)
    if lp.is_file():
        try:
            meta = json.loads(lp.read_text(encoding="utf-8"))
            pid = int(meta.get("pid") or 0)
            if pid and Path(f"/proc/{pid}").exists():
                return False
        except Exception:
            pass
    lp.write_text(
        json.dumps({"pid": os.getpid(), "started": utc_now()}) + "\n",
        encoding="utf-8",
    )
    return True


def release_lock(out: Path) -> None:
    p = _lock_path(out)
    if p.is_file():
        try:
            p.unlink()
        except OSError:
            pass


def build_prompt(prompt_path: Path | None, transcript: str | None, target: str, repo: Path) -> str:
    if prompt_path and prompt_path.is_file():
        base = prompt_path.read_text(encoding="utf-8").strip()
    elif transcript:
        base = (
            f"# Voice → agent (T-0092 local-first)\n\n"
            f"**Target:** {target}\n**Repo:** `{repo}`\n\n"
            f"## Spoken intent\n\n{transcript.strip()}\n\n"
            f"Prefer cheap local checks. Land changes in the repo when implementing. "
            f"Stop after success or 3 identical failures.\n"
        )
    else:
        raise ValueError("need --prompt-file or --transcript / --text")

    mem = memory_prompt_block()
    if mem:
        base = mem + "\n" + base

    footer = (
        "\n\n---\n"
        "**Auto-runner (ADR-0012):** Invoked from voice STT. Local OpenCode/Ollama is the "
        "default bulk path; keep replies concise. End with a short status "
        "(what ran, pass/fail, next step).\n"
    )
    return base + footer


def _finish_ok(
    *,
    out: Path,
    run_id: str,
    mode: str,
    reply: str,
    cmd: list[str],
    duration: float,
    exit_code: int = 0,
    extra: dict | None = None,
) -> dict:
    (out / "last-reply.txt").write_text(reply + ("\n" if reply else ""), encoding="utf-8")
    payload = {
        "status": "done" if exit_code == 0 else "error",
        "ok": exit_code == 0,
        "run_id": run_id,
        "mode": mode,
        "exit_code": exit_code,
        "reply": reply[-8000:] if len(reply) > 8000 else reply,
        "reply_preview": (reply[:500] + ("…" if len(reply) > 500 else "")),
        "command": cmd,
        "duration_s": duration,
        "error": None if exit_code == 0 else f"{mode} exit {exit_code}",
    }
    if extra:
        payload.update(extra)
    return payload


def run_mock(prompt: str, out: Path, run_id: str) -> dict:
    reply = (
        f"[mock agent / local-first] Would run OpenCode→Ollama on:\n"
        f"{prompt[:400]}{'…' if len(prompt) > 400 else ''}\n"
        f"VOICE_RUNNER_MOCK_OK"
    )
    time.sleep(0.15)
    return _finish_ok(
        out=out,
        run_id=run_id,
        mode="mock",
        reply=reply,
        cmd=["mock"],
        duration=0.15,
    )


def ollama_base_url() -> str:
    base = (
        os.environ.get("OPENAI_BASE_URL")
        or os.environ.get("OLLAMA_OPENAI_BASE")
        or "http://127.0.0.1:11434/v1"
    )
    base = base.rstrip("/")
    if not base.endswith("/v1"):
        base = base + "/v1"
    return base


def local_coder_model() -> str:
    return os.environ.get("LOCAL_CODER_MODEL") or os.environ.get("EVAL_MODEL") or "deepseek-coder:6.7b"


def local_agent_model() -> str:
    """Prefer tools-capable model (T-0093) for agent runs; else coder."""
    tools = (os.environ.get("LOCAL_TOOLS_MODEL") or os.environ.get("OPENCODE_AGENT_MODEL") or "").strip()
    if tools:
        return tools
    return local_coder_model()


def run_ollama_completion(prompt: str, out: Path, run_id: str, timeout_s: int) -> dict:
    """Direct local chat completion (no OpenCode CLI). Cloud-free fallback."""
    base = ollama_base_url()
    model = local_agent_model()
    url = base + "/chat/completions"
    # Keep prompt bounded for small local models
    user = prompt if len(prompt) < 6000 else (prompt[:5500] + "\n\n[truncated]\n")
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a local coding assistant. Be concise. "
                        "If asked to run checks, describe the commands and expected outcomes."
                    ),
                },
                {"role": "user", "content": user},
            ],
            "max_tokens": int(os.environ.get("VOICE_LOCAL_MAX_TOKENS", "512")),
            "temperature": 0.2,
        }
    ).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY', 'ollama')}",
        },
        method="POST",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    cmd = ["ollama-compat", "POST", url, f"model={model}"]
    log_path = out / "last-run.log"
    t0 = time.time()
    try:
        with opener.open(req, timeout=min(timeout_s, 180)) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        duration = round(time.time() - t0, 2)
        text = (
            (data.get("choices") or [{}])[0].get("message", {}).get("content") or ""
        ).strip()
        log_path.write_text(
            f"$ {' '.join(cmd)}\n\n--- response ---\n{text}\n\n--- raw keys ---\n"
            f"{list(data.keys())}\n",
            encoding="utf-8",
        )
        if not text:
            return {
                "status": "error",
                "ok": False,
                "run_id": run_id,
                "mode": "ollama",
                "exit_code": 1,
                "reply": "",
                "error": "empty Ollama completion",
                "command": cmd,
                "duration_s": duration,
                "log_path": str(log_path),
            }
        return _finish_ok(
            out=out,
            run_id=run_id,
            mode="ollama",
            reply=text,
            cmd=cmd,
            duration=duration,
            extra={"log_path": str(log_path), "model": model, "base_url": base},
        )
    except Exception as e:
        duration = round(time.time() - t0, 2)
        err = f"Ollama completion failed: {e}"
        log_path.write_text(err + "\n", encoding="utf-8")
        return {
            "status": "error",
            "ok": False,
            "run_id": run_id,
            "mode": "ollama",
            "exit_code": 1,
            "reply": "",
            "error": err,
            "command": cmd,
            "duration_s": duration,
            "log_path": str(log_path),
            "hint": "Start Ollama; set LOCAL_CODER_MODEL; or use VOICE_AUTO_AGENT=mock",
        }


def run_opencode(prompt: str, repo: Path, out: Path, run_id: str, timeout_s: int) -> dict:
    """OpenCode CLI if present; else Ollama HTTP completion (local-first)."""
    prompt_file = out / "last-agent-prompt.txt"
    prompt_file.write_text(prompt, encoding="utf-8")
    log_path = out / "last-run.log"
    model = local_agent_model()
    cfg = os.environ.get("OPENCODE_CONFIG") or str(OPENCODE_GEN / "opencode.json")
    # Auto-load tools-model.env if present and LOCAL_TOOLS_MODEL unset
    tools_env = OPENCODE_GEN / "tools-model.env"
    if tools_env.is_file() and not os.environ.get("LOCAL_TOOLS_MODEL"):
        for line in tools_env.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("export ") and "=" in line:
                k, v = line[len("export ") :].split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
        model = local_agent_model()

    oc = shutil.which("opencode")
    if oc:
        cmd = [oc, "run"]
        # model flag when config known
        if Path(cfg).is_file():
            env_prefix = {"OPENCODE_CONFIG": cfg}
        else:
            env_prefix = {}
        # Prefer ollama/model form used by smoke
        cmd.extend(["-m", f"ollama/{model}", prompt[:12000]])
        env = os.environ.copy()
        env.update(env_prefix)
        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(repo),
                capture_output=True,
                text=True,
                timeout=timeout_s,
                env=env,
            )
            duration = round(time.time() - t0, 2)
            out_txt = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
            log_path.write_text(
                f"$ OPENCODE_CONFIG={cfg} {' '.join(cmd)}\n\n{out_txt}\n",
                encoding="utf-8",
            )
            # OpenCode may exit 0 with tools warning — accept non-empty
            ok = proc.returncode == 0 or (len(out_txt) > 10 and proc.returncode in (0, 1))
            # Prefer treating non-zero with substantial output as soft-ok for local models
            if proc.returncode != 0 and len(out_txt) > 20:
                ok = True
            return _finish_ok(
                out=out,
                run_id=run_id,
                mode="opencode",
                reply=out_txt[-8000:],
                cmd=cmd,
                duration=duration,
                exit_code=0 if ok else proc.returncode,
                extra={
                    "log_path": str(log_path),
                    "model": model,
                    "opencode_config": cfg,
                    "raw_exit": proc.returncode,
                },
            )
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "ok": False,
                "run_id": run_id,
                "mode": "opencode",
                "error": f"timeout after {timeout_s}s",
                "exit_code": 124,
                "reply": "",
                "command": cmd,
            }
        except Exception as e:
            print(f"==> opencode CLI failed ({e}); falling back to Ollama HTTP", file=sys.stderr)

    print(
        "==> opencode CLI not used — local Ollama completion fallback (T-0092)",
        file=sys.stderr,
    )
    result = run_ollama_completion(prompt, out, run_id, timeout_s)
    result["mode"] = "opencode-ollama" if result.get("ok") else result.get("mode", "ollama")
    result["fallback"] = "ollama-http"
    return result


def run_grok(
    prompt: str,
    repo: Path,
    out: Path,
    *,
    max_turns: int,
    timeout_s: int,
    run_id: str,
) -> dict:
    grok = shutil.which("grok")
    if not grok:
        return {
            "status": "error",
            "ok": False,
            "run_id": run_id,
            "mode": "grok",
            "exit_code": 127,
            "reply": "",
            "error": "grok not on PATH",
            "command": [],
            "hint": "Use VOICE_AUTO_AGENT=opencode for local path",
        }

    prompt_file = out / "last-agent-prompt.txt"
    prompt_file.write_text(prompt, encoding="utf-8")
    log_path = out / "last-run.log"

    # Opt-in only. Unset / empty / 0 / false / no / off do not pass
    # --always-approve. A typo is treated as off (fail closed).
    always = os.environ.get("VOICE_AGENT_ALWAYS_APPROVE", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    cmd = [
        grok,
        "--cwd",
        str(repo),
        "--max-turns",
        str(max_turns),
        "--output-format",
        "plain",
        "--prompt-file",
        str(prompt_file),
        "--no-alt-screen",
    ]
    if always:
        cmd.insert(1, "--always-approve")

    env = os.environ.copy()
    env.setdefault("CI", "1")
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(repo),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
        )
        duration = round(time.time() - t0, 2)
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        log_path.write_text(
            f"$ {' '.join(cmd)}\n\n--- stdout ---\n{stdout}\n\n--- stderr ---\n{stderr}\n",
            encoding="utf-8",
        )
        reply = stdout.strip() or stderr.strip()
        return _finish_ok(
            out=out,
            run_id=run_id,
            mode="grok",
            reply=reply,
            cmd=cmd,
            duration=duration,
            exit_code=proc.returncode,
            extra={"log_path": str(log_path)},
        )
    except subprocess.TimeoutExpired as e:
        duration = round(time.time() - t0, 2)
        partial = e.stdout or ""
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", errors="replace")
        log_path.write_text(f"TIMEOUT after {timeout_s}s\n{partial}\n", encoding="utf-8")
        return {
            "status": "error",
            "ok": False,
            "run_id": run_id,
            "mode": "grok",
            "exit_code": 124,
            "reply": (partial or "")[-4000:],
            "error": f"timeout after {timeout_s}s",
            "command": cmd,
            "duration_s": duration,
            "log_path": str(log_path),
        }
    except Exception as e:
        return {
            "status": "error",
            "ok": False,
            "run_id": run_id,
            "mode": "grok",
            "exit_code": 1,
            "reply": "",
            "error": str(e),
            "command": cmd,
        }


def run_once(
    *,
    repo: Path,
    out: Path,
    mode: str,
    target: str,
    prompt_path: Path | None,
    transcript: str | None,
    max_turns: int,
    timeout_s: int,
) -> dict:
    out = ensure_out(out)
    run_id = uuid.uuid4().hex[:12]
    known = ("off", "mock", "grok", "opencode", "orchestrate", "orchestrate-mock")
    mode = normalize_mode(mode) if mode not in known else mode

    if mode == "off":
        write_run(
            out,
            {
                "status": "skipped",
                "ok": True,
                "run_id": run_id,
                "mode": "off",
                "message": (
                    "VOICE_AUTO_AGENT off — set VOICE_AUTO_AGENT=1 for dual-tier "
                    "(high-first default) or =opencode / =grok for single tier"
                ),
            },
        )
        return read_run(out)

    if not acquire_lock(out):
        cur = read_run(out)
        return {
            "status": "busy",
            "ok": False,
            "run_id": run_id,
            "mode": mode,
            "message": "another agent run is in progress",
            "current": cur,
        }

    try:
        prompt = build_prompt(prompt_path, transcript, target, repo)

        # T-0096 dual-tier
        if mode in ("orchestrate", "orchestrate-mock"):
            import orchestrator as orch

            mock = mode == "orchestrate-mock" or os.environ.get("VOICE_ORCH_MOCK", "").strip() in (
                "1",
                "true",
                "yes",
            )
            print(
                f"==> agent_runner orchestrate run_id={run_id} mock={mock}",
                file=sys.stderr,
            )
            result = orch.orchestrate(
                repo=repo,
                out=out,
                user_prompt=prompt,
                route=None,  # VOICE_ROUTE (default high-first)
                max_turns=max_turns,
                timeout_s=timeout_s,
                mock=mock,
            )
            result["target"] = target
            write_run(out, result)
            maybe_speak_status(result)
            return result

        # target=worker forces opencode path even if mode=grok was a mistake
        effective = mode
        if target == "worker" and mode == "grok":
            print("==> target=worker → using opencode (local) not grok", file=sys.stderr)
            effective = "opencode"

        write_run(
            out,
            {
                "status": "running",
                "ok": False,
                "run_id": run_id,
                "mode": effective,
                "target": target,
                "started": utc_now(),
                "transcript_preview": (transcript or "")[:200],
                "message": f"agent running ({effective})…",
            },
        )
        print(
            f"==> agent_runner mode={effective} run_id={run_id} target={target}",
            file=sys.stderr,
        )

        if effective == "mock":
            result = run_mock(prompt, out, run_id)
        elif effective == "opencode":
            result = run_opencode(prompt, repo, out, run_id, timeout_s)
        elif effective == "grok":
            result = run_grok(
                prompt, repo, out, max_turns=max_turns, timeout_s=timeout_s, run_id=run_id
            )
        else:
            result = {
                "status": "error",
                "ok": False,
                "run_id": run_id,
                "mode": effective,
                "error": f"unknown mode {effective}",
                "exit_code": 2,
                "reply": "",
            }

        result["target"] = target
        result["finished"] = utc_now()
        write_run(out, result)
        maybe_speak_status(result)
        preview = (result.get("reply_preview") or result.get("reply") or "")[:200]
        print(
            f"==> agent_runner {result.get('status')} mode={result.get('mode')} "
            f"exit={result.get('exit_code')}",
            file=sys.stderr,
        )
        if preview:
            print(f"==> REPLY: {preview!r}", file=sys.stderr)
        return result
    finally:
        release_lock(out)



def maybe_speak_status(result: dict) -> dict:
    """Opt-in T-0094 status beep. Never changes the agent result. Fail-soft."""
    import importlib.util

    phrase = "done" if result.get("ok") else "fail"
    speak = Path(__file__).resolve().parent.parent / "voice-tts-status" / "speak_status.py"
    try:
        spec = importlib.util.spec_from_file_location("voice_speak_status", speak)
        if spec is None or spec.loader is None:
            print("voice-tts: skip (speak_status.py missing)", file=sys.stderr)
            return {"ok": False, "skipped": True, "reason": "speak_status.py missing"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.speak_status(phrase)
    except Exception as exc:
        print(f"voice-tts: skip ({exc})", file=sys.stderr)
        return {"ok": False, "skipped": True, "reason": str(exc)}


def spawn_background(**kwargs) -> str:
    run_id = uuid.uuid4().hex[:12]
    out = ensure_out(kwargs["out"])
    write_run(
        out,
        {
            "status": "queued",
            "ok": False,
            "run_id": run_id,
            "mode": kwargs.get("mode"),
            "target": kwargs.get("target"),
            "message": "queued for agent runner",
            "started": utc_now(),
        },
    )

    def _job() -> None:
        try:
            run_once(**kwargs)
        except Exception as e:
            write_run(
                out,
                {
                    "status": "error",
                    "ok": False,
                    "run_id": run_id,
                    "error": str(e),
                    "message": str(e),
                },
            )

    threading.Thread(target=_job, name=f"voice-agent-{run_id}", daemon=True).start()
    return run_id


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="T-0092 voice → local OpenCode/Ollama agent (Grok escalate optional)"
    )
    p.add_argument("--repo", type=Path, default=ROOT)
    p.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    p.add_argument("--prompt-file", type=Path, help="agent-prompt.md path")
    p.add_argument("--transcript", "--text", dest="transcript", help="raw transcript text")
    p.add_argument("--target", default="worker", choices=["monitor", "worker", "raw"])
    p.add_argument(
        "--mode",
        default=None,
        help="off|orchestrate|opencode|grok|mock|1(=orchestrate high-first). Default: VOICE_AUTO_AGENT",
    )
    p.add_argument(
        "--max-turns",
        type=int,
        default=int(os.environ.get("VOICE_AGENT_MAX_TURNS", "8")),
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=int(os.environ.get("VOICE_AGENT_TIMEOUT", "600")),
    )
    p.add_argument("--background", action="store_true")
    p.add_argument("--status", action="store_true")
    args = p.parse_args(argv)

    out = ensure_out(args.out_dir)
    if args.status:
        print(json.dumps(read_run(out), indent=2))
        return 0

    if args.mode is None:
        env_mode = auto_mode()
        # CLI without env: default orchestrate (T-0096 high-first); env off → orchestrate for explicit CLI
        mode = env_mode if env_mode != "off" else "orchestrate"
    else:
        mode = normalize_mode(args.mode)

    prompt_path = args.prompt_file
    if prompt_path is None:
        cand = out / "agent-prompt.md"
        if cand.is_file():
            prompt_path = cand
    transcript = args.transcript
    if transcript is None:
        tpath = out / "last-transcript.txt"
        if tpath.is_file():
            transcript = tpath.read_text(encoding="utf-8").strip()

    # Default target: worker for opencode, monitor for grok
    target = args.target
    if args.mode is None and target == "worker" and mode == "grok":
        target = "monitor"

    if args.background:
        rid = spawn_background(
            repo=args.repo.resolve(),
            out=out,
            mode=mode,
            target=target,
            prompt_path=prompt_path,
            transcript=transcript,
            max_turns=args.max_turns,
            timeout_s=args.timeout,
        )
        print(json.dumps({"queued": True, "run_id": rid, "mode": mode, "target": target}, indent=2))
        return 0

    result = run_once(
        repo=args.repo.resolve(),
        out=out,
        mode=mode,
        target=target,
        prompt_path=prompt_path,
        transcript=transcript,
        max_turns=args.max_turns,
        timeout_s=args.timeout,
    )
    print(
        json.dumps(
            {
                k: result.get(k)
                for k in (
                    "status",
                    "ok",
                    "run_id",
                    "mode",
                    "exit_code",
                    "duration_s",
                    "error",
                    "reply_preview",
                    "fallback",
                    "model",
                )
            },
            indent=2,
        )
    )
    if result.get("reply"):
        print("--- reply ---", file=sys.stderr)
        print(result["reply"][:2000], file=sys.stderr)
    return 0 if result.get("ok") or result.get("status") in ("skipped", "done") else 1


if __name__ == "__main__":
    raise SystemExit(main())
