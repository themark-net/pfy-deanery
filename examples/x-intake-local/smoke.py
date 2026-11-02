#!/usr/bin/env python3
"""Operate-or-FAIL smokes for X intake Entries 095-097 (Qwen3.8-Flash-Next, Sandlock, Foremerge). Stdlib only.

Usage: python3 examples/x-intake-local/smoke.py --entry qwen38flash|sandlock|foremerge

Exit 0 = PASS. 1 = the tool ran but the check failed. 2 = can't run here (prereq missing; reason recorded).
Writes pipelines/smoke/<entry>/latest.json every time. Never installs anything, never downloads into the repo,
and every scratch file goes to a fresh tempfile directory that is removed afterwards.
New x-intake smokes must start every subprocess with run_isolated below, not with run() or subprocess.

  qwen38flash  $QWEN38_URL = an OpenAI-compatible base URL (e.g. http://127.0.0.1:8080/v1 from llama-server)
               already serving a Qwen3.8-Flash-Next GGUF. Asks for an exact token and checks it comes back.
               Never starts a server or loads a model itself (nimo memory edge: see Entries 089-094).
  sandlock     $SANDLOCK_BIN or ~/DEVELOP/pfy-mentat/tmp/sandlock/sandlock or `sandlock` on PATH; Linux 6.12+.
               Runs /bin/sh confined to one writable dir and expects the allowed write to land and a write to a
               sibling dir to be refused.
  foremerge    $FOREMERGE_BIN or ~/DEVELOP/pfy-mentat/tmp/foremerge/foremerge or `foremerge` on PATH.
               In a throwaway git repo: publish "replace symbol:PaymentService", then preflight
               "extend symbol:PaymentService" and expect a HIGH conflict; an unrelated scope must not conflict.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import platform
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TMP = Path.home() / "DEVELOP/pfy-mentat/tmp"
# Env vars stripped from every x-intake tool subprocess (smoke_103_105/106_108/109_111 import this): paid model
# keys and endpoints, cloud and forge tokens, so a third-party binary never sees them.
PAID_KEYS = ("OPENROUTER_API_KEY", "AI_GATEWAY_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_APIKEY",
             "GOOGLE_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY", "GROK_API_KEY",
             "OLLAMA_BASE_URL", "BUGPATROL_MODEL_ENDPOINT", "BUGPATROL_MODEL_NAME",
             "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE",
             "HAR_PORTAL_TOKEN", "CASS_PATH", "NOTION_API_KEY", "GITHUB_TOKEN", "GH_TOKEN")
# Names stripped on top of PAID_KEYS. Covers GH_TOKEN, GITHUB_TOKEN, GH_ENTERPRISE_TOKEN, GITHUB_PAT,
# NPM_TOKEN, and HF_TOKEN.
SECRET_ENV_RE = re.compile(r"(TOKEN|SECRET|PASSWORD|PASSWD|CREDENTIALS?|_API_KEY|_PAT)$", re.IGNORECASE)


def scrub_env(env: dict) -> dict:
    """Parent env minus paid-provider keys and token-like names."""
    return {k: v for k, v in env.items() if k not in PAID_KEYS and SECRET_ENV_RE.search(k) is None}


def node_version_env(home: str) -> dict[str, str]:
    """Allowlist for `node --version`: PATH, LANG, LC_ALL, TMPDIR, and the temp HOME."""
    env = {key: os.environ[key] for key in ("PATH", "LANG", "LC_ALL", "TMPDIR") if os.environ.get(key)}
    env["HOME"] = home
    return env


def write(entry: str, receipt: dict, code: int) -> int:
    # $PFY_SMOKE_RECEIPT_DIR lets tests write receipts outside the repo (never over a real run's latest.json).
    # Unset or empty keeps pipelines/smoke. A relative path is refused: resolving it from cwd can clobber a real receipt.
    raw = os.environ.get("PFY_SMOKE_RECEIPT_DIR")
    if raw:
        base = Path(raw)
        if not base.is_absolute():
            print(f"PFY_SMOKE_RECEIPT_DIR must be absolute; directory refused: {raw}")
            return 1
    else:
        base = ROOT / "pipelines/smoke"
    receipt["exit_code"] = code
    receipt["verdict"] = {0: "PASS", 1: "FAIL", 2: "FAIL_CANNOT_RUN_HERE"}[code]
    out = base / entry / "latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: receipt.get(k) for k in ("verdict", "reason")}, ensure_ascii=False))
    print(f"receipt: {out}")
    return code


# One shared helper. Loaded by path in tests, so put this directory on sys.path.
_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from xintake_walk import walk_nofollow  # noqa: E402


def run(cmd: list[str], cwd: str | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


# None until the first probe. Empty tuple means bubblewrap is unusable here.
_BWRAP_FLAGS: tuple[str, ...] | None = None


def _child_env(home: str, path: str = "/usr/bin:/bin", extra: dict | None = None) -> dict[str, str]:
    """An environment with nothing copied from this process. HOME is always `home`."""
    env = {"PATH": path, "TERM": "dumb", "LANG": "C.UTF-8", "NO_COLOR": "1"}
    for key, value in (extra or {}).items():
        if key != "HOME":
            env[str(key)] = str(value)
    env["HOME"] = home
    return env


def _spawn(cmd: list[str], env: dict, cwd: str | None, timeout: float) -> subprocess.CompletedProcess:
    """New session. On timeout SIGKILL the process group so a forked grandchild dies too."""
    proc = subprocess.Popen(
        cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        raise subprocess.TimeoutExpired(cmd, timeout)
    return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


def _probe_bwrap() -> tuple[str, ...]:
    bw = shutil.which("bwrap")
    if not bw:
        return ()
    flags = ["--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--unshare-net", "--die-with-parent"]
    with tempfile.TemporaryDirectory(prefix="pfy-bwrap-probe-") as home:
        env = _child_env(home)
        for extra in (["--unshare-pid"], []):
            try:
                probe = _spawn([bw, *flags, *extra, "/bin/true"], env, None, 10)
            except (OSError, subprocess.TimeoutExpired):
                continue
            if probe.returncode == 0:
                return tuple([bw, *flags, *extra])
    return ()


def _bwrap_prefix(writable: list[str]) -> list[str]:
    global _BWRAP_FLAGS
    if _BWRAP_FLAGS is None:
        _BWRAP_FLAGS = _probe_bwrap()
    if not _BWRAP_FLAGS:
        return []
    prefix = list(_BWRAP_FLAGS)
    for directory in writable:
        prefix += ["--bind", directory, directory]
    return prefix


def run_isolated(
    cmd: list[str],
    *,
    home: str,
    cwd: str | None = None,
    timeout: float = 120,
    path: str = "/usr/bin:/bin",
    extra: dict | None = None,
    bwrap_writable: list[str] | None = None,
) -> subprocess.CompletedProcess:
    """Start the one kind of child a new x-intake smoke is allowed to start.

    `home` is the child's HOME and must be a temp directory the caller owns. PATH, TERM, LANG,
    NO_COLOR, and the explicit `extra` keys are the only other variables. This process's environment
    is not copied. The child is a new session; a timeout SIGKILLs that process group, grandchildren
    included. When `bwrap_writable` is a list and bubblewrap can run, the command is prefixed with a
    read-only root and no network, plus --unshare-pid when that flag works. None skips bubblewrap.
    """
    argv = list(cmd)
    if bwrap_writable is not None:
        prefix = _bwrap_prefix(bwrap_writable)
        if prefix:
            argv = prefix + argv
    return _spawn(argv, _child_env(home, path, extra), cwd, timeout)


def find_bin(env: str, tmp_rel: str, name: str) -> str | None:
    for c in (os.environ.get(env), str(TMP / tmp_rel), shutil.which(name)):
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def kernel_at_least(major: int, minor: int) -> bool:
    try:
        parts = platform.release().split("-")[0].split(".")
        return (int(parts[0]), int("".join(ch for ch in parts[1] if ch.isdigit()) or 0)) >= (major, minor)
    except (IndexError, ValueError):
        return False


def timeout_reason(step: str, seconds: float) -> str:
    """The only timeout reason text an x-intake smoke records."""
    return f"{step} timeout after {seconds:g}s"


def pinned(r: dict, var: str, pin: str, lower: bool = False) -> str:
    """$var when set (source env), else the pin (source pin). WARN only when the override differs.

    SHA variables (lower=True, or a name ending in SHA256) compare case-insensitively.
    Recorded at r["expected"][var] = {value, source, pin}.
    """
    raw = (os.environ.get(var) or "").strip()
    if lower:
        raw = raw.lower()
    value = raw or pin
    r.setdefault("expected", {})[var] = {"value": value, "source": "env" if raw else "pin", "pin": pin}
    if raw:
        sha = lower or var.upper().endswith("SHA256")
        same = raw.lower() == pin.lower() if sha else raw == pin
        if not same:
            print(f"WARN: ${var}={raw} overrides the pinned {pin}", file=sys.stderr)
    return value


def smoke_qwen38flash(r: dict) -> int:
    base = os.environ.get("QWEN38_URL")
    r["note"] = "serving check only; quality vs qwen3.6:35b needs the 48-case decision benchmark"
    if not base:
        r["reason"] = ("set QWEN38_URL to an OpenAI-compatible base already serving a Qwen3.8-Flash-Next GGUF "
                       "(smallest upstream quants are ~66-68 GB: ISTA-DASLab GSQ-RCO Q2_0 / IQ2_XS). The smoke never "
                       "loads a model itself; start llama-server under ~/DEVELOP/pfy-mentat/tmp and respect the "
                       "nimo memory edge (Entries 089-094)")
        return 2
    body = json.dumps({"model": os.environ.get("QWEN38_MODEL", "qwen3.8-flash"), "temperature": 0, "max_tokens": 64,
                       "messages": [{"role": "user", "content": "Reply with exactly this token and nothing else: PFY-OK-095"}]}).encode()
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        r["reason"] = f"no usable response from {base}: {e}"
        return 2 if isinstance(e, urllib.error.URLError) and not isinstance(e, urllib.error.HTTPError) else 1
    r["seconds"] = round(time.time() - t, 1)
    try:
        text = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        r["reason"] = f"unexpected response shape: {str(data)[:400]}"
        return 1
    r["output"] = text[-300:]
    r["usage"] = data.get("usage")
    if "PFY-OK-095" not in text:
        r["reason"] = "model answered but did not return the exact token"
        return 1
    return 0


def smoke_sandlock(r: dict) -> int:
    b = find_bin("SANDLOCK_BIN", "sandlock/sandlock", "sandlock")
    r["bin"], r["kernel"] = b, platform.release()
    if platform.system() != "Linux" or not kernel_at_least(6, 12):
        r["reason"] = f"Sandlock needs Linux 6.12+ (Landlock ABI v6); this host is {platform.system()} {platform.release()}"
        return 2
    if not b:
        r["reason"] = ("no sandlock binary. Operator: unpack the upstream release tarball "
                       "(sandlock-x86_64-unknown-linux-gnu.tar.gz, check its sha256) into ~/DEVELOP/pfy-mentat/tmp/sandlock/ "
                       "-- no root, no cargo install to ~/.cargo")
        return 2
    with tempfile.TemporaryDirectory(prefix="pfy-sandlock-") as d:
        ok, no = Path(d, "ok"), Path(d, "no")
        ok.mkdir(); no.mkdir()
        ro = [x for x in ("/usr", "/lib", "/lib64", "/bin", "/etc") if os.path.exists(x)]
        cmd = [b, "run"] + sum((["-r", x] for x in ro), []) + ["-w", str(ok), "--", "/bin/sh", "-c",
               f"echo allowed > {ok}/a; echo denied > {no}/b; exit 0"]
        try:
            p = run(cmd, timeout=60)
        except subprocess.TimeoutExpired:
            r["reason"] = timeout_reason("sandlock run", 60)
            return 1
        r["output"] = (p.stdout + p.stderr)[-600:]
        allowed, leaked = (ok / "a").exists(), (no / "b").exists()
        r["allowed_write_landed"], r["denied_write_leaked"] = allowed, leaked
        if leaked:
            r["reason"] = "write outside the granted dir succeeded: confinement not enforced"
            return 1
        if not allowed:
            r["reason"] = f"granted write did not land (rc={p.returncode})"
            return 1
    return 0


def smoke_foremerge(r: dict) -> int:
    b = find_bin("FOREMERGE_BIN", "foremerge/foremerge", "foremerge")
    r["bin"] = b
    r["note"] = "local ledger in a throwaway repo; no `foremerge setup` (it edits client MCP configs)"
    if not b:
        r["reason"] = ("no foremerge binary. Operator: unpack the upstream release tarball "
                       "(foremerge-v0.5.1-x86_64-unknown-linux-gnu.tar.gz, check its sha256) into "
                       "~/DEVELOP/pfy-mentat/tmp/foremerge/ -- not install.sh (writes ~/.local/bin), no `setup`")
        return 2
    if not shutil.which("git"):
        r["reason"] = "git not on PATH"
        return 2

    def fm(args: list[str], cwd: str) -> dict:
        p = run([b, "--json"] + args, cwd=cwd, timeout=60)
        try:
            return json.loads(p.stdout)
        except ValueError:
            return {"ok": False, "raw": (p.stdout + p.stderr)[-400:], "rc": p.returncode}

    with tempfile.TemporaryDirectory(prefix="pfy-foremerge-") as d:
        g = ["git", "-c", "user.email=smoke@localhost", "-c", "user.name=smoke"]
        run(["git", "init", "-q"], cwd=d)
        run(g + ["commit", "-q", "--allow-empty", "-m", "init"], cwd=d)
        steps = {"init": fm(["init"], d)}
        agent = fm(["agent", "register", "--name", "smoke-a", "--model", "none"], d)
        aid = (agent.get("data") or {}).get("id")
        if not aid:
            r["steps"] = {"init": steps["init"], "agent": agent}
            r["reason"] = "agent register returned no id (CLI shape changed?)"
            return 1
        fm(["intent", "publish", "--agent", aid, "--task", "T1", "--summary",
            "Replace PaymentService with StripePaymentService", "--scope", "symbol:PaymentService=replace"], d)
        clash = fm(["conflicts", "check", "--intent", "Add PayPal support to PaymentService",
                    "--scope", "symbol:PaymentService=extend"], d)
        clean = fm(["conflicts", "check", "--intent", "Edit README", "--scope", "file:README.md=modify"], d)
    hits = [c for c in (clash.get("data") or {}).get("conflicts", []) if c.get("severity") == "HIGH"]
    stray = (clean.get("data") or {}).get("conflicts", [])
    r["high_conflicts"] = [{k: c.get(k) for k in ("kind", "severity", "explanation")} for c in hits]
    r["unrelated_conflicts"] = len(stray) if isinstance(stray, list) else stray
    if not hits:
        r["reason"] = f"expected a HIGH replace-vs-extend conflict, got {str(clash)[:400]}"
        return 1
    if stray:
        r["reason"] = "unrelated scope reported a conflict (false positive)"
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", required=True, choices=["qwen38flash", "sandlock", "foremerge"])
    a = ap.parse_args()
    receipt = {"entry": a.entry, "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "host": os.uname().nodename}
    code = {"qwen38flash": smoke_qwen38flash, "sandlock": smoke_sandlock, "foremerge": smoke_foremerge}[a.entry](receipt)
    return write(a.entry, receipt, code)


if __name__ == "__main__":
    sys.exit(main())
