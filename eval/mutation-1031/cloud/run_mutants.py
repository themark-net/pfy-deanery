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
        "old": "        for pg in kids:\n"
        "            _signal_pgid(pg, signal.SIGTERM)\n",
        "new": "        for pg in kids:\n"
        "            if False:\n"
        "                _signal_pgid(pg, signal.SIGTERM)\n",
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


# Wave-5 mutants. Kept off MUTANTS so the wave-3 harness test still sees C1-C16 only.
# Each old string must match the current runner once. Applied one at a time to a copy.
CLOUD2_MUTANTS: list[dict[str, str]] = [
    {
        "id": "C17",
        "title": "writable-test allow list ignored",
        "old": "        if _writable_test(rel, allowed):\n            continue\n",
        "new": "        if False and _writable_test(rel, allowed):\n            continue\n",
    },
    {
        "id": "C18",
        "title": "every base test treated as writable",
        "old": "def _writable_test(rel: str, patterns: list[str]) -> bool:\n"
        "    rel = _norm_rel(rel)\n"
        '    if not rel or rel.startswith("../") or rel == ".." or "/../" in "/%s/" % rel:\n'
        "        return False\n"
        "    name = Path(rel).name\n",
        "new": "def _writable_test(rel: str, patterns: list[str]) -> bool:\n"
        "    rel = _norm_rel(rel)\n"
        '    if not rel or rel.startswith("../") or rel == ".." or "/../" in "/%s/" % rel:\n'
        "        return False\n"
        "    return True\n"
        "    name = Path(rel).name\n",
    },
    {
        "id": "C19",
        "title": "writable-test match is exact, globs do not apply",
        "old": "        if pat and (fnmatch_path(rel, pat) or fnmatch_path(name, pat)):\n"
        "            return True\n",
        "new": "        if pat and (rel == pat or name == pat):\n"
        "            return True\n",
    },
    {
        "id": "C20",
        "title": "git add drops the literal pathspec",
        "old": '        added = _git(self.worktree, ["add", "--", *[":(literal)%s" % path for path in paths]])\n',
        "new": '        added = _git(self.worktree, ["add", "--", *paths])\n',
    },
    {
        "id": "C21",
        "title": "git add uses a glob pathspec",
        "old": '        added = _git(self.worktree, ["add", "--", *[":(literal)%s" % path for path in paths]])\n',
        "new": '        added = _git(self.worktree, ["add", "--", *[":(glob)%s" % path for path in paths]])\n',
    },
    {
        "id": "C22",
        "title": "archive recheck skipped",
        "old": '        reason, tail = self.recheck_sha(sha or "")\n'
        "        self.recheck_tail = tail\n"
        "        if reason:\n",
        "new": '        reason, tail = None, ""\n'
        "        self.recheck_tail = tail\n"
        "        if reason:\n",
    },
    {
        "id": "C23",
        "title": "archive recheck timeout counted as a pass",
        "old": '            if again.get("aborted") == "timeout":\n'
        '                return "timeout", tail\n',
        "new": '            if again.get("aborted") == "timeout":\n'
        "                return None, tail\n",
    },
    {
        "id": "C24",
        "title": "archive recheck failure does not retry",
        "old": '            if err == "commit-recheck-failed" and number < self.max_attempts:\n',
        "new": '            if err == "commit-recheck-failed" and False and number < self.max_attempts:\n',
    },
    {
        "id": "C25",
        "title": "protected path check skipped",
        "old": "            protected_hits = [path for path in changed if _protected(path)]\n"
        "            if protected_hits:\n",
        "new": "            protected_hits = [path for path in changed if _protected(path)]\n"
        "            if False and protected_hits:\n",
    },
    {
        "id": "C26",
        "title": "protected ** no longer matches zero directories",
        "old": '    collapsed = pat\n    while "/**/" in collapsed:\n',
        "new": '    collapsed = pat\n    while False and "/**/" in collapsed:\n',
    },
    {
        "id": "C27",
        "title": "protected globs do not match the file basename",
        "old": "def _glob_match(rel: str, name: str, pat: str) -> bool:\n"
        "    if fnmatch_path(rel, pat) or fnmatch_path(name, pat):\n"
        "        return True\n",
        "new": "def _glob_match(rel: str, name: str, pat: str) -> bool:\n"
        "    if fnmatch_path(rel, pat):\n"
        "        return True\n",
    },
    {
        "id": "C28",
        "title": "assignment redaction never fires",
        "old": '        if explicit or name.isupper() or looks or value == "[redacted]":\n'
        '            return name + sep + "[redacted]"\n'
        "        return match.group(0)\n",
        "new": '        if False and (explicit or name.isupper() or looks or value == "[redacted]"):\n'
        '            return name + sep + "[redacted]"\n'
        "        return match.group(0)\n",
    },
    {
        "id": "C29",
        "title": "assignment redaction hides fixture ids",
        "old": '        if explicit or name.isupper() or looks or value == "[redacted]":\n'
        '            return name + sep + "[redacted]"\n'
        "        return match.group(0)\n",
        "new": '        if True or explicit or name.isupper() or looks or value == "[redacted]":\n'
        '            return name + sep + "[redacted]"\n'
        "        return match.group(0)\n",
    },
    {
        "id": "C30",
        "title": "pem block redaction skipped",
        "old": '    text = _PEM.sub("[redacted-private-key]", text)\n',
        "new": "    text = text\n",
    },
    {
        "id": "C31",
        "title": "product gate keeps secret env vars",
        "old": "            ):\n"
        "                env.pop(key, None)\n"
        "        # Recheck runs with cwd set to the extract. A TMPDIR left on the\n"
        "        # build worktree makes TemporaryDirectory paths fail relative_to\n"
        "        # on that extract and pass on the worktree.\n"
        '        gate_tmp = where / "tmp"\n'
        "        try:\n"
        "            gate_tmp.mkdir(parents=True, exist_ok=True)\n"
        '            env["TMPDIR"] = str(gate_tmp)\n'
        "        except OSError:\n"
        "            pass\n"
        "        status, code, out, err = run_command(\n",
        "new": "            ):\n"
        "                pass\n"
        "        # Recheck runs with cwd set to the extract. A TMPDIR left on the\n"
        "        # build worktree makes TemporaryDirectory paths fail relative_to\n"
        "        # on that extract and pass on the worktree.\n"
        '        gate_tmp = where / "tmp"\n'
        "        try:\n"
        "            gate_tmp.mkdir(parents=True, exist_ok=True)\n"
        '            env["TMPDIR"] = str(gate_tmp)\n'
        "        except OSError:\n"
        "            pass\n"
        "        status, code, out, err = run_command(\n",
    },
    {
        "id": "C32",
        "title": "uppercase env name is not enough to redact",
        "old": '        if explicit or name.isupper() or looks or value == "[redacted]":\n',
        "new": '        if explicit or looks or value == "[redacted]":\n',
    },
    {
        "id": "C33",
        "title": "recovery line stays off the terminal",
        "old": "            if self.recovery:\n"
        "                # The receipt holds the same line. Print it so the terminal\n"
        "                # says what to run next without opening the json.\n"
        "                print(self.recovery, file=sys.stderr)\n",
        "new": "            if False and self.recovery:\n"
        "                # The receipt holds the same line. Print it so the terminal\n"
        "                # says what to run next without opening the json.\n"
        "                print(self.recovery, file=sys.stderr)\n",
    },
    {
        "id": "C34",
        "title": "gate timeout recovery says grok timed out",
        "old": '        if (detail or "").strip() == "gate":\n'
        "            return (\n"
        '                "Mark: the gate timed out. Rerun with a longer --timeout. "\n'
        '                "Then rerun ./pfy build %s."\n'
        "                % quoted_timeout\n"
        "            )\n",
        "new": '        if False and (detail or "").strip() == "gate":\n'
        "            return (\n"
        '                "Mark: the gate timed out. Rerun with a longer --timeout. "\n'
        '                "Then rerun ./pfy build %s."\n'
        "                % quoted_timeout\n"
        "            )\n",
    },
    {
        "id": "C35",
        "title": "missing base is a usage error",
        "old": "    except BaseMissing as exc:\n"
        "        return missing_base(args, repo, exc.ref)\n",
        "new": "    except BaseMissing as exc:\n"
        "        _print_usage()\n"
        '        print("base ref not found: %s" % exc.ref, file=sys.stderr)\n'
        "        return EXIT_USAGE\n",
    },
    {
        "id": "C36",
        "title": "HEAD mismatch silently builds origin/main",
        "old": "    if main_sha != head_sha:\n"
        "        raise UsageError(\n"
        '            "HEAD %s is not origin/main %s. Pass --base origin/main or --base HEAD."\n'
        "            % (head_sha[:12], main_sha[:12])\n"
        "        )\n"
        '    return "origin/main", main_sha\n',
        "new": "    if main_sha != head_sha:\n"
        '        return "origin/main", main_sha\n'
        '    return "origin/main", main_sha\n',
    },
    {
        "id": "C37",
        "title": "absent origin/main is an error instead of HEAD",
        "old": "    if probe.returncode != 0:\n"
        '        return "HEAD", head_sha\n',
        "new": "    if probe.returncode != 0:\n"
        '        raise UsageError("origin/main is absent. Pass --base HEAD.")\n',
    },
    {
        "id": "C38",
        "title": "timeout does not kill the grok process group",
        "old": "        except subprocess.TimeoutExpired:\n"
        "            _kill_pgid(proc.pid)\n"
        "            try:\n"
        "                out, err = proc.communicate(timeout=5)\n",
        "new": "        except subprocess.TimeoutExpired:\n"
        "            try:\n"
        "                out, err = proc.communicate(timeout=5)\n",
    },
    {
        "id": "C39",
        "title": "review timeout is a review reject",
        "old": '                if review_status == "timeout":\n'
        "                    self._undo_commit(keep_edits=True)\n"
        "                    if last_reject is not None:\n"
        "                        return as_reject(number, output, True)\n"
        '                    self.record(number, "TIMEOUT", "timeout", output)\n'
        '                    return self.fail("TIMEOUT", "timeout", EXIT_TIMEOUT, "")\n',
        "new": '                if review_status == "timeout":\n'
        "                    self._undo_commit(keep_edits=True)\n"
        '                    self.record(number, "PASS-REJECTED", "review-rejected", output)\n'
        "                    if number < self.max_attempts:\n"
        "                        continue\n"
        '                    return self.fail("FAIL", "review-rejected", EXIT_FAIL, "")\n',
    },
    {
        "id": "C40",
        "title": "before-gate timeout still starts grok",
        "old": '        if (self.gate_before or {}).get("aborted") == "timeout":\n'
        '            return self._gate_timeout_fail(0, str((self.gate_before or {}).get("tail") or ""))\n',
        "new": '        if False and (self.gate_before or {}).get("aborted") == "timeout":\n'
        '            return self._gate_timeout_fail(0, str((self.gate_before or {}).get("tail") or ""))\n',
    },
    {
        "id": "C41",
        "title": "timeout of zero is accepted",
        "old": "    if args.timeout <= 0:\n"
        '        raise UsageError("--timeout must be > 0")\n',
        "new": "    if args.timeout < 0:\n"
        '        raise UsageError("--timeout must be > 0")\n',
    },
    {
        "id": "C42",
        "title": "failure recovery line is empty",
        "old": "def failure_recovery(reason: str, task: str, detail: str = \"\") -> str:\n"
        '    """Non-empty recovery for every terminal failure. PASS stays empty."""\n'
        '    if reason == "rate-limit":\n',
        "new": "def failure_recovery(reason: str, task: str, detail: str = \"\") -> str:\n"
        '    """Non-empty recovery for every terminal failure. PASS stays empty."""\n'
        '    return ""\n'
        '    if reason == "rate-limit":\n',
    },
    {
        "id": "C43",
        "title": "missing-base recovery omits the ref",
        "old": '    if detail == "missing-ref":\n'
        "        return (\n"
        '            "Mark: base ref %s is not in this repo, so no worktree was created. "\n'
        '            "Fetch it or pass --base with a ref that exists, then rerun ./pfy build %s. "\n'
        '            "The caller checkout was not changed."\n'
        "            % (ref, quoted)\n"
        "        )\n",
        "new": '    if detail == "missing-ref":\n'
        "        return (\n"
        '            "Mark: base ref is not in this repo, so no worktree was created. "\n'
        '            "Fetch it or pass --base with a ref that exists, then rerun ./pfy build %s. "\n'
        '            "The caller checkout was not changed."\n'
        "            % quoted\n"
        "        )\n",
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
    for pattern in ("test_mut_cloud_*.py", "test_mut_cloud2_*.py"):
        for path in sorted(tests.glob(pattern)):
            if path.stem.endswith("_harness"):
                continue
            module = "tests.%s" % path.stem
            if module not in names:
                names.append(module)
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
    """Prefer the unittest failure over the runner's own FAIL: reason line.

    A passing recovery test prints `FAIL: commit-recheck-failed`. That line
    is not the kill. `FAIL: test_...` is.
    """
    preferred: list[str] = []
    fallback: list[str] = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("FAIL: test_", "ERROR: test_", "AssertionError", "Traceback")):
            preferred.append(stripped)
        elif stripped.startswith(("FAIL:", "ERROR:", "Ran ")):
            fallback.append(stripped)
    if preferred:
        return scrub(preferred[0])[:240]
    if fallback:
        return scrub(fallback[0])[:240]
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
    catalog = MUTANTS + CLOUD2_MUTANTS
    if args.list:
        print(format_table([{"id": item["id"], "title": item["title"], "status": "listed", "seconds": "", "detail": ""} for item in catalog]))
        return 0
    selected = catalog
    if args.mutant:
        wanted = set(args.mutant)
        selected = [item for item in catalog if item["id"] in wanted]
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
