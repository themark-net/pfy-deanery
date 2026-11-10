#!/usr/bin/env python3
"""Single-flight and GPU-wait decisions for the litellm eval lane.

The pure functions are what the exit tests call. run_trial is the one-shot
probe: it does not edit a stage card.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

BUSY_GPU_PCT = 30
MIN_FREE_RAM_GIB = 24
WAIT_POLLS = 15
WAIT_POLL_SECONDS = 60
SMOKE_MODEL = "deepseek-coder:latest"
# The smoke client talks OpenAI-style to Ollama. Port 11435 is checked, not assumed:
# an existing proxy there may not list the smoke model, and this lane does not restart it.
OLLAMA_V1 = "http://127.0.0.1:11434/v1"
PROXY_MODELS = "http://127.0.0.1:11435/v1/models"
OLLAMA_TAGS = "http://127.0.0.1:11434/api/tags"
OLLAMA_PS = "http://127.0.0.1:11434/api/ps"


def second_run_may_start(lock_held: bool, state_exists: bool) -> bool:
    """A second run starts nothing when the model lock or the state file is set."""
    return not lock_held and not state_exists


def decide_gpu_wait(samples: list, polls: int, poll_seconds: int) -> dict:
    """Start only when the latest sample is idle. Busy for the whole budget is a non-pass."""
    last = samples[-1] if samples else {}
    gpu = last.get("gpu_use_pct")
    ram = last.get("free_ram_gib")
    measured = {"gpu_use_pct": gpu, "free_ram_gib": ram}
    busy = _sample_busy(last)
    if not busy:
        return {"action": "start", "start_model": True, "measured": measured}
    elapsed = polls * poll_seconds
    if elapsed >= WAIT_POLLS * WAIT_POLL_SECONDS:
        return {"action": "non_pass", "start_model": False, "measured": measured}
    return {"action": "wait", "start_model": False, "measured": measured}


def _sample_busy(sample: dict) -> bool:
    gpu = sample.get("gpu_use_pct")
    ram = sample.get("free_ram_gib")
    if isinstance(gpu, bool) or not isinstance(gpu, (int, float)):
        return True
    if isinstance(ram, bool) or not isinstance(ram, (int, float)):
        return True
    return gpu > BUSY_GPU_PCT or ram < MIN_FREE_RAM_GIB


def state_file() -> Path:
    override = os.environ.get("PFY_LITELLM_STATE")
    if override:
        return Path(override)
    return Path.home() / ".cache" / "pfy" / "tools" / "litellm" / "next_gate.state"


def other_lock_held() -> bool:
    """True when some other process holds the model lock.

    A nested command inside scripts/model_lock.sh sees PFY_MODEL_LOCK_HELD=1.
    That process already owns the lock, so it is not a second run.
    """
    if os.environ.get("PFY_MODEL_LOCK_HELD") == "1":
        return False
    raw = os.environ.get("PFY_MODEL_LOCK")
    path = Path(raw) if raw else Path.home() / ".cache" / "pfy" / "locks" / "local-model.lock"
    if not path.is_file():
        return False
    import fcntl

    fd = os.open(path, os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return True
    else:
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)


def _run(cmd: list[str], timeout: int = 20) -> str:
    proc = subprocess.run(
        cmd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return proc.stdout or ""


def sample_host() -> tuple[dict, str]:
    """One rocm-smi plus free -g sample. Missing numbers count as busy."""
    try:
        rocm = _run(["rocm-smi", "--showuse", "--showmemuse"])
    except (OSError, subprocess.TimeoutExpired) as exc:
        rocm = "rocm-smi failed: %s" % type(exc).__name__
    try:
        freeg = _run(["free", "-g"])
    except (OSError, subprocess.TimeoutExpired) as exc:
        freeg = "free failed: %s" % type(exc).__name__
    gpu_nums = [int(item) for item in re.findall(r"GPU use \(%\):\s*([0-9]+)", rocm)]
    vram_nums = [int(item) for item in re.findall(r"GPU Memory Allocated \(VRAM%\):\s*([0-9]+)", rocm)]
    ram = _available_gib(freeg)
    sample = {
        "gpu_use_pct": max(gpu_nums) if gpu_nums else None,
        "free_ram_gib": ram,
        "vram_pct": max(vram_nums) if vram_nums else None,
    }
    return sample, rocm + "\n" + freeg


def _available_gib(text: str) -> int | None:
    for line in text.splitlines():
        if not line.startswith("Mem:"):
            continue
        parts = line.split()
        if len(parts) >= 7:
            try:
                return int(parts[6])
            except ValueError:
                return None
    return None


def wait_until_clear(sample_fn, sleep_fn, max_polls: int = WAIT_POLLS, poll_seconds: int = WAIT_POLL_SECONDS):
    samples = []
    raws = []
    decision = decide_gpu_wait([{"gpu_use_pct": None, "free_ram_gib": None}], polls=max_polls, poll_seconds=poll_seconds)
    for poll in range(1, max_polls + 1):
        sample, raw = sample_fn()
        samples.append(sample)
        raws.append(raw)
        decision = decide_gpu_wait(samples, polls=poll, poll_seconds=poll_seconds)
        if decision["action"] != "wait":
            break
        sleep_fn(poll_seconds)
    return decision, samples, raws


def _read_json(url: str, timeout: float = 5.0) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            data = json.loads(resp.read().decode("utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def model_present(name: str) -> dict | None:
    data = _read_json(OLLAMA_TAGS)
    if not data:
        return None
    for row in data.get("models") or []:
        if isinstance(row, dict) and row.get("name") == name:
            return {"name": name, "size": row.get("size"), "digest": row.get("digest")}
    return None


def loaded_vram(name: str) -> int | None:
    data = _read_json(OLLAMA_PS)
    if not data:
        return None
    for row in data.get("models") or []:
        if not isinstance(row, dict):
            continue
        if row.get("name") == name or row.get("model") == name:
            try:
                return int(row.get("size_vram") or 0)
            except (TypeError, ValueError):
                return None
    return None


def product_surface(root: Path) -> dict:
    makefile = (root / "Makefile").read_text(encoding="utf-8")
    help_body, _, rest = makefile.partition("\nhelp:\n")
    del help_body
    platform_split = rest.split("\nhelp-platform:\n", 1)
    help_text = platform_split[0]
    platform_text = platform_split[1] if len(platform_split) > 1 else ""
    on_default = "smoke-litellm-ollama" in help_text
    on_platform = "smoke-litellm-ollama" in platform_text
    env_text = (root / "scripts" / "env-stage.sh").read_text(encoding="utf-8")
    soft_skip = False
    for line in env_text.splitlines():
        if "smoke-litellm-ollama" in line and "||" in line:
            soft_skip = True
    product_ship = "smoke-litellm-ollama" in (root / "scripts" / "product-ship.sh").read_text(encoding="utf-8")
    onboard = "smoke-litellm-ollama" in (root / "scripts" / "product-onboard.sh").read_text(encoding="utf-8")
    required = on_default or product_ship or onboard or ("smoke-litellm-ollama" in env_text and not soft_skip)
    example = root / "examples" / "litellm-ollama" / "smoke_completion.py"
    card = root / "data" / "stages" / "litellm.json"
    return {
        "product_lever": required,
        "probe_on_platform_help": on_platform,
        "on_default_help": on_default,
        "env_stage_soft_skip": soft_skip,
        "local_code_needed": example.is_file(),
        "bounded_surface": example.is_file(),
        "isolatable": not required,
        "reversible": card.is_file(),
    }


def disk_facts(cache: Path) -> dict:
    cache.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(cache).free
    return {
        "disk_free_bytes": free,
        "download_over_25gb": False,
        "download_blocked": False,
        "download_bytes": 0,
    }


def _short_error(stderr: str) -> str:
    lines = [line.strip() for line in _scrub(stderr).splitlines() if line.strip()]
    if not lines:
        return ""
    return lines[-1][:240]


def _scrub(text: str) -> str:
    home = str(Path.home())
    if home:
        text = text.replace(home, "~")
    return text


def _claim_state(path: Path) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("smoke-litellm-ollama\n")
    return True


def _venv_python() -> str:
    override = os.environ.get("PFY_LITELLM_PYTHON")
    if override:
        return override
    path = Path.home() / ".cache" / "pfy" / "tools" / "litellm" / "venv" / "bin" / "python"
    return str(path) if path.is_file() else ""


def _tool_version(python: str) -> str:
    if not python:
        return ""
    proc = subprocess.run(
        [python, "-c", "import importlib.metadata as m; print(m.version('litellm'))"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=30,
    )
    return (proc.stdout or "").strip()


def _complete(root: Path, python: str, during: list) -> dict:
    code = (
        "import json,os,time,litellm\n"
        "litellm.suppress_debug_info = True\n"
        "t=time.perf_counter()\n"
        "resp=litellm.completion(\n"
        " model='openai/'+os.environ['LITELLM_MODEL'],\n"
        " api_base=os.environ['LITELLM_BASE'],\n"
        " api_key='ollama',\n"
        " messages=[{'role':'user','content':'Reply with exactly one word: pong'}],\n"
        " max_tokens=16, temperature=0, timeout=90)\n"
        "text=(resp.choices[0].message.content or '').strip()\n"
        "json.dump({'text':text,'elapsed_s':round(time.perf_counter()-t,4)}, __import__('sys').stdout)\n"
    )
    env = os.environ.copy()
    env["LITELLM_MODEL"] = SMOKE_MODEL
    env["LITELLM_BASE"] = OLLAMA_V1
    env["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
    cmd = ["bash", str(root / "scripts" / "model_lock.sh"), python, "-c", code]
    proc = subprocess.Popen(
        cmd,
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 120
    timed_out = False
    while proc.poll() is None:
        sample, _raw = sample_host()
        sample["size_vram"] = loaded_vram(SMOKE_MODEL)
        during.append(sample)
        if time.monotonic() >= deadline:
            timed_out = True
            proc.kill()
            break
        time.sleep(0.5)
    out, err = proc.communicate(timeout=10)
    result = {"returncode": proc.returncode, "timeout": timed_out, "stdout": out or "", "stderr": err or ""}
    if timed_out:
        result["parsed"] = None
        return result
    try:
        result["parsed"] = json.loads(out)
    except json.JSONDecodeError:
        result["parsed"] = None
    return result


def _write_verdict(path: Path, measured: dict, extra: dict) -> None:
    from scripts.litellm_verdict_writer import build_verdict

    doc = json.loads(build_verdict("litellm", measured))
    doc.update(extra)
    doc.pop("integration_stage", None)
    doc.pop("tier_ceiling", None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def _reason(measured: dict) -> str:
    gpu = measured.get("gpu_use_pct")
    ram = measured.get("free_ram_gib")
    if measured.get("second_run"):
        return (
            "Non-pass. A second litellm run saw the model lock or the per-tool state file "
            "and did not start a download or a model. GPU use %s percent, %s GiB available."
            % (gpu, ram)
        )
    if measured.get("reason_code") == "model-or-package-missing":
        return (
            "Non-pass. The smoke model or the cache LiteLLM package was not already present. "
            "No download started. GPU use %s percent, %s GiB available."
            % (gpu, ram)
        )
    if not measured.get("start_model"):
        return (
            "Non-pass. GPU use stayed above 30 percent or available RAM stayed under 24 GiB "
            "for the wait budget. Measured GPU use %s percent and %s GiB available. No model started."
            % (gpu, ram)
        )
    if measured.get("download_blocked"):
        return "STAY. no disk"
    if measured.get("timeout"):
        return (
            "Non-pass. The LiteLLM completion timed out. GPU use %s percent, %s GiB available. "
            "A timeout is not a pass."
            % (gpu, ram)
        )
    if measured.get("completion_ok") and measured.get("gpu_used") and not measured.get("product_lever"):
        return (
            "Propose I3. probe_not_product_lever is 1. smoke-litellm-ollama stays on platform help "
            "and off the product help. env-stage soft-skips it. LiteLLM %s completed openai/%s "
            "against the already listening Ollama OpenAI endpoint in %ss. Preflight GPU use %s percent, "
            "%s GiB available. During-call GPU use max %s percent, size_vram %s. No download and no new port."
            % (
                measured.get("tool_version") or "unknown",
                SMOKE_MODEL,
                measured.get("elapsed_s"),
                gpu,
                ram,
                measured.get("gpu_use_max_pct"),
                measured.get("size_vram"),
            )
        )
    return (
        "Non-pass. The probe did not show a GPU completion that stays off the product surface. "
        "completion_ok=%s gpu_used=%s product_lever=%s GPU use %s percent, %s GiB available."
        % (
            measured.get("completion_ok"),
            measured.get("gpu_used"),
            measured.get("product_lever"),
            gpu,
            ram,
        )
    )


def run_trial(root: Path, verdict_path: Path, log_dir: Path) -> dict:
    log_dir.mkdir(parents=True, exist_ok=True)
    surface = product_surface(root)
    cache = Path.home() / ".cache" / "pfy" / "tools" / "litellm"
    disk = disk_facts(cache)
    state = state_file()
    lock_held = other_lock_held()
    may_start = second_run_may_start(lock_held=lock_held, state_exists=state.is_file())
    base = {
        **surface,
        **disk,
        "timeout": False,
        "start_model": False,
        "completion_ok": False,
        "gpu_used": False,
        "second_run": not may_start,
        "model": SMOKE_MODEL,
        "completion_base": OLLAMA_V1,
    }
    if not may_start:
        sample, raw = sample_host()
        (log_dir / "gpu-blocked.txt").write_text(_scrub(raw), encoding="utf-8")
        measured = {**base, "gpu_use_pct": sample.get("gpu_use_pct"), "free_ram_gib": sample.get("free_ram_gib")}
        measured["reason_code"] = "second-run"
        _write_verdict(verdict_path, measured, {"reason": _reason(measured)})
        _write_report(log_dir / "REPORT.md", measured, _reason(measured))
        return measured

    if not _claim_state(state):
        sample, raw = sample_host()
        (log_dir / "gpu-blocked.txt").write_text(_scrub(raw), encoding="utf-8")
        measured = {
            **base,
            "second_run": True,
            "gpu_use_pct": sample.get("gpu_use_pct"),
            "free_ram_gib": sample.get("free_ram_gib"),
            "reason_code": "second-run",
        }
        _write_verdict(verdict_path, measured, {"reason": _reason(measured)})
        _write_report(log_dir / "REPORT.md", measured, _reason(measured))
        return measured

    decision, samples, raws = wait_until_clear(sample_host, time.sleep)
    (log_dir / "gpu-wait.txt").write_text(_scrub("\n".join(raws)), encoding="utf-8")
    last = decision["measured"]
    measured = {
        **base,
        "gpu_use_pct": last.get("gpu_use_pct"),
        "free_ram_gib": last.get("free_ram_gib"),
        "vram_pct": samples[-1].get("vram_pct") if samples else None,
        "wait_action": decision["action"],
        "wait_polls": len(samples),
    }
    if not decision["start_model"]:
        measured["reason_code"] = "gpu-busy"
        _write_verdict(verdict_path, measured, {"reason": _reason(measured)})
        _write_report(log_dir / "REPORT.md", measured, _reason(measured))
        return measured

    row = model_present(SMOKE_MODEL)
    measured["model_present"] = row is not None
    if row:
        measured["model_bytes"] = row.get("size")
        measured["model_digest"] = row.get("digest")
    proxy = _read_json(PROXY_MODELS)
    proxy_ids = []
    if proxy:
        proxy_ids = [item.get("id") for item in proxy.get("data") or [] if isinstance(item, dict) and item.get("id")]
    measured["proxy_model_ids"] = proxy_ids
    measured["smoke_model_on_proxy"] = SMOKE_MODEL in proxy_ids
    python = _venv_python()
    measured["tool_version"] = _tool_version(python)
    if row is None or not python or not measured["tool_version"]:
        measured["reason_code"] = "model-or-package-missing"
        measured["start_model"] = False
        _write_verdict(verdict_path, measured, {"reason": _reason(measured)})
        _write_report(log_dir / "REPORT.md", measured, _reason(measured))
        return measured

    during: list[dict] = []
    completed = _complete(root, python, during)
    (log_dir / "completion.stdout.txt").write_text(_scrub(completed["stdout"]), encoding="utf-8")
    (log_dir / "completion.stderr.txt").write_text(_scrub(completed["stderr"])[-4000:], encoding="utf-8")
    (log_dir / "gpu-during.json").write_text(json.dumps(during, indent=2) + "\n", encoding="utf-8")
    parsed = completed["parsed"] if isinstance(completed["parsed"], dict) else {}
    text = str(parsed.get("text") or "")
    vram_values = [item.get("size_vram") for item in during if isinstance(item.get("size_vram"), int) and item.get("size_vram") > 0]
    after_vram = loaded_vram(SMOKE_MODEL)
    if isinstance(after_vram, int) and after_vram > 0:
        vram_values.append(after_vram)
    size_vram = max(vram_values) if vram_values else 0
    after_sample, after_raw = sample_host()
    (log_dir / "gpu-after.txt").write_text(_scrub(after_raw), encoding="utf-8")
    gpu_values = [item.get("gpu_use_pct") for item in during if isinstance(item.get("gpu_use_pct"), int)]
    if isinstance(after_sample.get("gpu_use_pct"), int):
        gpu_values.append(after_sample["gpu_use_pct"])
    gpu_max = max(gpu_values) if gpu_values else measured.get("gpu_use_pct")
    pre = measured.get("gpu_use_pct")
    gpu_used = size_vram > 0 or (isinstance(gpu_max, int) and isinstance(pre, int) and gpu_max > pre)
    measured.update(
        {
            "start_model": True,
            "timeout": bool(completed["timeout"]),
            "completion_ok": bool(text) and not completed["timeout"] and completed["returncode"] == 0,
            "elapsed_s": parsed.get("elapsed_s"),
            "answer_chars": len(text),
            "answer": _scrub(text[:80]),
            "completion_error": "" if text and not completed["timeout"] and completed["returncode"] == 0 else _short_error(completed["stderr"]),
            "gpu_use_max_pct": gpu_max,
            "size_vram": size_vram,
            "gpu_used": gpu_used,
            "processes_started": ["model_lock completion"],
            "processes_stopped": ["model_lock completion"],
        }
    )
    _write_verdict(verdict_path, measured, {"reason": _reason(measured)})
    _write_report(log_dir / "REPORT.md", measured, _reason(measured))
    return measured


def _write_report(path: Path, measured: dict, reason: str) -> None:
    lines = [
        "# LiteLLM GPU eval",
        "",
        reason,
        "",
        "The card was not edited. integration_stage and tier_ceiling stay out of the verdict.",
        "",
        "Intake was `duplicate litellm data/stages/litellm.json`. No second card.",
        "Supersede check with track, catalog, evaluate, and integrate at none was not a candidate. No watchlist row.",
        "",
        "The full cage smoke was not started. That target recreates the agent cage. Port 11435 already belonged to a LiteLLM process, so it was not restarted. The completion used LiteLLM against the Ollama server already listening on 127.0.0.1:11434.",
        "",
        "```json",
        json.dumps({key: measured[key] for key in sorted(measured)}, indent=2, default=str),
        "```",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_scrub("\n".join(lines)), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--verdict", default="eval/evals/litellm/VERDICT.json")
    parser.add_argument("--log-dir", default="tmp/ops/eval/evals/litellm")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    measured = run_trial(root, root / args.verdict, root / args.log_dir)
    return 0 if measured.get("completion_ok") and not measured.get("product_lever") else 1


if __name__ == "__main__":
    raise SystemExit(main())
