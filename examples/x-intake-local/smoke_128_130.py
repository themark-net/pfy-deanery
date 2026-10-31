#!/usr/bin/env python3
"""Operate-or-FAIL smokes for X intake Entries 128-130 (Harness Score, OpenLore; hal0 is catalog-only). Stdlib only.

Usage: python3 examples/x-intake-local/smoke_128_130.py --entry harnessscore|openlore

Same contract and receipts as smoke.py next to it (whose helpers it reuses): exit 0 = PASS, 1 = the tool ran but
the check failed, 2 = can't run here (prereq missing; reason recorded). Writes pipelines/smoke/<entry>/latest.json.
Never installs or downloads anything. Every child process starts through `run_isolated` in smoke.py (fresh temp HOME,
env limited to PATH/HOME/TERM/LANG/NO_COLOR plus the variables named below; nothing copied from this process, so no
provider key is ever seen; a timeout SIGKILLs the process group) under bwrap with no network when bwrap works.
No smoke calls a model, adds a key, runs an `install`/`connect`/`setup` command or starts an agent CLI.
PFY_XINTAKE_TIMEOUT (float seconds, > 0) overrides the 600s per-command timeout.
Real HOME: each entry fingerprints the real-HOME dirs the tool could write (harnessscore: ~/.harness-score,
~/.config/harness-score, precautionary, upstream says it writes nothing; openlore: ~/.openlore, which holds its update
check, token descriptors and local embedding models, and ~/.pi/agent/extensions) with home_sig() before the run and
again in a finally, also on timeout or a crash. A created, deleted or renamed entry, or a change to any entry's type,
permission bits, mtime, size, content or symlink target, sets checks.real_home_untouched false, lists the dirs in
real_home_changed and FAILs (exit 1), even when bwrap is unavailable. Only those dirs are watched: a write elsewhere in
HOME (e.g. ~/.newdot) is not seen. checks.body_completed is false and `exception` names it when the run raised.

  harnessscore  Node >= 18 ($NODE_BIN, ~/DEVELOP/pfy-mentat/tmp/node/bin/node, or PATH) and the unpacked npm tarball
                harness-score-1.8.2.tgz: $HARNESS_SCORE_DIR, else ~/DEVELOP/pfy-mentat/tmp/harness-score/package
                (holding dist/cli.js; package.json version pinned to 1.8.2, $HARNESS_SCORE_VERSION overrides). Builds
                two fixture repos in the temp dir: "clean" (substantive AGENTS.md, .gitignore covering .env) and
                "leaky" (same AGENTS.md, a .gitignore without .env, and a placeholder .env file). `--json clean` must
                report tool.version = the pin, CTX-01 and HYG-03 passed, and be byte-identical on a second run
                (determinism); `--json leaky` must fail HYG-02 and HYG-03; `--min-level 4 clean` must exit 1 (the CI
                gate); fixtures unchanged, temp HOME empty.
  openlore      Node >= 22.19 ($NODE_BIN, ~/DEVELOP/pfy-mentat/tmp/node/bin/node, or PATH; ~/DEVELOP/pfy-mentat/tmp/node
                is where a Node 22 tarball would be unpacked) and an npm prefix holding node_modules/openlore:
                $OPENLORE_DIR, else ~/DEVELOP/pfy-mentat/tmp/openlore (`npm install --prefix <it> --ignore-scripts
                openlore@3.3.1`; package.json version pinned to 3.3.1, $OPENLORE_VERSION overrides). Needs git. In a
                temp git repo with src/pricing.ts (exported applyDiscount) and src/checkout.ts (calls it), with
                TMPDIR inside the temp dir (its index panics on a read-only /tmp) and OPENLORE_NO_UPDATE_NOTIFIER=1
                (otherwise it asks registry.npmjs.org for updates): `init` and `analyze` exit 0; `orient --json`
                must rank applyDiscount first; after adding a required parameter to applyDiscount,
                `certify-public-surface --base HEAD --json` must say "breaking" with checkout as the consumer; after
                restoring the file it must say "non-breaking" (no false positive). Only the .gitignore that `init`
                writes may show in `git status`; temp HOME empty.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from smoke import TMP, find_bin, pinned, run_isolated, timeout_reason, write
from smoke_122_124 import tree_sig

HS_PIN = "1.8.2"
OL_PIN = "3.3.1"
SYS_PATH = "/usr/local/bin:/usr/bin:/bin"
GIT_ID = {"GIT_AUTHOR_NAME": "pfy-smoke", "GIT_AUTHOR_EMAIL": "smoke@localhost",
          "GIT_COMMITTER_NAME": "pfy-smoke", "GIT_COMMITTER_EMAIL": "smoke@localhost"}
WATCH = {"harnessscore": (".harness-score", ".config/harness-score"),
         "openlore": (".openlore", ".pi/agent/extensions")}
AGENTS_MD = """# Fixture project

A tiny Python package used by the pfy-mentat Harness Score smoke.

## Build and test

- Run `python3 -m pytest` before every commit.
- Lint with `ruff check .` and type-check with `mypy src`.

## Do not touch

- Never edit `vendor/`. Never commit `.env` files or keys.

## Conventions

Use type hints. Keep functions short. Every bug fix gets a regression test first.
"""
PRICING = "export function applyDiscount(total: number, pct: number): number {\n  return total - (total * pct) / 100;\n}\n"
PRICING_BROKEN = ("export function applyDiscount(total: number, pct: number, cap: number): number {\n"
                  "  return Math.min(cap, total - (total * pct) / 100);\n}\n")
CHECKOUT = ('import { applyDiscount } from "./pricing";\n'
            "export function checkout(total: number): number {\n  return applyDiscount(total, 10);\n}\n")


def tmo() -> float:
    try:
        v = float(os.environ.get("PFY_XINTAKE_TIMEOUT", ""))
        return v if v > 0 else 600.0
    except ValueError:
        return 600.0


def iso(argv: list[str], tag: str, **kw) -> subprocess.CompletedProcess:
    try:
        return run_isolated(argv, timeout=tmo(), **kw)
    except subprocess.TimeoutExpired as e:
        raise TimeoutError(timeout_reason(tag, float(e.timeout)))


def finish(r: dict, checks: dict, ok_reason: str) -> int:
    r["checks"] = checks
    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        r["reason"] = f"failed checks: {', '.join(failed)}"
        return 1
    r["reason"] = ok_reason
    return 0


def watch_dirs(entry: str) -> str:
    return ", ".join("~/" + d for d in WATCH[entry])


def home_note(entry: str, r: dict) -> str:
    return f"real HOME {', '.join(r.get('real_home_changed') or ['~/' + d for d in WATCH[entry]])} changed"


def home_sig(p: Path) -> str | None:
    """Real-HOME fingerprint of p, or None when p doesn't exist. Stricter than smoke_122_124.tree_sig (which records
    permission bits and symlink readlink, including when the path itself is a symlink, and still does not record
    mtime): one line per entry, p included, with path, file type, permission bits and mtime_ns, plus size
    and content hash for a regular file, or size and inode when it can't be read (a rewrite still shows in size, mtime
    or inode), and the target string for a symlink. Symlinks below p are never followed; a symlinked p is recorded as
    a link and then its target is walked."""
    try:
        p.lstat()
    except FileNotFoundError:
        return None
    h = hashlib.sha256()
    if p.is_symlink():
        h.update(f"{p}:root-link:{os.readlink(p)}\n".encode())
        p = Path(os.path.realpath(p))
    _sig_walk(p, h)
    return h.hexdigest()


def _sig_walk(f: Path, h) -> None:
    try:
        st = f.lstat()
    except OSError as e:
        h.update(f"{f}:lstat-error:{e.errno}\n".encode())
        return
    head = f"{f}:{stat.S_IFMT(st.st_mode):o}:{stat.S_IMODE(st.st_mode):o}:{st.st_mtime_ns}"
    if stat.S_ISLNK(st.st_mode):
        h.update(f"{head}:link:{os.readlink(f)}\n".encode())
    elif stat.S_ISDIR(st.st_mode):
        h.update(f"{head}:dir\n".encode())
        try:
            names = sorted(os.listdir(f))
        except OSError:
            h.update(f"{f}:unlistable\n".encode())
            return
        for n in names:
            _sig_walk(f / n, h)
    elif stat.S_ISREG(st.st_mode):
        try:
            fh = hashlib.sha256()
            with f.open("rb") as fp:  # streamed in 1 MiB chunks, so a huge file doesn't load into RAM
                for chunk in iter(lambda: fp.read(1 << 20), b""):
                    fh.update(chunk)
            h.update(f"{head}:{st.st_size}:{fh.hexdigest()}\n".encode())
        except OSError:
            h.update(f"{head}:{st.st_size}:unreadable:{st.st_ino}\n".encode())
    else:
        h.update(f"{head}:other:{st.st_size}\n".encode())


def watched(entry: str, body, r: dict) -> int:
    """Run body(r, checks) with the real HOME watched; the finally runs on timeout and on any exception too."""
    real_home = Path.home()
    before = {d: home_sig(real_home / d) for d in WATCH[entry]}
    checks: dict[str, bool] = {}
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


def node_version(node: str, home: str, cwd: str) -> tuple[int, ...] | None:
    v = iso([node, "--version"], "node version", home=home, cwd=cwd, path=SYS_PATH, bwrap_writable=[cwd])
    m = re.match(r"v(\d+)\.(\d+)\.(\d+)", v.stdout.strip())
    return tuple(int(x) for x in m.groups()) if m else None


def pkg_version(p: Path) -> str:
    try:
        return str(json.loads(p.read_text(encoding="utf-8")).get("version", ""))
    except (OSError, ValueError):
        return ""


def as_json(cp: subprocess.CompletedProcess):
    try:
        return json.loads(cp.stdout)
    except ValueError:
        return None


# ---------------------------------------------------------------- harnessscore
def smoke_harnessscore(r: dict) -> int:
    node = find_bin("NODE_BIN", "node/bin/node", "node")
    if not node:
        r["reason"] = "node not found ($NODE_BIN, tmp/node/bin/node, PATH)"
        return 2
    pkg = Path(os.environ.get("HARNESS_SCORE_DIR") or (TMP / "harness-score" / "package"))
    cli = pkg / "dist" / "cli.js"
    r["node"], r["cli"] = node, str(cli)
    if not cli.is_file():
        r["reason"] = f"harness-score not staged ({cli} missing); unpack harness-score-{HS_PIN}.tgz, see the handoff"
        return 2
    want = pinned(r, "HARNESS_SCORE_VERSION", HS_PIN)
    have = pkg_version(pkg / "package.json")
    r["package_version"] = have
    if have != want:
        r["reason"] = f"harness-score package.json version is {have!r}, not {want} (set $HARNESS_SCORE_VERSION)"
        return 2
    return watched("harnessscore", lambda rr, checks: _harnessscore(rr, node, cli, want, checks), r)


def _harnessscore(r: dict, node: str, cli: Path, want: str, checks: dict) -> int | None:
    with tempfile.TemporaryDirectory(prefix="pfy-harnessscore-") as td:
        home, clean, leaky = Path(td, "home"), Path(td, "clean"), Path(td, "leaky")
        for d in (home, clean, leaky):
            d.mkdir()
        kw = {"home": str(home), "cwd": td, "path": SYS_PATH, "bwrap_writable": [td]}
        nv = node_version(node, str(home), td)
        r["node_version"] = ".".join(map(str, nv)) if nv else None
        if not nv or nv < (18,):
            r["reason"] = f"harness-score needs node >= 18, found {r['node_version']}"
            return 2
        for d in (clean, leaky):
            (d / "AGENTS.md").write_text(AGENTS_MD)
        (clean / ".gitignore").write_text(".env\n__pycache__/\n")
        (leaky / ".gitignore").write_text("__pycache__/\n")
        (leaky / ".env").write_text("PFY_SMOKE_PLACEHOLDER=not-a-real-value\n")
        sig_before = {d.name: tree_sig(d) for d in (clean, leaky)}
        a = iso([node, str(cli), "--json", str(clean)], "harness-score clean", **kw)
        b = iso([node, str(cli), "--json", str(clean)], "harness-score clean rerun", **kw)
        lk = iso([node, str(cli), "--json", str(leaky)], "harness-score leaky", **kw)
        gate = iso([node, str(cli), "--min-level", "4", str(clean)], "harness-score gate", **kw)
        ja, jl = as_json(a), as_json(lk)
        r["rc"] = {"clean": a.returncode, "rerun": b.returncode, "leaky": lk.returncode, "gate": gate.returncode}
        if not isinstance(ja, dict) or not isinstance(jl, dict):
            r["output_tail"] = (a.stdout + a.stderr + lk.stdout + lk.stderr).strip()[-600:]
            checks["json_reports"] = False
            return None
        ca = {c.get("id"): c.get("passed") for c in ja.get("checks", [])}
        cl = {c.get("id"): c.get("passed") for c in jl.get("checks", [])}
        r["clean"] = {"level": (ja.get("level") or {}).get("name"), "score": ja.get("score"),
                      "CTX-01": ca.get("CTX-01"), "HYG-02": ca.get("HYG-02"), "HYG-03": ca.get("HYG-03")}
        r["leaky"] = {"score": jl.get("score"), "HYG-02": cl.get("HYG-02"), "HYG-03": cl.get("HYG-03")}
        checks["clean_exit_0"] = a.returncode == 0
        checks["tool_version_pinned"] = (ja.get("tool") or {}).get("version") == want
        checks["clean_agents_md_found"] = ca.get("CTX-01") is True
        checks["clean_env_protected"] = ca.get("HYG-03") is True
        checks["deterministic_rerun"] = b.returncode == 0 and a.stdout == b.stdout
        checks["leaky_env_unignored_flagged"] = cl.get("HYG-02") is False
        checks["leaky_env_file_flagged"] = cl.get("HYG-03") is False
        checks["gate_below_min_level_exit_1"] = gate.returncode == 1
        checks["fixtures_untouched"] = {d.name: tree_sig(d) for d in (clean, leaky)} == sig_before
        checks["home_untouched"] = not any(home.iterdir())
    r["_ok_reason"] = ("offline scan: AGENTS.md and protected .env seen, unignored .env flagged, rerun byte-identical, "
                       "--min-level gate exits 1; fixtures, temp HOME and the watched real-HOME dirs "
                       f"({watch_dirs('harnessscore')}) unchanged")
    return None


# ---------------------------------------------------------------- openlore
def smoke_openlore(r: dict) -> int:
    node = find_bin("NODE_BIN", "node/bin/node", "node")
    if not node:
        r["reason"] = "node not found ($NODE_BIN, tmp/node/bin/node, PATH)"
        return 2
    prefix = Path(os.environ.get("OPENLORE_DIR") or (TMP / "openlore"))
    pkg = prefix / "node_modules" / "openlore"
    cli = pkg / "dist" / "cli" / "index.js"
    r["node"], r["cli"] = node, str(cli)
    if not cli.is_file():
        r["reason"] = f"OpenLore not staged ({cli} missing); see the handoff"
        return 2
    want = pinned(r, "OPENLORE_VERSION", OL_PIN)
    have = pkg_version(pkg / "package.json")
    r["package_version"] = have
    if have != want:
        r["reason"] = f"openlore package.json version is {have!r}, not {want} (set $OPENLORE_VERSION)"
        return 2
    git = shutil.which("git", path=SYS_PATH)
    if not git:
        r["reason"] = f"git not found in {SYS_PATH}"
        return 2
    return watched("openlore", lambda rr, checks: _openlore(rr, node, cli, git, checks), r)


def _openlore(r: dict, node: str, cli: Path, git: str, checks: dict) -> int | None:
    with tempfile.TemporaryDirectory(prefix="pfy-openlore-") as td:
        home, tmpd, proj = Path(td, "home"), Path(td, "tmp"), Path(td, "proj")
        for d in (home, tmpd, proj / "src"):
            d.mkdir(parents=True)
        extra = {"TMPDIR": str(tmpd), "OPENLORE_NO_UPDATE_NOTIFIER": "1", "NO_UPDATE_NOTIFIER": "1"}
        kw = {"home": str(home), "cwd": str(proj), "path": SYS_PATH, "extra": extra, "bwrap_writable": [td]}
        nv = node_version(node, str(home), td)
        r["node_version"] = ".".join(map(str, nv)) if nv else None
        if not nv or not ((22, 19) <= nv[:2] < (23, 0) or nv >= (23, 5)):
            r["reason"] = f"OpenLore {OL_PIN} needs node ^22.19.0 or >= 23.5.0, found {r['node_version']}"
            return 2
        (proj / "src" / "pricing.ts").write_text(PRICING)
        (proj / "src" / "checkout.ts").write_text(CHECKOUT)
        (proj / "package.json").write_text('{"name": "pfy-openlore-fixture", "version": "0.0.0"}\n')
        for argv in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "init"]):
            g = iso([git, "-C", str(proj), *argv], "git " + argv[0], **{**kw, "extra": {**extra, **GIT_ID}})
            if g.returncode != 0:
                r["reason"] = f"could not build the temp git repo: {(g.stdout + g.stderr).strip()[:160]}"
                return 1
        ol = [node, str(cli)]
        for step in ("init", "analyze"):
            s = iso(ol + [step, "-q"], f"openlore {step}", **kw)
            checks[f"{step}_exit_0"] = s.returncode == 0
            if s.returncode != 0:
                r[f"{step}_tail"] = (s.stdout + s.stderr).strip().splitlines()[-4:]
                return None
        o = as_json(iso(ol + ["orient", "change the discount calculation", "--json"], "openlore orient", **kw))
        names = [f.get("name") for f in (o or {}).get("relevantFunctions", [])] if isinstance(o, dict) else []
        r["orient_functions"] = names[:5]
        if isinstance(o, dict) and "error" in o:
            r["orient_error"] = str(o.get("error"))[:200]  # e.g. "No analysis found": analyze exits 0 even then
        checks["orient_ranks_applyDiscount_first"] = names[:1] == ["applyDiscount"]
        (proj / "src" / "pricing.ts").write_text(PRICING_BROKEN)
        brk = as_json(iso(ol + ["certify-public-surface", "--base", "HEAD", "--json"], "openlore certify (broken)", **kw))
        brk = brk if isinstance(brk, dict) else {}
        hits = [b for b in brk.get("breaking", []) if b.get("name") == "applyDiscount"]
        consumers = [c.get("name") for c in (hits[0].get("consumers") or [])] if hits else []
        r["broken"] = {"overall": brk.get("overall"), "consumers": consumers,
                       "reasons": hits[0].get("reasons") if hits else None}
        checks["breaking_change_flagged"] = brk.get("overall") == "breaking" and bool(hits)
        checks["breaking_names_consumer_checkout"] = "checkout" in consumers
        rs = iso([git, "-C", str(proj), "checkout", "-q", "--", "src/pricing.ts"], "git checkout", **kw)
        ok = as_json(iso(ol + ["certify-public-surface", "--base", "HEAD", "--json"], "openlore certify (clean)", **kw))
        ok = ok if isinstance(ok, dict) else {}
        r["restored_overall"] = ok.get("overall")
        checks["restored_is_non_breaking"] = rs.returncode == 0 and ok.get("overall") == "non-breaking"
        st = iso([git, "-C", str(proj), "status", "--porcelain"], "git status", **kw)
        r["git_status"] = st.stdout.strip().splitlines()[:10]
        checks["repo_only_gains_gitignore"] = st.returncode == 0 and set(st.stdout.split("\n")) <= {"?? .gitignore", ""}
        checks["home_untouched"] = not any(home.iterdir())
    r["_ok_reason"] = ("offline index of a temp TS repo: orient ranked applyDiscount first; an added required parameter "
                       "was flagged breaking with checkout as consumer; the restored file was non-breaking; temp HOME "
                       f"and the watched real-HOME dirs ({watch_dirs('openlore')}) unchanged")
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", required=True, choices=["harnessscore", "openlore"])
    a = ap.parse_args()
    receipt = {"entry": a.entry, "script": "examples/x-intake-local/smoke_128_130.py",
               "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    fn = {"harnessscore": smoke_harnessscore, "openlore": smoke_openlore}[a.entry]
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
