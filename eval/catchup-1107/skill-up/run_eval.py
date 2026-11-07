#!/usr/bin/env python3
"""Run the skill-up case set through engine_local.py and write summary.json.

The live path needs the pinned v0.14.0 binary, Ollama, and qwen3.6:35b.
`--score DIR` only reads iteration-*/result.json and prints a decision.
That path does not call a model or the skill-up binary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CASES = Path(__file__).resolve().parent / "cases"
ENGINE = Path(__file__).resolve().parent / "engine_local.py"
EVAL_YAML = CASES / "evals" / "eval.yaml"
SKILL = ROOT / "bootstrap" / "grok-cli" / "skills" / "karpathy-guidelines"
SUMMARY = Path(__file__).resolve().parent / "summary.json"
BIN_SHA = "5b1bdd0a30f57653c8f6a3a679e992b29982fe18709b2556d53a6f9ea1c85ab6"
MODEL = "qwen3.6:35b"
GATE_KIB = 47 * 1024 * 1024
CONFIGS = ("with_skill", "without_skill")
WHY = (
    "karpathy-guidelines tells the model to change only the lines the task names "
    "and to match the existing function. These five cases fail when the function "
    "is renamed, rewritten into a new helper, or left with the seeded bug."
)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _mem_kib() -> int | None:
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
    return GATE_KIB


def _resident_model() -> bool | None:
    base = os.environ.get("SKILLUP_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(base + "/api/ps", timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None
    for row in data.get("models") or []:
        if isinstance(row, dict) and str(row.get("name") or "") == MODEL:
            return True
    return False


def wait_for_memory() -> tuple[bool, str]:
    gate = _gate_kib()
    if gate <= 0:
        return True, "memory gate disabled"
    if _resident_model() is True:
        avail = _mem_kib()
        return True, "model already loaded, MemAvailable %s KiB" % avail
    deadline = time.time() + 30 * 60
    while True:
        avail = _mem_kib()
        if avail is not None and avail >= gate:
            return True, "MemAvailable %s KiB" % avail
        if time.time() >= deadline:
            have = "unknown" if avail is None else str(avail)
            return False, "HOST-BUSY MemAvailable %s KiB below %s KiB after 30 min" % (have, gate)
        print("memory %s KiB < %s, waiting" % (avail, gate), file=sys.stderr)
        time.sleep(30)


def find_binary() -> Path | None:
    env = os.environ.get("SKILLUP_BIN", "").strip()
    if env:
        path = Path(env)
        return path if path.is_file() else None
    cand = ROOT / "tmp" / "skill-up" / "skill-up"
    if cand.is_file():
        return cand
    return None


def score_dir(out: Path) -> dict:
    iterations = []
    for path in sorted(out.glob("iteration-*/result.json")):
        try:
            num = int(path.parent.name.split("-", 1)[1])
        except (IndexError, ValueError):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        cases = {}
        for row in data.get("case_results") or []:
            if not isinstance(row, dict):
                continue
            cid = str(row.get("case_id") or "")
            cfg = str(row.get("configuration") or "with_skill")
            if not cid:
                continue
            cases.setdefault(cid, {})[cfg] = str(row.get("status") or "ERROR")
        bench = path.parent / "benchmark.json"
        bench_summary = None
        if bench.is_file():
            try:
                bench_summary = json.loads(bench.read_text(encoding="utf-8")).get("run_summary")
            except (OSError, json.JSONDecodeError):
                bench_summary = None
        junit = path.parent / "report.xml"
        iterations.append({
            "iteration": num,
            "cases": cases,
            "benchmark": bench_summary,
            "junit": junit.is_file(),
            "result": str(path),
        })
    iterations.sort(key=lambda row: row["iteration"])
    case_ids = []
    for row in iterations:
        for cid in row["cases"]:
            if cid not in case_ids:
                case_ids.append(cid)
    rates = {cfg: [] for cfg in CONFIGS}
    flake_pairs = []
    errors = 0
    graded = 0
    for cid in case_ids:
        for cfg in CONFIGS:
            statuses = []
            for row in iterations:
                status = (row["cases"].get(cid) or {}).get(cfg)
                if status is None:
                    continue
                statuses.append(status)
                graded += 1
                if status == "ERROR":
                    errors += 1
            if len(statuses) >= 2 and len(set(statuses)) > 1:
                flake_pairs.append({"case_id": cid, "configuration": cfg, "statuses": statuses})
    for row in iterations:
        for cfg in CONFIGS:
            total = 0
            passed = 0
            for cid in case_ids:
                status = (row["cases"].get(cid) or {}).get(cfg)
                if status is None:
                    continue
                total += 1
                if status == "PASS":
                    passed += 1
            rates[cfg].append({"iteration": row["iteration"], "passed": passed, "total": total,
                               "pass_rate": (passed / total) if total else None})
    pair_slots = len(case_ids) * len(CONFIGS)
    return {
        "tool": "skill-up",
        "model": os.environ.get("SKILLUP_MODEL", MODEL),
        "skill": "karpathy-guidelines",
        "skill_why": WHY,
        "case_ids": case_ids,
        "iterations": iterations,
        "pass_rates": rates,
        "flake_pairs": flake_pairs,
        "flake_count": len(flake_pairs),
        "pair_slots": pair_slots,
        "flake_rate": (len(flake_pairs) / pair_slots) if pair_slots else None,
        "error_count": errors,
        "graded_count": graded,
    }


def decision(summary: dict) -> tuple[str, str]:
    """Return (PROMOTE or STAY, one-line reason)."""
    if summary.get("host_busy"):
        return "STAY", summary.get("host_busy_reason") or "HOST-BUSY"
    if summary.get("blocked"):
        return "STAY", summary["blocked"]
    iters = summary.get("iterations") or []
    if len(iters) < 2:
        return "STAY", "fewer than 2 finished iterations"
    if not summary.get("case_ids"):
        return "STAY", "no graded cases"
    missing = False
    for row in iters:
        for cid in summary["case_ids"]:
            got = row["cases"].get(cid) or {}
            if "with_skill" not in got or "without_skill" not in got:
                missing = True
    if missing:
        return "STAY", "a case is missing a with_skill or without_skill grade"
    if summary.get("error_count"):
        return "STAY", "%s engine error grades" % summary["error_count"]
    rate = summary.get("flake_rate")
    if rate is None or rate > 0.2:
        return "STAY", "flake rate %s is too high to read" % rate
    with_rates = [row["pass_rate"] for row in summary["pass_rates"]["with_skill"]]
    without_rates = [row["pass_rate"] for row in summary["pass_rates"]["without_skill"]]
    return "PROMOTE", (
        "baseline with_skill %s without_skill %s flake %s/%s"
        % (with_rates, without_rates, summary["flake_count"], summary["pair_slots"])
    )


def _binary_ok(path: Path) -> str | None:
    if not path.is_file():
        return "skill-up binary is missing"
    have = _sha256(path)
    if have != BIN_SHA:
        return "skill-up sha256 %s does not match the v0.14.0 pin" % have
    return None


def _model_present() -> str | None:
    base = os.environ.get("SKILLUP_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(base + "/api/tags", timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        return "Ollama tags failed: " + type(exc).__name__
    names = [str(row.get("name")) for row in (data.get("models") or []) if isinstance(row, dict)]
    if MODEL not in names:
        return "Ollama has no %s" % MODEL
    return None


def run_live(args: argparse.Namespace) -> dict:
    binary = find_binary()
    if binary is None:
        return {"blocked": "skill-up binary not found (SKILLUP_BIN or tmp/skill-up/skill-up)"}
    bad = _binary_ok(binary)
    if bad:
        return {"blocked": bad}
    ok, why = wait_for_memory()
    if not ok:
        return {"host_busy": True, "host_busy_reason": why, "blocked": why}
    missing = _model_present()
    if missing:
        return {"blocked": missing}
    work = ROOT / "tmp" / "skill-up-run"
    out = Path(args.output_dir) if args.output_dir else (ROOT / "tmp" / "skill-up-reports")
    for d in (work / "home", work / "xdg", work / "tmpdir", out):
        d.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    for key in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "all_proxy"):
        env.pop(key, None)
    env.update({
        "HOME": str(work / "home"),
        "XDG_CONFIG_HOME": str(work / "xdg"),
        "TMPDIR": str(work / "tmpdir"),
        "NO_PROXY": "*",
        "no_proxy": "*",
        "SKILLUP_ENGINE_BIN": str(ENGINE),
        "SKILLUP_SKILL_DIR": str(SKILL),
        "SKILLUP_MODEL": MODEL,
        "SKILLUP_PYTHON": sys.executable,
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    cmd = [
        str(binary), "run", str(EVAL_YAML),
        "--baseline",
        "--iteration", str(args.iteration),
        "--format", "json",
        "--format", "junit",
        "--output-dir", str(out),
        "--parallelism", "1",
    ]
    for name in args.include or []:
        cmd.extend(["--include-case-name", name])
    log_path = out / "skill-up.log"
    print("running " + " ".join(cmd), file=sys.stderr)
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.run(cmd, cwd=str(CASES), env=env, stdout=log, stderr=subprocess.STDOUT)
    summary = score_dir(out)
    summary["binary"] = str(binary)
    summary["binary_sha256"] = BIN_SHA
    summary["skill_up_exit"] = proc.returncode
    summary["log"] = str(log_path)
    summary["output_dir"] = str(out)
    summary["memory"] = why
    if proc.returncode not in (0, 1):
        summary["blocked"] = "skill-up exited %s (see %s)" % (proc.returncode, log_path)
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run or score the skill-up catch-up case set")
    ap.add_argument("--score", default="", help="score an existing output dir and print JSON")
    ap.add_argument("--output-dir", default="")
    ap.add_argument("--iteration", type=int, default=2)
    ap.add_argument("--include", action="append", default=[])
    ap.add_argument("--write-summary", default=str(SUMMARY))
    args = ap.parse_args(argv)
    if args.score:
        summary = score_dir(Path(args.score))
    else:
        summary = run_live(args)
    kind, reason = decision(summary)
    summary["decision"] = kind
    summary["decision_reason"] = reason
    text = json.dumps(summary, indent=2) + "\n"
    if args.score:
        sys.stdout.write(text)
    else:
        dest = Path(args.write_summary)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(text, encoding="utf-8")
        print(kind + " " + reason)
    if kind == "PROMOTE":
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
