#!/usr/bin/env python3
"""Run one mvp-realfail3 case against ./pfy build.

Usage: python3 eval/mvp-1031/realfail3/drive.py <case>

Scratch and TMPDIR stay under this worktree's tmp/. Throwaway clones live in
tmp/realfail3-targets/. The driver signals only process groups it started.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVAL = ROOT / "eval" / "mvp-1031" / "realfail3"
REPORT = EVAL / "REPORT.md"
TARGETS = ROOT / "tmp" / "realfail3-targets"
SCRATCH = ROOT / "tmp" / "realfail3-tmp"
GATES = EVAL / "gates"
VALUE_IS = GATES / "value_is.py"
LAUNCH = datetime(2026, 10, 31, 22, 38, 29, tzinfo=timezone.utc)
STOP_NEW = LAUNCH + timedelta(hours=8) - timedelta(minutes=20)

SECRET_SCRUBS = (
    ("akia", re.compile(r"AKIA[0-9A-Z]{16}")),
    (
        "pem",
        re.compile(
            r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
    ),
    ("bearer", re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]{8,}")),
    ("sk", re.compile(r"(?i)\b(?:sk|ghp)_[A-Za-z0-9_\-]{8,}")),
    ("xai", re.compile(r"\bxai-[A-Za-z0-9]{6,}\b")),
)

HEADER = """# Real failure receipts (wave 4)

One row per run. Expected values come from the Functional MVP failure table. `matches` means status, reason, and process exit matched that row and the case invariants held. `FINDING` means a DoD clause failed. Notes say what differed. The runner was not edited.

Rows: {marker}

| Case | Mode | Exp status | Exp reason | Exp exit | Obs status | Obs reason | Obs exit | Verdict | Attempts | Recovery | Notes |
|------|------|------------|------------|----------|------------|------------|----------|---------|----------|----------|-------|
"""


class Proc:
    def __init__(self, code: int, out: str, err: str) -> None:
        self.returncode = code
        self.stdout = out
        self.stderr = err


def mem_kib() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1])
    return 0


def load_1() -> float:
    return float(Path("/proc/loadavg").read_text(encoding="utf-8").split()[0])


def host_blocked() -> bool:
    cores = os.cpu_count() or 1
    return mem_kib() < 16 * 1024 * 1024 or load_1() > cores * 2


def host_gate() -> None:
    if not host_blocked():
        return
    time.sleep(600)
    if host_blocked():
        print("HOST_PRESSURE")
        raise SystemExit(75)


def wall_gate() -> None:
    now = datetime.now(timezone.utc)
    if now >= STOP_NEW:
        print("WALL_CAP")
        raise SystemExit(75)


def scrub(text: str) -> str:
    cleaned = text or ""
    for _name, pattern in SECRET_SCRUBS:
        cleaned = pattern.sub("[redacted]", cleaned)
    return cleaned


def git(repo: Path, args: list[str], check: bool = False) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "pfy-realfail3"
    env["GIT_AUTHOR_EMAIL"] = "pfy-realfail3@localhost"
    env["GIT_COMMITTER_NAME"] = "pfy-realfail3"
    env["GIT_COMMITTER_EMAIL"] = "pfy-realfail3@localhost"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["TMPDIR"] = str(SCRATCH)
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        env=env,
        text=True,
        capture_output=True,
        check=check,
    )


def assert_throwaway(repo: Path) -> None:
    resolved = repo.resolve()
    root = TARGETS.resolve()
    if resolved != root and root not in resolved.parents:
        raise SystemExit("refusing repo outside tmp/realfail3-targets")


def init_clone(name: str, extra: dict[str, str] | None = None) -> Path:
    dest = TARGETS / name
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.mkdir()
    created = git(dest, ["init", "-b", "main"])
    if created.returncode != 0:
        git(dest, ["init"], check=True)
        git(dest, ["symbolic-ref", "HEAD", "refs/heads/main"], check=True)
    (dest / "app.py").write_text("value = 0\n", encoding="utf-8")
    (dest / "README.md").write_text("throwaway clone for realfail3\n", encoding="utf-8")
    (dest / ".gitignore").write_text("tmp/\n", encoding="utf-8")
    paths = ["app.py", "README.md", ".gitignore"]
    for rel, body in (extra or {}).items():
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        paths.append(rel)
    git(dest, ["add", "--", *paths], check=True)
    git(dest, ["commit", "-m", "base"], check=True)
    assert_throwaway(dest)
    return dest


def snap(repo: Path) -> dict:
    head = git(repo, ["rev-parse", "HEAD"])
    status = git(repo, ["status", "--porcelain"])
    sym = git(repo, ["symbolic-ref", "-q", "HEAD"])
    branches = git(repo, ["branch", "--format=%(refname:short)"])
    stash = git(repo, ["stash", "list"])
    names = sorted(line.strip() for line in (branches.stdout or "").splitlines() if line.strip())
    return {
        "head": (head.stdout or "").strip(),
        "status": status.stdout or "",
        "detached": sym.returncode != 0,
        "branches": names,
        "stash": stash.stdout or "",
    }


def cloud_branches(info: dict) -> list[str]:
    return [name for name in info["branches"] if name.startswith("cloud/")]


def prepare(name: str) -> Path:
    dest = EVAL / name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    return dest


def base_env(extra: dict | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env["TMPDIR"] = str(SCRATCH)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for key in ("XAI_API_KEY", "GROK_API_KEY"):
        env.pop(key, None)
    if extra:
        env.update(extra)
    return env


def quoted_cmd(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def value_cmd(rel: str, expected: str) -> str:
    return quoted_cmd([sys.executable, str(VALUE_IS), rel, expected])


def green_cmd() -> str:
    return quoted_cmd([sys.executable, "-c", "print('gate-ok')"])


def real_grok() -> str:
    found = shutil.which("grok")
    if not found:
        print("GROK_MISSING")
        raise SystemExit(1)
    return found


def _cmdline(pid: int) -> str:
    try:
        raw = Path("/proc/%s/cmdline" % pid).read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\0", b" ").decode("utf-8", "replace")


def _alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def kill_group(pid: int) -> None:
    if pid <= 1 or pid == os.getpid():
        return
    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return
    if pgid <= 1 or pgid == os.getpgrp():
        return
    try:
        os.killpg(pgid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return
        except PermissionError:
            break
        time.sleep(0.05)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def sweep_clone(repo: Path, owned: list[int]) -> None:
    token = str(repo / "tmp" / "cloud-build")
    seen = set(owned)
    proc = Path("/proc")
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid in seen or pid == os.getpid() or pid <= 1:
            continue
        if token in _cmdline(pid):
            seen.add(pid)
    for pid in seen:
        if pid == os.getpid() or pid <= 1:
            continue
        if pid in owned or token in _cmdline(pid):
            kill_group(pid)


def run_build(args: list[str], env: dict | None = None, timeout: float = 600) -> Proc:
    merged = base_env()
    if env:
        merged.update(env)
    proc = subprocess.Popen(
        [str(ROOT / "pfy"), "build", *args],
        cwd=str(ROOT),
        env=merged,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_group(proc.pid)
        try:
            out, err = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            out, err = "", ""
        code = proc.returncode if proc.returncode is not None else -9
        return Proc(code, out or "", err or "")
    return Proc(proc.returncode if proc.returncode is not None else 1, out or "", err or "")


def launch_build(args: list[str]) -> subprocess.Popen:
    return subprocess.Popen(
        [str(ROOT / "pfy"), "build", *args],
        cwd=str(ROOT),
        env=base_env(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )


def common_args(repo: Path, receipt: Path, task: str, test_cmd: str | None, timeout: str) -> list[str]:
    args = [
        task,
        "--repo",
        str(repo),
        "--base",
        "HEAD",
        "--receipt-dir",
        str(receipt),
        "--retries",
        "0",
        "--no-review",
        "--timeout",
        timeout,
    ]
    if test_cmd is not None:
        args.extend(["--test-cmd", test_cmd])
    return args


def load_receipt(case_dir: Path) -> dict | None:
    path = case_dir / "receipt.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(scrub(text), encoding="utf-8")


def cell(value: object) -> str:
    text = scrub(str(value)).replace("|", "/").replace("\n", " ").strip()
    return text


def parse_rows(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [item.strip() for item in line.strip().strip("|").split("|")]
        if len(cells) < 12 or cells[0] in {"Case", "case"}:
            continue
        if all(set(item) <= set("-: ") for item in cells):
            continue
        rows.append(cells)
    return rows


def marker_of(text: str) -> str:
    if "Rows: complete" in text:
        return "complete"
    return "partial"


def upsert_row(row: list[str]) -> None:
    existing = REPORT.read_text(encoding="utf-8") if REPORT.is_file() else ""
    rows = [item for item in parse_rows(existing) if item[0] != row[0]]
    rows.append(row)
    rows.sort(key=lambda item: item[0])
    body = HEADER.format(marker=marker_of(existing))
    for item in rows:
        body += "| " + " | ".join(item) + " |\n"
    REPORT.write_text(body, encoding="utf-8")


def recovery_cell(recovery: str) -> str:
    if recovery == "":
        return "empty"
    return cell(recovery)[:80]


def checkout_problems(before: dict, after: dict) -> list[str]:
    problems = []
    if before["head"] != after["head"]:
        problems.append("HEAD changed")
    if before["status"] != after["status"]:
        problems.append("porcelain changed")
    if before["detached"] != after["detached"]:
        problems.append("detached state changed")
    if before["stash"] != after["stash"]:
        problems.append("stash list changed")
    return problems


def root_problems(before: str, after: str) -> list[str]:
    before_lines = {line for line in before.splitlines() if line.strip()}
    extra = []
    for line in after.splitlines():
        if not line.strip() or line in before_lines:
            continue
        if "eval/mvp-1031/realfail3/" in line:
            continue
        extra.append(line.strip())
    if extra:
        return ["pfy dirtied the catalog checkout: %s" % cell("; ".join(extra[:4]))]
    return []


def branch_problems(repo: Path, before: dict, after: dict, receipt: dict | None, expect_pass: bool) -> list[str]:
    problems = []
    new = [name for name in cloud_branches(after) if name not in before["branches"]]
    if receipt is None:
        if new:
            problems.append("no receipt but a cloud branch was created")
        return problems
    status = receipt.get("status")
    if expect_pass and status == "PASS":
        branch = str(receipt.get("branch") or "")
        commit = str(receipt.get("commit") or "")
        if not branch.startswith("cloud/"):
            problems.append("PASS branch does not start with cloud/")
        elif branch not in after["branches"]:
            problems.append("PASS branch is missing")
        else:
            shown = git(repo, ["rev-parse", branch])
            if (shown.stdout or "").strip() != commit:
                problems.append("branch does not point at the receipt commit")
        if len(commit) != 40:
            problems.append("PASS commit is not 40 hex")
        if receipt.get("pushed") is not False:
            problems.append("pushed is not false")
        if receipt.get("worktree_removed") is not True:
            problems.append("worktree was not removed")
    elif status in {"FAIL", "TIMEOUT", "BLOCKED", "ABORTED"} and new:
        problems.append("failure left cloud branch %s" % new[0])
    return problems


def commit_names(repo: Path, sha: str) -> list[str]:
    if len(sha) != 40:
        return []
    shown = git(repo, ["diff-tree", "--no-commit-id", "--name-only", "-r", sha])
    return [line.strip() for line in (shown.stdout or "").splitlines() if line.strip()]


def commit_line_count(repo: Path, sha: str) -> int:
    if len(sha) != 40:
        return 0
    shown = git(repo, ["show", "--numstat", "--format=", sha])
    total = 0
    for line in (shown.stdout or "").splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        for item in parts[:2]:
            if item.isdigit():
                total += int(item)
    return total


def attempt_tail(receipt: dict | None) -> str:
    if not receipt:
        return ""
    chunks = []
    for row in receipt.get("attempts") or []:
        if isinstance(row, dict):
            chunks.append(str(row.get("output_tail") or ""))
    return "\n".join(chunks)


def judge(exp_status: str, exp_reason: str, exp_exit: int, obs_status: str, obs_reason: str, obs_exit: int, problems: list[str]) -> str:
    same = exp_status == obs_status and exp_reason == obs_reason and exp_exit == obs_exit
    if same and not problems:
        return "matches"
    return "FINDING"


def save_run(case_dir: Path, proc: Proc) -> None:
    write_text(case_dir / "stdout.txt", (proc.stdout or "")[-4000:])
    write_text(case_dir / "stderr.txt", (proc.stderr or "")[-4000:])


def finish_pfy(
    name: str,
    mode: str,
    repo: Path,
    case_dir: Path,
    before: dict,
    root_before: str,
    proc: Proc,
    exp_status: str,
    exp_reason: str,
    exp_exit: int,
    extra_problems: list[str] | None = None,
    note: str = "",
    expect_pass: bool = False,
) -> None:
    save_run(case_dir, proc)
    receipt = load_receipt(case_dir)
    after = snap(repo)
    problems = checkout_problems(before, after)
    problems.extend(root_problems(root_before, git(ROOT, ["status", "--porcelain"]).stdout or ""))
    problems.extend(branch_problems(repo, before, after, receipt, expect_pass))
    problems.extend(extra_problems or [])
    if receipt is None:
        err_lines = [line.strip() for line in (proc.stderr or "").splitlines() if line.strip()]
        obs_status = "none"
        obs_reason = cell(err_lines[-1] if err_lines else "no-receipt")[:80]
        recovery = ""
        attempts = "-"
    else:
        obs_status = str(receipt.get("status") or "none")
        obs_reason = str(receipt.get("reason") or "")
        recovery = str(receipt.get("recovery") or "")
        got_attempts = receipt.get("attempts")
        attempts = str(len(got_attempts)) if isinstance(got_attempts, list) else "-"
        if receipt.get("exit_code") != proc.returncode:
            problems.append(
                "process exit %s != receipt exit_code %s" % (proc.returncode, receipt.get("exit_code"))
            )
    verdict = judge(exp_status, exp_reason, exp_exit, obs_status, obs_reason, proc.returncode, problems)
    bits = []
    if note:
        bits.append(note)
    if problems:
        bits.append("; ".join(problems))
    if receipt and receipt.get("review"):
        bits.append("review %s" % cell((receipt.get("review") or {}).get("verdict")))
    notes = cell(" ".join(bit for bit in bits if bit))
    if verdict == "FINDING" and not notes:
        notes = "see meta.json"
    meta = {
        "process_exit": proc.returncode,
        "status": obs_status,
        "reason": obs_reason,
        "recovery": recovery,
        "attempts": attempts,
        "verdict": verdict,
        "exp_status": exp_status,
        "exp_reason": exp_reason,
        "exp_exit": exp_exit,
        "invariant_problems": problems,
        "head": after["head"],
        "detached": after["detached"],
        "porcelain": after["status"],
        "cloud_branches": cloud_branches(after),
        "runner_sha": (git(ROOT, ["rev-parse", "HEAD"]).stdout or "").strip(),
        "elapsed_note": "see the driver clock in stdout of this process",
    }
    (case_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    upsert_row(
        [
            name,
            mode,
            exp_status,
            exp_reason,
            str(exp_exit),
            obs_status,
            cell(obs_reason),
            str(proc.returncode),
            verdict,
            attempts,
            recovery_cell(recovery),
            notes,
        ]
    )
    print(
        "CASE %s verdict=%s exit=%s status=%s reason=%s problems=%d"
        % (name, verdict, proc.returncode, obs_status, obs_reason, len(problems))
    )


def root_status() -> str:
    return git(ROOT, ["status", "--porcelain"]).stdout or ""


def case_dirty() -> None:
    host_gate()
    wall_gate()
    real_grok()
    repo = init_clone("dirty-tree")
    (repo / "kept-dirty.txt").write_text("clean\n", encoding="utf-8")
    git(repo, ["add", "--", "kept-dirty.txt"], check=True)
    git(repo, ["commit", "-m", "tracked file"], check=True)
    (repo / "kept-dirty.txt").write_text("dirty marker\n", encoding="utf-8")
    (repo / "untracked-dirty.txt").write_text("free\n", encoding="utf-8")
    before = snap(repo)
    case_dir = prepare("dirty-tree")
    root_before = root_status()
    task = "In app.py change the line value = 0 to value = 1. Do not edit or create any other file. Do not commit."
    started = time.monotonic()
    proc = run_build(
        common_args(repo, case_dir, task, value_cmd("app.py", "value = 1"), "240"),
        timeout=560,
    )
    extra = []
    after = snap(repo)
    if "kept-dirty.txt" not in after["status"] or "untracked-dirty.txt" not in after["status"]:
        extra.append("dirty paths disappeared from porcelain")
    if "dirty marker" not in (repo / "kept-dirty.txt").read_text(encoding="utf-8"):
        extra.append("tracked dirty content was rewritten")
    receipt = load_receipt(case_dir)
    sha = "" if not receipt else str(receipt.get("commit") or "")
    names = commit_names(repo, sha)
    if "kept-dirty.txt" in names or "untracked-dirty.txt" in names:
        extra.append("dirty path was committed")
    finish_pfy(
        "dirty-tree",
        "real",
        repo,
        case_dir,
        before,
        root_before,
        proc,
        "PASS",
        "ok",
        0,
        extra,
        "dirty porcelain must survive. elapsed %.0fs" % (time.monotonic() - started),
        expect_pass=True,
    )
    sweep_clone(repo, [])


def case_detached() -> None:
    host_gate()
    wall_gate()
    real_grok()
    repo = init_clone("detached-head")
    git(repo, ["checkout", "--detach"], check=True)
    before = snap(repo)
    if not before["detached"]:
        raise SystemExit("clone did not detach")
    case_dir = prepare("detached-head")
    root_before = root_status()
    task = "In app.py change the line value = 0 to value = 1. Do not edit or create any other file. Do not commit."
    proc = run_build(
        common_args(repo, case_dir, task, value_cmd("app.py", "value = 1"), "240"),
        timeout=560,
    )
    after = snap(repo)
    extra = []
    if not after["detached"]:
        extra.append("HEAD is no longer detached")
    if after["head"] != before["head"]:
        extra.append("detached SHA changed")
    finish_pfy(
        "detached-head",
        "real",
        repo,
        case_dir,
        before,
        root_before,
        proc,
        "PASS",
        "ok",
        0,
        extra,
        "HEAD must stay detached at the same SHA",
        expect_pass=True,
    )
    sweep_clone(repo, [])


def case_two() -> None:
    host_gate()
    wall_gate()
    real_grok()
    repo = init_clone("two-builds")
    before = snap(repo)
    case_dir = prepare("two-builds")
    left_dir = case_dir / "left"
    right_dir = case_dir / "right"
    left_dir.mkdir()
    right_dir.mkdir()
    root_before = root_status()
    left_args = common_args(
        repo,
        left_dir,
        "Create left.py whose only line is side = 1. Do not edit any other file. Do not commit.",
        value_cmd("left.py", "side = 1"),
        "200",
    )
    right_args = common_args(
        repo,
        right_dir,
        "Create right.py whose only line is side = 2. Do not edit any other file. Do not commit.",
        value_cmd("right.py", "side = 2"),
        "200",
    )
    left = launch_build(left_args)
    time.sleep(2)
    right = launch_build(right_args)
    overlapped = left.poll() is None and right.poll() is None
    exits = []
    tails = {}
    try:
        for label, proc in (("left", left), ("right", right)):
            try:
                out, err = proc.communicate(timeout=520)
            except subprocess.TimeoutExpired:
                kill_group(proc.pid)
                try:
                    out, err = proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    out, err = "", ""
            code = proc.returncode if proc.returncode is not None else -9
            exits.append(code)
            write_text(case_dir / label / "stdout.txt", (out or "")[-2000:])
            write_text(case_dir / label / "stderr.txt", (err or "")[-2000:])
            tails[label] = code
        after = snap(repo)
        fsck = git(repo, ["fsck", "--no-progress"])
        problems = checkout_problems(before, after)
        problems.extend(root_problems(root_before, root_status()))
        new = [name for name in cloud_branches(after) if name not in before["branches"]]
        if not overlapped:
            problems.append("the two builds did not overlap")
        if fsck.returncode != 0:
            problems.append("git fsck exit %s" % fsck.returncode)
        if len(new) < 2:
            problems.append("expected 2 cloud branches, saw %d" % len(new))
        if exits[0] != 0 or exits[1] != 0:
            problems.append("child exits %s and %s" % (exits[0], exits[1]))
        left_receipt = load_receipt(left_dir)
        right_receipt = load_receipt(right_dir)
        intact = not problems
        status = "PASS" if intact else "FAIL"
        reason = "intact" if intact else "not-intact"
        code = 0 if intact else 1
        summary = {
            "schema": "pfy-realfail3-observe/1",
            "status": status,
            "reason": reason,
            "exit_code": code,
            "recovery": "",
            "attempts": [],
            "pushed": False,
            "branch": None,
            "commit": None,
        }
        (case_dir / "receipt.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        proc = Proc(code, "", "")
        note = "left %s right %s branches %d fsck %s overlap %s" % (
            exits[0],
            exits[1],
            len(new),
            fsck.returncode,
            overlapped,
        )
        if left_receipt:
            note += " left_reason %s" % cell(left_receipt.get("reason"))
        if right_receipt:
            note += " right_reason %s" % cell(right_receipt.get("reason"))
        finish_pfy(
            "two-builds",
            "real",
            repo,
            case_dir,
            before,
            root_before,
            proc,
            "PASS",
            "intact",
            0,
            problems,
            note,
            expect_pass=False,
        )
    finally:
        sweep_clone(repo, [left.pid, right.pid])


def case_over_cap() -> None:
    host_gate()
    wall_gate()
    real_grok()
    repo = init_clone("over-cap")
    before = snap(repo)
    case_dir = prepare("over-cap")
    root_before = root_status()
    task = (
        "Create exactly four files named a.py, b.py, c.py, and d.py. "
        "Each file must contain exactly 70 lines. Each line is the file name, a space, "
        "and the line number from 1 to 70. Do not create or edit any other file. Do not commit."
    )
    proc = run_build(
        common_args(repo, case_dir, task, quoted_cmd([sys.executable, str(GATES / "over_cap.py")]), "300"),
        timeout=700,
    )
    receipt = load_receipt(case_dir)
    sha = "" if not receipt else str(receipt.get("commit") or "")
    names = commit_names(repo, sha)
    lines = commit_line_count(repo, sha)
    extra = []
    if receipt and receipt.get("status") == "PASS" and len(names) <= 3 and lines <= 250:
        extra.append("PASS diff stayed inside 3 files and 250 lines, so the cap was not exercised")
    note = "commit files %d lines %d names %s" % (len(names), lines, ",".join(names[:8]))
    finish_pfy(
        "over-cap",
        "real",
        repo,
        case_dir,
        before,
        root_before,
        proc,
        "PASS",
        "ok",
        0,
        extra,
        note,
        expect_pass=True,
    )
    sweep_clone(repo, [])


def case_no_tests() -> None:
    host_gate()
    wall_gate()
    real_grok()
    repo = init_clone("no-tests")
    before = snap(repo)
    case_dir = prepare("no-tests")
    root_before = root_status()
    task = (
        "In app.py change the line value = 0 to value = 1. "
        "Do not add a tests directory. Do not create or edit any other file. Do not commit."
    )
    proc = run_build(common_args(repo, case_dir, task, None, "240"), timeout=560)
    receipt = load_receipt(case_dir)
    extra = []
    gate = (receipt or {}).get("gate") or {}
    cmd = str(gate.get("cmd") or "")
    if "unittest discover" not in cmd:
        extra.append("gate cmd was not the default discover")
    before_gate = gate.get("before") or {}
    if isinstance(before_gate, dict) and before_gate.get("exit") not in {None, 0}:
        attempts = (receipt or {}).get("attempts") or []
        if any(isinstance(row, dict) and int(row.get("n") or 0) >= 1 for row in attempts):
            extra.append("")  # observed, not a table miss
    extra = [item for item in extra if item]
    note = "default gate on a repo with no tests directory"
    if isinstance(before_gate, dict):
        note += " before_exit %s" % before_gate.get("exit")
    finish_pfy(
        "no-tests",
        "real",
        repo,
        case_dir,
        before,
        root_before,
        proc,
        "FAIL",
        "tests",
        1,
        extra,
        note,
        expect_pass=False,
    )
    sweep_clone(repo, [])


def case_hang() -> None:
    host_gate()
    wall_gate()
    real_grok()
    repo = init_clone("gate-hang")
    before = snap(repo)
    case_dir = prepare("gate-hang")
    counter = case_dir / "counter"
    root_before = root_status()
    task = "In app.py change the line value = 0 to value = 1. Do not edit or create any other file. Do not commit."
    cmd = quoted_cmd([sys.executable, str(GATES / "hang_once.py"), str(counter)])
    proc = run_build(common_args(repo, case_dir, task, cmd, "180"), timeout=500)
    receipt = load_receipt(case_dir)
    extra = hang_problems(receipt)
    if _grok_timed_out(receipt):
        # The first timeout was the model, so the hanging gate never ran. One longer try.
        sweep_clone(repo, [])
        if case_dir.exists():
            shutil.rmtree(case_dir)
        case_dir = prepare("gate-hang")
        counter = case_dir / "counter"
        before = snap(repo)
        root_before = root_status()
        proc = run_build(common_args(repo, case_dir, task, quoted_cmd([sys.executable, str(GATES / "hang_once.py"), str(counter)]), "360"), timeout=860)
        receipt = load_receipt(case_dir)
        extra = hang_problems(receipt)
        extra.append("first run timed out in grok; this row is the longer timeout")
    finish_pfy(
        "gate-hang",
        "real",
        repo,
        case_dir,
        before,
        root_before,
        proc,
        "TIMEOUT",
        "timeout",
        3,
        extra,
        "gate sleeps after the first call",
        expect_pass=False,
    )
    sweep_clone(repo, [])


def _grok_timed_out(receipt: dict | None) -> bool:
    if not receipt or receipt.get("reason") != "timeout":
        return False
    after = (receipt.get("gate") or {}).get("after")
    return after in {None, {}}


def hang_problems(receipt: dict | None) -> list[str]:
    problems = []
    if not receipt:
        return problems
    if receipt.get("status") == "TIMEOUT" and "--timeout" not in str(receipt.get("recovery") or ""):
        problems.append("timeout recovery does not mention a longer --timeout")
    after = (receipt.get("gate") or {}).get("after") or {}
    tail = str(after.get("tail") or "") if isinstance(after, dict) else ""
    reason = str(receipt.get("reason") or "")
    if "gate timeout" in tail and reason != "timeout":
        problems.append("a hung gate was recorded as %s, not timeout" % reason)
    if reason == "timeout" and "gate timeout" not in tail:
        problems.append("timeout came from grok before the hanging gate was recorded")
    return problems


def case_network() -> None:
    host_gate()
    wall_gate()
    repo = init_clone("network-down")
    before = snap(repo)
    case_dir = prepare("network-down")
    root_before = root_status()
    shim = str(EVAL / "bin")
    env = base_env({"PATH": shim + os.pathsep + os.environ.get("PATH", "")})
    which = shutil.which("grok", path=env["PATH"])
    if not which or not Path(which).resolve().is_relative_to((EVAL / "bin").resolve()):
        raise SystemExit("refusing network case because PATH did not select the shim")
    task = "In app.py change the line value = 0 to value = 1. Do not edit any other file. Do not commit."
    proc = run_build(
        common_args(repo, case_dir, task, green_cmd(), "60"),
        env=env,
        timeout=120,
    )
    receipt = load_receipt(case_dir)
    extra = []
    if which is None or not which.startswith(shim):
        extra.append("PATH did not select the shim")
    tail = attempt_tail(receipt)
    if "Network is unreachable" not in tail:
        extra.append("network text missing from the attempt tail")
    finish_pfy(
        "network-down",
        "shim",
        repo,
        case_dir,
        before,
        root_before,
        proc,
        "FAIL",
        "no-change",
        1,
        extra,
        "PATH shim prints Network is unreachable and writes nothing",
        expect_pass=False,
    )
    sweep_clone(repo, [])


def case_tmp() -> None:
    host_gate()
    wall_gate()
    repo = init_clone("tmp-unwritable")
    tmp = repo / "tmp"
    tmp.mkdir()
    os.chmod(tmp, 0o555)
    before = snap(repo)
    case_dir = prepare("tmp-unwritable")
    root_before = root_status()
    task = "In app.py change the line value = 0 to value = 1. Do not edit any other file. Do not commit."
    try:
        proc = run_build(
            common_args(repo, case_dir, task, green_cmd(), "30"),
            timeout=90,
        )
    finally:
        os.chmod(tmp, 0o755)
    receipt = load_receipt(case_dir)
    extra = []
    attempts = [] if not receipt else receipt.get("attempts") or []
    if any(isinstance(row, dict) and int(row.get("n") or 0) >= 1 for row in attempts):
        extra.append("grok ran even though tmp was not writable")
    finish_pfy(
        "tmp-unwritable",
        "real",
        repo,
        case_dir,
        before,
        root_before,
        proc,
        "FAIL",
        "worktree-failed",
        1,
        extra,
        "repo tmp is mode 555",
        expect_pass=False,
    )
    sweep_clone(repo, [])


def case_unicode() -> None:
    host_gate()
    wall_gate()
    real_grok()
    repo = init_clone("non-ascii", {"my app.py": "value = 0\n"})
    before = snap(repo)
    case_dir = prepare("non-ascii")
    root_before = root_status()
    task = 'In the file "my app.py", set the only line to café = 2. Do not edit any other file. Do not commit.'
    proc = run_build(
        common_args(repo, case_dir, task, value_cmd("my app.py", "café = 2"), "240"),
        timeout=560,
    )
    receipt = load_receipt(case_dir)
    extra = []
    stored = "" if not receipt else str(receipt.get("task") or "")
    if "café" not in stored:
        extra.append("receipt task dropped the non-ASCII text")
    sha = "" if not receipt else str(receipt.get("commit") or "")
    names = commit_names(repo, sha)
    if receipt and receipt.get("status") == "PASS" and "my app.py" not in names:
        extra.append("PASS commit did not include the spaced path")
    finish_pfy(
        "non-ascii",
        "real",
        repo,
        case_dir,
        before,
        root_before,
        proc,
        "PASS",
        "ok",
        0,
        extra,
        "task keeps cafe-acute and the path contains a space",
        expect_pass=True,
    )
    sweep_clone(repo, [])


CASES = {
    "dirty-tree": case_dirty,
    "detached-head": case_detached,
    "two-builds": case_two,
    "over-cap": case_over_cap,
    "no-tests": case_no_tests,
    "gate-hang": case_hang,
    "network-down": case_network,
    "tmp-unwritable": case_tmp,
    "non-ascii": case_unicode,
}


def main() -> int:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    os.environ["TMPDIR"] = str(SCRATCH)
    if len(sys.argv) != 2 or sys.argv[1] not in CASES:
        print("usage: drive.py <%s>" % "|".join(sorted(CASES)))
        return 2
    CASES[sys.argv[1]]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
