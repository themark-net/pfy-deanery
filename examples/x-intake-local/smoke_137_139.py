#!/usr/bin/env python3
"""Operate-or-FAIL smokes for X intake Entries 137-139 (neatroots, Hermes Teammates, OpenCode Skill Creator). Stdlib only.

Usage: python3 examples/x-intake-local/smoke_137_139.py --entry neatroots|teammates|skillcreator

Same contract and receipts as smoke.py next to it (whose helpers it reuses): exit 0 = PASS, 1 = the tool ran but
the check failed, 2 = can't run here (prereq missing; reason recorded). Writes pipelines/smoke/<entry>/latest.json.
Never installs or downloads anything. Every child process starts through `run_isolated` in smoke.py (fresh temp HOME,
env limited to PATH/HOME/TERM/LANG/NO_COLOR plus the variables named below; nothing copied from this process, so no
provider key is ever seen; a timeout SIGKILLs the process group, grandchildren included) under bwrap with no network
when bwrap works. No smoke calls a model, starts a server, runs an installer (`install.sh`, `neatroots connect`,
`hermes plugins install`, `opencode-skill-creator install`) or touches Hermes or OpenCode config. PFY_XINTAKE_TIMEOUT
(float seconds, > 0) overrides the 600s per-command timeout.
Real HOME: each entry fingerprints the real-HOME paths the tool could write (neatroots: ~/.neatroots, its default app,
data and checks dir; teammates: ~/.hermes/plugin-data/hermes-teammates, its default ledger dir; skillcreator:
~/.config/opencode/skills/opencode-skill-creator, ~/.config/opencode/opencode-skill-creator-update-check.json and
~/.cache/opencode/packages/opencode-skill-creator@latest, where its plugin start-up writes) with
smoke_128_130.home_sig() before the run and again in a finally, also on timeout or a crash. Any created, deleted or
changed entry FAILs (exit 1) and is listed in real_home_changed, even when bwrap is unavailable. Only those paths are
watched: a write elsewhere in HOME is not seen. checks.body_completed is false and `exception` names it when the run
raised.

  neatroots     $NEATROOTS_APP, else ~/DEVELOP/pfy-mentat/tmp/neatroots/app (the unpacked v0.2.9 release bundle
                neatroots.tar.gz; its top dir holds neatroots/dist/cli.js). Node 22+: $NEATROOTS_NODE, else
                tmp/neatroots/node/bin/node, else `node` on PATH. neatroots/package.json and `cli.js --version` pinned
                to 0.2.9 ($NEATROOTS_VERSION overrides). Only `neatroots check` (rules over saved traces, no server, no
                model) on generated Neatlogs HTTP trace files: a clean run exits 0 with no findings; a run calling the
                same tool 3x with the same args and result fires repeated-tool-call (tool lookup_order, count 3); a run
                whose model output holds a fake sk- key fires secret-in-output and the key is never echoed; a refund
                with no earlier lookup fires a project rule from --checks (requires_before) and only then; --only
                narrows to one rule; an unparsable file exits 2. TMPDIR is a temp subdir (`check` makes a scratch dir
                there and must remove it). Fixtures unchanged, temp HOME empty.
  teammates     $HERMES_TEAMMATES_DIR, else ~/DEVELOP/pfy-mentat/tmp/hermes-teammates (a git clone). plugin.yaml version
                pinned to 1.1.0 ($HT_VERSION) and `git rev-parse HEAD` to de85f5d4793e ($HT_COMMIT). A system-python3
                driver imports only teammates_config.py and teammates_store.py (pure stdlib; no Hermes) with
                PYTHONDONTWRITEBYTECODE=1: a valid two-teammate roster parses with no errors (absent toolsets inherit as
                None); an unknown key, a bad name and an empty toolsets list each make that teammate invalid (fail
                closed); over-long instructions are clipped to 4000 with a warning and stay launchable; an out-of-range
                max_live_runs falls back to 4 with an error. Ledger on a temp SQLite file: admission cap 2 admits two
                runs and refuses the third in one session while another session is admitted; finish() is a single
                terminal CAS (second finish refused, a non-terminal status raises); unknown columns raise. Clone and
                temp HOME unchanged. This is the config and ledger contract only, not a Hermes run.
  skillcreator  $OSC_DIR, else ~/DEVELOP/pfy-mentat/tmp/opencode-skill-creator (an `npm install --prefix <dir>
                --ignore-scripts opencode-skill-creator@0.3.6` tree). Node 18+: $OSC_NODE, else
                tmp/opencode-skill-creator/node/bin/node, else `node` on PATH.
                node_modules/opencode-skill-creator/package.json pinned to 0.3.6 ($OSC_VERSION). A node driver loads the
                plugin's V2 entry with a fake OpenCode ctx (XDG_CONFIG_HOME and XDG_CACHE_HOME in the temp dir,
                OPENCODE_SKILL_CREATOR_AUTO_UPDATE=0), expects its 14 tools, and calls skill_validate on a good skill,
                an unknown frontmatter key, a non-kebab name and a missing SKILL.md, plus skill_parse on the good one.
                Start-up must install its bundled skill under the temp XDG dir and nowhere else, and with auto-update off
                no update-check file or package cache may appear. skill_eval (needs `opencode run` and a model) is not
                run. Fixtures and temp HOME unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from smoke import TMP, find_bin, pinned, run_isolated, timeout_reason, write
from smoke_128_130 import as_json, finish, home_sig, pkg_version, tmo

NR_PIN = "0.2.9"
HT_PIN = "1.1.0"
HT_COMMIT_PIN = "de85f5d4793e122cde98342bddd6e1bf3cd53459"
OSC_PIN = "0.3.6"
SYS_PATH = "/usr/local/bin:/usr/bin:/bin"
WATCH = {"neatroots": (".neatroots",),
         "teammates": (".hermes/plugin-data/hermes-teammates",),
         "skillcreator": (".config/opencode/skills/opencode-skill-creator",
                          ".config/opencode/opencode-skill-creator-update-check.json",
                          ".cache/opencode/packages/opencode-skill-creator@latest")}
FAKE_KEY = "sk-" + "pfysmoke" * 4      # matches neatroots' secret-in-output pattern; not a real key
OSC_TOOLS = 14


def iso(argv: list[str], tag: str, **kw) -> subprocess.CompletedProcess:
    try:
        return run_isolated(argv, timeout=tmo(), **kw)
    except subprocess.TimeoutExpired as e:
        raise TimeoutError(timeout_reason(tag, float(e.timeout)))


def watch_dirs(entry: str) -> str:
    return ", ".join("~/" + d for d in WATCH[entry])


def home_note(entry: str, r: dict) -> str:
    return f"real HOME {', '.join(r.get('real_home_changed') or ['~/' + d for d in WATCH[entry]])} changed"


def watched(entry: str, body, r: dict) -> int:
    """Run body(r, checks) with the real HOME watched; the finally runs on timeout and on any exception too."""
    real_home = Path.home()
    before = {d: home_sig(real_home / d) for d in WATCH[entry]}
    checks: dict[str, bool] = {}
    code = None
    try:
        code = body(r, checks)
        checks["body_completed"] = True
    except BaseException as e:  # main() turns it into a FAIL; the receipt says what stopped the run
        checks["body_completed"] = False
        r["exception"] = f"{type(e).__name__}: {e}"[:300]
        raise
    finally:
        after = {d: home_sig(real_home / d) for d in WATCH[entry]}
        changed = [f"~/{d}" for d in WATCH[entry] if before[d] != after[d]]
        checks["real_home_untouched"] = not changed
        if changed:
            r["real_home_changed"] = changed
        r["checks"] = checks
    if code is not None:
        if not checks["real_home_untouched"]:
            r["reason"] = f"{r.get('reason', '')}; {home_note(entry, r)}"
            return 1
        return code
    code = finish(r, checks, r.pop("_ok_reason", ""))
    if not checks["real_home_untouched"]:
        r["reason"] += f"; {home_note(entry, r)}"
    return code


def node_major(node: str, home: str, cwd: str) -> int | None:
    v = iso([node, "--version"], "node version", home=home, cwd=cwd, path=SYS_PATH, bwrap_writable=[cwd])
    m = re.match(r"v(\d+)\.", v.stdout.strip())
    return int(m.group(1)) if m else None


def tree_hash(p: Path) -> str:
    # is_symlink before is_file: is_file follows the link, so a mode-000 target raises
    # and an edit outside the tree changes the digest. rglob is not given
    # recurse_symlinks (3.13+); on 3.12 it already does not walk a linked directory.
    h = hashlib.sha256()
    rows = []
    for f in p.rglob("*"):
        if f.is_symlink():
            data = os.readlink(f).encode()
        elif f.is_file():
            data = f.read_bytes()
        else:
            continue
        rows.append((f, data))
    for f, data in sorted(rows, key=lambda item: item[0]):
        h.update(str(f.relative_to(p)).encode() + b"\0" + data + b"\0")
    return h.hexdigest()


def find_node(env: str, tmp_rel: str) -> str | None:
    return find_bin(env, tmp_rel, "node")


# ---------------------------------------------------------------- neatroots
def nr_span_tool(name: str, inp: dict, out: str) -> dict:
    return {"name": name, "kind": "TOOL", "input": inp, "output": out}


def nr_llm(inp: str, out: str) -> dict:
    return {"name": "answer", "kind": "LLM", "model": "stub", "input": inp, "output": out,
            "tokens": {"prompt": 10, "completion": 5}}


def nr_fixtures(d: Path) -> dict[str, Path]:
    clean = {"name": "pfy-clean", "project": "pfy-smoke", "input": "status of order 7", "output": "Order 7 shipped.",
             "children": [nr_span_tool("lookup_order", {"id": 7}, "shipped"), nr_llm("status", "Order 7 shipped.")]}
    loop = {"name": "pfy-loop", "project": "pfy-smoke", "input": "status of order 8", "output": "Still checking.",
            "children": [nr_span_tool("lookup_order", {"id": 8}, "pending") for _ in range(3)]
            + [nr_llm("status", "Still checking.")]}
    leak = {"name": "pfy-leak", "project": "pfy-smoke", "input": "which key", "output": "done",
            "children": [nr_llm("which key", "use " + FAKE_KEY)]}
    refund = {"name": "pfy-refund", "project": "pfy-smoke", "input": "refund order 9", "output": "Refunded.",
              "children": [nr_span_tool("refund", {"id": 9}, "ok"), nr_llm("refund", "Refunded.")]}
    files = {"clean": d / "clean.jsonl", "bad": d / "bad.jsonl", "broken": d / "broken.json"}
    files["clean"].write_text(json.dumps(clean) + "\n", encoding="utf-8")
    files["bad"].write_text("".join(json.dumps(x) + "\n" for x in (loop, leak, refund)), encoding="utf-8")
    files["broken"].write_text("{not json", encoding="utf-8")
    checks = d / "checks"
    checks.mkdir()
    (checks / "refund.yaml").write_text(
        "id: pfy-refund-needs-lookup\nkind: rule\ntitle: Refund without an order lookup first\nrule:\n"
        "  type: requires_before\n  span: { type: [tool], tool: refund }\n  requires: { type: [tool], tool: lookup_order }\n"
        "guidance: Look the order up before refunding it.\n", encoding="utf-8")
    files["checks"] = checks
    return files


def nr_findings(j) -> dict:
    out = {}
    for run in (j or {}).get("runs", []) if isinstance(j, dict) else []:
        out[run.get("root_name")] = {f.get("check_id"): f.get("params") or {} for f in run.get("findings", [])}
    return out


def smoke_neatroots(r: dict) -> int:
    app = Path(os.environ.get("NEATROOTS_APP") or TMP / "neatroots/app")
    cli = app / "neatroots/dist/cli.js"
    node = find_node("NEATROOTS_NODE", "neatroots/node/bin/node")
    r["app"], r["node"] = str(app), node
    if not cli.is_file():
        r["reason"] = ("neatroots not found ($NEATROOTS_APP or tmp/neatroots/app with neatroots/dist/cli.js); unpack the "
                       "v0.2.9 neatroots.tar.gz there, see the handoff. Never run install.sh")
        return 2
    if not node:
        r["reason"] = "node not found ($NEATROOTS_NODE, tmp/neatroots/node/bin/node, PATH)"
        return 2
    want = pinned(r, "NEATROOTS_VERSION", NR_PIN)
    return watched("neatroots", lambda rr, checks: _neatroots(rr, node, app, cli, want, checks), r)


def _neatroots(r: dict, node: str, app: Path, cli: Path, want: str, checks: dict) -> int | None:
    with tempfile.TemporaryDirectory(prefix="pfy-neatroots-") as tdn:
        td = Path(tdn)
        home = td / "home"
        home.mkdir()
        major = node_major(node, str(home), tdn)
        r["node_major"] = major
        if major is None or major < 22:
            r["reason"] = f"neatroots needs Node 22+, {node} is {major}"
            return 2
        have_pkg = pkg_version(app / "neatroots/package.json")
        ntmp = td / "tmp"   # `check` makes a neatroots-check-* dir under TMPDIR (EROFS without one)
        ntmp.mkdir()
        kw = {"home": str(home), "cwd": tdn, "path": SYS_PATH, "extra": {"TMPDIR": str(ntmp)}, "bwrap_writable": [tdn]}
        v = iso([node, str(cli), "--version"], "neatroots version", **kw)
        have = v.stdout.strip().splitlines()[-1].strip() if v.stdout.strip() else ""
        r["neatroots_version"] = {"package_json": have_pkg, "cli": have}
        if have_pkg != want or have != want:
            r["reason"] = f"neatroots version is {have_pkg!r}/{have!r}, not {want} (set $NEATROOTS_VERSION)"
            return 2
        fx = nr_fixtures(td)
        sig = {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in fx.items() if p.is_file()}
        base = [node, str(cli), "check"]
        clean = iso(base + [str(fx["clean"]), "--json"], "neatroots check clean", **kw)
        bad = iso(base + [str(fx["bad"]), "--json"], "neatroots check bad", **kw)
        proj = iso(base + [str(fx["bad"]), str(fx["clean"]), "--json", "--checks", str(fx["checks"])],
                   "neatroots check project rule", **kw)
        only = iso(base + [str(fx["bad"]), "--json", "--only", "repeated-tool-call"], "neatroots check only", **kw)
        broken = iso(base + [str(fx["broken"])], "neatroots check broken", **kw)
        jc, jb, jp, jo = as_json(clean), as_json(bad), as_json(proj), as_json(only)
        fc, fb, fp, fo = nr_findings(jc), nr_findings(jb), nr_findings(jp), nr_findings(jo)
        r["rc"] = {"clean": clean.returncode, "bad": bad.returncode, "project_rule": proj.returncode,
                   "only": only.returncode, "broken": broken.returncode}
        r["findings"] = {"bad": {k: sorted(v) for k, v in fb.items()}, "project_rule": {k: sorted(v) for k, v in fp.items()},
                         "only": {k: sorted(v) for k, v in fo.items()}}
        r["rules"] = {"library": len((jb or {}).get("rules", [])) if isinstance(jb, dict) else None,
                      "with_project": len((jp or {}).get("rules", [])) if isinstance(jp, dict) else None,
                      "only": (jo or {}).get("rules") if isinstance(jo, dict) else None}
        r["broken_tail"] = (broken.stdout + broken.stderr).strip()[-300:]
        rep = (fb.get("pfy-loop") or {}).get("repeated-tool-call") or {}
        lib_rules = r["rules"]["library"] or 0
        checks["clean_exit_0_no_findings"] = clean.returncode == 0 and fc == {"pfy-clean": {}}
        checks["bad_exit_1"] = bad.returncode == 1
        checks["repeat_fires_with_params"] = rep.get("tool") == "lookup_order" and str(rep.get("count")) == "3"
        checks["secret_in_output_fires"] = "secret-in-output" in (fb.get("pfy-leak") or {})
        checks["secret_never_echoed"] = not any(FAKE_KEY in (p.stdout + p.stderr) for p in (bad, proj, only))
        checks["library_has_no_refund_rule"] = (fb.get("pfy-refund") or {}) == {}
        checks["project_rule_fires_only_on_refund"] = (
            proj.returncode == 1 and "pfy-refund-needs-lookup" in (fp.get("pfy-refund") or {})
            and (fp.get("pfy-clean") or {}) == {}
            and "pfy-refund-needs-lookup" not in (fp.get("pfy-loop") or {})
            and r["rules"]["with_project"] == lib_rules + 1 and lib_rules > 0)
        checks["only_narrows_rules"] = (only.returncode == 1 and r["rules"]["only"] == ["repeated-tool-call"]
                                        and {k for v in fo.values() for k in v} == {"repeated-tool-call"})
        checks["unparsable_file_exits_2"] = broken.returncode == 2
        checks["fixtures_untouched"] = all(hashlib.sha256(fx[k].read_bytes()).hexdigest() == s for k, s in sig.items())
        r["tmpdir_left"] = sorted(x.name for x in ntmp.iterdir())
        checks["check_tmpdir_cleaned"] = not r["tmpdir_left"]
        checks["home_untouched"] = not any(home.iterdir())
    r["_ok_reason"] = ("`neatroots check` offline: clean run 0, repeated-tool-call and secret-in-output fire (key not "
                       "echoed), a --checks requires_before rule fires only on the refund run, --only narrows, bad file 2; "
                       f"fixtures, temp HOME and the watched real-HOME dir ({watch_dirs('neatroots')}) unchanged")
    return None


# ---------------------------------------------------------------- teammates (Hermes Teammates)
HT_DRIVER = r'''
import json, sqlite3, sys, time
spec = json.load(open(sys.argv[1]))
sys.path.insert(0, spec["dir"])
import teammates_config as C
import teammates_store as S
out = {}
ok = C.parse({"teammates": {
    "reviewer": {"description": "Careful reviewer.", "instructions": "Review with file:line.", "toolsets": ["file", "terminal"]},
    "scout": {"description": "Fast researcher.", "instructions": "Quote sources."}}})
out["valid"] = {"errors": ok.get("config_errors"), "invalid": sorted(ok.get("invalid_teammates") or {}),
                "names": sorted(ok.get("teammates") or {}),
                "toolsets": {k: v.get("toolsets") for k, v in (ok.get("teammates") or {}).items()}}
bad = C.parse({"max_live_runs": 99, "teammates": {
    "leaky": {"description": "d", "instructions": "i", "toolsets": ["file"], "api_key": "x"},
    "Reviewer!": {"description": "d", "instructions": "i"},
    "empty": {"description": "d", "instructions": "i", "toolsets": []},
    "long": {"description": "d", "instructions": "x" * 5000, "toolsets": ["file"]}}})
inv = bad.get("invalid_teammates") or {}
out["bad"] = {"invalid": sorted(inv), "invalid_msgs": {k: v for k, v in inv.items()},
              "errors": bad.get("config_errors"), "max_live_runs": bad.get("max_live_runs"),
              "long_len": len(((bad.get("teammates") or {}).get("long") or {}).get("instructions") or "")}
conn = sqlite3.connect(spec["db"])
st = S.Store(conn)


def row(rid, sess):
    return {"run_id": rid, "teammate": "reviewer", "owner_session_id": sess, "goal": "review", "status": "running",
            "instance_id": "pfy-smoke", "pid": 1, "created_at": time.time()}


out["admit"] = [st.admit(row("r1", "s1"), 2), st.admit(row("r2", "s1"), 2), st.admit(row("r3", "s1"), 2),
                st.admit(row("r4", "s2"), 2)]
out["finish"] = [st.finish("r1", "succeeded", summary="ok"), st.finish("r1", "failed")]
try:
    st.finish("r2", "running")
    out["finish_nonterminal_raises"] = False
except ValueError:
    out["finish_nonterminal_raises"] = True
try:
    st.insert(dict(row("r5", "s3"), bogus=1))
    out["unknown_column_raises"] = False
except ValueError:
    out["unknown_column_raises"] = True
out["r1_status"] = (st.get("r1", "s1") or {})["status"] if st.get("r1", "s1") else None
conn.close()
print(json.dumps(out))
'''


def smoke_teammates(r: dict) -> int:
    d = Path(os.environ.get("HERMES_TEAMMATES_DIR") or TMP / "hermes-teammates")
    r["dir"] = str(d)
    need = [d / "plugin.yaml", d / "teammates_config.py", d / "teammates_store.py"]
    if not all(p.is_file() for p in need):
        r["reason"] = ("hermes-teammates clone not found ($HERMES_TEAMMATES_DIR or tmp/hermes-teammates with plugin.yaml, "
                       "teammates_config.py, teammates_store.py); see the handoff. Never `hermes plugins install`")
        return 2
    python = shutil.which("python3", path=SYS_PATH)
    git = shutil.which("git", path=SYS_PATH)
    if not python or not git:
        r["reason"] = f"python3 and git are needed in {SYS_PATH}"
        return 2
    want = pinned(r, "HT_VERSION", HT_PIN)
    want_commit = pinned(r, "HT_COMMIT", HT_COMMIT_PIN, lower=True)
    return watched("teammates", lambda rr, checks: _teammates(rr, d, python, git, want, want_commit, checks), r)


def _teammates(r: dict, d: Path, python: str, git: str, want: str, want_commit: str, checks: dict) -> int | None:
    m = re.search(r"^version:\s*(\S+)", (d / "plugin.yaml").read_text(encoding="utf-8"), re.M)
    have = m.group(1).strip("'\"") if m else ""
    with tempfile.TemporaryDirectory(prefix="pfy-teammates-") as tdn:
        td = Path(tdn)
        home = td / "home"
        home.mkdir()
        g = iso([git, "-C", str(d), "rev-parse", "HEAD"], "git rev-parse", home=str(home), cwd=tdn, path=SYS_PATH,
                extra={"GIT_CONFIG_NOSYSTEM": "1", "GIT_CEILING_DIRECTORIES": str(d.parent)}, bwrap_writable=[tdn])
        commit = g.stdout.strip().lower()
        r["plugin_version"], r["commit"] = have, commit
        if have != want:
            r["reason"] = f"plugin.yaml version is {have!r}, not {want} (set $HT_VERSION)"
            return 2
        if commit != want_commit:
            r["reason"] = f"clone HEAD is {commit!r}, not {want_commit} (set $HT_COMMIT)"
            return 2
        before = tree_hash(d / "__pycache__") if (d / "__pycache__").exists() else None
        src_sig = {n: hashlib.sha256((d / n).read_bytes()).hexdigest() for n in ("teammates_config.py", "teammates_store.py")}
        drv, spec = td / "driver.py", td / "spec.json"
        drv.write_text(HT_DRIVER, encoding="utf-8")
        spec.write_text(json.dumps({"dir": str(d), "db": str(td / "ledger.db")}), encoding="utf-8")
        p = iso([python, str(drv), str(spec)], "teammates driver", home=str(home), cwd=tdn, path=SYS_PATH,
                extra={"PYTHONDONTWRITEBYTECODE": "1"}, bwrap_writable=[tdn])
        o = as_json(p)
        if not isinstance(o, dict):
            r["driver_rc"] = p.returncode
            r["driver_tail"] = (p.stdout + p.stderr).strip()[-800:]
            checks["driver_report"] = False
            return None
        v, b = o.get("valid") or {}, o.get("bad") or {}
        r["valid"], r["bad"] = v, {k: b.get(k) for k in ("invalid", "max_live_runs", "long_len")}
        r["admit"], r["finish"] = o.get("admit"), o.get("finish")
        msgs = b.get("invalid_msgs") or {}
        errs = b.get("errors") or []
        checks["valid_roster_no_errors"] = (v.get("errors") == [] and v.get("invalid") == []
                                            and v.get("names") == ["reviewer", "scout"])
        checks["absent_toolsets_inherit"] = (v.get("toolsets") or {}).get("scout") is None and \
            (v.get("toolsets") or {}).get("reviewer") == ["file", "terminal"]
        checks["unknown_key_fails_closed"] = any("unknown key api_key" in s for s in msgs.get("leaky", []))
        checks["bad_name_fails_closed"] = "Reviewer!" in msgs
        checks["empty_toolsets_fails_closed"] = "empty" in msgs
        checks["long_instructions_clipped_not_invalid"] = (b.get("long_len") == 4000 and "long" not in msgs
                                                           and any("clipped to 4000" in s for s in errs))
        checks["out_of_range_setting_defaults"] = b.get("max_live_runs") == 4 and any("max_live_runs" in s for s in errs)
        checks["admission_cap_per_session"] = o.get("admit") == [True, True, False, True]
        checks["finish_is_single_terminal_cas"] = o.get("finish") == [True, False] and o.get("r1_status") == "succeeded"
        checks["finish_nonterminal_raises"] = o.get("finish_nonterminal_raises") is True
        checks["unknown_column_raises"] = o.get("unknown_column_raises") is True
        after = tree_hash(d / "__pycache__") if (d / "__pycache__").exists() else None
        checks["clone_untouched"] = before == after and all(
            hashlib.sha256((d / n).read_bytes()).hexdigest() == s for n, s in src_sig.items())
        checks["home_untouched"] = not any(home.iterdir())
    r["_ok_reason"] = ("roster parse fails closed on unknown key, bad name and empty toolsets, clips long instructions, "
                       "defaults bad settings; SQLite ledger caps live runs per session and finishes once; clone, temp "
                       f"HOME and the watched real-HOME dir ({watch_dirs('teammates')}) unchanged")
    return None


# ---------------------------------------------------------------- skillcreator (OpenCode Skill Creator)
OSC_DRIVER = r'''
import { readFileSync } from "fs";
const spec = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const out = {};
try {
  const mod = await import(spec.entry);
  const tools = {};
  const ctx = { location: { directory: spec.proj },
                tool: { transform: async (f) => f({ add: (t) => { tools[t.name] = t; } }) } };
  const dispose = await mod.default.setup(ctx);
  out.tools = Object.keys(tools).sort();
  for (const s of ["good", "badkey", "BadName", "missing"]) {
    const res = await tools.skill_validate.execute({ skillPath: spec.proj + "/skills/" + s }, {});
    out[s] = JSON.parse(res.content);
  }
  const p = await tools.skill_parse.execute({ skillPath: spec.proj + "/skills/good" }, {});
  out.parse = JSON.parse(p.content);
  if (typeof dispose === "function") await dispose();
} catch (e) {
  out.error = String(e && e.stack || e).slice(0, 600);
}
console.log(JSON.stringify(out));
'''
OSC_GOOD = "---\nname: good\ndescription: Use when the user asks to summarize a pfy-deanery smoke receipt.\n---\n# Good\nBody.\n"


def smoke_skillcreator(r: dict) -> int:
    d = Path(os.environ.get("OSC_DIR") or TMP / "opencode-skill-creator")
    pkg = d / "node_modules/opencode-skill-creator"
    entry = pkg / "dist/skill-creator.js"
    node = find_node("OSC_NODE", "opencode-skill-creator/node/bin/node")
    r["dir"], r["node"] = str(d), node
    if not entry.is_file():
        r["reason"] = ("opencode-skill-creator not found ($OSC_DIR or tmp/opencode-skill-creator with "
                       "node_modules/opencode-skill-creator/dist/skill-creator.js); `npm install --prefix` it there, see "
                       "the handoff. Never run its `install` command")
        return 2
    if not node:
        r["reason"] = "node not found ($OSC_NODE, tmp/opencode-skill-creator/node/bin/node, PATH)"
        return 2
    want = pinned(r, "OSC_VERSION", OSC_PIN)
    return watched("skillcreator", lambda rr, checks: _skillcreator(rr, node, pkg, entry, want, checks), r)


def _skillcreator(r: dict, node: str, pkg: Path, entry: Path, want: str, checks: dict) -> int | None:
    have = pkg_version(pkg / "package.json")
    r["osc_version"] = have
    if have != want:
        r["reason"] = f"opencode-skill-creator package.json is {have!r}, not {want} (set $OSC_VERSION)"
        return 2
    with tempfile.TemporaryDirectory(prefix="pfy-skillcreator-") as tdn:
        td = Path(tdn)
        home, xdg, cache, proj = td / "home", td / "xdg", td / "cache", td / "proj"
        for p in (home, xdg, cache):
            p.mkdir()
        major = node_major(node, str(home), tdn)
        r["node_major"] = major
        if major is None or major < 18:
            r["reason"] = f"opencode-skill-creator needs Node 18+, {node} is {major}"
            return 2
        skills = {"good": OSC_GOOD, "badkey": "---\nname: badkey\ndescription: x\nfoo: bar\n---\nBody\n",
                  "BadName": "---\nname: BadName\ndescription: x\n---\nBody\n"}
        for name, text in skills.items():
            (proj / "skills" / name).mkdir(parents=True)
            (proj / "skills" / name / "SKILL.md").write_text(text, encoding="utf-8")
        fx_sig = tree_hash(proj)
        drv, spec = td / "driver.mjs", td / "spec.json"
        drv.write_text(OSC_DRIVER, encoding="utf-8")
        spec.write_text(json.dumps({"entry": str(entry), "proj": str(proj)}), encoding="utf-8")
        p = iso([node, str(drv), str(spec)], "skillcreator driver", home=str(home), cwd=tdn, path=SYS_PATH,
                extra={"XDG_CONFIG_HOME": str(xdg), "XDG_CACHE_HOME": str(cache),
                       "OPENCODE_SKILL_CREATOR_AUTO_UPDATE": "0"}, bwrap_writable=[tdn])
        o = as_json(p)
        if not isinstance(o, dict) or o.get("error"):
            r["driver_rc"] = p.returncode
            r["driver_tail"] = ((o or {}).get("error") if isinstance(o, dict) else (p.stdout + p.stderr).strip())
            r["driver_tail"] = str(r["driver_tail"])[-800:]
            checks["driver_report"] = False
            return None
        tools = o.get("tools") or []
        r["tools"] = tools
        r["validate"] = {k: o.get(k) for k in ("good", "badkey", "BadName", "missing")}
        bundled = xdg / "opencode/skills/opencode-skill-creator/SKILL.md"
        status = xdg / "opencode/opencode-skill-creator-update-check.json"
        r["xdg_files"] = sorted(str(x.relative_to(td)) for x in xdg.rglob("*") if x.is_file())[:20]

        def res(k: str) -> dict:
            v = o.get(k)
            return v if isinstance(v, dict) else {}

        checks["registers_14_tools"] = len(tools) == OSC_TOOLS and {"skill_validate", "skill_eval", "skill_parse"} <= set(tools)
        checks["good_skill_valid"] = res("good").get("valid") is True
        checks["unknown_key_rejected"] = res("badkey").get("valid") is False and "foo" in str(res("badkey").get("message"))
        checks["non_kebab_name_rejected"] = res("BadName").get("valid") is False and \
            "kebab" in str(res("BadName").get("message"))
        checks["missing_skill_md_rejected"] = res("missing").get("valid") is False
        checks["parse_reads_frontmatter"] = res("parse").get("name") == "good" and \
            res("parse").get("description", "").startswith("Use when the user asks")
        checks["bundled_skill_lands_in_xdg"] = bundled.is_file()
        checks["auto_update_off_no_status_file"] = not status.exists()
        checks["no_package_cache_written"] = not any(cache.iterdir())
        checks["fixtures_untouched"] = tree_hash(proj) == fx_sig
        checks["home_untouched"] = not any(home.iterdir())
    r["_ok_reason"] = ("V2 plugin loads with a fake ctx, 14 tools; skill_validate accepts the good skill and rejects an "
                       "unknown key, a non-kebab name and a missing SKILL.md; bundled skill goes to the temp XDG dir only, "
                       f"no update check with auto-update off; temp HOME and the watched real-HOME paths "
                       f"({watch_dirs('skillcreator')}) unchanged")
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", required=True, choices=["neatroots", "teammates", "skillcreator"])
    a = ap.parse_args()
    receipt = {"entry": a.entry, "script": "examples/x-intake-local/smoke_137_139.py",
               "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    fn = {"neatroots": smoke_neatroots, "teammates": smoke_teammates, "skillcreator": smoke_skillcreator}[a.entry]
    try:
        code = fn(receipt)
    except Exception as e:  # TimeoutError or any crash still writes a FAIL receipt (watched() saved the checks)
        receipt.pop("_ok_reason", None)
        receipt["reason"] = str(e) if isinstance(e, TimeoutError) else f"unexpected {type(e).__name__}: {e}"
        if receipt.get("checks", {}).get("real_home_untouched") is False:
            receipt["reason"] += f"; {home_note(a.entry, receipt)}"
        code = 1
    return write(a.entry, receipt, code)


if __name__ == "__main__":
    sys.exit(main())
