#!/usr/bin/env python3
"""Measure repository-harness install and update on a scratch copy of this repo.

The scratch lives under TMPDIR. Nothing is installed into the repo itself.
Filesystem bytes are the measurement. JSON from the tool is recorded beside them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MARKER = "pfy-local-edit-1107"
AUTHORITY = (
    "docs/DESIGN.md",
    "docs/adr/README.md",
    "docs/TODO.md",
    "docs/OPEN_QUESTIONS.md",
    "docs/QUICKSTART-pfy-build.md",
    "docs/PENDING-HANDOFF.md",
)
SEED_FILES = AUTHORITY + ("AGENTS.md",)
MAP_FILES = ("docs/README.md", "docs/WORKFLOW.md")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def copy_seed(repo: Path, dest: Path) -> list[str]:
    copied: list[str] = []
    for rel in SEED_FILES:
        src = repo / rel
        if not src.is_file():
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        copied.append(rel)
    plans = repo / "docs" / "plans"
    if plans.is_dir():
        for src in sorted(plans.rglob("*")):
            if not src.is_file():
                continue
            rel = src.relative_to(repo).as_posix()
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
            copied.append(rel)
    return copied


def snapshot(root: Path, rels: list[str]) -> dict[str, str]:
    return {rel: sha256_file(root / rel) for rel in rels if (root / rel).is_file()}


def tool_env(home: Path) -> dict[str, str]:
    for name in ("xdg-config", "xdg-cache", "tmp"):
        (home / name).mkdir(parents=True, exist_ok=True)
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / "xdg-config"),
        "XDG_CACHE_HOME": str(home / "xdg-cache"),
        "TMPDIR": str(home / "tmp"),
        "LANG": "C.UTF-8",
    }


def run_cmd(argv: list[str], cwd: Path, env: dict[str, str], timeout: float) -> dict:
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "rc": None,
            "seconds": round(time.perf_counter() - started, 3),
            "timeout": True,
            "stdout": (exc.stdout or "")[-800:] if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "")[-800:] if isinstance(exc.stderr, str) else "",
            "json": None,
        }
    parsed = None
    try:
        parsed = json.loads(proc.stdout)
    except json.JSONDecodeError:
        parsed = None
    return {
        "rc": proc.returncode,
        "seconds": round(time.perf_counter() - started, 3),
        "timeout": False,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "json": parsed,
    }


def harness(bin_path: Path, args: list[str], cwd: Path, env: dict[str, str], timeout: float) -> dict:
    return run_cmd([str(bin_path), *args], cwd, env, timeout)


def git_init(root: Path, env: dict[str, str]) -> dict:
    base = ["git", "-c", "user.email=probe@localhost", "-c", "user.name=probe"]
    steps = [
        ["git", "init", "-q"],
        ["git", "add", "."],
        base + ["commit", "-q", "-m", "seed"],
    ]
    last = None
    for argv in steps:
        last = run_cmd(argv, root, env, 30)
        if last["rc"] != 0:
            return last
    return last or {"rc": 0}


def named_in(text: str) -> list[str]:
    return [path for path in AUTHORITY if path in text]


def count_kinds(payload: dict | None) -> dict[str, int]:
    counts = {"adopt": 0, "create": 0, "other": 0}
    if not isinstance(payload, dict):
        return counts
    for change in payload.get("changes") or []:
        if not isinstance(change, dict):
            continue
        kind = str(change.get("kind") or change.get("action") or "").lower()
        if kind in counts:
            counts[kind] += 1
        else:
            counts["other"] += 1
    return counts


def payload_paths(payload: dict | None) -> list[str]:
    if not isinstance(payload, dict):
        return []
    out = []
    for change in payload.get("changes") or []:
        if isinstance(change, dict) and isinstance(change.get("path"), str):
            out.append(change["path"])
    return out


def marker_hits(root: Path) -> dict[str, int]:
    hits = {}
    for rel in ("AGENTS.md",) + MAP_FILES:
        path = root / rel
        if path.is_file():
            hits[rel] = path.read_text(encoding="utf-8", errors="replace").count(MARKER)
    return hits


def plant_markers(root: Path) -> list[str]:
    planted = []
    for rel in ("AGENTS.md", "docs/WORKFLOW.md"):
        path = root / rel
        if not path.is_file():
            continue
        with path.open("a", encoding="utf-8") as handle:
            handle.write("\n" + MARKER + "\n")
        planted.append(rel)
    return planted


def project_process(repo: Path, scratch: Path, env: dict[str, str]) -> dict:
    init = repo / "bootstrap" / "project-process" / "init.sh"
    if not init.is_file():
        return {"ran": False, "reason": "init.sh missing"}
    started = time.perf_counter()
    proc = run_cmd(
        [str(init), str(scratch), "--dry-run", "--name", "probe"],
        scratch,
        env,
        60,
    )
    text = (proc["stdout"] or "") + "\n" + (proc["stderr"] or "")
    skip = 0
    write = 0
    for line in text.splitlines():
        if "skip (exists):" in line:
            skip += 1
        elif line.startswith("dry-run: write "):
            write += 1
    templates = repo / "bootstrap" / "project-process" / "templates"
    present = 0
    total = 0
    if templates.is_dir():
        for src in templates.rglob("*"):
            if not src.is_file() or src.name == ".gitkeep":
                continue
            total += 1
            rel = src.relative_to(templates).as_posix()
            if (repo / rel).is_file():
                present += 1
    return {
        "ran": True,
        "rc": proc["rc"],
        "seconds": round(time.perf_counter() - started, 3),
        "dry_run_skip": skip,
        "dry_run_write": write,
        "template_files": total,
        "template_files_already_in_repo": present,
    }


def measure(repo: Path, bin_path: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="pfy-repository-harness-") as tmp:
        root = Path(tmp)
        home = root / "home"
        env = tool_env(home)
        empty = root / "empty"
        empty.mkdir()
        git_init(empty, env)
        dry = harness(bin_path, ["install", "--directory", str(empty), "--dry-run", "--json"], empty, env, 60)
        paths = payload_paths(dry["json"])
        already = [rel for rel in paths if (repo / rel).is_file()]
        parent_nonempty = []
        for rel in paths:
            if (repo / rel).exists():
                continue
            parent = repo / Path(rel).parent
            if parent.is_dir() and any(parent.iterdir()):
                parent_nonempty.append(rel)

        scratch = root / "scratch"
        scratch.mkdir()
        seeded = copy_seed(repo, scratch)
        before = snapshot(scratch, seeded)
        process = project_process(repo, scratch, env)
        git_init(scratch, env)
        install = harness(bin_path, ["install", "--directory", str(scratch), "--json"], scratch, env, 120)
        after = snapshot(scratch, seeded)
        changed = sorted(rel for rel, digest in before.items() if after.get(rel) != digest)
        plans = [rel for rel in seeded if rel.startswith("docs/plans/")]
        plans_changed = [rel for rel in plans if rel in changed]
        map_text = []
        for rel in MAP_FILES:
            path = scratch / rel
            if path.is_file():
                map_text.append(path.read_text(encoding="utf-8", errors="replace"))
        agents_text = ""
        agents_path = scratch / "AGENTS.md"
        if agents_path.is_file():
            agents_text = agents_path.read_text(encoding="utf-8", errors="replace")
        planted = plant_markers(scratch)
        agents_with_marker = agents_path.read_text(encoding="utf-8", errors="replace") if agents_path.is_file() else ""
        update = harness(bin_path, ["update", "--directory", str(scratch), "--json"], scratch, env, 90)
        if update["rc"] not in (0, 2) or update["timeout"]:
            for _ in range(2):
                if update["rc"] in (0, 2) and not update["timeout"]:
                    break
                update = harness(bin_path, ["update", "--directory", str(scratch), "--json"], scratch, env, 90)
        hits = marker_hits(scratch)
        agents_after = agents_path.read_text(encoding="utf-8", errors="replace") if agents_path.is_file() else ""
        doctor = harness(bin_path, ["doctor", "--directory", str(scratch), "--json"], scratch, env, 60)
        status = harness(bin_path, ["status", "--directory", str(scratch), "--json"], scratch, env, 60)
        install_json = install["json"] if isinstance(install["json"], dict) else {}
        update_json = update["json"] if isinstance(update["json"], dict) else {}
        doctor_json = doctor["json"] if isinstance(doctor["json"], dict) else {}
        status_json = status["json"] if isinstance(status["json"], dict) else {}
        conflicts = update_json.get("conflicts")
        conflict_count = len(conflicts) if isinstance(conflicts, list) else None
        modified = 0
        files = status_json.get("files")
        if isinstance(files, list):
            modified = sum(1 for row in files if isinstance(row, dict) and row.get("modified"))
        return {
            "binary_bytes": bin_path.stat().st_size,
            "binary_sha256": sha256_file(bin_path),
            "seed_files": seeded,
            "dry_run": {
                "rc": dry["rc"],
                "seconds": dry["seconds"],
                "timeout": dry["timeout"],
                "payload_paths": len(paths),
                "payload_files_already_in_repo": already,
                "payload_paths_whose_parent_is_nonempty": parent_nonempty,
                "empty_dir_entries_after_dry_run": sorted(p.name for p in empty.iterdir()),
            },
            "project_process": process,
            "install": {
                "rc": install["rc"],
                "seconds": install["seconds"],
                "timeout": install["timeout"],
                "applied": install_json.get("applied"),
                "version": install_json.get("version"),
                "kinds": count_kinds(install_json),
                "agents_sha_same": before.get("AGENTS.md") == after.get("AGENTS.md") and "AGENTS.md" in before,
                "preexisting_changed": changed,
                "plans_total": len(plans),
                "plans_changed": plans_changed,
                "stderr": (install["stderr"] or "")[-400:],
            },
            "authority": {
                "paths": list(AUTHORITY),
                "in_agents": named_in(agents_text),
                "in_new_map": named_in("\n".join(map_text)),
            },
            "update": {
                "rc": update["rc"],
                "seconds": update["seconds"],
                "timeout": update["timeout"],
                "applied": update_json.get("applied"),
                "from_version": update_json.get("from_version"),
                "to_version": update_json.get("to_version"),
                "conflicts": conflict_count,
                "planted": planted,
                "marker_hits": hits,
                "markers_kept": sum(hits.get(rel, 0) for rel in planted),
                "agents_keeps_pre_update_body": agents_after == agents_with_marker,
                "stderr": (update["stderr"] or "")[-400:],
            },
            "doctor": {
                "rc": doctor["rc"],
                "seconds": doctor["seconds"],
                "timeout": doctor["timeout"],
                "healthy": doctor_json.get("healthy"),
                "stderr": (doctor["stderr"] or "")[-400:],
            },
            "status": {
                "rc": status["rc"],
                "seconds": status["seconds"],
                "timeout": status["timeout"],
                "modified": modified,
                "stderr": (status["stderr"] or "")[-400:],
            },
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--harness", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    harness_bin = args.harness.resolve()
    if not repo.is_dir():
        print("repo missing", file=sys.stderr)
        return 2
    if not harness_bin.is_file() or not os.access(harness_bin, os.X_OK):
        print("harness missing", file=sys.stderr)
        return 2
    result = measure(repo, harness_bin)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    authority = result["authority"]
    install = result["install"]
    update = result["update"]
    print(
        "map %s/%s agents %s/%s changed %s markers %s/%s conflicts %s"
        % (
            len(authority["in_new_map"]),
            len(authority["paths"]),
            len(authority["in_agents"]),
            len(authority["paths"]),
            len(install["preexisting_changed"]),
            update["markers_kept"],
            len(update["planted"]),
            update["conflicts"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
