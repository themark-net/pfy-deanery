#!/usr/bin/env python3
"""MVP-3 local trial: the six MVP-2 tasks through ./pfy build --local with review.

No cloud arm. Logs and worktrees stay under this repo's tmp/. Stdout is short.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = "997d89264495861a178713ccf7d4447ea828afc4"
RUNS = ROOT / "tmp" / "mvp3-runs"
GATES = ROOT / "eval" / "mvp2" / "gates"
TASKS_DIR = ROOT / "eval" / "mvp3" / "tasks"
RESULTS = ROOT / "eval" / "mvp3" / "results"
PATCHES = ROOT / "eval" / "mvp3" / "patches"
SCRATCH = ROOT / "tmp" / "mvp3-trial-tmp"
MODEL = "qwen3.6:35b"
FLOOR_GIB = 32.0
WALL_CAP_S = 3 * 60 * 60
WALL_GRACE_S = 10 * 60
# Per task wrapper. Three 1200s attempts fit under this. The 3h cap is separate.
LOCAL_WRAPPER_TIMEOUT = 90 * 60

TASKS = [
    {
        "id": "t1-smolvm-stderr-first",
        "level": "trivial",
        "gate_name": "test_mvp2_t1_smolvm_evidence.py",
        "gate": "python3 -m unittest tests.test_mvp2_t1_smolvm_evidence",
        "writable": [],
    },
    {
        "id": "t2-tree-sig-119",
        "level": "trivial",
        "gate_name": "test_mvp2_t2_tree_sig_119.py",
        "gate": "python3 -m unittest tests.test_mvp2_t2_tree_sig_119",
        "writable": [],
    },
    {
        "id": "t3-daemon-stop-fail",
        "level": "medium",
        "gate_name": "test_mvp2_t3_daemon_stop.py",
        "gate": (
            "python3 -m unittest tests.test_mvp2_t3_daemon_stop "
            "tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_overtime_daemon_stop_timeout_uses_shared_text"
        ),
        "writable": [],
    },
    {
        "id": "t4-timeout-substep",
        "level": "medium",
        "gate_name": "test_mvp2_t4_timeout_step.py",
        "gate": (
            "python3 -m unittest tests.test_mvp2_t4_timeout_step "
            "tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_overtime_timeout_reason_is_shared_text "
            "tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_festival_timeout_reason_is_shared_text "
            "tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_overtime_daemon_stop_timeout_uses_shared_text"
        ),
        "writable": ["tests/test_x_intake_smoke_112_114.py"],
    },
    {
        "id": "t5-receipts-outside-repo",
        "level": "slightly-hard",
        "gate_name": "test_mvp2_t5_receipts.py",
        "gate": "python3 -m unittest tests.test_mvp2_t5_receipts",
        "writable": [
            "tests/test_x_intake_smoke_117_118.py",
            "tests/test_x_intake_smoke_119_121.py",
        ],
    },
    {
        "id": "t6-tree-sig-three",
        "level": "slightly-hard",
        "gate_name": "test_mvp2_t6_tree_sig_three.py",
        "gate": "python3 -m unittest tests.test_mvp2_t6_tree_sig_three",
        "writable": [],
    },
]


def _log(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(text)
        if not text.endswith("\n"):
            handle.write("\n")


def _say(line: str) -> None:
    print(line, flush=True)


def _git(cwd: Path, args: list[str], timeout: float = 60) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "pfy-local-build"
    env["GIT_AUTHOR_EMAIL"] = "pfy-local-build@localhost"
    env["GIT_COMMITTER_NAME"] = "pfy-local-build"
    env["GIT_COMMITTER_EMAIL"] = "pfy-local-build@localhost"
    return subprocess.run(
        ["git", *args], cwd=str(cwd), env=env, text=True, capture_output=True, timeout=timeout, check=False,
    )


def _meminfo() -> dict[str, int]:
    out = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        num = val.strip().split()[0]
        if num.isdigit():
            out[key] = int(num)
    return out


def _free_gib() -> float:
    info = _meminfo()
    kb = info.get("MemAvailable", 0) + info.get("SwapFree", 0)
    return kb / (1024.0 * 1024.0)


def _loaded_models() -> list[str]:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/ps", timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (OSError, json.JSONDecodeError, TimeoutError):
        return ["unreadable"]
    names = []
    for row in data.get("models") or []:
        name = row.get("name") or row.get("model") or ""
        if name:
            names.append(str(name))
    return names


def _api_answers() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=10) as resp:
            resp.read()
        return True
    except (OSError, TimeoutError):
        return False


def _unload_trial_model() -> bool:
    """Drop qwen3.6:35b only. No-op when another model is resident."""
    loaded = _loaded_models()
    if not loaded or loaded == ["unreadable"]:
        return False
    prefix = MODEL.split(":")[0]
    if any(not name.startswith(prefix) for name in loaded):
        return False
    body = json.dumps({
        "model": MODEL,
        "prompt": "",
        "stream": False,
        "keep_alive": 0,
        "options": {"num_ctx": 512, "num_predict": 1},
    }).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            resp.read()
    except (OSError, TimeoutError):
        return False
    return True


def _load_local():
    spec = importlib.util.spec_from_file_location("pfy_build_local", ROOT / "scripts" / "pfy_build_local.py")
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _task(task_id: str) -> dict:
    for task in TASKS:
        if task["id"] == task_id:
            return task
    raise SystemExit("unknown task " + task_id)


def _remove_worktree(path: Path) -> None:
    if path.exists():
        _git(ROOT, ["worktree", "remove", "--force", str(path)], timeout=120)
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
        _git(ROOT, ["worktree", "prune"], timeout=60)


def _plant(task: dict, dest: Path) -> str:
    _remove_worktree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    added = _git(ROOT, ["worktree", "add", "--detach", str(dest), BASE], timeout=120)
    if added.returncode != 0:
        raise SystemExit("worktree add failed: " + (added.stderr or added.stdout))
    gate_src = GATES / task["gate_name"]
    gate_dst = dest / "tests" / task["gate_name"]
    shutil.copyfile(gate_src, gate_dst)
    _git(dest, ["add", "--", str(Path("tests") / task["gate_name"])])
    committed = _git(dest, ["commit", "-m", "test: red gate for " + task["id"]])
    if committed.returncode != 0:
        raise SystemExit("plant commit failed: " + (committed.stderr or committed.stdout))
    sha = _git(dest, ["rev-parse", "HEAD"])
    return (sha.stdout or "").strip()


def _gate_env(worktree: Path) -> dict[str, str]:
    home = worktree / "tmp" / "gate-home"
    tmp = worktree / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    home.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["TMPDIR"] = str(tmp)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PFY_SMOKE_RECEIPT_DIR", None)
    return env


def _run_gate(module, worktree: Path, gate: str) -> dict:
    state = module.State()
    return module.run_tests(
        gate,
        worktree,
        _gate_env(worktree),
        600,
        state,
        repo=worktree,
        unsafe=False,
    )


def _diff_stat(worktree: Path, base: str) -> dict:
    proc = _git(worktree, ["diff", "--numstat", base])
    files = 0
    ins = 0
    dels = 0
    for line in (proc.stdout or "").splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        files += 1
        if parts[0].isdigit():
            ins += int(parts[0])
        if parts[1].isdigit():
            dels += int(parts[1])
    return {"files": files, "insertions": ins, "deletions": dels}


def _write_patch(worktree: Path, base: str, dest: Path) -> None:
    proc = _git(worktree, ["diff", base], timeout=60)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(proc.stdout or "", encoding="utf-8")


def _canonical_gate(module, task: dict, worktree: Path) -> dict:
    gate_path = worktree / "tests" / task["gate_name"]
    saved = gate_path.read_bytes() if gate_path.is_file() else None
    canonical = (GATES / task["gate_name"]).read_bytes()
    same = saved == canonical
    if not same:
        gate_path.write_bytes(canonical)
    try:
        record = _run_gate(module, worktree, task["gate"])
    finally:
        if saved is None:
            if gate_path.exists() and not same:
                gate_path.unlink()
        elif not same:
            gate_path.write_bytes(saved)
    return {
        "acceptance_test_unchanged": same,
        "exit": record.get("exit"),
        "passed": record.get("passed"),
        "failed": record.get("failed"),
        "errors": record.get("errors"),
    }


def _blank(task: dict, planted: str) -> dict:
    return {
        "task": task["id"],
        "level": task["level"],
        "arm": "L",
        "base_sha": BASE,
        "planted_sha": planted,
        "gate": task["gate"],
        "status": None,
        "reason": None,
        "attempts": 0,
        "loop_verdict": None,
        "quality_accept": None,
        "quality_why": "pending human-standard review",
        "gaming": None,
        "scope_creep": None,
    }


def _save_result(payload: dict) -> None:
    path = RESULTS / (payload["task"] + "-L.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _clock_path() -> Path:
    return RUNS / "first-model-call.txt"


def _first_call() -> float | None:
    path = _clock_path()
    if not path.is_file():
        return None
    try:
        return float(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def _mark_first_call() -> float:
    existing = _first_call()
    if existing is not None:
        return existing
    path = _clock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    path.write_text(str(now), encoding="utf-8")
    return now


def _over_cap() -> bool:
    started = _first_call()
    return started is not None and (time.time() - started) >= WALL_CAP_S


def _kill_groups(dest: Path, wrapper: subprocess.Popen) -> None:
    """Kill process groups this trial started. Leave every other pid alone."""
    pids = dest / "tmp" / "local-build.pids.json"
    groups = set()
    if pids.is_file():
        try:
            data = json.loads(pids.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        if isinstance(data, dict):
            for key in ("agent_pgid", "pgid"):
                try:
                    group = int(data.get(key) or 0)
                except (TypeError, ValueError):
                    group = 0
                if group > 1:
                    groups.add(group)
    try:
        groups.add(os.getpgid(wrapper.pid))
    except (OSError, ProcessLookupError):
        pass
    for group in groups:
        if group == os.getpgrp():
            continue
        try:
            os.killpg(group, signal.SIGTERM)
        except (OSError, ProcessLookupError):
            pass
    time.sleep(1)
    for group in groups:
        if group == os.getpgrp():
            continue
        try:
            os.killpg(group, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass


def _host_block() -> str | None:
    """None when the host can take another arm. Otherwise a STOPPED reason."""
    unread = 0
    for _ in range(2):
        loaded = _loaded_models()
        if loaded == ["unreadable"]:
            unread += 1
            time.sleep(2)
            continue
        foreign = [name for name in loaded if not name.startswith(MODEL.split(":")[0])]
        if foreign:
            return "STOPPED busy-host"
        break
    if unread >= 2:
        return "STOPPED ollama-ps-unreadable"
    if not _api_answers():
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            if _api_answers():
                break
            time.sleep(5)
        else:
            return "STOPPED ollama-api-silent"
    free = _free_gib()
    if free < FLOOR_GIB and _unload_trial_model():
        time.sleep(2)
        free = _free_gib()
    if free < FLOOR_GIB:
        return "STOPPED mem"
    cores = os.cpu_count() or 1
    limit = 2 * cores
    if os.getloadavg()[0] > limit:
        deadline = time.monotonic() + 5 * 60
        while time.monotonic() < deadline:
            if os.getloadavg()[0] <= limit:
                return None
            time.sleep(30)
        return "STOPPED load"
    return None


def _attempt_rows(receipt_dir: Path) -> list[dict]:
    rows = []
    if not receipt_dir.is_dir():
        return rows
    for path in sorted(receipt_dir.glob("attempt-*/receipt.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rows.append({
            "attempt": data.get("attempt"),
            "status": data.get("status"),
            "reason": data.get("reason"),
            "wall_seconds": data.get("wall_seconds"),
            "diff_stats": data.get("diff_stats"),
            "checks": data.get("checks"),
            "model_review": data.get("model_review"),
            "mem_min_available_gb": data.get("mem_min_available_gb"),
        })
    return rows


def _loop_verdict(status: str | None) -> str | None:
    if status == "PASS":
        return "accept"
    if status == "PASS-REJECTED":
        return "reject"
    if status in ("FAIL", "TIMEOUT", "BLOCKED"):
        return "reject" if status == "FAIL" else None
    return None


def prove_red(only: str | None) -> int:
    module = _load_local()
    bad = []
    for task in TASKS:
        if only and task["id"] != only:
            continue
        dest = RUNS / (task["id"] + "-prove")
        log = RUNS / "logs" / (task["id"] + "-prove.log")
        try:
            planted = _plant(task, dest)
            record = _run_gate(module, dest, task["gate"])
        except Exception as exc:
            _say("PROVE_FAIL " + task["id"] + " harness " + type(exc).__name__)
            _log(log, str(exc))
            bad.append(task["id"])
            continue
        failed = int((record.get("counts") or {}).get("failed") or 0)
        errors = int((record.get("counts") or {}).get("errors") or 0)
        exit_code = record.get("exit")
        tail = record.get("tail") or ""
        if not isinstance(tail, str):
            tail = "\n".join(str(part) for part in tail)
        _log(log, "planted " + planted + "\nexit " + str(exit_code) + "\n" + tail)
        if exit_code not in (0, None) and (failed + errors) > 0 and record.get("counts"):
            _say("PROVE_RED " + task["id"] + " failed=" + str(failed) + " errors=" + str(errors))
        else:
            _say("PROVE_FAIL " + task["id"] + " exit=" + str(exit_code) + " failed=" + str(failed))
            bad.append(task["id"])
        _remove_worktree(dest)
    if bad:
        _say("PROVE_DONE bad=" + ",".join(bad))
        return 1
    _say("PROVE_DONE ok")
    return 0


def _arm_dir(task_id: str) -> Path:
    return RUNS / (task_id + "-L")


def run_local(task: dict) -> dict:
    module = _load_local()
    dest = _arm_dir(task["id"])
    log = RUNS / "logs" / (task["id"] + "-L.log")
    if _over_cap():
        payload = _blank(task, "")
        payload["status"] = "not-run (wall cap)"
        payload["reason"] = "wall-cap"
        _save_result(payload)
        _say("ARM_DONE " + task["id"] + " L not-run (wall cap)")
        return payload
    block = _host_block()
    if block:
        payload = _blank(task, "")
        payload["status"] = block
        payload["reason"] = block
        _save_result(payload)
        _say("ARM_DONE " + task["id"] + " L " + block)
        return payload
    planted = _plant(task, dest)
    pre = _run_gate(module, dest, task["gate"])
    pre_failed = int((pre.get("counts") or {}).get("failed") or 0) + int((pre.get("counts") or {}).get("errors") or 0)
    if pre.get("exit") == 0 or pre_failed == 0:
        payload = _blank(task, planted)
        payload["status"] = "BLOCKED"
        payload["reason"] = "gate-not-red"
        _save_result(payload)
        _say("ARM_DONE " + task["id"] + " L BLOCKED gate-not-red")
        return payload
    free = _free_gib()
    receipt_dir = RUNS / "receipts" / (task["id"] + "-L")
    if receipt_dir.exists():
        shutil.rmtree(receipt_dir)
    cmd = [
        str(ROOT / "pfy"), "build", "--local",
        "--prompt-file", str(TASKS_DIR / (task["id"] + ".md")),
        "--repo", str(dest),
        "--base", planted,
        "--test-cmd", task["gate"],
        "--receipt-dir", str(receipt_dir),
        "--keep-worktree",
        "--model", MODEL,
        "--retries", "2",
    ]
    for glob in task["writable"]:
        cmd.extend(["--writable-test", glob])
    _mark_first_call()
    _say("ARM_START " + task["id"] + " L")
    started = time.monotonic()
    timed_out = False
    killed_cap = False
    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        env={**os.environ, "TMPDIR": str(SCRATCH), "PYTHONDONTWRITEBYTECODE": "1"},
    )
    try:
        while True:
            try:
                out_text, err_text = proc.communicate(timeout=15)
                code = proc.returncode
                break
            except subprocess.TimeoutExpired:
                if time.monotonic() - started >= LOCAL_WRAPPER_TIMEOUT:
                    timed_out = True
                    _kill_groups(dest, proc)
                    out_text, err_text = proc.communicate(timeout=10)
                    code = 124
                    break
                if _over_cap():
                    grace = time.monotonic()
                    finished = False
                    while time.monotonic() - grace < WALL_GRACE_S:
                        try:
                            out_text, err_text = proc.communicate(timeout=15)
                            code = proc.returncode
                            finished = True
                            break
                        except subprocess.TimeoutExpired:
                            continue
                    if not finished:
                        killed_cap = True
                        _kill_groups(dest, proc)
                        try:
                            out_text, err_text = proc.communicate(timeout=10)
                        except subprocess.TimeoutExpired:
                            out_text, err_text = "", ""
                        code = 124
                    break
    except Exception:
        _kill_groups(dest, proc)
        raise
    wall = round(time.monotonic() - started, 3)
    _log(log, out_text or "")
    _log(log, err_text or "")
    receipt_path = receipt_dir / "receipt.json"
    receipt = {}
    if receipt_path.is_file():
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            receipt = {}
    inner = receipt.get("worktree")
    diff_root = Path(inner) if inner else dest
    stat = _diff_stat(diff_root, BASE) if diff_root.exists() else {"files": 0, "insertions": 0, "deletions": 0}
    patch = PATCHES / (task["id"] + "-L.patch")
    if diff_root.exists():
        _write_patch(diff_root, BASE, patch)
    canonical = {"acceptance_test_unchanged": None, "exit": None}
    if diff_root.exists() and (diff_root / "tests" / task["gate_name"]).exists():
        canonical = _canonical_gate(module, task, diff_root)
    elif (dest / "tests" / task["gate_name"]).exists():
        canonical = _canonical_gate(module, task, dest)
    status = receipt.get("status")
    if killed_cap:
        status = "TIMEOUT"
    elif timed_out and not status:
        status = "TIMEOUT"
    elif not status:
        status = "PASS" if code == 0 else "FAIL"
    attempts = _attempt_rows(receipt_dir)
    payload = _blank(task, planted)
    payload.update({
        "status": status,
        "reason": "wall-cap" if killed_cap else ("wrapper-timeout" if timed_out else receipt.get("reason")),
        "exit_code": code,
        "wall_seconds": wall,
        "agent_seconds": receipt.get("agent_seconds"),
        "receipt_wall_seconds": receipt.get("wall_seconds"),
        "diff": stat,
        "attempts": receipt.get("attempts") or len(attempts) or 1,
        "attempt_rows": attempts,
        "free_gib_before": round(free, 3),
        "receipt_status": receipt.get("status"),
        "receipt_reason": receipt.get("reason"),
        "branch": receipt.get("branch"),
        "commit": receipt.get("commit"),
        "sandbox": receipt.get("sandbox"),
        "files_changed": receipt.get("files_changed"),
        "review": receipt.get("review"),
        "canonical_gate": canonical,
        "patch": str(patch.relative_to(ROOT)) if patch.exists() else None,
        "mem": receipt.get("mem"),
        "loop_verdict": _loop_verdict(status),
    })
    _save_result(payload)
    _say("ARM_DONE " + task["id"] + " L " + str(payload["status"]) + " " + str(payload["reason"]))
    if not receipt.get("unloaded"):
        _unload_trial_model()
    return payload


def _not_run_rest(start_id: str, reason: str) -> None:
    seen = False
    for task in TASKS:
        if task["id"] == start_id:
            seen = True
            continue
        if not seen:
            continue
        path = RESULTS / (task["id"] + "-L.json")
        if path.is_file():
            continue
        payload = _blank(task, "")
        payload["status"] = reason
        payload["reason"] = reason
        _save_result(payload)
        _say("ARM_DONE " + task["id"] + " L " + reason)


def main(argv: list[str]) -> int:
    os.environ["TMPDIR"] = str(SCRATCH)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)
    if len(argv) < 2:
        raise SystemExit("usage: run_trial.py prove-red [task] | arm L task | all-local")
    action = argv[1]
    if action == "prove-red":
        return prove_red(argv[2] if len(argv) > 2 else None)
    if action == "arm":
        if argv[2] != "L":
            raise SystemExit("MVP-3 has no cloud arm")
        run_local(_task(argv[3]))
        return 0
    if action == "all-local":
        _say("FREE_GIB " + str(round(_free_gib(), 3)))
        auth = Path.home() / ".grok" / "auth.json"
        _say("AUTH " + ("present" if auth.is_file() and auth.stat().st_size > 0 else "missing"))
        last_block = None
        block_run = 0
        for task in TASKS:
            payload = run_local(task)
            status = str(payload.get("status") or "")
            if status.startswith("STOPPED"):
                _not_run_rest(task["id"], "not-run (" + status + ")")
                _unload_trial_model()
                _say("ALL_LOCAL_DONE " + status)
                return 0
            if status.startswith("not-run"):
                _not_run_rest(task["id"], status)
                _unload_trial_model()
                _say("ALL_LOCAL_DONE " + status)
                return 0
            if status == "BLOCKED":
                reason = str(payload.get("reason") or "")
                if reason == last_block:
                    block_run += 1
                else:
                    last_block = reason
                    block_run = 1
                if block_run >= 2:
                    _not_run_rest(task["id"], "not-run (blocked " + reason + ")")
                    _unload_trial_model()
                    _say("ALL_LOCAL_DONE BLOCKED " + reason)
                    return 0
            else:
                last_block = None
                block_run = 0
        _unload_trial_model()
        _say("ALL_LOCAL_DONE")
        return 0
    raise SystemExit("unknown action")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
