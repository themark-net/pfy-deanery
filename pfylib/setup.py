"""pfy setup, doctor, and uninstall (phase 1).

Selection, parse-before-write, ledger, and the rea delegate. Adapters own
paths. Stdlib only. Doctor does not exec npx.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import registry
from .adapters import ADAPTERS, by_id
from .adapters.base import (
    atomic_write,
    file_sha,
    install_skill_tree,
    parse_config,
    backup_once,
    tree_hash,
)

EXIT_READY, EXIT_FAIL, EXIT_USAGE = 0, 1, 2
_FIELDS = ("backup", "harness", "item", "kind", "path", "sha256_after")
# Child processes get this set only. Paid-provider variables stay in the parent.
_NPX_ENV_ALLOW = frozenset(
    {
        "PATH",
        "HOME",
        "TMPDIR",
        "TEMP",
        "TMP",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
        "npm_config_cache",
        "NPM_CONFIG_CACHE",
        "LANG",
    }
)


def _root(args) -> Path:
    return registry.root(getattr(args, "root", None))


def _flag_list(args, name: str) -> list[str]:
    raw = getattr(args, name, None) or []
    return [str(x) for x in raw]


def _emit(args, payload: dict, lines: list[str]) -> None:
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for line in lines:
            print(line)


def _needs_confirmation(args) -> int:
    _emit(
        args,
        {"status": "needs_confirmation", "plan": [], "doctor": []},
        ["needs_confirmation"],
    )
    return EXIT_FAIL


def ledger_path() -> Path:
    env = os.environ.get("XDG_STATE_HOME")
    base = Path(env).expanduser() if env else Path.home() / ".local" / "state"
    return base / "pfy" / "installed.json"


def load_ledger() -> tuple[list[dict], str | None]:
    path = ledger_path()
    if not path.exists():
        return [], None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [], "malformed %s (%s)\nnext: fix the ledger, then re-run" % (path, exc)
    if isinstance(data, dict):
        recs = data.get("records") or []
    elif isinstance(data, list):
        recs = data
    else:
        return [], "malformed %s\nnext: fix the ledger, then re-run" % path
    if not isinstance(recs, list):
        return [], "malformed %s\nnext: fix the ledger, then re-run" % path
    return [r for r in recs if isinstance(r, dict)], None


def save_ledger(records: list[dict]) -> None:
    path = ledger_path()
    payload = {"records": records}
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if path.is_file() and path.read_bytes() == data:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, data)


def _canon(rec: dict) -> dict:
    return {k: str(rec.get(k) or "") for k in _FIELDS}


def _find(records: list[dict], rec: dict) -> int | None:
    key = (rec["harness"], rec["item"], rec["path"], rec["kind"])
    for i, old in enumerate(records):
        if (str(old.get("harness") or ""), str(old.get("item") or ""), str(old.get("path") or ""), str(old.get("kind") or "")) == key:
            return i
    return None


def _upsert(records: list[dict], rec: dict) -> bool:
    """Insert or replace. Return True when the ledger content changes.

    Skill rows are keyed by item + path. Codex and OpenCode share
    ~/.agents/skills, so the second harness updates the first row.
    """
    body = _canon(rec)
    if body["kind"] == "skill":
        for i, old in enumerate(records):
            if (
                str(old.get("kind") or "") == "skill"
                and str(old.get("item") or "") == body["item"]
                and str(old.get("path") or "") == body["path"]
            ):
                body["harness"] = str(old.get("harness") or body["harness"])
                if _canon(old) == body:
                    return False
                records[i] = body
                return True
    idx = _find(records, body)
    if idx is None:
        records.append(body)
        return True
    if _canon(records[idx]) == body:
        return False
    records[idx] = body
    return True


def _lookup_backup(records: list[dict], rec: dict) -> str:
    idx = _find(records, rec)
    if idx is None:
        return ""
    return str(records[idx].get("backup") or "")


def _has_delegate(records: list[dict], harness: str, item: str) -> bool:
    for rec in records:
        if rec.get("kind") == "delegate" and rec.get("harness") == harness and rec.get("item") == item:
            return True
    return False


def _items(root: Path) -> list[dict]:
    return [t for t in registry.toolset_rows(root) if isinstance(t, dict) and t.get("id")]


def _by_item(items: list[dict], iid: str) -> dict | None:
    for row in items:
        if row.get("id") == iid:
            return row
    return None


def _dedupe(seq: list[str]) -> list[str]:
    out: list[str] = []
    for x in seq:
        if x not in out:
            out.append(x)
    return out


def _explicit(args) -> bool:
    return bool(_flag_list(args, "harness") or _flag_list(args, "preset") or _flag_list(args, "item") or getattr(args, "all_detected", False))


def _select(args, root: Path, records: list[dict]) -> tuple[list[str], list[dict], str | None]:
    """Return (harness ids in CLI order, item rows, error)."""
    items = _items(root)
    harnesses = _dedupe(_flag_list(args, "harness"))
    chosen: list[dict] = []
    seen: set[str] = set()

    def add_item(row: dict | None, iid: str) -> str | None:
        if row is None:
            return "unknown item %s\nnext: pick an id from data/toolsets.json" % iid
        if str(row.get("id")) not in seen:
            seen.add(str(row.get("id")))
            chosen.append(row)
        return None

    if not _explicit(args):
        pairs: list[tuple[str, str]] = []
        for rec in records:
            pair = (str(rec.get("harness") or ""), str(rec.get("item") or ""))
            if pair[0] and pair[1] and pair not in pairs:
                pairs.append(pair)
        h_out: list[str] = []
        for hid, iid in pairs:
            err = add_item(_by_item(items, iid), iid)
            if err:
                return [], [], err
            if hid not in h_out:
                h_out.append(hid)
        return h_out, chosen, None

    for preset in _flag_list(args, "preset"):
        matched = [row for row in items if preset in (row.get("presets") or [])]
        if not matched:
            return [], [], "no catalog items for preset %s\nnext: add v2 presets to data/toolsets.json" % preset
        for row in matched:
            err = add_item(row, str(row.get("id")))
            if err:
                return [], [], err
    for iid in _flag_list(args, "item"):
        err = add_item(_by_item(items, iid), iid)
        if err:
            return [], [], err
    if getattr(args, "all_detected", False):
        for adapter in ADAPTERS:
            if adapter.detect().found and adapter.id not in harnesses:
                harnesses.append(adapter.id)
        if not _flag_list(args, "preset") and not _flag_list(args, "item"):
            for row in items:
                if "core" in (row.get("presets") or []):
                    err = add_item(row, str(row.get("id")))
                    if err:
                        return [], [], err
    for hid in harnesses:
        if by_id(hid) is None:
            return [], [], "unknown harness %s\nnext: use grok, claude-code, codex, or opencode" % hid
    return harnesses, chosen, None


def _skill_src(root: Path, skill: dict) -> Path:
    raw = str(skill.get("from") or "")
    path = Path(raw)
    if path.is_absolute():
        return path
    return root / raw


def _native_parts(item: dict) -> tuple[list[dict], list[dict], str | None]:
    """Skills and mcp entries a native item writes. Delegate items return empty."""
    strategy = str((item.get("install") or {}).get("strategy") or "")
    if strategy == "delegate":
        return [], [], None
    provides = item.get("provides") or {}
    skills = []
    for row in provides.get("skills") or []:
        if isinstance(row, dict) and row.get("name") and row.get("from"):
            skills.append(row)
    mcp = []
    for row in provides.get("mcp") or []:
        if isinstance(row, dict) and row.get("name") and row.get("command"):
            mcp.append(row)
    kind = str(item.get("kind") or "")
    if strategy == "native" and kind == "mcp" and not mcp:
        return [], [], "item %s has no provides.mcp\nnext: add a native mcp entry" % item.get("id")
    if strategy == "native" and kind in ("bundle", "skill") and not skills and not mcp:
        return [], [], "item %s has no skills to copy\nnext: add provides.skills" % item.get("id")
    if strategy not in ("native", "delegate", ""):
        return [], [], "item %s has unknown install strategy\nnext: use native or delegate" % item.get("id")
    return skills, mcp, None


def _clients_for(item: dict, harnesses: list[str]) -> tuple[list[str], str | None]:
    delegate = ((item.get("install") or {}).get("delegate") or {})
    cmap = delegate.get("client_map") or {}
    flag = str(delegate.get("client_flag") or "--client")
    clients = []
    for hid in harnesses:
        if hid not in cmap:
            return [], "no delegate client for %s\nnext: add it to install.delegate.client_map" % hid
        clients.append(str(cmap[hid]))
    return clients, None if clients else "no harnesses for delegate %s\nnext: pass --harness" % item.get("id")


def _expand_cmd(cmd: list[str], flag: str, clients: list[str], insert: bool) -> list[str]:
    out: list[str] = []
    did = False
    for tok in cmd:
        out.append(str(tok))
        if insert and tok == "setup" and not did:
            for client in clients:
                out.append(flag)
                out.append(client)
            did = True
    if insert and not did:
        raise ValueError("delegate cmd has no setup token")
    return out


def _npx_env() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if key in _NPX_ENV_ALLOW}


def _parse_json_obj(text: str) -> dict | None:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _delegate_failed(code: int, receipt: dict | None) -> bool:
    if code != 0:
        return True
    status = str((receipt or {}).get("status") or "")
    return status in ("needs_human", "needs_confirmation", "failed")


def _run_npx(tail: list[str]) -> tuple[int, dict | None]:
    npx = shutil.which("npx")
    if not npx:
        print("npx not found\nnext: install Node.js so npx is on PATH", file=sys.stderr)
        return EXIT_FAIL, None
    proc = subprocess.run([npx, *tail], env=_npx_env(), capture_output=True, text=True)
    receipt = _parse_json_obj(proc.stdout)
    if _delegate_failed(proc.returncode, receipt):
        return EXIT_FAIL, receipt
    return EXIT_READY, receipt


def _merge_actions(base: list, extra) -> list:
    out = list(base)
    if not isinstance(extra, list):
        return out
    for item in extra:
        if item not in out:
            out.append(item)
    return out


def _file_action(op: dict) -> dict:
    return {
        "harness": op["harness"],
        "item": op["item"],
        "kind": op["kind"],
        "path": str(op["path"]),
    }


def _delegate_tail(item: dict, harnesses: list[str], insert: bool) -> tuple[list[str] | None, str | None]:
    install = item.get("install") or {}
    if insert:
        cmd = list((install.get("delegate") or {}).get("cmd") or [])
        flag = str((install.get("delegate") or {}).get("client_flag") or "--client")
        clients, err = _clients_for(item, harnesses)
        if err:
            return None, err
    else:
        cmd = list((install.get("uninstall") or {}).get("cmd") or [])
        flag = ""
        clients = []
        if not cmd:
            return None, "item %s has no uninstall cmd\nnext: set install.uninstall.cmd" % item.get("id")
    try:
        full = _expand_cmd(cmd, flag, clients, insert)
    except ValueError as exc:
        return None, "%s\nnext: fix install.delegate.cmd" % exc
    if not full:
        return None, "empty delegate command\nnext: fix the catalog item"
    if Path(full[0]).name == "npx":
        return full[1:], None
    return full, None


def _build_ops(root: Path, harnesses: list[str], items: list[dict]) -> tuple[list[dict], list[dict], str | None]:
    """File ops and delegate items. No disk writes."""
    file_ops: list[dict] = []
    delegates: list[dict] = []
    for item in items:
        strategy = str((item.get("install") or {}).get("strategy") or "")
        if strategy == "delegate" or str(item.get("kind") or "") == "external":
            if strategy == "delegate":
                delegates.append(item)
            continue
        skills, mcp, err = _native_parts(item)
        if err:
            return [], [], err
        iid = str(item.get("id"))
        for hid in harnesses:
            adapter = by_id(hid)
            if adapter is None:
                return [], [], "unknown harness %s\nnext: use grok, claude-code, codex, or opencode" % hid
            for skill in skills:
                src = _skill_src(root, skill)
                file_ops.extend(adapter.plan_skill(iid, skill, src))
            for entry in mcp:
                file_ops.extend(adapter.plan_mcp(iid, entry))
    for item in delegates:
        _tail, err = _delegate_tail(item, harnesses, True)
        if err:
            return [], [], err
    return file_ops, delegates, None


def _preflight(file_ops: list[dict], delegates: list[dict]) -> str | None:
    seen: set[str] = set()
    errors: list[str] = []
    for op in file_ops:
        if op["kind"] == "skill":
            src = op["src"]
            if not src.is_dir():
                errors.append("missing skill source %s\nnext: restore that directory, then re-run pfy setup" % src)
            continue
        adapter = by_id(op["harness"])
        path = op["path"]
        key = str(path)
        if key in seen or adapter is None:
            continue
        seen.add(key)
        err = parse_config(path, adapter.config_kind)
        if err:
            errors.append(err)
    if delegates and shutil.which("npx") is None:
        errors.append("npx not found\nnext: install Node.js so npx is on PATH")
    if errors:
        return "\n".join(errors)
    return None


def _apply_mcp(op: dict, records: list[dict]) -> tuple[bool, bool]:
    """Return (file_wrote, ledger_changed)."""
    adapter = by_id(op["harness"])
    path: Path = op["path"]
    existed = path.is_file()
    current = path.read_bytes() if existed else None
    new = adapter.render_config(current, op["item"], op["entry"])
    wrote = current is None or new != current
    backup = _lookup_backup(records, {"harness": op["harness"], "item": op["item"], "path": str(path), "kind": "mcp"})
    if wrote:
        if existed:
            backup = backup_once(path) or backup
        atomic_write(path, new)
        sha = file_sha(path)
    else:
        sha = file_sha(path) if path.is_file() else hashlib.sha256(new).hexdigest()
    changed = _upsert(
        records,
        {
            "harness": op["harness"],
            "item": op["item"],
            "path": str(path),
            "kind": "mcp",
            "sha256_after": sha,
            "backup": backup,
        },
    )
    return wrote, changed


def _apply_skill(op: dict, records: list[dict]) -> tuple[bool, bool]:
    wrote, sha = install_skill_tree(op["src"], op["path"])
    changed = _upsert(
        records,
        {
            "harness": op["harness"],
            "item": op["item"],
            "path": str(op["path"]),
            "kind": "skill",
            "sha256_after": sha,
            "backup": "",
        },
    )
    return wrote, changed


def _zero(args, plan: list[dict] | None = None) -> int:
    payload = {
        "status": "ok",
        "plan": plan or [],
        "plannedActions": plan or [],
        "appliedActions": [],
        "doctor": [],
        "message": "0 writes",
    }
    _emit(args, payload, ["0 writes"])
    return EXIT_READY


def _nothing_planned(args) -> int:
    payload = {
        "status": "planned",
        "plan": [],
        "plannedActions": [],
        "appliedActions": [],
        "doctor": [],
        "message": "nothing was planned",
    }
    _emit(args, payload, ["nothing was planned"])
    return EXIT_READY


def _public_plan(file_ops: list[dict], delegates: list[dict], harnesses: list[str]) -> list[dict]:
    plan = []
    for op in file_ops:
        plan.append(
            {
                "harness": op["harness"],
                "item": op["item"],
                "kind": op["kind"],
                "path": str(op["path"]),
            }
        )
    for item in delegates:
        tail, _err = _delegate_tail(item, harnesses, True)
        plan.append(
            {
                "harness": ",".join(harnesses),
                "item": str(item.get("id")),
                "kind": "delegate",
                "path": "npx " + " ".join(tail or []),
            }
        )
    return plan


def cmd_setup(args) -> int:
    from . import model_choice
    model_choice_code = model_choice.setup_from_args(args)
    if isinstance(model_choice_code, int) and model_choice_code != 0:
        return model_choice_code
    dry = bool(getattr(args, "dry_run", False))
    yes = bool(getattr(args, "yes", False))
    if not dry and not yes and not sys.stdin.isatty():
        return _needs_confirmation(args)
    if not dry and not yes and not _explicit(args):
        return _needs_confirmation(args)

    records, err = load_ledger()
    if err:
        _emit(args, {"status": "failed", "plan": [], "doctor": []}, [err])
        return EXIT_FAIL
    harnesses, items, err = _select(args, _root(args), records)
    if err:
        _emit(args, {"status": "failed", "plan": [], "doctor": []}, [err])
        return EXIT_USAGE if err.startswith("unknown") else EXIT_FAIL
    if not harnesses or not items:
        if harnesses and not items:
            return _nothing_planned(args)
        if dry:
            _emit(args, {"status": "planned", "plan": [], "plannedActions": [], "appliedActions": [], "doctor": [], "message": "0 writes"}, ["0 writes"])
            return EXIT_READY
        return _zero(args)

    file_ops, delegates, err = _build_ops(_root(args), harnesses, items)
    if err:
        _emit(args, {"status": "failed", "plan": [], "doctor": []}, [err])
        return EXIT_FAIL
    err = _preflight(file_ops, delegates)
    if err:
        _emit(args, {"status": "failed", "plan": [], "doctor": []}, [err])
        return EXIT_FAIL
    plan = _public_plan(file_ops, delegates, harnesses)
    if dry:
        lines = ["dry-run"]
        for row in plan:
            lines.append("%s %s %s %s" % (row["kind"], row["harness"], row["item"], row["path"]))
        _emit(args, {"status": "planned", "plan": plan, "doctor": []}, lines)
        return EXIT_READY

    writes = 0
    lines: list[str] = []
    written: list[dict] = []
    ledger_changed = False
    for op in file_ops:
        if op["kind"] == "skill":
            wrote, changed = _apply_skill(op, records)
        else:
            wrote, changed = _apply_mcp(op, records)
        if wrote:
            writes += 1
            lines.append("wrote %s %s %s" % (op["harness"], op["item"], op["path"]))
            written.append(_file_action(op))
        if changed:
            ledger_changed = True
            writes += 1

    for item in delegates:
        iid = str(item.get("id"))
        if all(_has_delegate(records, hid, iid) for hid in harnesses):
            continue
        tail, err = _delegate_tail(item, harnesses, True)
        if err or tail is None:
            _emit(args, {"status": "failed", "plan": plan, "plannedActions": plan, "appliedActions": written, "doctor": []}, [err or "delegate failed"])
            return EXIT_FAIL
        code, receipt = _run_npx(tail)
        if code != EXIT_READY:
            if ledger_changed:
                save_ledger(records)
            status = "needs_human" if receipt and str(receipt.get("status") or "") == "needs_human" else "failed"
            payload = {
                "status": status,
                "plan": plan,
                "plannedActions": _merge_actions(plan, (receipt or {}).get("plannedActions")),
                "appliedActions": _merge_actions(written, (receipt or {}).get("appliedActions")),
                "doctor": [],
                "writes": writes,
            }
            print("delegate command failed\nnext: re-run when npx exits 0", file=sys.stderr)
            _emit(args, payload, ["delegate command failed", "next: re-run when npx exits 0"])
            return EXIT_FAIL
        writes += 1
        lines.append("delegate %s" % iid)
        delegate_row = {
            "harness": ",".join(harnesses),
            "item": iid,
            "kind": "delegate",
            "path": "npx " + " ".join(tail),
        }
        written.append(delegate_row)
        cmap = ((item.get("install") or {}).get("delegate") or {}).get("client_map") or {}
        for hid in harnesses:
            client = str(cmap[hid])
            if _upsert(
                records,
                {
                    "harness": hid,
                    "item": iid,
                    "path": "delegate:%s" % hid,
                    "kind": "delegate",
                    "sha256_after": hashlib.sha256(client.encode("utf-8")).hexdigest(),
                    "backup": "",
                },
            ):
                ledger_changed = True
                writes += 1

    if ledger_changed:
        save_ledger(records)
    if writes == 0:
        lines.append("0 writes")
    payload = {
        "status": "ok",
        "plan": plan,
        "plannedActions": plan,
        "appliedActions": written,
        "doctor": [],
        "writes": writes,
    }
    if writes == 0:
        payload["message"] = "0 writes"
    _emit(args, payload, lines)
    return EXIT_READY


def _skill_harnesses(path: Path) -> list[str]:
    owners: list[str] = []
    for adapter in ADAPTERS:
        try:
            path.relative_to(adapter.skills_dir())
        except ValueError:
            continue
        owners.append(adapter.id)
    return owners


def _expand_shared_skills(records: list[dict]) -> list[dict]:
    """Show a shared skill dir under every harness that reads it.

    The ledger keeps one row. Doctor still reports codex and opencode.
    """
    out: list[dict] = []
    seen: set[tuple[str, str, str, str]] = set()
    for rec in records:
        clones = [rec]
        if str(rec.get("kind") or "") == "skill" and rec.get("path"):
            owners = _skill_harnesses(Path(str(rec.get("path"))))
            if owners:
                clones = []
                for hid in owners:
                    clone = dict(rec)
                    clone["harness"] = hid
                    clones.append(clone)
        for clone in clones:
            key = (
                str(clone.get("harness") or ""),
                str(clone.get("item") or ""),
                str(clone.get("path") or ""),
                str(clone.get("kind") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(clone)
    return out


def _group_states(records: list[dict]) -> list[dict]:
    records = _expand_shared_skills(records)
    order: list[tuple[str, str]] = []
    groups: dict[tuple[str, str], list[dict]] = {}
    for rec in records:
        key = (str(rec.get("harness") or ""), str(rec.get("item") or ""))
        if not key[0] or not key[1]:
            continue
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(rec)
    rows = []
    for key in order:
        recs = groups[key]
        kind = str(recs[0].get("kind") or "")
        if kind == "delegate" or all(str(r.get("kind")) == "delegate" for r in recs):
            state = "aligned"
        elif kind == "skill" or all(str(r.get("kind")) == "skill" for r in recs):
            state = _skill_state(recs)
        else:
            state = _mcp_state(recs)
        rows.append({"harness": key[0], "item": key[1], "state": state})
    return rows


def _skill_state(recs: list[dict]) -> str:
    missing = False
    drifted = False
    for rec in recs:
        path = Path(str(rec.get("path") or ""))
        if not path.is_dir():
            missing = True
            continue
        if tree_hash(path) != str(rec.get("sha256_after") or ""):
            drifted = True
    if missing:
        return "missing"
    if drifted:
        return "drifted"
    return "aligned"


def _mcp_state(recs: list[dict]) -> str:
    missing = False
    drifted = False
    for rec in recs:
        if str(rec.get("kind")) == "delegate":
            continue
        path = Path(str(rec.get("path") or ""))
        if not path.is_file():
            missing = True
            continue
        if file_sha(path) != str(rec.get("sha256_after") or ""):
            drifted = True
    if missing:
        return "missing"
    if drifted:
        return "drifted"
    return "aligned"


def cmd_doctor(args) -> int:
    records, err = load_ledger()
    if err:
        print(err, file=sys.stderr)
        return EXIT_FAIL
    want_h = set(_flag_list(args, "harness"))
    want_i = set(_flag_list(args, "item"))
    rows = []
    for row in _group_states(records):
        if want_h and row["harness"] not in want_h:
            continue
        if want_i and row["item"] not in want_i:
            continue
        rows.append(row)
    payload = {"status": "ok", "plan": [], "doctor": rows}
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2))
        return EXIT_READY
    print("status: ok")
    for row in rows:
        print("%s %s %s" % (row["harness"], row["item"], row["state"]))
    return EXIT_READY


def cmd_uninstall(args) -> int:
    yes = bool(getattr(args, "yes", False))
    dry = bool(getattr(args, "dry_run", False))
    if not yes:
        return _needs_confirmation(args)
    records, err = load_ledger()
    if err:
        _emit(args, {"status": "failed", "plan": [], "doctor": []}, [err])
        return EXIT_FAIL
    if dry:
        plan = [
            {
                "harness": str(r.get("harness") or ""),
                "item": str(r.get("item") or ""),
                "kind": str(r.get("kind") or ""),
                "path": str(r.get("path") or ""),
            }
            for r in records
        ]
        lines = ["dry-run"] + ["%s %s %s" % (p["kind"], p["harness"], p["path"]) for p in plan]
        _emit(args, {"status": "planned", "plan": plan, "doctor": []}, lines)
        return EXIT_READY
    if not records:
        return _zero(args)

    kept: list[dict] = []
    delegate_ids: list[str] = []
    warnings: list[str] = []
    for rec in records:
        if rec.get("kind") == "delegate":
            iid = str(rec.get("item") or "")
            if iid and iid not in delegate_ids:
                delegate_ids.append(iid)
            continue
        adapter = by_id(str(rec.get("harness") or ""))
        status = adapter.remove(rec) if adapter is not None else "skip"
        if status == "warn":
            warnings.append(str(rec.get("path") or rec.get("harness")))
            kept.append(_canon(rec))
        elif status == "skip":
            kept.append(_canon(rec))
    lines = []
    for path in warnings:
        lines.append("warn: %s sha256 mismatch; left in place" % path)

    root = _root(args)
    items = _items(root)
    for iid in delegate_ids:
        item = _by_item(items, iid)
        if item is None:
            lines.append("warn: missing catalog item %s; skipped delegate uninstall" % iid)
            for rec in records:
                if rec.get("kind") == "delegate" and rec.get("item") == iid:
                    kept.append(_canon(rec))
            continue
        tail, err = _delegate_tail(item, [], False)
        if err or tail is None:
            _emit(args, {"status": "failed", "plan": [], "doctor": []}, [err or "delegate failed"])
            return EXIT_FAIL
        code, _receipt = _run_npx(tail)
        if code != EXIT_READY:
            print("delegate command failed\nnext: re-run when npx exits 0", file=sys.stderr)
            for rec in records:
                if rec.get("kind") == "delegate" and rec.get("item") == iid:
                    kept.append(_canon(rec))
            save_ledger(kept)
            return EXIT_FAIL
        lines.append("delegate uninstall %s" % iid)
    save_ledger(kept)
    if not lines:
        lines.append("uninstalled")
    _emit(args, {"status": "ok", "plan": [], "doctor": [], "warnings": warnings}, lines)
    return EXIT_READY
