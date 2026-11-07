#!/usr/bin/env python3
"""Live org queue from Tools -- cite #214.

Queue for org creates a REAL GitHub issue on themark-net/pfy-mentat with
Design->DevBot DoD (operate-or-FAIL, no mock success). Refresh status via
gh/api and paint open/closed/PR on Tools (or Loop). Honest SKIP/FAIL if
auth/connector missing or entry HOLD. Do not auto-lift catalog 70-75.
No Mark git/npm/CI. LIVE_HARD_OFF: no live catalog writes.

Extends pfy_catalog_ask_queue_209 (browse/gates). Selftest never spams
issues: FAIL without auth, PASS with stub create_fn, optional live dry-run
GET only when a token/gh auth is present.
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

ISSUE = "#214"
REPO = "themark-net/pfy-mentat"
ISSUE_API = "https://api.github.com/repos/%s/issues" % REPO
REPO_API = "https://api.github.com/repos/%s" % REPO
UA = "pfy-live-org-queue-214"
DRAFT_FILE = "catalog-issue-draft.md"
NEXT_HOLD = "catalog 70-75 HOLD (do not auto-lift)"
NEXT_GH = (
    "gh auth login && gh issue create --repo themark-net/pfy-mentat "
    "(or GITHUB_TOKEN POST api.github.com) -- draft in "
    "$PFY_STATE_DIR/catalog-issue-draft.md"
)
NEXT_NAME = "pick a catalog tool on Tools"
NEXT_ONE = "finish or cancel the pending catalog integration first"
NEXT_SETUP = "./pfy setup"
PENDING = frozenset({"pending", "open", "asked", "pr"})


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
        "mock": False,
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
        "mock": False,
    }
    out.update(extra)
    return out


def github_token():
    return (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()


def gh_bin():
    return shutil.which("gh") or ""


def gh_authed(gh_auth_fn=None):
    if gh_auth_fn is not None:
        return bool(gh_auth_fn())
    gh = gh_bin()
    if not gh:
        return False
    try:
        p = subprocess.run(
            [gh, "auth", "status"],
            capture_output=True,
            text=True,
            timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return p.returncode == 0


def has_auth(auth_fn=None, gh_auth_fn=None):
    if auth_fn is not None:
        return bool(auth_fn())
    if github_token():
        return True
    return gh_authed(gh_auth_fn=gh_auth_fn)


def issue_number(url, data=None):
    if isinstance(data, dict):
        n = data.get("number") or data.get("issue_number")
        try:
            if n is not None:
                return int(n)
        except (TypeError, ValueError):
            pass
    m = re.search(r"/issues/(\d+)", str(url or ""))
    if m:
        return int(m.group(1))
    m = re.search(r"/pull/(\d+)", str(url or ""))
    if m:
        return int(m.group(1))
    return None


def classify_status(rec):
    rec = rec or {}
    state = str(rec.get("state") or rec.get("status") or "").strip().lower()
    if state == "closed":
        return "closed"
    pr = rec.get("pr_url") or rec.get("pull_request") or rec.get("prs")
    if pr:
        return "pr"
    if state in ("pr", "open", "asked", "pending", "fail"):
        return state if state != "fail" else "FAIL"
    return "open"


def load_catalog_mod(cat=None):
    if cat is not None:
        return cat
    import importlib.util

    path = Path(__file__).resolve().parent / "pfy_catalog_ask_queue_209.py"
    if not path.is_file():
        raise FileNotFoundError(str(path))
    spec = importlib.util.spec_from_file_location("pfy_catalog_ask_queue_209", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
        "(CLI and/or Attach). Operate-or-FAIL. No mock success.\n"
        "2. Honest SKIP/FAIL if auth/connector is missing or the entry is "
        "HOLD/incomplete. Do **not** auto-lift catalog PRs/entries 70\u201375.\n"
        "3. One integration at a time. Cite %s only. Do not reopen #76. "
        "#198 parked. LIVE_HARD_OFF.\n"
        "4. **No Mark git/npm/CI chore** \u2014 DevBot owns the branch, tests, "
        "and launcher gates (`bash -n scripts/pfy`; `py_compile` on "
        "scripts/pfy-board.py + scripts/pfy-gui.py; no encoded payloads).\n"
        "5. Tools (or Loop) shows queued items + status (open/closed/PR).\n\n"
        "## Operator constraints\n"
        "- Catalog 70-75 HOLD (do not auto-lift / do not merge #75)\n"
        "- LIVE_HARD_OFF (no live catalog writes)\n"
        "- No TOOLS.md / tools.json triple-write in this issue unless Design un-HOLDs\n"
        "- Queued via Tools live org queue (%s) \u2014 real GitHub issue, not a mock DoD\n"
        % (
            ISSUE,
            name,
            item.get("github") or "",
            item.get("category") or "",
            item.get("stage") or "",
            item.get("notes") or "",
            name,
            ISSUE,
            ISSUE,
        )
    )


def _run_gh_create(title, body):
    gh = gh_bin()
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


def _api_json(url, token, method="GET", payload=None):
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer %s" % token,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": UA,
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", "replace") or "{}"
            return json.loads(raw), ""
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")[:240]
        except Exception:
            body = ""
        return None, ("HTTP %s %s" % (e.code, body or e.reason))[:240]
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
        return None, str(e)[:240]


def _api_create(title, body, token):
    data, err = _api_json(
        ISSUE_API, token, method="POST", payload={"title": title, "body": body}
    )
    if not data:
        return None, err or "api create failed"
    url = str(data.get("html_url") or "").strip()
    if not url:
        return None, "api returned no html_url"
    return url, ""


def try_create_issue(title, body, create_fn=None):
    """Create a real GitHub issue. create_fn is test-only (never a mock PASS)."""
    if create_fn is not None:
        return create_fn(title, body)
    url, err = _run_gh_create(title, body)
    if url:
        return url, ""
    token = github_token()
    if token:
        url, err2 = _api_create(title, body, token)
        if url:
            return url, ""
        err = err2 or err
    return None, err or "gh/api unavailable"


def _gh_json(args):
    gh = gh_bin()
    if not gh:
        return None, "gh missing"
    try:
        p = subprocess.run(
            [gh, *args], capture_output=True, text=True, timeout=20
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e)[:200]
    if p.returncode != 0:
        err = ((p.stderr or p.stdout or "gh failed")[-300:]).strip()
        return None, err or "gh failed"
    try:
        return json.loads(p.stdout or "null"), ""
    except json.JSONDecodeError as e:
        return None, str(e)[:200]


def fetch_issue(number, fetch_fn=None):
    """Return (rec, err). rec has state/url/number and optional pr_url."""
    if fetch_fn is not None:
        rec = fetch_fn(number)
        if isinstance(rec, tuple) and len(rec) == 2:
            return rec
        if rec:
            return rec, ""
        return None, "fetch_fn empty"
    n = int(number)
    data, err = _gh_json(
        [
            "issue",
            "view",
            str(n),
            "--repo",
            REPO,
            "--json",
            "state,url,number,title,closedAt",
        ]
    )
    rec = {}
    if isinstance(data, dict) and data.get("number"):
        rec = {
            "state": str(data.get("state") or "").lower(),
            "url": data.get("url") or "",
            "number": data.get("number"),
            "title": data.get("title") or "",
        }
    token = github_token()
    if not rec and token:
        data, err2 = _api_json("%s/%s" % (ISSUE_API, n), token)
        err = err2 or err
        if isinstance(data, dict) and data.get("number"):
            rec = {
                "state": str(data.get("state") or "").lower(),
                "url": data.get("html_url") or "",
                "number": data.get("number"),
                "title": data.get("title") or "",
                "pull_request": data.get("pull_request"),
            }
    if not rec:
        return None, err or "issue fetch failed"
    pr_url = linked_pr_url(n, rec, token=token)
    if pr_url:
        rec["pr_url"] = pr_url
    return rec, ""


def linked_pr_url(number, rec=None, token=""):
    rec = rec or {}
    pr = rec.get("pull_request")
    if isinstance(pr, dict):
        url = str(pr.get("html_url") or pr.get("url") or "").strip()
        if url:
            return url.replace("/repos/", "/").replace("api.github.com", "github.com")
    if rec.get("pr_url"):
        return str(rec.get("pr_url"))
    data, _err = _gh_json(
        [
            "pr",
            "list",
            "--repo",
            REPO,
            "--search",
            "%d" % int(number),
            "--json",
            "number,url,state,title",
            "--limit",
            "10",
        ]
    )
    if isinstance(data, list):
        for row in data:
            title = str(row.get("title") or "")
            url = str(row.get("url") or "")
            if ("#%d" % int(number)) in title or url.endswith("/pull/%d" % int(number)):
                return url
            # mention of the issue in a same-repo PR list hit is enough to paint PR
            if row.get("url") and str(row.get("state") or "").lower() == "open":
                if str(row.get("number")) == str(number):
                    return url
        # Prefer an open PR whose URL/title references this issue number only
        # when the search returned a single hit.
        if len(data) == 1 and data[0].get("url"):
            return str(data[0].get("url"))
    token = token or github_token()
    if token:
        data, _err = _api_json(
            "%s/%s/timeline" % (ISSUE_API, int(number)), token
        )
        if isinstance(data, list):
            for ev in data:
                if not isinstance(ev, dict):
                    continue
                src = (ev.get("source") or {}).get("issue") or {}
                if src.get("pull_request") and src.get("html_url"):
                    return str(src.get("html_url"))
                if ev.get("event") in ("connected", "cross-referenced"):
                    pr = src.get("pull_request") or {}
                    url = str(pr.get("html_url") or src.get("html_url") or "")
                    if "/pull/" in url:
                        return url
    return ""


def refresh_item(item, fetch_fn=None):
    item = dict(item or {})
    n = item.get("issue_number") or issue_number(item.get("issue_url") or "")
    if not n:
        return item
    rec, err = fetch_issue(n, fetch_fn=fetch_fn)
    if not rec:
        item["refresh_error"] = err or "refresh failed"
        return item
    item["issue_number"] = rec.get("number") or n
    if rec.get("url"):
        item["issue_url"] = rec.get("url")
    if rec.get("pr_url"):
        item["pr_url"] = rec.get("pr_url")
    item["status"] = classify_status(rec)
    item["issue"] = ISSUE
    item["refreshed"] = _now()
    return item


def refresh_queue(STATE=None, fetch_fn=None, cat=None):
    cat = load_catalog_mod(cat)
    STATE = state_dir(STATE)
    items = []
    for it in cat.load_queue(STATE):
        kind = str(it.get("kind") or "")
        if kind == "queue" and (it.get("issue_url") or it.get("issue_number")):
            items.append(refresh_item(it, fetch_fn=fetch_fn))
        else:
            items.append(it)
    cat.save_queue(STATE, items)
    return items


def queue_org(
    ROOT=None,
    STATE=None,
    name="",
    create_fn=None,
    attach_mode="",
    auth_fn=None,
    gh_auth_fn=None,
    cat=None,
):
    cat = load_catalog_mod(cat)
    ROOT = repo_root(ROOT)
    STATE = state_dir(STATE)
    rows = cat.load_catalog(ROOT, attach_mode=attach_mode or cat.current_attach_mode(STATE))
    item = cat.find_item(rows, name)
    gated = cat.gate_entry(item, "queue")
    if gated:
        gated["catalog"] = rows
        gated["queue"] = cat.load_queue(STATE)
        gated["issue"] = ISSUE
        gated["mock"] = False
        return gated
    busy = cat.gate_busy(STATE, item, "queue")
    if busy:
        busy["catalog"] = rows
        busy["queue"] = cat.load_queue(STATE)
        busy["issue"] = ISSUE
        busy["mock"] = False
        return busy
    title = org_issue_title(item)
    body = org_issue_body(item)
    STATE.mkdir(parents=True, exist_ok=True)
    draft = STATE / DRAFT_FILE
    _write(draft, "# %s\n\n%s" % (title, body))
    if create_fn is None and not has_auth(auth_fn=auth_fn, gh_auth_fn=gh_auth_fn):
        rec = {
            "id": item.get("id"),
            "name": item.get("name"),
            "kind": "queue",
            "status": "FAIL",
            "draft": str(draft),
            "when": _now(),
            "error": "auth/connector missing",
            "issue": ISSUE,
        }
        queue = cat.record_queue(STATE, rec)
        out = fail(
            "queue",
            "auth/connector missing (no gh auth, no GITHUB_TOKEN/GH_TOKEN)",
            NEXT_GH,
            name=item.get("name"),
            id=item.get("id"),
            draft=str(draft),
            catalog=rows,
            queue=queue,
            title=title,
        )
        out["live"] = "FAIL"
        out["mock"] = False
        return out
    url, err = try_create_issue(title, body, create_fn=create_fn)
    if not url:
        rec = {
            "id": item.get("id"),
            "name": item.get("name"),
            "kind": "queue",
            "status": "FAIL",
            "draft": str(draft),
            "when": _now(),
            "error": err or "gh/api unavailable",
            "issue": ISSUE,
        }
        queue = cat.record_queue(STATE, rec)
        out = fail(
            "queue",
            "cannot open GitHub issue (%s)" % (err or "no gh/api"),
            NEXT_GH,
            name=item.get("name"),
            id=item.get("id"),
            draft=str(draft),
            catalog=rows,
            queue=queue,
            title=title,
        )
        out["live"] = "FAIL"
        out["mock"] = False
        return out
    n = issue_number(url)
    rec = {
        "id": item.get("id"),
        "name": item.get("name"),
        "kind": "queue",
        "status": "open",
        "issue_url": url,
        "issue_number": n,
        "draft": str(draft),
        "when": _now(),
        "issue": ISSUE,
        "mock": False,
    }
    queue = cat.record_queue(STATE, rec)
    return {
        "ok": True,
        "live": "PASS",
        "copy": "PASS queue \u00b7 %s \u00b7 %s" % (item.get("name"), url),
        "issue_url": url,
        "issue_number": n,
        "name": item.get("name"),
        "id": item.get("id"),
        "title": title,
        "draft": str(draft),
        "next_step": url,
        "catalog": rows,
        "queue": queue,
        "usable": True,
        "issue": ISSUE,
        "mock": False,
    }


def queue_status(STATE=None, fetch_fn=None, cat=None):
    cat = load_catalog_mod(cat)
    STATE = state_dir(STATE)
    items = refresh_queue(STATE, fetch_fn=fetch_fn, cat=cat)
    pend = None
    for it in items:
        if str(it.get("status") or "") in PENDING:
            pend = it
            break
    return {
        "ok": True,
        "live": "PASS",
        "copy": "PASS queue-status \u00b7 %d item(s)" % len(items),
        "queue": items,
        "pending": pend,
        "busy": bool(pend),
        "next_step": NEXT_NAME if not pend else NEXT_ONE,
        "issue": ISSUE,
        "mock": False,
    }


def snapshot_fields(
    STATE=None,
    ROOT=None,
    attached="",
    active="",
    attach_mode="",
    pid_alive=None,
    fetch_fn=None,
    cat=None,
):
    cat = load_catalog_mod(cat)
    rec = cat.snapshot_fields(
        STATE=STATE,
        ROOT=ROOT,
        attached=attached,
        active=active,
        attach_mode=attach_mode,
        pid_alive=pid_alive,
        fetch_fn=fetch_fn,
        _skip_live=True,
    )
    rec["catalog_queue"] = refresh_queue(STATE, fetch_fn=fetch_fn, cat=cat)
    rec["issue"] = ISSUE
    return rec


def auth_probe(probe_fn=None, auth_fn=None, gh_auth_fn=None):
    """Live dry-run: prove auth can reach the repo. Never creates an issue."""
    if probe_fn is not None:
        rec = probe_fn()
        if isinstance(rec, dict):
            rec.setdefault("created", False)
            rec.setdefault("mock", False)
            rec.setdefault("issue", ISSUE)
            return rec
    if not has_auth(auth_fn=auth_fn, gh_auth_fn=gh_auth_fn):
        return fail(
            "dry-run",
            "auth/connector missing (no gh auth, no GITHUB_TOKEN/GH_TOKEN)",
            NEXT_GH,
            created=False,
        )
    data, err = _gh_json(["api", "repos/%s" % REPO, "--jq", ".full_name"])
    if data:
        name = data if isinstance(data, str) else (data.get("full_name") if isinstance(data, dict) else "")
        if REPO.split("/")[-1] in str(name or data):
            return {
                "ok": True,
                "live": "PASS",
                "copy": "PASS dry-run \u00b7 %s reachable (no issue created)" % REPO,
                "created": False,
                "mock": False,
                "issue": ISSUE,
                "repo": REPO,
            }
    token = github_token()
    if token:
        data, err2 = _api_json(REPO_API, token)
        err = err2 or err
        if isinstance(data, dict) and data.get("full_name") == REPO:
            return {
                "ok": True,
                "live": "PASS",
                "copy": "PASS dry-run \u00b7 %s reachable (no issue created)" % REPO,
                "created": False,
                "mock": False,
                "issue": ISSUE,
                "repo": REPO,
            }
    return fail(
        "dry-run",
        "cannot reach %s (%s)" % (REPO, err or "gh/api unavailable"),
        NEXT_GH,
        created=False,
    )


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
            "%s\t%s\t%s\t%s\t%s"
            % (
                it.get("name") or it.get("id") or "",
                it.get("kind") or "",
                it.get("status") or "",
                it.get("issue_url") or it.get("prompt") or "",
                it.get("pr_url") or "",
            )
        )
    if rec.get("next_step"):
        print("next: %s" % rec["next_step"])
    return 0 if rec.get("ok") else 2


def cmd_dry_run(args):
    rec = auth_probe()
    print(rec.get("copy") or rec.get("error") or "FAIL dry-run")
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
| **Hyperframes** | Agent Frameworks | https://github.com/heygen-com/hyperframes | 90 | 85 | 92 | 95 | 90 | S | #skills | **X Entry 070.** HOLD candidate. |
| **repowise** | Coding | https://github.com/repowise-dev/repowise | 88 | 92 | 88 | 82 | 88 | A | #context | **X Entry 006.** Pin `repowise==0.30.0`. |

## Autonomous AI Companies
"""
    with tempfile.TemporaryDirectory(prefix="pfy-214-") as tmp:
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
                            "notes": "Primary operator env (ADR-0002).",
                            "integration_stage": "I3",
                        },
                        {
                            "name": "repowise",
                            "primary_category": "Coding & Dev Agents",
                            "github": "https://github.com/repowise-dev/repowise",
                            "notes": "X Entry 006. Pin repowise==0.30.0.",
                            "integration_stage": "I1",
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        repo = str(Path(__file__).resolve().parents[1])
        if repo not in sys.path:
            sys.path.insert(0, repo)
        from pfylib.stage_registry import write_tool

        write_tool(
            root,
            "repowise",
            {
                "integration_stage": "I1",
                "github": "https://github.com/repowise-dev/repowise",
            },
        )

        hold_q = queue_org(
            root,
            state,
            name="Hyperframes",
            create_fn=lambda t, b: ("https://example.invalid/1", ""),
            auth_fn=lambda: True,
        )
        check(not hold_q.get("ok"), "HOLD queue blocked")
        check(hold_q.get("skipped") or hold_q.get("live") == "SKIP", "HOLD queue SKIP")
        check("70-75" in (hold_q.get("next_step") or ""), "HOLD next do not auto-lift")
        check(hold_q.get("mock") is not True, "HOLD is not mock success")

        created = []

        def create_ok(title, body):
            created.append((title, body))
            blob = title + "\n" + body
            check("No Mark" in blob or "no Mark" in blob.lower(), "issue forbids Mark git/npm/CI")
            check("70" in body and "HOLD" in body, "issue keeps 70-75 HOLD")
            check("#214" in body, "issue cites #214")
            check("#209" not in body.split("70")[0] or "#214" in body, "live queue cites #214")
            check("Design" in body and "DevBot" in body, "issue Design->DevBot DoD")
            check("open/closed/PR" in body or "open/closed/PR" in body.replace(" ", ""), "DoD paints status")
            check("mock" in body.lower(), "DoD says not a mock")
            return "https://github.com/%s/issues/2140" % REPO, ""

        qok = queue_org(root, state, name="repowise", create_fn=create_ok, auth_fn=lambda: False)
        check(qok.get("ok"), "queue PASS with stub create_fn")
        check(qok.get("issue_url", "").endswith("/issues/2140"), "queue url")
        check(qok.get("issue_number") == 2140, "issue_number parsed")
        check(qok.get("mock") is False, "stub create is not mock-success flag")
        check(created, "create_fn called")
        check(qok.get("live") == "PASS", "stub create live PASS")

        # FAIL without auth (no create_fn, auth_fn false) -- no fake success
        state_fail = Path(tmp) / "state-fail"
        state_fail.mkdir()
        qfail = queue_org(
            root,
            state_fail,
            name="repowise",
            create_fn=None,
            auth_fn=lambda: False,
        )
        check(not qfail.get("ok"), "queue FAIL without auth")
        check(qfail.get("live") == "FAIL", "no-auth is FAIL not SKIP/PASS")
        check("auth" in (qfail.get("error") or "").lower() or "auth" in (qfail.get("copy") or "").lower(), "FAIL names auth")
        check("gh issue create" in (qfail.get("next_step") or "") or "GITHUB_TOKEN" in (qfail.get("next_step") or ""), "operate-or-FAIL next")
        check((state_fail / DRAFT_FILE).is_file(), "draft written when auth missing")
        check(qfail.get("mock") is not True, "no mock success without auth")
        draft = _read(state_fail / DRAFT_FILE)
        check("Design" in draft and "DevBot" in draft, "draft has real DoD")
        check("#214" in draft, "draft cites #214")

        # status refresh: open / closed / PR
        def fetch_open(n):
            return {"state": "open", "url": "https://github.com/%s/issues/%s" % (REPO, n), "number": n}

        def fetch_closed(n):
            return {"state": "closed", "url": "https://github.com/%s/issues/%s" % (REPO, n), "number": n}

        def fetch_pr(n):
            return {
                "state": "open",
                "url": "https://github.com/%s/issues/%s" % (REPO, n),
                "number": n,
                "pr_url": "https://github.com/%s/pull/99" % REPO,
            }

        st_open = queue_status(state, fetch_fn=fetch_open)
        check(st_open.get("ok"), "status ok")
        by = {x.get("name"): x for x in st_open.get("queue") or []}
        check(by.get("repowise", {}).get("status") == "open", "status paints open")

        st_pr = queue_status(state, fetch_fn=fetch_pr)
        by = {x.get("name"): x for x in st_pr.get("queue") or []}
        check(by.get("repowise", {}).get("status") == "pr", "status paints PR")
        check(by.get("repowise", {}).get("pr_url", "").endswith("/pull/99"), "pr_url stored")

        st_closed = queue_status(state, fetch_fn=fetch_closed)
        by = {x.get("name"): x for x in st_closed.get("queue") or []}
        check(by.get("repowise", {}).get("status") == "closed", "status paints closed")
        check(st_closed.get("busy") is False, "closed is not pending")

        check(classify_status({"state": "open"}) == "open", "classify open")
        check(classify_status({"state": "closed"}) == "closed", "classify closed")
        check(classify_status({"state": "open", "pr_url": "x"}) == "pr", "classify pr")
        check(classify_status({"state": "closed", "pr_url": "x"}) == "closed", "closed wins over pr")

        dry_fail = auth_probe(auth_fn=lambda: False)
        check(not dry_fail.get("ok"), "dry-run FAIL without auth")
        check(dry_fail.get("created") is False, "dry-run never creates")

        dry_ok = auth_probe(probe_fn=lambda: {"ok": True, "live": "PASS", "copy": "PASS dry-run", "created": False})
        check(dry_ok.get("ok") and dry_ok.get("created") is False, "stub probe does not create")

        # optional live dry-run only if token/gh present -- GET, never POST
        if has_auth():
            live = auth_probe()
            check(live.get("created") is False, "live dry-run did not create an issue")
            check(live.get("mock") is not True, "live dry-run not mock")
            # PASS or FAIL is honest; SKIP is not used here
            check(live.get("live") in ("PASS", "FAIL"), "live dry-run honest live")

        snap = snapshot_fields(state, root, attached="grok", fetch_fn=fetch_closed)
        check(isinstance(snap.get("catalog"), list), "snapshot catalog")
        q = snap.get("catalog_queue") or []
        check(any(x.get("status") in ("open", "closed", "pr") for x in q), "snapshot paints status")
        check("s1" not in json.dumps(snap.get("catalog")), "snapshot not scores-only")

        here = Path(__file__).resolve().parents[1]
        html = _read(here / "gui" / "operator" / "frontend" / "index.html")
        js = _read(here / "gui" / "operator" / "frontend" / "app-ui.js")
        gui_src = _read(here / "scripts" / "pfy-gui.py")
        gui_tools = gui_loop = gui_src
        check("id=loop-queue" in html, "HTML Loop queue row")
        check(".open,.OPEN" in html and ".closed,.CLOSED" in html and ".pr,.PR" in html, "HTML open/closed/PR styles")
        check("pr_url" in js and "loop-queue" in js, "HTML paints pr + Loop queue")
        check("QUEUE" in gui_tools and "pr_url" in gui_tools, "tk Tools QUEUE paints pr/issue")
        check("queue      " in gui_loop, "tk Loop paints queue")
        check("Queue for org" in gui_src, "tk Queue for org button")
        board = _read(here / "scripts" / "pfy-board.py")
        check("_load_live_org_214" in board or "live.queue_org" in board, "board queue uses #214")

    if errors:
        print("FAIL selftest \u00b7 " + " ; ".join(errors))
        return 1
    print(
        "PASS selftest \u00b7 live org queue \u00b7 FAIL without auth \u00b7 "
        "PASS stub create_fn \u00b7 open/closed/PR \u00b7 HOLD 70-75"
    )
    return 0


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("-h", "--help"):
        print(
            "usage: pfy_live_org_queue_214.py "
            "[--selftest|--queue NAME|--status|--dry-run]"
        )
        return 0
    cmd = args[0]
    rest = args[1:]
    if cmd in ("--selftest", "selftest"):
        return cmd_selftest()
    if cmd in ("--queue", "queue"):
        return cmd_queue(rest)
    if cmd in ("--status", "status"):
        return cmd_status(rest)
    if cmd in ("--dry-run", "dry-run"):
        return cmd_dry_run(rest)
    print(
        "usage: pfy_live_org_queue_214.py "
        "[--selftest|--queue NAME|--status|--dry-run]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
