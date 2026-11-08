#!/usr/bin/env python3
"""Offline foremerge probe for the evq lane. No model, no setup, no real git dir.

Writes results.json next to this file. Throwaway repos stay under the cache tmp.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import statistics
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "results.json"
# HOME is redirected into the cache for this lane, so do not use Path.home().
CACHE = Path(os.environ.get("PFY_FOREMERGE_CACHE", "/home/mark/.cache/pfy/tools/foremerge"))
BIN = Path(os.environ.get("FOREMERGE_BIN", CACHE / "unpack" / "foremerge"))
TARBALL = CACHE / "dl" / "foremerge-v0.5.1-x86_64-unknown-linux-gnu.tar.gz"
SHA_FILE = CACHE / "dl" / "foremerge-v0.5.1-x86_64-unknown-linux-gnu.tar.gz.sha256"
EXPECTED_SHA = "9263599abd66a5a97b2222f3010b995f780ead892f26d02a3a2b61d44d5526e3"
TAG_COMMIT = "0fdeb6629379a5f644590bdbcb923f84e215a1c4"
WORK = CACHE / "tmp" / "evq-probe"

# name, group, scope_a, summary_a, scope_b, summary_b
CASES = [
    ("high-symbol", "high",
     "symbol:load_stages=replace", "Replace load_stages with a sqlite reader",
     "symbol:load_stages=extend", "Extend load_stages to accept a missing directory"),
    ("high-file", "high",
     "file:Makefile=replace", "Replace the Makefile with a task runner",
     "file:Makefile=extend", "Extend the Makefile with a probe target"),
    ("high-remove", "high",
     "symbol:write_tool=remove", "Remove write_tool and write cards inline",
     "symbol:write_tool=extend", "Extend write_tool to keep key order"),
    ("both-replace", "high",
     "symbol:pipeline_role_hits=replace", "Replace pipeline_role_hits with an allowlist file",
     "symbol:pipeline_role_hits=replace", "Replace pipeline_role_hits with a tag-only check"),
    ("park-makefile", "park",
     "file:Makefile=modify", "Add a smoke target for catalog check",
     "file:Makefile=modify", "Fix the help text for the stages target"),
    ("park-agents", "park",
     "file:AGENTS.md=modify", "Document the lane touch list",
     "file:AGENTS.md=modify", "Add the design-in-loop standing rule"),
    ("park-ranking", "park",
     "file:docs/eval/TOOLSET-RANKING.md=modify", "Record the 2026-11-07 Strata rank",
     "file:docs/eval/TOOLSET-RANKING.md=modify", "Note that gap B has no closer in entries 137 to 167"),
    ("park-registry", "park",
     "file:data/stages/_registry.json=modify", "Bump the stage policy date",
     "file:data/stages/_registry.json=modify", "Add a coverage key for probes"),
    ("park-pregate", "park",
     "file:scripts/pregate.sh=modify", "Skip doc-only diffs in the fast path",
     "file:scripts/pregate.sh=modify", "Print the selected modules"),
    ("park-symbol", "park",
     "symbol:load_stages=modify", "Fill last_updated from git when the card omits it",
     "symbol:load_stages=modify", "Reject two tools that slug to the same file"),
    ("cards", "clean",
     "file:data/stages/foremerge.json=modify", "Record the foremerge probe",
     "file:data/stages/hiroute.json=modify", "Record the HiRoute route timings"),
    ("scripts", "clean",
     "file:scripts/catalog_check.py=modify", "Fail closed when a stage card will not parse",
     "file:scripts/test_select.py=modify", "Select modules from the changed paths only"),
    ("disjoint-top", "clean",
     "file:Makefile=modify", "Add a smoke target for catalog check",
     "file:README.md=modify", "Point operators at pfy setup"),
    ("disjoint-symbol", "clean",
     "symbol:load_stages=extend", "Extend load_stages to accept a missing directory",
     "symbol:write_tool=extend", "Extend write_tool to keep key order"),
    ("unrelated", "clean",
     "file:pfylib/stage_registry.py=modify", "Fill last_updated from git",
     "file:docs/DESIGN.md=modify", "State the non-goals for the catalog"),
    ("readme-license", "clean",
     "file:README.md=modify", "Point operators at pfy setup",
     "file:LICENSE=modify", "Update the copyright year"),
    ("short-py", "short",
     "file:a.py=modify", "Fix the off-by-one in the counter",
     "file:b.py=modify", "Add a flag for the timeout"),
    ("short-docs", "short",
     "file:docs/a.md=modify", "Write the operator run steps",
     "file:docs/b.md=modify", "List the environment variables"),
    ("omitted-op", "note",
     "file:Makefile", "Add a smoke target for catalog check",
     "file:Makefile=replace", "Replace the Makefile with a task runner"),
    ("kind-mismatch", "note",
     "symbol:Makefile=replace", "Replace the Makefile symbol",
     "file:Makefile=extend", "Extend the Makefile with a probe target"),
]

HOT = [
    "Makefile",
    "AGENTS.md",
    "docs/eval/TOOLSET-RANKING.md",
    "data/stages/_registry.json",
    "scripts/pregate.sh",
    "scripts/test_select.py",
    "run_tests.py",
    "scripts/test_cache.py",
    "TOOLS.md",
    "data/tools.json",
    ".github",
]


def git_env() -> dict:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "probe"
    env["GIT_AUTHOR_EMAIL"] = "probe@localhost"
    env["GIT_COMMITTER_NAME"] = "probe"
    env["GIT_COMMITTER_EMAIL"] = "probe@localhost"
    return env


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=cwd, env=git_env(), capture_output=True, text=True, timeout=timeout, check=False,
    )


def git_common(path: Path) -> str:
    p = run(["git", "-C", str(path), "rev-parse", "--git-common-dir"])
    raw = (p.stdout or "").strip()
    if not raw:
        return ""
    common = Path(raw)
    if not common.is_absolute():
        common = (path / common).resolve()
    return str(common)


def assert_not_repo_git(path: Path) -> None:
    repo_common = git_common(REPO)
    here = git_common(path)
    if not here or here == repo_common:
        raise SystemExit(f"refusing to touch git dir {here}")


def fm(cwd: Path, args: list[str], database: Path | None) -> tuple[float, dict]:
    cmd = [str(BIN), "--json"]
    if database is not None:
        cmd += ["--database", str(database)]
    cmd += ["--cwd", str(cwd), *args]
    t0 = time.perf_counter()
    p = run(cmd, cwd=cwd)
    dt = (time.perf_counter() - t0) * 1000
    try:
        body = json.loads(p.stdout)
    except json.JSONDecodeError:
        body = {"ok": False, "rc": p.returncode, "raw": (p.stdout + p.stderr)[-400:]}
    return dt, body


def brief_conflicts(body: dict) -> list[dict]:
    out = []
    for c in ((body.get("data") or {}).get("conflicts") or []):
        ev = c.get("evidence") or {}
        out.append({
            "severity": c.get("severity"),
            "kind": c.get("kind"),
            "rule": ev.get("rule"),
            "score": c.get("score"),
            "explanation": c.get("explanation"),
            "blocking_policy_field": (body.get("data") or {}).get("blocking"),
        })
    return out


def init_repo(path: Path) -> None:
    path.mkdir(parents=True)
    run(["git", "init", "-q", str(path)])
    run(["git", "-C", str(path), "commit", "-q", "--allow-empty", "-m", "init"])
    assert_not_repo_git(path)


def one_case(name: str, group: str, sa: str, suma: str, sb: str, sumb: str) -> dict:
    d = WORK / "cases" / name
    if d.exists():
        shutil.rmtree(d)
    init_repo(d)
    db = d / "ledger.db"
    fm(d, ["init"], db)
    _, ag = fm(d, ["agent", "register", "--name", "lane-a", "--model", "none", "--no-worktree"], db)
    _, bg = fm(d, ["agent", "register", "--name", "lane-b", "--model", "none", "--no-worktree"], db)
    aid = (ag.get("data") or {}).get("id")
    bid = (bg.get("data") or {}).get("id")
    if not aid or not bid:
        return {"name": name, "group": group, "ok": False, "reason": "no agent id"}
    fm(d, ["intent", "publish", "--agent", aid, "--task", name, "--summary", suma, "--scope", sa], db)
    dt, chk = fm(d, ["conflicts", "check", "--agent", bid, "--intent", sumb, "--scope", sb], db)
    conflicts = brief_conflicts(chk)
    return {
        "name": name,
        "group": group,
        "scope_a": sa,
        "scope_b": sb,
        "ok": bool(chk.get("ok")),
        "blocking": (chk.get("data") or {}).get("blocking"),
        "n": len(conflicts),
        "check_ms": round(dt, 2),
        "conflicts": conflicts,
    }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pin() -> dict:
    tarball_sha = sha256_file(TARBALL) if TARBALL.is_file() else ""
    sidecar = SHA_FILE.read_text(encoding="utf-8").strip() if SHA_FILE.is_file() else ""
    version = run([str(BIN), "--version"]).stdout.strip()
    return {
        "version": version,
        "tag": "v0.5.1",
        "tag_commit": TAG_COMMIT,
        "tarball": TARBALL.name,
        "tarball_bytes": TARBALL.stat().st_size if TARBALL.is_file() else 0,
        "tarball_sha256": tarball_sha,
        "sidecar": sidecar,
        "sha_matches_sidecar": bool(sidecar) and sidecar.split()[0] == tarball_sha == EXPECTED_SHA,
        "binary_bytes": BIN.stat().st_size,
        "binary_sha256": sha256_file(BIN),
    }


def worktree_share() -> dict:
    base = WORK / "wt"
    if base.exists():
        shutil.rmtree(base)
    main = base / "main"
    init_repo(main)
    a = base / "lane-a"
    b = base / "lane-b"
    run(["git", "-C", str(main), "worktree", "add", "-q", str(a)])
    run(["git", "-C", str(main), "worktree", "add", "-q", str(b)])
    assert_not_repo_git(a)
    assert_not_repo_git(b)
    dt_init, init = fm(a, ["init"], None)
    data = init.get("data") or {}
    db = data.get("database") or ""
    runtime = data.get("runtime_dir") or ""
    throwaway = str(base.resolve())
    _, ag = fm(a, ["agent", "register", "--name", "lane-a", "--model", "none", "--no-worktree"], None)
    _, bg = fm(b, ["agent", "register", "--name", "lane-b", "--model", "none", "--no-worktree"], None)
    aid = (ag.get("data") or {}).get("id")
    bid = (bg.get("data") or {}).get("id")
    fm(a, ["intent", "publish", "--agent", aid, "--task", "wt",
           "--summary", "Replace load_stages with a sqlite reader",
           "--scope", "symbol:load_stages=replace"], None)
    dt, chk = fm(b, ["conflicts", "check", "--agent", bid,
                     "--intent", "Extend load_stages to accept a missing directory",
                     "--scope", "symbol:load_stages=extend"], None)
    conflicts = brief_conflicts(chk)
    return {
        "init_ms": round(dt_init, 2),
        "check_ms": round(dt, 2),
        "ok": bool(chk.get("ok")),
        "blocking": (chk.get("data") or {}).get("blocking"),
        "n": len(conflicts),
        "kinds": [c["kind"] for c in conflicts],
        "severities": [c["severity"] for c in conflicts],
        "shared_across_worktrees": data.get("shared_across_worktrees"),
        "database_under_throwaway": str(db).startswith(throwaway) or str(Path(db).resolve()).startswith(throwaway),
        "runtime_under_throwaway": str(runtime).startswith(throwaway),
        "token_file_exists": bool(data.get("token_file")) and Path(data["token_file"]).is_file(),
        "used_database_override": False,
    }


def edit_and_commit(repo: Path, branch: str, rel: str, mutator) -> None:
    run(["git", "-C", str(repo), "checkout", "-q", "-b", branch])
    path = repo / rel
    text = path.read_text(encoding="utf-8")
    path.write_text(mutator(text), encoding="utf-8")
    run(["git", "-C", str(repo), "add", rel])
    run(["git", "-C", str(repo), "commit", "-q", "-m", branch])


def merge_outcome(repo: Path, into: str, other: str) -> dict:
    run(["git", "-C", str(repo), "checkout", "-q", into])
    t0 = time.perf_counter()
    p = run(["git", "-C", str(repo), "merge", "--no-edit", other])
    dt = (time.perf_counter() - t0) * 1000
    text = (repo / "pfylib" / "stage_registry.py").read_text(encoding="utf-8", errors="replace")
    return {
        "merge_ms": round(dt, 2),
        "returncode": p.returncode,
        "conflict_markers": "<<<<<<<" in text,
    }


def prepare_copy(repo: Path) -> None:
    init_repo(repo)
    src = REPO / "pfylib" / "stage_registry.py"
    dest = repo / "pfylib"
    dest.mkdir()
    shutil.copy(src, dest / "stage_registry.py")
    run(["git", "-C", str(repo), "add", "pfylib/stage_registry.py"])
    run(["git", "-C", str(repo), "commit", "-q", "-m", "copy"])


def git_baseline() -> dict:
    src_name = "pfylib/stage_registry.py"

    def change_def(text: str, marker: str) -> str:
        lines = text.splitlines(keepends=True)
        for i, line in enumerate(lines):
            if line.startswith("def load_stages("):
                lines[i] = f"def load_stages(root, lane='{marker}'):\n"
                return "".join(lines)
        raise SystemExit("load_stages not in the copied file")

    def change_tail(text: str) -> str:
        return text + "\n# lane-b tail note\n"

    same = WORK / "git-same-line"
    if same.exists():
        shutil.rmtree(same)
    prepare_copy(same)
    run(["git", "-C", str(same), "branch", "base"])
    edit_and_commit(same, "lane-a", src_name, lambda t: change_def(t, "a"))
    run(["git", "-C", str(same), "checkout", "-q", "base"])
    edit_and_commit(same, "lane-b", src_name, lambda t: change_def(t, "b"))
    same_merge = merge_outcome(same, "lane-a", "lane-b")

    far = WORK / "git-far"
    if far.exists():
        shutil.rmtree(far)
    prepare_copy(far)
    run(["git", "-C", str(far), "branch", "base"])
    edit_and_commit(far, "lane-a", src_name, lambda t: change_def(t, "a"))
    run(["git", "-C", str(far), "checkout", "-q", "base"])
    edit_and_commit(far, "lane-b", src_name, change_tail)
    far_merge = merge_outcome(far, "lane-a", "lane-b")

    # Foremerge on the same real path, distinct summaries, before either edit.
    d = WORK / "git-intent"
    if d.exists():
        shutil.rmtree(d)
    init_repo(d)
    db = d / "ledger.db"
    fm(d, ["init"], db)
    _, ag = fm(d, ["agent", "register", "--name", "lane-a", "--model", "none", "--no-worktree"], db)
    _, bg = fm(d, ["agent", "register", "--name", "lane-b", "--model", "none", "--no-worktree"], db)
    aid = ag["data"]["id"]
    bid = bg["data"]["id"]
    fm(d, ["intent", "publish", "--agent", aid, "--task", "git",
           "--summary", "Fill last_updated from git when the card omits it",
           "--scope", "file:pfylib/stage_registry.py=modify"], db)
    dt, chk = fm(d, ["conflicts", "check", "--agent", bid,
                     "--intent", "Reject two tools that slug to the same file",
                     "--scope", "file:pfylib/stage_registry.py=modify"], db)
    return {
        "file": src_name,
        "same_line": same_merge,
        "different_region": far_merge,
        "foremerge_same_file_modify": {
            "check_ms": round(dt, 2),
            "blocking": (chk.get("data") or {}).get("blocking"),
            "conflicts": brief_conflicts(chk),
        },
    }


def history() -> dict:
    log = run([
        "git", "-C", str(REPO), "log", "origin/main", "-n", "80", "--name-only",
        "--pretty=format:%H%x09%aI%x09%an%x09%s",
    ]).stdout
    commits = []
    cur = None
    for line in log.splitlines():
        if not line.strip():
            continue
        if "\t" in line and len(line.split("\t", 3)[0]) == 40:
            if cur:
                commits.append(cur)
            h, ts, author, sub = line.split("\t", 3)
            cur = {"h": h, "ts": ts, "author": author, "files": []}
        elif cur is not None:
            cur["files"].append(line.strip())
    if cur:
        commits.append(cur)
    adjacent = 0
    same_author = 0
    cross_author = []
    for a, b in zip(commits, commits[1:]):
        shared = sorted(set(a["files"]) & set(b["files"]))
        if shared:
            adjacent += 1
            if a["author"] == b["author"]:
                same_author += 1
            else:
                cross_author.append({
                    "newer": a["h"][:12],
                    "older": b["h"][:12],
                    "files": shared[:8],
                })
    hot_counts = {h: 0 for h in HOT}
    for cm in commits:
        for f in cm["files"]:
            for h in HOT:
                if f == h or f.startswith(h + "/"):
                    hot_counts[h] += 1
    return {
        "commits": len(commits),
        "newest": commits[0]["h"][:12] if commits else "",
        "oldest": commits[-1]["h"][:12] if commits else "",
        "newest_ts": commits[0]["ts"] if commits else "",
        "oldest_ts": commits[-1]["ts"] if commits else "",
        "adjacent_pairs": max(len(commits) - 1, 0),
        "adjacent_pairs_sharing_a_path": adjacent,
        "of_those_same_author": same_author,
        "cross_author_shared_paths": cross_author,
        "hot_file_touches": hot_counts,
    }


def summarize(cases: list[dict]) -> dict:
    def grp(name: str) -> list[dict]:
        return [c for c in cases if c.get("group") == name]

    highs = grp("high")
    parks = grp("park")
    cleans = grp("clean")
    shorts = grp("short")
    times = [c["check_ms"] for c in cases if "check_ms" in c]
    high_ok = sum(1 for c in highs if c.get("blocking") is True and any(
        x.get("severity") == "HIGH" for x in c.get("conflicts") or []))
    park_block = sum(1 for c in parks if c.get("blocking") is True)
    park_medium = sum(1 for c in parks if c.get("blocking") is False and any(
        x.get("kind") == "shared_contract" for x in c.get("conflicts") or []))
    clean_ok = sum(1 for c in cleans if c.get("n") == 0 and c.get("blocking") is False)
    short_medium = sum(1 for c in shorts if c.get("n", 0) > 0 and c.get("blocking") is False)
    return {
        "high_blocking": f"{high_ok}/{len(highs)}",
        "park_blocking": f"{park_block}/{len(parks)}",
        "park_shared_contract_not_blocking": f"{park_medium}/{len(parks)}",
        "clean_quiet": f"{clean_ok}/{len(cleans)}",
        "short_path_advisory": f"{short_medium}/{len(shorts)}",
        "check_ms_min": min(times) if times else None,
        "check_ms_median": round(statistics.median(times), 2) if times else None,
        "check_ms_max": max(times) if times else None,
        "n_cases": len(cases),
    }


def main() -> int:
    if not BIN.is_file():
        raise SystemExit(f"missing binary {BIN}")
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    t0 = time.perf_counter()
    cases = [one_case(*row) for row in CASES]
    wt = worktree_share()
    gitb = git_baseline()
    hist = history()
    body = {
        "pin": pin(),
        "summary": summarize(cases),
        "cases": cases,
        "worktree": wt,
        "git_baseline": gitb,
        "history": hist,
        "elapsed_s": round(time.perf_counter() - t0, 2),
    }
    OUT.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "summary": body["summary"], "elapsed_s": body["elapsed_s"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
