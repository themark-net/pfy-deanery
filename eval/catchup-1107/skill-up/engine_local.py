#!/usr/bin/env python3
"""skill-up custom local engine for one case.

Reads a SessionInput JSON path (argv) and prints a SessionResult JSON object
on stdout: {"exit_code", "final_message"}. Logs go to stderr only.

With `opencode` on PATH, runs `opencode run` in the case workspace against
Ollama through a loopback proxy. The proxy forces temperature 0, seed 230,
and thinking off. keep_alive "2m" is added only when this trial loaded the
model (marker tmp/skill-up/we-loaded). A model that is already loaded and
unmarked is left alone.

`--skills-dir` is applied only when SessionInput.variant is with_skill.
OpenCode is pointed at that directory via a temp XDG config. It never reads
The operator's ~/.config/opencode.

If opencode is not on PATH, a single chat-completions call is used instead
and final_message says so. That path cannot edit the workspace.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MODEL_DEFAULT = "qwen3.6:35b"
OLLAMA_DEFAULT = "http://127.0.0.1:11434"
GATE_KIB_DEFAULT = 47 * 1024 * 1024  # 47 GiB
CUSHION_S = 12
MARKER_NAME = "we-loaded"


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for cand in [here.parent, *here.parents]:
        if (cand / "AGENTS.md").is_file() and (cand / "data").is_dir():
            return cand
    return here.parents[4]


def _marker_path() -> Path:
    override = os.environ.get("SKILLUP_LOAD_MARKER", "").strip()
    if override:
        return Path(override)
    return _repo_root() / "tmp" / "skill-up" / MARKER_NAME


def _mem_available_kib() -> int | None:
    override = os.environ.get("SKILLUP_MEM_AVAILABLE_KIB", "").strip()
    if override:
        return int(override)
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return None
    return None


def _gate_kib() -> int:
    raw = os.environ.get("SKILLUP_MEM_GATE_KIB", "").strip()
    if raw:
        return int(raw)
    return GATE_KIB_DEFAULT


def _opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _ollama_base() -> str:
    return os.environ.get("SKILLUP_OLLAMA_URL", OLLAMA_DEFAULT).rstrip("/")


def _ps_required() -> bool:
    """Do not call the real Ollama when /api/ps cannot be read.

    A missed ps check can load qwen3.6:35b with no keep_alive. Tests set
    SKILLUP_REQUIRE_PS=0 and point at a stub. SKILLUP_REQUIRE_PS=1 forces the check.
    """
    flag = os.environ.get("SKILLUP_REQUIRE_PS", "").strip()
    if flag == "0":
        return False
    if flag == "1":
        return True
    return _ollama_base() in ("http://127.0.0.1:11434", "http://localhost:11434")


def _get_json(url: str, timeout: float = 5) -> dict | None:
    req = urllib.request.Request(url, method="GET")
    try:
        with _opener().open(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _model_row(model: str) -> dict | bool | None:
    """The /api/ps row, False when that model is not resident, None when ps failed."""
    data = _get_json(_ollama_base() + "/api/ps")
    if data is None:
        return None
    for row in data.get("models") or []:
        if isinstance(row, dict) and str(row.get("name") or "") == model:
            return row
    return False


def _model_loaded(model: str) -> bool | None:
    row = _model_row(model)
    if row is None:
        return None
    return bool(row)


def _write_marker(model: str, token: str) -> None:
    marker = _marker_path()
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(model + "\n" + token + "\n", encoding="utf-8")
    except OSError:
        pass


def _we_own_model(model: str) -> bool:
    """True when this trial should attach keep_alive 2m.

    A loaded model is ours only when its expires_at still matches the marker
    written after our last request. A stale marker must not refresh someone
    else's copy of the same model.
    """
    row = _model_row(model)
    if row is None:
        return False
    if row is False:
        _write_marker(model, "pending")
        return True
    expires = str(row.get("expires_at") or "")
    marker = _marker_path()
    if not expires or not marker.is_file():
        return False
    lines = [ln.strip() for ln in marker.read_text(encoding="utf-8", errors="replace").splitlines()]
    return len(lines) >= 2 and lines[0] == model and lines[1] == expires


def _remember_resident(model: str) -> None:
    """Record the expires_at of a model this trial just loaded or refreshed."""
    row = _model_row(model)
    if not isinstance(row, dict):
        return
    expires = str(row.get("expires_at") or "")
    if expires:
        _write_marker(model, expires)


def _frontmatter_name(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ""
    for line in lines[1:30]:
        if line.strip() == "---":
            break
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return ""


def _install_skills(workspace: Path, variant: str, skills_dir: str) -> Path:
    """Return the directory OpenCode should scan. Empty when not with_skill."""
    off = workspace / ".opencode" / "skills-off"
    on = workspace / ".opencode" / "skills"
    if variant != "with_skill":
        off.mkdir(parents=True, exist_ok=True)
        return off
    on.mkdir(parents=True, exist_ok=True)
    src = Path(skills_dir).expanduser() if skills_dir else None
    if src and src.is_dir() and (src / "SKILL.md").is_file():
        name = _frontmatter_name(src / "SKILL.md") or src.name
        dest = on / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        return on
    root_skill = workspace / "SKILL.md"
    if root_skill.is_file():
        name = _frontmatter_name(root_skill) or "skill"
        dest = on / name
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root_skill, dest / "SKILL.md")
        return on
    return on


def _write_config(path: Path, base_url: str, model: str, skills_path: Path, rules: Path) -> None:
    cfg = {
        "$schema": "https://opencode.ai/config.json",
        "provider": {
            "ollama": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "Ollama (local)",
                "options": {"baseURL": base_url, "apiKey": "local"},
                "models": {
                    model: {
                        "name": model,
                        "options": {
                            "temperature": 0,
                            "seed": 230,
                            "chat_template_kwargs": {"enable_thinking": False},
                        },
                    }
                },
            }
        },
        "model": "ollama/" + model,
        "skills": {"paths": [str(skills_path)], "urls": []},
        "instructions": [str(rules)],
        "permission": {
            "edit": "allow",
            "bash": "allow",
            "webfetch": "deny",
            "external_directory": "deny",
        },
        "lsp": False,
        "formatter": False,
        "plugin": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


def _child_env(workspace: Path, home: Path, xdg: Path, config_path: Path) -> dict[str, str]:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "TMPDIR": str(workspace / ".tmp"),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "LC_ALL": "C.UTF-8",
        "XDG_CONFIG_HOME": str(xdg),
        "XDG_DATA_HOME": str(xdg / "data"),
        "XDG_STATE_HOME": str(xdg / "state"),
        "XDG_CACHE_HOME": str(xdg / "cache"),
        "OPENCODE_CONFIG": str(config_path),
        "OPENCODE_DISABLE_MODELS_FETCH": "1",
        "OPENCODE_DISABLE_AUTOUPDATE": "1",
        "OPENCODE_DISABLE_LSP_DOWNLOAD": "1",
        "OPENCODE_DISABLE_DEFAULT_PLUGINS": "1",
        "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
        "OPENCODE_DISABLE_CLAUDE_CODE": "1",
        "OPENCODE_PURE": "1",
        "NO_COLOR": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_CEILING_DIRECTORIES": str(workspace),
    }
    for key, value in os.environ.items():
        if key.startswith("STUB_") or key.startswith("SKILLUP_"):
            env[key] = value
    (workspace / ".tmp").mkdir(parents=True, exist_ok=True)
    return env


def _pdeath(sig: int = signal.SIGKILL):
    def _fn() -> None:
        try:
            import ctypes

            libc = ctypes.CDLL("libc.so.6", use_errno=True)
            libc.prctl(1, sig)
        except Exception:
            return

    return _fn


def _prompt_of(session: dict) -> str:
    messages = session.get("messages") or []
    parts = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        content = msg.get("content")
        if isinstance(content, str) and content.strip():
            parts.append(content.strip())
    return "\n\n".join(parts)


def _collect_text(blob: str) -> str:
    chunks: list[str] = []
    for line in blob.splitlines():
        line = line.strip()
        if not line or line[0] not in "{[":
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(ev, dict):
            continue
        part = ev.get("part")
        if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str):
            chunks.append(part["text"])
            continue
        if ev.get("type") in ("text", "message") and isinstance(ev.get("text"), str):
            chunks.append(ev["text"])
    if chunks:
        return "\n".join(chunks).strip()
    # Last non-empty plain line, skipping log noise.
    plain = [ln.strip() for ln in blob.splitlines() if ln.strip() and not ln.strip().startswith("{")]
    return plain[-1] if plain else ""


def _result(code: int, message: str, started: float, stderr: str = "", engine: str = "") -> dict:
    msg = (message or "").strip()
    if len(msg) > 8000:
        msg = msg[:8000]
    err = (stderr or "").strip()
    if len(err) > 2000:
        err = err[-2000:]
    out = {
        "exit_code": int(code),
        "final_message": msg,
        "duration_ms": int((time.monotonic() - started) * 1000),
        "engine": engine or "pfy-local",
    }
    if err:
        out["stderr"] = err
    return out


class _Proxy(BaseHTTPRequestHandler):
    own = False
    upstream = OLLAMA_DEFAULT

    def log_message(self, fmt: str, *args) -> None:
        return

    def _forward(self, method: str) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b""
        path = self.path or "/"
        if method == "POST" and (
            path.startswith("/v1/chat/completions") or path.startswith("/api/chat") or path.startswith("/api/generate")
        ):
            raw = _stamp_body(raw, self.own)
        url = self.upstream.rstrip("/") + path
        headers = {"Content-Type": self.headers.get("Content-Type", "application/json")}
        if self.headers.get("Authorization"):
            headers["Authorization"] = self.headers["Authorization"]
        req = urllib.request.Request(url, data=raw if method == "POST" else None, headers=headers, method=method)
        try:
            with _opener().open(req, timeout=120) as resp:
                body = resp.read()
                status = resp.status
                ctype = resp.headers.get("Content-Type", "application/json")
        except urllib.error.HTTPError as exc:
            body = exc.read()
            status = exc.code
            ctype = "application/json"
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            body = json.dumps({"error": "upstream " + type(exc).__name__}).encode()
            status = 502
            ctype = "application/json"
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        self._forward("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._forward("POST")


def _stamp_body(raw: bytes, own: bool) -> bytes:
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return raw
    if not isinstance(obj, dict):
        return raw
    obj["temperature"] = 0
    obj["seed"] = 230
    extra = obj.get("chat_template_kwargs")
    if not isinstance(extra, dict):
        extra = {}
    extra["enable_thinking"] = False
    obj["chat_template_kwargs"] = extra
    obj["think"] = False
    # Ollama 0.30's OpenAI endpoint ignores think:false. reasoning_effort none
    # is what puts the answer in content instead of reasoning.
    obj["reasoning_effort"] = "none"
    if own:
        obj["keep_alive"] = "2m"
    return json.dumps(obj).encode("utf-8")


def _start_proxy(own: bool) -> tuple[ThreadingHTTPServer, str]:
    handler = type("Handler", (_Proxy,), {})
    handler.own = own
    handler.upstream = _ollama_base()
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, "http://%s:%s/v1" % (host, port)


def _git_init(workspace: Path, env: dict[str, str]) -> None:
    subprocess.run(
        ["git", "init", "-q"],
        cwd=str(workspace),
        env=env,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _run_opencode(session: dict, skills_dir: str, timeout_s: float, own: bool, started: float) -> dict:
    workspace = Path(session.get("workspace") or ".").resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    model = os.environ.get("SKILLUP_MODEL", MODEL_DEFAULT).strip() or MODEL_DEFAULT
    skills_path = _install_skills(workspace, str(session.get("variant") or ""), skills_dir)
    rules = workspace / "EVAL_RULES.md"
    rules.write_text(
        "Edit only files inside this workspace. Do not read or write parent directories.\n"
        "Do the task exactly. Do not add files the task did not ask for.\n",
        encoding="utf-8",
    )
    server, base = _start_proxy(own)
    try:
        home = workspace / ".home"
        xdg = workspace / ".xdg"
        for d in (home, xdg, xdg / "data", xdg / "state", xdg / "cache"):
            d.mkdir(parents=True, exist_ok=True)
        config_path = xdg / "opencode.json"
        _write_config(config_path, base, model, skills_path, rules)
        env = _child_env(workspace, home, xdg, config_path)
        _git_init(workspace, env)
        opencode = shutil.which("opencode", path=env["PATH"])
        if not opencode:
            return _chat_fallback(session, own, started, "opencode is not on PATH")
        prompt = _prompt_of(session)
        cmd = [
            opencode,
            "run",
            "--dir",
            str(workspace),
            "--format",
            "json",
            "--pure",
            "--auto",
            "-m",
            "ollama/" + model,
            "--title",
            str(session.get("case_id") or "case")[:60],
            prompt,
        ]
        print(
            "engine=opencode case=%s variant=%s timeout=%.0f" % (session.get("case_id"), session.get("variant"), timeout_s),
            file=sys.stderr,
        )
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(workspace),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                preexec_fn=_pdeath(),
            )
        except OSError as exc:
            return _result(1, "opencode failed to start: " + type(exc).__name__, started, engine="opencode")
        try:
            out_b, err_b = proc.communicate(timeout=timeout_s)
            code = proc.returncode if proc.returncode is not None else 1
        except subprocess.TimeoutExpired:
            _kill_group(proc)
            try:
                out_b, err_b = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                _kill_group(proc, signal.SIGKILL)
                out_b, err_b = proc.communicate()
            text = _collect_text((out_b or b"").decode("utf-8", errors="replace"))
            return _result(124, text or "timeout", started, (err_b or b"").decode("utf-8", errors="replace"), engine="opencode")
        text = _collect_text((out_b or b"").decode("utf-8", errors="replace"))
        if not text:
            text = "opencode produced no assistant text"
        return _result(code, text, started, (err_b or b"").decode("utf-8", errors="replace"), engine="opencode")
    finally:
        if own:
            _remember_resident(model)
        server.shutdown()


def _kill_group(proc: subprocess.Popen, sig: int = signal.SIGTERM) -> None:
    try:
        os.killpg(proc.pid, sig)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill()
        except OSError:
            return


def _chat_fallback(session: dict, own: bool, started: float, why: str) -> dict:
    print("engine=chat-completions reason=%s case=%s" % (why, session.get("case_id")), file=sys.stderr)
    model = os.environ.get("SKILLUP_MODEL", MODEL_DEFAULT).strip() or MODEL_DEFAULT
    messages = []
    for msg in session.get("messages") or []:
        if isinstance(msg, dict) and isinstance(msg.get("content"), str):
            messages.append({"role": str(msg.get("role") or "user"), "content": msg["content"]})
    if not messages:
        messages = [{"role": "user", "content": _prompt_of(session) or "Reply with OK."}]
    body = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "seed": 230,
        "max_tokens": 800,
        "chat_template_kwargs": {"enable_thinking": False},
        "think": False,
    }
    raw = _stamp_body(json.dumps(body).encode("utf-8"), own)
    url = _ollama_base() + "/v1/chat/completions"
    req = urllib.request.Request(
        url, data=raw, headers={"Content-Type": "application/json", "Authorization": "Bearer local"}, method="POST"
    )
    try:
        with _opener().open(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        if own:
            _remember_resident(model)
        return _result(
            1,
            "direct chat-completions agent (" + why + ") failed: " + type(exc).__name__,
            started,
            engine="chat-completions",
        )
    text = ""
    try:
        text = str(payload["choices"][0]["message"].get("content") or "")
    except (KeyError, IndexError, TypeError):
        text = ""
    if own:
        _remember_resident(model)
    note = "direct chat-completions agent (" + why + "). No workspace edits."
    return _result(0, (note + "\n" + text).strip(), started, engine="chat-completions")


def _timeout_s(session: dict) -> float:
    raw = session.get("timeout_seconds") or 180
    try:
        total = float(raw)
    except (TypeError, ValueError):
        total = 180.0
    if total < 5:
        return max(1.0, total)
    return max(5.0, total - CUSHION_S)


def run_session(session: dict, skills_dir: str) -> dict:
    started = time.monotonic()
    if not isinstance(session, dict):
        return _result(1, "SessionInput was not an object", started)
    model = os.environ.get("SKILLUP_MODEL", MODEL_DEFAULT).strip() or MODEL_DEFAULT
    gate = _gate_kib()
    if gate > 0:
        avail = _mem_available_kib()
        # The 47 GiB check is the cost of loading qwen3.6:35b. Skip it when
        # that model is already resident. A dip under the gate must not
        # abort a run we already paid to load.
        loaded = _model_loaded(model)
        if loaded is not True and (avail is None or avail < gate):
            have = "unknown" if avail is None else str(avail)
            return _result(
                1,
                "HOST-BUSY MemAvailable %s KiB is below gate %s KiB. Model was not called." % (have, gate),
                started,
            )
    if _ps_required() and _model_row(model) is None:
        return _result(1, "Ollama /api/ps failed. Model was not called.", started)
    own = _we_own_model(model)
    if shutil.which("opencode") is None:
        return _chat_fallback(session, own, started, "opencode is not on PATH")
    return _run_opencode(session, skills_dir, _timeout_s(session), own, started)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="skill-up local engine adapter")
    ap.add_argument("session_input", help="SessionInput JSON path")
    ap.add_argument("--skills-dir", default=os.environ.get("SKILLUP_SKILL_DIR", ""), help="skill tree for with_skill only")
    ap.add_argument("--output", default="", help="also write SessionResult here")
    args = ap.parse_args(argv)
    path = Path(args.session_input)
    try:
        session = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        session = {"_error": type(exc).__name__}
        result = _result(1, "could not read SessionInput: " + type(exc).__name__, time.monotonic())
    else:
        try:
            result = run_session(session, args.skills_dir)
        except Exception as exc:  # last-resort so stdout stays JSON
            result = _result(1, "adapter error: " + type(exc).__name__, time.monotonic())
    text = json.dumps(result) + "\n"
    sys.stdout.write(text)
    sys.stdout.flush()
    if args.output:
        try:
            Path(args.output).write_text(text, encoding="utf-8")
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
