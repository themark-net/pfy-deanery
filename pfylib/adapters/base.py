"""Shared adapter types. No launch() in phase 1."""
# resolution follows morluto/rea SupportedClients, MIT
from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import tomllib
from pathlib import Path

MARKER = b"pfy\n"
MARKER_NAME = ".pfy-owned"


class Detection:
    def __init__(self, found: bool, detail: str = ""):
        self.found = found
        self.detail = detail


class Paths:
    def __init__(self, config: Path, skills: Path):
        self.config = config
        self.skills = skills


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmpname = tempfile.mkstemp(prefix=".pfy-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmpname, path)
    except Exception:
        try:
            os.unlink(tmpname)
        except OSError:
            pass
        raise


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _hash_rows(rows: list[tuple[str, bytes]]) -> str:
    h = hashlib.sha256()
    for rel, data in rows:
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(data)
        h.update(b"\0")
    return h.hexdigest()


def tree_hash(root: Path) -> str:
    rows: list[tuple[str, bytes]] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        base = Path(dirpath)
        for name in list(dirnames) + list(filenames):
            path = base / name
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                data = os.readlink(path).encode("utf-8")
            elif stat.S_ISREG(info.st_mode):
                data = path.read_bytes()
            else:
                continue
            rows.append((path.relative_to(root).as_posix(), data))
    rows.sort()
    return _hash_rows(rows)


def desired_skill_hash(src: Path) -> str:
    rows: list[tuple[str, bytes]] = []
    for dirpath, dirnames, filenames in os.walk(src, followlinks=False):
        base = Path(dirpath)
        for name in list(dirnames) + list(filenames):
            if name == MARKER_NAME:
                continue
            path = base / name
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                data = os.readlink(path).encode("utf-8")
            elif stat.S_ISREG(info.st_mode):
                data = path.read_bytes()
            else:
                continue
            rows.append((path.relative_to(src).as_posix(), data))
    rows.append((MARKER_NAME, MARKER))
    rows.sort()
    return _hash_rows(rows)


def toml_string_array(args: list) -> str:
    return "[" + ", ".join(json.dumps(str(a)) for a in args) + "]"


def mcp_object(item_id: str, entry: dict) -> dict:
    obj: dict = {"command": entry["command"]}
    if "args" in entry:
        obj["args"] = list(entry["args"])
    env = entry.get("env") or {}
    if env:
        obj["env"] = env
    if entry.get("startup_timeout_sec") is not None:
        obj["startup_timeout_sec"] = entry["startup_timeout_sec"]
    obj["_pfy"] = {"owner": "pfy", "item": item_id, "v": "1"}
    return obj


def render_toml_mcp(current: bytes | None, item_id: str, entry: dict) -> bytes:
    """Append a managed table. Never reserialize: comments stay byte-for-byte."""
    raw = current if current is not None else b""
    text = raw.decode("utf-8")
    name = str(entry["name"])
    marker = "# managed-by: pfy item=%s" % item_id
    header = "[mcp_servers.%s]" % name
    if marker in text and header in text:
        return raw
    lines = [
        "",
        marker,
        header,
        "command = %s" % json.dumps(str(entry["command"])),
    ]
    if "args" in entry:
        lines.append("args = %s" % toml_string_array(list(entry.get("args") or [])))
    if entry.get("startup_timeout_sec") is not None:
        lines.append("startup_timeout_sec = %s" % int(entry["startup_timeout_sec"]))
    addition = "\n".join(lines) + "\n"
    if text and not text.endswith("\n"):
        addition = "\n" + addition.lstrip("\n")
    return (text + addition).encode("utf-8")


def render_json_mcp(current: bytes | None, item_id: str, entry: dict, parent_fn) -> bytes:
    obj = mcp_object(item_id, entry)
    if current:
        data = json.loads(current.decode("utf-8"))
    else:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("config is not a JSON object")
    parent = parent_fn(data)
    name = str(entry["name"])
    if current is not None and parent.get(name) == obj:
        return current
    parent[name] = obj
    return (json.dumps(data, indent=2) + "\n").encode("utf-8")


def parse_config(path: Path, kind: str) -> str | None:
    """Return an error string (path + next) or None. Missing files are fine."""
    if not path.exists():
        return None
    if path.is_dir():
        return "malformed %s\nnext: expected a file, found a directory" % path
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return "malformed %s (%s)\nnext: fix the file, then re-run pfy setup" % (path, exc)
    try:
        if kind == "json":
            json.loads(text)
        else:
            tomllib.loads(text)
    except (json.JSONDecodeError, tomllib.TOMLDecodeError, UnicodeError) as exc:
        return "malformed %s (%s)\nnext: fix the file, then re-run pfy setup" % (path, exc)
    return None


def backup_once(path: Path) -> str:
    """First backup is path + '.pfy.backup'. Never overwrite an existing backup."""
    if not path.is_file():
        return ""
    dest = Path(str(path) + ".pfy.backup")
    if not dest.exists():
        shutil.copy(path, dest)
    return str(dest)


def install_skill_tree(src: Path, dest: Path) -> tuple[bool, str]:
    """Copy src to dest and write .pfy-owned. Return (wrote, tree sha256)."""
    desired = desired_skill_hash(src)
    if dest.is_dir() and (dest / MARKER_NAME).is_file() and tree_hash(dest) == desired:
        return False, desired
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dest)
    (dest / MARKER_NAME).write_bytes(MARKER)
    got = tree_hash(dest)
    if got != desired:
        raise RuntimeError("skill copy hash mismatch: %s" % dest)
    return True, got


def _delete_pfy_entry(obj: dict, item_id: str) -> bool:
    removed = False
    for key in list(obj.keys()):
        val = obj[key]
        if (
            isinstance(val, dict)
            and isinstance(val.get("_pfy"), dict)
            and str(val["_pfy"].get("item") or "") == item_id
        ):
            del obj[key]
            removed = True
            continue
        if isinstance(val, dict) and _delete_pfy_entry(val, item_id):
            removed = True
            if val == {}:
                del obj[key]
    return removed


def _strip_json_item(raw: bytes, item_id: str) -> bytes | None:
    """Return stripped bytes, or None when nothing meaningful remains."""
    try:
        data = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeError):
        return raw
    if not isinstance(data, dict) or not _delete_pfy_entry(data, item_id):
        return raw
    if not data:
        return None
    return (json.dumps(data, indent=2) + "\n").encode("utf-8")


def _strip_toml_item(text: str, item_id: str) -> str | None:
    marker = "# managed-by: pfy item=%s" % item_id
    if marker not in text:
        return text
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        if marker in lines[i]:
            i += 1
            if i < len(lines) and lines[i].strip().startswith("["):
                i += 1
            while i < len(lines):
                stripped = lines[i].strip()
                if stripped.startswith("[") or stripped.startswith("# managed-by:"):
                    break
                i += 1
            continue
        out.append(lines[i])
        i += 1
    result = "".join(out)
    if not result.strip():
        return None
    return result


def remove_created_file(path: Path, sha: str, item_id: str, kind: str) -> str:
    """Drop a file pfy created, or only its entry when other content remains.

    The ledger hash must still match. A mismatch is a user edit: leave the file.
    """
    if not path.exists():
        return "absent"
    if not path.is_file() or file_sha(path) != sha:
        return "warn"
    raw = path.read_bytes()
    if kind == "json":
        new = _strip_json_item(raw, item_id)
    else:
        stripped = _strip_toml_item(raw.decode("utf-8"), item_id)
        new = None if stripped is None else stripped.encode("utf-8")
    if new is None or not new.strip() or new == raw:
        path.unlink()
        return "removed"
    atomic_write(path, new)
    return "removed"


def restore_file(path: Path, backup: str, sha: str) -> str:
    """Copy the backup back when the live hash still matches, then delete that backup."""
    if not path.is_file():
        return "absent"
    if file_sha(path) != sha:
        return "warn"
    if not backup:
        return "warn"
    bpath = Path(backup)
    if not bpath.is_file():
        return "warn"
    data = bpath.read_bytes()
    atomic_write(path, data)
    if path.is_file() and path.read_bytes() == data:
        bpath.unlink()
    return "restored"


def remove_skill_dir(path: Path, sha: str) -> str:
    if not path.exists():
        return "absent"
    if not path.is_dir() or not (path / MARKER_NAME).is_file():
        return "warn"
    if tree_hash(path) != sha:
        return "warn"
    shutil.rmtree(path)
    return "removed"


class Adapter:
    id = ""
    config_kind = "json"

    def detect(self) -> Detection:
        cfg = self.config_path()
        found = cfg.is_file() or self.marker_dir().is_dir()
        return Detection(found, "directory or config file")

    def marker_dir(self) -> Path:
        return self.config_path().parent

    def config_path(self) -> Path:
        raise NotImplementedError

    def skills_dir(self) -> Path:
        raise NotImplementedError

    def paths(self) -> Paths:
        return Paths(self.config_path(), self.skills_dir())

    def plan_mcp(self, item_id: str, entry: dict) -> list[dict]:
        return [
            {
                "harness": self.id,
                "item": item_id,
                "kind": "mcp",
                "path": self.config_path(),
                "entry": entry,
            }
        ]

    def plan_skill(self, item_id: str, skill: dict, src: Path) -> list[dict]:
        name = str(skill["name"])
        return [
            {
                "harness": self.id,
                "item": item_id,
                "kind": "skill",
                "path": self.skills_dir() / name,
                "src": src,
                "name": name,
            }
        ]

    def render_config(self, current: bytes | None, item_id: str, entry: dict) -> bytes:
        raise NotImplementedError

    def remove(self, owned: dict) -> str:
        kind = owned.get("kind")
        path = Path(owned["path"]) if owned.get("path") else None
        sha = str(owned.get("sha256_after") or "")
        if kind == "delegate":
            return "delegate"
        if kind == "skill":
            if path is None:
                return "skip"
            return remove_skill_dir(path, sha)
        if kind in ("mcp", "file"):
            if path is None:
                return "skip"
            backup = str(owned.get("backup") or "")
            if not backup:
                return remove_created_file(path, sha, str(owned.get("item") or ""), self.config_kind)
            return restore_file(path, backup, sha)
        return "skip"
