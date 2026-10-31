#!/usr/bin/env python3
"""Operate-or-FAIL smokes for X intake Entries 112-114 (Overtime, Festival, Sloptrim). Stdlib only.

Usage: python3 examples/x-intake-local/smoke_112_114.py --entry overtime|festival|sloptrim

Same contract and receipts as smoke.py next to it: exit 0 = PASS, 1 = the tool ran but the check failed, 2 = can't
run here (prereq missing; reason recorded). Writes pipelines/smoke/<entry>/latest.json. Never installs anything;
scratch goes to a fresh tempfile directory that is removed. Every child, including the bwrap probe, `node --version`,
sloptrim's `git rev-parse`, tool commands, and overtime `daemon stop`, goes through smoke.run_isolated. That helper
uses a fresh temp HOME and an env limited to PATH, HOME, TERM, LANG, and NO_COLOR, plus only the variables this
smoke passes in `extra`. Festival passes GIT_AUTHOR_NAME, GIT_AUTHOR_EMAIL, GIT_COMMITTER_NAME, and
GIT_COMMITTER_EMAIL so `camp create` can commit. No smoke calls a model. The parent environment is not copied.
PFY_XINTAKE_TIMEOUT (float seconds, > 0) overrides the 120s per-command timeout and, when it is smaller than 10s,
the `node --version` probe. Each child is a new session; on timeout run_isolated SIGKILLs that process group,
including a forked grandchild.

When bubblewrap (`bwrap`) accepts the probe, festival and sloptrim run with a read-only root, only the temp HOME
and scratch dir writable, and no network. The prefix includes `--unshare-pid` when that probe works. Overtime
starts a detached background daemon, so it passes no bwrap prefix. `overtime daemon stop` runs in a finally. The
smoke checks that the real HOME's ~/overtime was not created or changed even when a command times out, and that
`daemon stop` leaves no daemon behind. The receipt records the mode (`containment`).

  overtime  $OVERTIME_DIR, then ~/DEVELOP/pfy-mentat/tmp/overtime (an `npm install --prefix <dir> --ignore-scripts
            @ukanwat/overtime@0.5.3`), package version pinned ($OVERTIME_VERSION overrides). Node >= 22.19 from
            $OVERTIME_NODE, ~/DEVELOP/pfy-mentat/tmp/overtime/node/bin/node, or PATH; older Node exits 2. In a temp
            HOME: `new` creates the agent folder (AGENT.md + .overtime/settings.json + state.json), `ls` lists it,
            `set budget=1 protect=<dir>` lands in .overtime/settings.json and `settings` shows it, the agent has
            never run a session (no model call), and `daemon stop` leaves no daemon. Records, without failing,
            whether a hand edit to AGENT.md's settings block is adopted (`agent_md_edit_adopted`).
  festival  $FEST_BIN (with `camp` beside it), then ~/DEVELOP/pfy-mentat/tmp/festival/fest (unpacked from the v0.3.20
            festival-0.3.20-linux-x86_64.tar.gz release), then PATH. fest and camp pinned by sha256 ($FEST_SHA256 /
            $CAMP_SHA256 override); a mismatch exits 2 without exec. In a temp HOME: `camp create` makes a git-backed
            camp with AGENTS.md; strict `fest create festival --agent` with unfilled template markers must roll back
            (ok false, no directory left); a non-strict create must scaffold fest.yaml plus the TESTING and REVIEW
            quality gates; `fest next` in that unfilled festival must refuse (nonzero, "VALIDATION FAILED").
  sloptrim  $SLOPTRIM_DIR, then ~/DEVELOP/pfy-mentat/tmp/sloptrim (a clone at tag v0.9.4), HEAD pinned
            ($SLOPTRIM_COMMIT overrides; a mismatch exits 2). `scripts/detect.py` must score a deliberately
            sloppy sample at least 30 points above a plain one and band it as tells, keep the plain one under 40,
            report a planted zero-width character, and `--clean` must remove it.
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

from smoke import TMP, run_isolated, timeout_reason, write

OVERTIME_PIN = "0.5.3"
# festival v0.3.20 festival-0.3.20-linux-x86_64.tar.gz (tarball sha256
# 0202a7b15cc385d1687d756ae6f513283a5adef445037f70a054b754e6ec716f, matching the release checksums.txt)
FEST_V0320_SHA256 = "21767cacd8a7dd346e634c99a9c21f99ba8c25424e762b42b746cd32cb29e4db"
CAMP_V0320_SHA256 = "550df7ee2716d0cc298d5e6f571cb719b9b611eafe4861c55d9e0e945cf20464"
SLOPTRIM_V094_COMMIT = "38dbb7cb4e97de0b9bf157903c95bdcab016dda2"

SLOP = ("In today's fast-paced digital landscape, it's important to note that leveraging robust, cutting-edge "
        "solutions is not just a game-changer, it's a testament to our unwavering commitment. Let's delve into this "
        "rich tapestry of seamless synergy. Moreover, it is crucial to embark on this transformative journey, "
        "unlocking the full potential of a vibrant ecosystem. In conclusion, this pivotal paradigm shift underscores "
        "the profound importance of navigating the ever-evolving realm.\n")
PLAIN = ("The meeting moved to Tuesday at ten. Bring the budget sheet and both vendor quotes. Sam will book the small "
         "room on the third floor, since the big one is taken. If the quotes are still over our limit, we will ask "
         "each vendor for a second round and decide by Friday. Lunch is not provided this time.\n")


def tmo() -> float:
    try:
        v = float(os.environ.get("PFY_XINTAKE_TIMEOUT", ""))
        return v if v > 0 else 120.0
    except ValueError:
        return 120.0


def sha256(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sh(cmd, *, home: str, path: str, cwd=None, extra: dict | None = None,
       bwrap_writable: list[str] | None = None):
    """Every child in this smoke. Delegates to run_isolated; does not spawn on its own."""
    return run_isolated(list(cmd), home=home, path=path, cwd=None if cwd is None else str(cwd), timeout=tmo(),
                        extra=extra, bwrap_writable=bwrap_writable)


def containment(home: str, writable: list[str], bare: str) -> str:
    """Receipt label for a bwrap_writable run. The probe itself goes through run_isolated."""
    try:
        probe = run_isolated(["/bin/true"], home=home, timeout=min(10.0, tmo()), bwrap_writable=writable)
    except (OSError, subprocess.TimeoutExpired):
        return bare
    args = [str(a) for a in (probe.args or [])]
    if "--unshare-pid" in args:
        return "bwrap read-only root, no network, own pid namespace"
    if args and Path(args[0]).name == "bwrap":
        return "bwrap read-only root, no network"
    return bare


def tree_sig(p: Path) -> str | None:
    """Content, lstat mode, and symlink text. mtime is ignored and links are not followed."""
    if not p.exists():
        return None
    h = hashlib.sha256()
    for f in sorted(p.rglob("*", recurse_symlinks=False)):
        try:
            st = f.lstat()
        except OSError:
            h.update(f"{f}:unreadable\n".encode())
            continue
        mode = stat.S_IMODE(st.st_mode)
        try:
            if stat.S_ISLNK(st.st_mode):
                h.update(f"{f}:{mode:o}:link:{os.readlink(f)}\n".encode())
            elif stat.S_ISREG(st.st_mode):
                fh = hashlib.sha256()
                with f.open("rb") as fp:  # 1 MiB chunks; a large file stays out of RAM
                    for chunk in iter(lambda: fp.read(1 << 20), b""):
                        fh.update(chunk)
                h.update(f"{f}:{mode:o}:{fh.hexdigest()}\n".encode())
            else:
                kind = "dir" if stat.S_ISDIR(st.st_mode) else "other"
                h.update(f"{f}:{mode:o}:{kind}\n".encode())
        except OSError:
            h.update(f"{f}:{mode:o}:unreadable\n".encode())
    return h.hexdigest()


def node_ok(node: str) -> tuple[bool, str]:
    try:
        with tempfile.TemporaryDirectory(prefix="pfy-node-") as td:
            v = run_isolated([node, "--version"], home=td, path="/usr/bin:/bin",
                             timeout=min(10.0, tmo())).stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"node not runnable: {e}"
    m = re.match(r"v(\d+)\.(\d+)", v)
    return bool(m and (int(m[1]), int(m[2])) >= (22, 19)), v


def smoke_overtime(r: dict) -> int:
    d = None
    for c in (os.environ.get("OVERTIME_DIR"), str(TMP / "overtime")):
        if c and (Path(c) / "node_modules/@ukanwat/overtime/dist/bin.js").is_file():
            d = Path(c)
            break
    if not d:
        r["reason"] = ("overtime not staged: npm install --prefix ~/DEVELOP/pfy-mentat/tmp/overtime --ignore-scripts "
                       f"@ukanwat/overtime@{OVERTIME_PIN} (or set $OVERTIME_DIR)")
        return 2
    pkg = d / "node_modules/@ukanwat/overtime"
    ver = json.loads((pkg / "package.json").read_text()).get("version")
    want = os.environ.get("OVERTIME_VERSION") or OVERTIME_PIN
    r["version"] = ver
    if ver != want:
        r["reason"] = f"overtime version {ver} != pinned {want}"
        return 2
    node = next((c for c in (os.environ.get("OVERTIME_NODE"), str(TMP / "overtime/node/bin/node"), shutil.which("node"))
                 if c and os.access(c, os.X_OK)), None)
    if not node:
        r["reason"] = "no node: stage Node >= 22.19 at ~/DEVELOP/pfy-mentat/tmp/overtime/node or set $OVERTIME_NODE"
        return 2
    ok, nv = node_ok(node)
    r["node"] = nv
    if not ok:
        r["reason"] = f"overtime needs Node >= 22.19, found {nv}; stage one under tmp/overtime/node"
        return 2
    real = Path.home() / "overtime"
    before = tree_sig(real)
    r["containment"] = "real-home-check (daemon is detached; no bwrap)"
    timed_out: subprocess.TimeoutExpired | None = None
    stop_timeout_reason: str | None = None
    timeout_step = "overtime"
    try:
        with tempfile.TemporaryDirectory(prefix="pfy-overtime-") as td:
            home = Path(td) / "home"
            home.mkdir()
            prot = Path(td) / "protected"
            prot.mkdir()
            home_s = str(home)
            path = f"{Path(node).parent}:/usr/bin:/bin"
            ot = [node, str(pkg / "dist/bin.js")]
            steps = r.setdefault("steps", [])
            try:
                try:
                    p = sh(ot + ["new", "smoke-agent"], home=home_s, path=path)
                except subprocess.TimeoutExpired:
                    timeout_step = "new"
                    raise
                steps.append({"new": p.returncode})
                a = home / "overtime/agents/smoke-agent"
                if p.returncode != 0 or not (a / "AGENT.md").is_file() or not (a / ".overtime/settings.json").is_file():
                    r["reason"] = f"`new` did not create the agent folder: {p.stdout[-300:]}{p.stderr[-300:]}"
                    return 1
                p = sh(ot + ["ls"], home=home_s, path=path)
                if "smoke-agent" not in p.stdout:
                    r["reason"] = "`ls` does not list the new agent"
                    return 1
                p = sh(ot + ["set", "smoke-agent", "budget=1", f"protect={prot}"], home=home_s, path=path)
                s = json.loads((a / ".overtime/settings.json").read_text())
                steps.append({"set": p.returncode, "settings": s})
                if p.returncode != 0 or s.get("dailyBudgetUsd") != 1 or str(prot) not in s.get("protect", []):
                    r["reason"] = "`set budget=1 protect=` did not land in .overtime/settings.json"
                    return 1
                p = sh(ot + ["settings", "smoke-agent"], home=home_s, path=path)
                if "$1 a day" not in p.stdout or str(prot) not in p.stdout:
                    r["reason"] = "`settings` does not show the new budget and protected path"
                    return 1
                st = json.loads((a / ".overtime/state.json").read_text())
                steps.append({"state": {k: st.get(k) for k in ("status", "mainSessionId", "lastRunAt")}})
                if st.get("mainSessionId") or st.get("lastRunAt"):
                    r["reason"] = "agent ran a session without a job (would have called a model)"
                    return 1
                md = a / "AGENT.md"
                md.write_text(md.read_text().replace("dailyBudgetUsd: 1", "dailyBudgetUsd: 999", 1))
                adopted = False
                for _ in range(20):
                    time.sleep(0.5)
                    if json.loads((a / ".overtime/settings.json").read_text()).get("dailyBudgetUsd") == 999:
                        adopted = True
                        break
                r["agent_md_edit_adopted"] = adopted
            finally:
                try:
                    p = sh(ot + ["daemon", "stop"], home=home_s, path=path)
                    steps.append({"daemon_stop": p.returncode})
                except subprocess.TimeoutExpired as e:
                    stop_timeout_reason = timeout_reason("overtime daemon stop", float(e.timeout))
                    steps.append({"daemon_stop": stop_timeout_reason})
                time.sleep(1)
            lock = home / "overtime/overtimed.lock"
            alive = False
            if lock.exists():
                m = re.search(r"\d+", lock.read_text())
                if m:
                    try:
                        os.kill(int(m[0]), 0)
                        alive = True
                    except OSError:
                        pass
            if alive:
                r["reason"] = "daemon still running after `daemon stop`"
                return 1
    except subprocess.TimeoutExpired as e:
        timed_out = e
    if tree_sig(real) != before:
        r["reason"] = "real HOME ~/overtime was created or changed"
        return 1
    if timed_out is not None:
        r["reason"] = timeout_reason(timeout_step, float(timed_out.timeout))
        return 1
    if stop_timeout_reason is not None:
        r["reason"] = stop_timeout_reason
        return 1
    r["reason"] = "agent created, listed, budget/protect set and shown, no session run, daemon stopped, real HOME untouched"
    return 0


def smoke_festival(r: dict) -> int:
    fest = next((c for c in (os.environ.get("FEST_BIN"), str(TMP / "festival/fest"), shutil.which("fest"))
                 if c and os.path.isfile(c) and os.access(c, os.X_OK)), None)
    if not fest:
        r["reason"] = "festival not staged: unpack festival-0.3.20-linux-x86_64.tar.gz into ~/DEVELOP/pfy-mentat/tmp/festival"
        return 2
    camp = str(Path(fest).parent / "camp")
    if not os.access(camp, os.X_OK):
        r["reason"] = f"no camp binary next to {fest}"
        return 2
    for b, var, pin in ((fest, "FEST_SHA256", FEST_V0320_SHA256), (camp, "CAMP_SHA256", CAMP_V0320_SHA256)):
        got, want = sha256(b), (os.environ.get(var) or pin).lower()
        if got != want:
            r["reason"] = f"{b} sha256 {got} != pinned {want} (${var} overrides); not executed"
            return 2
    git = shutil.which("git")
    if not git:
        r["reason"] = "git not on PATH"
        return 2
    real = [Path.home() / ".obey", Path.home() / "campaigns"]
    before = [tree_sig(p) for p in real]
    with tempfile.TemporaryDirectory(prefix="pfy-festival-") as td:
        home = Path(td) / "home"
        home.mkdir()
        home_s = str(home)
        path = f"{Path(fest).parent}:{Path(git).parent}:/usr/bin:/bin"
        extra = {"GIT_AUTHOR_NAME": "smoke", "GIT_AUTHOR_EMAIL": "smoke@localhost",
                 "GIT_COMMITTER_NAME": "smoke", "GIT_COMMITTER_EMAIL": "smoke@localhost"}
        r["containment"] = containment(home_s, [td], "real-home-check")
        W = lambda c, cwd=None: sh(c, home=home_s, path=path, cwd=cwd, extra=extra, bwrap_writable=[td])
        try:
            p = W([fest, "--version"])
        except subprocess.TimeoutExpired as e:
            r["reason"] = timeout_reason("version", float(e.timeout))
            return 1
        r["version"] = p.stdout.strip()
        p = W([camp, "create", "smokecamp", "-d", "smoke", "-m", "smoke mission"])
        root = home / "campaigns/smokecamp"
        if p.returncode != 0 or not (root / "AGENTS.md").is_file():
            r["reason"] = f"`camp create` failed: {p.stdout[-300:]}{p.stderr[-300:]}"
            return 1
        if not W([git, "-C", str(root), "log", "--oneline"]).stdout.strip():
            r["reason"] = "camp has no initial git commit"
            return 1
        p = W([fest, "create", "festival", "--agent", "--name", "strict", "--goal", "Print hello", "--type",
               "implementation"], cwd=str(root))
        try:
            j = json.loads(p.stdout)
        except ValueError:
            r["reason"] = f"strict create did not print JSON: {p.stdout[-300:]}{p.stderr[-300:]}"
            return 1
        left = root / (j.get("created_path") or "festivals/planning/strict-missing")
        r["strict_ok"], r["strict_left_dir"] = j.get("ok"), left.exists()
        if j.get("ok") is not False or left.exists():
            r["reason"] = "strict create with unfilled markers did not roll back"
            return 1
        p = W([fest, "create", "festival", "--json", "--name", "loose", "--goal", "Print hello", "--type",
               "implementation", "--skip-markers"], cwd=str(root))
        try:
            j = json.loads(p.stdout)
        except ValueError:
            r["reason"] = f"non-strict create did not print JSON: {p.stdout[-300:]}{p.stderr[-300:]}"
            return 1
        fd = root / (j.get("created_path") or "missing")
        need = ["fest.yaml", "gates/implementation/QUALITY_GATE_TESTING.md", "gates/implementation/QUALITY_GATE_REVIEW.md"]
        miss = [n for n in need if not (fd / n).is_file()]
        if not j.get("ok") or miss:
            r["reason"] = f"non-strict create missing {miss or 'ok'}"
            return 1
        p = W([fest, "next"], cwd=str(fd))
        r["next_rc"] = p.returncode
        if p.returncode == 0 or "VALIDATION FAILED" not in (p.stdout + p.stderr):
            r["reason"] = "`fest next` did not refuse an unfilled festival"
            return 1
    if [tree_sig(p) for p in real] != before:
        r["reason"] = "real HOME ~/.obey or ~/campaigns changed"
        return 1
    r["reason"] = "camp created, strict create rolled back, gates scaffolded, fest next refused the unfilled plan"
    return 0


def smoke_sloptrim(r: dict) -> int:
    d = next((Path(c) for c in (os.environ.get("SLOPTRIM_DIR"), str(TMP / "sloptrim"))
              if c and (Path(c) / "scripts/detect.py").is_file()), None)
    if not d:
        r["reason"] = ("sloptrim not staged: git clone --depth 1 --branch v0.9.4 https://github.com/seyedehsanhadi/sloptrim.git "
                       "~/DEVELOP/pfy-mentat/tmp/sloptrim (or set $SLOPTRIM_DIR)")
        return 2
    want = (os.environ.get("SLOPTRIM_COMMIT") or SLOPTRIM_V094_COMMIT).lower()
    git = shutil.which("git")
    if not git:
        head = ""
    else:
        with tempfile.TemporaryDirectory(prefix="pfy-sloptrim-git-") as ghome:
            head = sh([git, "-C", str(d), "rev-parse", "HEAD"], home=ghome, path="/usr/bin:/bin").stdout.strip()
    r["commit"] = head
    if head != want:
        r["reason"] = f"sloptrim HEAD {head or '(not a git clone)'} != pinned {want} ($SLOPTRIM_COMMIT overrides)"
        return 2
    py = sys.executable
    with tempfile.TemporaryDirectory(prefix="pfy-sloptrim-") as td:
        r["containment"] = containment(td, [td], "none needed (stdlib, no network per upstream)")
        files = {"slop": SLOP, "plain": PLAIN, "zw": PLAIN.replace("Tuesday", "Tues\u200bday")}
        scores = {}
        for k, v in files.items():
            f = Path(td) / f"{k}.md"
            f.write_text(v, encoding="utf-8")
            p = sh([py, str(d / "scripts/detect.py"), str(f)], home=td, path="/usr/bin:/bin", bwrap_writable=[td])
            try:
                scores[k] = json.loads(p.stdout)["_metrics"]
            except (ValueError, KeyError):
                r["reason"] = f"detect.py gave no JSON for {k}: {p.stderr[-300:]}"
                return 1
        r["scores"] = {k: (m.get("ai_tell_score"), m.get("ai_tell_band")) for k, m in scores.items()}
        s, c = scores["slop"].get("ai_tell_score"), scores["plain"].get("ai_tell_score")
        if s is None or c is None or s - c < 30 or c >= 40 or scores["slop"].get("ai_tell_band") == "clean":
            r["reason"] = f"scores do not separate sloppy ({s}) from plain ({c}) text"
            return 1
        if not scores["zw"].get("invisible_chars"):
            r["reason"] = "planted zero-width character not reported"
            return 1
        p = sh([py, str(d / "scripts/detect.py"), "--clean", str(Path(td) / "zw.md")], home=td, path="/usr/bin:/bin",
               bwrap_writable=[td])
        if p.returncode != 0 or "\u200b" in p.stdout or "Tuesday" not in p.stdout:
            r["reason"] = "`--clean` did not remove the zero-width character"
            return 1
    r["reason"] = f"sloppy {s} vs plain {c}; zero-width char reported and scrubbed"
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", required=True, choices=["overtime", "festival", "sloptrim"])
    a = ap.parse_args()
    receipt = {"entry": a.entry, "script": "examples/x-intake-local/smoke_112_114.py",
               "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    fn = {"overtime": smoke_overtime, "festival": smoke_festival, "sloptrim": smoke_sloptrim}[a.entry]
    try:
        code = fn(receipt)
    except subprocess.TimeoutExpired as e:
        receipt["reason"] = timeout_reason(a.entry, float(e.timeout))
        code = 1
    return write(a.entry, receipt, code)


if __name__ == "__main__":
    sys.exit(main())
