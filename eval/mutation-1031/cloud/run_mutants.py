#!/usr/bin/env python3
"""Apply one cloud-runner mutant at a time inside a throwaway clone.

Reads scripts/pfy_build_cloud.py from the source tree, writes the mutated
copy only under <clone>/scripts/pfy_build_cloud.py, and runs the cloud suite
there. The source file is never opened for write.

  python3 eval/mutation-1031/cloud/run_mutants.py --baseline-only --label before
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNNER_REL = "scripts/pfy_build_cloud.py"
DEFAULT_TIMEOUT = 180.0

# Each old string must match the runner once. new replaces that one site.
MUTANTS: list[dict[str, str]] = [
    {
        "id": "C1",
        "title": "gate result inverted",
        "old": '            if after.get("exit") != 0 or not after.get("started"):\n'
        '                feedback = "gate failed: tests\\n%s" % (after.get("tail") or "")\n',
        "new": '            if after.get("exit") == 0 and after.get("started"):\n'
        '                feedback = "gate failed: tests\\n%s" % (after.get("tail") or "")\n',
    },
    {
        "id": "C2",
        "title": "retry count off by one",
        "old": "        self.max_attempts = 1 if args.no_review else args.retries + 1\n",
        "new": "        self.max_attempts = 1 if args.no_review else args.retries\n",
    },
    {
        "id": "C3",
        "title": "review accept and reject swapped",
        "old": '    if "reject" in found:\n'
        '        return "reject", reasons or ["review-rejected"]\n'
        '    return "accept", reasons\n',
        "new": '    if "reject" in found:\n'
        '        return "accept", reasons or ["review-rejected"]\n'
        '    return "reject", reasons\n',
    },
    {
        "id": "C4",
        "title": "missing verdict treated as accept",
        "old": '    if not found:\n        return "reject", reasons or ["review-unparseable"]\n',
        "new": '    if not found:\n        return "accept", reasons or ["review-unparseable"]\n',
    },
    {
        "id": "C5",
        "title": "scope set check skipped",
        "old": "        if set(cached_names(self.worktree)) != set(paths):\n",
        "new": "        if False and set(cached_names(self.worktree)) != set(paths):\n",
    },
    {
        "id": "C6",
        "title": "git add of a path outside the reviewed set",
        "old": '        added = _git(self.worktree, ["add", "--", *[":(literal)%s" % path for path in paths]])\n',
        "new": '        added = _git(self.worktree, ["add", "-A", "-f"])\n',
    },
    {
        "id": "C7",
        "title": "rate-limit class ignored",
        "old": '    kind = classify_cloud_failure(code, stdout, stderr)\n'
        '    if kind != "other":\n'
        "        return kind\n",
        "new": '    kind = classify_cloud_failure(code, stdout, stderr)\n'
        '    if kind == "rate-limit":\n'
        '        kind = "other"\n'
        '    if kind != "other":\n'
        "        return kind\n",
    },
    {
        "id": "C8",
        "title": "auth regex removed",
        "old": '    if _NOT_SIGNED_IN.search("%s\\n%s" % (stdout or "", stderr or "")):\n'
        '        return "unauthenticated"\n',
        "new": '    if False and _NOT_SIGNED_IN.search("%s\\n%s" % (stdout or "", stderr or "")):\n'
        '        return "unauthenticated"\n',
    },
    {
        "id": "C9",
        "title": "interrupted handler does not kill the process group",
        "old": "        state.interrupted = True\n"
        "        if state.pgid:\n"
        "            _signal_pgid(state.pgid, signal.SIGTERM)\n",
        "new": "        state.interrupted = True\n"
        "        if False and state.pgid:\n"
        "            _signal_pgid(state.pgid, signal.SIGTERM)\n",
    },
    {
        "id": "C10",
        "title": "reap signals the local pid file",
        "old": "    notes: list[str] = []\n"
        '    pid_path = repo / "tmp" / "cloud-build.pids.json"\n'
        "    if pid_path.is_file():\n",
        "new": "    notes: list[str] = []\n"
        '    local_pid_path = repo / "tmp" / "local-build.pids.json"\n'
        "    if local_pid_path.is_file():\n"
        "        try:\n"
        '            local_data = json.loads(local_pid_path.read_text(encoding="utf-8"))\n'
        "        except (OSError, json.JSONDecodeError):\n"
        "            local_data = {}\n"
        "        if isinstance(local_data, dict):\n"
        '            for key in ("agent_pgid", "pgid"):\n'
        "                try:\n"
        "                    local_pg = int(local_data.get(key) or 0)\n"
        "                except (TypeError, ValueError):\n"
        "                    local_pg = 0\n"
        "                _kill_pgid(local_pg)\n"
        '    pid_path = repo / "tmp" / "cloud-build.pids.json"\n'
        "    if pid_path.is_file():\n",
    },
    {
        "id": "C11",
        "title": "redaction step skipped",
        "old": "def redact(text: str) -> str:\n    if not text:\n        return \"\"\n",
        "new": "def redact(text: str) -> str:\n    return text or \"\"\n    if not text:\n        return \"\"\n",
    },
    {
        "id": "C12",
        "title": "receipt pushed hard-coded true",
        "old": '            "recovery": self.recovery,\n'
        '            "pushed": False,\n'
        '            "worktree_removed": self.worktree_removed,\n',
        "new": '            "recovery": self.recovery,\n'
        '            "pushed": True,\n'
        '            "worktree_removed": self.worktree_removed,\n',
    },
    {
        "id": "C13",
        "title": "worktree not removed on PASS",
        "old": "        if self.args.keep_worktree:\n"
        "            self.worktree_removed = False\n"
        "            return\n",
        "new": "        if True or self.args.keep_worktree:\n"
        "            self.worktree_removed = False\n"
        "            return\n",
    },
    {
        "id": "C14",
        "title": "branch prefix changed",
        "old": '        self.branch_name = "cloud/%s-%s" % (self.slug, self.stamp)\n',
        "new": '        self.branch_name = "mut/%s-%s" % (self.slug, self.stamp)\n',
    },
    {
        "id": "C15",
        "title": "dry-run starts grok",
        "old": "    if args.dry_run:\n        return _dry_run(args, repo, base_ref, receipt)\n",
        "new": "    if False and args.dry_run:\n        return _dry_run(args, repo, base_ref, receipt)\n",
    },
    {
        "id": "C16",
        "title": "exit codes 4, 3, 1, 2 shuffled",
        "old": "EXIT_OK = 0\nEXIT_FAIL = 1\nEXIT_USAGE = 2\nEXIT_TIMEOUT = 3\nEXIT_BLOCKED = 4\n",
        "new": "EXIT_OK = 0\nEXIT_FAIL = 2\nEXIT_USAGE = 4\nEXIT_TIMEOUT = 1\nEXIT_BLOCKED = 3\n",
    },
]


class ApplyError(Exception):
    def __init__(self, count: int) -> None:
        self.count = count
        super().__init__("anchor count %s" % count)


class ScratchError(Exception):
    pass


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_text(text: str, mutant: dict[str, str]) -> str:
    count = text.count(mutant["old"])
    if count != 1:
        raise ApplyError(count)
    return text.replace(mutant["old"], mutant["new"], 1)


def require_scratch(src: Path, dest: Path) -> None:
    base = (src / "tmp").resolve()
    parent = dest.parent.resolve()
    target = parent / dest.name
    if target != base and base not in target.parents:
        raise ScratchError("refusing clone outside %s" % base)


def clone_repo(src: Path, dest: Path) -> None:
    require_scratch(src, dest)
    if dest.exists():
        stop_under(dest)
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["git", "clone", "--local", "--no-hardlinks", str(src), str(dest)],
        cwd=src,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0 or not dest.is_dir():
        raise ScratchError((proc.stderr or proc.stdout or "git clone failed").strip()[:400])


def cloud_modules(root: Path, baseline_only: bool) -> list[str]:
    tests = root / "tests"
    names = ["tests.%s" % path.stem for path in sorted(tests.glob("test_pfy_build_cloud*.py"))]
    if baseline_only:
        return names
    for path in sorted(tests.glob("test_mut_cloud_*.py")):
        if path.stem == "test_mut_cloud_harness":
            continue
        names.append("tests.%s" % path.stem)
    return names


def _pids_under(root: Path) -> list[int]:
    prefix = str(root.resolve())
    found: list[int] = []
    proc_root = Path("/proc")
    if not proc_root.is_dir():
        return found
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid <= 1 or pid == os.getpid():
            continue
        try:
            cwd = os.readlink(entry / "cwd")
        except OSError:
            continue
        if cwd == prefix or cwd.startswith(prefix + os.sep):
            found.append(pid)
    return found


def stop_under(root: Path) -> None:
    """Stop processes this harness started whose cwd is still the clone."""
    if not root.exists():
        return
    for pid in _pids_under(root):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    time.sleep(0.2)
    if not root.exists():
        return
    for pid in _pids_under(root):
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass


def scrub(text: str) -> str:
    import re

    text = re.sub(r"\bAKIA[0-9A-Z]{16}\b", "[redacted]", text)
    text = re.sub(r"(?i)bearer\s+\S+", "bearer [redacted]", text)
    text = re.sub(r"\bxai-[A-Za-z0-9]+\b", "[redacted]", text)
    text = re.sub(r"\b(?:sk|ghp)_[A-Za-z0-9_\-]+\b", "[redacted]", text)
    return text


def first_detail(text: str) -> str:
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("FAIL:", "ERROR:", "AssertionError", "Traceback", "Ran ")):
            return scrub(stripped)[:240]
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return ""
    return scrub(lines[-1])[:240]


def run_modules(clone: Path, modules: list[str], timeout: float) -> dict:
    scratch = clone / "tmp" / "harness-tmpdir"
    scratch.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["TMPDIR"] = str(scratch)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    argv = ["nice", "-n", "19", sys.executable, "-m", "unittest", *modules]
    started = time.monotonic()
    proc = subprocess.Popen(
        argv,
        cwd=str(clone),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    timed_out = False
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except OSError:
            pass
        try:
            out, err = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
            out, err = proc.communicate(timeout=5)
    seconds = round(time.monotonic() - started, 3)
    combined = (out or "") + "\n" + (err or "")
    log_dir = clone.parent / "logs"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / (clone.name + ".log")).write_text(scrub(combined)[-20000:], encoding="utf-8")
    except OSError:
        pass
    return {
        "returncode": proc.returncode,
        "seconds": seconds,
        "timed_out": timed_out,
        "detail": "timeout" if timed_out else first_detail(combined),
    }


def evaluate(
    *,
    src: Path,
    dest: Path,
    mutant: dict[str, str] | None,
    modules: list[str],
    timeout: float,
    script_rel: str,
    keep: bool = False,
) -> dict:
    """Clone src to dest, maybe mutate script_rel, run modules. Never writes src."""
    row: dict = {
        "id": mutant["id"] if mutant else "plain",
        "title": mutant["title"] if mutant else "unmutated",
        "status": "error",
        "returncode": None,
        "seconds": 0,
        "detail": "",
    }
    script = src / script_rel
    before = hash_file(script)
    try:
        require_scratch(src, dest)
        clone_repo(src, dest)
        target = dest / script_rel
        if mutant is not None:
            try:
                mutated = apply_text(target.read_text(encoding="utf-8"), mutant)
            except ApplyError as exc:
                row["status"] = "unapplicable"
                row["detail"] = "anchor count %s" % exc.count
                return row
            ast.parse(mutated)
            target.write_text(mutated, encoding="utf-8")
        if hash_file(script) != before:
            row["status"] = "error"
            row["detail"] = "source script changed"
            return row
        outcome = run_modules(dest, modules, timeout)
        row["returncode"] = outcome["returncode"]
        row["seconds"] = outcome["seconds"]
        row["detail"] = outcome["detail"]
        if outcome["timed_out"]:
            row["status"] = "killed"
            row["detail"] = "timeout"
        elif outcome["returncode"] == 0:
            row["status"] = "survived"
        else:
            row["status"] = "killed"
        return row
    except ScratchError as exc:
        row["status"] = "error"
        row["detail"] = str(exc)[:240]
        return row
    finally:
        if hash_file(script) != before:
            row["status"] = "error"
            row["detail"] = "source script changed"
        if not keep:
            stop_under(dest)
            shutil.rmtree(dest, ignore_errors=True)


def git_sha(repo: Path, ref: str) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", ref],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").strip()


def write_results(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def format_table(rows: list[dict]) -> str:
    lines = ["id | title | status | seconds | detail"]
    for row in rows:
        lines.append(
            "%s | %s | %s | %s | %s"
            % (row["id"], row["title"], row["status"], row.get("seconds", ""), row.get("detail", ""))
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run cloud runner mutants in throwaway clones")
    parser.add_argument("--mutant", action="append", default=[], help="mutant id, repeatable")
    parser.add_argument("--baseline-only", action="store_true", help="run only tests.test_pfy_build_cloud*")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--label", default="latest")
    parser.add_argument("--results", default="")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)
    if args.list:
        print(format_table([{"id": item["id"], "title": item["title"], "status": "listed", "seconds": "", "detail": ""} for item in MUTANTS]))
        return 0
    selected = MUTANTS
    if args.mutant:
        wanted = set(args.mutant)
        selected = [item for item in MUTANTS if item["id"] in wanted]
        missing = wanted - {item["id"] for item in selected}
        if missing:
            print("unknown mutant %s" % ", ".join(sorted(missing)), file=sys.stderr)
            return 2
    runner = ROOT / RUNNER_REL
    digest = hash_file(runner)
    modules = cloud_modules(ROOT, args.baseline_only)
    if not modules:
        print("no test modules", file=sys.stderr)
        return 2
    payload: dict = {
        "label": args.label,
        "baseline_only": args.baseline_only,
        "modules": modules,
        "head": git_sha(ROOT, "HEAD"),
        "cloudfix": git_sha(ROOT, "origin/bot/mvp-cloudfix-1031"),
        "runner_sha256": digest,
        "rows": [],
    }
    results_path = Path(args.results) if args.results else ROOT / "eval" / "mutation-1031" / "cloud" / "results" / (args.label + ".json")
    exit_code = 0
    for mutant in selected:
        dest = ROOT / "tmp" / "mutation-1031" / "cloud" / "clones" / mutant["id"]
        row = evaluate(
            src=ROOT,
            dest=dest,
            mutant=mutant,
            modules=modules,
            timeout=args.timeout,
            script_rel=RUNNER_REL,
            keep=args.keep,
        )
        payload["rows"].append(row)
        write_results(results_path, payload)
        print("%s %s %ss %s" % (row["id"], row["status"], row["seconds"], row["detail"]), flush=True)
        if row["status"] in {"unapplicable", "error"}:
            exit_code = 2
        if hash_file(runner) != digest:
            print("source runner changed", file=sys.stderr)
            return 2
    if hash_file(runner) != digest:
        print("source runner changed", file=sys.stderr)
        return 2
    print(format_table(payload["rows"]))
    counts: dict[str, int] = {}
    for row in payload["rows"]:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    print("counts %s" % json.dumps(counts, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
