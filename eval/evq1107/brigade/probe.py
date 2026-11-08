#!/usr/bin/env python3
"""Concurrent claim probe for pinned brigade-cli.

Reads stage slugs from this repo. The ledger repo is a throwaway git dir
under the cache tmp, never this worktree. No network. No model.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
WORKERS = 8
CLAIM_TIMEOUT_S = 90
NAIVE_WINDOW_S = float(os.environ.get("BRIGADE_NAIVE_WINDOW_S", "5"))
NAIVE_SLEEP_S = 0.05


def last_json(text: str) -> dict | None:
    for chunk in (text, text[text.find("{") :] if "{" in text else ""):
        try:
            obj = json.loads(chunk)
        except ValueError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def stage_slugs() -> list[str]:
    stages = ROOT / "data" / "stages"
    return sorted(p.stem for p in stages.glob("*.json") if p.stem != "_registry")


def child_env(cache_home: Path, cache_tmp: Path) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", "/usr/bin"),
        "HOME": str(cache_home),
        "XDG_CONFIG_HOME": str(cache_home / ".config"),
        "XDG_CACHE_HOME": str(cache_home / ".cache"),
        "XDG_DATA_HOME": str(cache_home / ".local" / "share"),
        "XDG_STATE_HOME": str(cache_home / ".local" / "state"),
        "TMPDIR": str(cache_tmp),
        "TMP": str(cache_tmp),
        "BRIGADE_NO_UPDATE_CHECK": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "probe",
        "GIT_AUTHOR_EMAIL": "probe@localhost",
        "GIT_COMMITTER_NAME": "probe",
        "GIT_COMMITTER_EMAIL": "probe@localhost",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }


def run(cmd: list[str], cwd: Path, env: dict[str, str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def dir_listing(path: Path) -> list[str]:
    if not path.exists():
        return []
    found = []
    for root, dirs, files in os.walk(path, followlinks=False):
        dirs.sort()
        for name in sorted(files):
            found.append(str(Path(root) / name))
    return found


def dup_stats(ids: list[str]) -> dict[str, int]:
    counts = Counter(ids)
    dup_ids = sorted(item for item, count in counts.items() if count > 1)
    return {
        "claim_rows": len(ids),
        "unique": len(counts),
        "duplicate_ids": len(dup_ids),
        "extra_claims": sum(count - 1 for count in counts.values() if count > 1),
    }


def wait_start(start_file: str) -> None:
    deadline = time.monotonic() + 30
    while not os.path.exists(start_file):
        if time.monotonic() > deadline:
            raise TimeoutError("start file never appeared: %s" % start_file)
        time.sleep(0.01)


def brigade_worker(actor: str, bin_path: str, repo: str, env: dict[str, str], start_file: str, out_file: str) -> None:
    wait_start(start_file)
    rows = []
    while True:
        try:
            proc = run(
                [bin_path, "work", "claim", "--target", repo, "--actor", actor, "--next", "--json"],
                Path(repo),
                env,
                CLAIM_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired as exc:
            rows.append({"rc": None, "reason": "timeout", "stderr": str(exc)[-240:]})
            break
        obj = last_json(proc.stdout or "")
        row = {
            "rc": proc.returncode,
            "task_id": None if obj is None else obj.get("task_id"),
            "status": None if obj is None else obj.get("status"),
            "assignee": None if obj is None else obj.get("assignee"),
            "reason": None if obj is None else obj.get("reason"),
        }
        if proc.returncode != 0 or not row["task_id"]:
            err = (proc.stderr or "").strip()
            if err:
                row["stderr"] = err[-240:]
        rows.append(row)
        if row["reason"] == "no_ready":
            break
        if proc.returncode != 0 or not row["task_id"]:
            break
    Path(out_file).write_text(json.dumps(rows), encoding="utf-8")


def marker_worker(actor: str, slugs: list[str], marker_dir: str, start_file: str, out_file: str) -> None:
    wait_start(start_file)
    won = []
    for slug in slugs:
        path = os.path.join(marker_dir, slug)
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            continue
        os.write(fd, actor.encode("ascii"))
        os.close(fd)
        won.append(slug)
    Path(out_file).write_text(json.dumps(won), encoding="utf-8")


def naive_worker(actor: str, path: str, start_file: str, out_file: str) -> None:
    wait_start(start_file)
    won = []
    deadline = time.monotonic() + NAIVE_WINDOW_S
    while time.monotonic() < deadline:
        try:
            items = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not items:
            break
        pick = items.pop(0)
        time.sleep(NAIVE_SLEEP_S)
        tmp = path + "." + actor
        Path(tmp).write_text(json.dumps(items), encoding="utf-8")
        os.replace(tmp, path)
        won.append(pick)
    Path(out_file).write_text(json.dumps(won), encoding="utf-8")


def launch(fn, arg_sets: list[tuple], start: Path) -> float:
    import multiprocessing as mp

    ctx = mp.get_context("fork")
    procs = [ctx.Process(target=fn, args=args) for args in arg_sets]
    for proc in procs:
        proc.start()
    time.sleep(0.2)
    started = time.perf_counter()
    start.write_text("go\n", encoding="utf-8")
    for proc in procs:
        proc.join()
    elapsed = time.perf_counter() - started
    failed = [proc.exitcode for proc in procs if proc.exitcode != 0]
    if failed:
        raise RuntimeError("worker exit codes: %s" % failed)
    return elapsed


def exclusive_markers(slugs: list[str], work: Path) -> dict:
    marker_dir = work / "markers"
    marker_dir.mkdir()
    start = work / "marker-start"
    outs = []
    arg_sets = []
    for index in range(WORKERS):
        out = work / ("marker-%d.json" % index)
        outs.append(out)
        arg_sets.append(("m%d" % index, slugs, str(marker_dir), str(start), str(out)))
    elapsed = launch(marker_worker, arg_sets, start)
    won = []
    for out in outs:
        won.extend(json.loads(out.read_text(encoding="utf-8")))
    stats = dup_stats(won)
    stats["wall_s"] = round(elapsed, 4)
    stats["left"] = len(slugs) - stats["unique"]
    return stats


def naive_json(slugs: list[str], work: Path) -> dict:
    path = work / "naive.json"
    path.write_text(json.dumps(list(slugs)), encoding="utf-8")
    start = work / "naive-start"
    outs = []
    arg_sets = []
    for index in range(WORKERS):
        out = work / ("naive-%d.json" % index)
        outs.append(out)
        arg_sets.append(("n%d" % index, str(path), str(start), str(out)))
    elapsed = launch(naive_worker, arg_sets, start)
    won = []
    for out in outs:
        won.extend(json.loads(out.read_text(encoding="utf-8")))
    stats = dup_stats(won)
    try:
        left = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        left = None
    stats["wall_s"] = round(elapsed, 4)
    stats["left_in_file"] = None if left is None else len(left)
    stats["window_s"] = NAIVE_WINDOW_S
    stats["sleep_s"] = NAIVE_SLEEP_S
    return stats


def watched_paths(real_home: Path) -> list[Path]:
    return [
        real_home / ".brigade",
        real_home / ".config" / "brigade",
        real_home / ".cache" / "brigade",
        real_home / ".local" / "share" / "brigade",
        real_home / ".local" / "state" / "brigade",
    ]


def main() -> int:
    cache = Path(os.environ["BRIGADE_CACHE"])
    real_home = Path(os.environ["PFY_REAL_HOME"])
    bin_path = os.environ["BRIGADE_BIN"]
    cache_home = cache / "home"
    cache_tmp = cache / "tmp"
    cache_home.mkdir(parents=True, exist_ok=True)
    cache_tmp.mkdir(parents=True, exist_ok=True)
    env = child_env(cache_home, cache_tmp)
    slugs = stage_slugs()
    wheel = cache / "wheels" / "brigade_cli-0.27.0-py3-none-any.whl"
    before_home = {str(path): dir_listing(path) for path in watched_paths(real_home)}
    product_brigade = ROOT / ".brigade"
    product_before = product_brigade.exists()

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    work = cache_tmp / ("probe-%s" % stamp)
    repo = work / "repo"
    repo.mkdir(parents=True)
    version = run([bin_path, "--version"], repo, env, 60)
    git_init = run(["git", "init", "-q", "-b", "main"], repo, env, 60)
    git_empty = run(["git", "commit", "-q", "--allow-empty", "-m", "init"], repo, env, 60)
    init = run(
        [bin_path, "init", "--target", str(repo), "--depth", "repo", "--harnesses", "none", "--no-wire"],
        repo,
        env,
        120,
    )
    add_errors = []
    add_started = time.perf_counter()
    for slug in slugs:
        proc = None
        for _attempt in range(3):
            proc = run(
                [
                    bin_path,
                    "work",
                    "task",
                    "add",
                    "--target",
                    str(repo),
                    "--acceptance",
                    "one exclusive claim",
                    slug,
                ],
                repo,
                env,
                60,
            )
            if proc.returncode == 0:
                break
        else:
            add_errors.append({"slug": slug, "rc": None if proc is None else proc.returncode, "stderr": "" if proc is None else (proc.stderr or "")[-240:]})
            break
    add_wall = time.perf_counter() - add_started
    ready = run([bin_path, "work", "ready", "--target", str(repo), "--json"], repo, env, 60)
    ready_obj = last_json(ready.stdout or "")

    claim = {}
    if not add_errors and ready_obj and ready_obj.get("ready_count") == len(slugs):
        start = work / "claim-start"
        outs = []
        arg_sets = []
        for index in range(WORKERS):
            out = work / ("claim-%d.json" % index)
            outs.append(out)
            arg_sets.append(("c%d" % index, bin_path, str(repo), env, str(start), str(out)))
        elapsed = launch(brigade_worker, arg_sets, start)
        rows = []
        for out in outs:
            rows.extend(json.loads(out.read_text(encoding="utf-8")))
        won = [row["task_id"] for row in rows if row.get("task_id") and row.get("reason") != "no_ready" and row.get("rc") == 0]
        bad = [row for row in rows if row.get("reason") != "no_ready" and not (row.get("rc") == 0 and row.get("task_id"))]
        stats = dup_stats(won)
        ledger_path = repo / ".brigade" / "work" / "tasks.json"
        if not ledger_path.is_file():
            stats["ledger_missing"] = True
            by_status = {}
            assignees = {}
        else:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            tasks = ledger.get("tasks") if isinstance(ledger, dict) else ledger
            if isinstance(tasks, dict):
                task_rows = list(tasks.values())
            elif isinstance(tasks, list):
                task_rows = tasks
            else:
                task_rows = []
            by_status = dict(Counter(str(item.get("status")) for item in task_rows if isinstance(item, dict)))
            assignees = {
                key: value
                for key, value in Counter(
                    str(item.get("assignee") or item.get("actor") or "")
                    for item in task_rows
                    if isinstance(item, dict) and item.get("status") == "in_progress"
                ).items()
                if key
            }
        stats["wall_s"] = round(elapsed, 4)
        stats["ready_before"] = ready_obj.get("ready_count")
        stats["error_rows"] = len(bad)
        stats["no_ready_rows"] = sum(1 for row in rows if row.get("reason") == "no_ready")
        stats["ledger_by_status"] = by_status
        stats["assignees"] = assignees
        if bad:
            stats["error_sample"] = bad[:3]
        claim = stats
    else:
        claim = {"skipped": True, "add_errors": add_errors, "ready": ready_obj, "ready_rc": ready.returncode}

    summary = {
        "pin": {
            "version": (version.stdout or "").strip(),
            "version_rc": version.returncode,
            "wheel_sha256": sha256_file(wheel) if wheel.is_file() else None,
        },
        "tasks": len(slugs),
        "workers": WORKERS,
        "git_init_rc": git_init.returncode,
        "git_empty_rc": git_empty.returncode,
        "init_rc": init.returncode,
        "add_wall_s": round(add_wall, 4),
        "add_errors": len(add_errors),
        "brigade": claim,
        "markers": exclusive_markers(slugs, work),
        "naive": naive_json(slugs, work),
        "product_brigade_before": product_before,
        "product_brigade_after": product_brigade.exists(),
        "real_home_before": {key: len(value) for key, value in before_home.items()},
        "real_home_after": {str(path): len(dir_listing(path)) for path in watched_paths(real_home)},
        "update_notify_in_cache_home": any("update-notify" in name for name in dir_listing(cache_home)),
        "throwaway": str(repo),
    }
    if init.returncode != 0:
        summary["init_stderr"] = (init.stderr or "")[-400:]
    out_path = Path(os.environ["BRIGADE_SUMMARY"]) if os.environ.get("BRIGADE_SUMMARY") else OUT / "summary.json"
    out_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("tasks", "workers", "brigade", "markers", "naive", "add_wall_s", "init_rc")}, indent=2))
    return 0 if init.returncode == 0 and not add_errors and not claim.get("skipped") else 1


if __name__ == "__main__":
    raise SystemExit(main())
