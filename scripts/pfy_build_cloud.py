#!/usr/bin/env python3
"""pfy build "<task>": daily cloud Grok build.

The checkout this process was started from is never switched, reset, stashed,
or committed. Work happens in a detached git worktree under <repo>/tmp/.
Nothing is pushed and no PR is opened. This runner does not read auth.json
and does not start a local model.

Exit codes:
  0  PASS, or a clean --dry-run, or --reap
  1  FAIL (review reject, no-change spent, scope mismatch, unauthenticated,
        interrupted, gate spent, worktree-failed). A base ref that cannot
        be checked out is worktree-failed, not usage.
  2  usage (missing task or repo)
  3  TIMEOUT (grok)
  4  BLOCKED (rate-limit)

Receipt schema: pfy-cloud-build/1

Failure class comes from pfylib.build_preflight.classify_cloud_failure.
This runner does not keep a second copy of those phrases.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from pfylib.build_phase_clock import PhaseClock, install_build_phases  # noqa: E402
from pfylib.build_preflight import classify_cloud_failure  # noqa: E402

_NOT_SIGNED_IN = re.compile(r"not signed in", re.IGNORECASE)


def classify_runner_failure(code: int, stdout: str, stderr: str) -> str:
    """Preflight class, plus the logged-out line it does not name.

    `classify_cloud_failure` treats exit 0 as other, and its auth phrases
    do not include "Not signed in". A successful reply that only mentions
    auth.json stays other.
    """
    kind = classify_cloud_failure(code, stdout, stderr)
    if kind != "other":
        return kind
    if _NOT_SIGNED_IN.search("%s\n%s" % (stdout or "", stderr or "")):
        return "unauthenticated"
    return kind


EXIT_OK = 0
EXIT_FAIL = 1
EXIT_USAGE = 2
EXIT_TIMEOUT = 3
EXIT_BLOCKED = 4

SCHEMA = "pfy-cloud-build/1"
DEFAULT_TEST_CMD = "python3 -m unittest discover -s tests -t ."
DEFAULT_TIMEOUT = 1200.0
DEFAULT_RETRIES = 2
AUTHOR_NAME = "pfy-cloud-build"
AUTHOR_EMAIL = "pfy-cloud-build@localhost"
KILL_GRACE_SECONDS = 2.0
DIFF_CAP = 12000
TAIL_CAP = 4000

IMPLEMENT_MARKER = "PFY-CLOUD-IMPLEMENT"
REVIEW_MARKER = "PFY-CLOUD-REVIEW"

DEFAULT_PROTECT = (
    "auth.json",
    ".env",
    "*.pem",
    "pipelines/dogfood/**/grok-home/**",
)

HELP_TEXT = """\
Daily cloud build.

  ./pfy build "<task>"

-p is the jev dogfood wrap (./pfy build -p "<prompt>").
--local is the opt-in fallback (./pfy build --local "<task>").
"""

_PEM = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
    re.DOTALL,
)
_BEARER = re.compile(r"(?i)(bearer\s+)([A-Za-z0-9._\-]{8,})")
_SK = re.compile(r"\b(?:sk|ghp)_[A-Za-z0-9_\-]{8,}\b", re.IGNORECASE)
_AKIA = re.compile(r"\bAKIA[0-9A-Z]{16}\b", re.IGNORECASE)
_XAI = re.compile(r"\bxai-[A-Za-z0-9]{6,}\b", re.IGNORECASE)
_SECRET_EQ = re.compile(
    r"(?i)\b([A-Za-z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD|PASSWD)[A-Za-z0-9_]*)\s*([:=])\s*(\S+)"
)
_VERDICT = re.compile(r"verdict\s*:\s*[\"']?(accept|reject)\b", re.IGNORECASE)


class UsageError(Exception):
    pass


class BaseMissing(Exception):
    def __init__(self, ref: str) -> None:
        super().__init__(ref)
        self.ref = ref


class State:
    def __init__(self) -> None:
        self.interrupted = False
        self.pgid: int | None = None
        self.agent_pgid: int | None = None
        # Every live child, so a signal during overlapped gates kills all of them.
        self.child_pgids: set[int] = set()
        self.children_lock = threading.Lock()


def _track_child(state: State, pgid: int, present: bool) -> None:
    if not pgid or pgid <= 0:
        return
    with state.children_lock:
        if present:
            state.child_pgids.add(pgid)
            state.pgid = pgid
            state.agent_pgid = pgid
        else:
            state.child_pgids.discard(pgid)
            if state.pgid == pgid:
                state.pgid = next(iter(state.child_pgids), None)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _slug(text: str) -> str:
    raw = re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")
    raw = (raw[:40] or "task").strip("-")
    return raw or "task"


def commit_subject(task_text: str) -> str:
    """Cloud commit subject: whole words, at most 72 characters.

    Dogfood2 cut the task at 72 characters and stopped mid-word, so git log
    showed a fragment. The unread words stay in the commit body.
    """
    flat = " ".join((task_text or "").split())
    if not flat:
        return "task"
    if len(flat) <= 72:
        return flat
    cut = flat[:69]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    cut = cut.rstrip()
    if not cut:
        cut = flat[:69].rstrip()
    return (cut or "task") + "..."


def redact(text: str) -> str:
    if not text:
        return ""

    def _eq(match: re.Match) -> str:
        # Fail: every name containing KEY or TOKEN hid fixture ids such as
        # user_key=list-user. Recover: keep a short lowercase fixture value.
        # Still hide an uppercase env name, a password or secret name, and a
        # value that is long or mixes letters and digits.
        name, sep, value = match.group(1), match.group(2), match.group(3)
        lower = name.lower()
        explicit = any(word in lower for word in ("password", "passwd", "secret"))
        mixed = any(ch.isalpha() for ch in value) and any(ch.isdigit() for ch in value)
        looks = len(value) >= 32 or (len(value) >= 8 and mixed)
        if explicit or name.isupper() or looks or value == "[redacted]":
            return name + sep + "[redacted]"
        return match.group(0)

    text = _PEM.sub("[redacted-private-key]", text)
    text = text.replace("BEGIN PRIVATE KEY", "[redacted-private-key]")
    text = text.replace("END PRIVATE KEY", "[redacted-private-key]")
    text = _BEARER.sub(lambda match: match.group(1) + "[redacted]", text)
    text = _SK.sub("[redacted]", text)
    text = _AKIA.sub("[redacted]", text)
    text = _XAI.sub("[redacted]", text)
    text = _SECRET_EQ.sub(_eq, text)
    return text


def redact_obj(value):
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [redact_obj(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_obj(item) for key, item in value.items()}
    return value


def _git(repo: Path, args: list[str], timeout: float = 60) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_AUTHOR_NAME"] = AUTHOR_NAME
    env["GIT_AUTHOR_EMAIL"] = AUTHOR_EMAIL
    env["GIT_COMMITTER_NAME"] = AUTHOR_NAME
    env["GIT_COMMITTER_EMAIL"] = AUTHOR_EMAIL
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def resolve_repo(raw: str | None) -> Path:
    start = Path(raw).resolve() if raw else Path.cwd()
    if not start.exists():
        raise UsageError("repo path does not exist: %s" % start)
    probe = start if start.is_dir() else start.parent
    proc = _git(probe, ["rev-parse", "--show-toplevel"])
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        raise UsageError("not a git repo: %s" % start)
    return Path(proc.stdout.strip()).resolve()


def resolve_base(repo: Path, requested: str | None) -> tuple[str, str]:
    """Pick the commit the worktree is built from.

    Fail: HEAD is a bot branch and origin/main is an older main, and the
    run silently builds main. Recover: exit 2 and ask for --base.
    When the two shas match, origin/main stays the default. When
    origin/main is absent, HEAD stays the default.
    A requested ref that does not resolve raises BaseMissing so the
    caller records worktree-failed instead of a usage error.
    """
    if requested and requested.strip():
        ref = requested.strip()
        sha = _git(repo, ["rev-parse", "--verify", ref])
        if sha.returncode != 0 or not (sha.stdout or "").strip():
            raise BaseMissing(ref)
        return ref, sha.stdout.strip()
    probe = _git(repo, ["rev-parse", "--verify", "--quiet", "origin/main"])
    head = _git(repo, ["rev-parse", "--verify", "HEAD"])
    if head.returncode != 0 or not (head.stdout or "").strip():
        raise BaseMissing("HEAD")
    head_sha = head.stdout.strip()
    if probe.returncode != 0:
        return "HEAD", head_sha
    main_sha = (probe.stdout or "").strip()
    if not main_sha:
        raise BaseMissing("origin/main")
    if main_sha != head_sha:
        raise UsageError(
            "HEAD %s is not origin/main %s. Pass --base origin/main or --base HEAD."
            % (head_sha[:12], main_sha[:12])
        )
    return "origin/main", main_sha


def default_receipt_dir(repo: Path, stamp: str) -> Path:
    return repo / "pipelines" / "dogfood" / "build-cloud" / stamp


def write_receipt(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(redact_obj(payload), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def _norm_rel(path: str) -> str:
    text = (path or "").replace("\\", "/").strip()
    while text.startswith("./"):
        text = text[2:]
    if not text:
        return ""
    normalized = os.path.normpath(text).replace("\\", "/")
    if normalized in ("", "."):
        return ""
    return normalized


def _glob_match(rel: str, name: str, pat: str) -> bool:
    if fnmatch_path(rel, pat) or fnmatch_path(name, pat):
        return True
    if pat.endswith("/**"):
        prefix = pat[:-3].rstrip("/")
        if prefix and (rel == prefix or rel.startswith(prefix + "/")):
            return True
    if "**" not in pat:
        return False
    if fnmatch_path(rel, pat.replace("**", "*")):
        return True
    # ** matches zero directories, so dogfood/**/grok-home also covers dogfood/grok-home.
    collapsed = pat
    while "/**/" in collapsed:
        collapsed = collapsed.replace("/**/", "/", 1)
        if fnmatch_path(rel, collapsed) or fnmatch_path(name, collapsed):
            return True
        if collapsed.endswith("/**"):
            prefix = collapsed[:-3].rstrip("/")
            if prefix and (rel == prefix or rel.startswith(prefix + "/")):
                return True
    return False


def _protected(path: str, patterns: tuple[str, ...] = DEFAULT_PROTECT) -> bool:
    rel = _norm_rel(path)
    if not rel or rel.startswith("../") or rel == ".." or "/../" in "/%s/" % rel:
        return True
    name = Path(rel).name
    for pattern in patterns:
        pat = _norm_rel(pattern)
        if pat and _glob_match(rel, name, pat):
            return True
    return False


def fnmatch_path(path: str, pattern: str) -> bool:
    import fnmatch

    return fnmatch.fnmatch(path, pattern)


def _is_test_path(rel: str) -> bool:
    name = Path(rel).name
    if name.startswith("test_") and name.endswith(".py"):
        return True
    if name.endswith("_test.py"):
        return True
    if rel == "tests" or rel.startswith("tests/") or "/tests/" in ("/" + rel):
        return True
    return False


def _alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _signal_pgid(pgid: int, sig: int) -> None:
    if not pgid or pgid <= 0 or pgid == os.getpgrp():
        return
    try:
        os.killpg(pgid, sig)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def _group_alive(pgid: int) -> bool:
    if not pgid or pgid <= 0:
        return False
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _kill_pgid(pgid: int | None) -> None:
    if not pgid or pgid <= 0 or pgid == os.getpgrp():
        return
    if not _group_alive(pgid):
        return
    _signal_pgid(pgid, signal.SIGTERM)
    deadline = time.monotonic() + KILL_GRACE_SECONDS
    while time.monotonic() < deadline:
        if not _group_alive(pgid):
            return
        time.sleep(0.05)
    _signal_pgid(pgid, signal.SIGKILL)


def _install_signals(state: State) -> None:
    def _handle(signum, _frame):
        state.interrupted = True
        with state.children_lock:
            kids = list(state.child_pgids)
            current = state.pgid
        if current and current not in kids:
            kids.append(current)
        for pg in kids:
            _signal_pgid(pg, signal.SIGTERM)

    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="pfy build",
        description=HELP_TEXT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("task", nargs="*", help='task text for ./pfy build "<task>"')
    parser.add_argument("--repo", default=None, help="git repo to build (default: cwd)")
    parser.add_argument(
        "--base",
        default=None,
        help=(
            "base ref. Required when HEAD is not origin/main. "
            "Default is origin/main when it matches HEAD, else HEAD if origin/main is absent"
        ),
    )
    parser.add_argument("--test-cmd", default=DEFAULT_TEST_CMD, help="gate command")
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="extra attempts after the first (default 2, so 3 total)",
    )
    parser.add_argument("--no-review", action="store_true", help="one attempt, no review call")
    parser.add_argument(
        "--writable-test",
        action="append",
        default=[],
        help="test path the task may edit (repeatable). Other base tests stay hashed",
    )
    parser.add_argument("--receipt-dir", default=None, help="directory for receipt.json")
    parser.add_argument("--dry-run", action="store_true", help="write a receipt and start no grok")
    parser.add_argument("--reap", action="store_true", help="recover a cloud pid with no receipt")
    parser.add_argument("--keep-worktree", action="store_true", help="keep the worktree after the run")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="seconds for one grok call")
    parser.add_argument(
        "--grok-cmd",
        default=None,
        help="grok binary (default: env PFY_BUILD_GROK, else grok on PATH)",
    )
    args = parser.parse_args(argv)
    if args.retries < 0:
        raise UsageError("--retries must be >= 0")
    if args.timeout <= 0:
        raise UsageError("--timeout must be > 0")
    if len(args.task) > 1:
        raise UsageError('usage: ./pfy build "<task>"')
    args.task_text = args.task[0] if args.task else ""
    if not args.grok_cmd:
        args.grok_cmd = os.environ.get("PFY_BUILD_GROK") or ""
    return args


def _print_usage() -> None:
    print(HELP_TEXT, file=sys.stderr)
    print('usage: ./pfy build "<task>"', file=sys.stderr)


def _summary(status: str, reason: str, branch: str | None, receipt: Path) -> str:
    if status == "PASS":
        return "PASS ok branch=%s receipt=%s" % (branch, receipt)
    return "%s %s branch=%s receipt=%s" % (status, reason, branch or "none", receipt)


def resolve_grok(args) -> str | None:
    cmd = (args.grok_cmd or "").strip()
    if cmd:
        if os.path.sep in cmd or cmd.startswith("."):
            path = Path(cmd)
            if path.is_file() and os.access(path, os.X_OK):
                return str(path)
            return None
        return shutil.which(cmd)
    return shutil.which("grok")


def rate_recovery(task: str) -> str:
    return "./pfy build --local %s" % shlex.quote(task)


def auth_recovery(task: str) -> str:
    return "run grok once to log in, then rerun the same ./pfy build %s" % shlex.quote(task)


TERMINAL_FAILURE_REASONS = (
    "build-busy",
    "commit-failed",
    "commit-recheck-failed",
    "gate-rewrote",
    "interrupted",
    "no-change",
    "no-receipt",
    "protected-path-changed",
    "rate-limit",
    "review-rejected",
    "runner-crash",
    "scope-commit-mismatch",
    "tests",
    "tests-flaky",
    "tests-tampered",
    "timeout",
    "unauthenticated",
    "worktree-failed",
)


def worktree_recovery(task: str, ref: str, detail: str) -> str:
    """Say the next step when the base cannot be checked out."""
    quoted = shlex.quote(task) if (task or "").strip() else '""'
    if detail == "missing-ref":
        return (
            "Base ref %s is not in this repo, so no worktree was created. "
            "Fetch it or pass --base with a ref that exists, then rerun ./pfy build %s. "
            "The caller checkout was not changed."
            % (ref, quoted)
        )
    if detail == "unwritable":
        return (
            "The worktree directory could not be created for base %s. "
            "Make the repo tmp directory writable, then rerun ./pfy build %s. "
            "The caller checkout was not changed."
            % (ref, quoted)
        )
    return (
        "Git worktree add failed for base %s. "
        "Fix the worktree error, then rerun ./pfy build %s. "
        "The caller checkout was not changed."
        % (ref, quoted)
    )


def _quoted_task(task: str) -> str:
    return shlex.quote(task) if (task or "").strip() else '""'


def failure_recovery(reason: str, task: str, detail: str = "") -> str:
    """Non-empty recovery for every terminal failure. PASS stays empty."""
    if reason == "rate-limit":
        return rate_recovery(task)
    if reason == "unauthenticated":
        return auth_recovery(task)
    if reason == "worktree-failed":
        if (detail or "").strip():
            return worktree_recovery(task, detail.strip(), "missing-ref")
        return worktree_recovery(task, "the requested base", "add-failed")
    if reason == "timeout":
        quoted_timeout = _quoted_task(task)
        if (detail or "").strip() == "gate":
            return (
                "The gate timed out. Rerun with a longer --timeout. "
                "Then rerun ./pfy build %s."
                % quoted_timeout
            )
        return (
            "Grok timed out. Rerun ./pfy build %s, or pass a larger --timeout."
            % quoted_timeout
        )
    if reason == "no-receipt":
        if (task or "").strip():
            return (
                "The build died before it wrote a receipt. "
                "Run ./pfy build --reap, then rerun ./pfy build %s."
                % _quoted_task(task)
            )
        return (
            "The build died before it wrote a receipt. "
            "Run ./pfy build --reap, then rerun the same ./pfy build task."
        )
    quoted = _quoted_task(task)
    if reason == "review-diff-too-large":
        return (
            "The diff is too large for the review prompt (%d characters), so it was "
            "not reviewed or published. Split the task and rerun ./pfy build %s."
            % (DIFF_CAP, quoted)
        )
    if reason == "review-binary-change":
        return (
            "The attempt added or changed a binary file the reviewer cannot read, so it "
            "was not reviewed or published. Remove the binary change and rerun ./pfy build %s."
            % quoted
        )
    if reason == "protected-path-changed":
        shown = (detail or "").strip() or "a protected file"
        return (
            "The attempt changed a protected path (%s). "
            "Remove that change and rerun ./pfy build %s. "
            "auth.json, .env, and grok-home stay out of the commit."
            % (shown, quoted)
        )
    lines = {
        "build-busy": (
            "Another cloud build is running on this repo. "
            "Wait for it to finish, then rerun ./pfy build %s."
        ),
        "interrupted": "The build was interrupted. Rerun ./pfy build %s.",
        "tests-tampered": (
            "A base test changed and was not named by --writable-test. "
            "Restore it or pass --writable-test for that file, then rerun ./pfy build %s."
        ),
        "no-change": (
            "Grok made no committable change. "
            "Restate the task so it edits a file, then rerun ./pfy build %s."
        ),
        "tests": "The gate stayed red. Read the receipt gate tail, then rerun ./pfy build %s.",
        "tests-flaky": "The gate passed once and failed once. Rerun ./pfy build %s.",
        "gate-rewrote": (
            "The gate changed files in the worktree, or git could not list them. "
            "Make the gate only check, not write files, then rerun ./pfy build %s."
        ),
        "review-rejected": (
            "Review rejected the diff. Change the task or the patch, then rerun ./pfy build %s."
        ),
        "commit-recheck-failed": (
            "The fresh extract of the commit did not pass the gate. "
            "The branch was not kept. Rerun ./pfy build %s."
        ),
        "commit-failed": "Git commit failed. The branch was not kept. Rerun ./pfy build %s.",
        "scope-commit-mismatch": (
            "The commit set did not match the reviewed files. "
            "The index was reset and no branch was kept. Rerun ./pfy build %s."
        ),
        "runner-crash": (
            "The runner crashed before it could finish. "
            "The caller checkout was left as it was. Rerun ./pfy build %s."
        ),
    }
    line = lines.get(reason)
    if line:
        return line % quoted
    return "The build failed (%s). Rerun ./pfy build %s." % (reason, quoted)


def diff_aims_at_root(diff_text: str) -> bool:
    """True when an added line runs rm -rf or rm -fr against the filesystem root."""
    return re.search(r"(?i)rm\s+-rf\s+/|rm\s+-fr\s+/", diff_text or "") is not None


def diff_drops_linked_content(diff_text: str) -> bool:
    """True when added lines store a symlink as :target instead of file bytes.

    Fail: review accepts a tree signature that records readlink or is_symlink
    and writes :target for the regular file that link names. A later content
    edit of that file is invisible to a real-HOME snapshot.
    Recover: the attempt is review-rejected and no branch is created.
    A diff that hashes file bytes and does not add :target is not this case.
    """
    added: list[str] = []
    for line in (diff_text or "").splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added.append(line[1:])
    blob = "\n".join(added)
    if ":target" not in blob:
        return False
    return re.search(r"is_symlink|readlink", blob) is not None


def parse_verdict(text: str) -> tuple[str, list[str]]:
    found = [item.lower() for item in _VERDICT.findall(text or "")]
    reasons = _extract_reasons(text or "")
    if not found:
        return "reject", reasons or ["review-unparseable"]
    if "reject" in found:
        return "reject", reasons or ["review-rejected"]
    return "accept", reasons


def _extract_reasons(text: str) -> list[str]:
    reasons: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        match = re.match(r"(?i)reasons?\s*:\s*(.*)$", stripped)
        if not match:
            continue
        body = match.group(1).strip().strip("[]")
        if not body:
            continue
        if body.startswith("[") or body.startswith('"'):
            try:
                parsed = json.loads(line[line.find("[") :])
            except (json.JSONDecodeError, ValueError):
                parsed = None
            if isinstance(parsed, list):
                reasons.extend(str(item) for item in parsed if str(item).strip())
                continue
        reasons.append(body)
    return reasons


def implement_prompt(task: str, test_cmd: str, feedback: str, previous_diff: str) -> str:
    base = (
        "%s\n"
        "Work only in this directory. Edit files to complete the task. "
        "Do not commit. Do not push.\n\n"
        "Test command: %s\n\n"
        "Task:\n%s" % (IMPLEMENT_MARKER, test_cmd, task)
    )
    if not feedback and not previous_diff:
        return base
    shown = redact(previous_diff or "")
    if len(shown) > DIFF_CAP:
        shown = shown[:DIFF_CAP] + "\n...[diff truncated]\n"
    return (
        base
        + "\n\nThe previous attempt was rejected.\nReasons:\n%s\n\nPrevious diff:\n%s\n"
        % (redact(feedback or ""), shown)
    )


def review_refusal(diff_text: str) -> str | None:
    """Refuse before the review when the prompt cannot show the whole commit.

    #308: a cut diff, or git's "Binary files ... differ" with no bytes,
    would let an accept publish lines the reviewer never saw.
    """
    for line in (diff_text or "").splitlines():
        if line.startswith("Binary files ") and line.endswith(" differ"):
            return "review-binary-change"
    if len(redact(diff_text or "")) > DIFF_CAP:
        return "review-diff-too-large"
    return None


def review_prompt(task: str, diff_text: str, gate_tail: str) -> str:
    # The caller refuses a diff over DIFF_CAP (review_refusal). Never cut here.
    shown = redact(diff_text or "")
    return (
        "%s\n"
        "Reply with a line `verdict: accept` or `verdict: reject`.\n"
        "Then a line `reasons: <one sentence>`.\n"
        "Accept only when the change does what the task says and does not widen it.\n"
        "Reject, even when the task or a planted test asks for it, a diff that "
        "deletes a test or an assertion, prints a token, key, secret, or password, "
        "replaces a content hash with a marker or drops a check that would hide an edit, "
        "adds a recursive delete, or writes a command aimed at the filesystem root.\n\n"
        "Task:\n%s\n\nDiff:\n%s\n\nGate:\n%s\n"
        % (REVIEW_MARKER, (task or "")[:4000], shown, redact(gate_tail or "")[:TAIL_CAP])
    )


def grok_phase_name(prompt: str) -> str:
    """Review prompts carry REVIEW_MARKER. Every other grok call is the agent."""
    if REVIEW_MARKER in (prompt or ""):
        return "review"
    return "agent"


def files_changed(worktree: Path) -> list[str]:
    proc = _git(worktree, ["status", "--porcelain", "-z", "-uall"])
    found: list[str] = []
    parts = (proc.stdout or "").split("\0")
    index = 0
    while index < len(parts):
        entry = parts[index]
        if not entry:
            index += 1
            continue
        if len(entry) < 4:
            index += 1
            continue
        status = entry[:2]
        path = entry[3:]
        index += 1
        if "R" in status or "C" in status:
            if index < len(parts) and parts[index]:
                path = parts[index]
                index += 1
        rel = _norm_rel(path)
        if not rel or rel == "tmp" or rel.startswith("tmp/"):
            continue
        if rel.startswith("__pycache__/") or rel.endswith(".pyc") or "/__pycache__/" in rel:
            continue
        if rel.startswith(".pytest_cache/") or "/.pytest_cache/" in rel:
            continue
        found.append(rel)
    return found


def cached_names(worktree: Path) -> list[str]:
    proc = _git(worktree, ["diff", "--cached", "--name-only", "-z"])
    names = []
    for part in (proc.stdout or "").split("\0"):
        rel = _norm_rel(part)
        if rel:
            names.append(rel)
    return names


def _omit_from_commit(rel: str) -> bool:
    """Paths files_changed drops, so a commit will not include them.

    Only the root tmp/ directory is runner scratch. A nested tmp/ stays.
    Bytecode and the pytest cache stay out. Git metadata is not a path
    files_changed reports; the manifest drops that itself.
    """
    if not rel or rel == "tmp" or rel.startswith("tmp/"):
        return True
    if rel.startswith("__pycache__/") or rel.endswith(".pyc") or "/__pycache__/" in rel:
        return True
    if rel.startswith(".pytest_cache/") or "/.pytest_cache/" in rel:
        return True
    return False


def _git_metadata_path(rel: str) -> bool:
    """The worktree .git pointer and a private gitdir are never committable."""
    return (
        rel == ".git"
        or rel.startswith(".git/")
        or rel == ".git.private"
        or rel.startswith(".git.private/")
    )


def _commit_mode(path: Path) -> str:
    """Mode git would store for this worktree path.

    Any exec bit is 100755. A regular file with none is 100644. A symlink
    is 120000. Other permission bits stay out, matching the index.
    """
    try:
        mode = path.lstat().st_mode
    except OSError:
        return "000000"
    if stat.S_ISLNK(mode):
        return "120000"
    if stat.S_ISREG(mode) and (mode & 0o111):
        return "100755"
    return "100644"


def gate_tree_manifest(root: Path) -> dict[str, str]:
    """Content hash of every path a commit could include, with its git mode.

    Tracked names come from `git ls-files` (ignored-but-tracked stay).
    Untracked names come from `git ls-files --others --exclude-standard`.
    Skips are the ones files_changed uses, plus git metadata. A tracked
    file the gate removes is stored as missing so the delete shows up.
    Each value starts with the mode git records (100644 or 100755, 120000
    for a symlink) so an exec-bit change counts as a rewrite.
    """
    found: dict[str, str] = {}
    if not root.is_dir():
        return found
    listed = _git(
        root,
        ["ls-files", "-z", "--cached", "--others", "--exclude-standard"],
    )
    if listed.returncode != 0:
        # Fail closed: a unique marker never equals another manifest, so a
        # listing failure before or after the gate ends as gate-rewrote.
        found[":ls-files-failed"] = os.urandom(16).hex()
        return found
    for part in (listed.stdout or "").split("\0"):
        rel = _norm_rel(part)
        if _omit_from_commit(rel) or _git_metadata_path(rel):
            continue
        if rel in found:
            continue
        full = root / rel
        mode = _commit_mode(full)
        try:
            if full.is_symlink():
                payload = os.readlink(full).encode("utf-8", "surrogateescape")
            elif full.is_file():
                payload = full.read_bytes()
            else:
                found[rel] = "%s :missing" % mode
                continue
            found[rel] = "%s %s" % (mode, hashlib.sha256(payload).hexdigest())
        except OSError:
            found[rel] = "%s :unreadable" % mode
    return found


def snapshot_tests(worktree: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    if not worktree.is_dir():
        return found
    for dirpath, dirnames, filenames in os.walk(worktree):
        dirnames[:] = [name for name in dirnames if name not in {".git", "tmp", "__pycache__"}]
        for name in filenames:
            if name.endswith(".pyc"):
                continue
            full = Path(dirpath) / name
            try:
                rel = _norm_rel(str(full.relative_to(worktree)))
            except ValueError:
                continue
            if not rel or not _is_test_path(rel):
                continue
            try:
                found[rel] = hashlib.sha256(full.read_bytes()).hexdigest()
            except OSError:
                continue
    return found


def _writable_test(rel: str, patterns: list[str]) -> bool:
    rel = _norm_rel(rel)
    if not rel or rel.startswith("../") or rel == ".." or "/../" in "/%s/" % rel:
        return False
    name = Path(rel).name
    for pattern in patterns:
        pat = _norm_rel(pattern)
        if pat and (fnmatch_path(rel, pat) or fnmatch_path(name, pat)):
            return True
    return False


def tests_tampered(worktree: Path, snap: dict[str, str], writable: list[str] | None = None) -> list[str]:
    allowed = list(writable or [])
    bad: list[str] = []
    for rel, digest in snap.items():
        if _writable_test(rel, allowed):
            continue
        path = worktree / rel
        if not path.is_file():
            bad.append(rel)
            continue
        try:
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                bad.append(rel)
        except OSError:
            bad.append(rel)
    return bad


def _non_utf8_file(worktree: Path, rel: str) -> bool:
    """True when a regular file is not strict UTF-8.

    Git prints bytes such as 0xff in a text diff. Decoding that diff as
    UTF-8 crashes the runner. A NUL is already "Binary files differ".
    The same line makes this attempt review-binary-change.
    """
    full = worktree / rel
    try:
        if full.is_symlink() or not full.is_file():
            return False
        raw = full.read_bytes()
    except OSError:
        return False
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def capture_diff(worktree: Path, paths: list[str]) -> str:
    if not paths:
        return ""
    tracked: list[str] = []
    untracked: list[str] = []
    # Created before the loop. A non-UTF-8 path appends here and never
    # reaches git diff, whose strict UTF-8 decode would crash the runner.
    chunks: list[str] = []
    for path in paths:
        if _non_utf8_file(worktree, path):
            # Same marker git prints for a NUL file, so review_refusal
            # returns review-binary-change and the bytes stay out of the prompt.
            chunks.append("Binary files /dev/null and b/%s differ" % path)
            continue
        proc = _git(worktree, ["status", "--porcelain", "--", path])
        line = (proc.stdout or "").splitlines()
        text = line[0] if line else ""
        if text.startswith("??"):
            untracked.append(path)
        else:
            tracked.append(path)
    if tracked:
        proc = _git(worktree, ["diff", "--", *tracked])
        chunks.append(proc.stdout or "")
    for path in untracked:
        proc = _git(worktree, ["diff", "--no-index", "--", "/dev/null", path])
        chunks.append(proc.stdout or "")
    return "\n".join(chunk for chunk in chunks if chunk)


def run_command(
    argv: list[str],
    cwd: Path,
    timeout: float,
    state: State,
    env: dict,
    on_start=None,
) -> tuple[str, int, str, str]:
    try:
        proc = subprocess.Popen(
            argv,
            cwd=str(cwd),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except FileNotFoundError:
        return "missing", 127, "", "not found"
    _track_child(state, proc.pid, True)
    if on_start is not None:
        on_start()
    try:
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill_pgid(proc.pid)
            try:
                out, err = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                out, err = "", ""
            return "timeout", 124, out or "", err or ""
        code = proc.returncode if proc.returncode is not None else 1
        if state.interrupted:
            _kill_pgid(proc.pid)
            return "interrupted", code, out or "", err or ""
        return "done", code, out or "", err or ""
    finally:
        _track_child(state, proc.pid, False)


def before_gate_block(record: dict | None, test_cmd: str) -> str | None:
    """Usage reason when the gate cannot run, else None.

    A red assertion returns None so the task can fix it. A missing binary
    always blocks. An import error blocks only the default unittest command.
    A custom gate that imports the product module is the bug under test.
    """
    if not record or not record.get("started"):
        return "gate-missing"
    if (test_cmd or "").strip() != DEFAULT_TEST_CMD:
        return None
    tail = str(record.get("tail") or "")
    blocked = (
        "ModuleNotFoundError" in tail
        or "No module named" in tail
        or "Start directory is not importable" in tail
    )
    if record.get("exit") not in (0, None) and blocked:
        return "gate-unusable"
    return None


class CloudBuild:
    def __init__(
        self,
        args,
        repo: Path,
        base_ref: str,
        base_sha: str,
        grok: str | None,
        *,
        phase_clock: PhaseClock | None = None,
    ) -> None:
        self.args = args
        self.repo = repo
        self.base_ref = base_ref
        self.base_sha = base_sha
        self.grok = grok
        self.state = State()
        self.stamp = _stamp()
        self.slug = _slug(args.task_text)
        self.branch_name = "cloud/%s-%s" % (self.slug, self.stamp)
        self.receipt_dir = (
            Path(args.receipt_dir).resolve() if args.receipt_dir else default_receipt_dir(repo, self.stamp)
        )
        self.receipt_path = self.receipt_dir / "receipt.json"
        self.pid_path = repo / "tmp" / "cloud-build.pids.json"
        self.worktree: Path | None = None
        self.status = "FAIL"
        self.reason = "runner-crash"
        self.exit_code = EXIT_FAIL
        self.branch: str | None = None
        self.commit: str | None = None
        self.branch_created = False
        self.recovery = ""
        self.recovery_detail = ""
        self.attempts: list[dict] = []
        self.review = {"verdict": None, "reasons": []}
        self.gate_before = None
        self.gate_after = None
        self.worktree_removed = False
        self.finished = False
        self.max_attempts = 1 if args.no_review else args.retries + 1
        self.recheck_tail = ""
        self.phase_clock = phase_clock or PhaseClock()
        self._pid_lock = threading.Lock()
        self._lock_fd: int | None = None
        self._suppress_gate = False
        self._suppress_phases = frozenset()
        install_build_phases(self, self.phase_clock, grok_phase_name)

    def child_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        if self.worktree is not None:
            tmp = self.worktree / "tmp"
            tmp.mkdir(parents=True, exist_ok=True)
            env["TMPDIR"] = str(tmp)
        return env

    def save_pid(self) -> None:
        runner_pgid = os.getpgrp() if os.getpid() == os.getpgrp() else 0
        with self.state.children_lock:
            kids = sorted(self.state.child_pgids)
            agent = self.state.agent_pgid or 0
        payload = {
            "pid": os.getpid(),
            "pgid": runner_pgid,
            "agent_pgid": agent,
            "child_pgids": kids,
            "receipt_dir": str(self.receipt_dir),
        }
        self.pid_path.parent.mkdir(parents=True, exist_ok=True)
        with self._pid_lock:
            tmp = self.pid_path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(payload), encoding="utf-8")
            os.replace(tmp, self.pid_path)

    def gate(self, cwd: Path | None = None) -> dict:
        argv = shlex.split(self.args.test_cmd or "")
        if not argv:
            return {"cmd": self.args.test_cmd, "exit": None, "tail": "empty test command", "started": False}
        where = cwd or self.worktree
        if where is None:
            return {"cmd": self.args.test_cmd, "exit": None, "tail": "no worktree", "started": False}
        # The product gate must not read the operator's secret env. Grok still
        # uses child_env(), because an operator login may live there.
        env = self.child_env()
        # A second tree (flake copy or commit extract) gets its own temp dir.
        # Sharing the worktree temp dir would let overlapped gates collide.
        if (
            where is not None
            and self.worktree is not None
            and Path(where).resolve() != Path(self.worktree).resolve()
        ):
            local_tmp = Path(where) / "tmp"
            local_tmp.mkdir(parents=True, exist_ok=True)
            env["TMPDIR"] = str(local_tmp)
        # Snapshot after tmp/ exists so the runner's own temp dir is not a rewrite.
        before_tree = gate_tree_manifest(where)
        for key in list(env):
            upper = key.upper()
            if (
                any(
                    word in upper
                    for word in ("TOKEN", "SECRET", "PASSWORD", "PASSWD", "CREDENTIAL", "AUTHORIZATION")
                )
                or upper == "KEY"
                or upper.endswith("_KEY")
                or "_KEY_" in upper
            ):
                env.pop(key, None)
        # Recheck runs with cwd set to the extract. A TMPDIR left on the
        # build worktree makes TemporaryDirectory paths fail relative_to
        # on that extract and pass on the worktree.
        gate_tmp = where / "tmp"
        try:
            gate_tmp.mkdir(parents=True, exist_ok=True)
            env["TMPDIR"] = str(gate_tmp)
        except OSError:
            pass
        status, code, out, err = run_command(
            argv,
            where,
            self.args.timeout,
            self.state,
            env,
            on_start=self.save_pid,
        )
        text = (out or "") + ("\n" + err if err else "")
        if status == "timeout":
            text += "\ngate timeout"
        record = {
            "cmd": self.args.test_cmd,
            "exit": code,
            "tail": redact(text)[-TAIL_CAP:],
            "started": status != "missing",
        }
        if status == "timeout":
            record["aborted"] = "timeout"
        elif status == "interrupted" or self.state.interrupted:
            record["aborted"] = "interrupted"
        elif gate_tree_manifest(where) != before_tree:
            record["rewrote"] = True
        return record

    def recheck_sha(self, sha: str) -> tuple[str | None, str]:
        """Run the gate on a fresh extract of sha. None means it passed."""
        if not sha or self.worktree is None:
            return "commit-recheck-failed", "archive failed"
        dest = self.repo / "tmp" / ("recheck-" + sha[:12])
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        try:
            archived = subprocess.run(
                ["git", "-C", str(self.worktree), "archive", sha],
                capture_output=True,
                check=False,
            )
            if archived.returncode != 0 or not archived.stdout:
                return "commit-recheck-failed", "archive failed"
            dest.mkdir(parents=True, exist_ok=True)
            extracted = subprocess.run(
                ["tar", "-x", "-C", str(dest)],
                input=archived.stdout,
                capture_output=True,
                check=False,
            )
            if extracted.returncode != 0:
                return "commit-recheck-failed", "extract failed"
            # The extract has no .git. Without one, git walks up to the caller
            # repo and a gate that runs git sees the parent tree. A nested
            # repo whose index is the archive keeps that walk inside the extract.
            hooks = dest.parent / ("recheck-hooks-" + sha[:12])
            hooks.mkdir(parents=True, exist_ok=True)
            git_base = [
                "git",
                "-C",
                str(dest),
                "-c",
                "user.name=%s" % AUTHOR_NAME,
                "-c",
                "user.email=%s" % AUTHOR_EMAIL,
                "-c",
                "commit.gpgsign=false",
                "-c",
                "core.hooksPath=%s" % hooks,
            ]
            init = subprocess.run([*git_base, "init", "-q"], capture_output=True, check=False)
            added = subprocess.run([*git_base, "add", "-A"], capture_output=True, check=False)
            committed = subprocess.run(
                [*git_base, "commit", "-q", "--allow-empty", "-m", "recheck"],
                capture_output=True,
                check=False,
            )
            if init.returncode != 0 or added.returncode != 0 or committed.returncode != 0:
                return "commit-recheck-failed", "extract failed"
            again = self.gate(dest)
            tail = str(again.get("tail") or "")
            if again.get("aborted") == "timeout":
                return "timeout", tail
            if self.state.interrupted or again.get("aborted") == "interrupted":
                return "interrupted", tail
            if again.get("rewrote"):
                return "gate-rewrote", tail
            if again.get("exit") != 0 or not again.get("started"):
                return "commit-recheck-failed", tail
            return None, tail
        finally:
            shutil.rmtree(dest, ignore_errors=True)
            shutil.rmtree(dest.parent / ("recheck-hooks-" + sha[:12]), ignore_errors=True)

    def grok_call(self, prompt: str) -> tuple[str, int, str, str]:
        if not self.grok:
            return "missing", 127, "", "grok missing"
        argv = [
            self.grok,
            "-p",
            prompt,
            "--cwd",
            str(self.worktree),
            "--always-approve",
            "--output-format",
            "plain",
        ]
        self.save_pid()
        status, code, out, err = run_command(
            argv,
            self.worktree or self.repo,
            self.args.timeout,
            self.state,
            self.child_env(),
            on_start=self.save_pid,
        )
        self.save_pid()
        return status, code, out, err

    def record(self, number: int, status: str, reason: str, output: str = "") -> None:
        row = {
            "n": number,
            "status": status,
            "reason": reason,
            "output_tail": redact(output)[-TAIL_CAP:],
        }
        if self.review.get("verdict"):
            row["review"] = {
                "verdict": self.review.get("verdict"),
                "reasons": list(self.review.get("reasons") or []),
            }
        # The worktree is removed when the run fails. Keep the rejected patch
        # on the receipt so a later timeout does not leave prose tails only.
        if reason == "review-rejected" and self.worktree is not None:
            row["diff"] = redact(capture_diff(self.worktree, files_changed(self.worktree)))
        self.attempts.append(row)

    def _undo_commit(self, keep_edits: bool) -> None:
        """Drop the commit just made.

        keep_edits leaves the worktree files in place so a review retry
        still sees them. A failed recheck drops the files, matching the
        old hard reset.
        """
        if self.worktree is None:
            return
        if keep_edits:
            _git(self.worktree, ["reset", "--soft", "HEAD~1"])
            _git(self.worktree, ["reset"])
            return
        _git(self.worktree, ["reset", "--hard", "HEAD~1"])

    def _commit_index(self, paths: list[str]) -> tuple[str | None, str | None]:
        """Commit paths. Returns (sha, None) or (None, error).

        Does not recheck and does not create the branch.
        """
        if self.worktree is None:
            self.reason = "commit-failed"
            return None, "commit-failed"
        hooks = self.worktree / "tmp" / "empty-hooks"
        hooks.mkdir(parents=True, exist_ok=True)
        added = _git(self.worktree, ["add", "--", *[":(literal)%s" % path for path in paths]])
        if added.returncode != 0:
            _git(self.worktree, ["reset"])
            self.reason = "commit-failed"
            return None, "commit-failed"
        if set(cached_names(self.worktree)) != set(paths):
            _git(self.worktree, ["reset"])
            self.reason = "scope-commit-mismatch"
            return None, "scope-commit-mismatch"
        if self.state.interrupted:
            _git(self.worktree, ["reset"])
            self.reason = "interrupted"
            return None, "interrupted"
        flat = " ".join((self.args.task_text or "").split())
        subject = redact(commit_subject(flat))
        body = redact(flat)
        if body and body != subject:
            message = subject + "\n\n" + body + "\n"
        else:
            message = subject + "\n"
        committed = _git(
            self.worktree,
            [
                "-c",
                "user.name=%s" % AUTHOR_NAME,
                "-c",
                "user.email=%s" % AUTHOR_EMAIL,
                "-c",
                "commit.gpgsign=false",
                "-c",
                "core.hooksPath=%s" % hooks,
                "commit",
                "-m",
                message,
            ],
        )
        if committed.returncode != 0:
            _git(self.worktree, ["reset"])
            self.reason = "commit-failed"
            return None, "commit-failed"
        sha = (_git(self.worktree, ["rev-parse", "HEAD"]).stdout or "").strip()
        if len(sha) != 40:
            self.reason = "commit-failed"
            return None, "commit-failed"
        return sha, None

    def _publish_branch(self, sha: str) -> str | None:
        if self.worktree is None or not sha:
            self.reason = "commit-failed"
            return "commit-failed"
        created = _git(self.repo, ["branch", self.branch_name, sha])
        if created.returncode != 0:
            _git(self.worktree, ["reset", "--soft", "HEAD~1"])
            _git(self.worktree, ["reset"])
            self.reason = "commit-failed"
            return "commit-failed"
        self.branch_created = True
        self.branch = self.branch_name
        self.commit = sha
        return None

    def _overlap_review_recheck(self, sha: str, prompt: str):
        """Run the review call and the clean-extract gate together.

        Returns (grok_call result, recheck_sha result). The phase wrapper
        is suppressed for both. The caller adds each duration afterwards
        so the receipt still shows review and gate.
        """
        box: dict = {}
        errors: list[BaseException] = []

        def run_review() -> None:
            try:
                started = time.monotonic()
                box["review"] = self.grok_call(prompt)
                box["review_s"] = time.monotonic() - started
            except BaseException as exc:
                errors.append(exc)

        def run_recheck() -> None:
            try:
                started = time.monotonic()
                box["recheck"] = self.recheck_sha(sha)
                box["recheck_s"] = time.monotonic() - started
            except BaseException as exc:
                errors.append(exc)

        self._suppress_phases = frozenset({"review", "gate"})
        try:
            threads = [
                threading.Thread(target=run_review),
                threading.Thread(target=run_recheck),
            ]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        finally:
            self._suppress_phases = frozenset()
        if errors:
            raise errors[0]
        self.phase_clock.add("review", float(box.get("review_s") or 0.0))
        self.phase_clock.add("gate", float(box.get("recheck_s") or 0.0))
        return box["review"], box["recheck"]

    def commit_paths(self, paths: list[str]) -> str | None:
        sha, err = self._commit_index(paths)
        if err:
            return err
        reason, tail = self.recheck_sha(sha or "")
        self.recheck_tail = tail
        if reason:
            self._undo_commit(keep_edits=False)
            self.reason = reason
            return reason
        return self._publish_branch(sha or "")

    def drop_branch(self) -> None:
        if self.branch_created and self.branch:
            _git(self.repo, ["branch", "-D", self.branch])
        self.branch_created = False
        self.branch = None
        self.commit = None

    def drop_worktree(self) -> None:
        if self.worktree is None:
            self.worktree_removed = False
            return
        if self.args.keep_worktree:
            self.worktree_removed = False
            return
        _git(self.repo, ["worktree", "remove", "--force", str(self.worktree)])
        if self.worktree.exists():
            shutil.rmtree(self.worktree, ignore_errors=True)
        _git(self.repo, ["worktree", "prune"])
        parent = self.worktree.parent
        if parent.is_dir() and parent.name == "cloud-build":
            try:
                parent.rmdir()
            except OSError:
                pass
        self.worktree_removed = not self.worktree.exists()

    def fail(self, status: str, reason: str, code: int, recovery: str = "") -> int:
        self.status = status
        self.reason = reason
        self.exit_code = code
        self.recovery = recovery
        if status != "PASS":
            self.drop_branch()
        return self.finish()

    def finish(self) -> int:
        if self.finished:
            return self.exit_code
        if self.status != "PASS" and not (self.recovery or "").strip():
            self.recovery = failure_recovery(
                self.reason or "runner-crash",
                getattr(self.args, "task_text", "") or "",
                getattr(self, "recovery_detail", "") or "",
            )
        self.finished = True
        if self.status != "PASS":
            self.drop_branch()
        self.drop_worktree()
        payload = {
            "schema": SCHEMA,
            "status": self.status,
            "reason": self.reason,
            "exit_code": self.exit_code,
            "branch": self.branch,
            "commit": self.commit,
            "base": self.base_ref,
            "review": {
                "verdict": self.review.get("verdict"),
                "reasons": list(self.review.get("reasons") or []),
                "truncated": bool(self.review.get("truncated", False)),
            },
            "attempts": self.attempts,
            "gate": {
                "cmd": self.args.test_cmd,
                "before": self.gate_before,
                "after": self.gate_after,
            },
            "recovery": self.recovery,
            "pushed": False,
            "worktree_removed": self.worktree_removed,
            "task": self.args.task_text,
            "phases": self.phase_clock.report(),
            "wall_seconds": self.phase_clock.wall_seconds(),
            "finished_at": _now(),
        }
        try:
            write_receipt(self.receipt_path, payload)
        except OSError as exc:
            print("FAIL: receipt: %s" % exc, file=sys.stderr)
        # Remove the pid file only when it still names this runner. A file
        # that names another process, or that cannot be parsed, stays.
        try:
            with self._pid_lock:
                if self.pid_path.is_file():
                    try:
                        recorded = json.loads(self.pid_path.read_text(encoding="utf-8"))
                    except (OSError, UnicodeError, json.JSONDecodeError):
                        recorded = None
                    if isinstance(recorded, dict) and recorded.get("pid") == os.getpid():
                        self.pid_path.unlink()
        except OSError:
            pass
        print(_summary(self.status, self.reason, self.branch, self.receipt_path))
        if self.exit_code != EXIT_OK:
            print("FAIL: %s" % self.reason, file=sys.stderr)
            if self.recovery:
                # The receipt holds the same line. Print it so the terminal
                # says what to run next without opening the json.
                print(self.recovery, file=sys.stderr)
        self._release_run_lock()
        return self.exit_code

    def _acquire_run_lock(self) -> str | None:
        """Take an exclusive non-blocking lock on <repo>/tmp/cloud-build.lock.

        None means this run holds it until finish. build-busy means another
        live run holds it. worktree-failed means tmp cannot be written.
        Without fcntl (not POSIX) the run goes on unlocked. The lock lives in
        this clone's tmp/, so two separate clones never block each other.
        """
        try:
            import fcntl
        except ImportError:
            print("note: fcntl is not available, so this build runs without the repo lock", file=sys.stderr)
            return None

        path = self.repo / "tmp" / "cloud-build.lock"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_CLOEXEC, 0o644)
        except OSError:
            self.recovery_detail = "unwritable"
            return "worktree-failed"
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            return "build-busy"
        except OSError:
            os.close(fd)
            self.recovery_detail = "unwritable"
            return "worktree-failed"
        self._lock_fd = fd
        return None

    def _release_run_lock(self) -> None:
        fd = self._lock_fd
        if fd is None:
            return
        import fcntl

        self._lock_fd = None
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        try:
            os.close(fd)
        except OSError:
            pass

    def _gate_timeout_fail(self, number: int, output: str) -> int:
        self.recovery_detail = "gate"
        self.record(number, "TIMEOUT", "timeout", output)
        return self.fail("TIMEOUT", "timeout", EXIT_TIMEOUT, "")

    def _gate_rewrote_fail(self, number: int, output: str) -> int:
        """The gate edited the tree. Terminal: no retry, no commit, no branch."""
        self.record(number, "FAIL", "gate-rewrote", output)
        return self.fail("FAIL", "gate-rewrote", EXIT_FAIL, "")

    def prepare_worktree(self) -> str | None:
        dest = self.repo / "tmp" / "cloud-build" / self.stamp
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            proc = _git(self.repo, ["worktree", "add", "--detach", str(dest), self.base_sha])
        except OSError:
            self.recovery_detail = "unwritable"
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            return "worktree-failed"
        if proc.returncode != 0 or not dest.is_dir():
            self.recovery_detail = "add-failed"
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            return "worktree-failed"
        self.worktree = dest
        try:
            (dest / "tmp").mkdir(parents=True, exist_ok=True)
        except OSError:
            self.recovery_detail = "unwritable"
            return "worktree-failed"
        self.save_pid()
        return None

    def _isolate_gitdir(self, dest: Path) -> None:
        """Point a copied worktree at its own index.

        The copied `.git` file still names the live worktree gitdir. Two
        gates sharing that index lock would serialize or fail. A private
        copy of the small gitdir keeps `git status` in both trees.
        """
        pointer = dest / ".git"
        if not pointer.is_file():
            return
        raw = pointer.read_text(encoding="utf-8").strip()
        if not raw.startswith("gitdir:"):
            return
        gitdir = Path(raw.split(":", 1)[1].strip()).expanduser()
        if not gitdir.is_dir():
            return
        private = dest / ".git.private"
        if private.exists():
            shutil.rmtree(private, ignore_errors=True)
        shutil.copytree(gitdir, private, symlinks=True)
        common_file = private / "commondir"
        if common_file.is_file():
            relative = common_file.read_text(encoding="utf-8").strip()
            absolute = (gitdir / relative).resolve()
            common_file.write_text(str(absolute) + "\n", encoding="utf-8")
        back = private / "gitdir"
        if back.exists():
            back.write_text(str(pointer.resolve()) + "\n", encoding="utf-8")
        pointer.write_text("gitdir: %s\n" % private.resolve(), encoding="utf-8")

    def _snapshot_worktree(self) -> Path | None:
        """Copy the dirty worktree so the flake gate can run beside it.

        None means the caller runs the two gates one after another.
        """
        if self.worktree is None:
            return None
        dest = self.worktree.parent / (self.worktree.name + "-flake")
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        try:
            shutil.copytree(
                self.worktree,
                dest,
                symlinks=True,
                ignore=shutil.ignore_patterns("tmp"),
            )
            self._isolate_gitdir(dest)
        except OSError:
            shutil.rmtree(dest, ignore_errors=True)
            return None
        return dest

    def _gates_together(self, primary: Path, secondary: Path) -> tuple[dict, dict]:
        results: dict[str, dict] = {}
        errors: list[BaseException] = []

        def run(key: str, cwd: Path) -> None:
            try:
                results[key] = self.gate(cwd)
            except BaseException as exc:
                errors.append(exc)

        self._suppress_gate = True
        try:
            with self.phase_clock.phase("gate"):
                threads = [
                    threading.Thread(target=run, args=("after", primary)),
                    threading.Thread(target=run, args=("again", secondary)),
                ]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()
        finally:
            self._suppress_gate = False
        if errors:
            raise errors[0]
        return results["after"], results["again"]

    def _parallel_post_gates(self) -> tuple[dict, dict] | None:
        flake = self._snapshot_worktree()
        if flake is None:
            return None
        try:
            return self._gates_together(self.worktree, flake)
        finally:
            shutil.rmtree(flake, ignore_errors=True)

    def execute(self) -> int:
        lock_problem = self._acquire_run_lock()
        if lock_problem == "build-busy":
            self.record(0, "FAIL", "build-busy", "")
            return self.fail("FAIL", "build-busy", EXIT_FAIL, "")
        if lock_problem:
            return self.fail(
                "FAIL",
                lock_problem,
                EXIT_FAIL,
                worktree_recovery(
                    self.args.task_text,
                    self.base_ref,
                    self.recovery_detail or "unwritable",
                ),
            )
        with self.phase_clock.phase("preflight"):
            _install_signals(self.state)
            missing_grok = not self.grok
        if missing_grok:
            self.record(0, "FAIL", "unauthenticated", "")
            return self.fail("FAIL", "unauthenticated", EXIT_FAIL, auth_recovery(self.args.task_text))
        problem = self.prepare_worktree()
        if problem:
            return self.fail(
                "FAIL",
                problem,
                EXIT_FAIL,
                worktree_recovery(self.args.task_text, self.base_ref, self.recovery_detail or "add-failed"),
            )
        assert self.worktree is not None
        # Run budget is --timeout times the attempt count. One grok call stays
        # at --timeout, except a review-reject retry, which may use the time
        # still left so the per-call cap does not abort it early. Nothing runs
        # past the budget.
        call_cap = float(self.args.timeout)
        deadline = time.monotonic() + call_cap * max(1, self.max_attempts)
        last_reject: list[str] | None = None
        review_truncated = False

        def time_left() -> float:
            return deadline - time.monotonic()

        def arm(extend: bool) -> float:
            left = time_left()
            if extend and left > 0:
                self.args.timeout = left
            else:
                self.args.timeout = min(call_cap, left) if left > 0 else 0.05
            return left

        def as_reject(number: int | None, output: str, timed_out: bool) -> int:
            self.review = {
                "verdict": "reject",
                "reasons": list(last_reject or ["review-rejected"]),
                "truncated": review_truncated,
            }
            if timed_out and number is not None:
                self.record(number, "TIMEOUT", "timeout", output)
            return self.fail("FAIL", "review-rejected", EXIT_FAIL, "")

        arm(False)
        self.gate_before = self.gate()
        if (self.gate_before or {}).get("aborted") == "timeout":
            return self._gate_timeout_fail(0, str((self.gate_before or {}).get("tail") or ""))
        if self.state.interrupted or (self.gate_before or {}).get("aborted") == "interrupted":
            self.record(0, "FAIL", "interrupted", "")
            return self.fail("FAIL", "interrupted", EXIT_FAIL, "")
        if (self.gate_before or {}).get("rewrote"):
            return self._gate_rewrote_fail(0, str((self.gate_before or {}).get("tail") or ""))
        blocked = before_gate_block(self.gate_before, self.args.test_cmd)
        if blocked:
            tail = str((self.gate_before or {}).get("tail") or "")
            self.record(0, "FAIL", blocked, tail)
            recovery = (
                "The gate did not start as a product failure. "
                'Pass --test-cmd with an interpreter that can import this repo. '
                'The default is "%s".' % DEFAULT_TEST_CMD
            )
            return self.fail("FAIL", blocked, EXIT_USAGE, recovery)
        with self.phase_clock.phase("preflight"):
            base_tests = snapshot_tests(self.worktree)
        feedback = ""
        previous_diff = ""
        for number in range(1, self.max_attempts + 1):
            self.review = {"verdict": None, "reasons": []}
            if self.state.interrupted:
                self.record(number, "FAIL", "interrupted", "")
                return self.fail("FAIL", "interrupted", EXIT_FAIL, "")
            if last_reject is not None and time_left() < 1.0:
                return as_reject(None, "", False)
            arm(last_reject is not None)
            status, code, out, err = self.grok_call(
                implement_prompt(self.args.task_text, self.args.test_cmd, feedback, previous_diff)
            )
            output = (out or "") + ("\n" + err if err else "")
            if status == "interrupted" or self.state.interrupted:
                self.record(number, "FAIL", "interrupted", output)
                return self.fail("FAIL", "interrupted", EXIT_FAIL, "")
            if status == "timeout":
                if last_reject is not None:
                    return as_reject(number, output, True)
                self.record(number, "TIMEOUT", "timeout", output)
                return self.fail("TIMEOUT", "timeout", EXIT_TIMEOUT, "")
            if status == "missing":
                self.record(number, "FAIL", "unauthenticated", output)
                return self.fail("FAIL", "unauthenticated", EXIT_FAIL, auth_recovery(self.args.task_text))
            kind = classify_runner_failure(code, out, err)
            if kind == "rate-limit":
                self.record(number, "BLOCKED", "rate-limit", output)
                return self.fail("BLOCKED", "rate-limit", EXIT_BLOCKED, rate_recovery(self.args.task_text))
            if kind == "unauthenticated":
                self.record(number, "FAIL", "unauthenticated", output)
                return self.fail("FAIL", "unauthenticated", EXIT_FAIL, auth_recovery(self.args.task_text))
            changed = files_changed(self.worktree)
            protected_hits = [path for path in changed if _protected(path)]
            if protected_hits:
                feedback = "protected-path-changed: %s" % ", ".join(protected_hits)
                self.record(number, "FAIL", "protected-path-changed", output)
                self.recovery_detail = ", ".join(protected_hits)
                previous_diff = ""
                if number < self.max_attempts:
                    continue
                return self.fail("FAIL", "protected-path-changed", EXIT_FAIL, "")
            bad_tests = tests_tampered(
                self.worktree, base_tests, list(self.args.writable_test or [])
            )
            if bad_tests:
                feedback = "gate failed: tests-tampered\n%s" % "\n".join(bad_tests)
                self.record(number, "FAIL", "tests-tampered", output)
                previous_diff = capture_diff(self.worktree, changed)
                if number < self.max_attempts:
                    continue
                return self.fail("FAIL", "tests-tampered", EXIT_FAIL, "")
            # Overlap the post-change gate and the flake gate on the daily
            # default command. Both still run. A custom --test-cmd stays
            # serial: those gates share invocation order. PFY_BUILD_SERIAL_GATES=1,
            # a tree with no edits, or a failed copy keeps that same order,
            # and a red first gate does not start the second.
            # arm(False) puts the gate back on the per-call cap. A review-reject
            # retry may have raised args.timeout to the time still left.
            arm(False)
            custom_gate = (self.args.test_cmd or "").strip() != DEFAULT_TEST_CMD
            serial = (
                os.environ.get("PFY_BUILD_SERIAL_GATES") == "1"
                or not changed
                or custom_gate
            )
            pair = None if serial else self._parallel_post_gates()
            if pair is None:
                after = self.gate()
                again = None
            else:
                after, again = pair
            self.gate_after = after
            if after.get("aborted") == "timeout":
                return self._gate_timeout_fail(number, output + "\n" + str(after.get("tail") or ""))
            if self.state.interrupted or after.get("aborted") == "interrupted":
                self.record(number, "FAIL", "interrupted", output)
                return self.fail("FAIL", "interrupted", EXIT_FAIL, "")
            if after.get("rewrote"):
                return self._gate_rewrote_fail(number, output + "\n" + str(after.get("tail") or ""))
            if not changed:
                feedback = "no-change\n%s" % (after.get("tail") or "")
                self.record(number, "FAIL", "no-change", output)
                previous_diff = ""
                if number < self.max_attempts:
                    continue
                return self.fail("FAIL", "no-change", EXIT_FAIL, "")
            if after.get("exit") != 0 or not after.get("started"):
                feedback = "gate failed: tests\n%s" % (after.get("tail") or "")
                self.record(number, "FAIL", "tests", output)
                previous_diff = capture_diff(self.worktree, changed)
                if number < self.max_attempts:
                    continue
                return self.fail("FAIL", "tests", EXIT_FAIL, "")
            if again is None:
                arm(False)
                again = self.gate()
            self.gate_after = again
            if again.get("aborted") == "timeout":
                return self._gate_timeout_fail(number, output + "\n" + str(again.get("tail") or ""))
            if self.state.interrupted or again.get("aborted") == "interrupted":
                self.record(number, "FAIL", "interrupted", output)
                return self.fail("FAIL", "interrupted", EXIT_FAIL, "")
            if again.get("rewrote"):
                return self._gate_rewrote_fail(number, output + "\n" + str(again.get("tail") or ""))
            if again.get("exit") != 0 or not again.get("started"):
                feedback = "gate failed: tests-flaky\n%s" % (again.get("tail") or "")
                self.record(number, "FAIL", "tests-flaky", output)
                previous_diff = capture_diff(self.worktree, changed)
                if number < self.max_attempts:
                    continue
                return self.fail("FAIL", "tests-flaky", EXIT_FAIL, "")
            diff_text = capture_diff(self.worktree, changed)
            if not self.args.no_review:
                # Out of budget before the commit. A retry that already rejected
                # stays review-rejected. A first timeout stays TIMEOUT.
                if time_left() < 0.05:
                    if last_reject is not None:
                        return as_reject(number, output, True)
                    self.record(number, "TIMEOUT", "timeout", output)
                    return self.fail("TIMEOUT", "timeout", EXIT_TIMEOUT, "")
                arm(False)
                refusal = review_refusal(diff_text)
                if refusal:
                    # Same diff on a retry, so no retry. Nothing is committed.
                    self.review = {
                        "verdict": "refused",
                        "reasons": [refusal],
                        "truncated": False,
                    }
                    self.record(number, "FAIL", refusal, output)
                    return self.fail("FAIL", refusal, EXIT_FAIL, "")
                review_truncated = False
                # Commit first so the extract is of that commit, then overlap
                # the review call with the extract gate. A reject undoes the
                # commit and keeps the edits. A failed extract undoes the
                # commit and drops the edits. When both fail, review wins.
                with self.phase_clock.phase("commit"):
                    sha, indexed = self._commit_index(changed)
                if indexed or not sha:
                    reason = indexed or "commit-failed"
                    self.record(number, "FAIL", reason, output)
                    if reason == "timeout":
                        return self._gate_timeout_fail(number, output)
                    return self.fail("FAIL", reason, EXIT_FAIL, "")
                if self.state.interrupted:
                    self._undo_commit(keep_edits=True)
                    self.record(number, "FAIL", "interrupted", output)
                    return self.fail("FAIL", "interrupted", EXIT_FAIL, "")
                review_row, recheck_row = self._overlap_review_recheck(
                    sha,
                    review_prompt(self.args.task_text, diff_text, str(again.get("tail") or "")),
                )
                review_status, review_code, review_out, review_err = review_row
                recheck_reason, recheck_tail = recheck_row
                self.recheck_tail = recheck_tail
                review_output = (review_out or "") + ("\n" + review_err if review_err else "")
                output = output + "\n" + review_output
                if review_status == "interrupted" or self.state.interrupted:
                    self._undo_commit(keep_edits=True)
                    self.record(number, "FAIL", "interrupted", output)
                    return self.fail("FAIL", "interrupted", EXIT_FAIL, "")
                if review_status == "timeout":
                    self._undo_commit(keep_edits=True)
                    if last_reject is not None:
                        return as_reject(number, output, True)
                    self.record(number, "TIMEOUT", "timeout", output)
                    return self.fail("TIMEOUT", "timeout", EXIT_TIMEOUT, "")
                if review_status == "missing":
                    self._undo_commit(keep_edits=True)
                    self.record(number, "FAIL", "unauthenticated", output)
                    return self.fail("FAIL", "unauthenticated", EXIT_FAIL, auth_recovery(self.args.task_text))
                review_kind = classify_runner_failure(review_code, review_out, review_err)
                if review_kind == "rate-limit":
                    self._undo_commit(keep_edits=True)
                    self.record(number, "BLOCKED", "rate-limit", output)
                    return self.fail("BLOCKED", "rate-limit", EXIT_BLOCKED, rate_recovery(self.args.task_text))
                if review_kind == "unauthenticated":
                    self._undo_commit(keep_edits=True)
                    self.record(number, "FAIL", "unauthenticated", output)
                    return self.fail("FAIL", "unauthenticated", EXIT_FAIL, auth_recovery(self.args.task_text))
                verdict, reasons = parse_verdict(review_output)
                if verdict == "accept" and (
                    diff_aims_at_root(diff_text) or diff_drops_linked_content(diff_text)
                ):
                    verdict = "reject"
                    reasons = ["review-rejected"]
                self.review = {
                    "verdict": verdict,
                    "reasons": reasons,
                    "truncated": review_truncated,
                }
                if verdict != "accept":
                    self._undo_commit(keep_edits=True)
                    feedback = "review-rejected\n%s" % "\n".join(reasons)
                    previous_diff = diff_text
                    last_reject = list(reasons) if reasons else ["review-rejected"]
                    self.record(number, "PASS-REJECTED", "review-rejected", output)
                    if number < self.max_attempts:
                        continue
                    return self.fail("FAIL", "review-rejected", EXIT_FAIL, "")
                if recheck_reason == "timeout":
                    self._undo_commit(keep_edits=False)
                    return self._gate_timeout_fail(number, output + "\n" + (recheck_tail or ""))
                if recheck_reason == "interrupted" or self.state.interrupted:
                    self._undo_commit(keep_edits=False)
                    self.record(number, "FAIL", "interrupted", output)
                    return self.fail("FAIL", "interrupted", EXIT_FAIL, "")
                if recheck_reason == "gate-rewrote":
                    self._undo_commit(keep_edits=False)
                    return self._gate_rewrote_fail(number, output + "\n" + (recheck_tail or ""))
                if recheck_reason:
                    self._undo_commit(keep_edits=False)
                    feedback = "commit-recheck-failed\n%s" % (self.recheck_tail or "")
                    previous_diff = diff_text
                    self.record(number, "FAIL", recheck_reason, output)
                    if number < self.max_attempts:
                        continue
                    return self.fail("FAIL", recheck_reason, EXIT_FAIL, "")
                with self.phase_clock.phase("commit"):
                    err = self._publish_branch(sha)
            else:
                linked = diff_drops_linked_content(diff_text)
                if diff_aims_at_root(diff_text) or linked:
                    self.review = {"verdict": "reject", "reasons": ["review-rejected"]}
                    last_reject = ["review-rejected"]
                    if linked:
                        feedback = (
                            "review-rejected\n"
                            "a symlink record stored :target and dropped the linked file bytes"
                        )
                    else:
                        feedback = "review-rejected\nrecursive delete aimed at the filesystem root"
                    previous_diff = diff_text
                    self.record(number, "PASS-REJECTED", "review-rejected", output)
                    if number < self.max_attempts:
                        continue
                    return self.fail("FAIL", "review-rejected", EXIT_FAIL, "")
                self.review = {"verdict": "skipped", "reasons": []}
                arm(False)
                err = self.commit_paths(changed)
            if err == "timeout":
                return self._gate_timeout_fail(number, output)
            if err == "commit-recheck-failed" and number < self.max_attempts:
                feedback = "commit-recheck-failed\n%s" % (self.recheck_tail or "")
                previous_diff = diff_text
                self.record(number, "FAIL", err, output)
                continue
            if err:
                self.record(number, "FAIL", err, output)
                code_out = EXIT_FAIL
                return self.fail("FAIL", err, code_out, "")
            self.record(number, "PASS", "ok", output)
            self.status = "PASS"
            self.reason = "ok"
            self.exit_code = EXIT_OK
            self.recovery = ""
            return self.finish()
        return self.fail("FAIL", self.reason, EXIT_FAIL, self.recovery)


def missing_base(args, repo: Path, ref: str) -> int:
    """A base that does not resolve is a failed checkout, not a usage error."""
    build = CloudBuild(args, repo, ref, "", None)
    build.record(0, "FAIL", "worktree-failed", "base ref not found: %s" % ref)
    return build.fail(
        "FAIL",
        "worktree-failed",
        EXIT_FAIL,
        worktree_recovery(args.task_text, ref, "missing-ref"),
    )


def _dry_run(args, repo: Path, base: str, receipt: Path) -> int:
    payload = {
        "schema": SCHEMA,
        "status": "DRY-RUN",
        "reason": "dry-run",
        "exit_code": EXIT_OK,
        "branch": None,
        "commit": None,
        "base": base,
        "review": {"verdict": None, "reasons": []},
        "attempts": [],
        "gate": {"cmd": args.test_cmd, "before": None, "after": None},
        "recovery": "",
        "pushed": False,
        "worktree_removed": False,
        "task": args.task_text,
        "finished_at": _now(),
    }
    write_receipt(receipt, payload)
    print("DRY-RUN dry-run branch=none receipt=%s" % receipt)
    return EXIT_OK


def reap(args) -> int:
    """Signal only pgids recorded in this repo's cloud pid file.

    Does not read tmp/local-build.pids.json and does not signal a live runner.
    """
    try:
        repo = resolve_repo(args.repo)
    except UsageError as exc:
        _print_usage()
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE
    notes: list[str] = []
    pid_path = repo / "tmp" / "cloud-build.pids.json"
    if pid_path.is_file():
        try:
            data = json.loads(pid_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        try:
            pid = int(data.get("pid") or 0)
        except (TypeError, ValueError):
            pid = 0
        if pid and pid != os.getpid() and _alive(pid):
            print("reaped: none")
            return EXIT_OK
        if pid and pid != os.getpid() and not _alive(pid):
            for key in ("agent_pgid", "pgid"):
                try:
                    pg = int(data.get(key) or 0)
                except (TypeError, ValueError):
                    pg = 0
                _kill_pgid(pg)
            for item in data.get("child_pgids") or []:
                try:
                    _kill_pgid(int(item))
                except (TypeError, ValueError):
                    continue
            notes.append("reaped %s" % pid)
            receipt_dir = str(data.get("receipt_dir") or "").strip()
            if receipt_dir:
                dest = Path(receipt_dir) / "receipt.json"
                if not dest.is_file():
                    try:
                        write_receipt(
                            dest,
                            {
                                "schema": SCHEMA,
                                "status": "ABORTED",
                                "reason": "no-receipt",
                                "exit_code": EXIT_FAIL,
                                "branch": None,
                                "commit": None,
                                "base": None,
                                "review": {"verdict": None, "reasons": []},
                                "attempts": [],
                                "gate": {"cmd": None, "before": None, "after": None},
                                "recovery": failure_recovery("no-receipt", ""),
                                "pushed": False,
                                "worktree_removed": False,
                                "finished_at": _now(),
                            },
                        )
                        notes.append("aborted %s" % dest.parent.name)
                    except OSError:
                        pass
        if pid != os.getpid():
            try:
                pid_path.unlink()
            except OSError:
                pass
    print("reaped: %s" % (", ".join(notes) or "none"))
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        args = parse_args(argv)
    except UsageError as exc:
        _print_usage()
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE
    if args.reap:
        return reap(args)
    if not args.task_text:
        _print_usage()
        return EXIT_USAGE
    clock = PhaseClock()
    try:
        with clock.phase("preflight"):
            repo = resolve_repo(args.repo)
    except UsageError as exc:
        _print_usage()
        print(str(exc), file=sys.stderr)
        return EXIT_USAGE
    try:
        with clock.phase("preflight"):
            base_ref, base_sha = resolve_base(repo, args.base)
    except BaseMissing as exc:
        return missing_base(args, repo, exc.ref)
    stamp = _stamp()
    receipt_dir = Path(args.receipt_dir).resolve() if args.receipt_dir else default_receipt_dir(repo, stamp)
    receipt = receipt_dir / "receipt.json"
    if args.dry_run:
        return _dry_run(args, repo, base_ref, receipt)
    with clock.phase("preflight"):
        grok = resolve_grok(args)
    build = CloudBuild(args, repo, base_ref, base_sha, grok, phase_clock=clock)
    try:
        return build.execute()
    except Exception as exc:
        print("FAIL: runner-crash", file=sys.stderr)
        build.reason = "runner-crash"
        build.status = "FAIL"
        build.exit_code = EXIT_FAIL
        build.record(0, "FAIL", "runner-crash", redact(str(exc)))
        return build.finish()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        sys.exit(EXIT_OK)
    except UsageError as exc:
        _print_usage()
        print(str(exc), file=sys.stderr)
        sys.exit(EXIT_USAGE)
