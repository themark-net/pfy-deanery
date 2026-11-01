#!/usr/bin/env python3
"""Operate-or-FAIL smokes for X intake Entries 122-124 (llm-router, HarnessRouter CE, Squadra). Stdlib only.

Usage: python3 examples/x-intake-local/smoke_122_124.py --entry llmrouter|harnessrouter|squadra

Same contract and receipts as smoke.py next to it (whose helpers it reuses): exit 0 = PASS, 1 = the tool ran but
the check failed, 2 = can't run here (prereq missing; reason recorded). Writes pipelines/smoke/<entry>/latest.json.
Never installs anything (harnessrouter's `docker run` may pull the pinned image digest). Every child process starts
through `run_isolated` in smoke.py (fresh temp HOME, env limited to PATH/HOME/TERM/LANG/NO_COLOR plus the variables
named below; nothing copied from this process, so no provider key is ever seen; a timeout SIGKILLs the process
group). No smoke calls a model, adds a provider key or starts an agent CLI.
PFY_XINTAKE_TIMEOUT (float seconds, > 0) overrides the 600s per-command timeout.
Real HOME: llmrouter and squadra snapshot the real-HOME dirs the tool writes by default (~/.llm-router;
~/.local/state/squadra, ~/.cache/squadra and ~/.squadra; content-hashed) and compare them in a finally, also on timeout:
checks.real_home_untouched, and any change FAILs (exit 1), even when bwrap is unavailable.

  llmrouter      $LLMROUTER_BIN, then ~/DEVELOP/pfy-mentat/tmp/llm-router/.venv/bin/llm-router (a venv with
                 `pip install llm-routing==15.4.0`), then PATH. The package version, read with the python next to
                 the binary, is pinned to 15.4.0 ($LLMROUTER_VERSION overrides). Under bwrap with no network when that
                 works: the offline heuristic classifier (`llm_router.classify.classify_signals`, no model) must call
                 "what does os.path.join do?" a confident simple query and "implement a Redis-backed rate limiter ..."
                 confident code; `llm-router demo` must exit 0 and print its routing table; the temp HOME must stay
                 empty (no ~/.llm-router written). `install` is never run, so no host config or hook is touched.
  harnessrouter  Needs docker ($DOCKER_BIN, ~/DEVELOP/pfy-mentat/tmp/docker/docker, or PATH); exit 2 without it, or
                 if 127.0.0.1:$HR_SMOKE_PORT (default 3917) already answers. Runs the image pinned by digest
                 ($HR_IMAGE overrides, with a WARN) as container "pfy-hr-smoke" with volume "pfy-hr-smoke" bound to that loopback
                 port only (exit 2, removing nothing, if that container or volume already exists), waits for the Console to answer (< 500), then POST /api/harness/v1/responses with no key
                 must be refused (401 or 403). Always removes the container and the volume after, including when
                 SIGTERM arrives during docker run (exit 1, reason names SIGTERM). No provider key,
                 no CE API key, no task. For a non-default socket set $HR_DOCKER_HOST.
  squadra        $SQUADRA_DIR, then ~/DEVELOP/pfy-mentat/tmp/squadra: a checkout of dagoSte/squadra at tag v3.10.1
                 holding scripts/squadra.py; `--version` pinned to 3.10.1 ($SQUADRA_VERSION overrides). Needs
                 python3 >= 3.12 and git. Under bwrap when it works, in a temp git repo with one commit and a registry
                 outside it: `init --temporary`, register a coordinator and a builder (client "manual"), record one
                 task; `doctor` must report integrity "passed" with the assignment pending acknowledgement, `status`
                 must show the task, the project repo must stay clean, and the temp HOME must stay empty.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from smoke import TMP, find_bin, pinned, run_isolated, timeout_reason, write

LR_PIN = "15.4.0"
HR_IMAGE = "harnessrouter/harnessrouter@sha256:db412234ea41162e70ecf92f0140402f7cf1fc2a7e00db9180906c7447eb9ad5"  # 0.34.2
SQ_PIN = "3.10.1"
GIT_ID = {"GIT_AUTHOR_NAME": "pfy-smoke", "GIT_AUTHOR_EMAIL": "smoke@localhost",
          "GIT_COMMITTER_NAME": "pfy-smoke", "GIT_COMMITTER_EMAIL": "smoke@localhost"}


def tmo() -> float:
    try:
        v = float(os.environ.get("PFY_XINTAKE_TIMEOUT", ""))
        return v if v > 0 else 600.0
    except ValueError:
        return 600.0


# Real-HOME dirs each tool writes by default (read from upstream source): llm-router's state dir (paths.py
# llm_router_home, every hook's fallback ~/.llm-router); Squadra's selftest folder (selftest.py
# ~/.local/state/squadra) and usage cache (usage_cache.py ~/.cache/squadra). HarnessRouter runs in Docker only.
WATCH = {"llmrouter": (".llm-router",),
         "squadra": (".local/state/squadra", ".cache/squadra", ".squadra")}  # .squadra: plugin store


def tree_sig(p: Path) -> str | None:
    if not p.exists():
        return None
    h = hashlib.sha256()
    for f in sorted(p.rglob("*")):
        # content hash, not mtime: a same-size in-place edit that restores mtime still changes the signature
        try:
            if f.is_file():
                fh = hashlib.sha256()
                with f.open("rb") as fp:  # streamed in 1 MiB chunks, so a huge file doesn't load into RAM
                    for chunk in iter(lambda: fp.read(1 << 20), b""):
                        fh.update(chunk)
                h.update(f"{f}:{f.stat().st_size}:{fh.hexdigest()}\n".encode())
            else:
                h.update(f"{f}:dir\n".encode())
        except OSError:
            h.update(f"{f}:unreadable\n".encode())
    return h.hexdigest()


def watched(entry: str, body, r: dict) -> int:
    """Run body(r, checks) with the real HOME watched. The finally runs on timeout too, so the receipt keeps the
    partial checks and real_home_untouched (the smoke_119_121 pattern); any change FAILs."""
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
    return finish(r, checks, r.pop("_ok_reason", ""))  # a step that failed early never set it


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


CLASSIFY = """
import json
from llm_router.classify import classify_signals
out = {}
for key, p in (("query", "what does os.path.join do?"),
               ("code", "implement a Redis-backed rate limiter with sliding windows, tests and a migration plan")):
    s = classify_signals(p)
    out[key] = {"task": s.task_type.value, "complexity": getattr(s.complexity, "value", str(s.complexity)),
                "confident": bool(s.confident)}
print(json.dumps(out))
"""


def smoke_llmrouter(r: dict) -> int:
    b = find_bin("LLMROUTER_BIN", "llm-router/.venv/bin/llm-router", "llm-router")
    if not b:
        r["reason"] = "llm-router not found ($LLMROUTER_BIN, tmp/llm-router/.venv, PATH); see the handoff"
        return 2
    r["bin"] = b
    py = Path(b).parent / "python"
    if not os.access(py, os.X_OK):
        r["reason"] = f"no python next to {b}, so the package version can't be checked"
        return 2
    return watched("llmrouter", lambda rr, checks: _llmrouter(rr, b, py, checks), r)


def _llmrouter(r: dict, b: str, py: Path, checks: dict) -> int | None:
    want = pinned(r, "LLMROUTER_VERSION", LR_PIN)
    with tempfile.TemporaryDirectory(prefix="pfy-llmrouter-") as td:
        home = Path(td, "home")
        home.mkdir()
        kw = {"home": str(home), "cwd": td, "bwrap_writable": [td]}
        v = iso([str(py), "-c", "import llm_router; print(llm_router.__version__)"], "llm-router version", **kw)
        r["version_out"] = (v.stdout + v.stderr).strip()[:200]
        if v.returncode != 0 or v.stdout.strip() != want:
            r["reason"] = f"llm-router version is not {want}: {r['version_out']!r} (set $LLMROUTER_VERSION)"
            return 2
        c = iso([str(py), "-c", CLASSIFY], "llm-router classify", **kw)
        try:
            got = json.loads(c.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            got = None
        r["classify"] = got or (c.stdout + c.stderr).strip()[-400:]
        ok = isinstance(got, dict)
        checks["classify_query_simple"] = ok and got["query"] == {"task": "query", "complexity": "simple",
                                                                  "confident": True}
        checks["classify_code"] = ok and got["code"]["task"] == "code" and got["code"]["confident"]
        d = iso([b, "demo"], "llm-router demo", **kw)
        out = d.stdout + d.stderr
        r["demo_rc"] = d.returncode
        r["demo_tail"] = [ln.rstrip() for ln in out.strip().splitlines()][-8:]
        checks["demo_exit_0"] = d.returncode == 0
        checks["demo_prints_table"] = "Complexity" in out and "Model" in out
        checks["home_untouched"] = not any(home.iterdir())
    r["_ok_reason"] = ("offline classifier and demo ran with no key or network; temp HOME stayed empty and the real "
                       "~/.llm-router was unchanged")
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


class _Sigterm(Exception):
    """SIGTERM arrived. Raised so the harnessrouter finally still removes the container."""


def _on_sigterm(_signum, _frame) -> None:
    raise _Sigterm("SIGTERM")


def smoke_harnessrouter(r: dict) -> int:
    docker = find_bin("DOCKER_BIN", "docker/docker", "docker")
    if not docker:
        r["reason"] = "docker is not available (HarnessRouter CE ships only as a Docker image)"
        return 2
    image = pinned(r, "HR_IMAGE", HR_IMAGE)  # WARNs on stderr when $HR_IMAGE overrides the digest
    r["image"] = image
    try:
        port = int(os.environ.get("HR_SMOKE_PORT", "3917"))
    except ValueError:
        r["reason"] = "HR_SMOKE_PORT is not an integer"
        return 2
    base = f"http://127.0.0.1:{port}"
    if http("GET", base + "/") != 0:
        r["reason"] = f"something is already listening on 127.0.0.1:{port} (set HR_SMOKE_PORT)"
        return 2
    path = f"{Path(docker).parent}:/usr/bin:/bin"
    extra = {}
    if os.environ.get("HR_DOCKER_HOST"):
        extra["DOCKER_HOST"] = os.environ["HR_DOCKER_HOST"]
        r["docker_host"] = extra["DOCKER_HOST"]
    checks: dict[str, bool] = {}
    with tempfile.TemporaryDirectory(prefix="pfy-hr-") as home:

        def dk(*args: str, tag: str) -> subprocess.CompletedProcess:
            return iso([docker, *args], tag, home=home, path=path, extra=extra, bwrap_writable=None)

        if dk("version", "--format", "{{.Server.Version}}", tag="docker version").returncode != 0:
            r["reason"] = "the docker daemon is not reachable"
            return 2
        # never adopt or delete someone else's container or volume
        if dk("container", "inspect", "pfy-hr-smoke", tag="docker container inspect").returncode == 0:
            r["reason"] = "a container named pfy-hr-smoke already exists; remove it yourself (nothing was removed)"
            return 2
        if dk("volume", "inspect", "pfy-hr-smoke", tag="docker volume inspect").returncode == 0:
            r["reason"] = "a volume named pfy-hr-smoke already exists; remove it yourself (nothing was removed)"
            return 2
        # Default SIGTERM ends the process inside docker run, so this finally never starts and the
        # container stays. Raising lets the same rm and volume rm below still run.
        previous_sigterm = signal.signal(signal.SIGTERM, _on_sigterm)
        try:
            up = dk("run", "-d", "--name", "pfy-hr-smoke", "-p", f"127.0.0.1:{port}:3000",
                    "-v", "pfy-hr-smoke:/data", image, tag="docker run")
            r["run_tail"] = (up.stdout + up.stderr).strip().splitlines()[-4:]
            if up.returncode != 0:
                r["reason"] = "docker run failed"
                return 1
            deadline = time.time() + min(tmo(), 420)
            st = 0
            while time.time() < deadline:
                st = http("GET", base + "/")
                if 0 < st < 500:
                    break
                time.sleep(5)
            r["console_status"] = st
            checks["console_answers"] = 0 < st < 500
            body = json.dumps({"model": "none", "input": "ping"}).encode()
            nk = http("POST", base + "/api/harness/v1/responses", body, {"Content-Type": "application/json"})
            r["responses_status_no_key"] = nk
            checks["api_refuses_no_key"] = nk in (401, 403)
        except _Sigterm:
            r["reason"] = "SIGTERM during docker run"
            return 1
        finally:
            signal.signal(signal.SIGTERM, previous_sigterm)
            r["checks"] = checks  # partial checks survive a timeout
            # each cleanup step runs even if the one before timed out; a cleanup timeout never replaces an
            # earlier failure reason (it is kept in cleanup_reason)
            for key, args, tag in (("rm_rc", ("rm", "-f", "pfy-hr-smoke"), "docker rm"),
                                   ("volume_rm_rc", ("volume", "rm", "-f", "pfy-hr-smoke"), "docker volume rm")):
                try:
                    r[key] = dk(*args, tag=tag).returncode
                except TimeoutError as e:
                    r[key] = None
                    r.setdefault("cleanup_reason", str(e))
        # a non-zero rm or volume rm is a FAIL too, not only a timeout (cleanup_reason keeps the timeout text);
        # finish() only writes the "removed after" PASS reason when every check, cleanup_ok included, is true
        checks["cleanup_ok"] = r.get("rm_rc") == 0 and r.get("volume_rm_rc") == 0
        if r.get("cleanup_reason"):
            # a FAIL, but as a check: the happy-path reason (failed checks) is kept, not replaced by the timeout
            checks["cleanup_ok"] = False
    return finish(r, checks, "pinned CE image came up on loopback and refused a keyless API call; removed after")


def smoke_squadra(r: dict) -> int:
    d = Path(os.environ.get("SQUADRA_DIR") or (TMP / "squadra"))
    r["dir"] = str(d)
    script = d / "scripts" / "squadra.py"
    if not script.exists():
        r["reason"] = f"Squadra checkout not staged ({script} missing); see the handoff"
        return 2
    py = shutil.which("python3", path="/usr/local/bin:/usr/bin:/bin")
    git = shutil.which("git", path="/usr/local/bin:/usr/bin:/bin")
    if not py or not git:
        r["reason"] = "python3 or git not found in /usr/local/bin:/usr/bin:/bin"
        return 2
    return watched("squadra", lambda rr, checks: _squadra(rr, script, py, git, checks), r)


def _squadra(r: dict, script: Path, py: str, git: str, checks: dict) -> int | None:
    want = pinned(r, "SQUADRA_VERSION", SQ_PIN)
    with tempfile.TemporaryDirectory(prefix="pfy-squadra-") as td:
        home, proj, reg = Path(td, "home"), Path(td, "proj"), Path(td, "reg")
        home.mkdir()
        proj.mkdir()
        kw = {"home": str(home), "cwd": td, "path": "/usr/local/bin:/usr/bin:/bin", "bwrap_writable": [td]}
        pv = iso([py, "-c", "import sys; print(sys.version_info >= (3, 12))"], "python version", **kw)
        if pv.stdout.strip() != "True":
            r["reason"] = "Squadra needs python3 >= 3.12"
            return 2
        sq = [py, "-B", str(script)]
        v = iso(sq + ["--version"], "squadra version", **kw)
        r["version_out"] = (v.stdout + v.stderr).strip()[:200]
        if v.returncode != 0 or v.stdout.strip() != want:
            r["reason"] = f"Squadra version is not {want}: {r['version_out']!r} (set $SQUADRA_VERSION)"
            return 2
        (proj / "a.py").write_text("x = 1\n")
        for argv in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "init"]):
            g = iso([git, "-C", str(proj), *argv], "git " + argv[0], **{**kw, "extra": GIT_ID})
            if g.returncode != 0:
                r["reason"] = f"could not build the temp git repo: {(g.stdout + g.stderr).strip()[:160]}"
                return 1
        scope = Path(td, "scope.json")
        scope.write_text('["a.py"]\n')
        root = ["--root", str(reg)]
        steps = {
            "init": ["init", "--name", "pfy-smoke", "--project", str(proj), "--lang", "en", "--temporary"],
            "agent_coordinator": ["agent", "--id", "c1", "--identity", "c1", "--role", "coordinator",
                                  "--client", "manual", "--repo", str(proj)],
            "agent_builder": ["agent", "--id", "w1", "--identity", "w1", "--role", "builder",
                              "--client", "manual", "--repo", str(proj)],
            "task": ["task", "--id", "T1", "--title", "pfy smoke task", "--actor", "c1", "--owner", "w1",
                     "--repo", str(proj), "--scope-file", str(scope)],
        }
        for name, argv in steps.items():
            s = iso(sq + argv + root, "squadra " + name, **kw)
            checks[f"{name}_exit_0"] = s.returncode == 0
            if s.returncode != 0:
                r[f"{name}_tail"] = (s.stdout + s.stderr).strip().splitlines()[-4:]
                return None
        doc = iso(sq + ["doctor"] + root, "squadra doctor", **kw)
        try:
            dj = json.loads(doc.stdout)
        except ValueError:
            dj = {}
        r["doctor"] = {k: dj.get(k) for k in ("events", "integrity", "pending_ack")}
        checks["doctor_integrity_passed"] = doc.returncode == 0 and dj.get("integrity") == "passed"
        checks["doctor_assignment_pending"] = "assign-T1" in (dj.get("pending_ack") or [])
        st = iso(sq + ["status"] + root, "squadra status", **kw)
        checks["status_shows_task"] = st.returncode == 0 and "pfy smoke task" in st.stdout
        cl = iso([git, "-C", str(proj), "status", "--porcelain"], "git status", **kw)
        checks["project_repo_clean"] = cl.returncode == 0 and cl.stdout.strip() == ""
        checks["home_untouched"] = not any(home.iterdir())
    r["_ok_reason"] = ("registry, two seats and a task recorded locally; integrity passed; project repo clean, temp "
                       "HOME empty, real ~/.local/state/squadra and ~/.cache/squadra unchanged")
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", required=True, choices=["llmrouter", "harnessrouter", "squadra"])
    a = ap.parse_args()
    receipt = {"entry": a.entry, "script": "examples/x-intake-local/smoke_122_124.py",
               "started": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    fn = {"llmrouter": smoke_llmrouter, "harnessrouter": smoke_harnessrouter, "squadra": smoke_squadra}[a.entry]
    try:
        code = fn(receipt)
    except TimeoutError as e:
        receipt.pop("_ok_reason", None)
        receipt["reason"] = str(e)
        if receipt.get("checks", {}).get("real_home_untouched") is False:
            receipt["reason"] += f"; real HOME {', '.join('~/' + d for d in WATCH.get(a.entry, ()))} changed"
        code = 1
    except Exception as e:  # any other crash still writes a FAIL receipt (checks were saved by watched()'s finally)
        receipt.pop("_ok_reason", None)
        receipt["reason"] = f"unexpected {type(e).__name__}: {e}"
        if receipt.get("checks", {}).get("real_home_untouched") is False:
            receipt["reason"] += f"; real HOME {', '.join('~/' + d for d in WATCH.get(a.entry, ()))} changed"
        code = 1
    return write(a.entry, receipt, code)


if __name__ == "__main__":
    sys.exit(main())
