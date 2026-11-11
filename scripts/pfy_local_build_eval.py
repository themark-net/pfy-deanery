#!/usr/bin/env python3
"""Offline coding eval for ./pfy build --local.

Copies each fixture into a fresh git repo under <repo>/tmp/, runs the local
build, then runs that task's check_cmd in the produced worktree. A task PASS
needs a PASS receipt and a zero check_cmd. Exit 0 when every scored task
passed, or when the run is a named skip. Exit 1 when pass is below
passed+failed+blocked, or when the runner itself broke. Exit 2 when
--require-live turns a skip into a hard stop.

PFY_LOCAL_BUILD_UNSAFE_NO_SANDBOX=1 forwards --unsafe-no-sandbox. That is the
same opt-in as the build flag. Without it, a missing bwrap is BLOCKED.

The only network is the configured loopback endpoint. A BLOCKED task stops
the run. Later tasks are not-run. They are not failures and not passes.

Scratch is this script's repo tmp/, or the tmp/ of an explicit --repo that
sits in that same tree. It is not the process cwd and not the git common
dir. On a linked worktree that common dir's parent is the main checkout,
and its tmp/pgs belongs to pregate.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib.bot_interface import _which_opencode  # noqa: E402

# Below this, do not start a task (a tiny host, or a full box). The build's
# own 32 GiB floor still reports BLOCKED when the process can start but a
# model must not load. 10 GiB is enough to enter task 1 and hit that floor.
EVAL_START_FLOOR_GB = 8.0
DEFAULT_ENDPOINT = "http://127.0.0.1:11434/v1"


def _load_build():
    path = ROOT / "scripts" / "pfy_build_local.py"
    spec = importlib.util.spec_from_file_location("pfy_build_local_for_eval", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load pfy_build_local")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BUILD = _load_build()


def _now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _tasks(only: str | None, limit: int | None) -> list[dict]:
    path = ROOT / "eval" / "local-build" / "tasks.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = list(data.get("tasks") or [])
    if only:
        rows = [row for row in rows if row.get("id") == only]
        if not rows:
            raise SystemExit("unknown task id: %s" % only)
    if limit is not None:
        rows = rows[:limit]
    return rows


def _under(parent: Path, child: Path) -> bool:
    try:
        parent_r = parent.resolve()
        child_r = child.resolve()
    except OSError:
        return False
    return child_r == parent_r or parent_r in child_r.parents


def _common_main(script_root: Path) -> Path | None:
    """Parent of the git common dir. For a linked worktree that is the main checkout."""
    proc = subprocess.run(
        ["git", "-C", str(script_root), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True,
        text=True,
        check=False,
    )
    raw = (proc.stdout or "").strip()
    if proc.returncode != 0 or not raw:
        return None
    common = Path(raw)
    if not common.is_absolute():
        common = script_root / common
    try:
        return common.resolve().parent
    except OSError:
        return None


def _refuse_main_checkout(repo: Path) -> str | None:
    """Block scratch in the main checkout when this file lives in another worktree.

    The worktree path itself is often under the main checkout's tmp/. That
    tree is allowed. The main checkout root and the rest of its files,
    including tmp/pgs, are not.
    """
    if repo == ROOT or _under(ROOT, repo):
        return None
    main = _common_main(ROOT)
    if main is None or main == ROOT:
        return None
    if repo == main or _under(main, repo):
        return (
            "refusing eval scratch in the main checkout: %s. "
            "Recovery: run this script from its worktree, or pass --repo under that worktree."
            % main
        )
    return None


def _pin_scratch(repo: Path) -> Path:
    """Create repo/tmp and point TMPDIR at it so children do not inherit a foreign temp."""
    path = repo / "tmp"
    path.mkdir(parents=True, exist_ok=True)
    os.environ["TMPDIR"] = str(path)
    return path


def _summary_dir(repo: Path, stamp: str) -> Path:
    """Run summaries are operator records: the ops checkout when PFY_OPS_ROOT
    is set, else the gitignored pipelines/dogfood/build-local-eval/ here."""
    ops = os.environ.get("PFY_OPS_ROOT", "").strip()
    rel = Path("pipelines") / "dogfood" / "build-local-eval"
    base = (Path(ops).expanduser() / rel) if ops else (repo / rel)
    path = base / stamp
    suffix = 1
    while path.exists():
        suffix += 1
        path = base / ("%s-%d" % (stamp, suffix))
    path.mkdir(parents=True)
    return path


def _write_summary(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2) + "\n"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
    md = path.with_name("summary.md")
    lines = [
        "# local build eval %s" % payload.get("stamp"),
        "",
        "- model: %s" % payload.get("model"),
        "- host: %s" % payload.get("host"),
        "- skip: %s" % (payload.get("skip") or "none"),
        "- passed: %s" % payload.get("passed"),
        "- failed: %s" % payload.get("failed"),
        "- blocked: %s" % payload.get("blocked"),
        "- pass_rate: %s" % payload.get("pass_rate"),
        "- total_seconds: %s" % payload.get("total_seconds"),
        "- mean_seconds: %s" % payload.get("mean_seconds"),
        "",
        "| id | status | reason | wall_s | receipt |",
        "|---|---|---|---|---|",
    ]
    for row in payload.get("tasks") or []:
        lines.append(
            "| %s | %s | %s | %s | %s |"
            % (row.get("id"), row.get("status"), row.get("reason"), row.get("wall_seconds"), row.get("receipt"))
        )
    if payload.get("not_run"):
        lines.append("")
        lines.append("not-run: %s" % ", ".join(payload["not_run"]))
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _endpoint(raw: str | None) -> str:
    value = (raw or os.environ.get("LOCAL_OPENAI_BASE_URL") or DEFAULT_ENDPOINT).strip()
    return value or DEFAULT_ENDPOINT


def _preflight(model: str, endpoint: str) -> str | None:
    """A skip reason, or None when the tasks may start."""
    if not _which_opencode(os.environ):
        return "opencode-missing"
    if BUILD._is_cloud_tag(model):
        return "model-missing %s" % model
    root, _base = BUILD._endpoint_pair(endpoint)
    tags, err = BUILD._ollama_tags(root)
    if err or tags is None:
        return "ollama-unreachable"
    if BUILD._tag_of(model, tags) is None:
        return "model-missing %s" % model
    free = BUILD.free_ram_plus_swap_gib(BUILD.read_meminfo())
    if free < EVAL_START_FLOOR_GB:
        return "mem-guard %.3f" % free
    names = BUILD._ps_names(root)
    if names is None:
        return "busy-host unknown"
    if names:
        others = [name for name in names if not BUILD._same_model(name, model)]
        if others:
            return "busy-host %s" % others[0]
    return None


def _copy_fixture(task_id: str, dest: Path) -> None:
    src = ROOT / "eval" / "local-build" / "fixtures" / task_id
    if not src.is_dir():
        raise RuntimeError("missing fixture %s" % task_id)
    shutil.copytree(
        src,
        dest,
        ignore=shutil.ignore_patterns("reference.patch", "__pycache__", "*.pyc"),
    )


def _git(repo: Path, *args: str) -> None:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), (proc.stderr or proc.stdout or "").strip()))


def _init_repo(repo: Path) -> None:
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "eval@example.com")
    _git(repo, "config", "user.name", "pfy-local-build-eval")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "fixture")


def _run_check(cmd: str, cwd: Path) -> int:
    proc = subprocess.run(
        ["sh", "-c", cmd],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    return proc.returncode


def _one_task(task: dict, repo_dir: Path, endpoint: str, model: str, timeout: float, test_timeout: float, receipt_dir: Path, unload: bool) -> dict:
    task_text = (repo_dir / "task.txt").read_text(encoding="utf-8").strip()
    cmd = [
        str(ROOT / "pfy"),
        "build",
        "--local",
        "--repo",
        str(repo_dir),
        "--model",
        model,
        "--endpoint",
        endpoint,
        "--test-cmd",
        task["test_cmd"],
        "--timeout",
        str(int(timeout)),
        "--test-timeout",
        str(int(test_timeout)),
        "--receipt-dir",
        str(receipt_dir),
        "--keep-worktree",
        "--keep-model",
        "--prompt-file",
        str(repo_dir / "task.txt"),
    ]
    for pattern in task.get("protect") or []:
        cmd.extend(["--protect", pattern])
    if unload:
        cmd.append("--unload-at-end")
    if os.environ.get("PFY_LOCAL_BUILD_UNSAFE_NO_SANDBOX") == "1":
        cmd.append("--unsafe-no-sandbox")
    proc = subprocess.run(
        cmd,
        cwd=repo_dir,
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        check=False,
    )
    receipt_path = receipt_dir / "receipt.json"
    if not receipt_path.is_file():
        raise RuntimeError(
            "no receipt for %s (exit %s)\n%s\n%s" % (task["id"], proc.returncode, proc.stdout, proc.stderr)
        )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    status = receipt.get("status") or "FAIL"
    reason = receipt.get("reason")
    # Pass/fail comes from the receipt. The build process exit is not the score:
    # a deleted test can leave the test command at exit 0 while the receipt says FAIL.
    if status == "PASS":
        worktree = receipt.get("worktree")
        check = task.get("check_cmd") or ""
        if not worktree or not check:
            status = "FAIL"
            reason = "check-failed"
        else:
            # The produced worktree, not the fixture source. The fixture still has the bug.
            code = _run_check(check, Path(worktree))
            if code != 0:
                status = "FAIL"
                reason = "check-failed"
    return {
        "id": task["id"],
        "status": status,
        "reason": reason,
        "wall_seconds": receipt.get("wall_seconds"),
        "tests_before": receipt.get("tests_before"),
        "tests_after": receipt.get("tests_after"),
        "receipt": str(receipt_path),
        "model_was_loaded": receipt.get("model_was_loaded"),
        "unloaded": receipt.get("unloaded"),
        "worktree": receipt.get("worktree"),
        "build_exit": proc.returncode,
    }


def _rates(rows: list[dict]) -> dict:
    passed = sum(1 for row in rows if row["status"] == "PASS")
    failed = sum(1 for row in rows if row["status"] not in ("PASS", "BLOCKED"))
    blocked = sum(1 for row in rows if row["status"] == "BLOCKED")
    scored = passed + failed
    walls = [float(row["wall_seconds"]) for row in rows if isinstance(row.get("wall_seconds"), (int, float))]
    total = round(sum(walls), 3) if walls else 0.0
    mean = round(total / len(walls), 3) if walls else 0.0
    return {
        "passed": passed,
        "failed": failed,
        "blocked": blocked,
        "pass_rate": None if scored == 0 else round(passed / scored, 3),
        "total_seconds": total,
        "mean_seconds": mean,
    }


def _blank(stamp: str, model: str, endpoint: str, skip: str | None, tasks: list, not_run: list, scratch: str | None = None) -> dict:
    payload = {
        "schema": "pfy-local-build-eval/1",
        "stamp": stamp,
        "model": model,
        "host": socket.gethostname(),
        "endpoint": BUILD._host_only(endpoint),
        "skip": skip,
        "tasks": tasks,
        "not_run": not_run,
        "passed": 0,
        "failed": 0,
        "blocked": 0,
        "pass_rate": None,
        "total_seconds": 0.0,
        "mean_seconds": 0.0,
        "scratch": scratch,
    }
    payload.update(_rates(tasks) if not skip else {})
    if skip:
        payload["passed"] = 0
        payload["failed"] = 0
        payload["blocked"] = 0
        payload["pass_rate"] = None
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local-build coding eval")
    parser.add_argument("--only", help="one task id")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--model", default=None, help="Ollama tag (env PFY_LOCAL_BUILD_MODEL, else model-choice)")
    parser.add_argument("--endpoint", default=None)
    parser.add_argument("--timeout", type=float, default=1200)
    parser.add_argument("--test-timeout", type=float, default=600)
    parser.add_argument("--require-live", action="store_true")
    parser.add_argument(
        "--repo",
        default=None,
        help="repo whose tmp/ holds the eval copies (default: the repo that contains this script, not the main checkout)",
    )
    args = parser.parse_args(argv)
    endpoint = _endpoint(args.endpoint)
    if args.model and str(args.model).strip():
        model = str(args.model).strip()
    else:
        explicit = (os.environ.get("PFY_LOCAL_BUILD_MODEL") or "").strip()
        if explicit:
            model = explicit
        else:
            root = Path(__file__).resolve().parents[1]
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            try:
                from pfylib.model_choice import runner_choice
                model = runner_choice("build-lane", transport="ollama", root=root)[1]
            except Exception:
                model = "qwen3.6:35b"
    repo = Path(args.repo).resolve() if args.repo else ROOT
    refused = _refuse_main_checkout(repo)
    if refused:
        print(refused, file=sys.stderr)
        return 2
    scratch_parent = _pin_scratch(repo)
    stamp = _now_stamp()
    try:
        selected = _tasks(args.only, args.limit)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 1
    out = _summary_dir(repo, stamp)
    summary_path = out / "summary.json"
    loaded_by_us = False
    ollama_root, _base = BUILD._endpoint_pair(endpoint)
    try:
        skip = _preflight(model, endpoint)
        if skip:
            payload = _blank(stamp, model, endpoint, skip, [], [row["id"] for row in selected], str(scratch_parent))
            _write_summary(summary_path, payload)
            print("SKIP: %s" % skip)
            print("summary: %s" % summary_path)
            return 2 if args.require_live else 0
        rows = []
        not_run: list[str] = []
        base = scratch_parent / ("local-build-eval-%s" % stamp)
        base.mkdir(parents=True, exist_ok=True)
        for index, task in enumerate(selected):
            dest = base / task["id"]
            _copy_fixture(task["id"], dest)
            _init_repo(dest)
            unload = bool(loaded_by_us and index == len(selected) - 1)
            row = _one_task(
                task,
                dest,
                endpoint,
                model,
                args.timeout,
                args.test_timeout,
                out / task["id"],
                unload,
            )
            rows.append(row)
            if row.get("model_was_loaded") is False and row.get("worktree") and not row.get("unloaded"):
                loaded_by_us = True
            if row["status"] == "BLOCKED":
                not_run = [later["id"] for later in selected[index + 1 :]]
                break
        payload = _blank(stamp, model, endpoint, None, rows, not_run, str(scratch_parent))
        _write_summary(summary_path, payload)
        scored = payload["passed"] + payload["failed"] + payload["blocked"]
        print(
            "pass %s/%s rate=%s summary=%s"
            % (payload["passed"], scored, payload["pass_rate"], summary_path)
        )
        if payload["passed"] < scored:
            return 1
        return 0
    except Exception:
        traceback.print_exc()
        payload = _blank(stamp, model, endpoint, "runner-broken", [], [], str(scratch_parent))
        try:
            _write_summary(summary_path, payload)
        except OSError:
            pass
        return 1
    finally:
        if loaded_by_us:
            try:
                current = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else {}
            except (OSError, json.JSONDecodeError):
                current = {}
            last = (current.get("tasks") or [None])[-1] if current.get("tasks") else None
            if not (isinstance(last, dict) and last.get("unloaded")):
                BUILD.unload_model(ollama_root, model)


if __name__ == "__main__":
    sys.exit(main())
