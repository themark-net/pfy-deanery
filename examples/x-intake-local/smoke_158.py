#!/usr/bin/env python3
"""Operate-or-FAIL smoke for X intake Entry 158 (Emdash). Uses smoke.py helpers.

Usage: python3 examples/x-intake-local/smoke_158.py

Emdash is an Electron GUI. This smoke checks the pinned Linux release asset's
name, size, and digest from the GitHub release JSON (or from $EMDASH_FETCH_BIN)
and then exits 2. It does not download the AppImage and it does not launch the app.

Exit 1 = the metadata fetch ran and the asset does not match the pin.
Exit 2 = metadata matches and the GUI was not launched, or the fetch cannot run here.

Receipt: $PFY_SMOKE_RECEIPT_DIR/emdash/latest.json, else pipelines/smoke/emdash/latest.json.
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

PIN_TAG = "v1.2.10"
PIN_ASSET = "emdash-x86_64.AppImage"
PIN_SHA = "274586c70ba70466667fa811c5ead49610493859bed8c51e4f9abc0850c26d7d"
PIN_SIZE = "233276140"
PIN_COMMIT = "ab766e8fbb436584dcf0f299740e79d559b8ed31"
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
WATCHED = (".config/emdash", ".local/share/emdash", ".emdash")


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
    override = os.environ.get("EMDASH_FETCH_BIN")
    if override is not None:
        if not (os.path.isfile(override) and os.access(override, os.X_OK)):
            return f"emdash metadata fetcher is not executable ({override})"
        return [override]
    url = f"https://api.github.com/repos/generalaction/emdash/releases/tags/{tag}"
    return [sys.executable, "-c", FETCH, url, asset, str(timeout)]


def body(rec: dict, home: str) -> int:
    tag = pinned(rec, "EMDASH_TAG", PIN_TAG)
    asset = pinned(rec, "EMDASH_ASSET", PIN_ASSET)
    sha = pinned(rec, "EMDASH_SHA256", PIN_SHA, lower=True)
    size = pinned(rec, "EMDASH_SIZE", PIN_SIZE)
    commit = pinned(rec, "EMDASH_COMMIT", PIN_COMMIT, lower=True)
    timeout = _limit()
    cmd = _fetch_cmd(tag, asset, timeout)
    if isinstance(cmd, str):
        rec["reason"] = cmd
        return 2
    # No local binary is required. Record one if a staged copy exists, and do not launch it.
    rec["checks"]["local_bin"] = find_bin("EMDASH_BIN", "emdash/emdash", "emdash")
    try:
        proc = run_isolated(
            cmd, home=home, timeout=timeout, bwrap_writable=None, kill_on_exit=True,
        )
    except subprocess.TimeoutExpired:
        rec["reason"] = timeout_reason("emdash metadata", timeout)
        return 2
    except OSError as exc:
        rec["reason"] = f"emdash metadata fetcher failed to start: {exc}"
        return 2
    raw = (proc.stdout or "").strip()
    if proc.returncode != 0 or not raw:
        rec["reason"] = "emdash release metadata could not be read: " + ((proc.stderr or raw)[-300:])
        return 2
    try:
        data = json.loads(raw.splitlines()[-1])
    except json.JSONDecodeError:
        rec["reason"] = "emdash metadata was not JSON"
        return 2
    if data.get("error"):
        rec["reason"] = "emdash release metadata could not be read: " + str(data["error"])[:300]
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
        rec["reason"] = f"emdash release asset does not match pin {tag} {asset} {sha} {size}"
        rec["failed"] = ["asset_pin"]
        return 1
    rec["reason"] = (
        f"Linux release asset {asset} matches pin {tag} (sha256 {sha}, {size} bytes) "
        f"at commit {commit}; Emdash is an Electron GUI desktop app and was not launched"
    )
    return 2


def _is_sha(value: str) -> bool:
    return len(value) == 40 and all(ch in "0123456789abcdef" for ch in value)


def main() -> int:
    rec: dict = {"entry": "158-emdash", "failed": [], "checks": {}}
    before = _sig(Path.home())
    home = tempfile.mkdtemp(prefix="emdash-smoke-")
    code = 1
    try:
        code = body(rec, home)
    except ValueError as exc:
        rec["reason"] = str(exc)
        code = 2
    finally:
        shutil.rmtree(home, ignore_errors=True)
        if _sig(Path.home()) != before:
            rec["reason"] = "real HOME emdash paths changed"
            rec["failed"] = ["real_home_unchanged"]
            code = 1
    return write("emdash", rec, code)


if __name__ == "__main__":
    raise SystemExit(main())
