#!/usr/bin/env python3
"""Operate-or-FAIL smoke for X intake Entry 187 (OpenKB). Uses smoke.py helpers.

Usage: python3 examples/x-intake-local/smoke_187.py

This smoke checks the pinned GitHub commit SHA via the commits API (or from
$OPENKB_FETCH_BIN) and then exits 2. It does not clone the repo and it does
not install the tool or touch any agent home.

Exit 1 = the metadata fetch ran and the commit does not match the pin.
Exit 2 = metadata matches and the tool was not installed, or the fetch cannot run here.

Receipt: $PFY_SMOKE_RECEIPT_DIR/openkb/latest.json, else pipelines/smoke/openkb/latest.json.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

from smoke import find_bin, pinned, run_isolated, timeout_reason, write

PIN_COMMIT = 'ff54396e575ee6feb0113b631a34caa082b441cc'
PIN_REPO = 'VectifyAI/OpenKB'
FETCH = r"""
import json, sys, urllib.request
url, want = sys.argv[1], sys.argv[2].lower()
req = urllib.request.Request(url, headers={"User-Agent": "pfy-xintake", "Accept": "application/vnd.github+json"})
try:
    with urllib.request.urlopen(req, timeout=float(sys.argv[3])) as resp:
        data = json.load(resp)
except Exception as exc:
    print(json.dumps({"error": str(exc)}))
    raise SystemExit(2)
sha = (data.get("sha") or "").lower()
msg = ((data.get("commit") or {}).get("message") or "").split("\n")[0][:120]
print(json.dumps({"sha": sha, "match": sha == want, "message": msg}))
"""
WATCHED = ('.local/bin/openkb', '.openkb', '.config/openkb', '.agents/skills/openkb')


def _limit() -> float:
    raw = os.environ.get("PFY_XINTAKE_TIMEOUT", "").strip()
    if not raw:
        return 30.0
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError("PFY_XINTAKE_TIMEOUT is not a positive number") from exc
    if not math.isfinite(value) or value <= 0:
        raise ValueError("PFY_XINTAKE_TIMEOUT is not a positive number")
    return value


def _sig(home: Path) -> dict:
    out = {}
    for rel in WATCHED:
        path = home / rel
        out[rel] = path.exists()
    return out


def _fetch_cmd(commit: str, timeout: float):
    override = os.environ.get("OPENKB_FETCH_BIN")
    if override is not None:
        if not (os.path.isfile(override) and os.access(override, os.X_OK)):
            return f"openkb metadata fetcher is not executable ({override})"
        return [override]
    url = f"https://api.github.com/repos/VectifyAI/OpenKB/commits/{commit}"
    return [sys.executable, "-c", FETCH, url, commit, str(timeout)]


def body(rec: dict, home: str) -> int:
    commit = pinned(rec, "OPENKB_COMMIT", PIN_COMMIT, lower=True)
    timeout = _limit()
    cmd = _fetch_cmd(commit, timeout)
    if isinstance(cmd, str):
        rec["reason"] = cmd
        return 2
    rec["checks"]["local_bin"] = find_bin("OPENKB_BIN", "OpenKB/bin/openkb", "openkb")
    before = _sig(Path(home))
    after = before
    try:
        try:
            proc = run_isolated(
                cmd, home=home, timeout=timeout, bwrap_writable=None, kill_on_exit=True,
            )
        except subprocess.TimeoutExpired:
            rec["reason"] = timeout_reason("openkb metadata", timeout)
            return 2
    finally:
        after = _sig(Path(home))
    if after != before:
        rec["reason"] = "openkb smoke wrote under the real HOME"
        rec["checks"]["home_sig"] = {"before": before, "after": after}
        return 1
    rec["checks"]["fetch_rc"] = proc.returncode
    rec["checks"]["fetch_out"] = ((proc.stdout or "") + (proc.stderr or ""))[-2000:]
    if proc.returncode != 0:
        rec["reason"] = f"openkb metadata fetch exited {proc.returncode}"
        return 2
    try:
        payload = json.loads((proc.stdout or "").strip().splitlines()[-1])
    except Exception as exc:
        rec["reason"] = f"openkb metadata JSON parse failed: {exc}"
        return 2
    if payload.get("error"):
        rec["reason"] = f"openkb metadata error: {payload.get('error')}"
        return 2
    got = (payload.get("sha") or "").lower()
    rec["checks"]["sha"] = got
    rec["checks"]["message"] = payload.get("message")
    if got != commit:
        rec["reason"] = f"openkb commit mismatch: want {commit} got {got}"
        return 1
    rec["reason"] = "openkb commit pin matched; tool not installed (catalog-only)"
    return 2


def main() -> int:
    rec = {"tool": "openkb", "entry": 187, "checks": {}}
    home = os.environ.get("HOME") or str(Path.home())
    try:
        code = body(rec, home)
    except ValueError as exc:
        rec["reason"] = str(exc)
        code = 2
    except Exception as exc:
        rec["reason"] = f"unhandled: {type(exc).__name__}: {exc}"
        code = 1
    write("openkb", rec, code)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
