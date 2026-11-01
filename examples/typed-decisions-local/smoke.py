#!/usr/bin/env python3
"""Operate-or-FAIL smokes for X intake Entries 086-088 (Laya, Bespoke Nimble, Beacon). Stdlib only.

Usage: python3 examples/typed-decisions-local/smoke.py --entry laya|nimble|beacon

Exit 0 = PASS. 1 = the tool ran but the check failed. 2 = can't run here (prereq missing; reason recorded).
Writes pipelines/smoke/<entry>/latest.json every time. Never installs anything, never downloads into the repo.

  laya    $LAYA_PYTHON or ~/DEVELOP/pfy-mentat/tmp/laya-venv/bin/python with `pip install laya`.
          Runs the upstream README billing example on CPU and expects department == billing.
  nimble  Needs an NVIDIA BF16 GPU (Linux) or Apple Silicon, plus $NIMBLE_DIR (prepared checkout with
          .cache/nimble-model.json) and $NIMBLE_PYTHON. Expects priority == HIGH, requires_review == true.
  beacon  $BEACON_BIN or `beacon` on PATH. Runs --version (falls back to --help). Install-only check.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TMP_VENV = Path.home() / "DEVELOP/pfy-mentat/tmp/laya-venv/bin/python"

LAYA_CODE = r"""
import json
from laya import Router
router = Router(device="cpu")
state = "Hi, we were billed twice for March. Please refund the duplicate today or we will cancel our plan."
q = {"department": {"type": "choice", "instructions": "Which department should handle this?",
     "criteria": {"billing": "invoices, payments, refunds", "technical": "bugs, outages, system errors",
                  "other": "everything else"}}}
r = router.predict(state, q)
a = r["answers"]["department"]
print(json.dumps({"choice": a.get("choice"), "answer_confidence": a.get("answer_confidence"),
                  "model": (r.get("routing") or {}).get("model")}))
"""

NIMBLE_CODE = r"""
import json, platform
from pathlib import Path
config = json.loads(Path(".cache/nimble-model.json").read_text())
if platform.system() == "Darwin":
    from nimble.scoring.parallel_scorer import ParallelScorer as S
else:
    from nimble.scoring.cuda_scorer import CudaCandidateScorer as S
scorer = S(**config)
schema = {"priority": {"type": "enum", "choices": ["HIGH", "LOW"],
          "description": "Urgency based on current business impact.",
          "choice_descriptions": {"HIGH": "A critical business operation is currently blocked.",
                                  "LOW": "An optional enhancement with no current business impact."}},
          "requires_review": {"type": "boolean",
          "description": "Whether customers are unable to complete a purchase."}}
r = scorer.score("The payment service is down for all customers.", schema)
print(json.dumps(r["output"]))
"""


def write(entry: str, receipt: dict, code: int) -> int:
    override = os.environ.get("PFY_SMOKE_RECEIPT_DIR")
    if override:
        dest = Path(override)
        if not dest.is_absolute():
            print("PFY_SMOKE_RECEIPT_DIR must be absolute")
            return 1
        out = dest / entry / "latest.json"
    else:
        out = ROOT / "pipelines/smoke" / entry / "latest.json"
    receipt["exit_code"] = code
    receipt["verdict"] = {0: "PASS", 1: "FAIL", 2: "FAIL_CANNOT_RUN_HERE"}[code]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: receipt.get(k) for k in ("verdict", "reason")}, ensure_ascii=False))
    print(f"receipt: {out}")
    return code


def run(cmd: list[str], cwd: str | None = None, timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def last_json(text: str) -> dict | None:
    for line in reversed(text.strip().splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            continue
    return None


def smoke_laya(r: dict) -> int:
    py = Path(os.environ.get("LAYA_PYTHON") or TMP_VENV)
    r["python"] = str(py)
    if not os.access(py, os.X_OK):
        r["reason"] = (f"no Laya venv at {py}. Operator: python3 -m venv ~/DEVELOP/pfy-mentat/tmp/laya-venv && "
                       "~/DEVELOP/pfy-mentat/tmp/laya-venv/bin/python -m pip install laya (inside ~/DEVELOP only)")
        return 2
    t = time.time()
    try:
        p = run([str(py), "-c", LAYA_CODE])
    except subprocess.TimeoutExpired:
        r["reason"] = "laya run timed out (first run downloads the checkpoint from the HF hub)"
        return 1
    r["seconds"] = round(time.time() - t, 1)
    out = last_json(p.stdout)
    r["output"] = out
    if p.returncode != 0 or not out:
        r["reason"] = f"laya rc={p.returncode}: {(p.stderr or p.stdout)[-800:]}"
        return 1
    if out.get("choice") != "billing":
        r["reason"] = f"expected billing, got {out.get('choice')!r}"
        return 1
    return 0


def smoke_nimble(r: dict) -> int:
    apple = platform.system() == "Darwin" and platform.machine() == "arm64"
    nvidia = shutil.which("nvidia-smi") is not None
    r["hardware"] = {"apple_silicon": apple, "nvidia_smi": nvidia, "machine": platform.machine()}
    if not (apple or nvidia):
        r["reason"] = ("upstream supports only Apple Silicon (MLX) or Linux with an NVIDIA BF16 GPU (CUDA); "
                       "this host has neither (nimo is AMD Strix Halo). ROCm/CPU path is undocumented upstream")
        return 2
    d, py = os.environ.get("NIMBLE_DIR"), os.environ.get("NIMBLE_PYTHON")
    if not d or not py or not (Path(d) / ".cache/nimble-model.json").exists():
        r["reason"] = "set NIMBLE_DIR (prepared checkout with .cache/nimble-model.json) and NIMBLE_PYTHON"
        return 2
    t = time.time()
    try:
        p = run([py, "-c", NIMBLE_CODE], cwd=d)
    except subprocess.TimeoutExpired:
        r["reason"] = "nimble run timed out"
        return 1
    r["seconds"] = round(time.time() - t, 1)
    out = last_json(p.stdout)
    r["output"] = out
    if p.returncode != 0 or not out:
        r["reason"] = f"nimble rc={p.returncode}: {(p.stderr or p.stdout)[-800:]}"
        return 1
    if out.get("priority") != "HIGH" or out.get("requires_review") is not True:
        r["reason"] = f"expected HIGH/true, got {out}"
        return 1
    return 0


def smoke_beacon(r: dict) -> int:
    b = os.environ.get("BEACON_BIN") or shutil.which("beacon")
    r["bin"] = b
    r["note"] = "install-only check; capture and learning are not exercised"
    if not b or not os.access(b, os.X_OK):
        r["reason"] = ("no beacon binary. Use upstream's user-mode tarball under ~/DEVELOP/pfy-mentat/tmp "
                       "(no sudo), choose Local, no beacon.sh sign-in, skills install off")
        return 2
    for flag in ("--version", "--help"):
        try:
            p = run([b, flag], timeout=60)
        except subprocess.TimeoutExpired:
            continue
        if p.returncode == 0:
            r["output"] = (p.stdout or p.stderr)[:600]
            r["flag"] = flag
            return 0
    r["reason"] = "beacon binary present but --version and --help both failed"
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", required=True, choices=["laya", "nimble", "beacon"])
    a = ap.parse_args()
    receipt = {"entry": a.entry, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "host": os.uname().nodename}
    code = {"laya": smoke_laya, "nimble": smoke_nimble, "beacon": smoke_beacon}[a.entry](receipt)
    return write(a.entry, receipt, code)


if __name__ == "__main__":
    sys.exit(main())
