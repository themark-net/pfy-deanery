#!/usr/bin/env python3
"""Operate-or-FAIL smokes for X intake Entries 143-145 (taste-skill, gitai, Muxin). Stdlib only.

Usage: python3 examples/x-intake-local/smoke_143_145.py --entry taste-skill|gitai|muxin

Same contract and receipts as smoke.py (whose helpers it reuses, with smoke_128_130 and smoke_140_142): exit 0 = PASS,
1 = the tool ran but a check failed, 2 = can't run here (prereq missing; reason recorded). Writes
pipelines/smoke/<entry>/latest.json. Never installs, builds or downloads anything. Every child starts through
`run_isolated` (fresh temp HOME, env limited to PATH/HOME/TERM/LANG/NO_COLOR plus the variables named below, nothing
copied from this process, a timeout SIGKILLs the process group) under bwrap with no network when bwrap works. A
listener a tool opens (Chrome's DevTools port, graft-cache's metrics port) lives inside that private network
namespace. No smoke calls a model, adds a key, runs an installer (`install.sh`, `npx skills add`, `make build`) or
touches an agent's skill or MCP config. PFY_XINTAKE_TIMEOUT and explicit binary overrides behave as in
smoke_140_142.py (a bad value exits 2 before anything runs).
Real HOME: each entry fingerprints the real-HOME paths the tool could write (taste-skill: ~/.taste-skill; gitai:
~/.config/graft, ~/.cache/graft; muxin: ~/.config/muxin, ~/.local/state/gh) before the run and again in a finally.
Any change FAILs (exit 1) and is listed in real_home_changed. Only those paths are watched.

  taste-skill  $TASTE_SKILL_DIR, else $PFY_TMP/taste-skill (a `git clone` of
               github.com/Leonxlnx/taste-skill; HEAD pinned to TASTE_SKILL_COMMIT, $TASTE_SKILL_COMMIT overrides).
               Node 22+ ($TASTE_NODE, else tmp/taste-skill/node/bin/node, else PATH) and a Chrome/Chromium
               ($TASTE_CHROME, else chromium, chromium-browser, google-chrome or google-chrome-stable on the system
               PATH, handed over as CHROME_PATH). Checks: SKILL.md frontmatter names design-taste-frontend; scripts/
               lint.mjs on a slop fixture exits 1 and flags gradient, emoji, eyebrow, lorem and purple, on a clean
               fixture exits 0 with no findings, on a missing path exits 2; draw.mjs --options 3 --seed 7 gives the
               same menu twice and writes nothing; a full draw writes direction.json into --out and its history only
               to the temp TASTE_SKILL_HISTORY; inspect.mjs renders the slop fixture in headless Chrome, exits 1 with
               FAIL findings for gradient, emoji and eyebrow and saves at least one .jpg; no ad-chrome-* profile left
               in TASTE_SKILL_TMP. Fixtures unchanged. Chrome's own leftovers (XDG dirs, NSS pki, Singleton dirs in
               TMPDIR) go to temp dirs; the temp HOME may hold only .local/share/{applications,pki} from Chrome.
  gitai        $GITAI_DIR, else $PFY_TMP/gitai (a `git clone --branch v0.3.1` of
               github.com/feder-cr/git-ai, HEAD pinned to GITAI_COMMIT) with `make build` already run there by hand
               (_build/bin/gitaly, gitaly-hooks, gitaly-ssh, graft, graft-cache; `gitaly --version` must print
               "Gitaly, version 0.3.1", $GITAI_VERSION overrides, else exit 2). The smoke runs the repo's own
               examples/graft/quickstart.sh in a temp work dir with a `make` shim that only accepts `-C <repo> build`
               and does nothing (the binaries are prebuilt; the smoke never builds). Needs git and openssl on the
               system PATH. Checks: exit 0; "denied as expected" printed; in the temp bare repo main holds README.md
               "hello graft" and not the denied "nope" line, and feature/demo holds feature.txt. Temp HOME empty.
               NOT verified on the box: it can't build Gitaly (Go 1.27.2 but no make, meson or ninja), so this path has
               only been exercised with stubs.
  muxin        $MUXIN_BIN, else $PFY_TMP/muxin/Muxin/muxin, else `muxin` on PATH (the v0.6.0
               linux-x86_64 release tarball unpacked; never its install.sh). Binary sha256 pinned to MUXIN_SHA256
               and `muxin --version` to MUXIN_VERSION. $MUXIN_LIB_DIR, when set, becomes LD_LIBRARY_PATH (for hosts
               missing libxkbcommon-x11 or libxcb-xkb; a --version that fails exits 2). MUXIN_HOME, XDG_STATE_HOME and XDG_CONFIG_HOME point at temp
               dirs. Checks: `muxin paths` resolves under MUXIN_HOME; `muxin machines --demo --json` lists exactly the
               9 demo machines; `muxin mcp --demo` over stdio reports serverInfo muxin at the pin, at least 80 tools
               with run_on_machines and cloud_destroy marked destructiveHint and status marked readOnlyHint; status
               summarises 9 machines; get_machine forge returns it; an unknown id returns not_found naming the known
               ids; a call with a wrong argument name returns invalid; run_on_machines on forge in demo mode returns
               succeeded; the server exits on stdin EOF. Nothing reaches a real machine (demo data, no network). The
               temp HOME stays empty. A probe without XDG_STATE_HOME set saw $HOME/.local/state/gh/device-id appear;
               that file is gh's own (Muxin has no device-id code, but it runs the host's gh), so XDG_STATE_HOME is
               pinned to a temp dir and ~/.local/state/gh is watched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from smoke import TMP, find_bin, pinned, write
from smoke_128_130 import as_json, finish, home_sig
from smoke_140_142 import (CHROMES, MCP_CLIENT, SYS_PATH, _body, bad_override, iso, node_major, system_python,
                           timeout_problem, tree_hash)

TASTE_PIN = "6010f91a9935f1c167dfc500fb1a475681892e6b"
GITAI_PIN = "914e481ef057ca7b9dc9a5a7338d96bca16790e1"
GITAI_VERSION = "0.3.1"
MUXIN_PIN = "0.6.0"
MUXIN_SHA = "b51e6fda3911d181f6bd188bd375d846eeaface64a060888dcfe14201fd3264d"
WATCH = {"taste-skill": (".taste-skill",),
         "gitai": (".config/graft", ".cache/graft"),
         "muxin": (".config/muxin", ".local/state/gh")}
SLOP = ('<html><body><p class="eyebrow">New</p><h1 style="background: linear-gradient(90deg,#6366f1,#a855f7)">'
        'Unlock your future \U0001F680</h1><p>Lorem ipsum dolor sit amet</p><hr></body></html>\n')
CLEAN = ('<html><head><style>body{font-family:"Fraunces",serif;background:#f3efe6;color:#1d1b16} h1{font-size:4rem}'
         '</style></head><body><h1>Bread baked at four, sold by nine</h1><p>We bake twelve loaves a morning and close '
         'when they are gone.</p><a href="/order">Order a loaf for Saturday</a></body></html>\n')
LINT_WANT = {"gradient", "emoji", "eyebrow", "lorem", "purple"}
INSPECT_WANT = {"gradient", "emoji", "eyebrow"}
DEMO_MACHINES = ["beacon", "dev-1", "forge", "harbor", "orbit", "pebble", "sandbox", "vault", "win-test"]
CHROME_LEFTOVERS = (".local/share/applications", ".local/share/pki")
GITAI_BINS = ("gitaly", "gitaly-hooks", "gitaly-ssh", "graft", "graft-cache")


def chrome_leftover(rel: str) -> bool:
    """A temp-HOME path Chrome may leave: the .local and .local/share parents, or a path at or under one of
    CHROME_LEFTOVERS on a path boundary (so .local/share/pkiX does not pass)."""
    return rel in (".local", ".local/share") or any(rel == c or rel.startswith(c + "/") for c in CHROME_LEFTOVERS)


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
    except BaseException as e:
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
            r["reason"] = "; ".join(x for x in (r.get("reason"), home_note(entry, r)) if x)
            return 1
        return code
    code = finish(r, checks, r.pop("_ok_reason", ""))
    if not checks["real_home_untouched"]:
        r["reason"] += f"; {home_note(entry, r)}"
    return code


def git_head(git: str, repo: Path, home: str, cwd: str) -> str:
    p = iso([git, "-C", str(repo), "rev-parse", "HEAD"], "git rev-parse", home=home, cwd=cwd, path=SYS_PATH,
            extra={"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}, bwrap_writable=[cwd])
    return p.stdout.strip() if p.returncode == 0 else ""


def files_under(p: Path) -> list[str]:
    return sorted(str(x.relative_to(p)) for x in p.rglob("*") if x.is_file()) if p.is_dir() else []


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_chrome(var: str) -> str | None:
    c = os.environ.get(var)
    if c and os.path.isfile(c) and os.access(c, os.X_OK):
        return c
    for name in CHROMES:
        p = shutil.which(name, path=SYS_PATH)
        if p:
            return p
    return None


def finding_ids(o, level: str | None = None) -> set[str]:
    f = (o or {}).get("findings") if isinstance(o, dict) else None
    return {x.get("id") for x in f or [] if isinstance(x, dict) and (level is None or x.get("level") == level)}


# ---------------------------------------------------------------- taste-skill
def smoke_taste(r: dict) -> int:
    d = Path(os.environ.get("TASTE_SKILL_DIR") or TMP / "taste-skill")
    skill = d / "skills/taste-skill"
    node = find_bin("TASTE_NODE", "taste-skill/node/bin/node", "node")
    git = shutil.which("git", path=SYS_PATH)
    r["dir"], r["node"] = str(d), node
    if not (skill / "scripts/lint.mjs").is_file() or not (d / ".git").exists():
        r["reason"] = ("taste-skill not found ($TASTE_SKILL_DIR or tmp/taste-skill as a git clone with "
                       "skills/taste-skill/scripts/lint.mjs); `git clone` it there, see the handoff. Never "
                       "`npx skills add` or copy it into an agent's skill dir")
        return 2
    bad = bad_override("TASTE_NODE", "TASTE_CHROME")
    if bad:
        r["reason"] = bad
        return 2
    if not node or not git:
        r["reason"] = f"node ($TASTE_NODE, tmp/taste-skill/node/bin/node, PATH) and git ({SYS_PATH}) are needed"
        return 2
    chrome = find_chrome("TASTE_CHROME")
    r["chrome"] = chrome
    if not chrome:
        r["reason"] = f"no Chrome/Chromium ($TASTE_CHROME, {', '.join(CHROMES)} in {SYS_PATH}) for inspect.mjs"
        return 2
    want = pinned(r, "TASTE_SKILL_COMMIT", TASTE_PIN, lower=True)
    return watched("taste-skill", lambda rr, checks: _taste(rr, node, git, chrome, d, skill, want, checks), r)


def _taste(r: dict, node: str, git: str, chrome: str, d: Path, skill: Path, want: str, checks: dict) -> int | None:
    with tempfile.TemporaryDirectory(prefix="pfy-taste-") as tdn:
        td = Path(tdn)
        names = ("home", "site", "tmp", "ttmp", "xdg", "cache", "data", "hist", "out", "cwd")
        home, site, ntmp, ttmp, xdg, cache, data, hist, out, cwd = (td / n for n in names)
        for p in (home, site, ntmp, ttmp, xdg, cache, data, hist, out, cwd):
            p.mkdir()
        head = git_head(git, d, str(home), tdn)
        r["commit"] = head
        if head.lower() != want:
            r["reason"] = f"taste-skill HEAD is {head!r}, not {want} (set $TASTE_SKILL_COMMIT)"
            return 2
        major = node_major(node, str(home), tdn)
        r["node_major"] = major
        if major is None or major < 22:
            r["reason"] = f"inspect.mjs needs Node 22+, {node} is {major}"
            return 2
        (site / "slop").mkdir()
        (site / "clean").mkdir()
        (site / "slop/index.html").write_text(SLOP, encoding="utf-8")
        (site / "clean/index.html").write_text(CLEAN, encoding="utf-8")
        fx_sig = tree_hash(site)
        hfile = hist / "history.json"
        extra = {"TMPDIR": str(ntmp), "TASTE_SKILL_TMP": str(ttmp), "TASTE_SKILL_HISTORY": str(hfile),
                 "XDG_CONFIG_HOME": str(xdg), "XDG_CACHE_HOME": str(cache), "XDG_DATA_HOME": str(data),
                 "CHROME_PATH": chrome}
        scripts = skill / "scripts"

        def run(args, tag, where=site):
            return iso([node, *args], tag, home=str(home), cwd=str(where), path=SYS_PATH, extra=extra,
                       bwrap_writable=[tdn])

        front = (skill / "SKILL.md").read_text(encoding="utf-8", errors="replace").split("---")
        checks["skill_frontmatter_name"] = len(front) > 2 and "name: design-taste-frontend" in front[1]
        slop = run([str(scripts / "lint.mjs"), "slop", "--json"], "lint slop")
        clean = run([str(scripts / "lint.mjs"), "clean", "--json"], "lint clean")
        missing = run([str(scripts / "lint.mjs"), "no-such-dir", "--json"], "lint missing")
        so, co = as_json(slop), as_json(clean)
        r["lint"] = {"slop_rc": slop.returncode, "slop_ids": sorted(x for x in finding_ids(so) if x),
                     "clean_rc": clean.returncode, "clean_ids": sorted(x for x in finding_ids(co) if x),
                     "missing_rc": missing.returncode}
        checks["lint_slop_fails"] = slop.returncode == 1 and LINT_WANT <= finding_ids(so)
        checks["lint_clean_passes"] = clean.returncode == 0 and isinstance(co, dict) and co.get("findings") == []
        checks["lint_missing_exit_2"] = missing.returncode == 2
        brief = ["--sector", "dev-tool", "--brief", "local agent harness", "--seed", "7"]
        m1 = run([str(scripts / "draw.mjs"), *brief, "--options", "3"], "draw options 1", cwd)
        m2 = run([str(scripts / "draw.mjs"), *brief, "--options", "3"], "draw options 2", cwd)
        checks["draw_menu_deterministic"] = m1.returncode == 0 and m2.returncode == 0 and len(m1.stdout) > 200 \
            and m1.stdout == m2.stdout
        checks["draw_menu_writes_nothing"] = not files_under(cwd) and not hfile.exists()
        full = run([str(scripts / "draw.mjs"), *brief, "--out", str(out / "direction")], "draw full", cwd)
        dj = out / "direction/direction.json"
        try:
            dobj = json.loads(dj.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            dobj = None
        r["draw"] = {"rc": full.returncode, "sheet_head": full.stdout[:200], "out_files": files_under(out)}
        checks["draw_writes_direction"] = full.returncode == 0 and isinstance(dobj, dict) and \
            "DIRECTION SHEET" in full.stdout
        checks["draw_history_in_temp"] = hfile.is_file()
        ins_out = out / "inspect"
        ins = run([str(scripts / "inspect.mjs"), "slop/index.html", "--out", str(ins_out), "--widths", "1024",
                   "--json"], "inspect slop")
        io_ = as_json(ins)
        shots = [x for x in files_under(ins_out) if x.endswith(".jpg")]
        r["inspect"] = {"rc": ins.returncode, "fail_ids": sorted(x for x in finding_ids(io_, "FAIL") if x),
                        "shots": shots, "tail": "" if isinstance(io_, dict) else (ins.stdout + ins.stderr)[-600:]}
        checks["inspect_fails_slop"] = ins.returncode == 1 and INSPECT_WANT <= finding_ids(io_, "FAIL")
        checks["inspect_screenshot"] = bool(shots)
        left = sorted(x.name for x in ttmp.iterdir() if x.name.startswith("ad-chrome-"))
        r["profiles_left"] = left
        checks["no_profile_left"] = not left
        checks["fixtures_untouched"] = tree_hash(site) == fx_sig
        rel = sorted(str(p.relative_to(home)) for p in home.rglob("*"))
        r["home_files"] = rel[:20]
        checks["home_only_chrome_leftovers"] = all(chrome_leftover(x) for x in rel)
    r["_ok_reason"] = ("lint flags the slop fixture and passes the clean one, missing path exits 2; seeded draw menu "
                       "deterministic and write-free; full draw writes direction.json and history only to temp; "
                       "headless Chrome inspect fails the slop page with screenshots, no profile left; watched "
                       f"real-HOME dir ({watch_dirs('taste-skill')}) unchanged")
    return None


# ---------------------------------------------------------------- gitai
MAKE_SHIM = r'''#!/bin/sh
# pfy smoke: the binaries are prebuilt; accept only `make -C <repo> build` and do nothing.
[ "$1" = "-C" ] && [ "$2" = __REPO__ ] && [ "$3" = "build" ] && [ "$#" = 3 ] && exit 0
echo "pfy make shim: refusing $*" >&2
exit 97
'''


def smoke_gitai(r: dict) -> int:
    d = Path(os.environ.get("GITAI_DIR") or TMP / "gitai")
    r["dir"] = str(d)
    script = d / "examples/graft/quickstart.sh"
    missing = [b for b in GITAI_BINS if not os.access(d / "_build/bin" / b, os.X_OK)]
    if not script.is_file() or not (d / ".git").exists():
        r["reason"] = ("gitai not found ($GITAI_DIR or tmp/gitai as a `git clone --branch v0.3.1` of "
                       "github.com/feder-cr/git-ai); see the handoff")
        return 2
    if missing:
        r["reason"] = (f"gitai is not built: missing _build/bin/{', '.join(missing)}. Run `make build` in {d} by hand "
                       "(needs Go 1.26, make, meson, ninja and the bundled-Git build deps); the smoke never builds")
        return 2
    need = {n: shutil.which(n, path=SYS_PATH) for n in ("git", "openssl", "bash")}
    if not all(need.values()):
        r["reason"] = f"{', '.join(n for n, v in need.items() if not v)} needed in {SYS_PATH}"
        return 2
    want = pinned(r, "GITAI_COMMIT", GITAI_PIN, lower=True)
    want_v = pinned(r, "GITAI_VERSION", GITAI_VERSION)
    return watched("gitai", lambda rr, checks: _gitai(rr, need, d, script, want, want_v, checks), r)


def _gitai(r: dict, need: dict, d: Path, script: Path, want: str, want_v: str, checks: dict) -> int | None:
    with tempfile.TemporaryDirectory(prefix="pfy-gitai-") as tdn:
        td = Path(tdn)
        home, work, shim, ntmp = td / "home", td / "work", td / "shim", td / "tmp"
        for p in (home, work, shim, ntmp):
            p.mkdir()
        head = git_head(need["git"], d, str(home), tdn)
        r["commit"] = head
        if head.lower() != want:
            r["reason"] = f"gitai HEAD is {head!r}, not {want} (set $GITAI_COMMIT)"
            return 2
        gv = iso([str(d / "_build/bin/gitaly"), "--version"], "gitaly --version", home=str(home), cwd=tdn,
                 path=SYS_PATH, bwrap_writable=[tdn])
        first = (gv.stdout.strip().splitlines() or [""])[0].strip()
        r["gitaly_version"] = first[:200]
        if gv.returncode != 0 or first != f"Gitaly, version {want_v}":
            r["reason"] = (f"_build/bin/gitaly --version is {first!r} (exit {gv.returncode}), not 'Gitaly, version "
                           f"{want_v}'; rebuild at the v{want_v} tag by hand (set $GITAI_VERSION)")
            return 2
        (shim / "make").write_text(MAKE_SHIM.replace("__REPO__", shlex.quote(str(d))), encoding="utf-8")
        (shim / "make").chmod(0o755)
        gitx = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "TMPDIR": str(ntmp)}
        p = iso([need["bash"], str(script), str(work)], "graft quickstart", home=str(home), cwd=tdn,
                path=f"{shim}:{SYS_PATH}", extra=gitx, bwrap_writable=[tdn])
        r["rc"], r["tail"] = p.returncode, (p.stdout + p.stderr)[-1200:]

        def show(ref: str) -> str:
            q = iso([need["git"], "--git-dir", str(work / "repos/demo.git"), "show", ref], f"git show {ref}",
                    home=str(home), cwd=tdn, path=SYS_PATH, extra=gitx, bwrap_writable=[tdn])
            return q.stdout if q.returncode == 0 else ""
        main_readme = show("main:README.md")
        r["main_readme"] = main_readme[:200]
        checks["quickstart_exit_0"] = p.returncode == 0
        checks["policy_denied_builder"] = "denied as expected" in p.stdout
        checks["planner_landed_on_main"] = "hello graft" in main_readme and "nope" not in main_readme
        checks["builder_landed_feature"] = show("feature/demo:feature.txt").strip() == "feature"
        checks["home_untouched"] = not any(home.iterdir())
    r["_ok_reason"] = ("standalone Gitaly + graft-cache from the repo's quickstart: planner landed on main, builder "
                       "landed feature/demo and was denied on main by policy; temp HOME and the watched real-HOME "
                       f"dirs ({watch_dirs('gitai')}) unchanged")
    return None


# ---------------------------------------------------------------- muxin
MUXIN_DRIVER = MCP_CLIENT + r'''
spec = json.load(open(sys.argv[1]))
out = {}
m = Mcp([spec["muxin"], "mcp", "--demo"], spec["cwd"])
try:
    out["server"] = m.init()
    tl = (m.req("tools/list").get("result") or {}).get("tools", [])
    out["tools"] = {t["name"]: {k: v for k, v in (t.get("annotations") or {}).items() if k.endswith("Hint")}
                    for t in tl}
    out["status"] = m.call("status", {})
    out["forge"] = m.call("get_machine", {"machine_id": "forge"})
    out["unknown"] = m.call("get_machine", {"machine_id": "no-such-machine"})
    out["badarg"] = m.call("get_machine", {"machine": "forge"})
    out["run"] = m.call("run_on_machines", {"command": "uname -a", "machine_ids": ["forge"], "wait": True})
except Exception as e:
    out["error"] = str(e)[:600]
finally:
    out["stopped"] = m.stop()
print(json.dumps(out))
'''


def smoke_muxin(r: dict) -> int:
    bad = bad_override("MUXIN_BIN")
    if bad:
        r["reason"] = bad
        return 2
    mux = find_bin("MUXIN_BIN", "muxin/Muxin/muxin", "muxin")
    r["muxin"] = mux
    if not mux:
        r["reason"] = ("muxin not found ($MUXIN_BIN, tmp/muxin/Muxin/muxin, PATH); unpack the v0.6.0 linux-x86_64 "
                       "release tarball there after checking SHA256SUMS.txt, see the handoff. Never run its install.sh")
        return 2
    lib = os.environ.get("MUXIN_LIB_DIR")
    if lib and not os.path.isdir(lib):
        r["reason"] = f"$MUXIN_LIB_DIR is set to {lib!r}, which is not a directory"
        return 2
    python = system_python()
    if not python:
        r["reason"] = f"python3 is needed in {SYS_PATH} for the MCP driver"
        return 2
    want_sha = pinned(r, "MUXIN_SHA256", MUXIN_SHA, lower=True)
    have_sha = sha256_file(Path(mux))
    r["sha256"] = have_sha
    if have_sha != want_sha:
        r["reason"] = f"muxin binary sha256 is {have_sha}, not {want_sha} (set $MUXIN_SHA256)"
        return 2
    want = pinned(r, "MUXIN_VERSION", MUXIN_PIN)
    return watched("muxin", lambda rr, checks: _muxin(rr, mux, python, lib, want, checks), r)


def _muxin(r: dict, mux: str, python: str, lib: str | None, want: str, checks: dict) -> int | None:
    with tempfile.TemporaryDirectory(prefix="pfy-muxin-") as tdn:
        td = Path(tdn)
        home, mhome, state, xdg, ntmp, cwd = (td / n for n in ("home", "mhome", "state", "xdg", "tmp", "cwd"))
        for p in (home, state, xdg, ntmp, cwd):
            p.mkdir()
        extra = {"MUXIN_HOME": str(mhome), "XDG_STATE_HOME": str(state), "XDG_CONFIG_HOME": str(xdg),
                 "TMPDIR": str(ntmp), "PYTHONDONTWRITEBYTECODE": "1"}
        if lib:
            extra["LD_LIBRARY_PATH"] = lib

        def run(args, tag):
            return iso([mux, *args], tag, home=str(home), cwd=str(cwd), path=SYS_PATH, extra=extra,
                       bwrap_writable=[tdn])
        v = run(["--version"], "muxin --version")
        r["version_out"] = (v.stdout + v.stderr).strip()[:200]
        if v.returncode != 0:
            r["reason"] = f"muxin --version exited {v.returncode} (missing X libraries? set $MUXIN_LIB_DIR)"
            return 2
        if v.stdout.strip() != f"muxin {want}":
            r["reason"] = f"muxin --version is {v.stdout.strip()!r}, not muxin {want} (set $MUXIN_VERSION)"
            return 2
        paths = run(["paths"], "muxin paths")
        lines = [ln[ln.index("/"):].strip() for ln in paths.stdout.splitlines() if "/" in ln]
        r["paths"] = lines
        checks["paths_under_muxin_home"] = paths.returncode == 0 and len(lines) >= 3 and all(
            ln.startswith(str(mhome)) for ln in lines)
        ms = run(["machines", "--demo", "--json"], "muxin machines")
        mo = as_json(ms)
        ids = sorted(x.get("id") for x in mo) if isinstance(mo, list) else None
        r["demo_machines"] = ids
        checks["demo_machines_exact"] = ms.returncode == 0 and ids == DEMO_MACHINES
        drv, spec = td / "driver.py", td / "spec.json"
        drv.write_text(MUXIN_DRIVER, encoding="utf-8")
        spec.write_text(json.dumps({"muxin": mux, "cwd": str(cwd)}), encoding="utf-8")
        p = iso([python, str(drv), str(spec)], "muxin mcp driver", home=str(home), cwd=tdn, path=SYS_PATH,
                extra=extra, bwrap_writable=[tdn])
        o = as_json(p)
        if not isinstance(o, dict) or o.get("error"):
            r["driver_rc"] = p.returncode
            r["driver_tail"] = str((o or {}).get("error") if isinstance(o, dict) else (p.stdout + p.stderr).strip())[-800:]
            checks["driver_report"] = False
            return None
        tools = o.get("tools") or {}
        txt = {k: json.dumps((o.get(k) or {}).get("body")) for k in ("status", "forge", "unknown", "badarg", "run")}
        r["server"], r["stopped"] = o.get("server"), o.get("stopped")
        r["tool_count"] = len(tools)
        r["destructive"] = sorted(k for k, a in tools.items() if a.get("destructiveHint"))
        r["results"] = {k: t[:300] for k, t in txt.items()}
        checks["server_pinned"] = (o.get("server") or {}).get("name") == "muxin" and \
            (o.get("server") or {}).get("version") == want
        checks["tools_listed"] = len(tools) >= 80
        checks["destructive_marked"] = all((tools.get(t) or {}).get("destructiveHint") for t in
                                           ("run_on_machines", "cloud_destroy"))
        checks["status_read_only"] = (tools.get("status") or {}).get("readOnlyHint") is True
        checks["status_summary"] = "9 machines" in txt["status"]
        checks["get_machine_forge"] = "forge" in txt["forge"].lower() and "not_found" not in txt["forge"]
        checks["unknown_not_found"] = "not_found" in txt["unknown"] and "forge" in txt["unknown"]
        checks["bad_arg_invalid"] = "invalid" in txt["badarg"]
        checks["demo_run_succeeded"] = "succeeded" in txt["run"]
        checks["stopped_on_eof"] = o.get("stopped") == "eof"
        r["home_files"] = sorted(str(x.relative_to(home)) for x in home.rglob("*"))[:20]
        r["state_files"] = files_under(state)
        checks["home_untouched"] = not any(home.iterdir())
    r["_ok_reason"] = (f"v{want} at the pinned sha; paths under MUXIN_HOME; 9 demo machines; MCP over stdio with "
                       f"{r.get('tool_count')} tools and destructive ones marked; status, get_machine, not_found, invalid "
                       "and a demo run_on_machines all as expected; exit on EOF; temp HOME and the watched real-HOME "
                       f"dirs ({watch_dirs('muxin')}) unchanged")
    return None


ENTRIES = {"taste-skill": smoke_taste, "gitai": smoke_gitai, "muxin": smoke_muxin}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", required=True, choices=list(ENTRIES))
    a = ap.parse_args()
    receipt = {"entry": a.entry, "script": "examples/x-intake-local/smoke_143_145.py",
               "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    bad = timeout_problem()
    if bad:
        receipt["reason"] = bad
        return write(a.entry, receipt, 2)
    try:
        code = ENTRIES[a.entry](receipt)
    except Exception as e:
        receipt.pop("_ok_reason", None)
        receipt["reason"] = str(e) if isinstance(e, TimeoutError) else f"unexpected {type(e).__name__}: {e}"
        if receipt.get("checks", {}).get("real_home_untouched") is False:
            receipt["reason"] += f"; {home_note(a.entry, receipt)}"
        code = 1
    return write(a.entry, receipt, code)


if __name__ == "__main__":
    sys.exit(main())
