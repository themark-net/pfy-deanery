#!/usr/bin/env python3
"""Catalog browse + ask-TUI / queue-org -- cite #209.

Tools panel: usable catalog subset (name/category/github/stage/notes/status),
not a scores-only dump. Ask attached TUI to implement for next launch writes
a concrete prompt/artifact (paste or auto-handoff) -- operate-or-FAIL.
Queue for org opens a GitHub issue with Design->DevBot DoD (no Mark
git/npm/CI). Honest SKIP/FAIL if no harness attached or entry HOLD/incomplete.
Do not auto-lift catalog 70-75. One integration at a time. Show queued status.

LIVE_HARD_OFF: no live catalog writes / no TOOLS.md triple-write.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ISSUE = "#209"
REPO = "themark-net/pfy-mentat"
ISSUE_API = "https://api.github.com/repos/%s/issues" % REPO
HOLD_ENTRIES = frozenset(range(70, 76))
SIDECAR_OK = ("grok", "opencode", "hermes", "codex", "claude", "claude-code")
STUB_ALWAYS = frozenset({"continue", "agent-cage"})
QUEUE_FILE = "catalog-queue.json"
PROMPT_FILE = "catalog-ask-prompt.md"
HANDOFF_FILE = "catalog-ask-handoff.md"
ASK_JSON = "catalog-ask.json"
DRAFT_FILE = "catalog-issue-draft.md"
NEXT_ATTACH = "Attach grok | opencode | hermes | codex | claude"
NEXT_HOLD = "catalog 70-75 HOLD (do not auto-lift)"
NEXT_INCOMPLETE = "pick a complete catalog entry (not I0 / skip / scores-only)"
NEXT_ONE = "finish or cancel the pending catalog integration first"
NEXT_GH = (
    "gh issue create --repo themark-net/pfy-mentat "
    "(or GITHUB_TOKEN POST api.github.com) -- draft in "
    "$PFY_STATE_DIR/catalog-issue-draft.md"
)
NEXT_SETUP = "./pfy setup"
NEXT_NAME = "pick a catalog tool on Tools"
IN_MODE_NAMES = frozenset(
    {
        "grok cli bootstrap",
        "project-process bootstrap",
        "agent-cage (pnnl)",
        "agent-cage",
        "codebase-memory-mcp",
        "write-guard-mcp",
        "eval-harness (pfy)",
        "hermes agent (feedback loops)",
        "finn loop / eval-loop / 8-exits patterns",
        "ponytail (skills pack)",
        "karpathy-guidelines",
        "mattpocock/skills",
        "marketing-skills (marketing-council)",
    }
)
INCOMPLETE_HINTS = (
    "skip install",
    "not integrated",
    "reference only",
    "docs-only",
    "raw-port-blocked",
    "no smoke",
    "initial scores only",
    "catalog hold",
    "not cataloged",
    "i1 stay",
)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_state(STATE):
    return Path(STATE)


def _read(path):
    path = Path(path)
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def _write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((text or "").rstrip() + "\n", encoding="utf-8")


def _slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s or "tool"


def fail(kind, reason, next_step, **extra):
    copy = "FAIL %s -- %s \u00b7 %s" % (kind, reason, next_step)
    out = {
        "ok": False,
        "live": "FAIL",
        "copy": copy,
        "error": reason,
        "next_step": next_step,
        "usable": False,
        "issue": ISSUE,
    }
    out.update(extra)
    return out


def skip(kind, reason, next_step, **extra):
    copy = "SKIP %s -- %s \u00b7 %s" % (kind, reason, next_step)
    out = {
        "ok": False,
        "live": "SKIP",
        "copy": copy,
        "error": reason,
        "next_step": next_step,
        "usable": False,
        "skipped": True,
        "issue": ISSUE,
    }
    out.update(extra)
    return out


def repo_root(ROOT=None):
    if ROOT:
        return Path(ROOT)
    env = os.environ.get("PFY_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[1]


def state_dir(STATE=None):
    if STATE:
        return Path(STATE)
    env = os.environ.get("PFY_STATE_DIR")
    if env:
        return Path(env)
    return Path.home() / ".pfy-mentat"


def x_entry_num(text):
    m = re.search(r"X Entry\s+(\d{1,3})", text or "", re.I)
    if not m:
        m = re.search(r"Entry\s+(\d{3})\b", text or "", re.I)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def is_hold_entry(item):
    n = item.get("x_entry")
    if n in HOLD_ENTRIES:
        return True
    blob = " ".join(
        str(item.get(k) or "") for k in ("notes", "name", "id", "github")
    )
    n2 = x_entry_num(blob)
    if n2 in HOLD_ENTRIES:
        return True
    return False


def is_incomplete(item):
    stage = str(item.get("stage") or "").strip().upper()
    if stage in ("I0", "0"):
        return True
    if not str(item.get("github") or "").strip():
        return True
    notes = (item.get("notes") or "").lower()
    return any(h in notes for h in INCOMPLETE_HINTS)


def in_attach_mode(item, attach_mode=""):
    name = (item.get("name") or "").strip().lower()
    if name in IN_MODE_NAMES:
        return True
    mode = (attach_mode or "").strip().lower()
    if mode == "code-graph" and "codebase-memory" in name:
        return True
    if mode == "orchestration" and "agent-loops" in name:
        return True
    return False


def item_status(item, attach_mode=""):
    if is_hold_entry(item):
        return "HOLD"
    if is_incomplete(item):
        return "incomplete"
    if in_attach_mode(item, attach_mode):
        return "in-mode"
    return "ready"


def _strip_md(s):
    s = (s or "").strip()
    s = s.replace("**", "")
    s = re.sub(r"\[([^\]]+)\]\([^)]+\]", r"\1", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    return s.strip()


def parse_tools_md(text):
    """Active Catalog rows without score columns. Cite #209."""
    items = []
    in_table = False
    for line in (text or "").splitlines():
        if line.startswith("## Active Catalog"):
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        if not in_table or not line.startswith("|"):
            continue
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) < 8:
            continue
        head = cols[0].lower()
        if head in ("tool", "") or set(head) <= set("-: "):
            continue
        raw_name = cols[0].strip()
        bold = re.match(r"\*\*([^*]+)\*\*(.*)", raw_name)
        short = bold.group(1).strip() if bold else ""
        name = _strip_md(raw_name)
        if not name:
            continue
        category = _strip_md(cols[1] if len(cols) > 1 else "")
        github = _strip_md(cols[2] if len(cols) > 2 else "")
        tags = _strip_md(cols[-2] if len(cols) >= 2 else "")
        notes = _strip_md(cols[-1] if cols else "")
        if github.lower().startswith("this repo"):
            github = "https://github.com/%s" % REPO
        item = {
            "id": _slug(name),
            "name": name,
            "short": short,
            "category": category,
            "github": github,
            "notes": notes,
            "tags": tags,
            "stage": "",
            "x_entry": x_entry_num(notes) or x_entry_num(name),
        }
        items.append(item)
    return items


def load_tools_json(ROOT):
    path = Path(ROOT) / "data" / "tools.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    out = []
    for t in data.get("tools") or []:
        if not isinstance(t, dict):
            continue
        name = str(t.get("name") or "").strip()
        if not name:
            continue
        notes = str(t.get("notes") or "").strip()
        out.append(
            {
                "id": _slug(name),
                "name": name,
                "category": str(t.get("primary_category") or "").strip(),
                "github": str(t.get("github") or "").strip(),
                "notes": notes,
                "tags": " ".join(t.get("tags") or [])
                if isinstance(t.get("tags"), list)
                else str(t.get("tags") or ""),
                "stage": str(t.get("integration_stage") or "").strip(),
                "x_entry": x_entry_num(notes),
                "bootstrap_path": str(t.get("bootstrap_path") or "").strip(),
            }
        )
    return out


def _stage_registry():
    repo = str(Path(__file__).resolve().parents[1])
    if repo not in sys.path:
        sys.path.insert(0, repo)
    from pfylib import stage_registry
    return stage_registry


def load_integration_stages(ROOT):
    root = Path(ROOT)
    if not (root / "data" / "stages").is_dir():
        return {}
    try:
        data = _stage_registry().load_stages(root)
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    tools = data.get("tools") or {}
    out = {}
    if isinstance(tools, dict):
        for name, rec in tools.items():
            if not isinstance(rec, dict):
                continue
            out[_slug(name)] = {
                "stage": str(rec.get("integration_stage") or "").strip(),
                "github": str(rec.get("github") or "").strip(),
                "notes_doc": str(rec.get("notes_doc") or "").strip(),
            }
    return out


def merge_catalog(md_items, json_items, stages):
    by_id = {}
    for src in (md_items, json_items):
        for item in src:
            key = item.get("id") or _slug(item.get("name"))
            cur = by_id.get(key) or {}
            merged = dict(cur)
            for k, v in item.items():
                if v in (None, "", [], {}):
                    continue
                if k == "notes" and cur.get("notes") and v not in cur.get("notes"):
                    merged["notes"] = (cur.get("notes") + " " + v).strip()
                elif not merged.get(k):
                    merged[k] = v
            by_id[key] = merged
    # A parenthetical display name ("adr-tools (optional)") does not slug to
    # the card. Alias the bold name so the card still attaches. The alias is
    # not a second row.
    aliases = {}
    for item in by_id.values():
        short = (item.get("short") or "").strip()
        if not short:
            continue
        sk = _slug(short)
        if sk and sk not in by_id and sk not in aliases:
            aliases[sk] = item
    for key, extra in stages.items():
        cur = by_id.get(key)
        if cur is None:
            cur = aliases.get(key)
        if cur is None:
            continue
        # The stage card is the lifecycle. tools.json can lag (I2 vs I3).
        if extra.get("stage"):
            cur["stage"] = extra["stage"]
        if extra.get("github") and not cur.get("github"):
            cur["github"] = extra["github"]
        if extra.get("notes_doc") and extra["notes_doc"] not in (cur.get("notes") or ""):
            cur["notes"] = ((cur.get("notes") or "") + " " + extra["notes_doc"]).strip()
    return list(by_id.values())


def usable_fields(item, attach_mode=""):
    """Operator browse row: no S1-S4 / overall. Cite #209."""
    status = item_status(item, attach_mode)
    notes = (item.get("notes") or "").strip()
    if len(notes) > 280:
        notes = notes[:277] + "..."
    return {
        "id": item.get("id") or _slug(item.get("name")),
        "name": item.get("name") or "",
        "category": item.get("category") or "",
        "github": item.get("github") or "",
        "stage": item.get("stage") or "",
        "notes": notes,
        "status": status,
        "hold": status == "HOLD",
        "incomplete": status == "incomplete",
        "in_mode": status == "in-mode",
        "x_entry": item.get("x_entry"),
    }


def load_catalog(ROOT, attach_mode=""):
    ROOT = Path(ROOT)
    md = parse_tools_md(_read(ROOT / "TOOLS.md"))
    js = load_tools_json(ROOT)
    stages = load_integration_stages(ROOT)
    merged = merge_catalog(md, js, stages)
    rows = [usable_fields(it, attach_mode) for it in merged]
    rows.sort(key=lambda r: ((r.get("name") or "").lower(), r.get("id") or ""))
    return rows


def find_item(rows, name):
    want = (name or "").strip()
    if not want:
        return None
    slug = _slug(want)
    low = want.lower()
    for r in rows:
        if (r.get("id") or "") == slug:
            return r
        if (r.get("name") or "").lower() == low:
            return r
    hits = [
        r
        for r in rows
        if slug in (r.get("id") or "") or low in (r.get("name") or "").lower()
    ]
    if len(hits) == 1:
        return hits[0]
    return None


def load_queue(STATE):
    path = Path(STATE) / QUEUE_FILE
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return data["items"]
    return []


def save_queue(STATE, items):
    STATE = Path(STATE)
    STATE.mkdir(parents=True, exist_ok=True)
    _write(STATE / QUEUE_FILE, json.dumps({"items": items, "issue": ISSUE}, indent=2))


def pending_item(STATE):
    for it in load_queue(STATE):
        if str(it.get("status") or "") in ("pending", "open", "asked", "pr"):
            return it
    return None


def record_queue(STATE, item):
    items = load_queue(STATE)
    key = item.get("id") or item.get("name")
    found = False
    out = []
    for it in items:
        if (it.get("id") or it.get("name")) == key:
            merged = dict(it)
            merged.update(item)
            out.append(merged)
            found = True
        else:
            out.append(it)
    if not found:
        out.append(item)
    save_queue(STATE, out)
    return out


def attached_harness(STATE, pid_alive=None, active=""):
    STATE = Path(STATE)
    hid = (active or _read(STATE / "active-harness")).strip()
    if hid in STUB_ALWAYS:
        return ""
    if hid not in SIDECAR_OK:
        hid = ""
        for cand in SIDECAR_OK:
            path = STATE / ("sidecar-%s.pid" % cand)
            if not path.is_file():
                continue
            try:
                pid = int(_read(path) or "0")
            except ValueError:
                continue
            if pid_alive is None:
                if _pid_alive(pid):
                    return cand
            elif pid_alive(pid):
                return cand
        return ""
    path = STATE / ("sidecar-%s.pid" % hid)
    if path.is_file():
        try:
            pid = int(_read(path) or "0")
        except ValueError:
            pid = 0
        if pid_alive is None:
            alive = _pid_alive(pid)
        else:
            alive = pid_alive(pid)
        if not alive:
            # recorded active harness still counts as attached if session_reach exists
            reach = _read(STATE / "session-reach") or _read(STATE / "session_reach")
            if not reach:
                return hid
            if str(reach).upper() in ("FAIL", "SKIP", ""):
                return hid
        return hid
    return hid


def _pid_alive(pid):
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def gate_entry(item, kind):
    if not item:
        return fail(kind, "unknown catalog tool", NEXT_NAME, catalog=[], name="")
    if item.get("hold"):
        return skip(
            kind,
            "catalog entry HOLD (70-75)",
            NEXT_HOLD,
            name=item.get("name"),
            id=item.get("id"),
            status="HOLD",
        )
    if item.get("incomplete"):
        return skip(
            kind,
            "catalog entry incomplete",
            NEXT_INCOMPLETE,
            name=item.get("name"),
            id=item.get("id"),
            status="incomplete",
        )
    return None


def gate_busy(STATE, item, kind):
    pend = pending_item(STATE)
    if not pend:
        return None
    same = (pend.get("id") or "") == (item.get("id") or "") or (
        pend.get("name") or ""
    ) == (item.get("name") or "")
    if same:
        return None
    return fail(
        kind,
        "one integration at a time (%s is %s)"
        % (pend.get("name") or pend.get("id") or "pending", pend.get("status") or "pending"),
        NEXT_ONE,
        pending=pend,
        name=item.get("name"),
    )


def implement_prompt(item, attached):
    name = item.get("name") or "catalog tool"
    github = item.get("github") or ""
    stage = item.get("stage") or "(unset)"
    notes = item.get("notes") or ""
    hid = attached or "attached TUI"
    return (
        "# Catalog implement-on-next-launch (%s)\n\n"
        "Harness: **%s**\n"
        "Tool: **%s**\n"
        "GitHub: %s\n"
        "Integration stage: %s\n"
        "Notes: %s\n\n"
        "## Do this on the next launch of this attached TUI\n\n"
        "Implement **%s** onto this operator stack for the next launch. "
        "One integration at a time. Cite %s only.\n\n"
        "### Design -> DevBot DoD\n"
        "1. Wire a developer-usable path (CLI and/or Attach child env). "
        "Operate-or-FAIL. No scores-only dump.\n"
        "2. Honest SKIP/FAIL if the entry is HOLD/incomplete. "
        "Do not auto-lift catalog 70-75.\n"
        "3. Do not reopen #76. #198 parked. LIVE_HARD_OFF "
        "(no live catalog writes).\n"
        "4. No Mark git/npm/CI chore. Prefer helper + existing `./pfy` / board.\n"
        "5. Leave queued status visible. `bash -n scripts/pfy` PASS "
        "if the launcher changes.\n\n"
        "Paste this prompt into the attached TUI, or rely on auto-handoff "
        "(`PFY_CATALOG_ASK_PROMPT`) at next Attach.\n"
        % (ISSUE, hid, name, github, stage, notes, name, ISSUE)
    )


def implement_handoff(item, attached, prompt_path):
    return (
        "# Catalog ask handoff %s\n\n"
        "Attached: %s\n"
        "Tool: %s\n"
        "Prompt: %s\n"
        "Next: Attach again (or paste the prompt). One integration.\n"
        % (ISSUE, attached, item.get("name") or "", prompt_path)
    )


def org_issue_title(item):
    return "Catalog implement: %s (Design\u2192DevBot)" % (item.get("name") or "tool")


def org_issue_body(item):
    name = item.get("name") or "catalog tool"
    return (
        "## Catalog queue (%s)\n\n"
        "Tool: **%s**\n"
        "GitHub: %s\n"
        "Category: %s\n"
        "Stage: %s\n"
        "Notes: %s\n\n"
        "## Design \u2192 DevBot DoD\n"
        "1. Implement a developer-usable path for **%s** on the operator stack "
        "(CLI and/or Attach). Operate-or-FAIL.\n"
        "2. Honest SKIP/FAIL if no harness is attached or the entry is "
        "HOLD/incomplete. Do **not** auto-lift catalog PRs/entries 70\u201375.\n"
        "3. One integration at a time. Cite %s only. Do not reopen #76. "
        "#198 parked. LIVE_HARD_OFF.\n"
        "4. **No Mark git/npm/CI chore** \u2014 DevBot owns the branch, tests, "
        "and launcher gates (`bash -n scripts/pfy`; no encoded payloads).\n"
        "5. Show queued items/status on Tools. No Env nav tab.\n\n"
        "## Operator constraints\n"
        "- Catalog 70-75 HOLD\n"
        "- LIVE_HARD_OFF (no live catalog writes)\n"
        "- No TOOLS.md / tools.json triple-write in this issue unless Design un-HOLDs\n"
        % (
            ISSUE,
            name,
            item.get("github") or "",
            item.get("category") or "",
            item.get("stage") or "",
            item.get("notes") or "",
            name,
            ISSUE,
        )
    )


def browse(ROOT=None, STATE=None, attach_mode=""):
    ROOT = repo_root(ROOT)
    STATE = state_dir(STATE)
    rows = load_catalog(ROOT, attach_mode=attach_mode or current_attach_mode(STATE))
    if not rows:
        return fail(
            "catalog",
            "no usable catalog subset",
            NEXT_SETUP,
            catalog=[],
            queue=load_queue(STATE),
        )
    # Scores must not be the browse payload.
    for r in rows:
        for banned in ("s1", "s2", "s3", "s4", "overall", "scores"):
            r.pop(banned, None)
    return {
        "ok": True,
        "live": "PASS",
        "copy": "PASS catalog \u00b7 %d tools" % len(rows),
        "catalog": rows,
        "queue": load_queue(STATE),
        "next_step": NEXT_NAME,
        "usable": True,
        "issue": ISSUE,
    }


def current_attach_mode(STATE):
    raw = _read(Path(STATE) / "attach-mode")
    return raw.strip() if raw else "bare"


def ask_implement(
    ROOT=None,
    STATE=None,
    name="",
    attached="",
    pid_alive=None,
    active="",
    attach_mode="",
):
    ROOT = repo_root(ROOT)
    STATE = state_dir(STATE)
    rows = load_catalog(ROOT, attach_mode=attach_mode or current_attach_mode(STATE))
    item = find_item(rows, name)
    gated = gate_entry(item, "ask")
    if gated:
        gated["catalog"] = rows
        gated["queue"] = load_queue(STATE)
        return gated
    busy = gate_busy(STATE, item, "ask")
    if busy:
        busy["catalog"] = rows
        busy["queue"] = load_queue(STATE)
        return busy
    hid = (attached or attached_harness(STATE, pid_alive=pid_alive, active=active) or "").strip()
    if not hid:
        return fail(
            "ask",
            "no harness attached",
            NEXT_ATTACH,
            catalog=rows,
            queue=load_queue(STATE),
            name=item.get("name"),
        )
    if hid in STUB_ALWAYS:
        return fail(
            "ask",
            "%s is not a startable TUI" % hid,
            NEXT_ATTACH,
            catalog=rows,
            queue=load_queue(STATE),
            name=item.get("name"),
        )
    prompt = implement_prompt(item, hid)
    STATE.mkdir(parents=True, exist_ok=True)
    prompt_path = STATE / PROMPT_FILE
    handoff_path = STATE / HANDOFF_FILE
    try:
        _write(prompt_path, prompt)
        _write(handoff_path, implement_handoff(item, hid, str(prompt_path)))
        _write(
            STATE / ASK_JSON,
            json.dumps(
                {
                    "name": item.get("name"),
                    "id": item.get("id"),
                    "attached": hid,
                    "prompt": str(prompt_path),
                    "when": _now(),
                    "issue": ISSUE,
                },
                indent=2,
            ),
        )
    except OSError as e:
        return fail(
            "ask",
            "cannot write prompt artifact (%s)" % str(e)[:160],
            NEXT_SETUP,
            catalog=rows,
            name=item.get("name"),
        )
    if not prompt_path.is_file() or not _read(prompt_path):
        return fail(
            "ask",
            "prompt artifact missing after write",
            NEXT_SETUP,
            catalog=rows,
            name=item.get("name"),
        )
    rec = {
        "id": item.get("id"),
        "name": item.get("name"),
        "kind": "ask",
        "status": "asked",
        "attached": hid,
        "prompt": str(prompt_path),
        "handoff": str(handoff_path),
        "when": _now(),
        "issue": ISSUE,
    }
    queue = record_queue(STATE, rec)
    return {
        "ok": True,
        "live": "PASS",
        "copy": "PASS ask \u00b7 %s \u00b7 paste or auto-handoff %s"
        % (item.get("name"), prompt_path),
        "prompt": prompt,
        "prompt_path": str(prompt_path),
        "handoff_path": str(handoff_path),
        "attached": hid,
        "name": item.get("name"),
        "id": item.get("id"),
        "next_step": "paste into %s or Attach again (PFY_CATALOG_ASK_PROMPT)" % hid,
        "catalog": rows,
        "queue": queue,
        "usable": True,
        "issue": ISSUE,
    }


def _run_gh_create(title, body):
    gh = shutil.which("gh")
    if not gh:
        return None, "gh missing"
    try:
        p = subprocess.run(
            [
                gh,
                "issue",
                "create",
                "--repo",
                REPO,
                "--title",
                title,
                "--body",
                body,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e)[:200]
    url = (p.stdout or "").strip().splitlines()
    url = url[-1].strip() if url else ""
    if p.returncode != 0 or "github.com" not in url:
        err = ((p.stderr or p.stdout or "gh failed")[-300:]).strip()
        return None, err or "gh failed"
    return url, ""


def _api_create(title, body, token):
    payload = json.dumps({"title": title, "body": body}).encode("utf-8")
    req = urllib.request.Request(
        ISSUE_API,
        data=payload,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer %s" % token,
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "pfy-catalog-ask-queue-209",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace") or "{}")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as e:
        return None, str(e)[:240]
    url = str(data.get("html_url") or "").strip()
    if not url:
        return None, "api returned no html_url"
    return url, ""


def try_create_issue(title, body, create_fn=None):
    if create_fn is not None:
        return create_fn(title, body)
    url, err = _run_gh_create(title, body)
    if url:
        return url, ""
    token = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    if token:
        url, err2 = _api_create(title, body, token)
        if url:
            return url, ""
        err = err2 or err
    return None, err or "gh/api unavailable"


def _load_live_214():
    """Live org queue (#214). Optional; queue still FAILs closed without it."""
    import importlib.util

    path = Path(__file__).resolve().parent / "pfy_live_org_queue_214.py"
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("pfy_live_org_queue_214", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def queue_org(
    ROOT=None,
    STATE=None,
    name="",
    create_fn=None,
    attach_mode="",
    auth_fn=None,
    gh_auth_fn=None,
):
    live = _load_live_214()
    if live is not None:
        return live.queue_org(
            ROOT=ROOT,
            STATE=STATE,
            name=name,
            create_fn=create_fn,
            attach_mode=attach_mode,
            auth_fn=auth_fn,
            gh_auth_fn=gh_auth_fn,
            cat=sys.modules[__name__],
        )
    ROOT = repo_root(ROOT)
    STATE = state_dir(STATE)
    rows = load_catalog(ROOT, attach_mode=attach_mode or current_attach_mode(STATE))
    item = find_item(rows, name)
    gated = gate_entry(item, "queue")
    if gated:
        gated["catalog"] = rows
        gated["queue"] = load_queue(STATE)
        return gated
    busy = gate_busy(STATE, item, "queue")
    if busy:
        busy["catalog"] = rows
        busy["queue"] = load_queue(STATE)
        return busy
    title = org_issue_title(item)
    body = org_issue_body(item)
    STATE.mkdir(parents=True, exist_ok=True)
    _write(STATE / DRAFT_FILE, "# %s\n\n%s" % (title, body))
    url, err = try_create_issue(title, body, create_fn=create_fn)
    if not url:
        rec = {
            "id": item.get("id"),
            "name": item.get("name"),
            "kind": "queue",
            "status": "FAIL",
            "draft": str(STATE / DRAFT_FILE),
            "when": _now(),
            "error": err or "gh/api unavailable",
            "issue": ISSUE,
        }
        queue = record_queue(STATE, rec)
        out = fail(
            "queue",
            "cannot open GitHub issue (%s)" % (err or "no gh/api"),
            NEXT_GH,
            name=item.get("name"),
            id=item.get("id"),
            draft=str(STATE / DRAFT_FILE),
            catalog=rows,
            queue=queue,
            title=title,
        )
        out["live"] = "FAIL"
        return out
    rec = {
        "id": item.get("id"),
        "name": item.get("name"),
        "kind": "queue",
        "status": "open",
        "issue_url": url,
        "draft": str(STATE / DRAFT_FILE),
        "when": _now(),
        "issue": ISSUE,
    }
    queue = record_queue(STATE, rec)
    return {
        "ok": True,
        "live": "PASS",
        "copy": "PASS queue \u00b7 %s \u00b7 %s" % (item.get("name"), url),
        "issue_url": url,
        "name": item.get("name"),
        "id": item.get("id"),
        "title": title,
        "draft": str(STATE / DRAFT_FILE),
        "next_step": url,
        "catalog": rows,
        "queue": queue,
        "usable": True,
        "issue": ISSUE,
    }


def queue_status(STATE=None, fetch_fn=None):
    live = _load_live_214()
    if live is not None:
        return live.queue_status(
            STATE=STATE, fetch_fn=fetch_fn, cat=sys.modules[__name__]
        )
    STATE = state_dir(STATE)
    items = load_queue(STATE)
    pend = pending_item(STATE)
    return {
        "ok": True,
        "live": "PASS",
        "copy": "PASS queue-status \u00b7 %d item(s)" % len(items),
        "queue": items,
        "pending": pend,
        "busy": bool(pend),
        "next_step": NEXT_NAME if not pend else NEXT_ONE,
        "issue": ISSUE,
    }


def snapshot_fields(
    STATE=None,
    ROOT=None,
    attached="",
    active="",
    attach_mode="",
    pid_alive=None,
    fetch_fn=None,
    _skip_live=False,
):
    ROOT = repo_root(ROOT)
    STATE = state_dir(STATE)
    mode = attach_mode or current_attach_mode(STATE)
    rec = browse(ROOT, STATE, attach_mode=mode)
    hid = attached or attached_harness(STATE, pid_alive=pid_alive, active=active)
    q = rec.get("queue") or load_queue(STATE)
    if not _skip_live:
        live = _load_live_214()
        if live is not None:
            q = live.refresh_queue(
                STATE, fetch_fn=fetch_fn, cat=sys.modules[__name__]
            )
    pend = pending_item(STATE)
    prompt = _read(STATE / PROMPT_FILE)
    return {
        "catalog_ok": bool(rec.get("ok")),
        "catalog": rec.get("catalog") or [],
        "catalog_copy": rec.get("copy") or "",
        "catalog_next": rec.get("next_step") or NEXT_NAME,
        "catalog_queue": q,
        "catalog_pending": pend or {},
        "catalog_busy": bool(pend),
        "catalog_prompt": prompt,
        "catalog_attached": hid or "",
        "catalog_hold": NEXT_HOLD,
    }


def apply_child_env(env, STATE=None):
    """Export ask prompt into Attach/start child env (next launch). Cite #209."""
    env = env if env is not None else {}
    STATE = state_dir(STATE)
    prompt = STATE / PROMPT_FILE
    handoff = STATE / HANDOFF_FILE
    if prompt.is_file():
        env["PFY_CATALOG_ASK_PROMPT"] = str(prompt)
    if handoff.is_file():
        env["PFY_CATALOG_ASK_HANDOFF"] = str(handoff)
    return env


def cmd_browse(args):
    rec = browse()
    rows = rec.get("catalog") or []
    print(rec.get("copy") or "")
    print("name\tstage\tstatus\tcategory\tgithub")
    for r in rows:
        print(
            "%s\t%s\t%s\t%s\t%s"
            % (
                r.get("name") or "",
                r.get("stage") or "-",
                r.get("status") or "",
                r.get("category") or "",
                r.get("github") or "",
            )
        )
    if rec.get("next_step"):
        print("next: %s" % rec["next_step"])
    return 0 if rec.get("ok") else 2


def cmd_ask(args):
    name = " ".join(args).strip()
    rec = ask_implement(name=name)
    print(rec.get("copy") or rec.get("error") or "FAIL ask")
    if rec.get("prompt_path"):
        print("prompt: %s" % rec["prompt_path"])
    if rec.get("next_step"):
        print("next: %s" % rec["next_step"])
    return 0 if rec.get("ok") else 2


def cmd_queue(args):
    name = " ".join(args).strip()
    rec = queue_org(name=name)
    print(rec.get("copy") or rec.get("error") or "FAIL queue")
    if rec.get("issue_url"):
        print("issue: %s" % rec["issue_url"])
    if rec.get("draft"):
        print("draft: %s" % rec["draft"])
    if rec.get("next_step"):
        print("next: %s" % rec["next_step"])
    return 0 if rec.get("ok") else 2


def cmd_status(args):
    rec = queue_status()
    print(rec.get("copy") or "")
    for it in rec.get("queue") or []:
        print(
            "%s\t%s\t%s\t%s"
            % (
                it.get("name") or it.get("id") or "",
                it.get("kind") or "",
                it.get("status") or "",
                it.get("issue_url") or it.get("prompt") or "",
            )
        )
    if rec.get("next_step"):
        print("next: %s" % rec["next_step"])
    return 0 if rec.get("ok") else 2


def cmd_selftest():
    import tempfile

    errors = []

    def check(cond, msg):
        if not cond:
            errors.append(msg)

    md = """
## Active Catalog

| Tool | Primary Cat | GitHub | S1 | S2 | S3 | S4 | Overall | Tier | Key Tags | Integration Notes / Grok CLI / MCP |
|------|-------------|--------|----|----|----|----|---------|------|----------|-------------------------------------|
| **Grok CLI bootstrap** | Pipeline | this repo (`bootstrap/grok-cli/`) | 95 | 90 | 98 | 90 | 94 | S | #grok-cli | **Primary operator env (ADR-0002).** |
| **kanbots** | Agent Frameworks | https://github.com/leodavinci1/kanbots | 85 | 70 | 90 | 78 | 81 | A | #kanban | **X Entry 078.** Stage 0 pass. Initial scores only; no smoke yet. |
| **Hyperframes** | Agent Frameworks | https://github.com/heygen-com/hyperframes | 90 | 85 | 92 | 95 | 90 | S | #skills | **X Entry 070.** HOLD candidate. |
| **Camofox Browser** | Tool Calling | https://github.com/jo-inc/camofox-browser | 88 | 82 | 90 | 88 | 87 | A | #browser | **X Entry 071.** |
| **Laguna S 2.1** | Inference | https://huggingface.co/poolside/Laguna-S-2.1 | 92 | 85 | 95 | 92 | 91 | S | #moe | **X Entry 073.** |
| **asm (agent-skill-manager)** | Agent Frameworks | https://github.com/luongnv89/asm | 90 | 88 | 95 | 90 | 91 | A | #skills | **X Entry 075.** |
| **repowise** | Coding | https://github.com/repowise-dev/repowise | 88 | 92 | 88 | 82 | 88 | A | #context | **X Entry 006.** Pin `repowise==0.30.0`. |

## Autonomous AI Companies
"""
    parsed = parse_tools_md(md)
    check(len(parsed) >= 6, "parse active catalog rows")
    names = [p["name"] for p in parsed]
    check("Grok CLI bootstrap" in names, "parse grok name")
    check("Hyperframes" in names, "parse hyperframes")
    check(all("s1" not in p and "scores" not in p for p in parsed), "md parse has no scores keys")

    with tempfile.TemporaryDirectory(prefix="pfy-209-") as tmp:
        root = Path(tmp) / "repo"
        state = Path(tmp) / "state"
        root.mkdir()
        state.mkdir()
        (root / "TOOLS.md").write_text(md, encoding="utf-8")
        (root / "data").mkdir()
        (root / "data" / "tools.json").write_text(
            json.dumps(
                {
                    "tools": [
                        {
                            "name": "Grok CLI bootstrap",
                            "primary_category": "Pipeline & CI/CD Components",
                            "github": "https://github.com/themark-net/pfy-mentat",
                            "scores": {"s1": 95, "overall": 94},
                            "tier": "S",
                            "notes": "Primary operator env (ADR-0002).",
                            "integration_stage": "I3",
                        },
                        {
                            "name": "kanbots",
                            "primary_category": "Agent Frameworks & Orchestration",
                            "github": "https://github.com/leodavinci1/kanbots",
                            "scores": {"s1": 85, "overall": 81},
                            "tier": "A",
                            "notes": "X Entry 078. Initial scores only; no smoke yet.",
                            "integration_stage": "I1",
                        },
                        {
                            "name": "repowise",
                            "primary_category": "Coding & Dev Agents",
                            "github": "https://github.com/repowise-dev/repowise",
                            "scores": {"s1": 88, "overall": 88},
                            "tier": "A",
                            "notes": "X Entry 006. Pin repowise==0.30.0.",
                            "integration_stage": "I1",
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        _stage_registry().write_tool(
            root,
            "repowise",
            {
                "integration_stage": "I1",
                "github": "https://github.com/repowise-dev/repowise",
            },
        )

        rec = browse(root, state)
        check(rec.get("ok"), "browse ok")
        rows = rec.get("catalog") or []
        check(len(rows) >= 6, "browse usable subset size")
        check(all("s1" not in r and "overall" not in r and "scores" not in r for r in rows), "browse not scores-only")
        check(all("name" in r and "github" in r and "notes" in r and "status" in r for r in rows), "browse usable fields")
        by = {r["name"]: r for r in rows}
        check(by["Hyperframes"]["status"] == "HOLD", "entry 070 HOLD")
        check(by["Camofox Browser"]["status"] == "HOLD", "entry 071 HOLD")
        check(by["Laguna S 2.1"]["status"] == "HOLD", "entry 073 HOLD")
        check(by["asm (agent-skill-manager)"]["status"] == "HOLD", "entry 075 HOLD")
        check(by["kanbots"]["status"] == "incomplete", "kanbots incomplete (no smoke)")
        check(by["Grok CLI bootstrap"]["status"] == "in-mode", "grok already in mode")
        check(by["repowise"]["status"] == "ready", "repowise ready")

        no_att = ask_implement(root, state, name="repowise", attached="")
        check(not no_att.get("ok"), "ask without harness FAIL")
        check("Attach" in (no_att.get("next_step") or ""), "ask next attach")
        check((state / PROMPT_FILE).is_file() is False, "no prompt without harness")

        hold = ask_implement(root, state, name="Hyperframes", attached="grok")
        check(not hold.get("ok"), "HOLD ask not ok")
        check(hold.get("skipped") or hold.get("live") == "SKIP", "HOLD is SKIP")
        check("70-75" in (hold.get("next_step") or ""), "HOLD next do not auto-lift")
        check(not (state / PROMPT_FILE).is_file(), "HOLD does not write prompt")

        inc = ask_implement(root, state, name="kanbots", attached="grok")
        check(not inc.get("ok"), "incomplete ask not ok")
        check(inc.get("skipped") or inc.get("live") == "SKIP", "incomplete SKIP")

        (state / "active-harness").write_text("grok\n", encoding="utf-8")
        (state / "sidecar-grok.pid").write_text("%d\n" % os.getpid(), encoding="utf-8")
        ok_ask = ask_implement(
            root, state, name="repowise", attached="grok", pid_alive=lambda p: True
        )
        check(ok_ask.get("ok"), "ask PASS when attached")
        check((state / PROMPT_FILE).is_file(), "prompt artifact")
        prompt = _read(state / PROMPT_FILE)
        check("repowise" in prompt.lower(), "prompt names tool")
        check("Design" in prompt and "DevBot" in prompt, "prompt has Design->DevBot DoD")
        check("#209" in prompt, "prompt cites #209")
        check("#76" in prompt, "prompt says do not reopen #76")
        env = apply_child_env({}, STATE=state)
        check(env.get("PFY_CATALOG_ASK_PROMPT"), "auto-handoff env")

        busy = ask_implement(
            root, state, name="Grok CLI bootstrap", attached="grok", pid_alive=lambda p: True
        )
        # grok is in-mode but complete; one-at-a-time should block a *different* pending
        # Grok CLI is in-mode, not HOLD. pending is repowise asked.
        check(not busy.get("ok"), "one at a time blocks other tool")
        check("one integration" in (busy.get("error") or "").lower() or "one integration" in (busy.get("next_step") or "").lower(), "one-at-a-time next")

        hold_q = queue_org(root, state, name="Hyperframes", create_fn=lambda t, b: ("https://example.invalid/1", ""))
        check(not hold_q.get("ok"), "HOLD queue blocked")
        check(hold_q.get("skipped") or hold_q.get("live") == "SKIP", "HOLD queue SKIP")

        # same tool may refresh ask; queue of same pending name is allowed
        created = []

        def create_ok(title, body):
            created.append((title, body))
            check("No Mark" in body or "No Mark" in title or "no Mark" in body.lower() or "No Mark git" in body, "issue forbids Mark git/npm/CI")
            check("70" in body and "HOLD" in body, "issue keeps 70-75 HOLD")
            check("#214" in body, "issue cites #214")
            check("Design" in body, "issue Design DoD")
            return "https://github.com/%s/issues/999" % REPO, ""

        qok = queue_org(root, state, name="repowise", create_fn=create_ok)
        check(qok.get("ok"), "queue PASS with create_fn")
        check(qok.get("issue_url", "").endswith("/issues/999"), "queue url")
        check(created, "create_fn called")

        st = queue_status(state)
        check(st.get("ok"), "status ok")
        check(any(x.get("name") == "repowise" for x in st.get("queue") or []), "status lists queued")
        check(st.get("busy") is True, "busy while open")

        # FAIL path when gh/api missing
        state2 = Path(tmp) / "state2"
        state2.mkdir()
        qfail = queue_org(
            root,
            state2,
            name="repowise",
            create_fn=lambda t, b: (None, "gh missing"),
        )
        check(not qfail.get("ok"), "queue FAIL without gh/api")
        check("catalog-issue-draft.md" in (qfail.get("draft") or ""), "draft path")
        check("gh issue create" in (qfail.get("next_step") or ""), "operate-or-FAIL gh path")
        check((state2 / DRAFT_FILE).is_file(), "draft written")

        snap = snapshot_fields(state, root, attached="grok")
        check(isinstance(snap.get("catalog"), list), "snapshot catalog")
        check(snap.get("catalog_ok") is True, "snapshot ok")
        check("s1" not in json.dumps(snap.get("catalog")), "snapshot not scores-only")

    if errors:
        print("FAIL selftest \u00b7 " + " ; ".join(errors))
        return 1
    print("PASS selftest \u00b7 catalog browse/ask/queue \u00b7 HOLD 70-75 \u00b7 one-at-a-time")
    return 0


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(
            "usage: pfy_catalog_ask_queue_209.py "
            "[--selftest|--browse|--ask NAME|--queue NAME|--status]"
        )
        return 0
    cmd = args[0]
    rest = args[1:]
    if cmd in ("--selftest", "selftest"):
        return cmd_selftest()
    if cmd in ("--browse", "browse", "list"):
        return cmd_browse(rest)
    if cmd in ("--ask", "ask"):
        return cmd_ask(rest)
    if cmd in ("--queue", "queue"):
        return cmd_queue(rest)
    if cmd in ("--status", "status"):
        return cmd_status(rest)
    print(
        "usage: pfy_catalog_ask_queue_209.py "
        "[--selftest|--browse|--ask NAME|--queue NAME|--status]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
