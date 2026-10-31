#!/usr/bin/env python3
"""Entry 089 local-inference bench on nimo. Stdlib only. Cite #230 for the case set.

For each Ollama model: inventory, cold load, prompt+decode tok/s, then the same
48 labeled Choice cases in data/decision-gates/laya-trial.cases.v0.json at gate
0.85. Parse-fail or confidence < gate → escalate. No silent auto-act.

Fail closed: Ollama unreachable, or a requested model name missing from /api/tags.
If a model is present but fails to load or stalls >30 min, drop it and continue.
Never pulls weights. Unloads with keep_alive:0. Does not change BIOS/kernel.

Usage:
  python3 examples/local-bench/bench.py
  python3 examples/local-bench/bench.py --check
  python3 examples/local-bench/bench.py --base-url http://127.0.0.1:11434 --models qwen2.5-coder:1.5b
"""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES_REL = Path("data/decision-gates/laya-trial.cases.v0.json")
RECEIPT_REL = Path("pipelines/dogfood/local-bench/receipt.json")
ISSUE = "#230"
ENTRY = "089"
DEFAULT_GATE = 0.85
DEFAULT_BASE = "http://127.0.0.1:11434"
DEFAULT_NUM_CTX = 2048
DEFAULT_STALL_S = 1800
DEFAULT_MIN_MEM_GB = 16.0  # Entry 091: raised after nimo lockup; abort under 16 GiB MemAvailable
REQUIRED_MODELS = (
    "qwen2.5-coder:1.5b",
    "glm-4.7-flash:latest",
    "qwen3-coder:30b",
)
STRETCH_MODEL = "qwen3-coder-next:latest"
SKIP_MODELS = ()  # Entry 091: Mark raised MemoryHigh to 85G; gpt-oss / Air in scope
BASELINES = {
    "cua-s1-forms": {
        "accuracy": 0.5625,
        "accuracy_pct": "56.3%",
        "n_correct": 27,
        "n_cases": 48,
        "escalate_rate": 0.2292,
        "escalate_pct": "22.9%",
        "n_escalate": 11,
        "wrong_but_confident": 16,
        "note": "CUA-S1-FORMS default local lane (Entry 086 trial)",
    },
    "laya-english": {
        "accuracy": 0.625,
        "accuracy_pct": "62.5%",
        "n_correct": 30,
        "n_cases": 48,
        "escalate_rate": 1.0,
        "escalate_pct": "100%",
        "n_escalate": 48,
        "wrong_but_confident": 0,
        "note": "laya:english never cleared 0.85 (Entry 086 trial)",
    },
}
JSON_RE = re.compile(r"\{[^{}]*\}", re.S)
FILLER = ("alpha bravo charlie delta echo foxtrot golf hotel india juliet " * 42).strip()

EXIT_OK = 0
EXIT_BROKEN = 1
EXIT_CANNOT_RUN = 2


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ollama_base(cli_base: str | None = None) -> str:
    raw = (
        cli_base
        or os.environ.get("OLLAMA_HOST")
        or os.environ.get("OLLAMA_BASE_URL")
        or DEFAULT_BASE
    )
    base = raw.strip().rstrip("/")
    if base.endswith("/v1"):
        base = base[: -len("/v1")]
    if "://" not in base:
        base = "http://" + base
    return base


def http_json(method: str, url: str, body=None, timeout: float = 30):
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Accept": "application/json", "User-Agent": "pfy-local-bench/089"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", "replace")
        return resp.status, json.loads(raw) if raw else {}


def fail_closed(reason: str, code: int = EXIT_CANNOT_RUN, extra=None) -> int:
    rec = {
        "verdict": "FAIL_CANNOT_RUN" if code == EXIT_CANNOT_RUN else "FAIL",
        "reason": reason,
        "issue": ISSUE,
        "entry": ENTRY,
        "catalog_hold": "70-75",
        "feature_go": False,
    }
    if extra:
        rec.update(extra)
    print(json.dumps(rec, ensure_ascii=False))
    return code


def meminfo() -> dict:
    out = {}
    path = Path("/proc/meminfo")
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        out[k.strip()] = v.strip()
    return out


def mem_available_gb(info: dict | None = None) -> float | None:
    blob = info if info is not None else meminfo()
    raw = blob.get("MemAvailable") or blob.get("MemFree")
    if not raw:
        return None
    try:
        kb = float(raw.split()[0])
    except (TypeError, ValueError, IndexError):
        return None
    return round(kb / (1024 * 1024), 3)


def mem_total_gb(info: dict | None = None) -> float | None:
    blob = info if info is not None else meminfo()
    raw = blob.get("MemTotal")
    if not raw:
        return None
    try:
        kb = float(raw.split()[0])
    except (TypeError, ValueError, IndexError):
        return None
    return round(kb / (1024 * 1024), 3)


def read_sysfs_int(path: Path) -> int | None:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def drm_mem() -> dict:
    cards = []
    drm = Path("/sys/class/drm")
    if not drm.is_dir():
        return {"cards": cards}
    for card_dir in sorted(drm.glob("card*")):
        if not card_dir.name[4:].isdigit():
            continue
        dev = card_dir / "device"
        vram_total = read_sysfs_int(dev / "mem_info_vram_total")
        if vram_total is None:
            continue
        cards.append(
            {
                "card": card_dir.name,
                "vram_total_bytes": vram_total,
                "vram_used_bytes": read_sysfs_int(dev / "mem_info_vram_used"),
                "gtt_total_bytes": read_sysfs_int(dev / "mem_info_gtt_total"),
                "gtt_used_bytes": read_sysfs_int(dev / "mem_info_gtt_used"),
                "vis_vram_total_bytes": read_sysfs_int(dev / "mem_info_vis_vram_total"),
            }
        )
    ttm = {}
    for name in ("pages_limit", "page_pool_size"):
        n = read_sysfs_int(Path("/sys/module/ttm/parameters") / name)
        if n is not None:
            ttm[name] = n
    gttsize = read_sysfs_int(Path("/sys/module/amdgpu/parameters/gttsize"))
    return {"cards": cards, "ttm": ttm, "amdgpu_gttsize": gttsize}


def bytes_gib(n: int | None) -> float | None:
    if n is None:
        return None
    return round(n / (1024**3), 3)


def free_h() -> str:
    try:
        p = subprocess.run(["free", "-h"], capture_output=True, text=True, timeout=5)
        return (p.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def ollama_version_cli() -> str | None:
    try:
        p = subprocess.run(["ollama", "--version"], capture_output=True, text=True, timeout=5)
        text = ((p.stdout or "") + (p.stderr or "")).strip()
        return text or None
    except (OSError, subprocess.TimeoutExpired):
        return None


def ollama_ps_cli() -> str:
    try:
        p = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=10)
        return (p.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def parse_ollama_ps(text: str) -> list[dict]:
    lines = [ln for ln in (text or "").splitlines() if ln.strip()]
    if len(lines) < 2:
        return []
    header = re.split(r"\s{2,}", lines[0].strip())
    rows = []
    for ln in lines[1:]:
        parts = re.split(r"\s{2,}", ln.strip())
        rec = {}
        for i, key in enumerate(header):
            rec[key.lower()] = parts[i] if i < len(parts) else ""
        if rec:
            rows.append(rec)
    return rows


def proc_status(pid: int) -> dict:
    path = Path("/proc/%s/status" % pid)
    out = {"pid": pid, "rss_kb": None, "hwm_kb": None, "name": None}
    if not path.is_file():
        return out
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("Name:"):
                out["name"] = line.split(":", 1)[1].strip()
            elif line.startswith("VmRSS:"):
                out["rss_kb"] = int(line.split()[1])
            elif line.startswith("VmHWM:"):
                out["hwm_kb"] = int(line.split()[1])
    except (OSError, ValueError, IndexError):
        return out
    return out


def _proc_exe(pid: int) -> str:
    try:
        return os.readlink("/proc/%s/exe" % pid)
    except OSError:
        return ""



def resolve_outdir(outdir_arg: str | None, receipt_path: Path) -> Path:
    """CLI --outdir must be absolute so relative paths survive chdir."""
    if outdir_arg:
        return Path(outdir_arg).resolve()
    return Path(receipt_path).resolve().parent


def log_path_for_receipt(log_path: Path, root: Path | None = None) -> str:
    """Repo-relative when the resolved log is inside the repo; absolute otherwise.

    Path.relative_to raises ValueError for an out-of-tree outdir. That used to
    escape into bench_one and record DROP. Recovery is the absolute resolved
    path, including when the input still contains '..' or a symlink.
    """
    root = root or ROOT
    try:
        resolved = log_path.resolve()
    except OSError:
        resolved = Path(os.path.abspath(log_path))
    try:
        return str(resolved.relative_to(root.resolve()))
    except ValueError:
        return str(resolved)

def is_ollama_exe(exe: str) -> bool:
    """Match the Ollama binary / llama-server, not a parent whose argv quotes those words."""
    e = (exe or "").lower()
    return "ollama" in e or "llama-server" in e


def _cmdline_argv0(pid: int) -> str:
    """Argv0 for cross-user runners when /proc/<pid>/exe is EACCES (ollama service user)."""
    try:
        raw = Path("/proc/%s/cmdline" % pid).read_bytes()
    except OSError:
        return ""
    if not raw:
        return ""
    return raw.split(b"\x00", 1)[0].decode("utf-8", "replace")


def _proc_comm(pid: int) -> str:
    try:
        return Path("/proc/%s/comm" % pid).read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def is_ollama_runner_proc(pid: int, exe: str = "") -> bool:
    """True for ollama / llama-server. Prefer exe; if unreadable, match argv0 path or comm only."""
    if is_ollama_exe(exe):
        return True
    # Cross-user: mark cannot read ollama-owned /proc/*/exe — do NOT scan full cmdline text.
    argv0 = _cmdline_argv0(pid)
    if argv0 and is_ollama_exe(argv0):
        return True
    comm = _proc_comm(pid)
    return comm in ("llama-server", "ollama")


def ollama_runner_stats() -> list[dict]:
    """RSS of Ollama / llama-server processes (incl. ollama-user runners mark cannot readlink)."""
    found = []
    proc = Path("/proc")
    if not proc.is_dir():
        return found
    for p in proc.iterdir():
        if not p.name.isdigit():
            continue
        pid = int(p.name)
        exe = _proc_exe(pid)
        if not is_ollama_runner_proc(pid, exe):
            continue
        try:
            cmd = (p / "cmdline").read_bytes().replace(b"\x00", b" ").decode("utf-8", "replace")
        except OSError:
            cmd = exe or _cmdline_argv0(pid)
        st = proc_status(pid)
        st["cmd"] = (cmd or exe).strip()[:240]
        st["exe"] = (exe or _cmdline_argv0(pid) or "").lower()
        name = Path(st["exe"]).name if st["exe"] else _proc_comm(pid)
        st["is_runner"] = name in ("llama-server", "runner") or "llama-server" in name
        found.append(st)
    return found


class PeakSampler:
    def __init__(self, interval: float = 0.25):
        self.interval = interval
        self.stop = threading.Event()
        self.peak_rss_kb = 0
        self.peak_hwm_kb = 0
        self.samples = 0
        self.last = []
        self._thread = threading.Thread(target=self._loop, name="rss-sampler", daemon=True)

    def start(self):
        self._thread.start()
        return self

    def _loop(self):
        while not self.stop.is_set():
            rows = ollama_runner_stats()
            self.last = rows
            for rec in rows:
                rss = rec.get("rss_kb") or 0
                hwm = rec.get("hwm_kb") or 0
                if rec.get("is_runner") or rss:
                    self.peak_rss_kb = max(self.peak_rss_kb, rss)
                    self.peak_hwm_kb = max(self.peak_hwm_kb, hwm)
            self.samples += 1
            self.stop.wait(self.interval)

    def finish(self) -> dict:
        self.stop.set()
        self._thread.join(timeout=2)
        return {
            "peak_rss_kb": self.peak_rss_kb or None,
            "peak_hwm_kb": self.peak_hwm_kb or None,
            "samples": self.samples,
            "last": self.last,
        }


def toks_per_s(count, duration_ns) -> float | None:
    try:
        c = float(count)
        d = float(duration_ns)
    except (TypeError, ValueError):
        return None
    if c <= 0 or d <= 0:
        return None
    return round(c / (d / 1e9), 3)


def timings_from(blob: dict) -> dict:
    load_ns = blob.get("load_duration")
    pp_n = blob.get("prompt_eval_count")
    pp_ns = blob.get("prompt_eval_duration")
    ev_n = blob.get("eval_count")
    ev_ns = blob.get("eval_duration")
    return {
        "load_duration_ns": load_ns,
        "load_duration_s": None if load_ns is None else round(float(load_ns) / 1e9, 4),
        "prompt_eval_count": pp_n,
        "prompt_eval_duration_ns": pp_ns,
        "prompt_eval_tok_s": toks_per_s(pp_n, pp_ns),
        "eval_count": ev_n,
        "eval_duration_ns": ev_ns,
        "eval_tok_s": toks_per_s(ev_n, ev_ns),
        "total_duration_ns": blob.get("total_duration"),
        "total_duration_s": None
        if blob.get("total_duration") is None
        else round(float(blob["total_duration"]) / 1e9, 4),
    }


def extract_json_object(text: str) -> str | None:
    if not text:
        return None
    s = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, re.S | re.I)
    if fence:
        return fence.group(1)
    if s.startswith("{") and s.endswith("}"):
        return s
    # last complete object wins if the model wrapped chatter around it
    matches = list(JSON_RE.finditer(s))
    if matches:
        return matches[-1].group(0)
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        return s[start : end + 1]
    return None


def parse_choice_json(text: str, criteria_keys=None) -> dict:
    """Parse {"choice": "...", "confidence": 0..1}. Parse fail is escalate, not a crash."""
    keys = list(criteria_keys or [])
    rec = {
        "parse_ok": False,
        "choice": None,
        "confidence": 0.0,
        "error": None,
        "raw": (text or "")[:800],
    }
    blob_s = extract_json_object(text or "")
    if not blob_s:
        rec["error"] = "no JSON object"
        return rec
    try:
        blob = json.loads(blob_s)
    except json.JSONDecodeError as e:
        rec["error"] = "json: %s" % e
        return rec
    if not isinstance(blob, dict):
        rec["error"] = "JSON is not an object"
        return rec
    choice = blob.get("choice")
    if choice is None:
        rec["error"] = "missing choice"
        rec["raw_obj_keys"] = sorted(blob.keys())
        return rec
    choice_s = str(choice).strip()
    if keys:
        lowered = {k.lower(): k for k in keys}
        if choice_s in keys:
            choice_s = choice_s
        elif choice_s.lower() in lowered:
            choice_s = lowered[choice_s.lower()]
    conf_raw = blob.get("confidence")
    try:
        conf = float(conf_raw)
    except (TypeError, ValueError):
        rec["error"] = "confidence not a number"
        rec["choice"] = choice_s
        return rec
    if conf > 1.0 and conf <= 100.0:
        conf = conf / 100.0
    if conf < 0:
        conf = 0.0
    rec["parse_ok"] = True
    rec["choice"] = choice_s
    rec["confidence"] = round(conf, 4)
    rec["error"] = None
    rec["extra_keys"] = sorted(k for k in blob.keys() if k not in ("choice", "confidence"))
    return rec


def score_case(case: dict, parsed: dict, gate: float, latency_s: float | None, error=None) -> dict:
    label = case.get("label")
    parse_ok = bool(parsed.get("parse_ok"))
    choice = parsed.get("choice") if parse_ok else None
    conf = float(parsed.get("confidence") or 0.0) if parse_ok else 0.0
    ran = error is None
    escalate = (not parse_ok) or (conf < gate) or (choice is None)
    correct = bool(ran and parse_ok and choice == label)
    return {
        "id": case.get("id"),
        "ran": ran,
        "parse_ok": parse_ok,
        "choice": choice,
        "label": label,
        "correct": correct,
        "confidence": conf,
        "escalate": escalate,
        "chip_conf": "conf ok" if (parse_ok and conf >= gate) else "conf low",
        "latency_s": latency_s,
        "error": error or (None if parse_ok else parsed.get("error")),
        "raw": parsed.get("raw"),
    }


def percentile(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    if len(s) == 1:
        return round(s[0], 4)
    k = (len(s) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return round(s[f], 4)
    return round(s[f] + (s[c] - s[f]) * (k - f), 4)


def summarize_rows(rows: list, gate: float) -> dict:
    n = len(rows)
    ran = [r for r in rows if r.get("ran")]
    n_ran = len(ran)
    correct = sum(1 for r in ran if r.get("correct"))
    esc = [r for r in ran if r.get("escalate")]
    held = [r for r in ran if not r.get("escalate")]
    wrong_conf = [r for r in ran if (not r.get("correct")) and (not r.get("escalate"))]
    lat = [float(r["latency_s"]) for r in ran if r.get("latency_s") is not None]
    parse_ok_rows = [r for r in ran if r.get("parse_ok")]
    n_parse_ok = len(parse_ok_rows)
    return {
        "n_cases": n,
        "n_ran": n_ran,
        "n_error": n - n_ran,
        "parse_ok": n_parse_ok,
        "parse_ok_rate": None if not n_ran else round(n_parse_ok / n_ran, 4),
        "accuracy": None if not n_ran else round(correct / n_ran, 4),
        "n_correct": correct,
        "escalate_rate": None if not n_ran else round(len(esc) / n_ran, 4),
        "n_escalate": len(esc),
        "n_held": len(held),
        "held_accuracy": None if not held else round(sum(1 for r in held if r.get("correct")) / len(held), 4),
        "wrong_but_confident": len(wrong_conf),
        "wrong_but_confident_ids": [r["id"] for r in wrong_conf],
        "latency_s": {
            "all_p50": percentile(lat, 50),
            "all_p95": percentile(lat, 95),
            "n": len(lat),
        },
        "gate": gate,
        "errors": [{"id": r["id"], "error": r.get("error")} for r in rows if not r.get("ran")],
    }


def decision_prompt(case: dict) -> str:
    keys = list((case.get("criteria") or {}).keys())
    return (
        "You are a typed Choice decision engine, not a chatbot.\n"
        "Pick exactly one criterion key. Confidence is a calibrated margin in 0..1, "
        "never percent-correct.\n"
        "Answer with ONLY JSON: {\"choice\":\"<one of the criteria keys>\",\"confidence\":0..1}\n"
        "No markdown. No extra keys. No explanation.\n\n"
        "INSTRUCTIONS:\n%s\n\n"
        "STATE:\n%s\n\n"
        "CRITERIA (keys: %s):\n%s\n"
        % (
            case.get("instructions") or "",
            json.dumps(case.get("state"), ensure_ascii=False, indent=2),
            ", ".join(keys),
            json.dumps(case.get("criteria"), ensure_ascii=False, indent=2),
        )
    )


def inventory_snippet(base: str, include_ps: bool = True) -> dict:
    info = meminfo()
    drm = drm_mem()
    cards = []
    for c in drm.get("cards") or []:
        cards.append(
            {
                **c,
                "vram_total_gib": bytes_gib(c.get("vram_total_bytes")),
                "vram_used_gib": bytes_gib(c.get("vram_used_bytes")),
                "gtt_total_gib": bytes_gib(c.get("gtt_total_bytes")),
                "gtt_used_gib": bytes_gib(c.get("gtt_used_bytes")),
            }
        )
    version = None
    try:
        _st, ver = http_json("GET", base.rstrip("/") + "/api/version", timeout=5)
        version = (ver or {}).get("version")
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, socket.timeout):
        version = None
    ps_text = ollama_ps_cli() if include_ps else ""
    api_ps = None
    if include_ps:
        try:
            _st, api_ps = http_json("GET", base.rstrip("/") + "/api/ps", timeout=5)
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, socket.timeout):
            api_ps = None
    return {
        "hostname": socket.gethostname(),
        "ollama_version": version,
        "ollama_version_cli": ollama_version_cli(),
        "base_url": base,
        "free_h": free_h(),
        "mem_total_gb": mem_total_gb(info),
        "mem_available_gb": mem_available_gb(info),
        "meminfo": {k: info.get(k) for k in ("MemTotal", "MemAvailable", "MemFree", "SwapTotal", "SwapFree") if k in info},
        "drm": {"cards": cards, "ttm": drm.get("ttm"), "amdgpu_gttsize": drm.get("amdgpu_gttsize")},
        "ollama_ps": ps_text,
        "ollama_ps_rows": parse_ollama_ps(ps_text),
        "api_ps": api_ps,
        "captured": now(),
    }


def ping_ollama(base: str, timeout: float = 5) -> tuple[bool, str, dict | None]:
    url = base.rstrip("/") + "/api/version"
    try:
        status, data = http_json("GET", url, timeout=timeout)
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, socket.timeout) as e:
        return False, "Ollama unreachable at %s: %s" % (url, e), None
    if status != 200 or not isinstance(data, dict) or not data.get("version"):
        return False, "Ollama version endpoint odd at %s status=%s body=%s" % (url, status, data), data
    return True, data.get("version"), data


def list_tags(base: str, timeout: float = 15) -> list[dict]:
    status, data = http_json("GET", base.rstrip("/") + "/api/tags", timeout=timeout)
    if status != 200 or not isinstance(data, dict):
        raise RuntimeError("tags status=%s" % status)
    return list(data.get("models") or [])


def model_names(tags: list[dict]) -> set[str]:
    names = set()
    for m in tags:
        n = m.get("name") or m.get("model")
        if n:
            names.add(n)
            if ":" not in n:
                names.add(n + ":latest")
            if n.endswith(":latest"):
                names.add(n[: -len(":latest")])
    return names


def tag_record(tags: list[dict], name: str) -> dict | None:
    want = {name, name + ":latest" if ":" not in name else name}
    if name.endswith(":latest"):
        want.add(name[: -len(":latest")])
    for m in tags:
        n = m.get("name") or m.get("model")
        if n in want:
            return m
    return None


def generate(base: str, model: str, prompt: str, *, timeout: float, num_ctx: int, num_predict: int,
             keep_alive, format_json: bool, temperature: float = 0.0, think=False) -> dict:
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": keep_alive,
        "options": {
            "num_ctx": num_ctx,
            "num_predict": num_predict,
            "temperature": temperature,
        },
    }
    if format_json:
        body["format"] = "json"
    if think is False:
        body["think"] = False
    url = base.rstrip("/") + "/api/generate"
    try:
        status, data = http_json("POST", url, body=body, timeout=timeout)
        return {"ok": status == 200, "status": status, "data": data, "error": None}
    except urllib.error.HTTPError as e:
        raw = ""
        try:
            raw = e.read().decode("utf-8", "replace")[:800]
        except OSError:
            raw = ""
        if think is False and e.code in (400, 422) and "think" in raw.lower():
            return generate(
                base, model, prompt, timeout=timeout, num_ctx=num_ctx, num_predict=num_predict,
                keep_alive=keep_alive, format_json=format_json, temperature=temperature, think=None,
            )
        return {"ok": False, "status": e.code, "data": None, "error": "HTTP %s %s" % (e.code, raw)}
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, socket.timeout) as e:
        return {"ok": False, "status": None, "data": None, "error": str(e)}


def unload(base: str, model: str, timeout: float = 60) -> dict:
    return generate(
        base, model, "", timeout=timeout, num_ctx=512, num_predict=1,
        keep_alive=0, format_json=False, think=None,
    )


def write_json(path: Path, blob: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(blob, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_log(path: Path, line: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line.rstrip() + "\n")


def load_cases(path: Path) -> dict:
    blob = json.loads(path.read_text(encoding="utf-8"))
    cases = list(blob.get("cases") or [])
    if len(cases) != 48:
        raise RuntimeError("expected 48 cases, got %s in %s" % (len(cases), path))
    return blob


def recommend(models_out: list[dict]) -> dict:
    """What to run on nimo now. Not a Feature GO. CUA-S1-FORMS stays default decision."""
    usable = [m for m in models_out if m.get("verdict") == "RAN"]
    by_name = {m["name"]: m for m in usable}

    def tok(m, key):
        speed = (m.get("speed") or {}).get(key)
        return speed

    small = by_name.get("qwen2.5-coder:1.5b")
    glm = by_name.get("glm-4.7-flash:latest")
    qwen30 = by_name.get("qwen3-coder:30b")
    nextm = by_name.get(STRETCH_MODEL)

    now_run = []
    if small:
        now_run.append("qwen2.5-coder:1.5b — small fast baseline for smokes / tight loops")
    # Prefer the 30B MoE with better held accuracy / fewer wbc, else the faster one.
    moe_ranked = []
    for m in (glm, qwen30):
        if not m:
            continue
        acc = m.get("decision") or {}
        moe_ranked.append((acc.get("held_accuracy") or 0, -(acc.get("wrong_but_confident") or 99), tok(m, "eval_tok_s") or 0, m["name"]))
    moe_ranked.sort(reverse=True)
    if moe_ranked:
        now_run.append("%s — 30B-class MoE for local coding workers (this bench)" % moe_ranked[0][3])
    if nextm:
        now_run.append("%s — stretch only; measured this run" % STRETCH_MODEL)
    else:
        now_run.append("skip gpt-oss:120b (65 GB > 64 GiB VRAM carve); skip qwen3-coder-next unless stretch ran")

    return {
        "run_on_nimo_now": now_run,
        "default_decision_lane": "cua-s1-forms",
        "not_a_feature_go": True,
        "catalog_hold": "70-75",
        "note": "Local LLM tok/s and Choice accuracy do not replace CUA-S1-FORMS. Confidence is a margin chip.",
    }


def bench_one(base: str, model: str, cases: list, args, outdir: Path, deadline: float) -> dict:
    log_path = outdir / ("%s.log" % model.replace("/", "_").replace(":", "_"))
    cases_path = outdir / ("%s-cases.jsonl" % model.replace("/", "_").replace(":", "_"))
    rec = {
        "name": model,
        "verdict": None,
        "started": now(),
        "inventory_before": inventory_snippet(base),
    }
    avail = rec["inventory_before"].get("mem_available_gb")
    if avail is not None and avail < args.min_mem_available_gb:
        rec["verdict"] = "STOP_MEM"
        rec["reason"] = "MemAvailable %.3f GiB < %.3f GiB; not loading %s" % (
            avail, args.min_mem_available_gb, model,
        )
        rec["finished"] = now()
        return rec

    sampler = PeakSampler().start()
    t_model = time.time()

    def timed_out() -> bool:
        return time.time() > deadline

    try:
        append_log(log_path, "%s start %s mem_avail=%s" % (now(), model, avail))
        unload(base, model, timeout=min(60, args.generate_timeout))
        if timed_out():
            rec["verdict"] = "DROP"
            rec["reason"] = "stalled before cold load (>30 min budget)"
            return rec

        load_prompt = "Reply with the single word: pong"
        t0 = time.perf_counter()
        cold = generate(
            base, model, load_prompt,
            timeout=args.load_timeout, num_ctx=args.num_ctx, num_predict=8,
            keep_alive="10m", format_json=False,
        )
        load_wall = round(time.perf_counter() - t0, 4)
        rec["cold"] = {
            "ok": cold.get("ok"),
            "error": cold.get("error"),
            "wall_s": load_wall,
            "response": ((cold.get("data") or {}).get("response") or "")[:200],
            "timings": timings_from(cold.get("data") or {}),
        }
        rec["inventory_loaded"] = inventory_snippet(base)
        rec["ollama_ps_loaded"] = rec["inventory_loaded"].get("ollama_ps_rows")
        if not cold.get("ok"):
            rec["verdict"] = "DROP"
            rec["reason"] = "cold load failed: %s" % (cold.get("error") or "unknown")
            append_log(log_path, "%s cold-fail %s" % (now(), rec["reason"]))
            return rec
        rec["load_duration_s"] = rec["cold"]["timings"].get("load_duration_s")
        rec["load_wall_s"] = load_wall

        if timed_out():
            rec["verdict"] = "DROP"
            rec["reason"] = "stalled after load"
            return rec

        speed_prompt = (
            "Read the padding, then reply with exactly BENCH_OK and nothing else.\n\nPADDING:\n"
            + FILLER
        )
        t1 = time.perf_counter()
        speed = generate(
            base, model, speed_prompt,
            timeout=args.generate_timeout, num_ctx=args.num_ctx, num_predict=16,
            keep_alive="10m", format_json=False,
        )
        speed_wall = round(time.perf_counter() - t1, 4)
        st = timings_from(speed.get("data") or {})
        rec["speed"] = {
            "ok": speed.get("ok"),
            "error": speed.get("error"),
            "wall_s": speed_wall,
            "response": ((speed.get("data") or {}).get("response") or "")[:200],
            "prompt_eval_tok_s": st.get("prompt_eval_tok_s"),
            "eval_tok_s": st.get("eval_tok_s"),
            "timings": st,
            "filler_chars": len(FILLER),
        }
        append_log(
            log_path,
            "%s speed pp=%s decode=%s load_s=%s"
            % (now(), st.get("prompt_eval_tok_s"), st.get("eval_tok_s"), rec.get("load_duration_s")),
        )

        rows = []
        n_cases = len(cases) if args.max_cases is None else min(len(cases), args.max_cases)
        for i, case in enumerate(cases[:n_cases]):
            if timed_out():
                rec["verdict"] = "DROP"
                rec["reason"] = "stalled during accuracy (>30 min); completed %s/%s cases" % (i, n_cases)
                rec["decision_partial"] = True
                break
            prompt = decision_prompt(case)
            keys = list((case.get("criteria") or {}).keys())
            t_c = time.perf_counter()
            gen = generate(
                base, model, prompt,
                timeout=args.case_timeout, num_ctx=args.num_ctx, num_predict=96,
                keep_alive="10m", format_json=True,
            )
            dt = round(time.perf_counter() - t_c, 4)
            if not gen.get("ok"):
                parsed = {"parse_ok": False, "choice": None, "confidence": 0.0, "error": gen.get("error"), "raw": ""}
                row = score_case(case, parsed, args.gate, dt, error=gen.get("error") or "generate failed")
            else:
                text = (gen.get("data") or {}).get("response") or ""
                parsed = parse_choice_json(text, keys)
                row = score_case(case, parsed, args.gate, dt, error=None)
            row["cold"] = i == 0
            row["timings"] = timings_from(gen.get("data") or {})
            rows.append(row)
            append_log(
                log_path,
                "%s case %s choice=%s label=%s conf=%s esc=%s ok=%s %.3fs"
                % (now(), row["id"], row.get("choice"), row.get("label"), row.get("confidence"),
                   row.get("escalate"), row.get("correct"), dt),
            )
            append_log(cases_path, json.dumps(row, ensure_ascii=False))
            print(
                "  %s %s/%s %s choice=%s label=%s conf=%s esc=%s"
                % (model, i + 1, n_cases, row["id"], row.get("choice"), row.get("label"),
                   row.get("confidence"), row.get("escalate")),
                flush=True,
            )

        rec["decision"] = summarize_rows(rows, args.gate)
        rec["cases"] = rows
        if rec.get("verdict") is None:
            rec["verdict"] = "RAN"
        rec["log"] = log_path_for_receipt(log_path)
    except Exception as e:
        rec["verdict"] = "DROP"
        rec["reason"] = "exception: %s" % e
        rec["traceback"] = traceback.format_exc()[-1500:]
        append_log(log_path, "%s exception %s" % (now(), e))
    finally:
        rec["rss"] = sampler.finish()
        rec["peak_rss_kb"] = rec["rss"].get("peak_rss_kb")
        rec["peak_hwm_kb"] = rec["rss"].get("peak_hwm_kb")
        # GiB view of llama-server RSS (cross-user readable via cmdline fallback)
        pr = rec.get("peak_rss_kb")
        rec["peak_runner_rss_gib"] = None if not pr else round(float(pr) / 1024 / 1024, 3)
        rec["seconds"] = round(time.time() - t_model, 2)
        try:
            unload(base, model, timeout=min(90, args.generate_timeout))
        except Exception as e:  # noqa: BLE001
            rec["unload_error"] = str(e)
        rec["inventory_after"] = inventory_snippet(base)
        rec["finished"] = now()
        append_log(log_path, "%s done verdict=%s seconds=%s" % (now(), rec.get("verdict"), rec.get("seconds")))
    return rec


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Entry 089 local-inference bench (Ollama). Cite #230.")
    ap.add_argument("--check", action="store_true", help="Ping Ollama /api/version and exit")
    ap.add_argument("--base-url", default=None, help="Ollama base (default http://127.0.0.1:11434)")
    ap.add_argument("--models", default=",".join(REQUIRED_MODELS), help="Comma-separated model names")
    ap.add_argument("--stretch", action="store_true", default=True, help="Try qwen3-coder-next if 1-3 RAN and RAM healthy")
    ap.add_argument("--no-stretch", action="store_false", dest="stretch")
    ap.add_argument("--receipt", default=str(ROOT / RECEIPT_REL))
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--cases", default=str(ROOT / CASES_REL))
    ap.add_argument("--gate", type=float, default=float(os.environ.get("PFY_JEV_CONF_GATE") or DEFAULT_GATE))
    ap.add_argument("--num-ctx", type=int, default=DEFAULT_NUM_CTX)
    ap.add_argument("--stall-s", type=float, default=DEFAULT_STALL_S)
    ap.add_argument("--load-timeout", type=float, default=600)
    ap.add_argument("--generate-timeout", type=float, default=180)
    ap.add_argument("--case-timeout", type=float, default=180)
    ap.add_argument("--min-mem-available-gb", type=float, default=DEFAULT_MIN_MEM_GB)
    ap.add_argument("--max-cases", type=int, default=None)
    ap.add_argument("--required-from-tags", action="store_true", default=True,
                    help="Fail closed if a named model is missing from /api/tags")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    base = ollama_base(args.base_url)
    ok, info, ver = ping_ollama(base)
    if args.check:
        if not ok:
            return fail_closed(info)
        print(json.dumps({"verdict": "READY", "ollama_version": info, "base_url": base, "issue": ISSUE}))
        return EXIT_OK
    if not ok:
        extra = {"receipt": args.receipt}
        rec = {
            "schema": "local-bench.receipt.v0",
            "issue": ISSUE,
            "entry": ENTRY,
            "verdict": "FAIL_CANNOT_RUN",
            "reason": info,
            "started": now(),
            "finished": now(),
            "host": socket.gethostname(),
            "base_url": base,
            "gate": args.gate,
            "catalog_hold": "70-75",
            "feature_go": False,
            "default_lane_unchanged": True,
            "baselines": BASELINES,
        }
        write_json(Path(args.receipt), rec)
        return fail_closed(info, extra=extra)

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    for banned in SKIP_MODELS:
        models = [m for m in models if m != banned]

    try:
        tags = list_tags(base)
    except Exception as e:  # noqa: BLE001
        return fail_closed("cannot list Ollama tags at %s: %s" % (base, e))
    names = model_names(tags)
    missing = [m for m in models if m not in names]
    if missing and args.required_from_tags:
        rec = {
            "schema": "local-bench.receipt.v0",
            "issue": ISSUE,
            "entry": ENTRY,
            "verdict": "FAIL_CANNOT_RUN",
            "reason": "model name missing from Ollama store (fail closed, no pull): %s" % ", ".join(missing),
            "missing_models": missing,
            "present": sorted(n for n in names if n in models or n + ":latest" in models),
            "started": now(),
            "finished": now(),
            "host": socket.gethostname(),
            "base_url": base,
            "gate": args.gate,
            "catalog_hold": "70-75",
            "feature_go": False,
        }
        write_json(Path(args.receipt), rec)
        return fail_closed(rec["reason"], extra={"missing_models": missing, "receipt": args.receipt})

    cases_path = Path(args.cases)
    try:
        cases_doc = load_cases(cases_path)
    except Exception as e:  # noqa: BLE001
        return fail_closed("cannot load cases %s: %s" % (cases_path, e), code=EXIT_BROKEN)
    cases = list(cases_doc["cases"])

    outdir = resolve_outdir(args.outdir, Path(args.receipt))
    outdir.mkdir(parents=True, exist_ok=True)
    receipt_path = Path(args.receipt)

    started = now()
    host_inv = inventory_snippet(base)
    models_out = []
    stop_mem = False
    print("local-bench start ollama=%s models=%s gate=%s ctx=%s" % (info, models, args.gate, args.num_ctx), flush=True)

    for name in models:
        avail = mem_available_gb()
        if avail is not None and avail < args.min_mem_available_gb:
            models_out.append({
                "name": name,
                "verdict": "STOP_MEM",
                "reason": "MemAvailable %.3f GiB < %.3f GiB; stopping further loads" % (
                    avail, args.min_mem_available_gb,
                ),
            })
            stop_mem = True
            print("STOP_MEM before %s: %s" % (name, models_out[-1]["reason"]), flush=True)
            break
        print("== %s (MemAvailable=%s GiB) ==" % (name, avail), flush=True)
        deadline = time.time() + args.stall_s
        one = bench_one(base, name, cases, args, outdir, deadline)
        one["tag"] = tag_record(tags, name)
        models_out.append(one)
        print("%s verdict=%s acc=%s esc=%s wbc=%s pp=%s decode=%s"
              % (name, one.get("verdict"),
                 (one.get("decision") or {}).get("accuracy"),
                 (one.get("decision") or {}).get("escalate_rate"),
                 (one.get("decision") or {}).get("wrong_but_confident"),
                 (one.get("speed") or {}).get("prompt_eval_tok_s"),
                 (one.get("speed") or {}).get("eval_tok_s")), flush=True)
        if one.get("verdict") == "STOP_MEM":
            stop_mem = True
            break

    stretch = None
    ran_required = [m for m in models_out if m.get("name") in REQUIRED_MODELS and m.get("verdict") == "RAN"]
    if (
        args.stretch
        and not stop_mem
        and len(ran_required) == len([m for m in models if m in REQUIRED_MODELS])
        and STRETCH_MODEL not in models
    ):
        avail = mem_available_gb()
        if avail is not None and avail < args.min_mem_available_gb:
            stretch = {"name": STRETCH_MODEL, "verdict": "SKIP", "reason": "MemAvailable %.3f GiB too low" % avail}
        elif STRETCH_MODEL not in names:
            stretch = {"name": STRETCH_MODEL, "verdict": "SKIP", "reason": "not in Ollama store"}
        else:
            print("== stretch %s (MemAvailable=%s GiB) ==" % (STRETCH_MODEL, avail), flush=True)
            deadline = time.time() + args.stall_s
            stretch = bench_one(base, STRETCH_MODEL, cases, args, outdir, deadline)
            models_out.append(stretch)

    # Always unload requested models at the end.
    for name in models + ([STRETCH_MODEL] if stretch else []):
        try:
            unload(base, name, timeout=30)
        except Exception:
            pass

    finished = now()
    rec = {
        "schema": "local-bench.receipt.v0",
        "issue": ISSUE,
        "entry": ENTRY,
        "started": started,
        "finished": finished,
        "host": socket.gethostname(),
        "worktree": str(ROOT),
        "base_url": base,
        "ollama_version": info,
        "gate": args.gate,
        "num_ctx": args.num_ctx,
        "cases_file": str(CASES_REL),
        "n_cases": len(cases),
        "labels_written": cases_doc.get("labels_written"),
        "labels_before_models": cases_doc.get("labels_before_models"),
        "cites": ["#230"],
        "catalog_hold": "70-75",
        "feature_go": False,
        "gui": False,
        "default_lane_unchanged": True,
        "primary_local": "cua-s1-forms",
        "skip_models": list(SKIP_MODELS),
        "skip_models_reason": "none — MemoryHigh raised to 85G by Mark (Entry 091); previously blocked models in scope",
        "inventory": host_inv,
        "baselines": BASELINES,
        "models": models_out,
        "stretch": None if stretch is None else {"name": stretch.get("name"), "verdict": stretch.get("verdict")},
        "stop_mem": stop_mem,
        "recommendation": recommend(models_out),
        "locks": {
            "cite": "#230",
            "do_not_reopen": "#76",
            "catalog_hold": "70-75",
            "no_silent_auto_act": True,
            "confidence_is_margin": True,
            "not_a_feature_go": True,
        },
    }
    any_ran = any(m.get("verdict") == "RAN" for m in models_out)
    if not any_ran:
        rec["verdict"] = "FAIL_CANNOT_RUN"
        rec["reason"] = "no model RAN"
        write_json(receipt_path, rec)
        print(json.dumps({"verdict": rec["verdict"], "reason": rec["reason"], "receipt": str(receipt_path)}))
        return EXIT_CANNOT_RUN
    rec["verdict"] = "RAN"
    write_json(receipt_path, rec)
    print("receipt: %s" % receipt_path, flush=True)
    print(json.dumps({"verdict": rec["verdict"], "models": [
        {"name": m.get("name"), "verdict": m.get("verdict"),
         "accuracy": (m.get("decision") or {}).get("accuracy"),
         "escalate_rate": (m.get("decision") or {}).get("escalate_rate"),
         "wrong_but_confident": (m.get("decision") or {}).get("wrong_but_confident"),
         "parse_ok": (m.get("decision") or {}).get("parse_ok"),
         "prompt_eval_tok_s": (m.get("speed") or {}).get("prompt_eval_tok_s"),
         "eval_tok_s": (m.get("speed") or {}).get("eval_tok_s")}
        for m in models_out
    ], "receipt": str(receipt_path)}, ensure_ascii=False))
    return EXIT_OK


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print(json.dumps({"verdict": "FAIL", "reason": "interrupted", "issue": ISSUE}))
        raise SystemExit(EXIT_BROKEN)
