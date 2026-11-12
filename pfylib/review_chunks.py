"""Shared review chunking, repo lock, usage, and gate-file checks.

Both pfy build wraps import this module. Review accept reuse is the memory
of the current process only. A JSON file on disk grants nothing.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import time
import urllib.parse
from pathlib import Path

TAIL_CAP = 4000
REVIEW_CHAR_CEILING = 2_000_000
REVIEW_PROMPT_CEILING = 200
ASSUME_IMPLEMENT_IN = 100000
ASSUME_IMPLEMENT_OUT = 8000
ASSUME_REVIEW_IN = 12000
ASSUME_REVIEW_OUT = 500
_DEF_LINE = re.compile(r"^(?:async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)\b")
_TABLE_RE = re.compile(r"^\s*\[([^\[\]]+)\]\s*$")
_GENERATED_DIRS = {
    "build",
    "dist",
    ".eggs",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "node_modules",
}
_FULLY_PROTECTED = {
    "conftest.py",
    "pytest.ini",
    "tox.ini",
    "setup.cfg",
    "sitecustomize.py",
    "usercustomize.py",
    ".gitattributes",
}
_TEST_PROBES = (
    "tests/test_x.py",
    "tests/test_calc.py",
    "conftest.py",
    "tests/conftest.py",
    "pytest.ini",
    "tox.ini",
    "setup.cfg",
)
_DANGEROUS_PATTERNS = {
    "*",
    "**",
    "?",
    "*.py",
    "tests",
    "tests/",
    "tests/**",
    "**/tests/**",
    "conftest.py",
}


class BuildAlreadyRunning(Exception):
    def __init__(self, pid, worktree=""):
        self.status = "build-already-running"
        self.pid = int(pid or 0)
        self.worktree = str(worktree or "")
        message = "build-already-running pid %s" % self.pid
        if self.worktree:
            message += " worktree %s" % self.worktree
        super().__init__(message)


class ReviewBudgetExceeded(Exception):
    def __init__(self, message):
        self.status = "review-budget-exceeded"
        super().__init__(message)


class _NopLock:
    noop = True
    path = None

    def release(self):
        return None

    def update_worktree(self, worktree):
        return None


class _Flock:
    noop = False

    def __init__(self, fd, path, fcntl_mod):
        self.fd = fd
        self.path = path
        self._fcntl = fcntl_mod

    def release(self):
        fd = self.fd
        if fd is None:
            return None
        self.fd = None
        try:
            self._fcntl.flock(fd, self._fcntl.LOCK_UN)
        except OSError:
            pass
        try:
            os.close(fd)
        except OSError:
            pass
        return None

    def update_worktree(self, worktree):
        if self.fd is None:
            return None
        payload = json.dumps({"pid": os.getpid(), "worktree": str(worktree or "")})
        os.lseek(self.fd, 0, os.SEEK_SET)
        os.ftruncate(self.fd, 0)
        os.write(self.fd, payload.encode("utf-8"))
        try:
            os.fsync(self.fd)
        except OSError:
            pass
        return None


def _load_fcntl():
    try:
        import fcntl as fcntl_mod
    except (ImportError, ModuleNotFoundError, TypeError):
        return None
    if fcntl_mod is None:
        return None
    return fcntl_mod


def _pid_alive(pid):
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _read_holder(path):
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return 0, ""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict):
        try:
            pid = int(data.get("pid") or 0)
        except (TypeError, ValueError):
            pid = 0
        return pid, str(data.get("worktree") or "")
    text = raw.strip()
    if text.isdigit():
        return int(text), ""
    return 0, ""


def _common_dir(repo):
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        proc = None
    if proc is not None and proc.returncode == 0 and (proc.stdout or "").strip():
        return Path(proc.stdout.strip())
    return Path(repo) / ".git"


def acquire_repo_lock(repo, worktree=""):
    """Exclusive lock in the git common dir. A dead holder is reclaimed.

    Missing fcntl returns a no-op lock so the caller can continue unlocked.
    release() unlocks and closes. It does not unlink the lock file.
    """
    fcntl_mod = _load_fcntl()
    if fcntl_mod is None:
        return _NopLock()
    path = _common_dir(repo) / "pfy-build.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR | os.O_CLOEXEC, 0o644)
    try:
        fcntl_mod.flock(fd, fcntl_mod.LOCK_EX | fcntl_mod.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        pid, held = _read_holder(path)
        if pid and not _pid_alive(pid):
            return _acquire_after_dead(repo, worktree, path, fcntl_mod)
        raise BuildAlreadyRunning(pid, held)
    except OSError:
        os.close(fd)
        raise
    lock = _Flock(fd, path, fcntl_mod)
    lock.update_worktree(worktree)
    return lock


def _acquire_after_dead(repo, worktree, path, fcntl_mod):
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR | os.O_CLOEXEC, 0o644)
    try:
        fcntl_mod.flock(fd, fcntl_mod.LOCK_EX | fcntl_mod.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        pid, held = _read_holder(path)
        raise BuildAlreadyRunning(pid, held)
    except OSError:
        os.close(fd)
        raise
    lock = _Flock(fd, path, fcntl_mod)
    lock.update_worktree(worktree)
    return lock


def link_legacy_cloud_lock(repo, lock):
    """Point <repo>/tmp/cloud-build.lock at the common-dir lock inode.

    Lane probes flock that legacy path. A symlink makes them the same lock.
    A no-op lock (no fcntl) creates nothing.
    """
    target = getattr(lock, "path", None)
    if target is None or getattr(lock, "noop", False):
        return None
    legacy = Path(repo) / "tmp" / "cloud-build.lock"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    resolved = Path(target).resolve()
    if legacy.is_symlink():
        try:
            if legacy.resolve() == resolved:
                return None
        except OSError:
            pass
        legacy.unlink()
    elif legacy.exists():
        legacy.unlink()
    legacy.symlink_to(resolved)
    return None


def review_reuse_allowed(root, path, sha, memory=None):
    """True only for an accept of this path and diff sha in memory.

    root is ignored. A review-verdicts.json file grants nothing.
    """
    del root
    if not memory:
        return False
    return memory.get((path, sha)) == "accept"


def assert_review_budget(total_chars, prompts):
    if total_chars > REVIEW_CHAR_CEILING:
        raise ReviewBudgetExceeded(
            "review-budget-exceeded: %s characters exceeds %s; split the task"
            % (total_chars, REVIEW_CHAR_CEILING)
        )
    if prompts > REVIEW_PROMPT_CEILING:
        raise ReviewBudgetExceeded(
            "review-budget-exceeded: %s prompts exceeds %s; split the task"
            % (prompts, REVIEW_PROMPT_CEILING)
        )


def estimate_without_history(prices, model="grok-4.7", attempts=1, review_prompts=1):
    """Point estimate when no previous wrap session costs exist.

    Implement assumes 100000 input and 8000 output tokens.
    Each review prompt assumes 12000 input and 500 output tokens.
    low is half of usd. high is double. Prices are USD per 1M tokens.
    """
    row = _price_row(prices, model)
    inn = float(row.get("in") or 0)
    out = float(row.get("out") or 0)
    attempts_n = max(0, int(attempts))
    reviews_n = max(0, int(review_prompts))
    usd = (
        attempts_n * (ASSUME_IMPLEMENT_IN * inn + ASSUME_IMPLEMENT_OUT * out)
        + reviews_n * (ASSUME_REVIEW_IN * inn + ASSUME_REVIEW_OUT * out)
    ) / 1_000_000
    basis = (
        "no-history implement %d in + %d out, review %d in + %d out, model %s"
        % (ASSUME_IMPLEMENT_IN, ASSUME_IMPLEMENT_OUT, ASSUME_REVIEW_IN, ASSUME_REVIEW_OUT, model)
    )
    return {"usd": usd, "low": usd / 2.0, "high": usd * 2.0, "basis": basis}


def load_price_table(path=None):
    if path is None:
        path = Path(__file__).resolve().parents[1] / "data" / "model-prices.json"
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    models = data.get("models") if isinstance(data, dict) else None
    return models if isinstance(models, dict) else {}


def _strip_build(model):
    text = str(model or "").strip()
    if text.endswith("-build"):
        return text[: -len("-build")]
    return text


def _price_row(prices, model):
    if not isinstance(prices, dict):
        return {}
    name = _strip_build(model) or "grok-4.7"
    row = prices.get(name)
    if isinstance(row, dict):
        return row
    row = prices.get(model)
    if isinstance(row, dict):
        return row
    return {}


def _median(values):
    return _percentile(values, 0.50)


def _p90(values):
    return _percentile(values, 0.90)


def _percentile(values, fraction):
    ordered = sorted(float(item) for item in values)
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * fraction
    lo = int(rank)
    hi = min(lo + 1, len(ordered) - 1)
    mix = rank - lo
    return ordered[lo] * (1.0 - mix) + ordered[hi] * mix


def _history_costs():
    """Per-session USD from usage.json whose cwd contains /cloud-build/."""
    found = []
    roots = []
    grok_home = os.environ.get("GROK_HOME", "").strip()
    if grok_home:
        roots.append(Path(grok_home) / "sessions")
    home = os.environ.get("HOME", "").strip()
    if home:
        roots.append(Path(home) / ".grok" / "sessions")
    seen = set()
    for root in roots:
        if not root.is_dir():
            continue
        try:
            children = list(root.iterdir())
        except OSError:
            continue
        for child in children:
            if "cloud-build" not in urllib.parse.unquote(child.name):
                continue
            try:
                sessions = list(child.iterdir())
            except OSError:
                continue
            for session in sessions:
                usage = session / "usage.json"
                if not usage.is_file():
                    continue
                key = str(usage.resolve()) if usage.exists() else str(usage)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    data = json.loads(usage.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, json.JSONDecodeError):
                    continue
                session_obj = data.get("session") if isinstance(data, dict) else None
                if not isinstance(session_obj, dict):
                    continue
                ticks = session_obj.get("costUsdTicks")
                if ticks is None:
                    continue
                try:
                    usd = float(ticks) / 1e10
                except (TypeError, ValueError):
                    continue
                phase = str(session_obj.get("phase") or "")
                found.append((usage.stat().st_mtime, usd, phase))
    found.sort(key=lambda item: item[0], reverse=True)
    recent = found[:40]
    implement = [usd for _mtime, usd, phase in recent if phase == "implement"]
    review = [usd for _mtime, usd, phase in recent if phase == "review"]
    pooled = [usd for _mtime, usd, _phase in recent]
    return {"implement": implement, "review": review, "all": pooled}


def estimate_for_run(prices, model="grok-4.7", attempts=1, review_prompts=1):
    """Historical medians when they exist, otherwise the no-history formula."""
    hist = _history_costs()
    pooled = hist["all"]
    if not pooled:
        return estimate_without_history(
            prices, model=model, attempts=attempts, review_prompts=review_prompts
        )
    implement = hist["implement"] or pooled
    review = hist["review"] or pooled
    med_i = _median(implement)
    med_r = _median(review)
    usd = med_i * int(attempts) + med_r * int(review_prompts)
    high = _p90(implement) * int(attempts) + _p90(review) * int(review_prompts)
    basis = "history median implement %.6f review %.6f sessions %d" % (
        med_i,
        med_r,
        len(pooled),
    )
    return {"usd": usd, "low": usd / 2.0, "high": high, "basis": basis}


def format_estimate_line(est, attempts):
    return (
        "cost estimate: ~$%s (range $%s-$%s) for %d attempt(s) + per-file review; basis: %s"
        % (_money(est["usd"]), _money(est["low"]), _money(est["high"]), int(attempts), est["basis"])
    )


def _money(value):
    text = ("%.6f" % float(value)).rstrip("0").rstrip(".")
    return text or "0"


def estimate_is_confirmed(args=None):
    """False only for an interactive decline. Pipes proceed without a prompt."""
    if args is not None and getattr(args, "yes", False):
        return True
    yes = os.environ.get("PFY_BUILD_YES", "").strip().lower()
    if yes in {"1", "true", "yes"}:
        return True
    ci = os.environ.get("CI", "").strip().lower()
    if ci in {"1", "true", "yes"}:
        return True
    try:
        interactive = sys_isatty()
    except Exception:
        interactive = False
    if not interactive:
        return True
    import sys

    print("Proceed? [y/N]", file=sys.stderr, flush=True)
    try:
        answer = sys.stdin.readline()
    except Exception:
        return False
    return answer.strip().lower() in {"y", "yes"}


def sys_isatty():
    import sys

    return bool(sys.stdin.isatty() and sys.stderr.isatty())


def _split_index(window):
    """Cut so the next part starts at a hunk or diff marker, else a new line."""
    cuts = []
    for marker in ("\n@@", "\ndiff --git "):
        found = window.rfind(marker)
        if found > 0:
            cuts.append(found + 1)
    if cuts:
        return max(cuts)
    newline = window.rfind("\n")
    if newline >= 0:
        return newline + 1
    return 0


def _split_text(text, cap):
    if len(text) <= cap:
        return [text]
    parts = []
    rest = text
    while rest:
        if len(rest) <= cap:
            parts.append(rest)
            break
        window = rest[:cap]
        cut = _split_index(window)
        if cut <= 0:
            cut = cap
        if cut > len(rest):
            cut = len(rest)
        parts.append(rest[:cut])
        rest = rest[cut:]
    return parts


def pack_review_prompts(files, cap, pack_multiple=True):
    """Sort by path, greedy-pack by len(text), split a file only when it alone exceeds cap.

    Parts of a split file are not packed back together. Each item has path,
    text, part (1-based), and parts (total). Concatenating a file's part
    texts returns the original text.
    """
    prepared = []
    ordered = sorted(list(files or []), key=lambda item: item.get("path") or "")
    for item in ordered:
        path = item.get("path") or ""
        text = item.get("text") or ""
        if len(text) <= cap:
            prepared.append({"path": path, "text": text, "part": 1, "parts": 1, "solo": False})
            continue
        chunks = _split_text(text, cap)
        total = len(chunks)
        for index, chunk in enumerate(chunks, 1):
            prepared.append(
                {"path": path, "text": chunk, "part": index, "parts": total, "solo": True}
            )
    packs = []
    current = []
    size = 0

    def flush():
        nonlocal current, size
        if current:
            packs.append(current)
        current = []
        size = 0

    for item in prepared:
        if item["solo"] or not pack_multiple:
            flush()
            packs.append([{key: item[key] for key in ("path", "text", "part", "parts")}])
            continue
        if current and size + len(item["text"]) > cap:
            flush()
        current.append({key: item[key] for key in ("path", "text", "part", "parts")})
        size += len(item["text"])
    flush()
    return packs


def diff_sha(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def file_part_label(item):
    path = item.get("path") or ""
    if int(item.get("parts") or 1) > 1:
        return "%s part %d/%d" % (path, int(item.get("part") or 1), int(item.get("parts") or 1))
    return path


def round_manifest(file_diffs):
    lines = []
    for path, text in file_diffs:
        added = 0
        removed = 0
        for line in (text or "").splitlines():
            if line.startswith("+++") or line.startswith("---"):
                continue
            if line.startswith("+"):
                added += 1
            elif line.startswith("-"):
                removed += 1
        lines.append("%s +%d -%d" % (path, added, removed))
    return "\n".join(lines)


def review_preamble(label, other_paths, manifest):
    others = ", ".join(other_paths) if other_paths else "(none)"
    return (
        "You are reviewing one file of a multi-file change: %s.\n"
        "Other files in this round: %s\n"
        "Judge only this file's change: it must be correct, safe, consistent with the task, and not widen it.\n"
        "Do not reject because this file alone does not implement the whole task.\n"
        "Round manifest:\n%s\n" % (label, others, manifest or "(empty)")
    )


def split_diff_by_file(diff_text):
    """Split a unified diff into (path, chunk) pairs. Chunks keep the diff header."""
    text = diff_text or ""
    if "diff --git " not in text:
        return []
    pieces = re.split(r"(?m)(?=^diff --git )", text)
    found = []
    for piece in pieces:
        if not piece.startswith("diff --git "):
            continue
        first = piece.splitlines()[0]
        match = re.search(r" b/(.+)$", first)
        path = match.group(1).strip() if match else ""
        found.append((path, piece if piece.endswith("\n") or text.endswith(piece) else piece))
    return found


def is_generated_artifact(rel):
    """Untracked build output, caches, bytecode, and *.so under build/."""
    text = (rel or "").replace("\\", "/").strip("/")
    if not text:
        return False
    parts = text.split("/")
    for part in parts:
        if part in _GENERATED_DIRS or part.endswith(".egg-info"):
            return True
    if text.endswith(".pyc"):
        return True
    if text.endswith(".so") and "build" in parts:
        return True
    return False


def _git(repo, args, timeout=60):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _own_toplevel(worktree):
    try:
        proc = _git(worktree, ["rev-parse", "--show-toplevel"])
    except (OSError, subprocess.TimeoutExpired):
        return False
    if proc.returncode != 0 or not (proc.stdout or "").strip():
        return False
    try:
        return Path(proc.stdout.strip()).resolve() == Path(worktree).resolve()
    except OSError:
        return False


def tracked_at_base(worktree):
    """Paths tracked in this worktree. A directory that is not its own repo yields nothing."""
    if not _own_toplevel(worktree):
        return set()
    try:
        proc = _git(worktree, ["ls-files", "-z"])
    except (OSError, subprocess.TimeoutExpired):
        return set()
    found = set()
    for part in (proc.stdout or "").split("\0"):
        rel = part.strip().replace("\\", "/")
        if rel:
            found.add(rel)
    return found


def partition_untracked_generated(worktree, paths, tracked=None):
    """Return (kept, excluded). Tracked-at-base paths stay even if they look generated."""
    if tracked is None:
        tracked = tracked_at_base(worktree)
    kept = []
    excluded = []
    for rel in paths or []:
        norm = (rel or "").replace("\\", "/")
        if norm and norm not in tracked and is_generated_artifact(norm):
            excluded.append(norm)
        else:
            kept.append(rel)
    return kept, excluded


def excluded_generated_receipt(paths):
    names = list(paths or [])
    return {"count": len(names), "paths": names[:20]}


def head_blob(worktree, rel):
    """Text at HEAD, None if the path is new, '' when this dir is not its own repo."""
    if not _own_toplevel(worktree):
        return ""
    try:
        proc = _git(worktree, ["show", "HEAD:%s" % rel])
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if proc.returncode != 0:
        return None
    return proc.stdout


def _meaningful_ignore(text):
    found = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        found.append(stripped)
    return found


def _ignore_match(pattern, rel):
    pat = (pattern or "").strip()
    if not pat or pat.startswith("#"):
        return False
    anchored = pat.startswith("/")
    if anchored:
        pat = pat[1:]
    directory = pat.endswith("/")
    if directory:
        pat = pat[:-1]
    rel = (rel or "").replace("\\", "/")
    parts = [part for part in rel.split("/") if part]
    pat_parts = [part for part in pat.split("/") if part]
    if directory:
        if anchored:
            return parts[: len(pat_parts)] == pat_parts
        for index in range(len(parts)):
            if parts[index : index + len(pat_parts)] == pat_parts:
                return True
        return False
    from fnmatch import fnmatch

    if anchored:
        return fnmatch(rel, pat)
    if fnmatch(rel, pat) or fnmatch(parts[-1] if parts else "", pat):
        return True
    for index in range(len(parts)):
        if fnmatch("/".join(parts[index:]), pat):
            return True
    return False


def _generated_pattern(pattern):
    token = pattern.strip().strip("/")
    name = token.split("/")[-1]
    if name in _GENERATED_DIRS or name.endswith(".egg-info"):
        return True
    if name in {"*.pyc", "*.egg-info"} or token.endswith(".pyc"):
        return True
    if name in {"*.so", "*.so"} and "build" in token.split("/"):
        return True
    return False


def _ignore_addition_allowed(pattern, tracked):
    if pattern.startswith("!"):
        return False
    if pattern.strip() in _DANGEROUS_PATTERNS:
        return False
    for probe in _TEST_PROBES:
        if _ignore_match(pattern, probe):
            return False
    for path in tracked or ():
        if _ignore_match(pattern, path):
            return False
    bare = pattern.strip().lstrip("/")
    if bare == "tests" or bare.startswith("tests/") or bare.startswith("tests\\"):
        return False
    if _generated_pattern(pattern):
        return True
    return True


def gitignore_change_allowed(old, new, tracked):
    old_lines = _meaningful_ignore(old or "")
    new_lines = _meaningful_ignore(new or "")
    remaining = list(new_lines)
    for line in old_lines:
        if line not in remaining:
            return False
        remaining.remove(line)
    for line in remaining:
        if not _ignore_addition_allowed(line, tracked):
            return False
    return True


def _toml_tables(text):
    tables = {}
    current = None
    body = []

    def flush():
        nonlocal current, body
        if current is None:
            return
        tables[current] = "\n".join(body).strip()
        current = None
        body = []

    for line in (text or "").splitlines():
        if line.strip().startswith("[["):
            if current is not None:
                body.append(line)
            continue
        match = _TABLE_RE.match(line)
        if match:
            flush()
            current = match.group(1).strip()
            body = []
            continue
        if current is not None:
            body.append(line)
    flush()
    return tables


def _protected_table(name):
    low = (name or "").strip().lower()
    for prefix in (
        "tool.pytest",
        "tool.unittest",
        "tool.coverage",
        "tool.tox",
        "tool.hatch.envs",
    ):
        if low == prefix or low.startswith(prefix + "."):
            return True
    return False


def _test_dep_keys(body):
    found = {}
    for line in (body or "").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip().strip("\"'")
        if key == "test" or key.startswith("test"):
            found[key] = value.strip()
    return found


def pyproject_change_allowed(old, new):
    old_tables = _toml_tables(old or "")
    new_tables = _toml_tables(new or "")
    for name in set(old_tables) | set(new_tables):
        low = name.lower()
        if low == "project.optional-dependencies" or low.startswith("project.optional-dependencies."):
            old_keys = _test_dep_keys(old_tables[name]) if name in old_tables else None
            new_keys = _test_dep_keys(new_tables[name]) if name in new_tables else None
            if name not in old_tables and new_keys:
                return False
            if name not in new_tables and old_keys:
                return False
            if (old_keys or {}) != (new_keys or {}):
                return False
            continue
        if _protected_table(name) and old_tables.get(name) != new_tables.get(name):
            return False
    return True


def gate_edit_allowed(worktree, rel):
    """True when a .gitignore or pyproject.toml edit is outside the gate guard.

    conftest, pytest.ini, tox.ini, setup.cfg, sitecustomize, usercustomize,
    and .gitattributes stay protected. Other paths are not decided here.
    """
    name = Path(str(rel).replace("\\", "/")).name
    if name in _FULLY_PROTECTED:
        return False
    if name not in {".gitignore", "pyproject.toml"}:
        return False
    try:
        new = (Path(worktree) / rel).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    old = head_blob(worktree, rel)
    if old is None:
        old = ""
    if name == ".gitignore":
        return gitignore_change_allowed(old, new, tracked_at_base(worktree))
    return pyproject_change_allowed(old, new)


def sigint_grace_seconds(default=20.0):
    raw = os.environ.get("PFY_BUILD_SIGINT_GRACE", "").strip()
    if not raw:
        return float(default)
    try:
        return max(0.0, float(raw))
    except ValueError:
        return float(default)


def _signal_group(pgid, sig):
    if not pgid or pgid <= 0 or pgid == os.getpgrp():
        return
    try:
        os.killpg(pgid, sig)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def _proc_stat_fields(pid):
    """Fields after comm in /proc/pid/stat. None when the proc entry is gone."""
    try:
        raw = Path("/proc/%s/stat" % pid).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    end = raw.rfind(")")
    if end < 0:
        return None
    return raw[end + 2 :].split()


def _group_alive(pgid):
    """True when some member of the group is still running.

    signal 0 succeeds for a zombie the parent has not reaped yet. A leader
    that already exited must not hold the SIGINT grace open.
    """
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
    fields = _proc_stat_fields(pgid)
    if not fields:
        return False
    if fields[0] not in {"Z", "X"}:
        return True
    try:
        entries = list(Path("/proc").iterdir())
    except OSError:
        return True
    for entry in entries:
        if not entry.name.isdigit() or int(entry.name) == int(pgid):
            continue
        member = _proc_stat_fields(entry.name)
        if not member or len(member) < 3 or member[0] in {"Z", "X"}:
            continue
        try:
            member_pgrp = int(member[2])
        except ValueError:
            continue
        if member_pgrp == int(pgid):
            return True
    return False


def _wait_group(pgid, seconds):
    deadline = time.monotonic() + max(0.0, float(seconds))
    while time.monotonic() < deadline:
        if not _group_alive(pgid):
            return True
        time.sleep(0.05)
    return not _group_alive(pgid)


def stop_group_for_timeout(pgid, kill_grace=2.0):
    """SIGINT, wait for a flush, then SIGTERM, then SIGKILL.

    The grace is PFY_BUILD_SIGINT_GRACE seconds (default 20). A process that
    exits on SIGINT does not wait out the grace.
    """
    if not pgid or pgid <= 0 or pgid == os.getpgrp():
        return
    if not _group_alive(pgid):
        return
    _signal_group(pgid, signal.SIGINT)
    if _wait_group(pgid, sigint_grace_seconds()):
        return
    _signal_group(pgid, signal.SIGTERM)
    if _wait_group(pgid, kill_grace):
        return
    _signal_group(pgid, signal.SIGKILL)


def _token(usage, *names):
    for name in names:
        if name in usage and usage.get(name) is not None:
            try:
                return int(usage.get(name) or 0)
            except (TypeError, ValueError):
                return 0
    return 0


def _price_tokens(usage, prices, model):
    row = _price_row(prices, _strip_build(usage.get("model") or usage.get("primaryModelId") or model))
    incoming = _token(usage, "inputTokens", "input_tokens", "promptTokens", "prompt_tokens")
    outgoing = _token(usage, "outputTokens", "output_tokens", "completionTokens")
    cached = _token(usage, "cachedInputTokens", "cached_input_tokens", "cachedTokens", "cached_tokens")
    if cached > incoming:
        cached = incoming
    uncached = incoming - cached
    usd = (
        uncached * float(row.get("in") or 0)
        + cached * float(row.get("cached_in") if row.get("cached_in") is not None else row.get("in") or 0)
        + outgoing * float(row.get("out") or 0)
    ) / 1_000_000
    return usd, incoming, outgoing


def _session_record_from_usage(data, prices, phase):
    session = data.get("session") if isinstance(data, dict) else None
    if not isinstance(session, dict):
        return None
    incoming = _token(session, "inputTokens", "input_tokens", "promptTokens")
    outgoing = _token(session, "outputTokens", "output_tokens")
    ticks = session.get("costUsdTicks")
    if ticks is not None:
        try:
            usd = float(ticks) / 1e10
        except (TypeError, ValueError):
            usd = 0.0
        return {
            "usd": usd,
            "input_tokens": incoming,
            "output_tokens": outgoing,
            "estimated": False,
            "source": "usage.json",
            "phase": phase,
            "model": str(session.get("primaryModelId") or ""),
        }
    usd, incoming, outgoing = _price_tokens(session, prices, "grok-4.7")
    return {
        "usd": usd,
        "input_tokens": incoming,
        "output_tokens": outgoing,
        "estimated": True,
        "source": "usage.json",
        "phase": phase,
        "model": str(session.get("primaryModelId") or ""),
    }


def _last_updates_usage(path):
    last = None
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("usage"), dict):
            last = obj["usage"]
    return last


def session_roots_for(worktree):
    quoted = urllib.parse.quote(str(Path(worktree).resolve()), safe="")
    roots = []
    grok_home = os.environ.get("GROK_HOME", "").strip()
    if grok_home:
        roots.append(Path(grok_home) / "sessions" / quoted)
    home = os.environ.get("HOME", "").strip()
    if home:
        roots.append(Path(home) / ".grok" / "sessions" / quoted)
    unique = []
    seen = set()
    for root in roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        unique.append(root)
    return unique


def collect_call_usage(worktree, started, phase, prices, seen_ids=None):
    """Sessions for this worktree touched at or after the call started.

    Reads usage.json and, if that file is missing, the last usage object in
    updates.jsonl. Does not open auth.json or chat history.
    """
    if worktree is None:
        return []
    rows = []
    skew = float(started) - 1.0
    for root in session_roots_for(worktree):
        if not root.is_dir():
            continue
        try:
            children = list(root.iterdir())
        except OSError:
            continue
        for child in children:
            if not child.is_dir():
                continue
            try:
                mtime = child.stat().st_mtime
            except OSError:
                continue
            usage_path = child / "usage.json"
            updates_path = child / "updates.jsonl"
            touched = mtime >= skew
            if usage_path.is_file():
                try:
                    touched = touched or usage_path.stat().st_mtime >= skew
                except OSError:
                    pass
            elif updates_path.is_file():
                try:
                    touched = touched or updates_path.stat().st_mtime >= skew
                except OSError:
                    pass
            if not touched:
                continue
            ident = child.name
            if seen_ids is not None and ident in seen_ids:
                continue
            record = None
            if usage_path.is_file():
                try:
                    data = json.loads(usage_path.read_text(encoding="utf-8"))
                except (OSError, UnicodeError, json.JSONDecodeError):
                    data = None
                if isinstance(data, dict):
                    record = _session_record_from_usage(data, prices, phase)
            if record is None and updates_path.is_file():
                usage = _last_updates_usage(updates_path)
                if isinstance(usage, dict):
                    usd, incoming, outgoing = _price_tokens(usage, prices, "grok-4.7")
                    record = {
                        "usd": usd,
                        "input_tokens": incoming,
                        "output_tokens": outgoing,
                        "estimated": True,
                        "source": "updates.jsonl",
                        "phase": phase,
                        "model": str(usage.get("model") or usage.get("primaryModelId") or ""),
                    }
            if record is None:
                continue
            record["id"] = ident
            if seen_ids is not None:
                seen_ids.add(ident)
            rows.append(record)
    return rows


def usage_receipt(rows):
    sessions = []
    usd = 0.0
    incoming = 0
    outgoing = 0
    for row in rows or []:
        usd += float(row.get("usd") or 0)
        incoming += int(row.get("input_tokens") or 0)
        outgoing += int(row.get("output_tokens") or 0)
        sessions.append(
            {
                "id": row.get("id"),
                "phase": row.get("phase"),
                "usd": row.get("usd"),
                "estimated": bool(row.get("estimated")),
                "source": row.get("source"),
            }
        )
    return {
        "usd": usd,
        "input_tokens": incoming,
        "output_tokens": outgoing,
        "sessions": sessions,
    }


def format_spend_line(rows):
    payload = usage_receipt(rows)
    estimated = sum(1 for row in rows or [] if row.get("estimated"))
    return "spend $%.2f (%d sessions, %d estimated)" % (
        payload["usd"],
        len(payload["sessions"]),
        estimated,
    )


def changed_symbols(diff_text):
    """def/class names touched by the diff, in first-seen order."""
    found = []
    seen = set()
    for raw in (diff_text or "").splitlines():
        if not raw or raw[:1] not in "+- ":
            continue
        if raw.startswith(("+++", "---")):
            continue
        match = _DEF_LINE.match(raw[1:].strip())
        if not match:
            continue
        name = match.group(1)
        if name in seen:
            continue
        seen.add(name)
        found.append(name)
        if len(found) >= 15:
            break
    return found


def _tool_bin(env_name, program, fallbacks):
    """A set env var is the only candidate, even when the file is missing."""
    if env_name in os.environ:
        raw = os.environ[env_name].strip()
        if not raw:
            return None
        path = Path(raw)
        if path.is_file() and os.access(path, os.X_OK):
            return path
        return None
    found = shutil.which(program)
    if found:
        return Path(found)
    for path in fallbacks:
        if path.is_file() and os.access(path, os.X_OK):
            return path
    return None


def _run_tool(argv, cwd, timeout=12):
    try:
        proc = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return proc.returncode, proc.stdout or ""


def _usable_tool_text(text):
    body = (text or "").strip()
    if not body:
        return ""
    if body.startswith("{") and '"error"' in body[:400]:
        return ""
    return body


def _cm_project(worktree, stdout):
    start = (stdout or "").find("{")
    if start < 0:
        return None
    try:
        data = json.loads(stdout[start:])
    except json.JSONDecodeError:
        return None
    projects = data.get("projects") if isinstance(data, dict) else None
    if not isinstance(projects, list):
        return None
    wanted = {str(Path(worktree).resolve())}
    try:
        top = _git(worktree, ["rev-parse", "--show-toplevel"])
    except (OSError, subprocess.TimeoutExpired):
        top = None
    if top is not None and top.returncode == 0 and (top.stdout or "").strip():
        try:
            wanted.add(str(Path(top.stdout.strip()).resolve()))
        except OSError:
            pass
    for proj in projects:
        if not isinstance(proj, dict):
            continue
        name = str(proj.get("name") or "").strip()
        root = str(proj.get("root_path") or "").strip()
        if not name or not root:
            continue
        try:
            if str(Path(root).resolve()) in wanted:
                return name
        except OSError:
            continue
    return None


def _cm_map(worktree, symbols):
    if not symbols:
        return ""
    home = os.environ.get("HOME") or str(Path.home())
    cache_root = os.environ.get("PFY_TOOL_CACHE") or str(Path(home) / ".cache" / "pfy")
    binary = _tool_bin(
        "PFY_CODEBASE_MEMORY",
        "codebase-memory-mcp",
        [
            Path(cache_root) / "bin" / "codebase-memory-mcp",
            Path.home() / ".local/bin/codebase-memory-mcp",
        ],
    )
    if binary is None:
        return ""
    code, out = _run_tool([str(binary), "cli", "list_projects"], worktree)
    if code != 0:
        return ""
    project = _cm_project(worktree, out)
    if not project:
        return ""
    chunks = []
    for name in symbols:
        code, traced = _run_tool(
            [
                str(binary),
                "cli",
                "trace_path",
                "--function-name",
                name,
                "--project",
                project,
                "--direction",
                "both",
            ],
            worktree,
        )
        usable = _usable_tool_text(traced)
        if code != 0 or not usable:
            continue
        chunks.append(usable)
    return "\n".join(chunks)


def _tsa_map(worktree, paths):
    binary = _tool_bin(
        "PFY_TSA_BIN",
        "tree-sitter-analyzer",
        [Path.home() / "DEVELOP/pfy-mentat/tmp/tree-sitter-analyzer/.venv/bin/tree-sitter-analyzer"],
    )
    if binary is None:
        return ""
    argv = [str(binary), "--change-impact", "--format", "json", "--change-impact-no-tests"]
    for path in (paths or [])[:20]:
        argv.extend(["--change-impact-scope", path])
    code, out = _run_tool(argv, worktree, timeout=20)
    if code != 0:
        return ""
    return _usable_tool_text(out)


def _git_grep_map(worktree, symbols):
    if not symbols:
        return "no changed symbols"
    lines = []
    for name in symbols:
        try:
            proc = _git(worktree, ["grep", "-n", "-I", "-F", "--untracked", "-e", name])
        except (OSError, subprocess.TimeoutExpired):
            continue
        text = (proc.stdout or "").strip()
        if not text:
            continue
        lines.append("symbol %s" % name)
        lines.extend(text.splitlines()[:8])
    if not lines:
        return "no changed symbols"
    return "\n".join(lines)


def _bound_text(text, cap=TAIL_CAP):
    if len(text) <= cap:
        return text
    return text[:cap] + "\n...[impact truncated]\n"


def change_impact_map(worktree, diff_text, paths):
    """Callers and callees for one review. Never raises.

    Prefer codebase-memory-mcp, then Tree-sitter Analyzer --change-impact,
    then git grep of changed symbol names. A missing tool is not a failure.
    """
    try:
        symbols = changed_symbols(diff_text)
        mapped = _cm_map(worktree, symbols)
        if mapped:
            return _bound_text(mapped), "codebase-memory-mcp"
        mapped = _tsa_map(worktree, paths)
        if mapped:
            return _bound_text(mapped), "tree-sitter-analyzer"
        return _bound_text(_git_grep_map(worktree, symbols)), "git-grep"
    except Exception:
        return "no changed symbols", "git-grep"
