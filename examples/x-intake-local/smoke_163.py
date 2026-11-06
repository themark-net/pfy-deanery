#!/usr/bin/env python3
"""Operate-or-FAIL smoke for X intake Entry 163 (magpie). Uses smoke.py helpers.

Usage: python3 examples/x-intake-local/smoke_163.py

This smoke checks the pinned Linux release asset's name, size, and digest from the
GitHub release JSON (or from $MAGPIE_FETCH_BIN) and then exits 2. It does not
download the asset and it does not run the tool.

Exit 1 = the metadata fetch ran and the asset does not match the pin.
Exit 2 = metadata matches and the tool was not launched, or the fetch cannot run here.

Receipt: $PFY_SMOKE_RECEIPT_DIR/magpie/latest.json, else pipelines/smoke/magpie/latest.json.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from smoke import find_bin, pinned, run_isolated, timeout_reason, write

PIN_TAG = 'v0.1.3081'
PIN_ASSET = 'magpie-cli-linux-amd64'
PIN_SHA = '6aaf6d22a43fcb01f3aee865ce721aa99fcc509ce9f4938bcff77fc134996adb'
PIN_SIZE = '71479458'
PIN_COMMIT = '4e7661adcee3ff019a729edcbae987b536ef4b53'
FETCH = r"""
import json, sys, urllib.request
url, asset = sys.argv[1], sys.argv[2]
req = urllib.request.Request(url, headers={"User-Agent": "pfy-xintake", "Accept": "application/vnd.github+json"})
try:
    with urllib.request.urlopen(req, timeout=float(sys.argv[3])) as resp:
        data = json.load(resp)
except Exception as exc:
    print(json.dumps({"error": str(exc)}))
    raise SystemExit(2)
assets = []
for item in data.get("assets") or []:
    if item.get("name") == asset:
        assets.append({"name": item.get("name"), "size": item.get("size"), "digest": item.get("digest")})
print(json.dumps({"tag": data.get("tag_name"), "commit": data.get("target_commitish"), "assets": assets}))
"""
WATCHED = ('.config/magpie', '.magpie')


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


def _fetch_cmd(tag: str, asset: str, timeout: float) -> list[str] | str:
    override = os.environ.get("MAGPIE_FETCH_BIN")
    if override is not None:
        if not (os.path.isfile(override) and os.access(override, os.X_OK)):
            return f"magpie metadata fetcher is not executable ({override})"
        return [override]
    url = f"https://api.github.com/repos/yetone/magpie-releases/releases/tags/{tag}"
    return [sys.executable, "-c", FETCH, url, asset, str(timeout)]


def body(rec: dict, home: str) -> int:
    tag = pinned(rec, "MAGPIE_TAG", PIN_TAG)
    asset = pinned(rec, "MAGPIE_ASSET", PIN_ASSET)
    sha = pinned(rec, "MAGPIE_SHA256", PIN_SHA, lower=True)
    size = pinned(rec, "MAGPIE_SIZE", PIN_SIZE)
    commit = pinned(rec, "MAGPIE_COMMIT", PIN_COMMIT, lower=True)
    timeout = _limit()
    cmd = _fetch_cmd(tag, asset, timeout)
    if isinstance(cmd, str):
        rec["reason"] = cmd
        return 2
    rec["checks"]["local_bin"] = find_bin("MAGPIE_BIN", "magpie/magpie", "magpie")
    try:
        proc = run_isolated(
            cmd, home=home, timeout=timeout, bwrap_writable=None, kill_on_exit=True,
        )
    except subprocess.TimeoutExpired:
        rec["reason"] = timeout_reason("magpie metadata", timeout)
        return 2
    except OSError as exc:
        rec["reason"] = f"magpie metadata fetcher failed to start: {exc}"
        return 2
    raw = (proc.stdout or "").strip()
    if proc.returncode != 0 or not raw:
        rec["reason"] = "magpie release metadata could not be read: " + ((proc.stderr or raw)[-300:])
        return 2
    try:
        data = json.loads(raw.splitlines()[-1])
    except json.JSONDecodeError:
        rec["reason"] = "magpie metadata was not JSON"
        return 2
    if data.get("error"):
        rec["reason"] = "magpie release metadata could not be read: " + str(data["error"])[:300]
        return 2
    got = (data.get("assets") or [None])[0] or {}
    digest = str(got.get("digest") or "")
    hexpart = digest.split(":", 1)[-1].lower()
    got_commit = str(data.get("commit") or "").lower()
    match = (
        data.get("tag") == tag
        and got.get("name") == asset
        and str(got.get("size")) == str(size)
        and hexpart == sha
        and (not _is_sha(got_commit) or got_commit == commit)
    )
    rec["checks"]["asset"] = {"name": got.get("name"), "size": got.get("size"), "digest": digest, "commit": got_commit}
    if not match:
        rec["reason"] = f"magpie release asset does not match pin {tag} {asset} {sha} {size}"
        rec["failed"] = ["asset_pin"]
        return 1
    rec["reason"] = (
        f"Linux release asset {asset} matches pin {tag} (sha256 {sha}, {size} bytes) "
        f"at commit {commit}; magpie CLI binary was not downloaded or run"
    )
    return 2


def _is_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value)


def main() -> int:
    rec: dict = {"entry": "163-magpie", "failed": [], "checks": {}}
    before = _sig(Path.home())
    home = tempfile.mkdtemp(prefix="magpie-smoke-")
    code = 1
    try:
        code = body(rec, home)
    except ValueError as exc:
        rec["reason"] = str(exc)
        code = 2
    finally:
        shutil.rmtree(home, ignore_errors=True)
        if _sig(Path.home()) != before:
            rec["reason"] = "real HOME magpie paths changed"
            rec["failed"] = ["real_home_unchanged"]
            code = 1
    return write("magpie", rec, code)


if __name__ == "__main__":
    raise SystemExit(main())
