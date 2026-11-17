#!/usr/bin/env python3
"""T-0094 — optional short local TTS status (not duplex).

Opt in with VOICE_TTS=1 (also true / yes / on). Default is silence: no
binary is started, no voice model is fetched, no paid call.

When opted in, speak a short status ("done" or "fail") with a host
binary already on PATH: espeak-ng, espeak, or say. piper is used only
when VOICE_TTS_PIPER_MODEL points at an existing local model file.

A missing binary or a TTS error is a skip (exit 0). This helper never
installs a package or downloads a model.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

MAX_CHARS = 80
TRUTHY = ("1", "true", "yes", "on")


def opted_in(env: dict[str, str] | os._Environ | None = None) -> bool:
    src = os.environ if env is None else env
    return str(src.get("VOICE_TTS", "")).strip().lower() in TRUTHY


def _which(name: str, env: dict[str, str] | os._Environ | None = None) -> str | None:
    path = None if env is None else env.get("PATH")
    return shutil.which(name, path=path)


def pick_command(
    status: str,
    *,
    env: dict[str, str] | os._Environ | None = None,
) -> tuple[list[str] | None, str, bytes | None]:
    """Return (argv, reason, stdin_bytes). argv is None when the call should skip."""
    src = os.environ if env is None else env
    if not opted_in(src):
        return None, "VOICE_TTS is off", None
    text = (status or "").strip() or "done"
    text = text[:MAX_CHARS]

    model = str(src.get("VOICE_TTS_PIPER_MODEL", "")).strip()
    piper = _which("piper", src)
    if piper and model and Path(model).is_file():
        return [piper, "--model", model], "piper", text.encode("utf-8")

    for name in ("espeak-ng", "espeak", "say"):
        binary = _which(name, src)
        if binary:
            return [binary, text], name, None

    if piper and not (model and Path(model).is_file()):
        return None, "piper is present but VOICE_TTS_PIPER_MODEL is not an existing file", None
    return None, "no local TTS binary (espeak-ng, espeak, say, or piper with VOICE_TTS_PIPER_MODEL)", None


def speak_status(
    status: str,
    *,
    env: dict[str, str] | os._Environ | None = None,
    timeout_s: float = 15,
) -> dict:
    cmd, reason, stdin = pick_command(status, env=env)
    if cmd is None:
        print(f"voice-tts: skip ({reason})", file=sys.stderr)
        return {"ok": True, "skipped": True, "reason": reason, "command": []}
    try:
        proc = subprocess.run(
            cmd,
            input=stdin,
            timeout=timeout_s,
            capture_output=True,
        )
    except Exception as exc:
        msg = f"tts error: {exc}"
        print(f"voice-tts: skip ({msg})", file=sys.stderr)
        return {
            "ok": False,
            "skipped": True,
            "reason": msg,
            "command": cmd,
        }
    if proc.returncode != 0:
        err = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
        msg = err or f"exit {proc.returncode}"
        print(f"voice-tts: skip ({msg})", file=sys.stderr)
        return {
            "ok": False,
            "skipped": True,
            "reason": msg,
            "command": cmd,
        }
    print(f"voice-tts: spoke {status!r} via {cmd[0]}", file=sys.stderr)
    return {"ok": True, "skipped": False, "reason": reason, "command": cmd}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Speak a short local TTS status (opt-in).")
    p.add_argument("status", nargs="?", default="done", help='Short phrase, usually "done" or "fail"')
    args = p.parse_args(argv)
    speak_status(args.status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
