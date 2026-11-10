#!/usr/bin/env python3
"""Run unittest modules in a process pool, one subprocess per module.

Default module list: every tests/test_*.py under the repo root.
Each child gets a fresh TMPDIR and PFY_STATE_DIR (plus XDG dirs) under the
run directory. -j 1 runs those subprocesses one at a time, in sorted order.

  python3 scripts/run_tests.py
  python3 scripts/run_tests.py -j 16 tests.test_hedge tests.test_cli
  python3 scripts/run_tests.py --shard 0/4
  PFY_TEST_JOBS=4 python3 scripts/run_tests.py

Exit 0 when every module passes. Exit 1 when any module fails. The failing
module's output tail is printed. A JSON receipt records modules, rc, seconds,
and the skip count parsed from unittest output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Modules that fail when they share the machine with the pool.
# Each entry is (dotted module, reason). They run after the pool, one at a time.
# Found on this 32-core host: one -j16 run (3 failures), a second -j16 run
# (4 more), then those modules with -j 1 (all passed). The cloud pair needs a
# clean tmp/cloud-build-tests. A leftover init commit makes the next git
# commit exit 1 with an empty stderr ("nothing to commit" is on stdout).
SERIAL: list[tuple[str, str]] = [
    (
        "tests.test_harness2_local_sandbox",
        "bwrap relay must answer within 5s; under the pool call.pgid is missing. Passes alone",
    ),
    (
        "tests.test_pfy_build_cloud",
        "shares tmp/cloud-build-tests with slice2 and creates /var/tmp/pfyb-* worktrees. Passes alone on a clean scratch",
    ),
    (
        "tests.test_pfy_build_cloud_slice2",
        "shares tmp/cloud-build-tests and snapshots /var/tmp/pfyb-* while the cloud module creates those directories. Passes alone on a clean scratch",
    ),
    (
        "tests.test_pfy_build_phase_clock",
        "under the pool the gate counter read 6 instead of 4. Passes alone",
    ),
    (
        "tests.test_x_intake_smoke_103_105",
        "reads pipelines/smoke/graphjin/latest.json while tests.test_x_intake_smoke_103_111_receipts writes that file",
    ),
    (
        "tests.test_x_intake_smoke_109_111",
        "snapshots pipelines/smoke mtimes and git status while other modules write that tree",
    ),
    (
        "tests.test_x_intake_smoke_112_115_receipts",
        "compares git status --ignored of pipelines/smoke while other modules write that tree",
    ),
]

SKIP_RE = re.compile(r"skipped=(\d+)")
TAIL_LINES = 40
OUT_CAP = 200_000


def repo_root_from(start: Path) -> Path:
    for cand in [start, *start.parents]:
        if (cand / "tests").is_dir() and (cand / "scripts" / "run_tests.py").is_file():
            return cand
    return start


def default_module_files(root: Path) -> list[str]:
    """Posix paths of every tests/**/test_*.py. This is the full suite.

    Files under a ``fixtures`` directory are test data that a test copies
    into a temp repo, not suite modules, so they are left out. This matches
    scripts/test_select.py, which never selects a path under ``/fixtures/``.
    """
    base = root / "tests"
    if not base.is_dir():
        return []
    found: list[str] = []
    for path in base.rglob("test_*.py"):
        rel_parts = path.relative_to(base).parts
        if "__pycache__" in rel_parts or "fixtures" in rel_parts:
            continue
        found.append(path.relative_to(root).as_posix())
    return sorted(found)


def file_to_module(rel: str) -> str:
    stem = rel[:-3] if rel.endswith(".py") else rel
    return stem.replace("/", ".")


def default_modules(root: Path) -> list[str]:
    return [file_to_module(rel) for rel in default_module_files(root)]


def module_file(root: Path, module: str) -> Path:
    return root / (module.replace(".", "/") + ".py")


def mentions_bwrap(root: Path, module: str) -> bool:
    path = module_file(root, module)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "bwrap" in text


def parse_shard(text: str) -> tuple[int, int]:
    """i/n with 0 <= i < n. Anything else is a usage error (exit 2)."""
    parts = text.split("/")
    index = count = 0
    ok = len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit()
    if ok:
        index, count = int(parts[0]), int(parts[1])
        ok = count >= 1 and 0 <= index < count
    if not ok:
        print(f"shard must be i/n with 0 <= i < n, got {text}", file=sys.stderr)
        raise SystemExit(2)
    return index, count


def shard_slot(name: str, count: int) -> int:
    """Stable slot. Python's hash() is salted per process, so this uses sha256."""
    digest = hashlib.sha256(name.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % count


def apply_shard(modules: list[str], shard: tuple[int, int] | None) -> list[str]:
    if shard is None:
        return list(modules)
    index, count = shard
    return [name for name in modules if shard_slot(name, count) == index]


def resolve_jobs(cli: int | None) -> int:
    if cli is not None:
        raw = str(cli)
    else:
        raw = os.environ.get("PFY_TEST_JOBS", "").strip()
    if not raw:
        n = min(16, os.cpu_count() or 1)
    else:
        try:
            n = int(raw)
        except ValueError as exc:
            raise SystemExit(f"PFY_TEST_JOBS is not an integer: {raw}") from exc
    if n < 1:
        raise SystemExit("jobs must be >= 1")
    return n


def skip_count(text: str) -> int:
    found = SKIP_RE.findall(text or "")
    if not found:
        return 0
    return int(found[-1])


def _emit(lock: threading.Lock, text: str) -> None:
    with lock:
        print(text, flush=True)


def run_one(root: Path, module: str, run_dir: Path) -> dict:
    slot = run_dir / module.replace(".", "_")
    tmp = slot / "tmp"
    state = slot / "state"
    xdg = slot / "xdg"
    for path in (tmp, state, xdg / "cache", xdg / "config", xdg / "data", xdg / "state"):
        path.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["TMPDIR"] = str(tmp)
    env["TMP"] = str(tmp)
    env["PFY_STATE_DIR"] = str(state)
    env["XDG_CACHE_HOME"] = str(xdg / "cache")
    env["XDG_CONFIG_HOME"] = str(xdg / "config")
    env["XDG_DATA_HOME"] = str(xdg / "data")
    env["XDG_STATE_HOME"] = str(xdg / "state")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if os.environ.get("PFY_TEST_ISOLATE_HOME") == "1":
        home = slot / "home"
        home.mkdir(parents=True, exist_ok=True)
        env["HOME"] = str(home)
    cmd = [sys.executable, "-m", "unittest", "-q", module]
    started = time.monotonic()
    proc = subprocess.run(
        cmd,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    seconds = time.monotonic() - started
    out = (proc.stdout or "") + (proc.stderr or "")
    if len(out) > OUT_CAP:
        out = out[-OUT_CAP:]
    shutil.rmtree(slot, ignore_errors=True)
    status = "PASS" if proc.returncode == 0 else "FAIL"
    return {
        "module": module,
        "status": status,
        "seconds": round(seconds, 3),
        "skips": skip_count(out),
        "rc": proc.returncode,
        "output": out,
    }


def _print_result(lock: threading.Lock, row: dict) -> None:
    line = (
        f"{row['status']} {row['module']} {row['seconds']:.2f}s skips={row['skips']}"
    )
    _emit(lock, line)
    if row["status"] != "PASS":
        tail = "\n".join((row.get("output") or "").splitlines()[-TAIL_LINES:])
        _emit(lock, f"FAIL {row['module']} output tail:\n{tail}")


def execute(root: Path, modules: list[str], jobs: int, run_dir: Path) -> dict:
    serial_set = {name for name, _reason in SERIAL}
    pool = [name for name in modules if name not in serial_set]
    serial = [name for name in modules if name in serial_set]
    lock = threading.Lock()
    rows: list[dict] = []
    started = time.monotonic()
    if jobs == 1:
        for name in pool + serial:
            row = run_one(root, name, run_dir)
            rows.append(row)
            _print_result(lock, row)
    else:
        with ThreadPoolExecutor(max_workers=jobs) as pool_ex:
            futures = [pool_ex.submit(run_one, root, name, run_dir) for name in pool]
            for fut in as_completed(futures):
                row = fut.result()
                rows.append(row)
                _print_result(lock, row)
        for name in serial:
            row = run_one(root, name, run_dir)
            rows.append(row)
            _print_result(lock, row)
    seconds = round(time.monotonic() - started, 3)
    by_module = {row["module"]: row for row in rows}
    ordered = [by_module[name] for name in modules if name in by_module]
    failed = [row for row in ordered if row["status"] != "PASS"]
    public = []
    for row in ordered:
        public.append({k: v for k, v in row.items() if k != "output"})
    receipt = {
        "modules": list(modules),
        "rc": 0 if not failed else 1,
        "seconds": seconds,
        "skips": sum(row["skips"] for row in ordered),
        "jobs": jobs,
        "serial": [name for name, _reason in SERIAL if name in serial_set and name in modules],
        "shard": None,
        "results": public,
    }
    return receipt


def write_receipt(path: Path, receipt: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(receipt, indent=2, sort_keys=True).encode("utf-8")
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    with tmp.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("modules", nargs="*", help="dotted unittest modules (default: all tests/test_*.py)")
    ap.add_argument("-j", "--jobs", type=int, default=None, help="parallel subprocesses (default min(16, cpus) or PFY_TEST_JOBS)")
    ap.add_argument("--root", type=Path, default=None)
    ap.add_argument("--receipt", type=Path, default=None)
    ap.add_argument("--list", action="store_true", help="print the default module list and exit")
    ap.add_argument("--print-bwrap", action="store_true", help="print modules whose source mentions bwrap, then exit")
    ap.add_argument("--shard", default=None, help="run shard i/n (0 <= i < n) by stable module-name hash")
    ap.add_argument("--run-dir", type=Path, default=None)
    args = ap.parse_args(argv)
    root = (args.root or Path.cwd()).resolve()
    shard = parse_shard(args.shard) if args.shard else None
    if args.list and not args.modules:
        for name in apply_shard(default_modules(root), shard):
            print(name)
        return 0
    modules = list(args.modules) or default_modules(root)
    if args.list:
        for name in apply_shard(modules, shard):
            print(name)
        return 0
    if args.print_bwrap:
        chosen = apply_shard(modules or default_modules(root), shard)
        for name in chosen:
            if mentions_bwrap(root, name):
                print(name)
        return 0
    if not modules:
        print("no test modules", file=sys.stderr)
        return 2
    jobs = resolve_jobs(args.jobs)
    shard_label = f"{shard[0]}/{shard[1]}" if shard else None
    modules = apply_shard(modules, shard)
    if shard and not modules:
        receipt = {
            "modules": [],
            "rc": 0,
            "seconds": 0,
            "skips": 0,
            "jobs": jobs,
            "serial": [],
            "shard": shard_label,
            "results": [],
        }
        parent_tmp = os.environ.get("TMPDIR") or tempfile.gettempdir()
        if args.run_dir:
            run_dir = args.run_dir
            run_dir.mkdir(parents=True, exist_ok=True)
        else:
            run_dir = Path(tempfile.mkdtemp(prefix="pfy-tests-", dir=parent_tmp))
        receipt_path = args.receipt or (run_dir / "receipt.json")
        write_receipt(receipt_path, receipt)
        print(
            f"modules=0 failed=0 skips=0 seconds=0.00 jobs={jobs} shard={shard_label}",
            flush=True,
        )
        print(f"receipt: {receipt_path}", flush=True)
        return 0
    parent_tmp = os.environ.get("TMPDIR") or tempfile.gettempdir()
    if args.run_dir:
        run_dir = args.run_dir
        run_dir.mkdir(parents=True, exist_ok=True)
    else:
        run_dir = Path(tempfile.mkdtemp(prefix="pfy-tests-", dir=parent_tmp))
    receipt = execute(root, modules, jobs, run_dir)
    receipt["shard"] = shard_label
    receipt_path = args.receipt or (run_dir / "receipt.json")
    write_receipt(receipt_path, receipt)
    failed = receipt["rc"] != 0
    print(
        f"modules={len(modules)} failed={sum(1 for row in receipt['results'] if row['status'] != 'PASS')} "
        f"skips={receipt['skips']} seconds={receipt['seconds']:.2f} jobs={jobs}"
        + (f" shard={shard_label}" if shard_label else ""),
        flush=True,
    )
    print(f"receipt: {receipt_path}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
