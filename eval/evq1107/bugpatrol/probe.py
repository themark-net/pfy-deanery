#!/usr/bin/env python3
"""Probe bugpatrol 0.3.0 against the operator-window gap.

  python3 eval/evq1107/bugpatrol/probe.py gate
  python3 eval/evq1107/bugpatrol/probe.py live

gate is offline. live talks to Ollama and must run under scripts/model_lock.sh.
Scratch checkouts stay under ~/.cache/pfy/tools/bugpatrol/tmp. This script writes
only eval/evq1107/bugpatrol/results.json in the repo.
"""

from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
FIXTURE = OUT / "fixture"
RESULTS = OUT / "results.json"
CACHE = Path.home() / ".cache/pfy/tools/bugpatrol"
BIN = CACHE / "prefix/node_modules/.bin/bugpatrol"
FRONTEND = ROOT / "gui/operator/frontend"
TAURI = [
    ROOT / "gui/operator/src-tauri/target/release/pfy-operator",
    ROOT / "gui/operator/src-tauri/target/debug/pfy-operator",
]
PLANTED = "tauri binary absent"
MODELS = ("qwen2.5-coder:7b-instruct", "qwen3.6:35b")
GIB = 1024 ** 3
OLLAMA = shutil.which("ollama") or "/usr/local/bin/ollama"


def cache_env() -> dict[str, str]:
    home = CACHE / "home"
    env = {
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(CACHE / "xdg-config"),
        "XDG_CACHE_HOME": str(CACHE / "xdg-cache"),
        "XDG_DATA_HOME": str(home / ".local/share"),
        "XDG_STATE_HOME": str(home / ".local/state"),
        "TMPDIR": str(CACHE / "tmp"),
        "npm_config_cache": str(CACHE / "npm-cache"),
        "PLAYWRIGHT_BROWSERS_PATH": str(CACHE / "browsers"),
        "PLAYWRIGHT_SKIP_BROWSER_GC": "1",
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    if os.environ.get("PFY_MODEL_LOCK_HELD") == "1":
        env["PFY_MODEL_LOCK_HELD"] = "1"
    return env


def stopped() -> bool:
    return (ROOT / "tmp/STOP").exists()


def load_results() -> dict:
    if RESULTS.is_file():
        return json.loads(RESULTS.read_text(encoding="utf-8"))
    return {}


def save_results(data: dict) -> None:
    RESULTS.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start_server(directory: Path, port: int) -> subprocess.Popen:
    return subprocess.Popen(
        ["/usr/bin/python3", "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=directory,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def stop_server(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except OSError:
        return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=5)


def wait_http(url: str, timeout: float = 10) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"server did not answer {url}")


def git_init(path: Path) -> None:
    subprocess.run(["/usr/bin/git", "init", "-q"], cwd=path, check=True)
    subprocess.run(
        ["/usr/bin/git", "-c", "user.email=probe@localhost", "-c", "user.name=probe",
         "commit", "-q", "--allow-empty", "-m", "init"],
        cwd=path,
        check=True,
    )
    subprocess.run(
        ["/usr/bin/git", "remote", "add", "origin", "https://example.invalid/bugpatrol-probe.git"],
        cwd=path,
        check=True,
    )


def write_gate_config(root: Path, url: str, selector: str) -> None:
    ready = f'    selectors: ["{selector}"]\n' if selector else "    selectors: []\n"
    text = f"""version: 1
run:
  command: "python3 -m http.server"
  url: {url}
  ready:
{ready}    forbidConsoleErrors: true
    timeoutMs: 20000
app:
  platform: web
  source: .
viewports:
  - {{ name: desktop, width: 1440, height: 900 }}
determinism:
  image: ""
  freezeClockAt: "2026-01-01T00:00:00.000Z"
  timezone: UTC
  locale: en-US
  failOnFontFallback: false
  blockThirdPartyRequests: true
decisions:
  model:
    via: custom
    name: ""
  budget:
    perRunUsd: 0
"""
    dest = root / ".bugpatrol"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "bugpatrol.yml").write_text(text, encoding="utf-8")


def summarize_run(root: Path) -> dict:
    runs = root / ".bugpatrol" / "runs"
    if not runs.is_dir():
        return {}
    files = sorted(runs.glob("**/run.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        return {}
    payload = json.loads(files[-1].read_text(encoding="utf-8"))
    findings = []
    for item in payload.get("findings") or []:
        findings.append({
            "ruleId": item.get("ruleId"),
            "severity": item.get("severity"),
            "route": item.get("route"),
            "summary": str(item.get("summary") or "")[:240],
        })
    run = payload.get("run") or {}
    trace_path = files[-1].with_name("trace.json")
    pixels = None
    console_errors = []
    if trace_path.is_file():
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        screens = trace.get("screens") or []
        if screens:
            diff = screens[0].get("diff") or {}
            pixels = diff.get("changedPixels")
            console_errors = [str(x)[:200] for x in (screens[0].get("consoleErrors") or [])[:6]]
    blocking = [f for f in findings if f["route"] == "check"]
    return {
        "run_id": run.get("id"),
        "status": run.get("status"),
        "exit_code_recorded": run.get("exitCode"),
        "findings": len(findings),
        "blocking": len(blocking),
        "rules": [f["ruleId"] for f in findings],
        "blocking_rules": [f["ruleId"] for f in blocking],
        "summaries": [f["summary"] for f in blocking][:6],
        "changed_pixels": pixels,
        "console_errors": console_errors,
    }


def run_gate_once(root: Path, env: dict) -> dict:
    started = time.monotonic()
    try:
        proc = subprocess.run(
            [str(BIN), "run", "--no-models", "--screens", "/"],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "exit": None,
            "seconds": round(time.monotonic() - started, 3),
            "timeout": True,
            "tail": ((exc.stdout or "") + (exc.stderr or ""))[-1500:],
        }
    tail = (proc.stdout + proc.stderr)[-1500:]
    summary = summarize_run(root)
    return {
        "exit": proc.returncode,
        "seconds": round(time.monotonic() - started, 3),
        "timeout": False,
        "pass_line": next((ln.strip() for ln in proc.stdout.splitlines() if ln.startswith(("PASS", "FAIL", "INCOMPLETE"))), ""),
        "tail": tail,
        **summary,
    }


def one_target(name: str, www: Path, selector: str, mutate) -> dict:
    """mutate(phase) prepares www before that phase. phases: baseline, clean, broken."""
    port = free_port()
    url = f"http://127.0.0.1:{port}/"
    project = www.parent / f"project-{name}"
    project.mkdir(parents=True)
    git_init(project)
    write_gate_config(project, url, selector)
    server = start_server(www, port)
    phases = {}
    try:
        wait_http(url)
        env = cache_env()
        for phase in ("baseline", "clean", "broken"):
            if stopped():
                phases[phase] = {"skipped": "tmp/STOP"}
                break
            mutate(phase)
            phases[phase] = run_gate_once(project, env)
            if phases[phase].get("exit") in (None, 4) and phase == "baseline":
                break
    finally:
        stop_server(server)
    return {"url": url, "phases": phases}


def tauri_count() -> int:
    return sum(1 for path in TAURI if path.is_file())


def gate() -> None:
    if not BIN.is_file():
        raise SystemExit(f"missing {BIN}")
    scratch = CACHE / "tmp" / time.strftime("probe-%Y%m%dT%H%M%SZ", time.gmtime())
    scratch.mkdir(parents=True)
    data = load_results()
    data["tauri_binaries"] = tauri_count()
    data["frontend_files"] = sorted(p.name for p in FRONTEND.iterdir() if p.is_file()) if FRONTEND.is_dir() else []
    data["bugpatrol_version"] = subprocess.run(
        [str(BIN), "--version"], capture_output=True, text=True, env=cache_env(), check=True,
    ).stdout.strip()
    data["node"] = subprocess.run(
        ["/usr/bin/node", "--version"], capture_output=True, text=True, check=True,
    ).stdout.strip()

    fix_www = scratch / "fixture-www"
    fix_www.mkdir()
    shutil.copy(FIXTURE / "index-clean.html", fix_www / "index.html")

    def mutate_fixture(phase: str) -> None:
        src = FIXTURE / ("index-broken.html" if phase == "broken" else "index-clean.html")
        shutil.copy(src, fix_www / "index.html")

    fixture = one_target("fixture", fix_www, "[data-testid=app-root]", mutate_fixture)
    clean = fixture["phases"].get("clean") or {}
    broken = fixture["phases"].get("broken") or {}
    planted_hit = PLANTED in " ".join(broken.get("console_errors") or []) or any(
        PLANTED in (line or "") for line in (broken.get("summaries") or [])
    )
    fixture["clean_agreement"] = 1 if clean.get("exit") == 0 and not clean.get("blocking") else 0
    fixture["defect_caught"] = 1 if broken.get("exit") == 1 and (
        "runtime/console-errors" in (broken.get("blocking_rules") or []) or planted_hit
    ) else 0
    data["fixture"] = fixture

    real_www = scratch / "frontend-www"
    real_www.mkdir()
    if FRONTEND.is_dir():
        for src in FRONTEND.iterdir():
            if src.is_file():
                shutil.copy(src, real_www / src.name)

        def mutate_real(phase: str) -> None:
            # All three phases serve the copied frontend. The third is a second compare.
            return None

        data["frontend"] = one_target("frontend", real_www, "", mutate_real)
        second = data["frontend"]["phases"].get("clean") or {}
        data["frontend"]["clean_agreement"] = 1 if second.get("exit") == 0 and not second.get("blocking") else 0
        data["frontend"]["third_phase"] = "same files as the baseline; second compare, not a plant"
    else:
        data["frontend"] = {"skipped": "gui/operator/frontend missing"}
    data["scratch"] = str(scratch)
    save_results(data)
    print(json.dumps({
        "tauri_binaries": data["tauri_binaries"],
        "fixture_clean_agreement": fixture["clean_agreement"],
        "fixture_defect_caught": fixture["defect_caught"],
        "frontend_clean_agreement": (data.get("frontend") or {}).get("clean_agreement"),
    }, indent=2))


def mem_available_bytes() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    return 0


def model_size_bytes(name: str) -> int:
    proc = subprocess.run([OLLAMA, "list"], capture_output=True, text=True, check=False)
    for line in proc.stdout.splitlines()[1:]:
        parts = line.split()
        # NAME ID SIZE UNIT MODIFIED...
        if parts and parts[0] == name and len(parts) >= 4:
            return parse_size(parts[2], parts[3])
    return 0


def parse_size(number: str, unit: str) -> int:
    token = (number + unit).strip()
    mult = 1
    for suffix, factor in (("GB", 1000 ** 3), ("GiB", GIB), ("MB", 1000 ** 2), ("MiB", 1024 ** 2)):
        if token.upper().endswith(suffix.upper()):
            mult = factor
            token = token[: -len(suffix)]
            break
    try:
        return int(float(token) * mult)
    except ValueError:
        return 0


def model_loaded(name: str) -> bool:
    proc = subprocess.run([OLLAMA, "ps"], capture_output=True, text=True, check=False)
    return any(line.split() and line.split()[0] == name for line in proc.stdout.splitlines()[1:])


def wait_for_memory(need: int) -> str:
    deadline = time.monotonic() + 30 * 60
    while True:
        have = mem_available_bytes()
        if have >= need:
            return "ok"
        if time.monotonic() >= deadline or stopped():
            return "HOST-BUSY"
        time.sleep(30)


def warmup(name: str) -> dict:
    if model_loaded(name):
        return {"keep_alive": "omitted", "loaded_before": True}
    body = json.dumps({
        "model": name,
        "prompt": "ok",
        "stream": False,
        "keep_alive": "2m",
        "options": {"num_predict": 1},
    }).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=body,
        headers={"content-type": "application/json"},
    )
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=600) as resp:
        resp.read()
    return {
        "keep_alive": "2m",
        "loaded_before": False,
        "seconds": round(time.monotonic() - started, 3),
    }


def explore_once(model: str) -> dict:
    scratch = CACHE / "tmp" / time.strftime("live-%Y%m%dT%H%M%SZ", time.gmtime())
    project = scratch / "cli"
    project.mkdir(parents=True)
    (project / "window_status.py").write_text(
        "print('tauri=absent')\nprint('status=window-not-built')\n",
        encoding="utf-8",
    )
    git_init(project)
    endpoint = "http://127.0.0.1:11434/v1/chat/completions"
    use = (
        "{ runtime: model, via: custom, model: " + model
        + ", endpoint: " + endpoint + " }"
    )
    config = f"""version: 1
app:
  platform: cli
  source: .
  setup: []
  connect:
    cli: {{ timeoutMs: 60000 }}
  instructions: .bugpatrol/instructions.md
agents:
  explorer:
    maxSteps: 4
    use: {use}
  judge:
    use: {use}
  fixer:
    enabled: false
  github:
    enabled: false
  patrol:
    pull: false
"""
    (project / ".bugpatrol").mkdir()
    (project / ".bugpatrol/bugpatrol.yml").write_text(config, encoding="utf-8")
    (project / ".bugpatrol/instructions.md").write_text(
        "Run `python3 window_status.py` once with the run_command tool.\n"
        "The bug is a line tauri=absent while the command exits 0.\n"
        "If you see that line, call report_bug and quote tauri=absent.\n"
        "Do not edit files. Then finish.\n",
        encoding="utf-8",
    )
    env = cache_env()
    env["BUGPATROL_MODEL_API_KEY"] = "pfy-local-dummy"
    started = time.monotonic()
    try:
        proc = subprocess.run(
            [str(BIN), "explore", "--steps", "4",
             "--goal", "Run python3 window_status.py and report tauri=absent if it prints that."],
            cwd=project,
            env=env,
            capture_output=True,
            text=True,
            timeout=720,
        )
        out = proc.stdout + proc.stderr
        timed_out = False
        code = proc.returncode
    except subprocess.TimeoutExpired as exc:
        out = (exc.stdout or "") + (exc.stderr or "")
        timed_out = True
        code = None
    text = out if isinstance(out, str) else out.decode("utf-8", "replace")
    hosts = sorted({
        token for token in text.replace("(", " ").replace(")", " ").split()
        if token.startswith("http://") or token.startswith("https://")
    })
    off_box = [h for h in hosts if "127.0.0.1:11434" not in h and "example.invalid" not in h]
    return {
        "model": model,
        "exit": code,
        "timeout": timed_out,
        "seconds": round(time.monotonic() - started, 3),
        "tool_calls": text.count("Called "),
        "run_command": text.count("Called run_command"),
        "report_bug": text.count("Called report_bug"),
        "text_only_replies": text.count("Model replied without a tool call"),
        "candidates": candidates_of(text),
        "quoted_plant": "tauri=absent" in text,
        "off_box_urls": off_box[:8],
        "tail": text[-1800:],
    }


def candidates_of(text: str) -> int | None:
    marker = " candidate(s) raised"
    for line in text.splitlines():
        if marker in line:
            head = line.split(marker)[0].split()
            if head and head[-1].isdigit():
                return int(head[-1])
    return None


def live() -> None:
    if stopped():
        data = load_results()
        data["live"] = {"skipped": "tmp/STOP"}
        save_results(data)
        return
    attempts = []
    for model in MODELS:
        if stopped():
            attempts.append({"model": model, "skipped": "tmp/STOP"})
            break
        size = model_size_bytes(model)
        if size <= 0:
            attempts.append({"model": model, "skipped": "not in ollama list"})
            continue
        need = size + 25 * GIB
        memory = wait_for_memory(need)
        row = {"model": model, "size_bytes": size, "need_bytes": need, "memory": memory}
        if memory != "ok":
            row["skipped"] = "HOST-BUSY"
            attempts.append(row)
            continue
        try:
            row["warmup"] = warmup(model)
        except OSError as exc:
            row["warmup_error"] = str(exc)[:200]
            attempts.append(row)
            continue
        row["explore"] = explore_once(model)
        attempts.append(row)
        explore = row["explore"]
        if explore.get("tool_calls") or explore.get("candidates"):
            break
    data = load_results()
    data["live"] = {"attempts": attempts}
    save_results(data)
    print(json.dumps(data["live"], indent=2)[:4000])


def main() -> None:
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "gate"
    if cmd == "gate":
        gate()
    elif cmd == "live":
        live()
    else:
        raise SystemExit("usage: probe.py gate|live")


if __name__ == "__main__":
    main()
