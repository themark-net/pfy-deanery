"""Shared apply ledger writer.

CLI ``pfy toolset apply`` and Loop Launch session both record through
``toolsets.apply``, which calls this module. One file:
``$PFY_STATE_DIR/installed.json`` (the ``--state`` / GUI STATE dir).
This is not the setup/uninstall XDG ledger.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path

from . import registry
from .adapters.base import atomic_write, tree_hash

FIELDS = ("backup", "harness", "item", "kind", "path", "sha256_after")


def path_for(state: str | os.PathLike | None = None) -> Path:
    return registry.state_dir(state) / "installed.json"


def content_sha(path: Path) -> str:
    try:
        info = path.lstat()
    except OSError:
        return ""
    if stat.S_ISLNK(info.st_mode):
        return hashlib.sha256(os.readlink(path).encode("utf-8")).hexdigest()
    if stat.S_ISREG(info.st_mode):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    if stat.S_ISDIR(info.st_mode):
        return tree_hash(path)
    return ""


def load(path: Path) -> list[dict]:
    if not path.is_file():
        if path.exists() or path.is_symlink():
            raise OSError("ledger is not a file: %s" % path)
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        recs = data.get("records") or []
    elif isinstance(data, list):
        recs = data
    else:
        raise OSError("malformed ledger %s" % path)
    if not isinstance(recs, list):
        raise OSError("malformed ledger %s" % path)
    return [r for r in recs if isinstance(r, dict)]


def save(path: Path, records: list[dict]) -> None:
    payload = {"records": records}
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if path.is_file() and path.read_bytes() == data:
        return
    atomic_write(path, data)


def _canon(rec: dict) -> dict:
    return {k: str(rec.get(k) or "") for k in FIELDS}


def upsert(records: list[dict], rec: dict) -> bool:
    body = _canon(rec)
    key = (body["harness"], body["item"], body["path"], body["kind"])
    for i, old in enumerate(records):
        old_key = (
            str(old.get("harness") or ""),
            str(old.get("item") or ""),
            str(old.get("path") or ""),
            str(old.get("kind") or ""),
        )
        if old_key == key:
            if _canon(old) == body:
                return False
            records[i] = body
            return True
    records.append(body)
    return True


def record_apply(
    state: str | os.PathLike | None,
    *,
    harness: str,
    item: str,
    applied: list[dict],
) -> Path:
    """Upsert one file row per successful apply. Raises OSError on a bad ledger path."""
    path = path_for(state)
    records = load(path)
    changed = False
    for row in applied:
        target = Path(str(row.get("path") or ""))
        rec = {
            "harness": harness,
            "item": item,
            "kind": "file",
            "path": str(target),
            "sha256_after": content_sha(target),
            "backup": "",
        }
        if upsert(records, rec):
            changed = True
    if changed or not path.is_file():
        save(path, records)
    return path
