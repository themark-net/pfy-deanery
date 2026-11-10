#!/usr/bin/env python3
"""GPU trial for the LEANN next gate.

Measures five clauses on the saved 216-passage set: pin under 50 MiB, no torch
wheel, no embedding weights, index smaller than the raw passages, and file
recall ahead of shadow codebase-memory. Embeddings go through a loopback
Ollama this process starts, with models under the tool cache. The caller wraps
the process in scripts/model_lock.sh on the leann lock.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
QUESTIONS = ROOT / "eval" / "evq1107" / "leann" / "questions.json"
ONCE = Path(__file__).resolve().parent / "gpu_once.py"
CPU_PROBE = ROOT / "eval" / "evq1107" / "leann" / "probe.py"
CACHE = Path.home() / ".cache" / "pfy" / "tools" / "leann"
OPS = ROOT / "tmp" / "ops" / "eval" / "evals" / "leann"
PUBLIC = ROOT / "eval" / "evals" / "leann"
PIN_LIMIT = 50 * 1024 * 1024
DOWNLOAD_CAP = 25 * 1024 * 1024 * 1024
DISK_MARGIN = 50 * 1024 * 1024 * 1024
BUSY_MAX = 30
MIN_RAM_GIB = 24


def _load_cpu_probe():
    spec = importlib.util.spec_from_file_location("leann_cpu_probe", CPU_PROBE)
    if spec is None or spec.loader is None:
        raise RuntimeError("missing cpu probe")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _scrub(text: str) -> str:
    home = str(Path.home())
    return re.sub(r"/home/[^/\s'\"]+", "~", text.replace(home, "~"))


def _dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for item in path.rglob("*"):
        if item.is_file() and not item.is_symlink():
            try:
                total += item.stat().st_size
            except OSError:
                continue
    return total


def _read_requires_torch(cache: Path) -> tuple[bool, str]:
    hits = sorted(cache.glob("venv/lib/python3.12/site-packages/leann_core-*.dist-info/METADATA"))
    if not hits:
        return False, ""
    text = hits[0].read_text(encoding="utf-8", errors="replace")
    requires = []
    for line in text.splitlines():
        if line.startswith("Requires-Dist:"):
            requires.append(line.split(":", 1)[1].strip())
    torch = any(item.lower().startswith("torch") for item in requires)
    return torch, hits[0].parent.name


def _torch_present(cache: Path) -> bool:
    site = cache / "venv" / "lib" / "python3.12" / "site-packages"
    if any(site.glob("torch-*.dist-info")):
        return True
    return any(cache.rglob("torch-*.whl"))


def _weight_bytes(cache: Path) -> int:
    roots = [cache / "st", cache / "hf", cache / "ollama"]
    total = 0
    suffixes = {".safetensors", ".bin", ".gguf", ".onnx", ".pt", ".pth", ".ggml"}
    for root in roots:
        if not root.exists():
            continue
        for item in root.rglob("*"):
            if not item.is_file() or item.is_symlink():
                continue
            try:
                size = item.stat().st_size
            except OSError:
                continue
            if item.suffix.lower() in suffixes or size >= 1_000_000:
                total += size
    return total


def measure_pin(cache: Path) -> dict:
    requires, dist_name = _read_requires_torch(cache)
    torch_dir = cache / "venv" / "lib" / "python3.12" / "site-packages" / "torch"
    return {
        "install_bytes": _dir_size(cache),
        "leann_pkg_bytes": _dir_size(cache / "venv" / "lib" / "python3.12" / "site-packages" / "leann"),
        "torch_bytes": _dir_size(torch_dir),
        "torch_required": requires,
        "torch_wheel": _torch_present(cache) or requires,
        "torch_dist": dist_name,
        "weight_bytes": _weight_bytes(cache),
        "pin_limit_bytes": PIN_LIMIT,
    }


def _gpu_busy() -> int | None:
    try:
        proc = subprocess.run(
            ["rocm-smi", "--showuse"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    nums = [int(item) for item in re.findall(r"GPU use \(%\):\s*([0-9]+)", proc.stdout)]
    if not nums:
        return None
    return max(nums)


def _vram_used() -> int | None:
    try:
        proc = subprocess.run(
            ["rocm-smi", "--showmeminfo", "vram"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    nums = [int(item) for item in re.findall(r"VRAM Total Used Memory \(B\):\s*([0-9]+)", proc.stdout)]
    if not nums:
        return None
    return max(nums)


def _ram_gib() -> int:
    text = Path("/proc/meminfo").read_text(encoding="utf-8")
    match = re.search(r"^MemAvailable:\s+(\d+)", text, re.M)
    if not match:
        return 0
    return int(match.group(1)) // 1048576


def _free_bytes(path: Path) -> int:
    path.mkdir(parents=True, exist_ok=True)
    return shutil.disk_usage(path).free


def headroom(samples: int = 3, gap_s: float = 2.0) -> dict:
    rows = []
    ok = True
    for _ in range(samples):
        busy = _gpu_busy()
        ram = _ram_gib()
        vram = _vram_used()
        rows.append({"gpu_busy_pct": busy, "ram_avail_gib": ram, "vram_used_bytes": vram})
        if busy is None or busy > BUSY_MAX or ram < MIN_RAM_GIB:
            ok = False
        if gap_s:
            time.sleep(gap_s)
    return {"ok": ok, "samples": rows}


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


def _http_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def _stop(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        proc.wait(timeout=5)


def _start_ollama(port: int, models: Path, log_path: Path) -> subprocess.Popen:
    models.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = log_path.open("w", encoding="utf-8")
    env = os.environ.copy()
    env.pop("PFY_MODEL_LOCK_HELD", None)
    env["OLLAMA_HOST"] = "127.0.0.1:%s" % port
    env["OLLAMA_MODELS"] = str(models)
    env["OLLAMA_NOPRUNE"] = "1"
    proc = subprocess.Popen(
        ["ollama", "serve"],
        env=env,
        stdout=handle,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    proc._log = handle  # type: ignore[attr-defined]
    return proc


def _pull(port: int, models: Path, name: str, log_path: Path) -> tuple[bool, str]:
    before = _dir_size(models)
    env = os.environ.copy()
    env["OLLAMA_HOST"] = "127.0.0.1:%s" % port
    env["OLLAMA_MODELS"] = str(models)
    with log_path.open("a", encoding="utf-8") as handle:
        proc = subprocess.Popen(
            ["ollama", "pull", name],
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        deadline = time.time() + 600
        while proc.poll() is None:
            growth = _dir_size(models) - before
            if growth > DOWNLOAD_CAP:
                _stop(proc)
                free_now = _free_bytes(models)
                if free_now < DISK_MARGIN:
                    return False, "no disk"
                return False, "pull exceeded 25 GB"
            if time.time() > deadline:
                _stop(proc)
                return False, "timeout"
            time.sleep(1)
    if proc.returncode != 0:
        return False, "pull exit %s" % proc.returncode
    return True, name


def _log_used_gpu(log_path: Path) -> bool:
    if not log_path.is_file():
        return False
    text = log_path.read_text(encoding="utf-8", errors="replace")
    return "using device ROCm" in text or "library=ROCm" in text and "loading model" in text


def _ping(host: str, model: str) -> tuple[bool, str]:
    body = json.dumps({"model": model, "input": "ping"}).encode("utf-8")
    req = urllib.request.Request(
        host.rstrip("/") + "/api/embed",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return False, type(exc).__name__
    embeds = payload.get("embeddings") if isinstance(payload, dict) else None
    if not embeds:
        return False, "empty embeddings"
    return True, "dim %s" % len(embeds[0])


def _passages(cpu, cache: Path) -> tuple[Path, int, str]:
    saved = cache / "probe-index" / "passages.jsonl"
    if saved.is_file():
        lines = [line for line in saved.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(lines) == 216:
            digest = hashlib.sha256(saved.read_bytes()).hexdigest()
            return saved, 216, digest
    built = OPS / "passages.jsonl"
    rows = cpu.build_passages(ROOT)
    cpu.write_passages(built, rows)
    digest = hashlib.sha256(built.read_bytes()).hexdigest()
    return built, len(rows), digest


def _hits(summary: dict, field: str) -> tuple[int, int]:
    total_h = 0
    total_n = 0
    for kind in ("prose", "code"):
        row = summary.get("%s_%s" % (kind, field)) or {}
        total_h += int(row.get("hits") or 0)
        total_n += int(row.get("n") or 0)
    return total_h, total_n


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _scrub(json.dumps(payload, indent=2) + "\n")
    path.write_text(text, encoding="utf-8")


def _verdict(doc: dict) -> dict:
    clauses = doc["clauses"]
    passed = sum(1 for value in clauses.values() if value)
    value_legs = doc["value_legs"]
    value_pass = sum(1 for value in value_legs.values() if value == "pass") >= 3
    return {
        "metric": "lightweight_pin_clauses",
        "threshold": 5,
        "clauses_passed": passed,
        "value_gate": "pass" if value_pass else "fail",
        "modularity_gate": "pass" if doc["modularity_gate"] == "pass" else "fail",
        "proposed_stage": "I1" if passed < 5 or not value_pass else "I2",
        "intent": "catalog_default",
        "pin": "v0.3.9 07796bd7e40f2d5f3a4be9e45adf1f62a68481fd",
        "clauses": clauses,
        "measured": doc["measured"],
        "value_legs": value_legs,
        "modularity_legs": doc["modularity_legs"],
        "supersede": doc["supersede"],
        "gpu": doc["gpu"],
        "reason": doc["reason"],
    }


def _report(doc: dict) -> str:
    measured = doc["measured"]
    lines = [
        "# LEANN GPU trial",
        "",
        doc["reason"],
        "",
        "The next gate stays at I1 until all five clauses pass: a pin under 50 MiB, no torch wheel, no embedding weights, an index smaller than the raw passages on this 216-passage set, and file recall ahead of shadow codebase-memory.",
        "",
        "Clauses passed: %s / 5." % doc["clauses_passed"],
        "",
        "| Clause | Result |",
        "| --- | --- |",
    ]
    for name, value in doc["clauses"].items():
        lines.append("| %s | %s |" % (name, "pass" if value else "fail"))
    lines.extend(
        [
            "",
            "Install bytes: %s. Torch package bytes: %s. Embedding-weight bytes: %s."
            % (measured.get("install_bytes"), measured.get("torch_bytes"), measured.get("weight_bytes")),
            "Passages: %s. Raw bytes: %s. Index bytes: %s."
            % (measured.get("passages"), measured.get("raw_bytes"), measured.get("index_bytes")),
            "LEANN file hits: %s / %s. Shadow codebase-memory file hits: %s / %s."
            % (
                measured.get("leann_file_hits"),
                measured.get("file_questions"),
                measured.get("cm_file_hits"),
                measured.get("file_questions"),
            ),
            "The HNSW graph file is smaller than the raw passages. The clause uses the whole catalog bundle, the same comparison as the earlier CPU probe, and that bundle is larger.",
            "Embedder: %s. Build seconds: %s. Search seconds: %s. GPU used: %s."
            % (
                measured.get("embedding_model"),
                measured.get("build_s"),
                measured.get("search_s"),
                measured.get("gpu_used"),
            ),
            "",
            "Headroom samples are in headroom.json. The embedder log is ollama.log. This file stays out of the public tree.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    OPS.mkdir(parents=True, exist_ok=True)
    cpu = _load_cpu_probe()
    pin = measure_pin(CACHE)
    room = headroom()
    _write(OPS / "headroom.json", room)
    _write(OPS / "pin.json", pin)
    free = _free_bytes(CACHE)
    doc: dict = {
        "clauses": {
            "pin_under_50mb": pin["install_bytes"] < PIN_LIMIT,
            "no_torch_wheel": not pin["torch_wheel"],
            "no_embedding_weights": pin["weight_bytes"] == 0,
            "index_smaller_than_raw": False,
            "beats_cm_file_recall": False,
        },
        "measured": {
            "install_bytes": pin["install_bytes"],
            "leann_pkg_bytes": pin["leann_pkg_bytes"],
            "torch_bytes": pin["torch_bytes"],
            "torch_required": pin["torch_required"],
            "weight_bytes": pin["weight_bytes"],
            "pin_limit_bytes": PIN_LIMIT,
            "disk_free_bytes": free,
            "passages": None,
            "raw_bytes": None,
            "index_bytes": None,
            "leann_file_hits": None,
            "cm_file_hits": None,
            "file_questions": None,
            "embedding_model": None,
            "build_s": None,
            "search_s": None,
            "gpu_used": False,
        },
        "value_legs": {
            "gap_fill": "fail",
            "operator_leverage": "fail",
            "evidence": "pass",
            "blast_radius": "fail" if pin["torch_wheel"] or pin["weight_bytes"] or pin["install_bytes"] >= PIN_LIMIT else "pass",
        },
        "modularity_gate": "pass",
        "modularity_legs": {
            "local_code_needed": "pass",
            "bounded_surface": "pass",
            "isolatable": "pass",
            "reversible": "pass",
        },
        "supersede": {
            "coverage": {
                "track": "none",
                "catalog": "none",
                "evaluate": "none",
                "integrate": "none",
            },
            "checker": {
                "parts": [],
                "coverage": {
                    "track": "none",
                    "catalog": "none",
                    "evaluate": "none",
                    "integrate": "none",
                },
                "suite": ["track", "catalog", "evaluate", "integrate"],
                "supersede_candidate": False,
            },
            "watchlist_row": False,
            "why": "Compressed local RAG. It does not track outside tools, keep a stage card per tool, score tools, or install them. No suite part is partial or full. No watchlist row.",
        },
        "gpu": room,
        "reason": "",
        "clauses_passed": 0,
    }
    doc["measured"]["disk_free_bytes"] = free
    if not room["ok"]:
        busy = room["samples"][-1]["gpu_busy_pct"] if room["samples"] else None
        ram = room["samples"][-1]["ram_avail_gib"] if room["samples"] else None
        doc["reason"] = "GPU or RAM headroom failed before the embedder started (gpu_busy_pct=%s ram_avail_gib=%s). A timeout is not a pass." % (busy, ram)
        doc["clauses_passed"] = sum(1 for value in doc["clauses"].values() if value)
        _finish(doc)
        return 0

    passages_path, passage_n, passage_sha = _passages(cpu, CACHE)
    doc["measured"]["passages"] = passage_n
    doc["measured"]["passages_sha256"] = passage_sha
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    port = _free_port()
    host = "http://127.0.0.1:%s" % port
    models = CACHE / "ollama"
    log_path = OPS / "ollama.log"
    proc = None
    vram_before = _vram_used()
    try:
        proc = _start_ollama(port, models, log_path)
        ready = False
        for _ in range(40):
            if proc.poll() is not None:
                break
            if _http_ok(host + "/api/version"):
                ready = True
                break
            time.sleep(0.5)
        if not ready:
            doc["reason"] = "private embedder did not become ready on loopback. The model was not started."
            doc["clauses_passed"] = sum(1 for value in doc["clauses"].values() if value)
            _finish(doc)
            return 0
        pulled = ""
        pull_note = ""
        for name in ("all-minilm", "nomic-embed-text"):
            ok, note = _pull(port, models, name, log_path)
            pull_note = note
            if note == "no disk":
                doc["reason"] = "no disk"
                doc["clauses_passed"] = sum(1 for value in doc["clauses"].values() if value)
                _finish(doc)
                return 0
            if ok:
                pulled = name
                break
        if not pulled:
            doc["reason"] = "embedder model pull failed (%s). No model was left running." % pull_note
            doc["clauses_passed"] = sum(1 for value in doc["clauses"].values() if value)
            _finish(doc)
            return 0
        ping_ok, ping_note = _ping(host, pulled)
        vram_after = _vram_used()
        doc["gpu"]["vram_before_bytes"] = vram_before
        doc["gpu"]["vram_after_bytes"] = vram_after
        doc["gpu"]["during"] = headroom(samples=1, gap_s=0)
        gpu_used = (
            vram_before is not None
            and vram_after is not None
            and vram_after > vram_before + 10_000_000
        )
        doc["measured"]["gpu_used"] = gpu_used
        doc["measured"]["embedding_model"] = pulled
        doc["measured"]["ping"] = ping_note if ping_ok else "ping failed: %s" % ping_note
        if not ping_ok:
            doc["reason"] = "embedder answered but the ping embedding failed (%s)." % ping_note
            doc["clauses_passed"] = sum(1 for value in doc["clauses"].values() if value)
            _finish(doc)
            return 0
        index_dir = CACHE / "gpu-index"
        if index_dir.exists():
            shutil.rmtree(index_dir)
        index_dir.mkdir(parents=True)
        adapter_out = index_dir / "adapter.json"
        venv_py = CACHE / "venv" / "bin" / "python"
        env = os.environ.copy()
        env["OLLAMA_HOST"] = "127.0.0.1:%s" % port
        env["HF_HUB_DISABLE_TELEMETRY"] = "1"
        proc_once = subprocess.run(
            [
                str(venv_py),
                str(ONCE),
                "--passages",
                str(passages_path),
                "--questions",
                str(QUESTIONS),
                "--index-dir",
                str(index_dir),
                "--out",
                str(adapter_out),
                "--host",
                host,
                "--model",
                pulled,
            ],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=1200,
            check=False,
        )
        (OPS / "gpu_once.log").write_text(
            _scrub((proc_once.stderr or "") + "\n" + (proc_once.stdout or "")),
            encoding="utf-8",
        )
        adapter = {"ok": False, "error": "no adapter output"}
        if adapter_out.is_file():
            try:
                adapter = json.loads(adapter_out.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                adapter = {"ok": False, "error": "adapter json: %s" % exc}
        if not adapter.get("ok"):
            err = _scrub(str(adapter.get("error") or proc_once.stderr or "exit %s" % proc_once.returncode))
            doc["reason"] = "index build failed: %s" % err[:400]
            doc["measured"]["weight_bytes"] = _weight_bytes(CACHE)
            doc["clauses"]["no_embedding_weights"] = doc["measured"]["weight_bytes"] == 0
            doc["clauses_passed"] = sum(1 for value in doc["clauses"].values() if value)
            _finish(doc)
            return 0
        raw_bytes = int(adapter.get("raw_bytes") or 0)
        index_bytes = int(adapter.get("index_bytes") or 0)
        cm = cpu.run_cm(questions, index_dir)
        graded = cpu.grade(questions, adapter, cm, raw_bytes)
        summary = cpu.summarize(graded["questions"])
        leann_h, leann_n = _hits(summary, "vector_hit")
        cm_h, cm_n = _hits(summary, "cm_hit")
        doc["measured"].update(
            {
                "raw_bytes": raw_bytes,
                "index_bytes": index_bytes,
                "dim": adapter.get("dim"),
                "naive_embedding_bytes": adapter.get("naive_embedding_bytes"),
                "embedding_matrix_stored": adapter.get("embedding_matrix_stored"),
                "build_s": adapter.get("build_s"),
                "search_s": adapter.get("search_s"),
                "files": adapter.get("files") or [],
                "leann_file_hits": leann_h,
                "cm_file_hits": cm_h,
                "file_questions": leann_n,
                "weight_bytes": _weight_bytes(CACHE),
                "install_bytes": _dir_size(CACHE),
            }
        )
        doc["clauses"]["pin_under_50mb"] = doc["measured"]["install_bytes"] < PIN_LIMIT
        doc["clauses"]["no_embedding_weights"] = doc["measured"]["weight_bytes"] == 0
        doc["clauses"]["index_smaller_than_raw"] = bool(raw_bytes) and index_bytes < raw_bytes and passage_n == 216
        doc["clauses"]["beats_cm_file_recall"] = bool(cm) and leann_n > 0 and cm_n == leann_n and leann_h > cm_h
        log_gpu = _log_used_gpu(log_path)
        doc["measured"]["gpu_used"] = bool(doc["measured"]["gpu_used"] or log_gpu)
        doc["measured"]["gpu_evidence"] = "rocm-device-log" if log_gpu else "vram-delta" if gpu_used else "none"
        doc["summary"] = summary
        beats = doc["clauses"]["beats_cm_file_recall"]
        doc["value_legs"]["gap_fill"] = "pass" if beats and doc["clauses"]["index_smaller_than_raw"] else "fail"
        doc["value_legs"]["operator_leverage"] = "pass" if doc["clauses"]["pin_under_50mb"] and not pin["torch_wheel"] else "fail"
        doc["value_legs"]["blast_radius"] = "fail" if pin["torch_wheel"] or doc["measured"]["weight_bytes"] or doc["measured"]["install_bytes"] >= PIN_LIMIT else "pass"
        passed = sum(1 for value in doc["clauses"].values() if value)
        doc["clauses_passed"] = passed
        doc["reason"] = (
            "STAY I1: %s of 5 lightweight-pin clauses passed on the %s-passage set. "
            "Install is %s bytes with torch_required=%s and embedding weights %s bytes. "
            "Index %s bytes vs raw %s bytes. File recall %s/%s vs shadow codebase-memory %s/%s. "
            "GPU embedder %s, gpu_used=%s."
            % (
                passed,
                passage_n,
                doc["measured"]["install_bytes"],
                pin["torch_required"],
                doc["measured"]["weight_bytes"],
                index_bytes,
                raw_bytes,
                leann_h,
                leann_n,
                cm_h,
                cm_n,
                pulled,
                doc["measured"]["gpu_used"],
            )
        )
        _finish(doc)
        return 0
    finally:
        _stop(proc)
        handle = getattr(proc, "_log", None) if proc is not None else None
        if handle is not None:
            handle.close()


def _finish(doc: dict) -> None:
    doc["clauses_passed"] = sum(1 for value in doc["clauses"].values() if value)
    if not doc["reason"]:
        doc["reason"] = "STAY I1: %s of 5 lightweight-pin clauses passed." % doc["clauses_passed"]
    verdict = _verdict(doc)
    _write(PUBLIC / "results.json", doc)
    _write(PUBLIC / "VERDICT.json", verdict)
    OPS.mkdir(parents=True, exist_ok=True)
    (OPS / "REPORT.md").write_text(_scrub(_report(doc)), encoding="utf-8")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - the lane needs a verdict, not a traceback-only exit
        OPS.mkdir(parents=True, exist_ok=True)
        (OPS / "crash.log").write_text(_scrub("%s: %s" % (type(exc).__name__, exc)), encoding="utf-8")
        fail = {
            "metric": "lightweight_pin_clauses",
            "threshold": 5,
            "clauses_passed": 0,
            "value_gate": "fail",
            "modularity_gate": "fail",
            "proposed_stage": "I1",
            "intent": "catalog_default",
            "reason": "trial crashed before a measurement: %s" % type(exc).__name__,
        }
        _write(PUBLIC / "VERDICT.json", fail)
        sys.exit(1)
