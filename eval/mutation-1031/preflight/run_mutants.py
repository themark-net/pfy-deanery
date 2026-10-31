#!/usr/bin/env python3
"""Apply one preflight or receipt mutant at a time inside a throwaway clone.

Reads the target from the source tree, writes the mutated copy only under
the clone, and runs the classifier and receipt suites there. The source
files are never opened for write.

  python3 eval/mutation-1031/preflight/run_mutants.py --baseline-only --label before
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
TARGETS = (
    "pfylib/build_preflight.py",
    "eval/mvp-1031/check_receipt.py",
)
DEFAULT_TIMEOUT = 90.0

# Each old string must match its target once. new replaces that one site.
# Mutants are applied to a fresh clone of the original, never stacked.
MUTANTS: list[dict[str, str]] = [
    {
        "id": "P1",
        "title": "zero exit still classified",
        "target": "pfylib/build_preflight.py",
        "old": '    if rc == 0:\n        return "other"\n    text = f"{stdout}\\n{stderr}".lower()\n',
        "new": '    if False and rc == 0:\n        return "other"\n    text = f"{stdout}\\n{stderr}".lower()\n',
    },
    {
        "id": "P2",
        "title": "auth rule runs before rate-limit",
        "target": "pfylib/build_preflight.py",
        "old": '    if any(phrase in text for phrase in _RATE_LIMIT):\n'
        '        return "rate-limit"\n'
        '    if any(phrase in text for phrase in _UNAUTHENTICATED):\n'
        '        return "unauthenticated"\n',
        "new": '    if any(phrase in text for phrase in _UNAUTHENTICATED):\n'
        '        return "unauthenticated"\n'
        '    if any(phrase in text for phrase in _RATE_LIMIT):\n'
        '        return "rate-limit"\n',
    },
    {
        "id": "P3",
        "title": "429 phrase removed",
        "target": "pfylib/build_preflight.py",
        "old": '    "too many requests",\n    "429",\n',
        "new": '    "too many requests",\n',
    },
    {
        "id": "P5",
        "title": "case fold removed",
        "target": "pfylib/build_preflight.py",
        "old": '    text = f"{stdout}\\n{stderr}".lower()\n',
        "new": '    text = f"{stdout}\\n{stderr}"\n',
    },
    {
        "id": "P6",
        "title": "stdout and stderr joined without a newline",
        "target": "pfylib/build_preflight.py",
        "old": '    text = f"{stdout}\\n{stderr}".lower()\n'
        '    if any(phrase in text for phrase in _RATE_LIMIT):\n',
        "new": '    text = f"{stdout}{stderr}".lower()\n'
        '    if any(phrase in text for phrase in _RATE_LIMIT):\n',
    },
    {
        "id": "P7",
        "title": "negative rc treated as success",
        "target": "pfylib/build_preflight.py",
        "old": '    if rc == 0:\n        return "other"\n',
        "new": '    if rc <= 0:\n        return "other"\n',
    },
    {
        "id": "P8",
        "title": "repeated spaces collapsed before match",
        "target": "pfylib/build_preflight.py",
        "old": '    text = f"{stdout}\\n{stderr}".lower()\n',
        "new": '    text = f"{stdout}\\n{stderr}".lower().replace("  ", " ")\n',
    },
    {
        "id": "P9",
        "title": "zero float clause added",
        "target": "pfylib/build_preflight.py",
        "old": '    if rc == 0:\n        return "other"\n',
        "new": '    if rc == 0 or rc == 0.0:\n        return "other"\n',
    },
    {
        "id": "R1",
        "title": "status check skipped",
        "target": "eval/mvp-1031/check_receipt.py",
        "old": '    if data.get("status") != "PASS":\n        return "rejected: status is not PASS"\n',
        "new": '    if False and data.get("status") != "PASS":\n        return "rejected: status is not PASS"\n',
    },
    {
        "id": "R2",
        "title": "reason check skipped",
        "target": "eval/mvp-1031/check_receipt.py",
        "old": '    if data.get("reason") != "ok":\n        return "rejected: reason is not ok"\n',
        "new": '    if False and data.get("reason") != "ok":\n        return "rejected: reason is not ok"\n',
    },
    {
        "id": "R3",
        "title": "exit_code check skipped",
        "target": "eval/mvp-1031/check_receipt.py",
        "old": '    if type(data.get("exit_code")) is not int or data.get("exit_code") != 0:\n'
        '        return "rejected: exit_code is not 0"\n',
        "new": '    if False and (type(data.get("exit_code")) is not int or data.get("exit_code") != 0):\n'
        '        return "rejected: exit_code is not 0"\n',
    },
    {
        "id": "R4",
        "title": "gate cmd check skipped",
        "target": "eval/mvp-1031/check_receipt.py",
        "old": '    if not isinstance(cmd, str) or cmd == "":\n        return "rejected: gate.cmd is empty"\n',
        "new": '    if False and (not isinstance(cmd, str) or cmd == ""):\n'
        '        return "rejected: gate.cmd is empty"\n',
    },
    {
        "id": "R5",
        "title": "invalid json accepted",
        "target": "eval/mvp-1031/check_receipt.py",
        "old": '    except json.JSONDecodeError:\n        return "rejected: receipt is not json"\n',
        "new": '    except json.JSONDecodeError:\n        return None\n',
    },
    {
        "id": "R7",
        "title": "pushed 0 accepted",
        "target": "eval/mvp-1031/check_receipt.py",
        "old": '    if data.get("pushed") is not False:\n',
        "new": '    if data.get("pushed") != False:\n',
    },
    {
        "id": "R8",
        "title": "attempts accepts any truthy value",
        "target": "eval/mvp-1031/check_receipt.py",
        "old": '    if not isinstance(attempts, list) or len(attempts) == 0:\n'
        '        return "rejected: attempts is empty"\n',
        "new": '    if not attempts:\n        return "rejected: attempts is empty"\n',
    },
    {
        "id": "R10",
        "title": "branch prefix allows cloudy",
        "target": "eval/mvp-1031/check_receipt.py",
        "old": '    if not isinstance(branch, str) or not branch.startswith("cloud/"):\n',
        "new": '    if not isinstance(branch, str) or not branch.startswith("cloud"):\n',
    },
    {
        "id": "R11",
        "title": "AKIA check skipped",
        "target": "eval/mvp-1031/check_receipt.py",
        "old": '    if "AKIA" in raw:\n        return "rejected: receipt text contains AKIA"\n',
        "new": '    if False and "AKIA" in raw:\n        return "rejected: receipt text contains AKIA"\n',
    },
    {
        "id": "R12",
        "title": "missing receipt file accepted",
        "target": "eval/mvp-1031/check_receipt.py",
        "old": '    if not path.is_file():\n'
        '        print("rejected: receipt file is missing", file=sys.stderr)\n'
        '        return 1\n',
        "new": '    if not path.is_file():\n'
        '        print("rejected: receipt file is missing", file=sys.stderr)\n'
        '        return 0\n',
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


def suite_modules(root: Path, baseline_only: bool) -> list[str]:
    names = [
        "tests.test_build_preflight",
        "tests.test_mvp_1031_receipt",
    ]
    if baseline_only:
        return names
    tests = root / "tests"
    for path in sorted(tests.glob("test_mut_preflight_*.py")):
        if path.stem == "test_mut_preflight_harness":
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
        "id": mutant["id"] if mutant else "base",
        "title": mutant["title"] if mutant else "unmutated suite",
        "target": mutant.get("target", script_rel) if mutant else script_rel,
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
        if script.is_file() and hash_file(script) != before:
            row["status"] = "error"
            row["detail"] = "source script changed"
        if not keep:
            stop_under(dest)
            shutil.rmtree(dest, ignore_errors=True)


def source_hashes(src: Path) -> dict[str, str]:
    return {rel: hash_file(src / rel) for rel in TARGETS}


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


def count_rows(rows: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run preflight and receipt mutants in throwaway clones")
    parser.add_argument("--mutant", action="append", default=[], help="mutant id, repeatable")
    parser.add_argument(
        "--baseline-only",
        action="store_true",
        help="run only the classifier and receipt suites, not tests.test_mut_preflight_*",
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--label", default="latest")
    parser.add_argument("--results", default="")
    parser.add_argument("--keep", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)
    if args.list:
        print(
            format_table(
                [
                    {
                        "id": item["id"],
                        "title": item["title"],
                        "status": "listed",
                        "seconds": "",
                        "detail": item["target"],
                    }
                    for item in MUTANTS
                ]
            )
        )
        return 0
    selected = MUTANTS
    if args.mutant:
        wanted = set(args.mutant)
        selected = [item for item in MUTANTS if item["id"] in wanted]
        missing = wanted - {item["id"] for item in selected}
        if missing:
            print("unknown mutant %s" % ", ".join(sorted(missing)), file=sys.stderr)
            return 2
    for item in selected:
        if item["target"] not in TARGETS:
            print("mutant %s target is not owned" % item["id"], file=sys.stderr)
            return 2
    hashes = source_hashes(ROOT)
    modules = suite_modules(ROOT, args.baseline_only)
    if not modules:
        print("no test modules", file=sys.stderr)
        return 2
    payload: dict = {
        "label": args.label,
        "baseline_only": args.baseline_only,
        "modules": modules,
        "head": git_sha(ROOT, "HEAD"),
        "integrate": git_sha(ROOT, "origin/bot/mvp-integrate-1031"),
        "sources": hashes,
        "base": None,
        "rows": [],
    }
    results_path = (
        Path(args.results)
        if args.results
        else ROOT / "eval" / "mutation-1031" / "preflight" / "results" / (args.label + ".json")
    )
    exit_code = 0
    base_row = evaluate(
        src=ROOT,
        dest=ROOT / "tmp" / "mutation-1031" / "preflight" / "clones" / "base",
        mutant=None,
        modules=modules,
        timeout=args.timeout,
        script_rel=TARGETS[0],
        keep=args.keep,
    )
    payload["base"] = base_row
    write_results(results_path, payload)
    print("%s %s %ss %s" % (base_row["id"], base_row["status"], base_row["seconds"], base_row["detail"]), flush=True)
    if source_hashes(ROOT) != hashes:
        print("source changed", file=sys.stderr)
        return 2
    if base_row["status"] != "survived":
        print("red base", file=sys.stderr)
        return 2
    for mutant in selected:
        dest = ROOT / "tmp" / "mutation-1031" / "preflight" / "clones" / mutant["id"]
        row = evaluate(
            src=ROOT,
            dest=dest,
            mutant=mutant,
            modules=modules,
            timeout=args.timeout,
            script_rel=mutant["target"],
            keep=args.keep,
        )
        payload["rows"].append(row)
        write_results(results_path, payload)
        print("%s %s %ss %s" % (row["id"], row["status"], row["seconds"], row["detail"]), flush=True)
        if row["status"] in {"unapplicable", "error"}:
            exit_code = 2
        if source_hashes(ROOT) != hashes:
            print("source changed", file=sys.stderr)
            return 2
    if source_hashes(ROOT) != hashes:
        print("source changed", file=sys.stderr)
        return 2
    print(format_table(payload["rows"]))
    print("counts %s" % json.dumps(count_rows(payload["rows"]), sort_keys=True))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
