#!/usr/bin/env python3
"""Operate-or-FAIL smokes for X intake Entries 146-147 (skill-up, HiRoute). Stdlib only.

Usage: python3 examples/x-intake-local/smoke_146_147.py --entry skill-up|hiroute

Same contract and receipts as smoke.py (whose helpers it reuses, with smoke_128_130, smoke_140_142 and smoke_143_145):
exit 0 = PASS, 1 = the tool ran but a check failed, 2 = can't run here (prereq missing; reason recorded). Writes
pipelines/smoke/<entry>/latest.json. Never downloads or builds anything. Every child starts through `run_isolated`
(fresh temp HOME, env limited to PATH/HOME/TERM/LANG/NO_COLOR plus the variables named below, a timeout SIGKILLs the
process group) under bwrap with no network when bwrap works. No smoke calls a model, adds a key or touches a real
agent's skill, MCP or systemd config. PFY_XINTAKE_TIMEOUT and explicit binary overrides behave as in smoke_140_142.py
(a bad value exits 2 before anything runs).
Real HOME: each entry fingerprints the real-HOME paths the tool could write before the run and again in a finally.
Any change FAILs (exit 1) and is listed in real_home_changed. Only those paths are watched.

  skill-up  $SKILLUP_BIN, else $PFY_TMP/skill-up/skill-up, else `skill-up` on PATH (the v0.14.0
            skill-up_0.14.0_linux_amd64.tar.gz release asset unpacked; binary sha256 pinned to SKILLUP_SHA256,
            `--version` to SKILLUP_VERSION). Needs python3 on the system PATH for the stub agent. The smoke writes a
            fixture skill in a temp dir: an eval.yaml (environment none, no skills, no MCP) whose engine is a custom
            local command (a python stub that answers "pong-7" only when the prompt contains "ping") and two cases
            that both expect "pong-7". Checks: `validate` exits 0 and reports 2 cases; `run --output-dir` exits 1
            (one case fails by design) with "1 passed, 1 failed, 0 errors"; result.json shows ping-pass PASS with
            response pong-7 and hello-fail FAIL with must_contain evidence; the stub got a SessionInput naming both
            case ids; skill-up's temp workspaces land in the temp TMPDIR; the temp HOME stays empty. Watched:
            ~/.skill-up, ~/.config/skill-up. No model, provider, docker or OpenSandbox runtime is used.
  hiroute   $HIROUTE_DIR, else $PFY_TMP/hiroute, holding the v0.3.1 linux x86_64 release archive
            (hiroute-0.3.1-13856abd873d-x86_64-unknown-linux-gnu.tar.gz), its manifest (.tar.gz.json) and the
            standalone installer (standalone.py from hiroute.ai/install/), all three sha256-pinned
            (HIROUTE_ARCHIVE_SHA256, HIROUTE_MANIFEST_SHA256, HIROUTE_INSTALLER_SHA256). Needs bwrap (the gateway
            listens on 127.0.0.1 and must stay in a private network namespace; without bwrap exit 2) and python3 on
            the system PATH. hirouted refuses to start without the installer's marker, so the smoke runs
            `standalone.py install --manifest --archive --console-mode off` with HOME, XDG_* and TMPDIR all in a temp
            dir (offline; its `systemctl --user daemon-reload` has no bus there and its unit file stays in the temp
            HOME), then a driver in the same sandbox starts `hiroute service run`, waits for local control and
            checks: installed version 0.3.1 with every installed path under the temp HOME; service status
            local_control_ready; system status daemon role_all, gateway ready; gateway show ready on a 127.0.0.1
            address; with no source, route or grant configured /v1/models answers 503 GATEWAY_PUBLICATION_UNAVAILABLE
            and /v1/chat/completions 401 GATEWAY_GRANT_UNAUTHORIZED (fails closed, nothing forwarded); `schema list`
            exposes routing.preview and decision.services.test; the daemon exits on SIGTERM. Watched: ~/.local/bin/
            hiroute, ~/.local/bin/hirouted, ~/.local/lib/hiroute, ~/.local/share/hiroute, ~/.local/state/hiroute,
            ~/.config/systemd/user/ai.hiroute.cli.service, ~/.agents/skills/hiroute-management,
            ~/.claude/skills/hiroute-management. NOT exercised: routing a real request to a model (needs a source,
            a published route and an agent grant; that is the trial, not this smoke).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

from smoke import TMP, _bwrap_prefix, find_bin, pinned, write
from smoke_128_130 import as_json, finish, home_sig
from smoke_140_142 import SYS_PATH, bad_override, iso, system_python, timeout_problem
from smoke_143_145 import sha256_file

SKILLUP_PIN = "0.14.0"
SKILLUP_SHA = "5b1bdd0a30f57653c8f6a3a679e992b29982fe18709b2556d53a6f9ea1c85ab6"
HIROUTE_PIN = "0.3.1"
HIROUTE_ARCHIVE = "hiroute-0.3.1-13856abd873d-x86_64-unknown-linux-gnu.tar.gz"
HIROUTE_ARCHIVE_SHA = "dfa35ada12fcef9d0d2e10e680422cd0bf6a0454a8809c27879b74ba932d21aa"
HIROUTE_MANIFEST_SHA = "e7e313ac6d709ecaed9411f1c01121542d512f572bbe40542f8f2dd6a9474509"
HIROUTE_INSTALLER_SHA = "3a7ef92f0dd55119aa31b19877e3ac34dedcd5b4b32cbb012ef396b70649b7c2"
WATCH = {"skill-up": (".skill-up", ".config/skill-up"),
         "hiroute": (".local/bin/hiroute", ".local/bin/hirouted", ".local/lib/hiroute", ".local/share/hiroute",
                     ".local/state/hiroute", ".config/systemd/user/ai.hiroute.cli.service",
                     ".agents/skills/hiroute-management", ".claude/skills/hiroute-management")}


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


# ---------------------------------------------------------------- skill-up
STUB_AGENT = r'''#!/usr/bin/env python3
import json, os, sys
d = json.load(open(sys.argv[1]))
msgs = d.get("messages") or []
text = " ".join(str(m.get("content", "")) for m in msgs if isinstance(m, dict))
with open(os.environ["STUB_LOG"], "a") as f:
    f.write(json.dumps({"case_id": d.get("case_id"), "keys": sorted(d)}) + "\n")
print(json.dumps({"exit_code": 0, "final_message": "pong-7" if "ping" in text else "no-ping"}))
'''
SKILL_MD = "---\nname: sut\ndescription: pfy smoke fixture skill (no instructions)\n---\n\nFixture only.\n"
EVAL_YAML = """schema_version: v1alpha1
environment:
  type: none
mcp:
  servers: []
skills: []
engine:
  name: pfy-stub-agent
  custom:
    transport: local
    response_format: session_result
    local:
      command: ${STUB_AGENT_BIN}
      args:
        - ${input_file}
cases:
  files:
    - evals/cases/pass.yaml
    - evals/cases/fail.yaml
  defaults:
    timeout_seconds: 60
    max_turns: 1
  parallelism: 1
report:
  formats: [json]
"""
CASES = {"pass.yaml": 'id: ping-pass\ntitle: stub answers pong to ping\ninput:\n  prompt: please ping the stub\n'
                      'expect:\n  must_contain:\n    - "pong-7"\n',
         "fail.yaml": 'id: hello-fail\ntitle: no ping so the expectation must fail\ninput:\n  prompt: say hello\n'
                      'expect:\n  must_contain:\n    - "pong-7"\n'}


def smoke_skillup(r: dict) -> int:
    bad = bad_override("SKILLUP_BIN")
    if bad:
        r["reason"] = bad
        return 2
    su = find_bin("SKILLUP_BIN", "skill-up/skill-up", "skill-up")
    r["skill_up"] = su
    if not su:
        r["reason"] = ("skill-up not found ($SKILLUP_BIN, tmp/skill-up/skill-up, PATH); unpack the v0.14.0 "
                       "skill-up_0.14.0_linux_amd64.tar.gz release asset there after checking its digest, see the handoff")
        return 2
    python = system_python()
    if not python:
        r["reason"] = f"python3 is needed in {SYS_PATH} for the stub agent"
        return 2
    want_sha = pinned(r, "SKILLUP_SHA256", SKILLUP_SHA, lower=True)
    have_sha = sha256_file(Path(su))
    r["sha256"] = have_sha
    if have_sha != want_sha:
        r["reason"] = f"skill-up binary sha256 is {have_sha}, not {want_sha} (set $SKILLUP_SHA256)"
        return 2
    want = pinned(r, "SKILLUP_VERSION", SKILLUP_PIN)
    return watched("skill-up", lambda rr, checks: _skillup(rr, su, python, want, checks), r)


def _skillup(r: dict, su: str, python: str, want: str, checks: dict) -> int | None:
    with tempfile.TemporaryDirectory(prefix="pfy-skillup-") as tdn:
        td = Path(tdn)
        home, ttmp, out, skill = td / "home", td / "tmp", td / "out", td / "sut"
        for p in (home, ttmp, skill / "evals" / "cases"):
            p.mkdir(parents=True)
        stub = td / "stub_agent.py"
        stub.write_text(STUB_AGENT.replace("#!/usr/bin/env python3", "#!" + python, 1))
        stub.chmod(0o755)
        log = td / "stub.log"
        (skill / "SKILL.md").write_text(SKILL_MD)
        (skill / "evals" / "eval.yaml").write_text(EVAL_YAML)
        for n, body in CASES.items():
            (skill / "evals" / "cases" / n).write_text(body)
        extra = {"TMPDIR": str(ttmp), "STUB_AGENT_BIN": str(stub), "STUB_LOG": str(log),
                 "XDG_CONFIG_HOME": str(td / "xdg"), "PYTHONDONTWRITEBYTECODE": "1"}

        def run(args, tag):
            return iso([su, *args], tag, home=str(home), cwd=str(skill), path=SYS_PATH, extra=extra,
                       bwrap_writable=[tdn])
        v = run(["--version"], "skill-up --version")
        r["version_out"] = (v.stdout + v.stderr).strip()[:200]
        if v.returncode != 0 or f"skill-up version {want}" not in v.stdout:
            r["reason"] = f"`skill-up --version` gave {r['version_out']!r}, want 'skill-up version {want}'"
            return 2
        val = run(["validate", str(skill / "evals" / "eval.yaml")], "skill-up validate")
        vt = val.stdout + val.stderr
        r["validate"] = {"rc": val.returncode, "out": vt.strip()[-400:]}
        checks["validate_ok"] = val.returncode == 0 and "is valid" in vt and "2 case" in vt
        res = run(["run", str(skill), "--output-dir", str(out)], "skill-up run")
        rt = res.stdout + res.stderr
        r["run"] = {"rc": res.returncode, "out": rt.strip()[-600:]}
        checks["run_exit_1"] = res.returncode == 1
        checks["run_summary"] = "1 passed, 1 failed, 0 errors" in rt
        results = sorted(out.rglob("result.json"))
        r["result_files"] = [str(p.relative_to(td)) for p in results]
        cases = {}
        if results:
            try:
                cases = {c.get("case_id"): c for c in json.loads(results[0].read_text()).get("case_results", [])}
            except ValueError:
                cases = {}
        ok, bad = cases.get("ping-pass", {}), cases.get("hello-fail", {})
        r["cases"] = {k: {"status": c.get("status"), "response": c.get("response")} for k, c in cases.items()}
        checks["ping_pass"] = ok.get("status") == "PASS" and ok.get("response") == "pong-7"
        ev = " ".join(a.get("evidence", "") for a in (bad.get("grading") or {}).get("assertion_results") or [])
        checks["hello_fail"] = bad.get("status") == "FAIL" and bad.get("response") == "no-ping" and "pong-7" in ev
        seen = []
        if log.is_file():
            for line in log.read_text().splitlines():
                try:
                    seen.append(json.loads(line))
                except ValueError:
                    pass
        r["stub_calls"] = seen
        checks["stub_got_session_input"] = ({s.get("case_id") for s in seen} == {"ping-pass", "hello-fail"}
                                            and all("messages" in s.get("keys", []) for s in seen))
        r["home_files"] = sorted(str(x.relative_to(home)) for x in home.rglob("*"))
        checks["temp_home_empty"] = not r["home_files"]
        fixture = {str(p.relative_to(skill)) for p in skill.rglob("*") if p.is_file()}
        checks["fixture_unchanged"] = fixture == {"SKILL.md", "evals/eval.yaml", "evals/cases/pass.yaml",
                                                  "evals/cases/fail.yaml"}
        r["_ok_reason"] = (f"skill-up {want}: validate + custom local-command engine run (1 PASS, 1 FAIL as designed), "
                           f"result.json graded; temp HOME empty; {', '.join('~/' + d for d in WATCH['skill-up'])} "
                           "untouched")
    return None


# ---------------------------------------------------------------- hiroute
HIROUTE_DRIVER = r'''
import json, os, signal, subprocess, sys, time, urllib.request, urllib.error
H = sys.argv[1]
out = {}


def cli(*a):
    p = subprocess.run([H, *a, "--output", "json"], capture_output=True, text=True, timeout=60)
    try:
        return json.loads(p.stdout)
    except ValueError:
        return {"_rc": p.returncode, "_out": (p.stdout + p.stderr)[-300:]}


def http(url, body=None):
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(),
                                 headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode()[:400]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"[:200]


log = open(os.environ["HR_DAEMON_LOG"], "w")
d = subprocess.Popen([H, "service", "run"], stdout=log, stderr=subprocess.STDOUT)
try:
    ready = False
    for _ in range(60):
        time.sleep(0.5)
        if d.poll() is not None:
            break
        s = cli("service", "status")
        if (s.get("data") or {}).get("local_control_ready"):
            ready = True
            break
    out["ready"] = ready
    out["service"] = cli("service", "status").get("data")
    out["system"] = cli("system", "status").get("data")
    g = cli("gateway", "show").get("data") or {}
    out["gateway"] = {"ready": g.get("ready"), "connect_address": g.get("connect_address")}
    addr = g.get("connect_address")
    if addr:
        out["models"] = http(f"http://{addr}/v1/models")
        out["chat"] = http(f"http://{addr}/v1/chat/completions",
                           {"model": "x", "messages": [{"role": "user", "content": "hi"}]})
    sl = cli("schema", "list").get("data")
    cmds = sl.get("commands", []) if isinstance(sl, dict) else (sl or [])
    out["schema_ids"] = sorted({(c.get("command_id") or c.get("id")) if isinstance(c, dict) else c for c in cmds} - {None})
finally:
    if d.poll() is None:
        d.send_signal(signal.SIGTERM)
        try:
            d.wait(timeout=float(os.environ.get("HR_TERM_WAIT", "45")))
            out["sigterm_exit"] = True
        except subprocess.TimeoutExpired:
            d.kill()
            d.wait()
            out["sigterm_exit"] = False
    else:
        out["sigterm_exit"] = None
        out["daemon_exited_early"] = d.returncode
    log.close()
    print(json.dumps(out))
'''


def term_wait() -> str:
    """$HIROUTE_TERM_WAIT (seconds the driver waits after SIGTERM, default 45 = the unit's TimeoutStopSec)."""
    raw = os.environ.get("HIROUTE_TERM_WAIT", "")
    try:
        v = float(raw)
    except ValueError:
        return "45"
    return str(v) if 0 < v <= 600 else "45"


def err_code(resp) -> str | None:
    try:
        return json.loads(resp[1]).get("code")
    except (TypeError, ValueError, IndexError, AttributeError):
        return None


def smoke_hiroute(r: dict) -> int:
    d = Path(os.environ.get("HIROUTE_DIR") or (TMP / "hiroute"))
    archive, manifest, installer = d / HIROUTE_ARCHIVE, d / (HIROUTE_ARCHIVE + ".json"), d / "standalone.py"
    r["hiroute_dir"] = str(d)
    missing = [p.name for p in (archive, manifest, installer) if not p.is_file()]
    if missing:
        r["reason"] = (f"HiRoute v{HIROUTE_PIN} not staged in {d} (missing {', '.join(missing)}); download the release "
                       "archive + manifest and hiroute.ai/install/standalone.py there and check their digests, see the "
                       "handoff. Never run install.sh or install into the real HOME")
        return 2
    python = system_python()
    if not python:
        r["reason"] = f"python3 is needed in {SYS_PATH} for the installer and driver"
        return 2
    if not _bwrap_prefix([str(d)]):
        r["reason"] = "bwrap is not usable here; the HiRoute gateway listener must run in a private network namespace"
        return 2
    for p, var, pin in ((archive, "HIROUTE_ARCHIVE_SHA256", HIROUTE_ARCHIVE_SHA),
                        (manifest, "HIROUTE_MANIFEST_SHA256", HIROUTE_MANIFEST_SHA),
                        (installer, "HIROUTE_INSTALLER_SHA256", HIROUTE_INSTALLER_SHA)):
        want_sha = pinned(r, var, pin, lower=True)
        have = sha256_file(p)
        r.setdefault("sha256", {})[p.name] = have
        if have != want_sha:
            r["reason"] = f"{p.name} sha256 is {have}, not {want_sha} (set ${var})"
            return 2
    want = pinned(r, "HIROUTE_VERSION", HIROUTE_PIN)
    return watched("hiroute", lambda rr, checks: _hiroute(rr, python, archive, manifest, installer, want, checks), r)


def _hiroute(r, python, archive, manifest, installer, want, checks) -> int | None:
    with tempfile.TemporaryDirectory(prefix="pfy-hiroute-") as tdn:
        td = Path(tdn)
        home = td / "home"
        for p in (home, td / "tmp", td / "run"):
            p.mkdir()
        extra = {"TMPDIR": str(td / "tmp"), "XDG_RUNTIME_DIR": str(td / "run"),
                 "XDG_CONFIG_HOME": str(home / ".config"), "XDG_DATA_HOME": str(home / ".local/share"),
                 "XDG_STATE_HOME": str(home / ".local/state"), "XDG_CACHE_HOME": str(home / ".cache"),
                 "PYTHONDONTWRITEBYTECODE": "1", "HR_DAEMON_LOG": str(td / "daemon.log"),
                 "HR_TERM_WAIT": term_wait()}
        path = f"{home}/.local/bin:{SYS_PATH}"
        ins = iso([python, str(installer), "install", "--manifest", str(manifest), "--archive", str(archive),
                   "--console-mode", "off"], "hiroute install", home=str(home), cwd=str(td), path=path,
                  extra=extra, bwrap_writable=[tdn])
        r["install"] = {"rc": ins.returncode, "out": (ins.stdout + ins.stderr).strip()[-500:]}
        info = {}
        for line in ins.stdout.splitlines():
            if line.startswith("{"):
                try:
                    info = json.loads(line)
                except ValueError:
                    pass
        checks["installed"] = ins.returncode == 0 and info.get("installed") is True and info.get("version") == want
        mk = home / ".local/share/hiroute/standalone.json"
        marker = {}
        if mk.is_file():
            try:
                marker = json.loads(mk.read_text())
            except ValueError:
                marker = {}
        paths = [marker.get(k) for k in ("cpa_binary", "install_root", "service_definition")]
        paths += list(marker.get("installed_skills") or [])
        r["marker_paths"] = paths
        checks["install_under_temp_home"] = bool(marker) and all(
            isinstance(p, str) and p.startswith(str(home) + "/") for p in paths)
        hr = home / ".local/bin/hiroute"
        if not checks["installed"] or not hr.exists():
            checks["installed"] = False
            failed = [k for k, ok in checks.items() if not ok] or ["installed"]
            r["reason"] = (f"failed checks: {', '.join(failed)}; standalone.py install did not produce a usable "
                           "~/.local/bin/hiroute in the temp HOME")
            r["checks"] = checks
            return 1
        drv = td / "driver.py"
        drv.write_text(HIROUTE_DRIVER)
        p = iso([python, str(drv), str(hr)], "hiroute driver", home=str(home), cwd=str(td), path=path,
                extra=extra, bwrap_writable=[tdn])
        o = as_json(p) or {}
        r["driver"] = {"rc": p.returncode, "stderr": p.stderr.strip()[-300:]}
        r["probe"] = {k: o.get(k) for k in ("ready", "service", "system", "gateway", "models", "chat", "sigterm_exit",
                                            "daemon_exited_early")}
        try:
            r["daemon_log"] = (td / "daemon.log").read_text()[-600:]
        except OSError:
            r["daemon_log"] = ""
        sysd = o.get("system") or {}
        gw = o.get("gateway") or {}
        checks["local_control_ready"] = o.get("ready") is True
        checks["daemon_role_all"] = sysd.get("daemon") == "role_all" and sysd.get("gateway") == "ready"
        checks["gateway_loopback"] = gw.get("ready") is True and str(gw.get("connect_address") or "").startswith(
            "127.0.0.1:")
        checks["unpublished_models_503"] = (o.get("models") or [None])[0] == 503 and err_code(
            o.get("models")) == "GATEWAY_PUBLICATION_UNAVAILABLE"
        checks["ungranted_chat_401"] = (o.get("chat") or [None])[0] == 401 and err_code(
            o.get("chat")) == "GATEWAY_GRANT_UNAUTHORIZED"
        ids = set(o.get("schema_ids") or [])
        checks["schema_routing_decision"] = {"routing.preview", "decision.services.test"} <= ids
        checks["sigterm_exit"] = o.get("sigterm_exit") is True
        r["_ok_reason"] = (f"HiRoute {want}: installer into temp HOME (offline), daemon role_all with local control, "
                           "gateway on 127.0.0.1 fails closed (503 unpublished, 401 ungranted), routing/decision "
                           "commands present, SIGTERM exit; real HOME install paths untouched. Routing to a model not "
                           "exercised")
    return None


ENTRIES = {"skill-up": smoke_skillup, "hiroute": smoke_hiroute}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", required=True, choices=list(ENTRIES))
    a = ap.parse_args()
    receipt = {"entry": a.entry, "script": "examples/x-intake-local/smoke_146_147.py",
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
