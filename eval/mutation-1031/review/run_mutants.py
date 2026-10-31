#!/usr/bin/env python3
"""One review-loop mutant at a time, on a throwaway clone.

The worktree copy of scripts/pfy_build_local.py is never written. Each mutant
is applied to the clone, the local-runner tests run there, then the clone file
is restored. A missing anchor is not-applied. A timeout is not a kill.

No local model. The targeted modules stub Ollama, opencode, and the reviewer.
Default invocation only checks that each anchor matches the runner once.
Pass --run to clone and execute the suite.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
RUNNER_REL = "scripts/pfy_build_local.py"
SCRATCH = REPO / "tmp" / "mutation-1031"

# Audited 2026-10-31 against the three modules. None call a model.
# The review module uses the stub HTTP server in tests.test_pfy_build_local.
# The CI module reruns that review module with bwrap hidden.
# test_help_and_dry_run_stay_the_same runs `pfy build -p --dry-run`, which
# does not execute grok. test_real_opencode_accepts_the_flags_we_pass runs
# `opencode --version` and `opencode run --help`.
MODEL_AUDIT = (
    "No targeted test calls a model. Exclude list is empty. "
    "Stubs only: in-process Ollama, stub opencode, in-process HTTP reviewer. "
    "Cloud dry-run does not execute grok. opencode --help is not a model call."
)
EXCLUDE_MODEL_TESTS: list[str] = []

DRIVER = r"""
import os
import sys
import unittest

mods = [item for item in os.environ.get("PFY_MUT_MODULES", "").split(",") if item]
exclude = [item for item in os.environ.get("PFY_MUT_EXCLUDE", "").split(",") if item]
loader = unittest.defaultTestLoader
suite = loader.loadTestsFromNames(mods)
kept = unittest.TestSuite()

def _skip(tid):
    for item in exclude:
        if tid == item or tid.endswith("." + item):
            return True
    return False

def _walk(node):
    if isinstance(node, unittest.TestSuite):
        for child in node:
            _walk(child)
        return
    tid = node.id()
    if _skip(tid):
        print("EXCLUDED %s" % tid)
        return
    kept.addTest(node)

_walk(suite)
result = unittest.TextTestRunner(verbosity=1).run(kept)
sys.exit(0 if result.wasSuccessful() else 1)
"""


class ApplyError(Exception):
    pass


class Mutant:
    def __init__(self, mid, title, reviewer, replacements):
        self.id = mid
        self.title = title
        self.reviewer = reviewer
        self.replacements = replacements


def _m(mid, title, reviewer, old, new):
    return Mutant(mid, title, reviewer, ((old, new),))


def _catalog():
    review_off = (
        "    args.review = not args.no_review_flag\n",
        "    args.review = False\n",
    )
    invert = (
        "    if not all(isinstance(item, str) for item in reasons):\n"
        '        return "reject", ["review-unparseable"], raw[:500]\n'
        "    return verdict, reasons, raw[:500]\n",
        "    if not all(isinstance(item, str) for item in reasons):\n"
        '        return "reject", ["review-unparseable"], raw[:500]\n'
        '    verdict = "reject" if verdict == "accept" else "accept"\n'
        "    return verdict, reasons, raw[:500]\n",
    )
    outage = (
        '        return "unavailable", {\n'
        '            "verdict": "unavailable",\n'
        '            "reasons": ["review-unavailable"],\n'
        '            "raw_tail": redact(detail)[:500],\n'
        "        }\n"
    )
    outage_accept = (
        '        return "accept", {\n'
        '            "verdict": "accept",\n'
        '            "reasons": ["review-unavailable"],\n'
        '            "raw_tail": redact(detail)[:500],\n'
        "        }\n"
    )
    outage_reject = (
        '        return "reject", {\n'
        '            "verdict": "reject",\n'
        '            "reasons": ["review-unparseable"],\n'
        '            "raw_tail": redact(detail)[:500],\n'
        "        }\n"
    )
    drop_diff = (
        '        % (redact(feedback or ""), shown)\n',
        '        % (redact(feedback or ""), "")\n',
    )
    drop_tail = (
        '    return "gate failed: %s\\n%s" % (why, tail)\n',
        '    return "gate failed: %s\\n%s" % (why, "")\n',
    )
    size_line = '        "ok": files_n <= max_files and lines_n <= max_lines,\n'
    allow = (
        "    outside = [path for path in paths if not _protected(path, patterns)]\n",
        "    outside = []\n",
    )
    stage_argv = (
        "        argv = [\n"
        '            "add",\n'
        '            "-A",\n'
        '            "-f",\n'
        '            "--",\n'
        '            *(":(literal)%s" % rel for rel in wanted),\n'
        '            ":!tmp",\n'
        '            ":!**/__pycache__",\n'
        '            ":!**/*.pyc",\n'
        '            ":!.pytest_cache",\n'
        '            ":!**/.pytest_cache",\n'
        "        ]\n",
        '        argv = ["add", "-A", "-f"]\n',
    )
    stage_check = (
        "    if set(staged) != set(wanted):\n",
        "    if False and set(staged) != set(wanted):\n",
    )
    no_change = (
        "                feedback = _no_change_feedback(tests_after)\n"
        '                if _can_retry(args.review, attempts_used, max_attempts, "no-change"):\n',
        "                feedback = _no_change_feedback(tests_after)\n"
        '                if tests_after.get("started") and tests_after.get("exit") == 0:\n'
        '                    status, reason, exit_code = "PASS", "ok", EXIT_OK\n'
        "                    commit_ready = True\n"
        "                    break\n"
        '                if _can_retry(args.review, attempts_used, max_attempts, "no-change"):\n',
    )
    attempts = (
        "        def _record_attempt(number, t0, mem_snap, attempt_status, attempt_reason, checks, model_review, diff_stats, diff_text):\n"
        "            if not args.review:\n"
        "                return\n",
        "        def _record_attempt(number, t0, mem_snap, attempt_status, attempt_reason, checks, model_review, diff_stats, diff_text):\n"
        "            if True:\n"
        "                return\n",
    )
    stub = (
        '    if os.environ.get("PFY_LOCAL_BUILD_TEST_SEAM") != "1":\n'
        "        return []\n",
        "",
    )
    return [
        _m("R1", "review skipped", "", review_off[0], review_off[1]),
        _m("R2", "verdict inverted", "", invert[0], invert[1]),
        _m("R3", "reviewer outage treated as accept", "", outage, outage_accept),
        _m("R4", "reviewer outage treated as reject", "M4", outage, outage_reject),
        _m("R5", "retry prompt missing previous diff", "M7", drop_diff[0], drop_diff[1]),
        _m("R6", "missing gate tail in feedback", "", drop_tail[0], drop_tail[1]),
        _m("R7", "file cap off by one", "", size_line, '        "ok": files_n <= (max_files + 1) and lines_n <= max_lines,\n'),
        _m("R8", "line cap off by one", "", size_line, '        "ok": files_n <= max_files and lines_n <= (max_lines + 1),\n'),
        _m("R9", "size cap removed", "", size_line, '        "ok": True,\n'),
        _m("R10", "allow list ignored", "", allow[0], allow[1]),
        Mutant("R11", "git add -A -f scope check bypassed", "", (stage_argv, stage_check)),
        _m("R12", "no-change counted as PASS", "", no_change[0], no_change[1]),
        _m("R13", "attempts not recorded", "", attempts[0], attempts[1]),
        _m("R14", "stub env read in production", "", stub[0], stub[1]),
    ]


CATALOG = _catalog()


def apply_text(text, mutant):
    updated = text
    for old, new in mutant.replacements:
        count = updated.count(old)
        if count != 1:
            raise ApplyError("%s anchor count %d" % (mutant.id, count))
        updated = updated.replace(old, new, 1)
    if updated == text:
        raise ApplyError("%s replacement did not change the file" % mutant.id)
    return updated


def review_modules(repo):
    names = ["tests.test_pfy_build_local_review", "tests.test_pfy_build_local"]
    for path in sorted((repo / "tests").glob("test_pfy_build_local_*.py")):
        mod = "tests." + path.stem
        if mod not in names:
            names.append(mod)
    return names


def assert_throwaway(dest, worktree):
    root = (worktree / "tmp").resolve()
    try:
        dest_r = dest.resolve()
    except OSError:
        dest_r = dest.absolute()
    if dest_r != root and root not in dest_r.parents:
        raise RuntimeError("clone must live under %s" % root)
    if dest_r == worktree.resolve():
        raise RuntimeError("refusing to clone over the worktree")


def make_clone(source, dest):
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["git", "clone", "--local", "--quiet", str(source), str(dest)],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        detail = ((proc.stderr or "") + (proc.stdout or ""))[-500:]
        raise RuntimeError("git clone failed: %s" % detail.strip())


def _kill_group(pid):
    try:
        os.killpg(pid, signal.SIGTERM)
    except OSError:
        return
    time.sleep(0.2)
    try:
        os.killpg(pid, signal.SIGKILL)
    except OSError:
        return


def run_suite(repo, modules, exclude, timeout_s, tmpdir):
    tmpdir.mkdir(parents=True, exist_ok=True)
    driver = tmpdir / "mut-driver.py"
    driver.write_text(DRIVER, encoding="utf-8")
    log_path = tmpdir / "suite.log"
    env = os.environ.copy()
    env["TMPDIR"] = str(tmpdir)
    env["PYTHONPATH"] = str(repo)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    env["PFY_MUT_MODULES"] = ",".join(modules)
    env["PFY_MUT_EXCLUDE"] = ",".join(exclude)
    cmd = ["nice", "-n", "19", "python3", str(driver)]
    started = time.monotonic()
    proc = subprocess.Popen(
        cmd,
        cwd=str(repo),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    timed_out = False
    try:
        output, _ = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_group(proc.pid)
        try:
            output, _ = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            output = ""
    seconds = round(time.monotonic() - started, 3)
    output = output or ""
    log_path.write_text(output, encoding="utf-8")
    excluded = re.findall(r"^EXCLUDED (\S+)", output, re.M)
    fail = re.search(r"^(FAIL|ERROR): (\S+)", output, re.M)
    first = ""
    if fail:
        first = "%s: %s" % (fail.group(1), fail.group(2))
    tail = output[-1500:]
    if timed_out:
        status = "timeout"
        code = 124
    elif proc.returncode == 0:
        status = "pass"
    elif proc.returncode is None:
        status = "error"
        code = 1
    else:
        status = "fail"
        code = proc.returncode
    if not timed_out and proc.returncode is not None:
        code = proc.returncode
    return {
        "status": status,
        "returncode": code,
        "seconds": seconds,
        "first_failure": first,
        "excluded": excluded,
        "tail": tail,
        "log": str(log_path),
    }


def judge(applied, suite):
    if not applied:
        return "not-applied"
    if suite is None:
        return "error"
    status = suite.get("status")
    if status == "fail":
        return "killed"
    if status == "pass":
        return "survived"
    if status == "timeout":
        return "timeout"
    return "error"


def _hashes(paths):
    found = {}
    for path in paths:
        if path.is_file():
            found[path] = path.read_bytes()
    return found


def _same(before):
    for path, data in before.items():
        if not path.is_file() or path.read_bytes() != data:
            return False
    return True


def write_mutant(clone_file, protect_files, mutant, pristine):
    clone_r = clone_file.resolve()
    for path in protect_files:
        if path.is_file() and path.resolve() == clone_r:
            raise RuntimeError("refusing to mutate a protected file: %s" % path)
    before = _hashes(protect_files)
    try:
        updated = apply_text(pristine, mutant)
    except ApplyError:
        if not _same(before):
            raise RuntimeError("protected file changed while applying %s" % mutant.id)
        raise
    clone_file.write_text(updated, encoding="utf-8")
    if not _same(before):
        clone_file.write_text(pristine, encoding="utf-8")
        raise RuntimeError("protected file changed while writing %s" % mutant.id)
    return updated


def check_anchors(repo, mutants=None):
    mutants = list(mutants or CATALOG)
    path = repo / RUNNER_REL
    text = path.read_text(encoding="utf-8")
    before = path.read_bytes()
    problems = []
    for mutant in mutants:
        try:
            apply_text(text, mutant)
        except ApplyError as exc:
            problems.append(str(exc))
    if path.read_bytes() != before:
        problems.append("runner bytes changed during anchor check")
    for item in problems:
        print(item, file=sys.stderr)
    if not problems:
        print("anchors %d ok" % len(mutants))
    return 1 if problems else 0


def render_report(meta, rows):
    lines = [
        "# Mutation report: local review loop",
        "",
        "Source: `%s` %s" % (meta.get("commit", ""), meta.get("source", "")),
        "Baseline: %s" % meta.get("baseline", ""),
        "Modules: %s" % ", ".join(meta.get("modules") or []),
        "Red base modules skipped: %s" % (", ".join(meta.get("red_modules") or []) or "none"),
        "Model audit: %s" % meta.get("audit", MODEL_AUDIT),
        "Excluded tests: %s" % (", ".join(meta.get("excluded") or []) or "none"),
        "",
        "| id | reviewer | mutant | result | seconds | first failure |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| %s | %s | %s | %s | %s | %s |"
            % (
                row.get("id", ""),
                row.get("reviewer", ""),
                row.get("title", ""),
                row.get("result", ""),
                row.get("seconds", ""),
                (row.get("first_failure") or "").replace("|", "/"),
            )
        )
    killed = [row["id"] for row in rows if row.get("result") == "killed"]
    survived = [row["id"] for row in rows if row.get("result") == "survived"]
    other = [row["id"] for row in rows if row.get("result") not in ("killed", "survived")]
    lines.extend(
        [
            "",
            "Kills before: %d (%s)" % (len(killed), ", ".join(killed) or "none"),
            "Survivors before: %d (%s)" % (len(survived), ", ".join(survived) or "none"),
            "Kills after: pending until survivor tests or a review-fix2 re-run",
            "Survivors left: %d (%s)" % (len(survived), ", ".join(survived) or "none"),
            "Not killed or survived: %s" % (", ".join(other) or "none"),
            "",
        ]
    )
    return "\n".join(lines)


def run_campaign(
    source_repo,
    clone_dest,
    worktree,
    mutants,
    modules,
    exclude,
    timeout_s,
    tmpdir,
    report_path,
    protect_files,
    runner_rel=RUNNER_REL,
    audit=MODEL_AUDIT,
):
    assert_throwaway(clone_dest, worktree)
    for path in protect_files:
        if path.resolve() == (clone_dest / runner_rel).resolve():
            raise RuntimeError("protected path is the clone runner")
    protected_before = _hashes(protect_files)
    make_clone(source_repo, clone_dest)
    clone_file = clone_dest / runner_rel
    if not clone_file.is_file():
        raise RuntimeError("clone has no %s" % runner_rel)
    pristine = clone_file.read_text(encoding="utf-8")
    commit = ""
    sha = subprocess.run(
        ["git", "-C", str(source_repo), "rev-parse", "--short", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if sha.returncode == 0:
        commit = (sha.stdout or "").strip()
    red_modules = []
    usable = list(modules)
    baseline = run_suite(clone_dest, modules, exclude, timeout_s, tmpdir / "baseline")
    baseline_label = baseline["status"]
    if baseline["status"] != "pass":
        usable = []
        for mod in modules:
            one = run_suite(clone_dest, [mod], exclude, timeout_s, tmpdir / ("base-" + mod.split(".")[-1]))
            if one["status"] == "pass":
                usable.append(mod)
            else:
                red_modules.append(mod)
        if usable:
            again = run_suite(clone_dest, usable, exclude, timeout_s, tmpdir / "baseline-usable")
            baseline_label = "red-base-trimmed:%s" % again["status"]
            if again["status"] != "pass":
                usable = []
                baseline_label = "red-base"
        else:
            baseline_label = "red-base"
    rows = []
    excluded_seen = list(baseline.get("excluded") or [])
    try:
        for mutant in mutants:
            clone_file.write_text(pristine, encoding="utf-8")
            row = {
                "id": mutant.id,
                "title": mutant.title,
                "reviewer": mutant.reviewer,
                "result": "",
                "seconds": "",
                "first_failure": "",
            }
            if not usable:
                row["result"] = "skipped-red-base"
                rows.append(row)
                print("%s skipped-red-base" % mutant.id, flush=True)
                continue
            try:
                write_mutant(clone_file, protect_files, mutant, pristine)
            except ApplyError as exc:
                row["result"] = "not-applied"
                row["first_failure"] = str(exc)
                rows.append(row)
                print("%s not-applied %s" % (mutant.id, exc), flush=True)
                continue
            suite = run_suite(clone_dest, usable, exclude, timeout_s, tmpdir / mutant.id)
            excluded_seen.extend(suite.get("excluded") or [])
            row["result"] = judge(True, suite)
            row["seconds"] = suite.get("seconds", "")
            row["first_failure"] = suite.get("first_failure") or ""
            if row["result"] == "timeout":
                row["first_failure"] = row["first_failure"] or "suite timeout"
            rows.append(row)
            print(
                "%s %s %ss %s" % (mutant.id, row["result"], row["seconds"], row["first_failure"]),
                flush=True,
            )
    finally:
        clone_file.write_text(pristine, encoding="utf-8")
        if not _same(protected_before):
            raise RuntimeError("a protected file changed during the campaign")
    seen = []
    for item in excluded_seen:
        if item not in seen:
            seen.append(item)
    meta = {
        "commit": commit,
        "source": str(source_repo),
        "baseline": baseline_label,
        "modules": usable,
        "red_modules": red_modules,
        "audit": audit,
        "excluded": seen,
    }
    report = render_report(meta, rows)
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        results = {"meta": meta, "rows": rows}
        report_path.with_suffix(".json").write_text(
            json.dumps(results, indent=2) + "\n",
            encoding="utf-8",
        )
    return {"meta": meta, "rows": rows, "report": report}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Mutation-test the local review loop on a clone.")
    parser.add_argument("--run", action="store_true", help="clone and run the suite (default is anchor check only)")
    parser.add_argument("--check-anchors", action="store_true", help="check catalog anchors and exit")
    parser.add_argument("--timeout", type=int, default=420, help="seconds per suite run")
    parser.add_argument("--ids", default="", help="comma-separated mutant ids (default all)")
    parser.add_argument("--repo", default=str(REPO), help="source repo to clone")
    parser.add_argument("--report", default=str(REPO / "eval" / "mutation-1031" / "review" / "REPORT.md"))
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    if not args.run or args.check_anchors:
        return check_anchors(repo)
    wanted = [item for item in args.ids.split(",") if item]
    mutants = [item for item in CATALOG if not wanted or item.id in wanted]
    if wanted and len(mutants) != len(wanted):
        print("unknown mutant id", file=sys.stderr)
        return 2
    worktree = REPO
    clone_dest = SCRATCH / "review-clone"
    tmpdir = SCRATCH / "run"
    protect = [worktree / RUNNER_REL]
    os.environ["TMPDIR"] = str(SCRATCH / "tmpdir")
    (SCRATCH / "tmpdir").mkdir(parents=True, exist_ok=True)
    outcome = run_campaign(
        source_repo=repo,
        clone_dest=clone_dest,
        worktree=worktree,
        mutants=mutants,
        modules=review_modules(repo),
        exclude=list(EXCLUDE_MODEL_TESTS),
        timeout_s=args.timeout,
        tmpdir=tmpdir,
        report_path=Path(args.report),
        protect_files=protect,
    )
    survived = [row["id"] for row in outcome["rows"] if row["result"] == "survived"]
    print("survivors %s" % (",".join(survived) or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
