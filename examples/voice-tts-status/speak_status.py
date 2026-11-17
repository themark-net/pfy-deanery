#!/usr/bin/env python3
"""T-0094 — optional local TTS (not duplex, no phone playback).

Opt in with VOICE_TTS=1 (also true / yes / on). Default is silence: no
binary is started, no voice model is fetched, no paid call.

VOICE_TTS_MODE:
  unset / status — speak a short "done" or "fail" (default)
  reply / full   — speak the agent reply, clipped to REPLY_MAX characters

A typo in the mode does not switch to full reply. piper is used only when
VOICE_TTS_PIPER_MODEL points at an existing local model file. Kokoro is
not wired (catalog-fit verdict: redundant; see kokoro-fit.md).

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

STATUS_MAX = 80
REPLY_MAX = 400
TRUTHY = ("1", "true", "yes", "on")
REPLY_MODES = ("reply", "full")


def opted_in(env: dict[str, str] | os._Environ | None = None) -> bool:
    src = os.environ if env is None else env
    return str(src.get("VOICE_TTS", "")).strip().lower() in TRUTHY


def tts_mode(env: dict[str, str] | os._Environ | None = None) -> str:
    src = os.environ if env is None else env
    raw = str(src.get("VOICE_TTS_MODE", "")).strip().lower()
    if raw in REPLY_MODES:
        return "reply"
    return "status"


def clip_text(text: str, max_chars: int) -> str:
    """Collapse whitespace, cap length, prefer a word boundary, mark a cut."""
    cleaned = " ".join((text or "").split())
    if max_chars <= 0:
        return ""
    if len(cleaned) <= max_chars:
        return cleaned
    cut = cleaned[:max_chars].rstrip()
    space = cut.rfind(" ")
    if space >= max(max_chars // 2, 1):
        cut = cut[:space].rstrip()
    return cut.rstrip(".,;:") + "…"


def phrase_for_result(result: dict, env: dict[str, str] | os._Environ | None = None) -> str:
    """Status mode: done/fail. Reply mode: clipped reply, else done/fail."""
    if tts_mode(env) == "reply":
        reply = str(result.get("reply") or result.get("reply_preview") or "")
        clipped = clip_text(reply, REPLY_MAX)
        if clipped:
            return clipped
    return "done" if result.get("ok") else "fail"


def _which(name: str, env: dict[str, str] | os._Environ | None = None) -> str | None:
    path = None if env is None else env.get("PATH")
    return shutil.which(name, path=path)


def pick_command(
    status: str,
    *,
    env: dict[str, str] | os._Environ | None = None,
    max_chars: int | None = None,
) -> tuple[list[str] | None, str, bytes | None]:
    """Return (argv, reason, stdin_bytes). argv is None when the call should skip."""
    src = os.environ if env is None else env
    if not opted_in(src):
        return None, "VOICE_TTS is off", None
    cap = STATUS_MAX if tts_mode(src) == "status" else REPLY_MAX
    if max_chars is not None:
        cap = max_chars
    text = clip_text(status, cap) or "done"

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
    timeout_s: float | None = None,
    max_chars: int | None = None,
) -> dict:
    src = os.environ if env is None else env
    cmd, reason, stdin = pick_command(status, env=env, max_chars=max_chars)
    if cmd is None:
        print(f"voice-tts: skip ({reason})", file=sys.stderr)
        return {"ok": True, "skipped": True, "reason": reason, "command": [], "text": ""}
    spoken = stdin.decode("utf-8") if stdin else (cmd[-1] if cmd else "")
    if timeout_s is None:
        timeout_s = 15 if tts_mode(src) == "status" else 60
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
            "text": spoken,
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
            "text": spoken,
        }
    preview = spoken if len(spoken) <= 80 else spoken[:77] + "…"
    print(f"voice-tts: spoke {preview!r} via {cmd[0]}", file=sys.stderr)
    return {"ok": True, "skipped": False, "reason": reason, "command": cmd, "text": spoken}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Speak a short local TTS status or clipped reply (opt-in).")
    p.add_argument("status", nargs="?", default="done", help='Text to speak ("done"/"fail", or a reply)')
    p.add_argument(
        "--mode",
        choices=("status", "reply"),
        default=None,
        help="Override VOICE_TTS_MODE for this call",
    )
    args = p.parse_args(argv)
    if args.mode:
        os.environ["VOICE_TTS_MODE"] = args.mode
    speak_status(args.status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
