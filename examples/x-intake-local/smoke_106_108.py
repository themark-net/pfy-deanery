#!/usr/bin/env python3
"""Operate-or-FAIL smokes for X intake Entries 106-108 (Rulora, HAR, cass-memory). Stdlib only.

Usage: python3 examples/x-intake-local/smoke_106_108.py --entry rulora|har|cassmemory

Same contract and receipts as smoke.py next to it (whose helpers it reuses): exit 0 = PASS, 1 = the tool ran but
the check failed, 2 = can't run here (prereq missing; reason recorded). Writes pipelines/smoke/<entry>/latest.json.
Never installs or downloads anything; every scratch file goes to a fresh tempfile directory that is removed.
Tool subprocesses get a fresh temp HOME and an env with paid provider keys stripped. No smoke calls a model.
PFY_XINTAKE_TIMEOUT (float seconds, > 0) overrides the per-command tool timeouts (default 120s); Empty keeps the
default. Any other set value (abc, 0, -1, nan, inf) exits 2 before the entry runs.

  rulora      $RULORA_DIR (a dir holding node_modules/@rulora/core), then ~/DEVELOP/pfy-mentat/tmp/rulora
              (npm --prefix install of @rulora/core@0.1.0-alpha.4); plus Node 20+ from $RULORA_NODE,
              ~/DEVELOP/pfy-mentat/tmp/rulora/node/bin/node, or PATH. Runs the three Core controls with no model:
              OutputBoundary accepts a valid output and rejects a bad one at stage `core` and an unknown evidence
              id at stage `audit`; LoopControl (maxNoProgress 2) stays active while progress is made, goes to
              `human_handoff` after two no-progress attempts and then refuses more records (LOOP_CLOSED);
              CollectiveControl freezes candidates (later mutation does not leak in), refuses an invented id
              (UNKNOWN_CANDIDATE) and returns a frozen selection.
  har         $HAR_BIN, then ~/DEVELOP/pfy-mentat/tmp/har/node_modules/.bin/har (npm --prefix install of
              @osfactory/har@1.16.0), then PATH; plus Node 20+ from $HAR_NODE, ~/DEVELOP/pfy-mentat/tmp/har/node/
              bin/node, or PATH; and git. In a temp HOME: `har telemetry off` first, then on a throwaway git repo
              `har env init --profile cli` (no agents, no cursor rule, no commit gate), `env launch 1`,
              `env verify 1 --full --json` must pass with every stage passing, a broken `test` script in the
              session worktree must make verify fail on unit-tests, the main checkout must stay untouched, and
              `env teardown 1` must remove the worktree. FAILs if the launch work dir is not under the temp
              HOME, or if any agent hook file (~/.cursor/hooks.json, ~/.claude/settings.json,
              ~/.codex/hooks.json, ~/.har/otel-hooks) appears in the temp HOME with telemetry off.
  cassmemory  $CM_BIN, then ~/DEVELOP/pfy-mentat/tmp/cass-memory/cm, then PATH (`cm`). The v0.5.0
              cass-memory-linux-x64 release binary is pinned by sha256; $CM_SHA256 overrides the pin, and a
              mismatch exits 2 without exec. In a temp HOME with every LLM provider key and OLLAMA_BASE_URL
              stripped: `cm init`, add two rules, `cm context` must return the matching rule, three `--harmful`
              marks must deprecate it and drop it from context while the other rule stays listed, and
              `cm usage` must report 0 LLM spend. Never runs `cm doctor --fix` (model download), `cm hook`,
              `cm reflect` with a key, or `cm update`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from smoke import TMP, find_bin, node_version_env, pinned, run, scrub_env, timeout_reason, write

# cass-memory v0.5.0 release asset cass-memory-linux-x64 (matches upstream cass-memory-linux-x64.sha256)
CM_V050_SHA256 = "06e1563881f8bb1225cf7036068252ef210f242704a27f8ce32518b822181bd7"
HOOK_FILES = (".cursor/hooks.json", ".claude/settings.json", ".codex/hooks.json", ".har/otel-hooks")


def xintake_timeout(default: float) -> float:
    """Seconds from PFY_XINTAKE_TIMEOUT when that value is a float > 0; otherwise default."""
    raw = (os.environ.get("PFY_XINTAKE_TIMEOUT") or "").strip()
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def timeout_problem() -> str | None:
    """PFY_XINTAKE_TIMEOUT must be a finite number of seconds > 0 when set; xintake_timeout() would quietly use the default instead."""
    raw = os.environ.get("PFY_XINTAKE_TIMEOUT", "")
    if not raw or not raw.strip():
        return None
    raw = raw.strip()
    try:
        v = float(raw)
    except ValueError:
        v = math.nan
    if math.isfinite(v) and v > 0:
        return None
    return f"PFY_XINTAKE_TIMEOUT={raw[:40]!r} is not a number of seconds > 0"


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_env(home: str, **extra: str) -> dict:
    env = scrub_env(os.environ)
    env.update(HOME=home, NO_COLOR="1",
               XDG_CONFIG_HOME=os.path.join(home, ".config"),
               XDG_CACHE_HOME=os.path.join(home, ".cache"),
               XDG_DATA_HOME=os.path.join(home, ".local", "share"),
               npm_config_cache=os.path.join(home, ".npm"),
               **extra)
    return env


def node_major(node: str) -> int:
    try:
        with tempfile.TemporaryDirectory(prefix="pfy-node-ver-") as home:
            out = subprocess.run(
                [node, "--version"], capture_output=True, text=True, timeout=30, env=node_version_env(home),
            ).stdout.strip()
        return int(out.lstrip("v").split(".")[0])
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0


def find_node(env_var: str, tmp_rel: str, minimum: int) -> str | None:
    for c in (os.environ.get(env_var), str(TMP / tmp_rel), shutil.which("node")):
        if c and os.path.isfile(c) and os.access(c, os.X_OK) and node_major(c) >= minimum:
            return c
    return None


def call(cmd: list[str], cwd: str, env: dict, r: dict, tag: str) -> subprocess.CompletedProcess | None:
    try:
        limit = xintake_timeout(120)
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=limit, env=env)
    except subprocess.TimeoutExpired:
        r["reason"] = timeout_reason(tag, limit)
        return None


# ---------------------------------------------------------------- rulora

RULORA_JS = r"""
'use strict'
const core = require(process.argv[2])
const out = { version: require(process.argv[3]).version }
async function main() {
  const { OutputBoundary, LoopControl, CollectiveControl } = core
  const b = new OutputBoundary({
    recover: raw => JSON.parse(raw), adapt: v => v,
    validateCore: v => v !== null && typeof v.summary === 'string' && v.summary.trim().length > 0,
    validateAudit: v => Array.isArray(v.evidenceIds) && v.evidenceIds.every(id => ['E1', 'E2'].includes(id))
  })
  const ok = await b.process('{"summary":"s","evidenceIds":["E1"]}')
  out.accepted = ok.accepted === true && ok.value.summary === 's'
  for (const [k, raw] of [['core', '{"summary":"","evidenceIds":[]}'], ['audit', '{"summary":"s","evidenceIds":["E9"]}']]) {
    try { await b.process(raw); out[k + '_stage'] = 'accepted' } catch (e) { out[k + '_stage'] = e.stage || String(e.code || e) }
  }
  const live = new LoopControl({ kind: 'constraint_revision', maxAttempts: 3, maxNoProgress: 2 })
  live.record({ progressed: true })
  out.progress_status = live.snapshot().status
  const loop = new LoopControl({ kind: 'constraint_revision', maxAttempts: 5, maxNoProgress: 2 })
  out.trace = []
  for (let i = 0; i < 5 && loop.snapshot().status === 'active'; i++) out.trace.push(loop.record({ progressed: false }).status)
  out.loop_status = loop.snapshot().status
  try { loop.record({ progressed: true }); out.closed = 'accepted' } catch (e) { out.closed = e.code || String(e) }
  const cc = new CollectiveControl({ quorum: 2 })
  const subs = [{ id: 'a', answer: { evidence: ['E1'] } }, { id: 'b', answer: { evidence: ['E2'] } }]
  const pool = cc.freezeCandidates(subs)
  subs[0].answer.evidence.push('late')
  out.frozen_pool = JSON.stringify(pool[0].answer.evidence) === '["E1"]'
  try { cc.select(pool, 'invented'); out.unknown = 'accepted' } catch (e) { out.unknown = e.code || String(e) }
  const sel = cc.select(pool, 'b')
  out.selected = sel.id
  out.selection_frozen = Object.isFrozen(sel) && Object.isFrozen(sel.answer)
  console.log(JSON.stringify(out))
}
main().catch(e => { console.log(JSON.stringify({ error: String(e && e.stack || e) })); process.exitCode = 1 })
"""


def smoke_rulora(r: dict) -> int:
    pkg = None
    for c in (os.environ.get("RULORA_DIR"), str(TMP / "rulora")):
        if c and os.path.isfile(os.path.join(c, "node_modules/@rulora/core/package.json")):
            pkg = os.path.join(c, "node_modules/@rulora/core")
            break
    r["package"] = pkg
    if not pkg:
        r["reason"] = ("no @rulora/core. Operator: npm install --prefix ~/DEVELOP/pfy-mentat/tmp/rulora --ignore-scripts "
                       "@rulora/core@0.1.0-alpha.4 (Apache-2.0, Node 20+, no runtime deps). Not in a product checkout")
        return 2
    node = find_node("RULORA_NODE", "rulora/node/bin/node", 20)
    r["node"] = node
    if not node:
        r["reason"] = "no Node 20+ (set $RULORA_NODE or unpack node-v22 to ~/DEVELOP/pfy-mentat/tmp/rulora/node)"
        return 2
    with tempfile.TemporaryDirectory(prefix="pfy-rulora-") as d, \
            tempfile.TemporaryDirectory(prefix="pfy-rulora-home-") as home:
        js = Path(d, "probe.js")
        js.write_text(RULORA_JS)
        p = call([node, str(js), pkg, os.path.join(pkg, "package.json")], d, clean_env(home), r, "rulora probe")
    if p is None:
        return 1
    r["rc"] = p.returncode
    try:
        o = json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        r["reason"] = f"probe printed no JSON (API shape changed?): {(p.stdout + p.stderr)[-400:]}"
        return 1
    r["probe"] = o
    if o.get("error") or p.returncode != 0:
        r["reason"] = f"probe failed (API shape changed?): {str(o.get('error'))[:300]}"
        return 1
    checks = {
        "valid output accepted": o.get("accepted") is True,
        "empty summary rejected at core": o.get("core_stage") == "core",
        "unknown evidence rejected at audit": o.get("audit_stage") == "audit",
        "progress keeps loop active": o.get("progress_status") == "active",
        "two no-progress attempts hand off": o.get("trace") == ["active", "human_handoff"]
                                              and o.get("loop_status") == "human_handoff",
        "closed loop refuses records": o.get("closed") == "LOOP_CLOSED",
        "frozen pool ignores later mutation": o.get("frozen_pool") is True,
        "invented candidate refused": o.get("unknown") == "UNKNOWN_CANDIDATE",
        "existing candidate selected and frozen": o.get("selected") == "b" and o.get("selection_frozen") is True,
    }
    r["checks"] = checks
    bad = [k for k, v in checks.items() if not v]
    if bad:
        r["reason"] = f"control check failed: {bad}"
        return 1
    return 0


# ---------------------------------------------------------------- har

def smoke_har(r: dict) -> int:
    b = find_bin("HAR_BIN", "har/node_modules/.bin/har", "har")
    r["bin"] = b
    if not b:
        r["reason"] = ("no har. Operator: npm install --prefix ~/DEVELOP/pfy-mentat/tmp/har --ignore-scripts "
                       "@osfactory/har@1.16.0 (Apache-2.0, Node 20+). Not `npm install -g`, not `har onboard` in a "
                       "product checkout, no `har hq`, no `har telemetry on`")
        return 2
    node = find_node("HAR_NODE", "har/node/bin/node", 20)
    r["node"] = node
    if not node:
        r["reason"] = "no Node 20+ (set $HAR_NODE or unpack node-v22 to ~/DEVELOP/pfy-mentat/tmp/har/node)"
        return 2
    if not shutil.which("git"):
        r["reason"] = "git not on PATH"
        return 2
    js = os.path.realpath(b)
    with tempfile.TemporaryDirectory(prefix="pfy-har-") as d, \
            tempfile.TemporaryDirectory(prefix="pfy-har-home-") as home:
        repo = os.path.join(d, "repo")
        os.mkdir(repo)
        env = clean_env(home, PATH=os.path.dirname(node) + os.pathsep + os.environ.get("PATH", ""),
                        GIT_AUTHOR_NAME="smoke", GIT_AUTHOR_EMAIL="smoke@localhost",
                        GIT_COMMITTER_NAME="smoke", GIT_COMMITTER_EMAIL="smoke@localhost")
        g = lambda *a: subprocess.run(["git", *a], cwd=repo, capture_output=True, text=True, env=env, timeout=60)
        g("init", "-q", "-b", "main")
        ok_pkg = {"name": "pfy-har-smoke", "version": "0.0.0", "private": True,
                  "scripts": {"typecheck": "node -e 0", "lint": "node -e 0", "test": "node -e 0"}}
        Path(repo, "package.json").write_text(json.dumps(ok_pkg) + "\n")
        g("add", "-A")
        g("commit", "-q", "-m", "init")
        har = lambda tag, *a: call([node, js, *a], repo, env, r, tag)
        steps = [("telemetry off", ["telemetry", "off"]),
                 ("env init", ["env", "init", "--profile", "cli", "--no-cursor-rule", "--no-agents",
                               "--commit-gate", "never"])]
        for tag, args in steps:
            p = har(tag, *args)
            if p is None:
                return 1
            if p.returncode != 0:
                r["reason"] = f"`har {' '.join(args)}` exited {p.returncode}: {(p.stdout + p.stderr)[-300:]}"
                return 1
        if not os.path.isfile(os.path.join(repo, ".har/stages.json")):
            r["reason"] = "env init wrote no .har/stages.json (scaffold shape changed?)"
            return 1
        g("add", "-A")
        g("commit", "-q", "-m", "har scaffold")
        head = g("rev-parse", "HEAD").stdout.strip()
        p = har("env launch", "env", "launch", "1")
        if p is None:
            return 1
        out = p.stdout + p.stderr
        r["launch_rc"] = p.returncode
        m = re.search(r"make ALL file edits under:\s*(\S+)", out)
        if p.returncode != 0 or not m:
            r["reason"] = f"env launch failed or printed no work dir: {out[-400:]}"
            return 1
        work = m.group(1)
        under = Path(work).resolve().is_relative_to(Path(home).resolve())
        r["work_dir_under_temp_home"] = under
        try:
            if not under:
                r["reason"] = "work dir is not under the temp HOME"
                return 1
            p = har("verify pass", "env", "verify", "1", "--full", "--json")
            if p is None:
                return 1
            r["verify_pass_rc"] = p.returncode
            try:
                vp = json.loads(p.stdout[p.stdout.index("{"):])
            except ValueError:
                r["reason"] = f"verify --json printed no JSON: {(p.stdout + p.stderr)[-300:]}"
                return 1
            r["verify_pass"] = vp
            if p.returncode != 0 or vp.get("status") != "pass" or not vp.get("stages") \
                    or not all(s.get("pass") for s in vp["stages"]):
                r["reason"] = "verify --full did not pass on an all-green repo"
                return 1
            bad_pkg = dict(ok_pkg, scripts=dict(ok_pkg["scripts"], test="node -e process.exit(1)"))
            Path(work, "package.json").write_text(json.dumps(bad_pkg) + "\n")
            p = har("verify fail", "env", "verify", "1", "--full", "--json")
            if p is None:
                return 1
            r["verify_fail_rc"] = p.returncode
            try:
                vf = json.loads(p.stdout[p.stdout.index("{"):])
            except ValueError:
                vf = {}
            r["verify_fail"] = {"status": vf.get("status"),
                                "failed": [s.get("name") for s in vf.get("stages", []) if not s.get("pass")]}
            if p.returncode == 0 or vf.get("status") != "fail" or r["verify_fail"]["failed"] != ["unit-tests"]:
                r["reason"] = "a broken test script in the worktree did not fail verify on unit-tests alone"
                return 1
            main_pkg = json.loads(Path(repo, "package.json").read_text())
            dirty = g("status", "--porcelain").stdout.strip()
            if main_pkg != ok_pkg or g("rev-parse", "HEAD").stdout.strip() != head or dirty:
                r["reason"] = f"main checkout changed by the session (dirty={dirty!r})"
                return 1
        finally:
            p = har("teardown", "env", "teardown", "1")
            r["teardown_rc"] = None if p is None else p.returncode
        if r["teardown_rc"] != 0 or os.path.exists(work):
            r["reason"] = "env teardown failed or left the worktree behind"
            return 1
        hooks = [h for h in HOOK_FILES if os.path.exists(os.path.join(home, h))]
        r["hook_files_in_temp_home"] = hooks
        if hooks:
            r["reason"] = f"agent hook files written with telemetry off: {hooks}"
            return 1
    return 0


# ---------------------------------------------------------------- cass-memory

def smoke_cassmemory(r: dict) -> int:
    b = find_bin("CM_BIN", "cass-memory/cm", "cm")
    r["bin"] = b
    if not b:
        r["reason"] = ("no cm binary. Operator: download cass-memory-linux-x64 and cass-memory-linux-x64.sha256 from "
                       "https://github.com/Dicklesworthstone/cass_memory_system/releases/tag/v0.5.0, verify, and save "
                       f"it as ~/DEVELOP/pfy-mentat/tmp/cass-memory/cm (sha256 {CM_V050_SHA256}). Not the "
                       "curl | bash installer, not brew, no `cm hook`; MIT with an OpenAI/Anthropic rider")
        return 2
    expect = pinned(r, "CM_SHA256", CM_V050_SHA256, lower=True)
    digest = sha256_file(b)
    r["sha256"] = digest
    if digest != expect:
        r["reason"] = f"sha256 mismatch: cm binary is {digest}, expected {expect}"
        return 2
    with tempfile.TemporaryDirectory(prefix="pfy-cm-") as d, \
            tempfile.TemporaryDirectory(prefix="pfy-cm-home-") as home:
        env = clean_env(home)

        def cm(tag: str, *a: str) -> dict | None:
            p = call([b, *a, "--json"], d, env, r, f"cm {tag}")
            if p is None:
                return None
            try:
                o = json.loads(p.stdout)
            except ValueError:
                r["reason"] = f"cm {tag} printed no JSON (exit {p.returncode}): {(p.stdout + p.stderr)[-300:]}"
                return None
            if p.returncode != 0 or o.get("success") is not True:
                r["reason"] = f"cm {tag} failed (exit {p.returncode}): {json.dumps(o)[:300]}"
                return None
            return o.get("data") or {}

        if cm("init", "init") is None:
            return 1
        a = cm("add", "add", "Always run the smoke script before opening a catalog pull request", "--category", "testing")
        o = cm("add", "add", "Prefer squash merges pinned to the head sha", "--category", "git")
        if a is None or o is None:
            return 1
        ida, idb = (a.get("bullet") or {}).get("id"), (o.get("bullet") or {}).get("id")
        if not ida or not idb:
            r["reason"] = "cm add returned no bullet id (output shape changed?)"
            return 1
        task = "open a catalog pull request with a smoke script"
        c = cm("context", "context", task)
        if c is None:
            return 1
        r["semantic_mode"] = c.get("semanticMode")
        before = [x.get("id") for x in c.get("relevantBullets", [])]
        r["context_before"] = before
        if ida not in before:
            r["reason"] = "cm context did not return the matching rule"
            return 1
        states = []
        for i in range(3):
            m = cm("mark", "mark", ida, "--harmful", "--reason", "other")
            if m is None:
                return 1
            states.append(m.get("newState"))
        r["harmful_states"] = states
        if states[-1] != "deprecated":
            r["reason"] = f"three harmful marks did not deprecate the rule: {states}"
            return 1
        c = cm("context", "context", task)
        if c is None:
            return 1
        after = [x.get("id") for x in c.get("relevantBullets", [])]
        r["context_after"] = after
        if ida in after:
            r["reason"] = "deprecated rule still returned by cm context"
            return 1
        ls = cm("ls", "ls")
        if ls is None:
            return 1
        listed = json.dumps(ls)
        if idb not in listed:
            r["reason"] = "the untouched rule is missing from cm ls"
            return 1
        u = cm("usage", "usage")
        if u is None:
            return 1
        r["usage"] = u
        if u.get("total") != 0:
            r["reason"] = f"cm usage reports LLM spend with no keys set: {u}"
            return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", required=True, choices=["rulora", "har", "cassmemory"])
    a = ap.parse_args()
    receipt = {"entry": a.entry, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "host": os.uname().nodename}
    bad = timeout_problem()
    if bad:
        receipt["reason"] = bad
        return write(a.entry, receipt, 2)
    code = {"rulora": smoke_rulora, "har": smoke_har, "cassmemory": smoke_cassmemory}[a.entry](receipt)
    return write(a.entry, receipt, code)


if __name__ == "__main__":
    sys.exit(main())
