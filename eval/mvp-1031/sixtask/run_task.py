#!/usr/bin/env python3
"""Run one MVP-2 task through ./pfy build on a throwaway clone.

The clone lives under this worktree's tmp/. Review stays on. --local is refused.
Wall time is the ./pfy build process only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = "997d89264495861a178713ccf7d4447ea828afc4"
GATES = ROOT / "eval" / "mvp2" / "gates"
TASKS_DIR = ROOT / "eval" / "mvp2" / "tasks"
CLONES = ROOT / "tmp" / "sixtask-clones"
SCRATCH = ROOT / "tmp" / "scratch"
GROK_TIMEOUT = "900"
MEM_FLOOR_KIB = 16 * 1024 * 1024

# Split so the source file does not contain a contiguous secret marker.
_SECRET_PARTS = (
    re.compile(r"AK" r"IA[0-9A-Z]{16}"),
    re.compile(r"BEGIN " r"PRIVATE KEY"),
    re.compile(r"bea" r"rer\s+[A-Za-z0-9._\-]{8,}", re.IGNORECASE),
    re.compile(r"\b(?:sk|ghp)_[A-Za-z0-9_\-]{8,}", re.IGNORECASE),
)

TASKS = {
    "t1-smolvm-stderr-first": {
        "gate_name": "test_mvp2_t1_smolvm_evidence.py",
        "gate": "python3 -m unittest tests.test_mvp2_t1_smolvm_evidence",
    },
    "t2-tree-sig-119": {
        "gate_name": "test_mvp2_t2_tree_sig_119.py",
        "gate": "python3 -m unittest tests.test_mvp2_t2_tree_sig_119",
    },
    "t3-daemon-stop-fail": {
        "gate_name": "test_mvp2_t3_daemon_stop.py",
        "gate": (
            "python3 -m unittest tests.test_mvp2_t3_daemon_stop "
            "tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_overtime_daemon_stop_timeout_uses_shared_text"
        ),
    },
    "t4-timeout-substep": {
        "gate_name": "test_mvp2_t4_timeout_step.py",
        "gate": (
            "python3 -m unittest tests.test_mvp2_t4_timeout_step "
            "tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_overtime_timeout_reason_is_shared_text "
            "tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_festival_timeout_reason_is_shared_text "
            "tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_overtime_daemon_stop_timeout_uses_shared_text"
        ),
    },
    "t5-receipts-outside-repo": {
        "gate_name": "test_mvp2_t5_receipts.py",
        "gate": "python3 -m unittest tests.test_mvp2_t5_receipts",
    },
    "t6-tree-sig-three": {
        "gate_name": "test_mvp2_t6_tree_sig_three.py",
        "gate": "python3 -m unittest tests.test_mvp2_t6_tree_sig_three",
    },
}


def build_argv(
    pfy: Path,
    task_text: str,
    repo: Path,
    base: str,
    test_cmd: str,
    receipt_dir: Path,
    retries: int | None = None,
    keep_worktree: bool = True,
    timeout: str = GROK_TIMEOUT,
) -> list[str]:
    """Argv for one reviewed cloud build. Refuses --local and --no-review."""
    argv = [
        str(pfy),
        "build",
        task_text,
        "--repo",
        str(repo),
        "--base",
        base,
        "--test-cmd",
        test_cmd,
        "--receipt-dir",
        str(receipt_dir),
        "--timeout",
        str(timeout),
    ]
    if keep_worktree:
        argv.append("--keep-worktree")
    if retries is not None:
        argv.extend(["--retries", str(int(retries))])
    banned = [flag for flag in ("--local", "--no-review") if flag in argv]
    if banned:
        raise SystemExit("refusing " + ",".join(banned))
    return argv


def secret_hits(text: str) -> int:
    """Count secret-shaped matches. Does not return the matched text."""
    if not text:
        return 0
    return sum(len(part.findall(text)) for part in _SECRET_PARTS)


def redact_text(text: str) -> str:
    cleaned = text or ""
    for part in _SECRET_PARTS:
        cleaned = part.sub("[redacted]", cleaned)
    return cleaned


def out_dir(label: str, task_id: str) -> Path:
    base = ROOT / "eval" / "mvp-1031" / "sixtask"
    if label in ("", "pass1"):
        return base / task_id
    return base / label / task_id


def _mem_available_kib() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1])
    return 0


def host_pressure() -> str | None:
    """Return 'mem' or 'load' when the drop-in floor is breached, else None."""
    if _mem_available_kib() < MEM_FLOOR_KIB:
        return "mem"
    cores = os.cpu_count() or 1
    if os.getloadavg()[1] > (2 * cores):
        return "load"
    return None


def _git(cwd: Path, args: list[str], timeout: float = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _identity() -> list[str]:
    return [
        "-c",
        "user.name=pfy-sixtask",
        "-c",
        "user.email=pfy-sixtask@localhost",
        "-c",
        "commit.gpgsign=false",
    ]


def _say(line: str) -> None:
    print(line, flush=True)


def ensure_clone(task_id: str, label: str, fresh: bool) -> Path:
    dest = CLONES / (label or "pass1") / task_id
    if dest.exists() and fresh:
        shutil.rmtree(dest)
    if (dest / ".git").is_dir() or (dest / ".git").is_file():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    cloned = subprocess.run(
        ["git", "clone", "--no-hardlinks", "--quiet", str(ROOT), str(dest)],
        text=True,
        capture_output=True,
        timeout=300,
        check=False,
    )
    if cloned.returncode != 0 or not (dest / ".git").exists():
        raise SystemExit("clone failed: " + (cloned.stderr or cloned.stdout or "no repo"))
    return dest


def plant(dest: Path, task_id: str, task: dict) -> str:
    reset = _git(dest, ["checkout", "-B", "demo-base", BASE])
    if reset.returncode != 0:
        raise SystemExit("checkout base failed: " + (reset.stderr or reset.stdout))
    hard = _git(dest, ["reset", "--hard", BASE])
    if hard.returncode != 0:
        raise SystemExit("reset base failed: " + (hard.stderr or hard.stdout))
    gate_name = task["gate_name"]
    src = GATES / gate_name
    dst = dest / "tests" / gate_name
    if not src.is_file():
        raise SystemExit("missing gate " + str(src))
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    added = _git(dest, ["add", "--", str(Path("tests") / gate_name)])
    if added.returncode != 0:
        raise SystemExit("git add gate failed: " + (added.stderr or added.stdout))
    committed = _git(
        dest,
        _identity()
        + ["commit", "-m", "test: red gate for " + task_id],
    )
    if committed.returncode != 0:
        raise SystemExit("plant commit failed: " + (committed.stderr or committed.stdout))
    sha = _git(dest, ["rev-parse", "HEAD"])
    planted = (sha.stdout or "").strip()
    if len(planted) != 40:
        raise SystemExit("plant sha missing")
    return planted


def prove_red(dest: Path, gate: str) -> None:
    scratch = SCRATCH / "prove-red"
    scratch.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["TMPDIR"] = str(scratch)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PFY_SMOKE_RECEIPT_DIR", None)
    proc = subprocess.run(
        shlex.split(gate),
        cwd=str(dest),
        env=env,
        text=True,
        capture_output=True,
        timeout=300,
        check=False,
    )
    if proc.returncode == 0:
        raise SystemExit("gate not red before build")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _worktree(dest: Path) -> Path | None:
    root = dest / "tmp" / "cloud-build"
    if not root.is_dir():
        return None
    dirs = [path for path in root.iterdir() if path.is_dir()]
    if not dirs:
        return None
    dirs.sort(key=lambda path: path.stat().st_mtime)
    return dirs[-1]


def _write_diff(dest: Path, planted: str, commit: str | None, diff_path: Path) -> None:
    if commit and len(commit) == 40:
        proc = _git(dest, ["diff", planted, commit], timeout=60)
        diff_path.write_text(proc.stdout or "", encoding="utf-8")
        return
    work = _worktree(dest)
    if work is None:
        diff_path.write_text("", encoding="utf-8")
        return
    tracked = _git(work, ["diff", "HEAD"], timeout=60)
    chunks = [tracked.stdout or ""]
    status = _git(work, ["status", "--porcelain", "-uall"], timeout=60)
    for line in (status.stdout or "").splitlines():
        if not line.startswith("??"):
            continue
        rel = line[3:].strip()
        if not rel or rel.startswith("tmp/") or rel == "tmp":
            continue
        untracked = _git(work, ["diff", "--no-index", "--", "/dev/null", rel], timeout=60)
        if untracked.stdout:
            chunks.append(untracked.stdout)
    diff_path.write_text("\n".join(chunk for chunk in chunks if chunk), encoding="utf-8")


def _run_gate(cwd: Path, gate: str) -> int:
    scratch = SCRATCH / "gate-rerun"
    home = scratch / "home"
    scratch.mkdir(parents=True, exist_ok=True)
    home.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["TMPDIR"] = str(scratch)
    env["HOME"] = str(home)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PFY_SMOKE_RECEIPT_DIR", None)
    proc = subprocess.run(
        shlex.split(gate),
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
        timeout=300,
        check=False,
    )
    log = scratch / "last.log"
    log.write_text((proc.stdout or "") + "\n" + (proc.stderr or ""), encoding="utf-8")
    return proc.returncode


def canonical_gate(dest: Path, task: dict, commit: str | None) -> dict:
    """Re-run the canonical gate. Restore any file we swap."""
    gate_name = task["gate_name"]
    canonical = (GATES / gate_name).read_bytes()
    work = _worktree(dest)
    target = work
    if target is None and commit and len(commit) == 40:
        target = SCRATCH / "gate-tree" / dest.name
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        archive = subprocess.run(
            ["git", "-C", str(dest), "archive", commit],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )
        if archive.returncode != 0:
            return {"exit": None, "acceptance_unchanged": None, "error": "archive failed"}
        extracted = subprocess.run(
            ["tar", "-x", "-C", str(target)],
            input=archive.stdout,
            check=False,
            timeout=120,
        )
        if extracted.returncode != 0:
            return {"exit": None, "acceptance_unchanged": None, "error": "extract failed"}
    if target is None:
        return {"exit": None, "acceptance_unchanged": None, "error": "no tree"}
    gate_path = target / "tests" / gate_name
    saved = gate_path.read_bytes() if gate_path.is_file() else None
    unchanged = saved == canonical
    if not unchanged:
        gate_path.parent.mkdir(parents=True, exist_ok=True)
        gate_path.write_bytes(canonical)
    try:
        code = _run_gate(target, task["gate"])
    finally:
        if work is not None:
            if saved is None:
                if gate_path.exists() and not unchanged:
                    gate_path.unlink()
            elif not unchanged:
                gate_path.write_bytes(saved)
    return {"exit": code, "acceptance_unchanged": unchanged}


def _child_env() -> dict[str, str]:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    state = SCRATCH / "pfy-state"
    state.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["TMPDIR"] = str(SCRATCH)
    env["PFY_STATE_DIR"] = str(state)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_one(task_id: str, label: str, retries: int | None, fresh: bool) -> int:
    task = TASKS.get(task_id)
    if task is None:
        raise SystemExit("unknown task " + task_id)
    pressure = host_pressure()
    if pressure:
        _say("HOST_PRESSURE " + pressure + " pausing 600s")
        time.sleep(600)
        pressure = host_pressure()
        if pressure:
            _say("HOST_PRESSURE persist " + pressure)
            return 75
    text_path = TASKS_DIR / (task_id + ".md")
    task_text = text_path.read_text(encoding="utf-8")
    dest = ensure_clone(task_id, label, fresh)
    planted = plant(dest, task_id, task)
    prove_red(dest, task["gate"])
    receipt_dir = out_dir(label, task_id)
    if receipt_dir.exists():
        shutil.rmtree(receipt_dir)
    receipt_dir.mkdir(parents=True)
    argv = build_argv(
        ROOT / "pfy",
        task_text,
        dest,
        "demo-base",
        task["gate"],
        receipt_dir,
        retries=retries,
    )
    _say("TASK_START " + task_id)
    started = time.monotonic()
    proc = subprocess.run(
        argv,
        cwd=str(ROOT),
        env=_child_env(),
        text=True,
        capture_output=True,
        timeout=3 * 60 * 60,
        check=False,
    )
    wall = round(time.monotonic() - started, 1)
    log_text = redact_text((proc.stdout or "") + "\n" + (proc.stderr or ""))
    (receipt_dir / "run.log").write_text(log_text, encoding="utf-8")
    receipt_path = receipt_dir / "receipt.json"
    receipt: dict = {}
    if receipt_path.is_file():
        raw = receipt_path.read_text(encoding="utf-8")
        hits = secret_hits(raw)
        if hits:
            receipt_path.write_text(redact_text(raw), encoding="utf-8")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    commit = receipt.get("commit") if isinstance(receipt.get("commit"), str) else None
    diff_path = receipt_dir / "diff.patch"
    _write_diff(dest, planted, commit, diff_path)
    diff_raw = diff_path.read_text(encoding="utf-8")
    if secret_hits(diff_raw):
        diff_path.write_text(redact_text(diff_raw), encoding="utf-8")
    gate = canonical_gate(dest, task, commit if commit else None)
    attempts = receipt.get("attempts")
    attempt_count = len(attempts) if isinstance(attempts, list) else None
    review = receipt.get("review") if isinstance(receipt.get("review"), dict) else {}
    lane = _git(ROOT, ["rev-parse", "HEAD"])
    meta = {
        "task": task_id,
        "label": label or "pass1",
        "command": argv,
        "wall_s": wall,
        "exit_code": proc.returncode,
        "receipt_status": receipt.get("status"),
        "receipt_reason": receipt.get("reason"),
        "attempts": attempt_count,
        "review_verdict": review.get("verdict"),
        "review_reasons": review.get("reasons") or [],
        "commit": commit,
        "branch": receipt.get("branch"),
        "base": BASE,
        "planted": planted,
        "lane_head": (lane.stdout or "").strip(),
        "gate_rerun": gate,
        "human": "pending",
        "human_note": "",
        "timeout_s": int(GROK_TIMEOUT),
    }
    (receipt_dir / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _say(
        "TASK_DONE %s exit=%s status=%s attempts=%s wall=%s gate_rerun=%s review=%s"
        % (
            task_id,
            proc.returncode,
            receipt.get("status"),
            attempt_count,
            wall,
            gate.get("exit"),
            review.get("verdict"),
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one MVP-2 task through ./pfy build")
    parser.add_argument("task_id")
    parser.add_argument("--label", default="pass1")
    parser.add_argument("--retries", type=int, default=None)
    parser.add_argument("--no-fresh", action="store_true")
    args = parser.parse_args(argv)
    if args.retries is not None and args.retries < 0:
        raise SystemExit("--retries must be >= 0")
    return run_one(args.task_id, args.label, args.retries, fresh=not args.no_fresh)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except subprocess.TimeoutExpired:
        print("TASK_TIMEOUT wrapper", flush=True)
        sys.exit(124)
