#!/usr/bin/env python3
"""Entry 086 Laya eval-auto trial vs CUA-S1-FORMS. Cite #230.

Head-to-head on data/decision-gates/laya-trial.cases.v0.json at the ~0.85
gate. CUA-S1-FORMS stays the default decision lane. Laya is reached only by
pointing the typesafe lane at 127.0.0.1 via PFY_JEV_TYPESAFE_URL.

Fail closed: missing venv or unreachable laya-serve → non-zero + reason.
Does not install packages, does not change product defaults.

Usage:
  python3 examples/typed-decisions-local/trial.py --check
  python3 examples/typed-decisions-local/trial.py
  python3 examples/typed-decisions-local/trial.py --shadow
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import resource
import signal
import statistics
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES_REL = Path("data/decision-gates/laya-trial.cases.v0.json")
RECEIPT_REL = Path("pipelines/dogfood/laya-trial/receipt.json")
SHADOW_RECEIPT_REL = Path("pipelines/dogfood/laya-shadow/receipt.json")
SHARED_TRIAL_ROOT = (Path.home() / "DEVELOP/pfy-mentat/tmp/laya-trial")
DEFAULT_VENV = ROOT / ".venv-laya" / "bin" / "python"
DEFAULT_HF = ROOT / ".hf-cache"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_GATE = 0.85
SHADOW_START_TIMEOUT = 600
ISSUE = "#230"
STRICT_ROOT = {"model", "answers", "usage"}
STRICT_CHOICE = {"choice", "probabilities", "confidence"}
PARSER_ROOT = {"answers", "model"}
PARSER_ANSWER = {"confidence"}

EXIT_OK = 0
EXIT_BROKEN = 1
EXIT_CANNOT_RUN = 2


# HARNESS2_PROMPT_BEGIN
def decision_prompt() -> str:
    """Executor procedure. The 0.85 figure is DEFAULT_GATE. harness2-local maps this string."""
    return """Read cases.json in this workspace.
Each case has an id, instructions, a state, and criteria.
Pick exactly one criteria key for each case.
Write output/answer.json and nothing else, in this shape:
{"answers":[{"case":"<id>","choice":"<criteria key>","confidence":0.0,"why":"one short reason"}]}
Use a confidence below 0.85 when the state does not settle the choice.
When a case is a typed Choice, load the `jev-decision` skill.
"""
# HARNESS2_PROMPT_END


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_jev():
    spec = importlib.util.spec_from_file_location("pfy_jev_230", ROOT / "scripts" / "pfy_jev_230.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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


def rss_kb(pid: int) -> int | None:
    path = Path("/proc/%s/status" % pid)
    if not path.is_file():
        return None
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
            if line.startswith("VmHWM:"):
                pass
    except (OSError, ValueError):
        return None
    return None


def hwm_kb(pid: int) -> int | None:
    path = Path("/proc/%s/status" % pid)
    if not path.is_file():
        return None
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1])
    except (OSError, ValueError):
        return None
    return None


def http_json(method: str, url: str, body=None, timeout=30, headers=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    hdrs = {"Accept": "application/json"}
    if data is not None:
        hdrs["Content-Type"] = "application/json"
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", "replace")
        return resp.status, json.loads(raw) if raw else {}


def fail_closed(reason: str, code: int = EXIT_CANNOT_RUN, extra=None) -> int:
    rec = {"verdict": "FAIL_CANNOT_RUN" if code == EXIT_CANNOT_RUN else "FAIL", "reason": reason, "issue": ISSUE}
    if extra:
        rec.update(extra)
    print(json.dumps(rec, ensure_ascii=False))
    return code


def venv_python() -> Path:
    env = os.environ.get("LAYA_PYTHON")
    if env:
        return Path(env)
    if os.access(DEFAULT_VENV, os.X_OK):
        return DEFAULT_VENV
    shared = SHARED_TRIAL_ROOT / ".venv-laya" / "bin" / "python"
    if os.access(shared, os.X_OK):
        return shared
    return DEFAULT_VENV


def hf_home() -> Path:
    env = os.environ.get("HF_HOME") or os.environ.get("HF_HUB_CACHE")
    if env:
        return Path(env)
    if DEFAULT_HF.is_dir():
        return DEFAULT_HF
    shared = SHARED_TRIAL_ROOT / ".hf-cache"
    if shared.is_dir():
        return shared
    return DEFAULT_HF


def serve_bin(py: Path) -> Path:
    return py.parent / "laya-serve"


def require_venv(py: Path) -> str | None:
    if not os.access(py, os.X_OK):
        return (
            "no Laya venv at %s. Operator: ~/.local/bin/python3.11 -m venv "
            "~/DEVELOP/pfy-mentat/tmp/laya-trial/.venv-laya && "
            ".venv-laya/bin/python -m pip install torch --index-url https://download.pytorch.org/whl/cpu && "
            ".venv-laya/bin/python -m pip install 'laya[serve]' (inside this worktree only)"
            % py
        )
    if not os.access(serve_bin(py), os.X_OK):
        return "laya-serve missing next to %s (venv exists but laya[serve] is not installed)" % py
    return None


def health_url(host: str, port: int) -> str:
    return "http://%s:%s/health" % (host, port)


def systemone_url(host: str, port: int) -> str:
    return "http://%s:%s/v1/systemone" % (host, port)


def wait_health(host: str, port: int, timeout_s: float, pid: int | None = None):
    deadline = time.time() + timeout_s
    last = ""
    while time.time() < deadline:
        if pid is not None:
            try:
                os.kill(pid, 0)
            except OSError:
                return False, "laya-serve pid %s exited before /health: %s" % (pid, last[-400:])
        try:
            status, data = http_json("GET", health_url(host, port), timeout=2)
            if status == 200 and isinstance(data, dict) and data.get("status") == "ok":
                return True, data
            last = json.dumps(data)[:400]
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            last = str(e)
        time.sleep(1.0)
    return False, "timed out waiting for %s (%s)" % (health_url(host, port), last[-400:])


def start_serve(py: Path, host: str, port: int, models: str, strict: bool, log_path: Path, timeout_s: float):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["LAYA_HOST"] = host
    env["LAYA_PORT"] = str(port)
    env["LAYA_DEVICE"] = "cpu"
    env["LAYA_PRELOAD"] = os.environ.get("LAYA_PRELOAD") or "1"
    env["LAYA_MODELS"] = models
    env["LAYA_JEV_STRICT"] = "1" if strict else "0"
    env["LAYA_THREADS"] = os.environ.get("LAYA_THREADS") or "16"
    env["LAYA_DEFAULT_MODEL"] = os.environ.get("LAYA_DEFAULT_MODEL") or "english"
    env["HF_HOME"] = str(hf_home())
    env["HF_HUB_CACHE"] = str(Path(os.environ.get("HF_HUB_CACHE") or env["HF_HOME"]))
    env["HF_HUB_DISABLE_TELEMETRY"] = "1"
    env.pop("LAYA_API_KEY", None)
    t0 = time.time()
    log_f = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [str(serve_bin(py))],
        cwd=str(ROOT),
        env=env,
        stdout=log_f,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    ok, info = wait_health(host, port, timeout_s, pid=proc.pid)
    rec = {
        "pid": proc.pid,
        "seconds_to_health": round(time.time() - t0, 2),
        "health": info if ok else None,
        "log": str(log_path),
        "env": {
            "LAYA_HOST": host,
            "LAYA_PORT": port,
            "LAYA_DEVICE": "cpu",
            "LAYA_MODELS": models,
            "LAYA_JEV_STRICT": env["LAYA_JEV_STRICT"],
            "HF_HOME": env["HF_HOME"],
            "HF_HUB_CACHE": env["HF_HUB_CACHE"],
        },
    }
    if not ok:
        tail = ""
        try:
            tail = Path(log_path).read_text(encoding="utf-8", errors="replace")[-1200:]
        except OSError:
            pass
        rec["error"] = info
        rec["log_tail"] = tail
        stop_serve(proc)
        log_f.close()
        return None, rec
    rec["log_f"] = log_f
    rec["proc"] = proc
    return proc, rec


def stop_serve(proc):
    if proc is None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        try:
            proc.terminate()
        except (OSError, ProcessLookupError):
            return
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass


def summarize_lane(rows, gate: float):
    n = len(rows)
    ran = [r for r in rows if r.get("ran")]
    n_ran = len(ran)
    correct = sum(1 for r in ran if r.get("correct"))
    esc = [r for r in ran if r.get("escalate")]
    held = [r for r in ran if not r.get("escalate")]
    wrong_conf = [r for r in ran if (not r.get("correct")) and (not r.get("escalate"))]
    lat = [float(r["latency_s"]) for r in ran if r.get("latency_s") is not None]
    cold = [float(r["latency_s"]) for r in ran if r.get("cold") and r.get("latency_s") is not None]
    warm = [float(r["latency_s"]) for r in ran if (not r.get("cold")) and r.get("latency_s") is not None]
    return {
        "n_cases": n,
        "n_ran": n_ran,
        "n_error": n - n_ran,
        "accuracy": None if not n_ran else round(correct / n_ran, 4),
        "n_correct": correct,
        "escalate_rate": None if not n_ran else round(len(esc) / n_ran, 4),
        "n_escalate": len(esc),
        "n_held": len(held),
        "held_accuracy": None if not held else round(sum(1 for r in held if r.get("correct")) / len(held), 4),
        "wrong_but_confident": len(wrong_conf),
        "wrong_but_confident_ids": [r["id"] for r in wrong_conf],
        "latency_s": {
            "cold_first": None if not cold else round(cold[0], 4),
            "warm_p50": percentile(warm, 50),
            "warm_p95": percentile(warm, 95),
            "all_p50": percentile(lat, 50),
            "all_p95": percentile(lat, 95),
            "n_warm": len(warm),
        },
        "gate": gate,
        "errors": [{"id": r["id"], "error": r.get("error")} for r in rows if not r.get("ran")],
    }


def run_cua(jev, case, gate: float):
    t0 = time.perf_counter()
    rec = jev.decide_choice(case["state"], case["criteria"], instructions=case.get("instructions") or "")
    dt = time.perf_counter() - t0
    choice = rec.get("choice")
    conf = float(rec.get("confidence") or 0)
    return {
        "id": case["id"],
        "ran": bool(rec.get("choice")),
        "choice": choice,
        "label": case["label"],
        "correct": choice == case["label"],
        "confidence": conf,
        "escalate": conf < gate,
        "latency_s": round(dt, 4),
        "engine": rec.get("engine") or "cua-s1-forms",
        "chip_conf": rec.get("chip_conf"),
        "error": None if rec.get("choice") else (rec.get("error") or rec.get("copy")),
    }


def run_laya(jev, case, gate: float, model: str):
    qid = case["id"]
    questions = {
        qid: {
            "type": "choice",
            "instructions": case.get("instructions") or "",
            "criteria": case["criteria"],
        }
    }
    os.environ["PFY_JEV_MODEL"] = model
    t0 = time.perf_counter()
    rec = jev.typesafe_evaluate(case["state"], questions)
    dt = time.perf_counter() - t0
    if not rec.get("answers") and not rec.get("ok"):
        return {
            "id": qid,
            "ran": False,
            "choice": None,
            "label": case["label"],
            "correct": False,
            "confidence": 0.0,
            "escalate": True,
            "latency_s": round(dt, 4),
            "engine": rec.get("engine") or "typesafe",
            "model": rec.get("model") or model,
            "error": rec.get("error") or rec.get("copy"),
            "raw_keys": list(rec.keys()),
        }
    ans = (rec.get("answers") or {}).get(qid) or {}
    choice = ans.get("choice")
    conf = float(ans.get("confidence") or 0)
    return {
        "id": qid,
        "ran": choice is not None,
        "choice": choice,
        "label": case["label"],
        "correct": choice == case["label"],
        "confidence": conf,
        "answer_confidence": ans.get("answer_confidence"),
        "escalate": conf < gate,
        "latency_s": round(dt, 4),
        "engine": rec.get("engine") or "typesafe",
        "model": rec.get("model") or model,
        "answer_keys": sorted(ans.keys()) if isinstance(ans, dict) else [],
        "error": None if choice is not None else (rec.get("error") or "no choice in answers"),
    }


def run_shadow_held(jev, case, cua_row, gate: float):
    """Apply maybe_laya_shadow only when CUA would have auto-acted."""
    if cua_row.get("escalate") or not cua_row.get("ran"):
        return {
            "enabled": False,
            "skipped": "cua_escalate" if cua_row.get("escalate") else "cua_error",
            "action": "skip",
            "cua_choice": cua_row.get("choice"),
            "laya_choice": None,
            "agree": None,
            "latency_s": None,
        }
    rec = jev.decide_choice(case["state"], case["criteria"], instructions=case.get("instructions") or "")
    rec["engine"] = "cua-s1-forms"
    rec = jev.maybe_laya_shadow(
        rec,
        case["state"],
        case["criteria"],
        instructions=case.get("instructions") or "",
        qid=case["id"],
    )
    shadow = rec.get("shadow")
    if not isinstance(shadow, dict):
        return {
            "enabled": True,
            "engine": "laya",
            "action": "escalate",
            "error": "maybe_laya_shadow returned no shadow fields",
            "cua_choice": cua_row.get("choice"),
            "laya_choice": None,
            "agree": False,
            "latency_s": None,
        }
    return shadow


def summarize_shadow(cua_rows, shadow_rows):
    wbc = [r for r in cua_rows if r.get("ran") and (not r.get("correct")) and (not r.get("escalate"))]
    held_ok = [r for r in cua_rows if r.get("ran") and r.get("correct") and (not r.get("escalate"))]
    by_id = {r["id"]: s for r, s in zip(cua_rows, shadow_rows)}
    catch_ids = []
    miss_ids = []
    false_ids = []
    error_ids = []
    for row in wbc:
        sh = by_id.get(row["id"]) or {}
        if sh.get("error") or sh.get("laya_choice") is None:
            error_ids.append(row["id"])
            continue
        if sh.get("agree") is True:
            miss_ids.append(row["id"])
        else:
            catch_ids.append(row["id"])
    for row in held_ok:
        sh = by_id.get(row["id"]) or {}
        if sh.get("error"):
            error_ids.append(row["id"])
        if sh.get("action") == "escalate":
            false_ids.append(row["id"])
    lats = [
        float(s["latency_s"])
        for s in shadow_rows
        if s.get("latency_s") is not None and s.get("action") != "skip"
    ]
    return {
        "n_cua_held": sum(1 for r in cua_rows if r.get("ran") and not r.get("escalate")),
        "n_cua_wrong_but_confident": len(wbc),
        "n_cua_held_correct": len(held_ok),
        "catch": len(catch_ids),
        "catch_ids": catch_ids,
        "miss": len(miss_ids),
        "miss_ids": miss_ids,
        "false_escalate": len(false_ids),
        "false_escalate_ids": false_ids,
        "n_shadow_calls": sum(1 for s in shadow_rows if s.get("action") != "skip"),
        "n_shadow_error": sum(1 for s in shadow_rows if s.get("error")),
        "error_ids": error_ids,
        "latency_s": {
            "p50": percentile(lats, 50),
            "p95": percentile(lats, 95),
            "n": len(lats),
        },
    }


def probe_wire(jev, url: str, dummy_key: str, timeout: float):
    """Diff one /v1/systemone response against the ADR-0016 typesafe parser."""
    body = {
        "state": "Hi, we were billed twice for March. Please refund the duplicate today or we will cancel our plan.",
        "questions": {
            "department": {
                "type": "choice",
                "instructions": "Which department should handle this?",
                "criteria": {
                    "billing": "invoices, payments, refunds",
                    "technical": "bugs, outages, system errors",
                    "other": "everything else",
                },
            }
        },
    }
    t0 = time.perf_counter()
    try:
        status, raw = http_json(
            "POST",
            url,
            body,
            timeout=timeout,
            headers={"Authorization": "Bearer %s" % dummy_key},
        )
        http_s = time.perf_counter() - t0
        http_err = None
    except Exception as e:
        status, raw, http_s, http_err = None, None, time.perf_counter() - t0, str(e)[:400]
    os.environ["PFY_JEV_TYPESAFE_URL"] = url
    os.environ["TYPESAFE_API_KEY"] = dummy_key
    os.environ.pop("PFY_JEV_OFFLINE", None)
    t1 = time.perf_counter()
    parsed = jev.typesafe_evaluate(body["state"], body["questions"])
    parse_s = time.perf_counter() - t1
    raw_root = set(raw.keys()) if isinstance(raw, dict) else set()
    ans = ((raw or {}).get("answers") or {}).get("department") if isinstance(raw, dict) else None
    ans_keys = set(ans.keys()) if isinstance(ans, dict) else set()
    parsed_ans = (parsed.get("answers") or {}).get("department") if isinstance(parsed.get("answers"), dict) else None
    extra_root = sorted(raw_root - STRICT_ROOT)
    extra_ans = sorted(ans_keys - STRICT_CHOICE) if ans_keys else []
    missing_root = sorted(STRICT_ROOT - raw_root)
    missing_ans = sorted(STRICT_CHOICE - ans_keys) if ans_keys else sorted(STRICT_CHOICE)
    parser_reads_conf = isinstance(parsed_ans, dict) and "confidence" in parsed_ans
    parser_reads_choice = isinstance(parsed_ans, dict) and "choice" in parsed_ans
    return {
        "http_status": status,
        "http_seconds": round(http_s, 4),
        "http_error": http_err,
        "parser_seconds": round(parse_s, 4),
        "parser_ok": bool(parsed.get("answers")),
        "parser_error": parsed.get("error"),
        "raw_root_keys": sorted(raw_root),
        "raw_answer_keys": sorted(ans_keys),
        "raw_choice": None if not isinstance(ans, dict) else ans.get("choice"),
        "raw_confidence": None if not isinstance(ans, dict) else ans.get("confidence"),
        "raw_answer_confidence": None if not isinstance(ans, dict) else ans.get("answer_confidence"),
        "strict_contract_root": sorted(STRICT_ROOT),
        "strict_contract_choice": sorted(STRICT_CHOICE),
        "extra_root_vs_strict": extra_root,
        "extra_answer_vs_strict": extra_ans,
        "missing_root_vs_strict": missing_root,
        "missing_answer_vs_strict": missing_ans,
        "parser_uses": {
            "root": sorted(PARSER_ROOT),
            "answer_confidence_field": "confidence",
            "reads_choice_pass_through": True,
            "got_confidence": parser_reads_conf,
            "got_choice": parser_reads_choice,
        },
        "parser_choice": None if not isinstance(parsed_ans, dict) else parsed_ans.get("choice"),
        "parser_confidence": None if not isinstance(parsed_ans, dict) else parsed_ans.get("confidence"),
        "note": (
            "ADR-0016 typesafe parser is lenient (reads answers + confidence, ignores extras). "
            "LAYA_JEV_STRICT=1 should drop routing/action/answer_confidence and shrink usage. "
            "Field drift is extra/missing vs that strict contract, plus whether the parser saw confidence."
        ),
    }


def write_receipt(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Entry 086 Laya vs CUA-S1-FORMS trial. Cite #230.")
    ap.add_argument("--check", action="store_true", help="prereq check only (venv + optional live server)")
    ap.add_argument("--shadow", action="store_true", help="CUA primary + Laya english second opinion on CUA-held cases")
    ap.add_argument("--cases", default=str(ROOT / CASES_REL))
    ap.add_argument("--receipt", default=None)
    ap.add_argument("--host", default=os.environ.get("LAYA_HOST") or DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=int(os.environ.get("LAYA_PORT") or DEFAULT_PORT))
    ap.add_argument("--gate", type=float, default=float(os.environ.get("PFY_JEV_CONF_GATE") or DEFAULT_GATE))
    ap.add_argument("--models", default=None)
    ap.add_argument("--no-start", action="store_true", help="do not spawn laya-serve; require it already up")
    ap.add_argument("--start-timeout", type=float, default=None)
    ap.add_argument("--http-timeout", type=float, default=float(os.environ.get("PFY_JEV_TYPESAFE_TIMEOUT") or 180))
    args = ap.parse_args(argv)
    if args.receipt is None:
        args.receipt = str(ROOT / (SHADOW_RECEIPT_REL if args.shadow else RECEIPT_REL))
    if args.models is None:
        args.models = os.environ.get("LAYA_TRIAL_MODELS") or ("english" if args.shadow else "english,typed-decisions")
    if args.start_timeout is None:
        args.start_timeout = float(
            os.environ.get("LAYA_START_TIMEOUT") or (SHADOW_START_TIMEOUT if args.shadow else 1800)
        )

    py = venv_python()
    missing = require_venv(py)
    if missing:
        return fail_closed(missing, EXIT_CANNOT_RUN)

    host = args.host
    if host not in ("127.0.0.1", "localhost"):
        return fail_closed("laya-serve must bind 127.0.0.1 only (got %s)" % host, EXIT_BROKEN)

    if args.check:
        live = False
        health = None
        try:
            st, health = http_json("GET", health_url(host, args.port), timeout=2)
            live = st == 200
        except Exception:
            live = False
        print(json.dumps({"verdict": "READY", "python": str(py), "server_live": live, "health": health}, ensure_ascii=False))
        return EXIT_OK

    cases_path = Path(args.cases)
    if not cases_path.is_file():
        return fail_closed("labeled cases missing at %s" % cases_path, EXIT_BROKEN)
    blob = json.loads(cases_path.read_text(encoding="utf-8"))
    cases = list(blob.get("cases") or [])
    if not cases:
        return fail_closed("no cases in %s" % cases_path, EXIT_BROKEN)
    if not blob.get("labels_before_models"):
        return fail_closed("cases file must set labels_before_models true", EXIT_BROKEN)

    jev = load_jev()
    gate = float(args.gate)
    dummy_key = os.environ.get("TYPESAFE_API_KEY") or "laya-local-trial"
    url = systemone_url(host, args.port)
    os.environ["PFY_JEV_TYPESAFE_URL"] = url
    os.environ["PFY_JEV_TYPESAFE_TIMEOUT"] = str(args.http_timeout)
    os.environ["PFY_JEV_CONF_GATE"] = str(gate)
    os.environ["TYPESAFE_API_KEY"] = dummy_key
    os.environ.pop("PFY_JEV_OFFLINE", None)
    os.environ.pop("TYPESAFE_KEY", None)

    if args.shadow:
        os.environ["PFY_JEV_LAYA_SHADOW"] = "1"
        if not str(os.environ.get("PFY_JEV_MODEL") or "").strip():
            os.environ["PFY_JEV_MODEL"] = "english"

    receipt = {
        "schema": "laya-shadow.receipt.v0" if args.shadow else "laya-trial.receipt.v0",
        "issue": ISSUE,
        "entry": "086",
        "mode": "shadow" if args.shadow else "head-to-head",
        "started": now(),
        "host": os.uname().nodename,
        "worktree": str(ROOT),
        "branch": "bot/laya-shadow" if args.shadow else "bot/laya-trial",
        "gate": gate,
        "cases_file": str(cases_path.relative_to(ROOT)),
        "n_cases": len(cases),
        "labels_written": blob.get("labels_written"),
        "labels_before_models": True,
        "default_lane_unchanged": True,
        "primary_local": jev.PRIMARY_LOCAL,
        "typesafe_url_default": jev.TYPESAFE_URL,
        "typesafe_url_override": url,
        "python": str(py),
        "hf_home": str(hf_home()),
        "recommendation": None,
        "lanes": {},
    }
    if args.shadow:
        receipt["flag"] = "PFY_JEV_LAYA_SHADOW"
        receipt["shadow_model"] = jev.laya_shadow_model()

    proc = None
    serve_meta = None
    started_here = False
    try:
        live = False
        try:
            st, health = http_json("GET", health_url(host, args.port), timeout=2)
            live = st == 200
            serve_meta = {"already_up": True, "health": health, "pid": None}
        except Exception:
            live = False
        if not live:
            if args.no_start:
                receipt["lanes"]["laya"] = {
                    "ran": False,
                    "error": "laya-serve not reachable at %s and --no-start was set" % health_url(host, args.port),
                }
                receipt["finished"] = now()
                receipt["verdict"] = "FAIL_CANNOT_RUN"
                receipt["reason"] = receipt["lanes"]["laya"]["error"]
                write_receipt(Path(args.receipt), receipt)
                return fail_closed(receipt["reason"], EXIT_CANNOT_RUN, extra={"receipt": args.receipt})
            log_dir = "pipelines/dogfood/laya-shadow" if args.shadow else "pipelines/dogfood/laya-trial"
            log_path = ROOT / log_dir / "laya-serve.log"
            proc, serve_meta = start_serve(
                py, host, args.port, args.models, True, log_path, args.start_timeout
            )
            started_here = proc is not None
            if proc is None:
                receipt["serve"] = {k: v for k, v in (serve_meta or {}).items() if k not in ("proc", "log_f")}
                receipt["lanes"]["laya"] = {"ran": False, "error": (serve_meta or {}).get("error")}
                receipt["finished"] = now()
                receipt["verdict"] = "FAIL_CANNOT_RUN"
                receipt["reason"] = (serve_meta or {}).get("error") or "laya-serve failed to start"
                write_receipt(Path(args.receipt), receipt)
                return fail_closed(receipt["reason"], EXIT_CANNOT_RUN, extra={"receipt": args.receipt})
        receipt["serve"] = {k: v for k, v in (serve_meta or {}).items() if k not in ("proc", "log_f")}
        if proc is not None:
            receipt["serve"]["pid"] = proc.pid
            receipt["serve"]["peak_rss_kb_at_health"] = rss_kb(proc.pid)
            receipt["serve"]["hwm_kb_at_health"] = hwm_kb(proc.pid)

        # CUA-S1-FORMS in-process (stdlib analogue). Laya is HTTP to 127.0.0.1.
        cua_rows = []
        t_cua = time.time()
        for i, case in enumerate(cases):
            row = run_cua(jev, case, gate)
            row["cold"] = i == 0
            cua_rows.append(row)
        cua_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        receipt["lanes"]["cua-s1-forms"] = {
            **summarize_lane(cua_rows, gate),
            "peak_rss_kb": cua_rss,
            "peak_rss_note": "Linux ru_maxrss of the trial process after the CUA loop (KB).",
            "seconds": round(time.time() - t_cua, 3),
            "cases": cua_rows,
        }

        if args.shadow:
            peak = receipt["serve"].get("peak_rss_kb_at_health") or 0
            hwm = receipt["serve"].get("hwm_kb_at_health") or 0
            pid = (proc.pid if proc is not None else None) or receipt["serve"].get("pid")
            shadow_rows = []
            t_shadow = time.time()
            case_by_id = {c["id"]: c for c in cases}
            for i, cua_row in enumerate(cua_rows):
                case = case_by_id[cua_row["id"]]
                shadow = run_shadow_held(jev, case, cua_row, gate)
                shadow_rows.append(shadow)
                if pid and shadow.get("action") != "skip":
                    r = rss_kb(pid)
                    h = hwm_kb(pid)
                    if r:
                        peak = max(peak, r)
                    if h:
                        hwm = max(hwm, h)
            stats = summarize_shadow(cua_rows, shadow_rows)
            stats["peak_rss_kb"] = peak
            stats["hwm_kb"] = hwm
            stats["seconds"] = round(time.time() - t_shadow, 3)
            stats["model"] = jev.laya_shadow_model()
            per_case = []
            for cua_row, shadow in zip(cua_rows, shadow_rows):
                row = dict(cua_row)
                row["shadow"] = shadow
                per_case.append(row)
            catch = stats.get("catch") or 0
            collateral = stats.get("false_escalate") or 0
            wbc = stats.get("n_cua_wrong_but_confident") or 0
            held_ok = stats.get("n_cua_held_correct") or 0
            useful = catch > 0 and catch > collateral
            if stats.get("n_shadow_error"):
                recommendation = (
                    "keep CUA-S1-FORMS; Laya shadow had errors (fail closed). Flag stays off by default."
                )
            elif useful:
                recommendation = (
                    "Laya english shadow catches %s/%s CUA wrong-but-confident with %s/%s false-escalate; "
                    "useful as opt-in, default stays off, not a lane swap"
                    % (catch, wbc, collateral, held_ok)
                )
            else:
                recommendation = (
                    "keep CUA-S1-FORMS as default; Laya english shadow catch %s/%s vs false-escalate %s/%s "
                    "does not clearly beat collateral. Flag stays off."
                    % (catch, wbc, collateral, held_ok)
                )
            receipt["shadow"] = stats
            receipt["cases"] = per_case
            receipt["recommendation"] = recommendation
            receipt["finished"] = now()
            receipt["verdict"] = "RAN"
            write_receipt(Path(args.receipt), receipt)
            print(
                json.dumps(
                    {
                        "verdict": "RAN",
                        "mode": "shadow",
                        "receipt": str(Path(args.receipt)),
                        "catch": "%s/%s" % (catch, wbc),
                        "false_escalate": "%s/%s" % (collateral, held_ok),
                        "miss": "%s/%s" % (stats.get("miss"), wbc),
                        "latency_s": stats.get("latency_s"),
                        "peak_rss_kb": peak,
                        "hwm_kb": hwm,
                        "recommendation": recommendation,
                    },
                    ensure_ascii=False,
                )
            )
            return EXIT_OK

        probe = probe_wire(jev, url, dummy_key, args.http_timeout)
        receipt["wire_contract"] = probe

        model_names = [m.strip() for m in args.models.split(",") if m.strip()]
        peak = receipt["serve"].get("peak_rss_kb_at_health") or 0
        hwm = receipt["serve"].get("hwm_kb_at_health") or 0
        pid = (proc.pid if proc is not None else None) or receipt["serve"].get("pid")
        for model in model_names:
            rows = []
            t_lane = time.time()
            for i, case in enumerate(cases):
                row = run_laya(jev, case, gate, model)
                row["cold"] = i == 0
                rows.append(row)
                if pid:
                    r = rss_kb(pid)
                    h = hwm_kb(pid)
                    if r:
                        peak = max(peak, r)
                    if h:
                        hwm = max(hwm, h)
            key = "laya:%s" % model
            receipt["lanes"][key] = {
                **summarize_lane(rows, gate),
                "checkpoint": model,
                "seconds": round(time.time() - t_lane, 3),
                "cases": rows,
            }
        receipt["lanes"]["laya_peak_rss_kb"] = peak
        receipt["lanes"]["laya_hwm_kb"] = hwm

        cua_s = receipt["lanes"]["cua-s1-forms"]
        recs = []
        for model in model_names:
            lane = receipt["lanes"].get("laya:%s" % model) or {}
            recs.append(
                {
                    "lane": "laya:%s" % model,
                    "accuracy": lane.get("accuracy"),
                    "held_accuracy": lane.get("held_accuracy"),
                    "wrong_but_confident": lane.get("wrong_but_confident"),
                    "escalate_rate": lane.get("escalate_rate"),
                    "warm_p50_s": (lane.get("latency_s") or {}).get("warm_p50"),
                    "n_ran": lane.get("n_ran"),
                }
            )
        cua_wrong = cua_s.get("wrong_but_confident")
        best = None
        for r in recs:
            if r.get("n_ran"):
                if best is None or (r.get("held_accuracy") or 0) > (best.get("held_accuracy") or 0):
                    best = r
        swap = False
        if best and cua_s.get("n_ran"):
            # Measured win = higher held accuracy and fewer wrong-but-confident, at this gate.
            if (
                (best.get("held_accuracy") or 0) > (cua_s.get("held_accuracy") or 0)
                and (best.get("wrong_but_confident") or 0) <= (cua_wrong or 0)
                and (best.get("n_ran") == cua_s.get("n_ran"))
            ):
                swap = True
        if not any(r.get("n_ran") for r in recs):
            recommendation = "keep CUA-S1-FORMS; Laya lane did not run"
        elif swap:
            recommendation = (
                "measured win on this set for %s vs CUA-S1-FORMS; still not a default-lane swap "
                "without founder say"
                % best["lane"]
            )
        else:
            recommendation = "keep CUA-S1-FORMS as the default decision lane (no measured win on this set)"
        receipt["recommendation"] = recommendation
        receipt["recommendation_rows"] = recs
        receipt["finished"] = now()
        receipt["verdict"] = "RAN"
        write_receipt(Path(args.receipt), receipt)
        print(
            json.dumps(
                {
                    "verdict": "RAN",
                    "receipt": str(Path(args.receipt)),
                    "cua": {
                        "accuracy": cua_s.get("accuracy"),
                        "escalate_rate": cua_s.get("escalate_rate"),
                        "held_accuracy": cua_s.get("held_accuracy"),
                        "wrong_but_confident": cua_s.get("wrong_but_confident"),
                    },
                    "laya": recs,
                    "recommendation": recommendation,
                    "wire_extra_root": probe.get("extra_root_vs_strict"),
                    "wire_extra_answer": probe.get("extra_answer_vs_strict"),
                },
                ensure_ascii=False,
            )
        )
        return EXIT_OK
    except Exception as e:
        receipt["finished"] = now()
        receipt["verdict"] = "FAIL"
        receipt["reason"] = str(e)[:400]
        receipt["traceback"] = traceback.format_exc()[-2000:]
        write_receipt(Path(args.receipt), receipt)
        return fail_closed(receipt["reason"], EXIT_BROKEN, extra={"receipt": args.receipt})
    finally:
        if started_here and proc is not None:
            stop_serve(proc)
            log_f = (serve_meta or {}).get("log_f")
            if log_f:
                try:
                    log_f.close()
                except Exception:
                    pass


if __name__ == "__main__":
    sys.exit(main())
