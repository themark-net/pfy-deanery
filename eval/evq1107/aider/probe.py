#!/usr/bin/env python3
"""One headless git-edit probe for aider 0.86.2.

`run` copies the fixture into a throwaway git repo and scores whatever
`--editor` does. Tests pass a stub. `live` is the Ollama step: it refuses
to start unless scripts/model_lock.sh is holding the lock, skips the editor
when memory is short, and only then runs aider. No hosted model and no key.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "mathutil.py"
MESSAGE = HERE / "message.txt"
CACHE = Path(os.environ.get("AIDER_PROBE_CACHE", str(Path.home() / ".cache" / "pfy" / "tools" / "aider")))
AIDER_BIN = CACHE / "venv" / "bin" / "aider"
LOCK = Path(os.environ.get("AIDER_PROBE_LOCK", str(ROOT / "scripts" / "model_lock.sh")))
MODEL = "qwen2.5-coder:7b-instruct"
MODEL_REF = "ollama_chat/" + MODEL
OLLAMA = "http://127.0.0.1:11434"
GIB = 1024 * 1024 * 1024
HEADROOM = 25 * GIB
PIN_VERSION = "0.86.2"
PIN_COMMIT = "253f0368b873ba30d8ee26e463718f0c03614ddf"
WHEEL_SHA256 = "64f6a0c66c9f4633ad9f479bca3e64ebcba02b9da03c6b604b74a44736b2416e"


def _opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _get_json(path: str, timeout: float) -> dict:
    req = urllib.request.Request(OLLAMA + path)
    with _opener().open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_json(path: str, body: dict, timeout: float) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA + path, data=data, headers={"Content-Type": "application/json"}
    )
    with _opener().open(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def mem_kib() -> int:
    override = os.environ.get("AIDER_PROBE_MEM_KIB")
    if override is not None:
        return int(override)
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1])
    raise RuntimeError("MemAvailable missing")


def model_size_bytes() -> int:
    override = os.environ.get("AIDER_PROBE_MODEL_BYTES")
    if override is not None:
        return int(override)
    tags = _get_json("/api/tags", 10)
    for row in tags.get("models") or []:
        name = row.get("name") or row.get("model") or ""
        if name == MODEL:
            return int(row["size"])
    raise RuntimeError("model not in ollama list: " + MODEL)


def model_loaded() -> bool:
    if os.environ.get("AIDER_PROBE_SKIP_OLLAMA") == "1":
        return os.environ.get("AIDER_PROBE_PRELOADED") == "1"
    ps = _get_json("/api/ps", 10)
    for row in ps.get("models") or []:
        name = row.get("name") or row.get("model") or ""
        if name == MODEL or name.startswith(MODEL):
            return True
    return False


def child_env(home: Path, gitconfig: Path) -> dict[str, str]:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config").mkdir(parents=True, exist_ok=True)
    (home / "cache").mkdir(parents=True, exist_ok=True)
    (home / "tmp").mkdir(parents=True, exist_ok=True)
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / "config"),
        "XDG_CACHE_HOME": str(home / "cache"),
        "TMPDIR": str(home / "tmp"),
        "GIT_CONFIG_GLOBAL": str(gitconfig),
        "GIT_CONFIG_SYSTEM": str(gitconfig),
        "GIT_AUTHOR_NAME": "Aider Probe",
        "GIT_AUTHOR_EMAIL": "probe@example.invalid",
        "GIT_COMMITTER_NAME": "Aider Probe",
        "GIT_COMMITTER_EMAIL": "probe@example.invalid",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
        "LITELLM_LOCAL_MODEL_COST_MAP": "True",
        "OLLAMA_API_BASE": OLLAMA,
        "NO_COLOR": "1",
    }


def git(work: Path, env: dict[str, str], *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=work,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def prepare(work: Path, env: dict[str, str]) -> None:
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    shutil.copyfile(FIXTURE, work / "mathutil.py")
    git(work, env, "init", "-q")
    git(work, env, "config", "--local", "user.name", "Aider Probe")
    git(work, env, "config", "--local", "user.email", "probe@example.invalid")
    git(work, env, "config", "--local", "commit.gpgsign", "false")
    git(work, env, "add", "mathutil.py")
    git(work, env, "commit", "-q", "-m", "base")


def score(work: Path, env: dict[str, str]) -> dict:
    path = work / "mathutil.py"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "import mathutil\n"
            "raise SystemExit(0 if mathutil.add(2, 2) == 4 else 1)\n",
        ],
        cwd=work,
        env={
            "PATH": "/usr/bin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(work),
            "LANG": "C.UTF-8",
        },
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    try:
        count = int(
            subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                cwd=work,
                env=env,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
        new_commits = count - 1
    except (subprocess.CalledProcessError, ValueError):
        new_commits = None
    fixed = (
        proc.returncode == 0
        and "return a + b" in text
        and "return a - b" not in text
    )
    return {
        "correct_edits": 1 if fixed else 0,
        "add_2_2_ok": proc.returncode == 0,
        "new_commits": new_commits,
        "git_edit": 1 if fixed and new_commits and new_commits >= 1 else 0,
        "mathutil_excerpt": text[:500],
    }


def aider_argv(binary: Path, home: Path) -> list[str]:
    return [
        str(binary),
        "--model",
        MODEL_REF,
        "--weak-model",
        MODEL_REF,
        "--edit-format",
        "whole",
        "--no-show-model-warnings",
        "--no-check-model-accepts-settings",
        "--no-analytics",
        "--no-check-update",
        "--no-show-release-notes",
        "--disable-playwright",
        "--no-gitignore",
        "--no-auto-lint",
        "--no-suggest-shell-commands",
        "--no-detect-urls",
        "--no-fancy-input",
        "--no-stream",
        "--no-pretty",
        "--no-notifications",
        "--map-tokens",
        "0",
        "--yes-always",
        "--timeout",
        "180",
        "--line-endings",
        "lf",
        "--message-file",
        str(MESSAGE),
        "--input-history-file",
        str(home / "input.history"),
        "--chat-history-file",
        str(home / "chat.history.md"),
        "mathutil.py",
    ]


def executable(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def ensure_lock() -> None:
    if os.environ.get("PFY_MODEL_LOCK_HELD") == "1":
        return
    os.execv(str(LOCK), [str(LOCK), sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]])


def wait_for_memory(need: int) -> bool:
    deadline = time.monotonic() + float(os.environ.get("AIDER_PROBE_WAIT_SEC", "1800"))
    while True:
        avail = mem_kib() * 1024
        if avail >= need:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(min(15.0, max(0.0, deadline - time.monotonic())))


def preload() -> None:
    _post_json(
        "/api/generate",
        {
            "model": MODEL,
            "prompt": "ok",
            "stream": False,
            "keep_alive": "2m",
            "options": {"num_predict": 1},
        },
        180,
    )


def write_results(path: Path, body: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def base_body() -> dict:
    venv = CACHE / "venv"
    venv_bytes = None
    if venv.is_dir():
        total = 0
        for dirpath, _dirs, files in os.walk(venv):
            for name in files:
                try:
                    total += (Path(dirpath) / name).stat().st_size
                except OSError:
                    pass
        venv_bytes = total
    return {
        "tool": "aider",
        "pin": PIN_VERSION,
        "commit": PIN_COMMIT,
        "wheel_sha256": WHEEL_SHA256,
        "model": MODEL,
        "venv_bytes": venv_bytes,
        "gap_b_closed": 0,
        "fixture_sha256": hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
    }


def redact(text: str) -> str:
    kept = []
    for line in text.splitlines():
        low = line.lower()
        if "api_key" in low or "phc_" in low or "bearer " in low or "sk-" in low:
            kept.append("[redacted]")
        else:
            kept.append(line)
    return "\n".join(kept)[-4000:]


def run_editor(cmd: list[str], work: Path, env: dict[str, str], out: Path) -> int:
    if not executable(Path(cmd[0])):
        print("editor missing: " + cmd[0], file=sys.stderr)
        return 2
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=work,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=420,
            check=False,
        )
        elapsed = round(time.perf_counter() - started, 4)
        editor_exit: int | None = proc.returncode
        tail = redact(proc.stdout + "\n" + proc.stderr)
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        elapsed = round(time.perf_counter() - started, 4)
        editor_exit = None
        out_s = exc.stdout or ""
        err_s = exc.stderr or ""
        if isinstance(out_s, bytes):
            out_s = out_s.decode("utf-8", "replace")
        if isinstance(err_s, bytes):
            err_s = err_s.decode("utf-8", "replace")
        tail = redact(out_s + "\n" + err_s + "\nTIMEOUT")
        timed_out = True
    scored = score(work, env)
    body = base_body()
    body.update(scored)
    body.update(
        {
            "status": "pass" if scored["git_edit"] == 1 and not timed_out else "miss",
            "editor_exit": editor_exit,
            "editor_seconds": elapsed,
            "editor_tail": tail,
            "timed_out": timed_out,
            "host_busy": False,
            "keep_alive_sent": False,
        }
    )
    write_results(out, body)
    print(
        "correct_edits={correct_edits} git_edit={git_edit} new_commits={new_commits} seconds={seconds}".format(
            correct_edits=scored["correct_edits"],
            git_edit=scored["git_edit"],
            new_commits=scored["new_commits"],
            seconds=elapsed,
        )
    )
    return 0


def skip_result(out: Path, reason: str) -> int:
    body = base_body()
    body.update(
        {
            "status": "SKIPPED",
            "reason": reason,
            "correct_edits": 0,
            "git_edit": 0,
            "new_commits": 0,
            "host_busy": False,
            "keep_alive_sent": False,
        }
    )
    write_results(out, body)
    print("SKIPPED " + reason, file=sys.stderr)
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    if not args.editor:
        print("run needs --editor", file=sys.stderr)
        return 2
    # `run` is the stub path. The real binary is a model call and must use `live`.
    banned = Path(os.environ.get("AIDER_PROBE_AIDER_BIN", str(AIDER_BIN)))
    if Path(args.editor).resolve() == banned.resolve():
        print("refusing run on the aider binary; use live", file=sys.stderr)
        return 2
    home = Path(args.home)
    gitconfig = Path(args.gitconfig) if args.gitconfig else home / "gitconfig"
    gitconfig.parent.mkdir(parents=True, exist_ok=True)
    gitconfig.write_text("", encoding="utf-8")
    env = child_env(home, gitconfig)
    prepare(args.work, env)
    return run_editor([args.editor], args.work, env, args.out)


def cmd_live(args: argparse.Namespace) -> int:
    ensure_lock()
    if (ROOT / "tmp" / "STOP").exists():
        print("tmp/STOP present", file=sys.stderr)
        return 3
    home = Path(args.home)
    gitconfig = Path(args.gitconfig) if args.gitconfig else home / "gitconfig"
    gitconfig.parent.mkdir(parents=True, exist_ok=True)
    gitconfig.write_text("", encoding="utf-8")
    env = child_env(home, gitconfig)
    work = args.work
    prepare(work, env)
    loaded = False
    keep_alive_sent = False
    try:
        loaded = model_loaded()
    except Exception as exc:
        return skip_result(args.out, "ollama ps failed: " + type(exc).__name__)
    if not loaded:
        try:
            need = model_size_bytes() + HEADROOM
        except Exception as exc:
            return skip_result(args.out, "model size failed: " + type(exc).__name__)
        if not wait_for_memory(need):
            scored = score(work, env)
            body = base_body()
            body.update(scored)
            body.update(
                {
                    "status": "HOST-BUSY",
                    "correct_edits": 0,
                    "git_edit": 0,
                    "host_busy": True,
                    "keep_alive_sent": False,
                    "model_loaded_before": False,
                    "mem_kib": mem_kib(),
                    "need_bytes": need,
                }
            )
            write_results(args.out, body)
            print("HOST-BUSY", file=sys.stderr)
            return 0
        if os.environ.get("AIDER_PROBE_PRELOAD_FAIL") == "1":
            return skip_result(args.out, "preload failed")
        if os.environ.get("AIDER_PROBE_SKIP_OLLAMA") != "1":
            try:
                preload()
            except Exception as exc:
                return skip_result(args.out, "preload failed: " + type(exc).__name__)
            keep_alive_sent = True
    editor = Path(args.editor) if args.editor else AIDER_BIN
    if args.editor:
        cmd = [args.editor]
    else:
        cmd = aider_argv(editor, home)
    code = run_editor(cmd, work, env, args.out)
    if code == 0 and args.out.is_file():
        body = json.loads(args.out.read_text(encoding="utf-8"))
        body["keep_alive_sent"] = keep_alive_sent
        body["model_loaded_before"] = loaded
        args.out.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="aider headless git-edit probe")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("run", "live"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--editor", default="")
        cmd.add_argument("--work", type=Path, required=True)
        cmd.add_argument("--out", type=Path, required=True)
        cmd.add_argument("--home", type=Path, required=True)
        cmd.add_argument("--gitconfig", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.cmd == "run":
        return cmd_run(args)
    return cmd_live(args)


if __name__ == "__main__":
    sys.exit(main())
