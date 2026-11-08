#!/usr/bin/env python3
"""Offline probe for pinned kander 0.9.5.

Measures path-overlap agreement with git, and whether move-to-done waits
for an independent reviewer. Starts no agent. Writes results.json here.
The product worktree is read-only except that file.
"""

from __future__ import annotations

import hashlib
import json
import os
import pwd
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PIN_VERSION = "0.9.5"
PIN_SHA = "3a5f8979f94fc1325dbcf9aa30e73831d1db907302c13b5273362313c327e254"
PIN_COMMIT = "590f1ced69af6e144bf78f43eee01fa050734b3c"
SCAN_WORDS = ("worktree", "kanban", "review", "reviewer", "parallel", "orchestrat")


def real_home() -> Path:
    explicit = os.environ.get("PFY_REAL_HOME", "").strip()
    if explicit:
        return Path(explicit)
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def cache_root() -> Path:
    return Path(os.environ.get("KANDER_CACHE", str(real_home() / ".cache" / "pfy" / "tools" / "kander")))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def child_env(cache: Path) -> dict[str, str]:
    home = cache / "home"
    tmp = cache / "tmp"
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(cache / "xdg-config"),
        "XDG_CACHE_HOME": str(cache / "xdg-cache"),
        "XDG_DATA_HOME": str(home / ".local" / "share"),
        "XDG_STATE_HOME": str(home / ".local" / "state"),
        "TMPDIR": str(tmp),
        "TMP": str(tmp),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "probe",
        "GIT_AUTHOR_EMAIL": "probe@localhost",
        "GIT_COMMITTER_NAME": "probe",
        "GIT_COMMITTER_EMAIL": "probe@localhost",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }


def run(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout: int = 90,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def run_bytes(
    cmd: list[str],
    cwd: Path,
    env: dict[str, str],
    timeout: int = 90,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def tail(text: str, limit: int = 400) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[-limit:]


def side_paths(repo: Path, base: str, commit: str, env: dict[str, str], rename: bool) -> set[str]:
    cmd = ["git", "diff", "--name-status"]
    if rename:
        cmd.append("-M")
    cmd.extend([base, commit])
    cp = run(cmd, repo, env)
    if cp.returncode != 0:
        raise RuntimeError(tail(cp.stderr) or "git diff failed")
    found: set[str] = set()
    for line in cp.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        if rename and (status.startswith("R") or status.startswith("C")) and len(parts) >= 3:
            found.add(parts[1])
            found.add(parts[2])
        else:
            found.add(parts[-1])
    return found


def merge_base(repo: Path, left: str, right: str, env: dict[str, str]) -> str:
    cp = run(["git", "merge-base", left, right], repo, env)
    if cp.returncode != 0:
        raise RuntimeError(tail(cp.stderr) or "merge-base failed")
    return cp.stdout.strip()


def overlap_pair(
    repo: Path,
    source: str,
    head: str,
    label: str,
    kander: Path,
    env: dict[str, str],
) -> dict:
    base = merge_base(repo, source, head, env)
    t0 = time.perf_counter()
    aware_left = side_paths(repo, base, head, env, True)
    aware_right = side_paths(repo, base, source, env, True)
    naive_left = side_paths(repo, base, head, env, False)
    naive_right = side_paths(repo, base, source, env, False)
    git_s = time.perf_counter() - t0
    aware = sorted(aware_left & aware_right)
    naive = sorted(naive_left & naive_right)
    t1 = time.perf_counter()
    cp = run(
        [str(kander), "--lang", "en", "check", "overlap", "--source", source, "--head", head, "--json"],
        repo,
        env,
        timeout=120,
    )
    kander_s = time.perf_counter() - t1
    obj = None
    try:
        obj = json.loads(cp.stdout)
    except json.JSONDecodeError:
        obj = None
    paths = []
    status = None
    if isinstance(obj, dict):
        status = obj.get("status")
        raw_paths = obj.get("paths") or []
        if isinstance(raw_paths, list):
            paths = sorted(path_text(item) for item in raw_paths)
    return {
        "label": label,
        "source": source,
        "head": head,
        "merge_base": base,
        "kander_rc": cp.returncode,
        "kander_status": status,
        "kander_paths": paths,
        "git_rename_aware": aware,
        "git_destination_only": naive,
        "agree_rename_aware": paths == aware and cp.returncode in (0, 1) and status not in (None, "error"),
        "agree_destination_only": paths == naive and cp.returncode in (0, 1) and status not in (None, "error"),
        "kander_s": round(kander_s, 4),
        "git_s": round(git_s, 4),
        "stderr": tail(cp.stderr),
    }


def path_text(item: object) -> str:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        utf8 = item.get("utf8")
        if isinstance(utf8, str) and utf8:
            return utf8
    return str(item)


def replace_section(text: str, name: str, body: str) -> str:
    """Replace one markdown section. An empty section must not swallow the next heading."""
    if not body.endswith("\n"):
        body += "\n"
    parts = re.split(r"(?m)^(## .+)$", text)
    found = False
    out = [parts[0]]
    index = 1
    while index < len(parts):
        heading = parts[index]
        blob = parts[index + 1] if index + 1 < len(parts) else ""
        if heading == f"## {name}":
            found = True
            blob = "\n" + body + "\n"
        out.append(heading)
        out.append(blob)
        index += 2
    if not found:
        raise RuntimeError(f"section {name} missing")
    return "".join(out)


def show(kander: Path, repo: Path, env: dict[str, str], task_id: str) -> dict:
    cp = run([str(kander), "--lang", "en", "show", "--json", task_id], repo, env)
    if cp.returncode != 0:
        raise RuntimeError(tail(cp.stderr) or tail(cp.stdout) or "show failed")
    return json.loads(cp.stdout)


def fill_spec(text: str, goal: str, summary: str) -> str:
    text = replace_section(text, "GOAL", goal + "\n")
    text = replace_section(
        text,
        "EXPECTED_OUTCOME",
        "The card state after the probe commands is the recorded result.\n",
    )
    text = replace_section(
        text,
        "ACCEPTANCE_CRITERIA",
        "- [ ] The recorded exit code matches the gate under test\n",
    )
    text = replace_section(
        text,
        "OUT_OF_SCOPE",
        "- existing issues: leave them\n"
        "- hardening: not this card\n"
        "- shared contracts and docs: not this card\n"
        "- adjacent features: not this card\n",
    )
    text = replace_section(
        text,
        "DISCUSSION",
        "SELF_REVIEW: one criterion, no large-task trigger, no invented user decision.\n",
    )
    text = replace_section(text, "IMPLEMENTATION", "No product code. Offline probe only.\n")
    text = replace_section(text, "SUMMARY", summary + "\n")
    if "<FILL_IN>" in text:
        raise RuntimeError("template placeholder left in spec")
    return text


def publish(kander: Path, repo: Path, env: dict[str, str], task_id: str, text: str, scratch: Path) -> None:
    current = show(kander, repo, env, task_id)
    path = scratch / f"{task_id}.md"
    path.write_text(text, encoding="utf-8")
    cp = run(
        [
            str(kander),
            "--lang",
            "en",
            "update",
            task_id,
            "--document",
            "spec.md",
            "--file",
            str(path),
            "--expect-revision",
            str(current["revision"]),
        ],
        repo,
        env,
    )
    if cp.returncode != 0:
        raise RuntimeError(tail(cp.stderr) or tail(cp.stdout) or "update failed")


def new_card(kander: Path, repo: Path, env: dict[str, str], slug: str, title: str) -> str:
    cp = run([str(kander), "--lang", "en", "new", "chore", slug, title], repo, env)
    if cp.returncode != 0:
        raise RuntimeError(tail(cp.stderr) or tail(cp.stdout) or "new failed")
    match = re.search(r"(\d{8}-" + re.escape(slug) + r"-task)", cp.stdout)
    if not match:
        raise RuntimeError(tail(cp.stdout) or "task id missing")
    return match.group(1)


def move(kander: Path, repo: Path, env: dict[str, str], task_id: str, *args: str) -> dict:
    cp = run([str(kander), "--lang", "en", "move", task_id, *args], repo, env)
    err = tail(cp.stderr)
    # A successful done move prints the report template on stderr. Keep the first line.
    first = err.splitlines()[0] if err else ""
    return {"rc": cp.returncode, "first": first, "stderr": err}


def prepare_working(
    kander: Path,
    repo: Path,
    env: dict[str, str],
    slug: str,
    title: str,
    goal: str,
    summary: str,
    scratch: Path,
) -> str:
    task_id = new_card(kander, repo, env, slug, title)
    current = show(kander, repo, env, task_id)
    publish(kander, repo, env, task_id, fill_spec(current["text"], goal, summary), scratch)
    todo = move(kander, repo, env, task_id, "todo")
    if todo["rc"] != 0:
        raise RuntimeError(f"move todo failed: {todo['first']}")
    working = move(kander, repo, env, task_id, "working", "--owner", "probe")
    if working["rc"] != 0:
        raise RuntimeError(f"move working failed: {working['first']}")
    return task_id


def plan_and_close(
    kander: Path,
    repo: Path,
    env: dict[str, str],
    task_id: str,
    plan_id: str,
    batch_id: str,
    sha: str,
    requirements: dict[str, str],
    scratch: Path,
) -> dict:
    plan = {
        "schema": 1,
        "sealed": True,
        "plan_id": plan_id,
        "author": "probe",
        "basis": "offline probe records whether a reviewer run is required",
        "cwd": str(repo.resolve()),
        "report_language": "en",
        "task_ids": [task_id],
        "batches": [
            {
                "batch_id": batch_id,
                "task_ids": [task_id],
                "base": sha,
                "target_commit": sha,
                "requirements": requirements,
            }
        ],
    }
    plan_path = scratch / f"{plan_id}.json"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    created = run([str(kander), "--lang", "en", "review", "plan", str(repo.resolve()), str(plan_path)], repo, env)
    if created.returncode != 0:
        raise RuntimeError(tail(created.stderr) or tail(created.stdout) or "review plan failed")
    agg = run_bytes(
        [str(kander), "--lang", "en", "review", "aggregate", str(repo.resolve()), batch_id],
        repo,
        env,
    )
    if agg.returncode != 0:
        raise RuntimeError(tail(agg.stderr.decode("utf-8", "replace")) or "aggregate failed")
    view = json.loads(agg.stdout.decode("utf-8"))
    close = {
        "batch_id": batch_id,
        "expected_revision": view["batch"]["revision"],
        "view_hash": hashlib.sha256(agg.stdout).hexdigest(),
        "author": "probe",
        "roles": {},
        "resolved_failures": {},
        "opinions": [],
    }
    close_path = scratch / f"{batch_id}-close.json"
    close_path.write_text(json.dumps(close) + "\n", encoding="utf-8")
    closed = run(
        [str(kander), "--lang", "en", "review", "close", str(repo.resolve()), str(close_path)],
        repo,
        env,
    )
    return {
        "plan_rc": created.returncode,
        "close_rc": closed.returncode,
        "close_first": tail(closed.stderr, 300).splitlines()[0] if closed.stderr.strip() else "",
        "runs_in_view": len(view.get("runs") or []),
    }


def worktree_count(repo: Path, env: dict[str, str]) -> int:
    cp = run(["git", "worktree", "list", "--porcelain"], repo, env)
    return sum(1 for line in cp.stdout.splitlines() if line.startswith("worktree "))


def porcelain(repo: Path, env: dict[str, str]) -> list[str]:
    cp = run(["git", "status", "--porcelain"], repo, env)
    return [line for line in cp.stdout.splitlines() if line.strip()]


def build_fixture(repo: Path, env: dict[str, str]) -> dict[str, str]:
    files = {
        "sources/entries/117-kander.md": ROOT / "sources" / "entries" / "117-kander.md",
        "data/stages/brigade.json": ROOT / "data" / "stages" / "brigade.json",
        "data/stages/festival.json": ROOT / "data" / "stages" / "festival.json",
        "data/stages/kanbots.json": ROOT / "data" / "stages" / "kanbots.json",
    }
    for rel, src in files.items():
        dest = repo / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest)
    run(["git", "init", "-q", "-b", "base"], repo, env)
    run(["git", "add", "."], repo, env)
    base_commit = run(["git", "commit", "-q", "-m", "base"], repo, env)
    if base_commit.returncode != 0:
        raise RuntimeError(tail(base_commit.stderr) or "base commit failed")
    base = run(["git", "rev-parse", "HEAD"], repo, env).stdout.strip()

    def branch(name: str, edits) -> str:
        cp = run(["git", "checkout", "-q", "-b", name, "base"], repo, env)
        if cp.returncode != 0:
            raise RuntimeError(tail(cp.stderr) or f"branch {name} failed")
        edits()
        run(["git", "add", "-A"], repo, env)
        committed = run(["git", "commit", "-q", "-m", name], repo, env)
        if committed.returncode != 0:
            raise RuntimeError(tail(committed.stderr) or f"commit {name} failed")
        sha = run(["git", "rev-parse", "HEAD"], repo, env).stdout.strip()
        run(["git", "checkout", "-q", "base"], repo, env)
        return sha

    entry = repo / "sources" / "entries" / "117-kander.md"

    def touch_entry() -> None:
        entry.write_text(entry.read_text(encoding="utf-8") + "\nprobe line\n", encoding="utf-8")

    def touch_card() -> None:
        card = repo / "data" / "stages" / "festival.json"
        card.write_text(card.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    def touch_both() -> None:
        touch_entry()
        touch_card()

    def rename_entry() -> None:
        renamed = repo / "sources" / "entries" / "117-kander-renamed.md"
        entry.rename(renamed)
        renamed.write_text(renamed.read_text(encoding="utf-8") + "\nrenamed\n", encoding="utf-8")

    refs = {
        "base": base,
        "lane_entry": branch("lane-entry", touch_entry),
        "lane_card": branch("lane-card", touch_card),
        "lane_both": branch("lane-both", touch_both),
        "lane_rename": branch("lane-rename", rename_entry),
    }
    dirty = porcelain(repo, env)
    if dirty:
        raise RuntimeError(f"fixture left dirty: {dirty}")
    return refs


def latest_merge(env: dict[str, str]) -> dict | None:
    cp = run(["git", "rev-list", "--merges", "--max-count", "1", "HEAD"], ROOT, env)
    if cp.returncode != 0 or not cp.stdout.strip():
        return None
    sha = cp.stdout.strip()
    parents = run(["git", "rev-list", "--parents", "-n", "1", sha], ROOT, env).stdout.split()
    subject = run(["git", "log", "-1", "--format=%s", sha], ROOT, env).stdout.strip()
    if len(parents) < 3:
        return None
    return {"sha": sha, "parents": parents[1:], "subject": subject}


def catalog_hits() -> list[dict]:
    hits = []
    stages = ROOT / "data" / "stages"
    for path in sorted(stages.glob("*.json")):
        if path.name == "_registry.json":
            continue
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        blob_parts = [str(card.get("uses") or "")]
        for key in ("features", "tags", "catalog_tags"):
            value = card.get(key) or []
            if isinstance(value, list):
                blob_parts.extend(str(item) for item in value)
        blob = " ".join(blob_parts).lower()
        matched = [word for word in SCAN_WORDS if word in blob]
        if not matched:
            continue
        hits.append(
            {
                "slug": path.stem,
                "name": card.get("name"),
                "integration_stage": card.get("integration_stage"),
                "uses": card.get("uses"),
                "matched": matched,
            }
        )
    return hits


def home_sentinels(home: Path) -> dict[str, bool]:
    return {
        "agents_kander": (home / ".agents" / "kander").exists(),
        "config_kander": (home / ".config" / "kander").exists(),
    }


def main() -> int:
    cache = cache_root()
    binary = cache / "bin" / "kander"
    home = real_home()
    env = child_env(cache)
    before_home = home_sentinels(home)
    exclude = ROOT / ".git" / "info" / "exclude"
    exclude_before = exclude.read_text(encoding="utf-8") if exclude.is_file() else ""
    product_status_before = porcelain(ROOT, env)
    if not binary.is_file():
        print(f"missing {binary}")
        return 2
    digest = sha256_file(binary)
    version = run([str(binary), "--lang", "en", "version"], ROOT, env)
    if digest != PIN_SHA or version.returncode != 0 or PIN_VERSION not in version.stdout:
        print(f"pin failed sha={digest} version={version.stdout.strip()!r}")
        return 2

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    scratch = cache / "tmp" / f"probe-{stamp}"
    repo = scratch / "repo"
    repo.mkdir(parents=True)
    refs = build_fixture(repo, env)
    tarball = cache / "kander-linux-amd64.tar.gz"
    config_path = cache / "home" / ".config" / "kander" / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {}

    pairs = [
        overlap_pair(repo, refs["lane_entry"], refs["lane_card"], "disjoint", binary, env),
        overlap_pair(repo, refs["lane_entry"], refs["lane_both"], "entry_overlap", binary, env),
        overlap_pair(repo, refs["lane_card"], refs["lane_both"], "card_overlap", binary, env),
        overlap_pair(repo, refs["lane_entry"], refs["lane_rename"], "rename_overlap", binary, env),
    ]
    merge = latest_merge(env)
    repo_pair = None
    if merge is not None:
        repo_pair = overlap_pair(
            ROOT,
            merge["parents"][0],
            merge["parents"][1],
            "this_repo_merge",
            binary,
            env,
        )
        repo_pair["merge"] = merge["sha"]
        repo_pair["subject"] = merge["subject"]

    init = run([str(binary), "--lang", "en", "init", "."], repo, env)
    if init.returncode != 0:
        raise RuntimeError(tail(init.stderr) or tail(init.stdout) or "init failed")
    trees_before = worktree_count(repo, env)
    head = run(["git", "rev-parse", "HEAD"], repo, env).stdout.strip()

    blocked = []
    block_id = prepare_working(
        binary,
        repo,
        env,
        "block-card",
        "Block card",
        "Count done moves that have no sealed review plan.",
        "Summary is present. No reviewer has run.",
        scratch,
    )
    # The backlog and todo blocks need a card that has not been claimed yet.
    early_id = new_card(binary, repo, env, "early-card", "Early card")
    early = show(binary, repo, env, early_id)
    publish(
        binary,
        repo,
        env,
        early_id,
        fill_spec(early["text"], "Count illegal done moves before working.", "Not complete."),
        scratch,
    )
    for label, args in (
        ("backlog_to_done", ["done", "--result", "completed"]),
    ):
        row = move(binary, repo, env, early_id, *args)
        blocked.append({"label": label, "task": early_id, "blocked": row["rc"] != 0, "rc": row["rc"], "first": row["first"]})
    todo = move(binary, repo, env, early_id, "todo")
    if todo["rc"] != 0:
        raise RuntimeError(todo["first"] or "early todo failed")
    row = move(binary, repo, env, early_id, "done", "--result", "completed")
    blocked.append({"label": "todo_to_done", "task": early_id, "blocked": row["rc"] != 0, "rc": row["rc"], "first": row["first"]})

    # Empty summary: a third card, claimed before the summary is replaced.
    empty_id = new_card(binary, repo, env, "empty-card", "Empty card")
    empty = show(binary, repo, env, empty_id)
    empty_text = fill_spec(empty["text"], "Count a done move with an empty summary.", "placeholder")
    empty_text = replace_section(empty_text, "SUMMARY", "<FILL_IN>\n")
    publish(binary, repo, env, empty_id, empty_text, scratch)
    if move(binary, repo, env, empty_id, "todo")["rc"] != 0:
        raise RuntimeError("empty todo failed")
    if move(binary, repo, env, empty_id, "working", "--owner", "probe")["rc"] != 0:
        raise RuntimeError("empty working failed")
    row = move(binary, repo, env, empty_id, "done", "--result", "completed")
    blocked.append({"label": "empty_summary", "task": empty_id, "blocked": row["rc"] != 0, "rc": row["rc"], "first": row["first"]})

    row = move(binary, repo, env, block_id, "done", "--result", "completed")
    blocked.append({"label": "no_plan", "task": block_id, "blocked": row["rc"] != 0, "rc": row["rc"], "first": row["first"]})

    dirty = porcelain(repo, env)
    if dirty:
        raise RuntimeError(f"board left the worktree dirty: {dirty}")

    required = plan_and_close(
        binary,
        repo,
        env,
        block_id,
        "blockcard-plan-required",
        "blockcard-batch-required",
        head,
        {"PMQA": "required", "Security": "required"},
        scratch,
    )
    row = move(binary, repo, env, block_id, "done", "--result", "completed")
    blocked.append({"label": "required_unclosed", "task": block_id, "blocked": row["rc"] != 0, "rc": row["rc"], "first": row["first"]})

    half_id = prepare_working(
        binary,
        repo,
        env,
        "half-card",
        "Half card",
        "Count a close where only one reviewer role is required.",
        "Summary is present. Security is waived. PMQA is required.",
        scratch,
    )
    half = plan_and_close(
        binary,
        repo,
        env,
        half_id,
        "halfcard-plan",
        "halfcard-batch",
        head,
        {"PMQA": "required", "Security": "N/A: offline probe starts no reviewer agent"},
        scratch,
    )

    waive_id = prepare_working(
        binary,
        repo,
        env,
        "waive-card",
        "Waive card",
        "Count a done move when both reviewer roles are explicit N/A.",
        "Zero reviewer processes. Both roles are explicit N/A.",
        scratch,
    )
    waive = plan_and_close(
        binary,
        repo,
        env,
        waive_id,
        "waivecard-plan-na",
        "waivecard-batch-na",
        head,
        {
            "PMQA": "N/A: offline probe starts no reviewer agent",
            "Security": "N/A: offline probe starts no reviewer agent",
        },
        scratch,
    )
    waive_done = move(binary, repo, env, waive_id, "done", "--result", "completed")
    trees_after = worktree_count(repo, env)
    after_home = home_sentinels(home)
    exclude_after = exclude.read_text(encoding="utf-8") if exclude.is_file() else ""
    product_kanban = (ROOT / "kanban").exists()
    fixture_kanban = (repo / "kanban").is_dir()

    agree = [row for row in pairs if row["agree_rename_aware"]]
    kander_overlap_s = round(sum(row["kander_s"] for row in pairs), 4)
    git_overlap_s = round(sum(row["git_s"] for row in pairs), 4)
    blocked_n = sum(1 for row in blocked if row["blocked"])
    result = {
        "pin": {
            "version": PIN_VERSION,
            "binary_sha256": digest,
            "sha_matches_entry": digest == PIN_SHA,
            "commit": PIN_COMMIT,
            "tarball_sha256": sha256_file(tarball) if tarball.is_file() else None,
            "binary_bytes": binary.stat().st_size,
        },
        "config_agents": {
            "kanban_agent": config.get("kanban_agent"),
            "reviewers": config.get("reviewers"),
        },
        "tmux_on_path_usr_bin": Path("/usr/bin/tmux").exists(),
        "fixture": str(repo),
        "refs": refs,
        "pairs": pairs,
        "pair_agree_rename_aware": f"{len(agree)}/{len(pairs)}",
        "kander_overlap_s": kander_overlap_s,
        "git_overlap_s": git_overlap_s,
        "this_repo_merge": repo_pair,
        "blocked": blocked,
        "blocked_count": f"{blocked_n}/{len(blocked)}",
        "required_both": required,
        "one_role_required": half,
        "both_na": waive,
        "waive_done_rc": waive_done["rc"],
        "waive_reached_done": waive_done["rc"] == 0,
        "reviewer_processes": 0,
        "worktrees_before": trees_before,
        "worktrees_after": trees_after,
        "fixture_kanban": fixture_kanban,
        "product_kanban": product_kanban,
        "product_exclude_unchanged": exclude_before == exclude_after,
        "product_status_before": product_status_before,
        "real_home_sentinels_before": before_home,
        "real_home_sentinels_after": after_home,
        "catalog_hits": catalog_hits(),
        "live_agents": "SKIPPED",
        "live_agents_reason": "offline lane; start, pick, orchestrate, and review-agent were not run",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "pair_agree_rename_aware": result["pair_agree_rename_aware"],
        "kander_overlap_s": kander_overlap_s,
        "git_overlap_s": git_overlap_s,
        "blocked_count": result["blocked_count"],
        "required_close_rc": required["close_rc"],
        "half_close_rc": half["close_rc"],
        "waive_close_rc": waive["close_rc"],
        "waive_done_rc": waive_done["rc"],
        "worktrees_after": trees_after,
        "reviewer_processes": 0,
        "this_repo_agree": None if repo_pair is None else repo_pair["agree_rename_aware"],
        "this_repo_kander_s": None if repo_pair is None else repo_pair["kander_s"],
        "product_kanban": product_kanban,
        "product_exclude_unchanged": result["product_exclude_unchanged"],
        "home_after": after_home,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
