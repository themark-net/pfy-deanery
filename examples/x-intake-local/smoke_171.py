#!/usr/bin/env python3
"""Operate-or-FAIL smoke for X intake Entry 171 (LocalHarness). Uses smoke.py helpers.

Usage: python3 examples/x-intake-local/smoke_171.py

This smoke checks the pinned GitHub commit SHA via the commits API (or from
$LOCALHARNESS_FETCH_BIN) and then exits 2. It does not clone the repo and it does
not install the tool or touch any agent home.

Exit 1 = the metadata fetch ran and the commit does not match the pin.
Exit 2 = metadata matches and the tool was not installed, or the fetch cannot run here.

Receipt: $PFY_SMOKE_RECEIPT_DIR/localharness/latest.json, else pipelines/smoke/localharness/latest.json.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path

from smoke import find_bin, pinned, run_isolated, timeout_reason, write

PIN_COMMIT = '5af7511ce8f8f799f74de877698e4c4aec0dec45'
PIN_REPO = 'ahwurm/localharness'
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
WATCHED = ('.localharness', '.local/bin/localharness', '.local/share/uv/tools/localharness')


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
    override = os.environ.get("LOCALHARNESS_FETCH_BIN")
    if override is not None:
        if not (os.path.isfile(override) and os.access(override, os.X_OK)):
            return f"localharness metadata fetcher is not executable ({override})"
        return [override]
    url = f"https://api.github.com/repos/ahwurm/localharness/commits/{commit}"
    return [sys.executable, "-c", FETCH, url, commit, str(timeout)]


def body(rec: dict, home: str) -> int:
    commit = pinned(rec, "LOCALHARNESS_COMMIT", PIN_COMMIT, lower=True)
    timeout = _limit()
    cmd = _fetch_cmd(commit, timeout)
    if isinstance(cmd, str):
        rec["reason"] = cmd
        return 2
    rec["checks"]["local_bin"] = find_bin("LOCALHARNESS_BIN", "localharness/localharness", "localharness")
    before = _sig(Path(home))
    after = before
    try:
        try:
            proc = run_isolated(
                cmd, home=home, timeout=timeout, bwrap_writable=None, kill_on_exit=True,
            )
        except subprocess.TimeoutExpired:
            rec["reason"] = timeout_reason("localharness metadata", timeout)
            return 2
    finally:
        after = _sig(Path(home))
    if after != before:
        rec["reason"] = "localharness smoke wrote under the real HOME"
        rec["checks"]["home_sig"] = {"before": before, "after": after}
        return 1
    rec["checks"]["fetch_rc"] = proc.returncode
    rec["checks"]["fetch_out"] = ((proc.stdout or "") + (proc.stderr or ""))[-2000:]
    if proc.returncode != 0:
        rec["reason"] = f"localharness metadata fetch exited {proc.returncode}"
        return 2
    try:
        payload = json.loads((proc.stdout or "").strip().splitlines()[-1])
    except Exception as exc:
        rec["reason"] = f"localharness metadata JSON parse failed: {exc}"
        return 2
    if payload.get("error"):
        rec["reason"] = f"localharness metadata error: {payload.get('error')}"
        return 2
    got = (payload.get("sha") or "").lower()
    rec["checks"]["sha"] = got
    rec["checks"]["message"] = payload.get("message")
    if got != commit:
        rec["reason"] = f"localharness commit mismatch: want {commit} got {got}"
        return 1
    rec["reason"] = "localharness commit pin matched; tool not installed (catalog-only)"
    return 2


def main() -> int:
    rec = {"tool": "localharness", "entry": 171, "checks": {}}
    home = os.environ.get("HOME") or str(Path.home())
    try:
        code = body(rec, home)
    except ValueError as exc:
        rec["reason"] = str(exc)
        code = 2
    except Exception as exc:
        rec["reason"] = f"unhandled: {type(exc).__name__}: {exc}"
        code = 1
    write("localharness", rec, code)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
