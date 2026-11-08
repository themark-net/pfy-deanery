#!/usr/bin/env python3
"""Offline probe of the pinned open-steps stop hook. No model, no account.

The question is gap B: a ./pfy build lane that hits the 3 hour timeout or a
parked pregate failure. The hook claims to keep the session open until an
os-done-or-not report exists. This probe counts how often a second stop is
still blocked when that report file is absent.

The clean case runs in this worktree and does not edit it. Every other case
uses a throwaway git repo under the cache tmp dir. Reports and hook state
stay under that case's HOME.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CACHE = Path.home() / ".cache/pfy/tools/open-steps"
PACK = CACHE / "src/repo"
HOOKS = PACK / "hooks"
REAL_STATE = Path("/home/mark/.claude/open-steps")
N_COMMITS = 30


def base_env(home: Path) -> dict[str, str]:
    e = os.environ.copy()
    e["HOME"] = str(home)
    e["XDG_CONFIG_HOME"] = str(home / "xdg-config")
    e["XDG_CACHE_HOME"] = str(home / "xdg-cache")
    e["XDG_DATA_HOME"] = str(home / "xdg-data")
    e["TMPDIR"] = str(CACHE / "tmp")
    e["GIT_CONFIG_GLOBAL"] = "/dev/null"
    e["GIT_CONFIG_SYSTEM"] = "/dev/null"
    e["GIT_AUTHOR_NAME"] = "probe"
    e["GIT_AUTHOR_EMAIL"] = "probe@localhost"
    e["GIT_COMMITTER_NAME"] = "probe"
    e["GIT_COMMITTER_EMAIL"] = "probe@localhost"
    for key in ("OPEN_STEPS_DISABLE", "OPEN_STEPS_COOLDOWN", "OPEN_STEPS_MIN_FILES",
                "OPEN_STEPS_NO_SESSION_START", "PFY_ELAPSED_S", "PFY_PREGATE"):
        e.pop(key, None)
    return e


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None,
        payload: str | None = None, timeout: float = 60.0,
        clip: int | None = 800) -> dict:
    t0 = time.perf_counter()
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        input=payload,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    ms = round((time.perf_counter() - t0) * 1000, 1)
    out, err = p.stdout, p.stderr
    if clip is not None:
        out, err = out[-clip:], err[-clip:]
    return {"exit": p.returncode, "stdout": out, "stderr": err, "ms": ms}


def hook(name: str, session: str, cwd: Path, home: Path,
         extra: dict[str, str] | None = None, payload: str | None = None) -> dict:
    env = base_env(home)
    if extra:
        env.update(extra)
    body = payload if payload is not None else json.dumps({"session_id": session, "cwd": str(cwd)})
    got = run(["bash", str(HOOKS / name)], cwd, env, body, timeout=30.0)
    got["asks"] = got["exit"] == 2 and "os-done-or-not" in got["stderr"]
    return got


def git(cwd: Path, args: list[str], home: Path) -> None:
    r = run(["git", *args], cwd, base_env(home))
    if r["exit"] != 0:
        raise RuntimeError(f"git {' '.join(args)} -> {r['exit']} {r['stderr']}")


def new_repo(scratch: Path, name: str) -> tuple[Path, Path]:
    home = scratch / "home" / name
    repo = scratch / "repo" / name
    home.mkdir(parents=True)
    repo.mkdir(parents=True)
    (home / "xdg-config").mkdir()
    (home / "xdg-cache").mkdir()
    (home / "xdg-data").mkdir()
    git(repo, ["init", "-q"], home)
    first = (ROOT / "AGENTS.md").read_text(encoding="utf-8").splitlines()[0]
    (repo / "AGENTS.md").write_text(first + "\n", encoding="utf-8")
    git(repo, ["add", "."], home)
    git(repo, ["commit", "-q", "-m", "init"], home)
    return repo, home


def scope_dir(home: Path, repo: Path) -> Path:
    return home / ".claude/open-steps/reports" / repo.name


def report_md_count(home: Path, repo: Path) -> int:
    d = scope_dir(home, repo)
    if not d.is_dir():
        return 0
    return sum(1 for p in d.rglob("*.md") if p.is_file())


def write_outside_report(home: Path, repo: Path) -> None:
    d = scope_dir(home, repo)
    d.mkdir(parents=True, exist_ok=True)
    (d / "latest.md").write_text(
        "Lead: the lane ended.\n\n"
        "| | |\n|---|---|\n| Fully done? | Yes |\n"
        "| Anything needed from you? | No |\n"
        "| New debt? | No |\n"
        "| Safe to close? | Yes |\n",
        encoding="utf-8",
    )


def edit(repo: Path, name: str = "AGENTS.md") -> None:
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write("changed\n")


def porcelain(cwd: Path) -> str:
    r = run(["git", "status", "--porcelain"], cwd, os.environ.copy())
    if r["exit"] != 0:
        raise RuntimeError(r["stderr"])
    return r["stdout"]


def case_worktree_clean(scratch_note: dict) -> dict:
    before = porcelain(ROOT)
    home = CACHE / "tmp" / "probe-worktree-home"
    if home.exists():
        shutil.rmtree(home)
    home.mkdir(parents=True)
    (home / "xdg-config").mkdir()
    (home / "xdg-cache").mkdir()
    (home / "xdg-data").mkdir()
    start = hook("session-start.sh", "wt-clean", ROOT, home)
    stop = hook("stop-report.sh", "wt-clean", ROOT, home)
    after = porcelain(ROOT)
    scratch_note["worktree_porcelain_same"] = before == after
    return {
        "start_exit": start["exit"],
        "stop_exit": stop["exit"],
        "stop_asks": stop["asks"],
        "stop_ms": stop["ms"],
        "start_ms": start["ms"],
        "report_md": report_md_count(home, ROOT),
        "porcelain_same": before == after,
        "porcelain_lines": len([ln for ln in before.splitlines() if ln.strip()]),
    }


def case_second_stop_no_report(scratch: Path) -> dict:
    repo, home = new_repo(scratch, "second-no-report")
    hook("session-start.sh", "s", repo, home)
    edit(repo)
    first = hook("stop-report.sh", "s", repo, home)
    second = hook("stop-report.sh", "s", repo, home)
    return {
        "first_exit": first["exit"],
        "first_asks": first["asks"],
        "second_exit": second["exit"],
        "second_asks": second["asks"],
        "report_md": report_md_count(home, repo),
        "first_ms": first["ms"],
        "second_ms": second["ms"],
    }


def case_report_ignored(scratch: Path) -> dict:
    repo, home = new_repo(scratch, "report-ignored")
    hook("session-start.sh", "s", repo, home)
    edit(repo)
    write_outside_report(home, repo)
    first = hook("stop-report.sh", "s", repo, home)
    second = hook("stop-report.sh", "s", repo, home)
    return {
        "report_md_before_stop": 1,
        "first_exit": first["exit"],
        "first_asks": first["asks"],
        "second_exit": second["exit"],
        "report_md": report_md_count(home, repo),
    }


def case_in_repo_handoff(scratch: Path) -> dict:
    repo, home = new_repo(scratch, "in-repo-handoff")
    hook("session-start.sh", "s", repo, home)
    edit(repo, "docs/HANDOFF.md")
    first = hook("stop-report.sh", "s", repo, home)
    second = hook("stop-report.sh", "s", repo, home)
    return {
        "first_exit": first["exit"],
        "first_asks": first["asks"],
        "second_exit": second["exit"],
        "outside_report_md": report_md_count(home, repo),
        "handoff_in_repo": (repo / "docs/HANDOFF.md").is_file(),
    }


def case_commit(scratch: Path) -> dict:
    repo, home = new_repo(scratch, "commit-lands")
    hook("session-start.sh", "s", repo, home)
    edit(repo)
    git(repo, ["add", "."], home)
    git(repo, ["commit", "-q", "-m", "land"], home)
    first = hook("stop-report.sh", "s", repo, home)
    second = hook("stop-report.sh", "s", repo, home)
    clean = porcelain(repo).strip()
    return {
        "worktree_clean_after_commit": clean == "",
        "first_exit": first["exit"],
        "first_asks": first["asks"],
        "second_exit": second["exit"],
        "report_md": report_md_count(home, repo),
    }


def case_big_picture(scratch: Path) -> dict:
    repo, home = new_repo(scratch, "big-picture")
    hook("session-start.sh", "s", repo, home)
    edit(repo, "BIG-PICTURE.md")
    stop = hook("stop-report.sh", "s", repo, home)
    return {"stop_exit": stop["exit"], "stop_asks": stop["asks"]}


def case_cooldown(scratch: Path) -> dict:
    repo, home = new_repo(scratch, "cooldown")
    hook("session-start.sh", "s", repo, home)
    edit(repo, "one.txt")
    first = hook("stop-report.sh", "s", repo, home)
    edit(repo, "two.txt")
    second = hook("stop-report.sh", "s", repo, home)
    return {
        "first_exit": first["exit"],
        "first_asks": first["asks"],
        "second_exit_with_more_work": second["exit"],
        "second_asks": second["asks"],
        "report_md": report_md_count(home, repo),
    }


def case_disable(scratch: Path) -> dict:
    repo, home = new_repo(scratch, "disable")
    hook("session-start.sh", "s", repo, home)
    edit(repo)
    stop = hook("stop-report.sh", "s", repo, home, extra={"OPEN_STEPS_DISABLE": "1"})
    return {"stop_exit": stop["exit"], "stop_asks": stop["asks"]}


def case_min_files(scratch: Path) -> dict:
    repo, home = new_repo(scratch, "min-files")
    hook("session-start.sh", "s", repo, home)
    edit(repo, "only-one.txt")
    small = hook("stop-report.sh", "s", repo, home, extra={"OPEN_STEPS_MIN_FILES": "5"})
    for i in range(4):
        edit(repo, f"more-{i}.txt")
    large = hook("stop-report.sh", "s", repo, home, extra={"OPEN_STEPS_MIN_FILES": "5"})
    return {
        "one_file_exit": small["exit"],
        "five_files_exit": large["exit"],
        "five_files_asks": large["asks"],
    }


def case_gap_b_env(scratch: Path) -> dict:
    repo, home = new_repo(scratch, "gap-b-env")
    extra = {"PFY_ELAPSED_S": "10800", "PFY_PREGATE": "FAIL"}
    hook("session-start.sh", "s", repo, home)
    clean = hook("stop-report.sh", "s", repo, home, extra=extra)
    edit(repo)
    dirty = hook("stop-report.sh", "s", repo, home, extra=extra)
    return {
        "clean_exit": clean["exit"],
        "dirty_exit": dirty["exit"],
        "dirty_asks": dirty["asks"],
        "env_pfy_elapsed_s": "10800",
        "env_pfy_pregate": "FAIL",
    }


def case_cursor(scratch: Path) -> dict:
    repo, home = new_repo(scratch, "cursor-host")
    hook("session-start.sh", "s", repo, home)
    edit(repo)
    payload = json.dumps({
        "conversation_id": "s",
        "status": "completed",
        "cwd": str(repo),
    })
    env_extra = {"CURSOR_PROJECT_DIR": str(repo)}
    first = hook_adapter("cursor", "stop", repo, home, payload, env_extra)
    second = hook_adapter("cursor", "stop", repo, home, payload, env_extra)
    return {
        "first_exit": first["exit"],
        "first_has_followup": "followup_message" in first["stdout"],
        "second_exit": second["exit"],
        "second_stdout": second["stdout"].strip(),
        "report_md": report_md_count(home, repo),
    }


def case_gemini_retry(scratch: Path) -> dict:
    repo, home = new_repo(scratch, "gemini-host")
    hook("session-start.sh", "s", repo, home)
    edit(repo)
    payload = json.dumps({"session_id": "s", "cwd": str(repo)})
    extra = {"GEMINI_PROJECT_DIR": str(repo)}
    first = hook_adapter("gemini", "stop", repo, home, payload, extra)
    retry_payload = json.dumps({
        "session_id": "s",
        "cwd": str(repo),
        "stop_hook_active": True,
    })
    retry = hook_adapter("gemini", "stop", repo, home, retry_payload, extra)
    denied = '"decision":"deny"' in first["stdout"].replace(" ", "")
    return {
        "first_exit": first["exit"],
        "first_denies": denied,
        "retry_exit": retry["exit"],
        "retry_stdout": retry["stdout"].strip(),
        "report_md": report_md_count(home, repo),
    }


def case_two_sessions(scratch: Path) -> dict:
    # Lane B stops after the edit and before lane A does. A new session id
    # stores the dirty tree as its baseline and exits 0, so the edit never
    # produces an ask.
    repo, home = new_repo(scratch, "two-sessions")
    hook("session-start.sh", "lane-a", repo, home)
    edit(repo)
    other = hook("stop-report.sh", "lane-b", repo, home)
    again = hook("stop-report.sh", "lane-a", repo, home)
    return {
        "lane_b_exit": other["exit"],
        "lane_b_asks": other["asks"],
        "lane_a_after_b_exit": again["exit"],
        "lane_a_after_b_asks": again["asks"],
        "report_md": report_md_count(home, repo),
    }


def case_grok_host(scratch: Path) -> dict:
    repo, home = new_repo(scratch, "grok-host")
    got = hook_adapter("grok", "stop", repo, home, "{}", {})
    return {"exit": got["exit"], "stderr_has_usage": "usage:" in got["stderr"]}


def hook_adapter(tool: str, event: str, cwd: Path, home: Path, payload: str,
                 extra: dict[str, str]) -> dict:
    env = base_env(home)
    env.update(extra)
    return run(["bash", str(HOOKS / "adapter.sh"), tool, event], cwd, env, payload, timeout=30.0)


def recent_commits() -> dict:
    listing = run(
        ["git", "rev-list", f"-n{N_COMMITS}", "HEAD"],
        ROOT,
        os.environ.copy(),
        clip=None,
    )
    if listing["exit"] != 0:
        raise RuntimeError(listing["stderr"])
    shas = [ln.strip() for ln in listing["stdout"].splitlines() if ln.strip()]
    docs = 0
    handoff = 0
    nonempty = 0
    for sha in shas:
        names = run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", sha],
            ROOT,
            os.environ.copy(),
            clip=None,
        )
        paths = [ln for ln in names["stdout"].splitlines() if ln.strip()]
        if paths:
            nonempty += 1
        if any(p.startswith("docs/") for p in paths):
            docs += 1
        if any("HANDOFF" in p for p in paths):
            handoff += 1
    return {
        "n": len(shas),
        "newest": shas[0] if shas else "",
        "oldest": shas[-1] if shas else "",
        "nonempty_trees": nonempty,
        "touch_docs": docs,
        "touch_handoff_name": handoff,
    }


def upstream_suite() -> dict:
    env = base_env(CACHE / "home")
    env["TMPDIR"] = str(CACHE / "tmp")
    got = run(["bash", str(HOOKS / "test.sh")], PACK, env, timeout=120.0)
    passed = failed = None
    for line in got["stdout"].splitlines():
        if line.startswith("passed "):
            # passed N, failed M
            parts = line.replace(",", "").split()
            passed = int(parts[1])
            failed = int(parts[3])
    return {"exit": got["exit"], "passed": passed, "failed": failed, "ms": got["ms"]}


def tree_bytes() -> int:
    total = 0
    for p in PACK.rglob("*"):
        if ".git" in p.parts:
            continue
        if p.is_file():
            total += p.stat().st_size
    return total


def skill_merge_allowed() -> bool:
    text = (PACK / "skills/os-check-work/SKILL.md").read_text(encoding="utf-8")
    return "Bash(gh pr merge *)" in text


def main() -> int:
    if not (HOOKS / "stop-report.sh").is_file():
        print(json.dumps({"error": "stop-report.sh missing", "pack": str(PACK)}))
        return 2
    before_real = REAL_STATE.exists()
    scratch = CACHE / "tmp" / "probe"
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    note: dict = {}
    t0 = time.perf_counter()
    work_cases = {
        "second_stop_no_report": case_second_stop_no_report(scratch),
        "outside_report_ignored_on_first_stop": case_report_ignored(scratch),
        "in_repo_handoff": case_in_repo_handoff(scratch),
        "commit_then_second_stop": case_commit(scratch),
    }
    blocked_second = 0
    for item in work_cases.values():
        if item.get("second_exit") == 2:
            blocked_second += 1
    results = {
        "pack": str(PACK),
        "pin": run(["git", "-C", str(PACK), "rev-parse", "HEAD"], PACK, os.environ.copy())["stdout"].strip(),
        "worktree_clean_session": case_worktree_clean(note),
        "work_landed": work_cases,
        "second_stop_still_blocked": blocked_second,
        "work_landed_cases": len(work_cases),
        "big_picture_only": case_big_picture(scratch),
        "cooldown_more_work": case_cooldown(scratch),
        "disable": case_disable(scratch),
        "min_files": case_min_files(scratch),
        "gap_b_env": case_gap_b_env(scratch),
        "cursor": case_cursor(scratch),
        "gemini_retry": case_gemini_retry(scratch),
        "grok_adapter": case_grok_host(scratch),
        "two_sessions": case_two_sessions(scratch),
        "recent_commits": recent_commits(),
        "upstream_suite": upstream_suite(),
        "tree_bytes_excluding_git": tree_bytes(),
        "os_check_work_allows_gh_pr_merge": skill_merge_allowed(),
        "real_home_state_dir_existed_before": before_real,
        "real_home_state_dir_exists_after": REAL_STATE.exists(),
        "worktree_porcelain_same": note["worktree_porcelain_same"],
        "wall_ms": round((time.perf_counter() - t0) * 1000, 1),
    }
    text = json.dumps(results, indent=2) + "\n"
    (OUT / "results.json").write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
