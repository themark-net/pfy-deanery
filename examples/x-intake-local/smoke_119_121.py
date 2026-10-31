#!/usr/bin/env python3
"""Operate-or-FAIL smokes for X intake Entries 119-121 (AgentDescent, Kenfold, Tree-sitter Analyzer). Stdlib only.

Usage: python3 examples/x-intake-local/smoke_119_121.py --entry agentdescent|kenfold|tsa

Same contract and receipts as smoke.py next to it (whose helpers it reuses): exit 0 = PASS, 1 = the tool ran but
the check failed, 2 = can't run here (prereq missing; reason recorded). Writes pipelines/smoke/<entry>/latest.json.
Never installs anything (kenfold's compose build may pull the pinned base images). Every child process starts
through `run_isolated` in smoke.py (fresh temp HOME, env limited to PATH/HOME/TERM/LANG/NO_COLOR plus the variables
named below; nothing copied from this process, so no provider key is ever seen; a timeout SIGKILLs the process
group). No smoke calls a model or starts an agent CLI.
PFY_XINTAKE_TIMEOUT (float seconds, > 0) overrides the 600s per-command timeout.
Real HOME: before each run the smoke snapshots the real-HOME dirs the tool writes by default (agentdescent
~/.agentdescent, tsa ~/.tsa and ~/.cache/tree-sitter-analyzer, kenfold ~/.local/state/kenfold and ~/.cache/kenfold)
and compares them in a finally, also on timeout: checks.real_home_untouched, and a change FAILs (exit 1). On a
timeout the receipt keeps the partial checks; a `compose down -v` timeout never replaces an earlier failure reason.

  agentdescent  $AGENTDESCENT_BIN, then ~/DEVELOP/pfy-mentat/tmp/agentdescent/.venv/bin/agentdescent (a venv with
                `pip install agentdescent==0.5.1`), then PATH. The package version, read with the python next to the
                binary, is pinned to 0.5.1 ($AGENTDESCENT_VERSION overrides). Runs the packaged offline demo
                (`demo --dir`, with `--store` in the temp dir) under bwrap with a read-only root and no network when
                that works: it must exit 0, print "held-out reward: 1.000" and learn rules.md -> 'COLUMN: amount',
                and the demo skill on disk must still say 'COLUMN: id' (an evolved artifact only lands on `apply`).
  kenfold       $KENFOLD_DIR, then ~/DEVELOP/pfy-mentat/tmp/kenfold: a checkout of jeonjw85/kenfold at tag v0.1.1
                ($KENFOLD_REF overrides; checked with `git describe --tags --exact-match`) and commit dfc18f9f ($KENFOLD_COMMIT
                overrides, `skip` disables; checked with `git rev-parse HEAD`), holding compose.yaml.
                Needs docker ($DOCKER_BIN, ~/DEVELOP/pfy-mentat/tmp/docker/docker, or PATH) with the compose plugin;
                exit 2 without them, or if 127.0.0.1:7077 is already answering. Builds and starts only the postgres and
                kenfold services as compose project "pfy-kenfold-smoke" (no Ollama, no reranker, update check off),
                then GET /healthz and /readyz must be 200, POST /mcp with no API key must be refused with 401, and
                `kenfold healthcheck` inside the container must exit 0. Always runs `compose down -v` after. No API key
                is minted and no memory is written. For a non-default socket set $KENFOLD_DOCKER_HOST.
  tsa           $TSA_BIN, then ~/DEVELOP/pfy-mentat/tmp/tree-sitter-analyzer/.venv/bin/tree-sitter-analyzer (a
                venv with `pip install "tree-sitter-analyzer[all]==2.2.0"`), then PATH; `miswire-audit` must sit
                next to it. `--version` pinned to 2.2.0 ($TSA_VERSION overrides). In a temp fixture repo (three
                Python files counting __init__.py, one JavaScript file; both languages define `total`), under bwrap
                when it works: `--structure --output-format json` on pkg/billing.py must list exactly the functions tax and total, and
                `miswire-audit` must index python:3 and javascript:1 and report that Tree-sitter Analyzer mis-wires
                0 call edges. Its .ast-cache lands in the temp repo only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from smoke import TMP, find_bin, pinned, run_isolated, timeout_reason, write

AD_PIN = "0.5.1"
KENFOLD_REF = "v0.1.1"
KENFOLD_COMMIT = "dfc18f9f1a7be98c5af8c0e7e1cbf566c37d51af"
TSA_PIN = "2.2.0"
GIT_ID = {"GIT_AUTHOR_NAME": "pfy-smoke", "GIT_AUTHOR_EMAIL": "smoke@localhost",
          "GIT_COMMITTER_NAME": "pfy-smoke", "GIT_COMMITTER_EMAIL": "smoke@localhost"}


def tmo() -> float:
    try:
        v = float(os.environ.get("PFY_XINTAKE_TIMEOUT", ""))
        return v if v > 0 else 600.0
    except ValueError:
        return 600.0


# Real-HOME dirs each tool writes by default (read from upstream source): agentdescent's run store; tsa's
# core/analysis_session.py sessions plus its cache; kenfold's internal/hook DefaultStateDir and internal/bench cache.
WATCH = {"agentdescent": (".agentdescent",),
         "tsa": (".tsa", ".cache/tree-sitter-analyzer"),
         "kenfold": (".local/state/kenfold", ".cache/kenfold")}


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


def guarded(entry: str, body, r: dict) -> int:
    """Run body(r, checks) with the real HOME watched. The finally runs on timeout too, so the receipt keeps the
    partial checks and real_home_untouched (the #295 kander pattern)."""
    real_home = Path.home()
    before = {d: tree_sig(real_home / d) for d in WATCH[entry]}
    checks: dict[str, bool] = {}
    try:
        code = body(r, checks)
    finally:
        after = {d: tree_sig(real_home / d) for d in WATCH[entry]}
        checks["real_home_untouched"] = before == after
        r["checks"] = checks
    if code is not None:
        if not checks["real_home_untouched"]:
            r["reason"] = f"{r.get('reason', '')}; real HOME {', '.join('~/' + d for d in WATCH[entry])} changed"
            return 1
        return code
    return finish(r, checks, r.pop("_ok_reason"))


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


def smoke_agentdescent(r: dict) -> int:
    b = find_bin("AGENTDESCENT_BIN", "agentdescent/.venv/bin/agentdescent", "agentdescent")
    if not b:
        r["reason"] = "agentdescent not found ($AGENTDESCENT_BIN, tmp/agentdescent/.venv, PATH); see the handoff"
        return 2
    r["bin"] = b
    py = Path(b).parent / "python"
    if not os.access(py, os.X_OK):
        r["reason"] = f"no python next to {b}, so the package version can't be checked"
        return 2
    return guarded("agentdescent", lambda rr, checks: _agentdescent(rr, b, py, checks), r)


def _agentdescent(r: dict, b: str, py: Path, checks: dict) -> int | None:
    want = pinned(r, "AGENTDESCENT_VERSION", AD_PIN)
    with tempfile.TemporaryDirectory(prefix="pfy-agentdescent-") as td:
        home = Path(td, "home")
        home.mkdir()
        v = iso([str(py), "-c", "import agentdescent; print(agentdescent.__version__)"], "agentdescent version",
                home=str(home), cwd=td, bwrap_writable=[td])
        r["version_out"] = (v.stdout + v.stderr).strip()[:200]
        if v.returncode != 0 or v.stdout.strip() != want:
            r["reason"] = f"agentdescent version is not {want}: {r['version_out']!r} (set $AGENTDESCENT_VERSION)"
            return 2
        demo = Path(td, "demo")
        d = iso([b, "--store", str(Path(td, "runs")), "demo", "--dir", str(demo)], "agentdescent demo",
                home=str(home), cwd=td, bwrap_writable=[td])
        out = d.stdout + d.stderr
        r["demo_rc"] = d.returncode
        r["demo_tail"] = out.strip().splitlines()[-12:]
        checks["demo_exit_0"] = d.returncode == 0
        checks["heldout_reward_1"] = "held-out reward: 1.000" in out
        checks["learned_amount"] = "rules.md -> 'COLUMN: amount'" in out
        rules = list(demo.rglob("references/rules.md"))
        checks["skill_on_disk_untouched"] = bool(rules) and "COLUMN: id" in rules[0].read_text()
        checks["home_untouched"] = not any(home.iterdir())
    r["_ok_reason"] = ("offline demo evolved the skill (reward 1.000) without a key or network; "
                       "the original skill stayed untouched")
    return None


def http(method: str, url: str, body: bytes | None = None, headers: dict | None = None) -> int:
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, OSError):
        return 0


def smoke_kenfold(r: dict) -> int:
    d = Path(os.environ.get("KENFOLD_DIR") or (TMP / "kenfold"))
    r["dir"] = str(d)
    if not (d / "compose.yaml").exists():
        r["reason"] = f"Kenfold checkout not staged ({d / 'compose.yaml'} missing); see the handoff"
        return 2
    docker = find_bin("DOCKER_BIN", "docker/docker", "docker")
    if not docker:
        r["reason"] = "docker is not available"
        return 2
    want = pinned(r, "KENFOLD_REF", KENFOLD_REF)
    base = "http://127.0.0.1:7077"
    if http("GET", f"{base}/healthz") != 0:
        r["reason"] = "something is already listening on 127.0.0.1:7077 (compose.yaml hardcodes that port)"
        return 2
    return guarded("kenfold", lambda rr, checks: _kenfold(rr, d, docker, want, base, checks), r)


def _kenfold(r: dict, d: Path, docker: str, want: str, base: str, checks: dict) -> int | None:
    path = f"{Path(docker).parent}:/usr/bin:/bin"
    with tempfile.TemporaryDirectory(prefix="pfy-kenfold-") as home:
        g = iso(["git", "-C", str(d), "describe", "--tags", "--exact-match"], "git describe", home=home,
                extra=GIT_ID)
        r["ref"] = g.stdout.strip()
        if g.returncode != 0 or r["ref"] != want:
            r["reason"] = f"Kenfold checkout is not at {want} (got {r['ref'] or g.stderr.strip()[:120]!r})"
            return 2
        want_commit = pinned(r, "KENFOLD_COMMIT", KENFOLD_COMMIT, lower=True)
        c = iso(["git", "-C", str(d), "rev-parse", "HEAD"], "git rev-parse", home=home, extra=GIT_ID)
        r["commit"] = c.stdout.strip()
        if want_commit != "skip" and (c.returncode != 0 or r["commit"] != want_commit):
            r["reason"] = f"Kenfold checkout {r['commit'][:12] or '?'} is not commit {want_commit[:12]} (set $KENFOLD_COMMIT)"
            return 2
        extra = {"KENFOLD_UPDATE_CHECK": "false"}
        if os.environ.get("KENFOLD_DOCKER_HOST"):
            extra["DOCKER_HOST"] = os.environ["KENFOLD_DOCKER_HOST"]
            r["docker_host"] = extra["DOCKER_HOST"]

        def dc(*args: str, tag: str) -> subprocess.CompletedProcess:
            return iso([docker, "compose", "-p", "pfy-kenfold-smoke", *args], tag, home=home, cwd=str(d),
                       path=path, extra=extra, bwrap_writable=None)

        if dc("version", tag="docker compose version").returncode != 0:
            r["reason"] = "the docker compose plugin is not available"
            return 2
        try:
            up = dc("up", "-d", "--build", "postgres", "kenfold", tag="docker compose up")
            r["up_tail"] = (up.stdout + up.stderr).strip().splitlines()[-6:]
            if up.returncode != 0:
                r["reason"] = "docker compose up failed"
                return 1
            deadline = time.time() + min(tmo(), 300)
            ready = 0
            while time.time() < deadline:
                ready = http("GET", f"{base}/readyz")
                if ready == 200:
                    break
                time.sleep(3)
            checks["readyz_200"] = ready == 200
            checks["healthz_200"] = http("GET", f"{base}/healthz") == 200
            init = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                               "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                                          "clientInfo": {"name": "pfy-smoke", "version": "0"}}}).encode()
            st = http("POST", f"{base}/mcp", init,
                      {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
                       "Host": "127.0.0.1:7077"})
            r["mcp_status_no_key"] = st
            checks["mcp_refuses_no_key"] = st == 401
            hc = dc("exec", "-T", "kenfold", "/usr/local/bin/kenfold", "healthcheck", tag="kenfold healthcheck")
            checks["container_healthcheck"] = hc.returncode == 0
        finally:
            # a down timeout must not replace an earlier failure (up rc 1 or an up/exec timeout)
            try:
                r["down_rc"] = dc("down", "-v", tag="docker compose down").returncode
            except TimeoutError as e:
                r["down_rc"] = None
                r["down_reason"] = str(e)
        if r.get("down_reason"):
            raise TimeoutError(r["down_reason"])
    r["_ok_reason"] = "postgres+kenfold came up at the pinned tag and commit; probes 200 and /mcp refused a keyless call"
    return None


FIXTURE = {
    "pkg/__init__.py": "",
    "pkg/billing.py": "def tax(amount):\n    return round(amount * 0.08, 2)\n\n\n"
                      "def total(amount):\n    return amount + tax(amount)\n",
    "pkg/main.py": "from pkg.billing import total\n\n\ndef checkout(cart):\n    return sum(total(x) for x in cart)\n",
    "web/cart.js": "function total(items) {\n  return items.length;\n}\n\nfunction render(items) {\n"
                   "  return \"n=\" + total(items);\n}\n\nmodule.exports = { render };\n",
}


def smoke_tsa(r: dict) -> int:
    b = find_bin("TSA_BIN", "tree-sitter-analyzer/.venv/bin/tree-sitter-analyzer", "tree-sitter-analyzer")
    if not b:
        r["reason"] = "tree-sitter-analyzer not found ($TSA_BIN, tmp/tree-sitter-analyzer/.venv, PATH); see the handoff"
        return 2
    audit = Path(b).parent / "miswire-audit"
    if not os.access(audit, os.X_OK):
        r["reason"] = f"miswire-audit is not next to {b}"
        return 2
    r["bin"] = b
    return guarded("tsa", lambda rr, checks: _tsa(rr, b, audit, checks), r)


def _tsa(r: dict, b: str, audit: Path, checks: dict) -> int | None:
    want = pinned(r, "TSA_VERSION", TSA_PIN)
    with tempfile.TemporaryDirectory(prefix="pfy-tsa-") as td:
        home, repo = Path(td, "home"), Path(td, "repo")
        home.mkdir()
        for rel, text in FIXTURE.items():
            p = repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        kw = {"home": str(home), "cwd": str(repo), "bwrap_writable": [td]}
        v = iso([b, "--version"], "tsa version", **kw)
        r["version_out"] = (v.stdout + v.stderr).strip()[:200]
        if v.returncode != 0 or want not in v.stdout.split():
            r["reason"] = f"tree-sitter-analyzer version is not {want}: {r['version_out']!r} (set $TSA_VERSION)"
            return 2
        s = iso([b, "pkg/billing.py", "--structure", "--output-format", "json", "--project-root", str(repo)],
                "tsa structure", **kw)
        try:
            names = sorted(m["name"] for m in json.loads(s.stdout)["methods"])
        except (ValueError, KeyError, TypeError):
            names = None
        r["structure_methods"] = names
        checks["structure_lists_tax_total"] = s.returncode == 0 and names == ["tax", "total"]
        a = iso([str(audit), "."], "miswire-audit", **kw)
        out = a.stdout + a.stderr
        r["audit_tail"] = [ln.strip() for ln in out.strip().splitlines() if ln.strip()][:8]
        checks["audit_exit_0"] = a.returncode == 0
        checks["audit_indexed_both_languages"] = "javascript:1" in out and "python:3" in out
        checks["tsa_miswires_0"] = "Tree-sitter Analyzer mis-wires 0" in out
    r["_ok_reason"] = "structure query and cross-language mis-wire audit ran locally with no network"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", required=True, choices=["agentdescent", "kenfold", "tsa"])
    a = ap.parse_args()
    receipt = {"entry": a.entry, "script": "examples/x-intake-local/smoke_119_121.py",
               "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    fn = {"agentdescent": smoke_agentdescent, "kenfold": smoke_kenfold, "tsa": smoke_tsa}[a.entry]
    try:
        code = fn(receipt)
    except TimeoutError as e:
        receipt["reason"] = str(e)
        receipt.pop("_ok_reason", None)
        if receipt.get("checks", {}).get("real_home_untouched") is False:
            receipt["reason"] += f"; real HOME {', '.join('~/' + d for d in WATCH[a.entry])} changed"
        code = 1
    return write(a.entry, receipt, code)


if __name__ == "__main__":
    sys.exit(main())
