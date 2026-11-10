#!/usr/bin/env python3
"""One localhost llama-server completion on the local GPU.

Does not clone or fork a tree, does not download weights, and does not
signal any process it did not start. Binds 127.0.0.1 only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path


BUSY_MAX = 30
MIN_RAM_GIB = 24
HEALTH_WAIT_S = 90
COMPLETION_TIMEOUT_S = 60
PROMPT = "What is the capital of France? Answer with one word."


def ram_avail_gib() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) // 1048576
    return 0


def gpu_sample() -> dict:
    proc = subprocess.run(
        ["rocm-smi", "--showuse", "--showmemuse"],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    use = re.search(r"GPU use \(%\):\s*(\d+)", proc.stdout)
    vram = re.search(r"VRAM%\):\s*(\d+)", proc.stdout)
    return {
        "use_pct": int(use.group(1)) if use else None,
        "vram_pct": int(vram.group(1)) if vram else None,
        "ram_avail_gib": ram_avail_gib(),
        "rc": proc.returncode,
    }


def headroom_ok(sample: dict) -> bool:
    use = sample.get("use_pct")
    ram = sample.get("ram_avail_gib")
    return use is not None and ram is not None and use <= BUSY_MAX and ram >= MIN_RAM_GIB


def wait_headroom(max_waits: int, pause_s: float) -> tuple[list[dict], bool]:
    samples = []
    for i in range(max_waits + 1):
        sample = gpu_sample()
        samples.append(sample)
        if headroom_ok(sample):
            # Three clear samples, matching the lane driver, before a start.
            if len(samples) >= 3 and all(headroom_ok(s) for s in samples[-3:]):
                return samples, True
        elif i < max_waits:
            time.sleep(pause_s)
            continue
        if i < max_waits:
            time.sleep(pause_s)
    return samples, False


def scrub(text: str) -> str:
    return re.sub(r"/home/[A-Za-z_][A-Za-z0-9_-]*", "<home>", text)


def scrub_obj(value):
    if isinstance(value, str):
        return scrub(value)
    if isinstance(value, list):
        return [scrub_obj(item) for item in value]
    if isinstance(value, dict):
        return {str(k): scrub_obj(v) for k, v in value.items()}
    return value


def run_text(cmd: list[str], env: dict | None = None, timeout: int = 30) -> str:
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=env,
    )
    return scrub((proc.stdout or "") + (proc.stderr or ""))


def device_lines(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("Available devices"):
            continue
        if "load_backend:" in stripped or stripped.startswith("version:"):
            continue
        if "MiB" in stripped or stripped.startswith("ROCm") or stripped.startswith("CUDA") or stripped.startswith("Vulkan"):
            lines.append(stripped)
    return lines


def version_line(text: str) -> str:
    for line in text.splitlines():
        if "version:" in line:
            return line.split("version:", 1)[1].strip()
    return ""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


def http_json(method: str, url: str, body: dict | None, timeout: float) -> tuple[int, dict | str]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            code = int(resp.status)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        code = int(exc.code)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, scrub(str(exc))
    try:
        return code, json.loads(raw)
    except json.JSONDecodeError:
        return code, scrub(raw[:500])


class Sampler:
    def __init__(self) -> None:
        self.samples: list[dict] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> list[dict]:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=5)
        return self.samples

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.samples.append(gpu_sample())
            except (OSError, subprocess.TimeoutExpired):
                pass
            self._stop.wait(0.5)


def stop_process(proc: subprocess.Popen | None) -> bool:
    if proc is None or proc.poll() is not None:
        return proc is not None
    try:
        os.killpg(proc.pid, 15)
    except ProcessLookupError:
        return True
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and proc.poll() is None:
        time.sleep(0.1)
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, 9)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            return False
    return True


def parse_log(text: str) -> dict:
    off = re.findall(r"offloaded (\d+)/(\d+) layers to GPU", text)
    buffers = re.findall(r"ROCm0 model buffer size =\s+([0-9.]+) MiB", text)
    cpu_buffers = re.findall(r"CPU model buffer size =\s+([0-9.]+) MiB", text)
    pp = re.findall(r"prompt eval time =.*?([0-9.]+) tokens per second", text)
    # "prompt eval time" also contains "eval time". The decode line is indented.
    dec = re.findall(r" {4}eval time =.*?([0-9.]+) tokens per second", text)
    devices = []
    for line in text.splitlines():
        if "ROCm" in line or "assigned to device" in line or "using device" in line:
            devices.append(scrub(line.strip())[:240])
    return {
        "offloaded": [f"{a}/{b}" for a, b in off],
        "rocm_buffer_mib": [float(x) for x in buffers],
        "cpu_buffer_mib": [float(x) for x in cpu_buffers],
        "prompt_tok_s": [float(x) for x in pp],
        "decode_tok_s": [float(x) for x in dec],
        "device_lines": devices[:12],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bin", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--backend-so", required=True)
    parser.add_argument("--stock-bin", default="/usr/bin/llama-server")
    parser.add_argument("--out", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--ctx", type=int, default=2048)
    parser.add_argument("--max-waits", type=int, default=30)
    args = parser.parse_args()

    model = Path(args.model)
    backend = Path(args.backend_so)
    binary = Path(args.bin)
    out = Path(args.out)
    log_path = Path(args.log)
    out.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    receipt: dict = {
        "forked_into_repo": False,
        "download_bytes": 0,
        "timeout": False,
        "model_started": False,
        "port_bound": False,
        "stopped": False,
        "host": "127.0.0.1",
    }

    def finish(code: int) -> int:
        out.write_text(json.dumps(scrub_obj(receipt), indent=2) + "\n", encoding="utf-8")
        return code

    if not binary.is_file() or not model.is_file() or not backend.is_file():
        receipt["error"] = "missing bin, model, or backend"
        return finish(2)
    magic = model.read_bytes()[:4]
    receipt["model"] = {
        "bytes": model.stat().st_size,
        "sha256": sha256_file(model),
        "gguf_magic": magic == b"GGUF",
        "label": "qwen2.5-coder-1.5b-q4km",
    }
    usage = shutil.disk_usage(model.parent)
    receipt["disk"] = {"avail_bytes": usage.free, "total_bytes": usage.total}

    stock_env = os.environ.copy()
    stock_text = run_text([args.stock_bin, "--list-devices"]) if Path(args.stock_bin).is_file() else ""
    stock_ver = run_text([args.stock_bin, "--version"]) if Path(args.stock_bin).is_file() else ""
    receipt["stock_debian"] = {
        "present": Path(args.stock_bin).is_file(),
        "version": version_line(stock_ver),
        "device_lines": device_lines(stock_text),
    }

    hip_env = os.environ.copy()
    lib_dir = str(backend.parent)
    bin_dir = str(binary.parent)
    previous = hip_env.get("LD_LIBRARY_PATH", "")
    hip_env["HSA_OVERRIDE_GFX_VERSION"] = "11.5.1"
    hip_env["GGML_BACKEND_PATH"] = str(backend)
    hip_env["LD_LIBRARY_PATH"] = lib_dir + ":" + bin_dir + ((":" + previous) if previous else "")
    hip_env["GGML_CUDA_ENABLE_UNIFIED_MEMORY"] = "1"
    hip_env["GGML_HIP_UMA"] = "1"
    hip_text = run_text([str(binary), "--list-devices"], env=hip_env)
    hip_ver = run_text([str(binary), "--version"], env=hip_env)
    devices = device_lines(hip_text)
    receipt["hip"] = {
        "version": version_line(hip_ver),
        "backend_so": str(backend),
        "binary": str(binary),
        "device_lines": devices,
        "ngl": 999,
        "fit": "off",
        "no_mmap": True,
        "ctx": args.ctx,
        "hsa_override_gfx_version": "11.5.1",
    }

    samples, clear = wait_headroom(args.max_waits, 5)
    receipt["gpu_preflight"] = {
        "samples": samples[-6:],
        "clear": clear,
        "busy_max_pct": BUSY_MAX,
        "min_ram_gib": MIN_RAM_GIB,
        "waits": max(0, len(samples) - 3),
    }
    if not clear or not devices:
        receipt["error"] = "no headroom" if not clear else "no hip device"
        return finish(1)

    port = free_port()
    receipt["port"] = port
    cmd = [
        str(binary),
        "--model",
        str(model),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--no-mmap",
        "-fit",
        "off",
        "-ngl",
        "999",
        "-c",
        str(args.ctx),
        "-np",
        "1",
        "-fa",
        "on",
        "-lv",
        "5",
        "--no-webui",
        "--alias",
        "llama-cpp-server-mode",
    ]
    log_handle = log_path.open("w", encoding="utf-8")
    proc = None
    sampler = Sampler()
    started = time.monotonic()
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=hip_env,
        )
        receipt["model_started"] = True
        receipt["pid"] = proc.pid
        sampler.start()
        healthy = False
        deadline = time.monotonic() + HEALTH_WAIT_S
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                break
            code, payload = http_json("GET", f"http://127.0.0.1:{port}/health", None, 2)
            if code == 200:
                healthy = True
                receipt["health"] = payload if isinstance(payload, dict) else {"raw": payload}
                break
            time.sleep(0.4)
        receipt["load_seconds"] = round(time.monotonic() - started, 3)
        receipt["port_bound"] = healthy
        if not healthy:
            receipt["timeout"] = proc.poll() is None
            receipt["error"] = "server exited" if proc.poll() is not None else "health timeout"
        else:
            code, models = http_json("GET", f"http://127.0.0.1:{port}/v1/models", None, 10)
            ids = []
            if isinstance(models, dict):
                for row in models.get("data") or []:
                    if isinstance(row, dict) and row.get("id"):
                        ids.append(str(row["id"]))
            receipt["models"] = {"http": code, "ids": ids}

            body = {
                "model": "llama-cpp-server-mode",
                "messages": [{"role": "user", "content": PROMPT}],
                "temperature": 0,
                "max_tokens": 16,
            }
            t0 = time.monotonic()
            code, completion = http_json(
                "POST",
                f"http://127.0.0.1:{port}/v1/chat/completions",
                body,
                COMPLETION_TIMEOUT_S,
            )
            latency = round(time.monotonic() - t0, 3)
            content = ""
            finish_reason = ""
            completion_tokens = 0
            if isinstance(completion, dict):
                choices = completion.get("choices") or []
                if choices and isinstance(choices[0], dict):
                    message = choices[0].get("message") or {}
                    content = str(message.get("content") or "")
                    finish_reason = str(choices[0].get("finish_reason") or "")
                usage = completion.get("usage") or {}
                if isinstance(usage, dict):
                    completion_tokens = int(usage.get("completion_tokens") or 0)
            elif code == 0:
                receipt["timeout"] = True
            receipt["completion"] = {
                "http": code,
                "latency_s": latency,
                "completion_tokens": completion_tokens,
                "finish_reason": finish_reason,
                "content": scrub(content)[:200],
                "paris": "paris" in content.lower(),
            }
    finally:
        during = sampler.stop()
        receipt["gpu_during"] = {
            "n": len(during),
            "use_pct_max": max((s.get("use_pct") or 0) for s in during) if during else None,
            "vram_pct_max": max((s.get("vram_pct") or 0) for s in during) if during else None,
            "samples_head": during[:4],
            "samples_tail": during[-4:],
        }
        receipt["stopped"] = stop_process(proc)
        log_handle.close()

    log_text = scrub(log_path.read_text(encoding="utf-8", errors="replace"))
    parsed = parse_log(log_text)
    receipt["log"] = parsed
    receipt["log_tail"] = "\n".join(log_text.splitlines()[-25:])
    off_ok = False
    for item in parsed["offloaded"]:
        done, total = item.split("/")
        if int(done) > 0 and int(done) == int(total):
            off_ok = True
    model_ids = (receipt.get("models") or {}).get("ids") or []
    models_ok = (receipt.get("models") or {}).get("http") == 200 and bool(model_ids)
    comp = receipt.get("completion") or {}
    comp_ok = (
        comp.get("http") == 200
        and int(comp.get("completion_tokens") or 0) >= 1
        and bool(str(comp.get("content") or "").strip())
        and not receipt.get("timeout")
    )
    receipt["checks"] = {
        "hip_offload": off_ok,
        "models_endpoint": bool(models_ok),
        "completion": bool(comp_ok),
    }
    receipt["gpu_server_checks"] = sum(1 for ok in receipt["checks"].values() if ok)
    return finish(0 if receipt["gpu_server_checks"] == 3 else 1)


if __name__ == "__main__":
    raise SystemExit(main())
