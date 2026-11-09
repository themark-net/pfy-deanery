#!/usr/bin/env python3
"""Offline overtime probe. No model, no account, no daemon install.

Measures whether a pinned @ukanwat/overtime can keep an agent folder across a
daemon restart, resume one stub ACP session, and hold a reported budget.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

OUT = Path(__file__).resolve().parent
STUB = OUT / "stub_acp.mjs"
CACHE = (Path.home() / ".cache/pfy/tools/overtime")
PREFIX = CACHE / "prefix"
PKG = PREFIX / "node_modules/@ukanwat/overtime"
BIN = PKG / "dist/bin.js"
NODE = "/usr/bin/node"
RUN = CACHE / "probe-run"
OT_HOME = CACHE / "home/overtime"
REAL_OT = (Path.home() / "overtime")
AGENT = "gapb"
TARBALL = CACHE / "dl/overtime-0.5.3.tgz"
WANT_SHA512 = "7TRVkwud4AcYvW4Wwgem3gegB1z+t6Kl3ggI/4MRwZFmNs2dUACapjnrR7uZrNHqBj1VzLKcOqvGpy4P4C6owg=="


def sha512_b64(path: Path) -> str:
    import base64

    digest = hashlib.sha512(path.read_bytes()).digest()
    return base64.b64encode(digest).decode()


def env() -> dict[str, str]:
    return {
        "HOME": str(CACHE / "home"),
        "XDG_CONFIG_HOME": str(CACHE / "config"),
        "XDG_CACHE_HOME": str(CACHE / "cache"),
        "TMPDIR": str(CACHE / "tmp"),
        "npm_config_cache": str(CACHE / "npm-cache"),
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "OVERTIME_HOME": str(OT_HOME),
        "OVERTIME_STUB_LOG": str(RUN / "stub.jsonl"),
        "OVERTIME_STUB_STATE": str(RUN / "stub-state.json"),
        "OVERTIME_STUB_PROFILE": str(RUN / "profile.json"),
    }


def run(args: list[str], timeout: float = 30) -> dict:
    t0 = time.perf_counter()
    p = subprocess.run(
        [NODE, str(BIN), *args],
        env=env(),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return {
        "args": args,
        "code": p.returncode,
        "stdout": p.stdout[-1500:],
        "stderr": p.stderr[-1500:],
        "seconds": round(time.perf_counter() - t0, 4),
    }


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def stub_events() -> list[dict]:
    path = RUN / "stub.jsonl"
    if not path.is_file():
        return []
    out = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def starts() -> int:
    return sum(1 for e in stub_events() if e.get("event") == "start")


def methods() -> list[str]:
    return [e.get("method") for e in stub_events() if e.get("event") == "in" and e.get("method")]


def state() -> dict:
    return read_json(OT_HOME / "agents" / AGENT / ".overtime/state.json", {})


def settings() -> dict:
    return read_json(OT_HOME / "agents" / AGENT / ".overtime/settings.json", {})


def usage_rows() -> list[dict]:
    path = OT_HOME / "agents" / AGENT / ".overtime/usage.jsonl"
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


def lock_pid() -> int | None:
    lock = OT_HOME / "overtimed.lock"
    if not lock.is_file():
        return None
    digits = "".join(ch if ch.isdigit() else " " for ch in lock.read_text())
    parts = [int(x) for x in digits.split() if x]
    return parts[0] if parts else None


def cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\x00", b" ")
        return raw.decode("utf-8", "replace")
    except OSError:
        return ""


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def stop_daemon() -> dict:
    step = run(["daemon", "stop"], timeout=20)
    deadline = time.time() + 15
    while time.time() < deadline:
        pid = lock_pid()
        if pid is None or not pid_alive(pid):
            break
        time.sleep(0.25)
    pid = lock_pid()
    killed = False
    if pid and pid_alive(pid) and "overtime" in cmdline(pid):
        os.kill(pid, 15)
        killed = True
        time.sleep(0.5)
        if pid_alive(pid):
            os.kill(pid, 9)
    step["lock_pid_after"] = lock_pid()
    step["killed"] = killed
    return step


def wait_until(pred, seconds: float, pause: float = 0.25):
    deadline = time.time() + seconds
    last = None
    while time.time() < deadline:
        last = pred()
        if last:
            return last
        time.sleep(pause)
    return last


def write_profile(tokens: int, session_cost: float) -> None:
    body = {
        "tokens": tokens,
        "session_cost": session_cost,
        "write_ok": str(RUN / "outside/ok.txt"),
        "write_deny": str(RUN / "protected/no.txt"),
    }
    (RUN / "profile.json").write_text(json.dumps(body) + "\n")


def main() -> int:
    t0 = time.perf_counter()
    results: dict = {
        "pin": "0.5.3",
        "git_head": "fc215d4e90cd95fa6b64c39268bb49490cba7ca1",
        "github_v0_5_9": "c4a5725c21c785b6bd014e164678fa70c04026f1",
        "npm_latest_seen": "0.7.1",
        "node": subprocess.check_output([NODE, "--version"], text=True).strip(),
        "agent": AGENT,
    }
    if not BIN.is_file():
        results["error"] = "package missing"
        (OUT / "results.json").write_text(json.dumps(results, indent=2) + "\n")
        return 1
    pkg = json.loads((PKG / "package.json").read_text())
    results["version"] = pkg.get("version")
    results["license"] = pkg.get("license")
    if TARBALL.is_file():
        got = sha512_b64(TARBALL)
        results["tarball_bytes"] = TARBALL.stat().st_size
        results["tarball_sha512_b64"] = got
        results["tarball_integrity_ok"] = got == WANT_SHA512
    results["prefix_bytes"] = sum(p.stat().st_size for p in PREFIX.rglob("*") if p.is_file())
    real_before = REAL_OT.exists()
    # A previous probe leaves the agent folder. Clear only this cache home.
    if OT_HOME.is_relative_to(CACHE):
        stop_daemon()
        shutil.rmtree(OT_HOME, ignore_errors=True)

    if RUN.exists():
        shutil.rmtree(RUN)
    RUN.mkdir(parents=True)
    (RUN / "outside").mkdir()
    (RUN / "protected").mkdir()
    (RUN / "stub.jsonl").write_text("")
    write_profile(4, 0.4)

    steps = []
    results["steps"] = steps
    ver = run(["--version"])
    steps.append({"version": ver})

    created = run(["new", AGENT])
    steps.append({"new": created})
    agent_md = OT_HOME / "agents" / AGENT / "AGENT.md"
    if created["code"] != 0 or not agent_md.is_file():
        results["error"] = "new failed"
        results["seconds"] = round(time.perf_counter() - t0, 4)
        (OUT / "results.json").write_text(json.dumps(results, indent=2) + "\n")
        stop_daemon()
        return 1

    global_settings = OT_HOME / "settings.json"
    doc = read_json(global_settings, {})
    doc["customBackends"] = {"stub": {"command": NODE, "args": [str(STUB)]}}
    global_settings.write_text(json.dumps(doc, indent=2) + "\n")

    configured = run(
        ["set", AGENT, "backend=stub", "budget=1", "tokens=10", f"protect={RUN / 'protected'}"]
    )
    steps.append({"set": configured})
    s0 = settings()
    results["settings_after_set"] = {
        "backend": s0.get("backend"),
        "dailyBudgetUsd": s0.get("dailyBudgetUsd"),
        "dailyTokenBudget": s0.get("dailyTokenBudget"),
        "protect": s0.get("protect"),
    }

    text = agent_md.read_text()
    if "dailyBudgetUsd: 1" not in text:
        results["budget_edit"] = "token missing"
    else:
        agent_md.write_text(text.replace("dailyBudgetUsd: 1", "dailyBudgetUsd: 999", 1))
        adopted = wait_until(lambda: settings().get("dailyBudgetUsd") == 999, 15)
        results["agent_md_edit_adopted"] = bool(adopted)
        results["budget_after_edit"] = settings().get("dailyBudgetUsd")

    reset = run(["set", AGENT, "budget=1"])
    steps.append({"reset_budget": reset})
    results["budget_after_reset"] = settings().get("dailyBudgetUsd")

    # Turn 1. Under the token cap and under $1. Protect is on.
    write_profile(4, 0.4)
    before_starts = starts()
    sent1 = run(["send", AGENT, "ping one"])
    steps.append({"send1": sent1})
    t1 = time.perf_counter()
    turn1 = wait_until(
        lambda: state().get("lastRunAt") and methods().count("session/prompt") >= 1,
        45,
    )
    results["turn1_seconds"] = round(time.perf_counter() - t1, 4)
    results["turn1_ok"] = bool(turn1)
    results["turn1_state"] = {
        "status": state().get("status"),
        "mainSessionId": state().get("mainSessionId"),
        "mainSessionBackend": state().get("mainSessionBackend"),
        "lastError": state().get("lastError"),
        "failures": state().get("failures"),
    }
    results["turn1_methods"] = methods()
    results["turn1_starts"] = starts() - before_starts
    writes = [e.get("writes") for e in stub_events() if e.get("event") == "writes"]
    results["protect_writes"] = writes[-1] if writes else None

    sid = state().get("mainSessionId")
    stopped = stop_daemon()
    steps.append({"stop_after_turn1": {"code": stopped["code"], "killed": stopped["killed"]}})
    results["folder_after_stop"] = agent_md.is_file()
    results["session_id_after_stop"] = read_json(
        OT_HOME / "agents" / AGENT / ".overtime/state.json", {}
    ).get("mainSessionId")

    # Turn 2. Same stub, higher reported cost and tokens. Expect session/load.
    write_profile(20, 2.0)
    starts_before_2 = starts()
    methods_before_2 = len(methods())
    sent2 = run(["send", AGENT, "ping two"])
    steps.append({"send2": sent2})
    t2 = time.perf_counter()
    turn2 = wait_until(lambda: methods().count("session/prompt") >= 2, 45)
    results["turn2_seconds"] = round(time.perf_counter() - t2, 4)
    results["turn2_ok"] = bool(turn2)
    new_methods = methods()[methods_before_2:]
    results["turn2_methods"] = new_methods
    results["turn2_starts"] = starts() - starts_before_2
    load_ids = [
        e.get("brief", {}).get("sessionId")
        for e in stub_events()
        if e.get("event") == "in" and e.get("method") == "session/load"
    ]
    results["load_session_ids"] = load_ids
    results["resumed_same_session"] = bool(sid) and sid in load_ids and "session/new" not in new_methods
    results["turn2_state"] = {
        "status": state().get("status"),
        "mainSessionId": state().get("mainSessionId"),
        "lastError": state().get("lastError"),
    }
    rows = usage_rows()
    results["usage_rows"] = len(rows)
    results["usage_usd"] = round(sum(r.get("turnCostUsd") or 0 for r in rows), 4)
    results["usage_tokens"] = sum((r.get("tokens") or {}).get("total") or 0 for r in rows)

    # Turn 3. Budget should refuse another ACP spawn.
    starts_before_3 = starts()
    sent3 = run(["send", AGENT, "ping three"])
    steps.append({"send3": sent3})
    time.sleep(8)
    results["turn3_starts"] = starts() - starts_before_3
    results["turn3_state"] = {
        "status": state().get("status"),
        "pauseReason": state().get("pauseReason"),
        "lastError": state().get("lastError"),
    }
    results["budget_blocked_third_spawn"] = results["turn3_starts"] == 0 and state().get("pauseReason") == "budget"

    # Watch without a model. Plant the monitor file the daemon already knows how to run.
    stop_daemon()
    counter = RUN / "watch-counter.txt"
    if counter.exists():
        counter.unlink()
    mon = [
        {
            "id": "mon-probe",
            "run": f"echo same >> {counter}; echo same",
            "everyMs": 1000,
            "why": "probe constant watch",
            "cooldownMs": 600000,
            "createdAt": "2026-11-07T00:00:00.000Z",
            "lastFiredAt": None,
            "lastOutput": None,
            "failures": 0,
            "status": "active",
        }
    ]
    meta = OT_HOME / "agents" / AGENT / ".overtime"
    (meta / "monitors.json").write_text(json.dumps(mon) + "\n")
    starts_before_watch = starts()
    tw = time.perf_counter()
    listed = run(["ls"])
    time.sleep(3.5)
    watch_stop = stop_daemon()
    watch_lines = 0
    if counter.is_file():
        watch_lines = len([ln for ln in counter.read_text().splitlines() if ln.strip()])
    results["watch"] = {
        "ls_code": listed["code"],
        "seconds": round(time.perf_counter() - tw, 4),
        "runs": watch_lines,
        "acp_starts": starts() - starts_before_watch,
        "stop_code": watch_stop["code"],
    }

    results["real_overtime_before"] = real_before
    results["real_overtime_after"] = REAL_OT.exists()
    results["gap_b_closed"] = 0
    results["grok_builtin_backend"] = 0
    results["seconds"] = round(time.perf_counter() - t0, 4)
    # Drop bulky step stdout from the committed file once the codes are kept.
    slim = []
    for step in steps:
        slim.append({k: {"args": v.get("args"), "code": v.get("code"), "seconds": v.get("seconds"), "stderr": v.get("stderr", "")[-400:], "killed": v.get("killed")} for k, v in step.items()})
    results["steps"] = slim
    (OUT / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({
        "version": results.get("version"),
        "turn1_ok": results.get("turn1_ok"),
        "resumed_same_session": results.get("resumed_same_session"),
        "budget_blocked_third_spawn": results.get("budget_blocked_third_spawn"),
        "agent_md_edit_adopted": results.get("agent_md_edit_adopted"),
        "watch": results.get("watch"),
        "seconds": results.get("seconds"),
        "turn1_state": results.get("turn1_state"),
        "turn2_methods": results.get("turn2_methods"),
        "protect_writes": results.get("protect_writes"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
