#!/usr/bin/env python3
"""Opt-in ngram-mod decode for one model-bound step.

PFY_LLAMA_NGRAM=1 starts a llama-server this process owns, on 127.0.0.1 and a
free port, with a GGUF that is already on disk. Any other value, including
unset, prints the baseline engine and starts nothing.

A missing binary, a missing or oversized model, a server that does not become
healthy, or a check prompt that differs from the baseline stops only the pid
this run started and prints the baseline engine. This script never calls
ollama stop and never signals a pid it did not start.

A real server requires PFY_MODEL_LOCK_HELD=1 (scripts/model_lock.sh).
Health wait is 180s. One completion wait is 180s. Stop waits 2s, then SIGKILL
on that same pid. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import select
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_MAX_BYTES = 25_000_000_000
HEADROOM_BYTES = 25 * 1024**3
HEALTH_TIMEOUT = 180
COMPLETE_TIMEOUT = 180
N_PREDICT = 64
CHECK_PROMPT = (
    "Repeat the next function exactly.\n"
    "def ping():\n"
    "    return 1\n"
    "def ping():\n"
    "    return 1\n"
    "def ping():\n"
    "    return 1\n"
    "def ping():\n"
)

SLUG = "llama-cpp-ngram-mod"


def log(message: str) -> None:
    print(message, file=sys.stderr)


def say_baseline(reason: str) -> None:
    if reason:
        log(reason)
    print("engine: baseline")


def flag_on() -> bool:
    return os.environ.get("PFY_LLAMA_NGRAM") == "1"


def cache_dir() -> Path:
    raw = os.environ.get("PFY_LLAMA_NGRAM_CACHE", "").strip()
    if raw:
        return Path(raw)
    return Path.home() / ".cache" / "pfy" / "tools" / "integrate-llama-cpp-ngram-mod"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def receipt_blocks() -> bool:
    """True when this sha already has a receipt. Does not write the file."""
    sha = os.environ.get("PFY_LLAMA_NGRAM_SHA", "").strip()
    raw = os.environ.get("PFY_LLAMA_NGRAM_RECEIPT", "").strip()
    if not sha or not raw:
        return False
    path = Path(raw)
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(data, dict):
        return False
    have = data.get("sha")
    if have is None:
        have = data.get("main_sha")
    if str(have) == sha:
        log("receipt already exists for sha %s" % sha)
        return True
    return False


def resolve_model() -> Path | None:
    raw = os.environ.get("PFY_LLAMA_NGRAM_MODEL", "").strip()
    if not raw:
        log("model path unset; max 25 GB; using baseline")
        return None
    path = Path(raw)
    if not path.is_file():
        log("model missing at %s; using baseline" % path)
        return None
    limit = DEFAULT_MAX_BYTES
    raw_max = os.environ.get("PFY_LLAMA_NGRAM_MAX_BYTES", "").strip()
    if raw_max:
        try:
            limit = int(raw_max)
        except ValueError:
            log("max bytes is not an integer; using baseline")
            return None
        if limit < 0:
            log("max bytes is negative; using baseline")
            return None
    size = path.stat().st_size
    if size > limit:
        log("model size %s exceeds max %s (25 GB cap)" % (size, limit))
        return None
    return path


def server_binary() -> tuple[Path | None, bool]:
    """Return (path, fake). fake is true when PFY_LLAMA_NGRAM_FAKE_SERVER is set."""
    fake = os.environ.get("PFY_LLAMA_NGRAM_FAKE_SERVER", "").strip()
    if fake:
        path = Path(fake)
        if path.is_file() and os.access(path, os.X_OK):
            return path, True
        log("llama-server missing at %s" % path)
        return None, True
    candidates = []
    chosen = os.environ.get("PFY_LLAMA_NGRAM_SERVER", "").strip()
    if chosen:
        candidates.append(chosen)
    candidates.append("/usr/local/lib/ollama/llama-server")
    for item in candidates:
        path = Path(item)
        if path.is_file() and os.access(path, os.X_OK):
            return path, False
    found = shutil.which("llama-server")
    if found:
        return Path(found), False
    log("llama-server missing")
    return None, False


def _note_pid(pid: int) -> None:
    raw = os.environ.get("PFY_LLAMA_NGRAM_LOCK_DIR", "").strip()
    if not raw or pid < 2:
        return
    folder = Path(raw)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "server.pid").write_text("%s\n" % pid, encoding="utf-8")


def _stop(proc: subprocess.Popen | None) -> None:
    """Stop a process this run started. No-op if it already exited."""
    if proc is None or proc.pid < 2 or proc.poll() is not None:
        return
    pid = proc.pid
    try:
        pgid = os.getpgid(pid)
    except OSError:
        return

    def send(sig: int) -> None:
        try:
            if pgid == pid:
                os.killpg(pid, sig)
            else:
                os.kill(pid, sig)
        except OSError:
            pass

    send(signal.SIGTERM)
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return
        time.sleep(0.05)
    if proc.poll() is None:
        send(signal.SIGKILL)
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass


def _read_line(stream, timeout: float) -> str:
    ready, _, _ = select.select([stream], [], [], timeout)
    if not ready:
        return ""
    return stream.readline().decode("utf-8", "replace")


def _fake_text(binary: Path) -> str:
    proc = subprocess.Popen(
        [str(binary)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=os.environ.copy(),
        start_new_session=True,
    )
    _note_pid(proc.pid)
    try:
        if proc.stdout is None:
            return ""
        return _read_line(proc.stdout, 5).strip()
    finally:
        _stop(proc)
        if proc.stdout is not None:
            proc.stdout.close()


def _mem_available() -> int | None:
    try:
        text = Path("/proc/meminfo").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        if not line.startswith("MemAvailable:"):
            continue
        parts = line.split()
        if len(parts) < 2:
            return None
        try:
            return int(parts[1]) * 1024
        except ValueError:
            return None
    return None


def _ollama_busy() -> str | None:
    exe = shutil.which("ollama")
    if not exe:
        return None
    try:
        proc = subprocess.run(
            [exe, "ps"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    rows = []
    for line in (proc.stdout or "").splitlines():
        text = line.strip()
        if not text or text.upper().startswith("NAME"):
            continue
        rows.append(text)
    if rows:
        return "ollama ps shows a loaded model; leaving it alone"
    return None


def host_block_reason(size: int) -> str | None:
    avail = _mem_available()
    if avail is None:
        return "MemAvailable unreadable; using baseline"
    if avail < size + HEADROOM_BYTES:
        return "MemAvailable below model size plus 25 GiB; using baseline"
    busy = _ollama_busy()
    if busy:
        return busy + "; using baseline"
    return None


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
    finally:
        sock.close()


def _child_env() -> dict:
    root = cache_dir()
    for name in ("home", "xdg/config", "xdg/cache", "xdg/data", "tmp"):
        (root / name).mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["HOME"] = str(root / "home")
    env["XDG_CONFIG_HOME"] = str(root / "xdg" / "config")
    env["XDG_CACHE_HOME"] = str(root / "xdg" / "cache")
    env["XDG_DATA_HOME"] = str(root / "xdg" / "data")
    env["TMPDIR"] = str(root / "tmp")
    lib = Path("/usr/local/lib/ollama")
    hip = lib / "rocm_v7_2" / "libggml-hip.so"
    if hip.is_file():
        env["HSA_OVERRIDE_GFX_VERSION"] = os.environ.get("HSA_OVERRIDE_GFX_VERSION", "11.5.1")
        env["GGML_BACKEND_PATH"] = str(hip)
        ld = "%s/rocm_v7_2:%s" % (lib, lib)
        old = os.environ.get("LD_LIBRARY_PATH")
        env["LD_LIBRARY_PATH"] = ld if not old else ld + ":" + old
        env["GGML_CUDA_ENABLE_UNIFIED_MEMORY"] = "1"
        env["GGML_HIP_UMA"] = "1"
    return env


def _opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _healthy(port: int) -> bool:
    req = urllib.request.Request("http://127.0.0.1:%s/health" % port)
    try:
        with _opener().open(req, timeout=2) as resp:
            return 200 <= int(resp.status) < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _wait_healthy(proc: subprocess.Popen, port: int) -> bool:
    deadline = time.monotonic() + HEALTH_TIMEOUT
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return False
        if _healthy(port):
            return True
        time.sleep(0.2)
    return proc.poll() is None and _healthy(port)


def _complete(port: int, prompt: str, n_predict: int) -> tuple[str, float | None]:
    body = {
        "prompt": prompt,
        "n_predict": int(n_predict),
        "temperature": 0,
        "top_k": 1,
        "top_p": 1,
        "seed": 7,
        "repeat_penalty": 1.0,
        "stream": False,
        "cache_prompt": False,
        "stop": ["# END"],
    }
    req = urllib.request.Request(
        "http://127.0.0.1:%s/completion" % port,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with _opener().open(req, timeout=COMPLETE_TIMEOUT) as resp:
        payload = json.loads(resp.read().decode("utf-8", "replace"))
    text = str(payload.get("content") or "")
    timings = payload.get("timings") if isinstance(payload.get("timings"), dict) else {}
    tok = timings.get("predicted_per_second")
    if not tok:
        count = timings.get("predicted_n")
        millis = timings.get("predicted_ms")
        if count and millis:
            tok = float(count) / (float(millis) / 1000.0)
    try:
        rate = float(tok) if tok else None
    except (TypeError, ValueError):
        rate = None
    return text, rate


def _start_real(binary: Path, model: Path, spec: str, port: int) -> subprocess.Popen:
    argv = [
        str(binary),
        "--model",
        str(model),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--spec-type",
        spec,
        "--no-mmap",
        "-ngl",
        "999",
        "-c",
        "2048",
        "-np",
        "1",
        "-fa",
        "on",
        "--no-webui",
    ]
    root = cache_dir()
    root.mkdir(parents=True, exist_ok=True)
    handle = (root / ("server-%s.log" % spec)).open("w", encoding="utf-8")
    try:
        proc = subprocess.Popen(
            argv,
            stdout=handle,
            stderr=subprocess.STDOUT,
            env=_child_env(),
            start_new_session=True,
        )
    finally:
        handle.close()
    _note_pid(proc.pid)
    return proc


def _pass_prompts(
    binary: Path,
    model: Path,
    spec: str,
    prompts: list[str],
    limits: list[int],
) -> list[tuple[str, float | None]]:
    port = _free_port()
    proc = _start_real(binary, model, spec, port)
    try:
        if not _wait_healthy(proc, port):
            raise RuntimeError("health timeout for spec %s" % spec)
        out = []
        for prompt, limit in zip(prompts, limits):
            out.append(_complete(port, prompt, limit))
        return out
    finally:
        _stop(proc)


def _version(binary: Path) -> str:
    try:
        proc = subprocess.run(
            [str(binary), "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "llama-server"
    lines = ((proc.stdout or "") + "\n" + (proc.stderr or "")).splitlines()
    for line in lines:
        text = line.strip()
        if text:
            return text[:200]
    return "llama-server"


def _sha() -> str:
    env = os.environ.get("PFY_LLAMA_NGRAM_SHA", "").strip()
    if env:
        return env
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (proc.stdout or "").strip()


def write_receipt(
    path: str,
    *,
    started: str,
    tok_s: float | None,
    baseline_tok_s: float | None,
    identical: bool,
    version: str,
    did: str,
    outcome: str,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    log_path = target.with_suffix(".log")
    log_path.write_text(did + "\n", encoding="utf-8")
    body = {
        "slug": SLUG,
        "run_kind": "pipeline",
        "main_sha": _sha(),
        "sha": _sha(),
        "log_path": str(log_path),
        "started": started,
        "finished": utc_now(),
        "outcome": outcome,
        "tool_version": version,
        "did": did,
        "tok_s": tok_s,
        "baseline_tok_s": baseline_tok_s,
        "identical_outputs": "yes" if identical else "no",
    }
    text = json.dumps(body, indent=2) + "\n"
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, target)


def _lock_ok(fake: bool) -> bool:
    if fake:
        return True
    if os.environ.get("PFY_MODEL_LOCK_HELD") == "1":
        return True
    log("refusing llama-server outside scripts/model_lock.sh")
    return False


def compare_check(binary: Path, model: Path, fake: bool) -> dict:
    """Run the fixed check. Always stops servers this call started.

    Keys: identical (bool), text, baseline_text, tok_s, baseline_tok_s, version, error.
    """
    if fake:
        text = _fake_text(binary)
        baseline = os.environ.get("PFY_LLAMA_NGRAM_BASELINE_TEXT", "")
        return {
            "identical": bool(baseline) and text.strip() == baseline.strip(),
            "text": text,
            "baseline_text": baseline,
            "tok_s": None,
            "baseline_tok_s": None,
            "version": "fake",
            "error": "" if baseline else "baseline text unset",
        }
    blocked = host_block_reason(model.stat().st_size)
    if blocked:
        return {
            "identical": False,
            "text": "",
            "baseline_text": "",
            "tok_s": None,
            "baseline_tok_s": None,
            "version": "llama-server",
            "error": blocked,
        }
    version = _version(binary)
    base_text, base_tok = _pass_prompts(binary, model, "none", [CHECK_PROMPT], [N_PREDICT])[0]
    ngram_text, ngram_tok = _pass_prompts(
        binary, model, "ngram-mod", [CHECK_PROMPT], [N_PREDICT]
    )[0]
    same = bool(base_text.strip()) and base_text.strip() == ngram_text.strip()
    error = "" if base_text.strip() and ngram_text.strip() else "empty check output"
    return {
        "identical": same and not error,
        "text": ngram_text,
        "baseline_text": base_text,
        "tok_s": ngram_tok,
        "baseline_tok_s": base_tok,
        "version": version,
        "error": error,
    }


def complete_for_lane(prompt: str, max_tokens: int = 256) -> str | None:
    """Return one ngram completion, or None so the caller keeps the current engine."""
    if not flag_on() or receipt_blocks():
        return None
    model = resolve_model()
    if model is None:
        return None
    binary, fake = server_binary()
    if binary is None or not _lock_ok(fake):
        return None
    try:
        if fake:
            result = compare_check(binary, model, True)
            if result["error"] or not result["identical"]:
                if not result["identical"]:
                    log("mismatch on check prompt")
                return None
            return str(result["text"]).strip() or None
        blocked = host_block_reason(model.stat().st_size)
        if blocked:
            log(blocked)
            return None
        base_text, _base_tok = _pass_prompts(
            binary, model, "none", [CHECK_PROMPT], [N_PREDICT]
        )[0]
        rows = _pass_prompts(
            binary,
            model,
            "ngram-mod",
            [CHECK_PROMPT, prompt],
            [N_PREDICT, max_tokens],
        )
    except (OSError, urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
        log("llama-server failed: %s" % exc)
        return None
    check_text = rows[0][0]
    if not base_text.strip() or check_text.strip() != base_text.strip():
        log("mismatch on check prompt")
        return None
    return rows[1][0].strip() or None


def _emit(args: argparse.Namespace, started: str, result: dict, did: str) -> int:
    identical = bool(result.get("identical")) and not result.get("error")
    if result.get("error") and not identical:
        say_baseline(str(result["error"]))
        outcome = "fallback"
    elif not identical:
        say_baseline("mismatch on check prompt")
        outcome = "fallback"
        did = "check prompt mismatch; baseline engine kept"
    else:
        print("engine: ngram")
        outcome = "ok"
    if args.receipt_out:
        write_receipt(
            args.receipt_out,
            started=started,
            tok_s=result.get("tok_s"),
            baseline_tok_s=result.get("baseline_tok_s"),
            identical=identical,
            version=str(result.get("version") or "llama-server"),
            did=did,
            outcome=outcome,
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--receipt-out",
        default="",
        help="Write an INTEGRATE.md receipt JSON here",
    )
    args = parser.parse_args(argv)
    if not flag_on():
        say_baseline("PFY_LLAMA_NGRAM is not 1")
        return 0
    if receipt_blocks():
        return 2
    started = utc_now()
    model = resolve_model()
    if model is None:
        say_baseline("")
        if args.receipt_out:
            write_receipt(
                args.receipt_out,
                started=started,
                tok_s=None,
                baseline_tok_s=None,
                identical=False,
                version="unset",
                did="model missing, unset, or over the 25 GB cap; baseline engine kept",
                outcome="fallback",
            )
        return 0
    binary, fake = server_binary()
    if binary is None:
        say_baseline("")
        if args.receipt_out:
            write_receipt(
                args.receipt_out,
                started=started,
                tok_s=None,
                baseline_tok_s=None,
                identical=False,
                version="missing",
                did="llama-server missing; baseline engine kept",
                outcome="fallback",
            )
        return 0
    if not _lock_ok(fake):
        say_baseline("")
        if args.receipt_out:
            write_receipt(
                args.receipt_out,
                started=started,
                tok_s=None,
                baseline_tok_s=None,
                identical=False,
                version="unlocked",
                did="refused to start llama-server outside scripts/model_lock.sh",
                outcome="fallback",
            )
        return 0
    try:
        result = compare_check(binary, model, fake)
    except (OSError, urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as exc:
        result = {
            "identical": False,
            "tok_s": None,
            "baseline_tok_s": None,
            "version": "llama-server",
            "error": "llama-server failed: %s" % exc,
        }
    did = "one check prompt on llama-server --spec-type ngram-mod versus --spec-type none"
    return _emit(args, started, result, did)


if __name__ == "__main__":
    sys.exit(main())
