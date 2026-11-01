#!/usr/bin/env python3
"""Rerun one MVP-3 task through ./pfy build --local.

The wrapper is the contract. This process does not take the lock. A second
flock attempt before the model load would race, so the only accepted proof is
an inherited fd that already holds an exclusive flock on the contract file
(what `flock(1)` leaves open until this process exits):

    flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock \\
      nice -n 19 python3 eval/mvp-1031/rerun_local.py t5-receipts-outside-repo

Review stays on. Retries stay at 2. The model is qwen3.6:35b.
t4-timeout-substep runs only after a t5 receipt is on disk.
A commit that contains a gitignored path is a failed rerun.

Exit codes:
  0  runner passed and the commit has no gitignored path
  1  runner failed, or a gitignored path landed in the commit
  2  usage, unknown task, missing flock, or t4 before t5
  4  host cannot take the model (mem, host busy, ollama down)
  143  SIGTERM (the child process group this script started is signaled first)
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL = "qwen3.6:35b"
BASE = "997d89264495861a178713ccf7d4447ea828afc4"
LOCK_DEFAULT = Path("/home/mark/DEVELOP/pfy-mentat/tmp/heavy-1030.lock")
MEM_FLOOR_KIB = 32 * 1024 * 1024
WRAPPER = (
    "flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock \\\n"
    "  nice -n 19 python3 eval/mvp-1031/rerun_local.py t5-receipts-outside-repo"
)

TASKS = {
    "t5-receipts-outside-repo": {
        "gate": "python3 -m unittest tests.test_mvp2_t5_receipts",
        "gate_name": "test_mvp2_t5_receipts.py",
        "writable": [
            "tests/test_x_intake_smoke_117_118.py",
            "tests/test_x_intake_smoke_119_121.py",
        ],
        "prompt": ROOT / "eval" / "mvp3" / "tasks" / "t5-receipts-outside-repo.md",
        "needs": None,
    },
    "t4-timeout-substep": {
        "gate": (
            "python3 -m unittest tests.test_mvp2_t4_timeout_step "
            "tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_overtime_timeout_reason_is_shared_text "
            "tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_festival_timeout_reason_is_shared_text "
            "tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_overtime_daemon_stop_timeout_uses_shared_text"
        ),
        "gate_name": "test_mvp2_t4_timeout_step.py",
        "writable": ["tests/test_x_intake_smoke_112_114.py"],
        "prompt": ROOT / "eval" / "mvp3" / "tasks" / "t4-timeout-substep.md",
        "needs": "t5-receipts-outside-repo",
    },
}

_CHILD = {"pgid": None}


def contract_lock() -> Path:
    raw = os.environ.get("PFY_RERUN_LOCK")
    if raw:
        return Path(raw)
    return LOCK_DEFAULT


def holds_contract_flock(lock_path: Path | None = None) -> bool:
    """True when this process already holds an exclusive flock on the lock file.

    Looks at inherited fds. Does not open the lock or call flock(2).
    """
    path = lock_path or contract_lock()
    try:
        wanted = path.resolve()
    except OSError:
        return False
    fd_dir = Path("/proc/self/fd")
    if not fd_dir.is_dir():
        return False
    for entry in fd_dir.iterdir():
        try:
            target = Path(os.readlink(entry))
        except OSError:
            continue
        if not target.is_absolute():
            continue
        try:
            if target.resolve() != wanted:
                continue
        except OSError:
            continue
        info_path = Path("/proc/self/fdinfo") / entry.name
        try:
            info = info_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in info.splitlines():
            if line.startswith("lock:") and "FLOCK" in line and "WRITE" in line:
                return True
    return False


def mem_free_kib() -> int:
    avail = 0
    swap = 0
    try:
        text = Path("/proc/meminfo").read_text(encoding="utf-8")
    except OSError:
        return 0
    for line in text.splitlines():
        if line.startswith("MemAvailable:"):
            avail = int(line.split()[1])
        elif line.startswith("SwapFree:"):
            swap = int(line.split()[1])
    return avail + swap


def loaded_models() -> list[str] | None:
    """Model names from the local ollama ps API. None when the API does not answer."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/ps", timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    names = []
    for row in data.get("models") or []:
        if not isinstance(row, dict):
            continue
        name = row.get("name") or row.get("model") or ""
        if name:
            names.append(str(name))
    return names


def host_block() -> str | None:
    """None when this lane may load qwen3.6:35b. Otherwise a stop reason."""
    if mem_free_kib() < MEM_FLOOR_KIB:
        return "mem"
    loaded = loaded_models()
    if loaded is None:
        return "ollama-down"
    if loaded:
        return "host busy"
    return None


def out_dir() -> Path:
    raw = os.environ.get("PFY_RERUN_OUT")
    if raw:
        return Path(raw)
    return ROOT / "eval" / "mvp-1031" / "local-rerun"


def t5_recorded(folder: Path) -> bool:
    return (folder / "t5-receipts-outside-repo" / "receipt.json").is_file()


def _git(cwd: Path, args: list[str], timeout: float = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _safe_rmtree(path: Path) -> None:
    root_tmp = (ROOT / "tmp").resolve()
    target = path.resolve() if path.exists() else path.absolute()
    if target != root_tmp and root_tmp not in target.parents:
        raise SystemExit("refusing to delete outside tmp: %s" % target)
    if path.exists():
        shutil.rmtree(path)


def plant(task_id: str) -> tuple[Path, str]:
    """Clone this lane into tmp and commit the canonical red gate on BASE."""
    task = TASKS[task_id]
    dest = ROOT / "tmp" / "local-rerun-clones" / task_id
    _safe_rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    cloned = subprocess.run(
        ["git", "clone", "--no-hardlinks", "--quiet", str(ROOT), str(dest)],
        text=True,
        capture_output=True,
        timeout=600,
        check=False,
    )
    if cloned.returncode != 0 or not (dest / ".git").exists():
        detail = (cloned.stderr or cloned.stdout or "clone failed").strip().splitlines()
        raise SystemExit("clone failed: " + (detail[0] if detail else "clone failed"))
    checked = _git(dest, ["checkout", "--detach", BASE], timeout=180)
    if checked.returncode != 0:
        raise SystemExit("checkout base failed: " + (checked.stderr or checked.stdout or "").strip())
    gate_src = ROOT / "eval" / "mvp2" / "gates" / task["gate_name"]
    if not gate_src.is_file():
        raise SystemExit("missing gate file: %s" % gate_src)
    gate_dst = dest / "tests" / task["gate_name"]
    gate_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(gate_src, gate_dst)
    added = _git(dest, ["add", "--", "tests/%s" % task["gate_name"]])
    if added.returncode != 0:
        raise SystemExit("plant add failed: " + (added.stderr or added.stdout or "").strip())
    quiet = _git(dest, ["diff", "--cached", "--quiet"])
    if quiet.returncode == 0:
        sha = _git(dest, ["rev-parse", "HEAD"])
        return dest, (sha.stdout or "").strip()
    committed = _git(
        dest,
        [
            "-c",
            "user.name=pfy-local-rerun",
            "-c",
            "user.email=pfy-local-rerun@localhost",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-m",
            "test: plant red gate for " + task_id,
        ],
    )
    if committed.returncode != 0:
        raise SystemExit("plant commit failed: " + (committed.stderr or committed.stdout or "").strip())
    sha = _git(dest, ["rev-parse", "HEAD"])
    if sha.returncode != 0 or not (sha.stdout or "").strip():
        raise SystemExit("plant sha missing")
    return dest, (sha.stdout or "").strip()


def resolve_repo(task_id: str) -> tuple[Path, str]:
    raw = os.environ.get("PFY_RERUN_REPO")
    if raw:
        repo = Path(raw).resolve()
        base = (os.environ.get("PFY_RERUN_BASE") or "").strip()
        if not base:
            sha = _git(repo, ["rev-parse", "HEAD"])
            if sha.returncode != 0 or not (sha.stdout or "").strip():
                raise SystemExit("repo has no HEAD: %s" % repo)
            base = (sha.stdout or "").strip()
        return repo, base
    return plant(task_id)


def pfy_bin() -> Path:
    raw = os.environ.get("PFY_RERUN_PFY")
    if raw:
        return Path(raw)
    return ROOT / "pfy"


def build_argv(task_id: str, repo: Path, base: str, receipt_dir: Path) -> list[str]:
    task = TASKS[task_id]
    prompt = task["prompt"]
    if not Path(prompt).is_file():
        raise SystemExit("missing prompt: %s" % prompt)
    argv = [
        str(pfy_bin()),
        "build",
        "--local",
        "--review",
        "--retries",
        "2",
        "--model",
        MODEL,
        "--prompt-file",
        str(prompt),
        "--repo",
        str(repo),
        "--base",
        base,
        "--test-cmd",
        task["gate"],
        "--receipt-dir",
        str(receipt_dir),
        "--keep-worktree",
    ]
    for rel in task["writable"]:
        argv.extend(["--writable-test", rel])
    if "--no-review" in argv or MODEL not in argv:
        raise SystemExit("refusing a command that drops review or the pinned model")
    return argv


def _on_signal(signum, _frame):
    pgid = _CHILD.get("pgid")
    if pgid and pgid != os.getpgrp():
        try:
            os.killpg(pgid, signal.SIGTERM)
        except OSError:
            pass
        time.sleep(0.5)
        try:
            os.killpg(pgid, signal.SIGKILL)
        except OSError:
            pass
    raise SystemExit(128 + int(signum))


def spawn_runner(argv: list[str]) -> int:
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("PFY_RERUN_"):
            env.pop(key, None)
    scratch = ROOT / "tmp"
    scratch.mkdir(parents=True, exist_ok=True)
    env["TMPDIR"] = str(scratch)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.Popen(
        argv,
        cwd=str(ROOT),
        env=env,
        start_new_session=True,
    )
    _CHILD["pgid"] = proc.pid
    pid_path = scratch / "rerun-local.pid"
    pid_path.write_text(str(proc.pid) + "\n", encoding="utf-8")
    try:
        code = proc.wait()
        return int(code if code is not None else 1)
    finally:
        _CHILD["pgid"] = None
        pid_path.unlink(missing_ok=True)


def gitignored_in_commit(repo: Path, sha: str) -> list[str]:
    """Paths this commit adds or changes that match a gitignore rule.

    Files already tracked on the parent are not a new landing. A root commit
    has no parent, so every path in that tree counts.
    """
    if not sha or not str(sha).strip():
        return []
    if not repo or not Path(repo).exists():
        return ["<commit unreadable>"]
    parent = _git(Path(repo), ["rev-parse", "--verify", "--quiet", sha + "^"])
    parent_sha = (parent.stdout or "").strip()
    if parent.returncode == 0 and parent_sha:
        listed = _git(Path(repo), ["diff", "--name-only", "-z", parent_sha, sha])
    else:
        listed = _git(Path(repo), ["ls-tree", "-r", "--name-only", "-z", sha])
    if listed.returncode != 0:
        return ["<commit unreadable>"]
    paths = [part for part in (listed.stdout or "").split("\0") if part]
    if not paths:
        return []
    proc = subprocess.run(
        ["git", "-C", str(repo), "check-ignore", "--no-index", "-z", "--stdin"],
        input="\0".join(paths) + "\0",
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if proc.returncode == 1:
        return []
    if proc.returncode != 0:
        return ["<check-ignore failed>"]
    return [part for part in (proc.stdout or "").split("\0") if part]


def _display(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _load_receipt(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"_unreadable": True}
    return data if isinstance(data, dict) else {"_unreadable": True}


def _section(task_id: str, info: dict) -> str:
    lines = [
        "## %s" % task_id,
        "",
        "Receipt: %s" % info["receipt"],
        "Exit code: %s" % info["exit_code"],
        "Runner exit code: %s" % info["runner_exit"],
        "Gate: %s" % info["gate"],
        "Gitignored path in the commit: %s" % info["ignored_label"],
    ]
    if info.get("ignored_paths"):
        lines.append("Paths: %s" % ", ".join(info["ignored_paths"]))
    lines.append("Commit: %s" % (info.get("commit") or "none"))
    if info.get("rerun"):
        lines.append("Rerun: %s" % info["rerun"])
    return "\n".join(lines)


def upsert_note(path: Path, task_id: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text(encoding="utf-8") if path.is_file() else "# Local rerun\n"
    if not existing.endswith("\n"):
        existing += "\n"
    heading = "## " + task_id
    lines = existing.splitlines()
    start = None
    end = None
    for index, line in enumerate(lines):
        if line == heading and start is None:
            start = index
            continue
        if start is not None and line.startswith("## "):
            end = index
            break
    block = body.rstrip("\n").splitlines()
    if start is None:
        if lines and lines[-1] != "":
            lines.append("")
        lines.extend(block)
    else:
        if end is None:
            end = len(lines)
        lines = lines[:start] + block + [""] + lines[end:]
    text = "\n".join(lines).rstrip() + "\n"
    path.write_text(text, encoding="utf-8")


def _record(task_id: str, folder: Path, runner_exit: int, repo: Path) -> int:
    dest_dir = folder / task_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    scratch = ROOT / "tmp" / "local-rerun-receipts" / task_id / "receipt.json"
    dest = dest_dir / "receipt.json"
    if scratch.is_file():
        shutil.copyfile(scratch, dest)
    elif not dest.is_file():
        dest.write_text(
            json.dumps(
                {
                    "status": "MISSING",
                    "reason": "no-receipt",
                    "commit": None,
                    "runner_exit": runner_exit,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    receipt = _load_receipt(dest)
    if receipt.get("_unreadable"):
        gate = "unreadable"
        commit = None
        ignored = ["<receipt unreadable>"]
        inspect = repo
    else:
        status = receipt.get("status") or "missing"
        reason = receipt.get("reason") or "none"
        gate = "%s %s" % (status, reason)
        commit = receipt.get("commit") or None
        if commit is not None:
            commit = str(commit)
        raw_tree = receipt.get("worktree")
        inspect = Path(raw_tree) if raw_tree and Path(str(raw_tree)).exists() else repo
        ignored = gitignored_in_commit(inspect, commit or "")
    real_ignored = [path for path in ignored if not path.startswith("<")]
    broken = [path for path in ignored if path.startswith("<")]
    if real_ignored or broken:
        label = "yes"
    else:
        label = "no"
    final = runner_exit
    rerun = "ok" if runner_exit == 0 else "failed"
    if label == "yes":
        rerun = "failed"
        if final == 0:
            final = 1
    info = {
        "receipt": _display(dest),
        "exit_code": final,
        "runner_exit": runner_exit,
        "gate": gate,
        "ignored_label": label,
        "ignored_paths": real_ignored or broken,
        "commit": commit,
        "rerun": rerun,
    }
    upsert_note(folder / "NOTE.md", task_id, _section(task_id, info))
    print(
        "rerun %s exit %s gate %s gitignored %s" % (task_id, final, gate, label),
        flush=True,
    )
    return final


def main(argv: list[str] | None = None) -> int:
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) != 1 or not argv[0].strip():
        print("usage: python3 eval/mvp-1031/rerun_local.py <task>", file=sys.stderr)
        print("tasks: %s" % ", ".join(TASKS), file=sys.stderr)
        return 2
    task_id = argv[0].strip()
    if task_id not in TASKS:
        print("unknown task: %s" % task_id, file=sys.stderr)
        return 2
    if not holds_contract_flock():
        print("refusing to run without the flock", file=sys.stderr)
        print(WRAPPER, file=sys.stderr)
        return 2
    folder = out_dir()
    needs = TASKS[task_id]["needs"]
    if needs and not t5_recorded(folder):
        print("t5 receipt is not recorded; refusing %s" % task_id, file=sys.stderr)
        return 2
    if os.environ.get("PFY_RERUN_SKIP_HOST") != "1":
        block = host_block()
        if block:
            print(block, file=sys.stderr)
            return 4
    scratch = ROOT / "tmp" / "local-rerun-receipts" / task_id
    _safe_rmtree(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    repo, base = resolve_repo(task_id)
    argv_run = build_argv(task_id, repo, base, scratch)
    print("rerun start %s" % task_id, flush=True)
    try:
        code = spawn_runner(argv_run)
    except OSError:
        print("runner failed to start", file=sys.stderr)
        return _record(task_id, folder, 1, repo)
    return _record(task_id, folder, code, repo)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(1)
