#!/usr/bin/env python3
"""Run the real cloud reviewer on each planted diff.

The call matches CloudBuild.grok_call: grok -p PROMPT --cwd WORKDIR
--always-approve --output-format plain. The prompt is review_prompt().
The verdict is parse_verdict plus the root-delete override.

This process does not pass --local and does not read auth.json.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

from plant import decide, load_cases, load_cloud, prepare_workdir, review_argv, score

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]


def _mem_available_kib() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1])
    return 0


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run_grok(argv: list[str], cwd: Path, timeout: float) -> tuple[str, int, str, str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    scratch = cwd / "tmp"
    scratch.mkdir(parents=True, exist_ok=True)
    env["TMPDIR"] = str(scratch)
    try:
        proc = subprocess.Popen(
            argv,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except FileNotFoundError:
        return "missing", 127, "", "grok missing"
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, 15)
        try:
            out, err = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, 9)
            out, err = "", ""
        return "timeout", 124, out or "", err or ""
    code = proc.returncode if proc.returncode is not None else 1
    return "done", code, out or "", err or ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", required=True, choices=["before", "after"])
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--skip-done", action="store_true")
    args = parser.parse_args()
    if args.timeout <= 0:
        print("timeout must be positive")
        return 2
    mem = _mem_available_kib()
    if mem and mem < 16 * 1024 * 1024:
        print("host pressure: MemAvailable %s KiB" % mem)
        return 3
    grok = shutil.which("grok")
    if not grok:
        print("grok missing")
        return 1
    cloud = load_cloud()
    cases = load_cases()
    wanted = set(args.only)
    out_root = HERE / "results" / args.round
    out_root.mkdir(parents=True, exist_ok=True)
    rows = []
    stopped = ""
    for case in cases:
        ident = case["id"]
        if wanted and ident not in wanted:
            continue
        dest_dir = out_root / ident
        result_path = dest_dir / "result.json"
        if args.skip_done and result_path.is_file():
            prior = json.loads(result_path.read_text(encoding="utf-8"))
            if prior.get("status") == "done":
                rows.append(prior)
                continue
        diff_text = (HERE / case["diff"]).read_text(encoding="utf-8")
        work = ROOT / "tmp" / "review-quality-cwd" / ident
        row = {
            "id": ident,
            "expect": case["expect"],
            "bug": case.get("bug") or "",
            "status": "error",
            "verdict": None,
            "reasons": [],
        }
        try:
            prepare_workdir(work, diff_text)
        except RuntimeError as exc:
            row["error"] = str(exc)
            _write(result_path, json.dumps(row, indent=2) + "\n")
            rows.append(row)
            print("%s apply-failed" % ident)
            continue
        prompt = cloud.review_prompt(case["task"], diff_text, case.get("gate_tail") or "")
        argv = review_argv(grok, prompt, work)
        if "--local" in argv:
            row["error"] = "refusing --local"
            _write(result_path, json.dumps(row, indent=2) + "\n")
            rows.append(row)
            return 2
        _write(dest_dir / "prompt.txt", cloud.redact(prompt))
        started = time.monotonic()
        status, code, out, err = _run_grok(argv, work, args.timeout)
        elapsed = round(time.monotonic() - started, 3)
        shown_out = cloud.redact(out)
        shown_err = cloud.redact(err)
        _write(dest_dir / "stdout.txt", shown_out)
        _write(dest_dir / "stderr.txt", shown_err)
        kind = cloud.classify_runner_failure(code, out, err)
        row["elapsed_s"] = elapsed
        row["grok_status"] = status
        row["code"] = code
        if status == "timeout":
            row["status"] = "timeout"
            row["error"] = "timeout"
        elif status == "missing":
            row["status"] = "missing"
            row["error"] = "grok missing"
            stopped = "missing"
        elif kind == "rate-limit":
            row["status"] = "rate-limit"
            row["error"] = "rate-limit"
            stopped = "rate-limit"
        elif kind == "unauthenticated":
            row["status"] = "unauthenticated"
            row["error"] = "unauthenticated"
            stopped = "unauthenticated"
        else:
            verdict, reasons = decide(shown_out + ("\n" + shown_err if shown_err else ""), diff_text, cloud)
            row["status"] = "done"
            row["verdict"] = verdict
            row["reasons"] = reasons
        _write(result_path, json.dumps(row, indent=2) + "\n")
        rows.append(row)
        print("%s %s %s" % (ident, row["status"], row.get("verdict") or row.get("error")))
        shutil.rmtree(work, ignore_errors=True)
        if stopped:
            break
    summary = score(rows)
    summary["round"] = args.round
    summary["mem_available_kib"] = mem
    summary["stopped"] = stopped
    summary["cases"] = len(rows)
    _write(out_root / "summary.json", json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))
    if stopped:
        return 4
    if summary["error_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
