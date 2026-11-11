#!/usr/bin/env python3
"""Count full-suite runs and runner-minutes for recent main landings.

Landings are first-parent commits on origin/main. The report joins local
pregate summaries, lane progress files, GitHub Actions jobs, and (when the
API missed a self-hosted job) the runner diag logs.

Baseline for a docs-only landing: about 6 full-suite runs and about 127
runner-minutes (39 min pregate + 44 min branch CI + 44 min main CI).

Stdlib only. Read-only apart from the GitHub response cache. Never prints
diag log bodies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASELINE_FULL = 6
BASELINE_MINUTES = 127.0
BASELINE_TEXT = (
    "about 6 full-suite runs and about 127 runner-minutes per docs-only landing "
    "(39 min pregate + 44 min branch CI + 44 min main CI)"
)
FULL_PREGATE_CHECKS = frozenset({"ubuntu-parity", "eval-structural", "suite"})
SELECTED_PREGATE_CHECKS = frozenset({"ci-parity"})
# A progress line has no check table. At or above this wall time, treat it as
# one full-suite pregate. Below it, keep the minutes and do not call it a suite.
PROGRESS_FULL_SECONDS = 600
RANK = {"other": 0, "selected": 1, "full": 2}
REPO_SLUG = "themark-net/pfy-deanery"
API = "https://api.github.com"
MIN_REMAINING = 8
USER_AGENT = "pfy-pipeline-retro"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_utc(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    text = value.replace("Z", "+00:00")
    try:
        stamp = datetime.fromisoformat(text)
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc)


def _zone_for(label: str):
    name = label.upper()
    if name == "PST":
        return timezone(timedelta(hours=-8))
    if name == "PDT":
        return timezone(timedelta(hours=-7))
    if name in ("UTC", "GMT", "Z"):
        return timezone.utc
    if name == "PT":
        # Progress notes sometimes say PT. November landings are PST.
        return timezone(timedelta(hours=-8))
    return None


def parse_pregate_summary(text: str) -> dict | None:
    """Parse one pregate-summary.md. None when the ref line has no sha."""
    ref = re.search(r"^- ref:.*$", text, re.M)
    if not ref:
        return None
    hexes = re.findall(r"`([0-9a-fA-F]{7,40})`", ref.group(0))
    if not hexes:
        return None
    sha = hexes[-1].lower()
    wall_m = re.search(r"^- wall seconds:\s*(\d+)\s*$", text, re.M)
    wall_s = int(wall_m.group(1)) if wall_m else 0
    run_m = re.search(r"^- run id:\s*`([^`]+)`", text, re.M)
    started = None
    stamp = re.search(
        r"^- started \(local\):\s*(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})(?::(\d{2}))?\s+([A-Za-z]{2,4})\s*$",
        text,
        re.M,
    )
    if stamp:
        naive = datetime.strptime(
            f"{stamp.group(1)} {stamp.group(2)}:{stamp.group(3) or '00'}",
            "%Y-%m-%d %H:%M:%S",
        )
        zone = _zone_for(stamp.group(4))
        if zone is not None:
            started = naive.replace(tzinfo=zone).astimezone(timezone.utc)
    checks = []
    for status, name in re.findall(
        r"^\| (PASS|FAIL|SKIP|NOTE) \| ([^|]+?) \|",
        text,
        re.M,
    ):
        checks.append({"status": status, "name": name.strip()})
    return {
        "sha": sha,
        "run_id": run_m.group(1).strip() if run_m else "",
        "wall_s": wall_s,
        "started": started,
        "checks": checks,
        "source": "summary",
    }


def parse_progress_text(text: str) -> list[dict]:
    """Lines shaped like 'pregate PASS <sha>' with an optional 'in <n>s'."""
    rows = []
    seen = set()
    for line in text.splitlines():
        if not re.search(r"pregate\s+PASS\b", line, re.I):
            continue
        found = re.search(
            r"pregate\s+PASS(?:\s+for)?\s+(?:sha=)?([0-9a-fA-F]{7,40})\b",
            line,
            re.I,
        )
        if not found:
            continue
        duration = re.search(r"\bin\s+(\d+)\s*s\b", line, re.I)
        raw = line.strip()
        if raw in seen:
            continue
        seen.add(raw)
        rows.append(
            {
                "sha": found.group(1).lower(),
                "wall_s": int(duration.group(1)) if duration else None,
                "raw": raw,
                "source": "progress",
            }
        )
    return rows


def sha_match(left: str, right: str) -> bool:
    a = (left or "").lower()
    b = (right or "").lower()
    if not a or not b:
        return False
    if a == b:
        return True
    if len(a) < 40 and b.startswith(a):
        return True
    if len(b) < 40 and a.startswith(b):
        return True
    return False


_RUN_TESTS_VALUE_FLAGS = {"-j", "--jobs", "--root", "--receipt", "--run-dir"}


def _run_tests_kind(code: str) -> str | None:
    """full when scripts/run_tests.py has no module args. selected when it does.

    A bare `python3 scripts/run_tests.py` is the nightly full suite. Flags such
    as `--receipt` are not modules. A positional token is a module list.
    """
    saw_full = False
    saw_selected = False
    for raw in code.splitlines():
        if "run_tests.py" not in raw:
            continue
        match = re.search(r"(?:^|\s)(\S*run_tests\.py)\b(.*)$", raw)
        if not match:
            continue
        tokens = match.group(2).split()
        index = 0
        positional = False
        while index < len(tokens):
            token = tokens[index]
            if token in _RUN_TESTS_VALUE_FLAGS:
                index += 2
                continue
            if token.startswith("-"):
                index += 1
                continue
            positional = True
            break
        if positional:
            saw_selected = True
        else:
            saw_full = True
    if saw_full:
        return "full"
    if saw_selected:
        return "selected"
    return None


def classify_workflow_text(text: str) -> dict[str, str]:
    """Map a workflow's job display name to full, selected, or other.

    full: `unittest discover -s tests`, or `scripts/run_tests.py` with no
    module arguments (the nightly backstop).
    selected: `scripts/ci_selected_tests.sh`, a named `unittest` module list,
    or `run_tests.py` with module arguments.
    Comments are ignored. A job that does both is full.
    """
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.match(r"^jobs:\s*(?:#.*)?$", line):
            start = i + 1
            break
    if start is None:
        return {}
    section: list[str] = []
    for line in lines[start:]:
        if line.startswith("#") or line.strip() == "":
            section.append(line)
            continue
        if not line.startswith(" "):
            break
        section.append(line)
    idxs = [
        i
        for i, line in enumerate(section)
        if re.match(r"^  [A-Za-z0-9_-]+:\s*(?:#.*)?$", line)
    ]
    out: dict[str, str] = {}
    for n, i in enumerate(idxs):
        end = idxs[n + 1] if n + 1 < len(idxs) else len(section)
        chunk_lines = section[i:end]
        chunk = "\n".join(chunk_lines)
        key_m = re.match(r"^  ([A-Za-z0-9_-]+):", chunk_lines[0])
        if not key_m:
            continue
        name_m = re.search(r"^    name:\s*[\"']?(.+?)[\"']?\s*$", chunk, re.M)
        display = name_m.group(1).strip() if name_m else key_m.group(1)
        code = "\n".join(line.split("#", 1)[0] for line in chunk_lines)
        run_kind = _run_tests_kind(code)
        if re.search(r"unittest\s+discover\s+-s\s+tests\b", code) or run_kind == "full":
            kind = "full"
        elif (
            run_kind == "selected"
            or re.search(r"ci_selected_tests\.sh\b", code)
            or re.search(r"\bunittest\b", code)
        ):
            kind = "selected"
        else:
            kind = "other"
        prev = out.get(display)
        if prev is None or RANK[kind] > RANK[prev]:
            out[display] = kind
    return out


def load_job_classes(workflows_dir: Path) -> dict[str, str]:
    merged: dict[str, str] = {}
    if not workflows_dir.is_dir():
        return merged
    paths = sorted(workflows_dir.glob("*.yml")) + sorted(workflows_dir.glob("*.yaml"))
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        for name, kind in classify_workflow_text(text).items():
            prev = merged.get(name)
            if prev is None or RANK[kind] > RANK[prev]:
                merged[name] = kind
    return merged


def _owned_by(sha: str, landing: dict, landings: list[dict]) -> bool:
    owners = _owners(sha, landings)
    return len(owners) == 1 and owners[0] is landing


def _owners(sha: str, landings: list[dict]) -> list[dict]:
    hits = []
    for landing in landings:
        if sha_match(sha, landing["sha"]):
            hits.append(landing)
            continue
        if any(sha_match(sha, extra) for extra in landing.get("extra_shas") or []):
            hits.append(landing)
    return hits


def _minutes(seconds: float) -> float:
    return round(seconds / 60.0, 1)


def build_landing_rows(
    landings: list[dict],
    pregates: list[dict],
    progress: list[dict],
    ci_jobs: list[dict],
) -> list[dict]:
    """Join parsed runs onto landings. One row per landing, input order."""
    summary_shas = [item["sha"] for item in pregates if item.get("sha")]
    rows = []
    for landing in landings:
        full_sources: list[str] = []
        selected = 0
        pregate_s = 0.0
        branch_s = 0.0
        main_s = 0.0
        self_s = 0.0
        gh_s = 0.0
        pregate_runs = 0
        pregate_checks: Counter = Counter()
        starts: list[datetime] = []
        main_done: list[datetime] = []

        for item in pregates:
            if not _owned_by(item["sha"], landing, landings):
                continue
            pregate_runs += 1
            pregate_s += item.get("wall_s") or 0
            self_s += item.get("wall_s") or 0
            if item.get("started"):
                starts.append(item["started"])
            for check in item.get("checks") or []:
                if check["status"] in ("PASS", "FAIL"):
                    pregate_checks[check["name"]] += 1
            full_here = [
                check
                for check in item.get("checks") or []
                if check["name"] in FULL_PREGATE_CHECKS and check["status"] in ("PASS", "FAIL")
            ]
            if full_here:
                for check in full_here:
                    full_sources.append(f"pregate:{check['name']}")
            elif any(
                check["name"] in SELECTED_PREGATE_CHECKS and check["status"] in ("PASS", "FAIL")
                for check in item.get("checks") or []
            ):
                selected += 1

        for item in progress:
            if any(sha_match(item["sha"], summary) for summary in summary_shas):
                continue
            if not _owned_by(item["sha"], landing, landings):
                continue
            wall = item.get("wall_s")
            pregate_runs += 1
            if wall is None:
                continue
            pregate_s += wall
            self_s += wall
            if wall >= PROGRESS_FULL_SECONDS:
                full_sources.append("pregate:progress")

        schedule_s = 0.0
        for job in ci_jobs:
            if not _owned_by(job["sha"], landing, landings):
                continue
            seconds = float(job.get("seconds") or 0)
            host = job.get("host") or "github-hosted"
            lane = job.get("lane") or "branch"
            # A clock on main is not this landing's pipeline. Keep the minutes
            # visible and out of the baseline total.
            if lane == "schedule":
                schedule_s += seconds
                continue
            if host == "self-hosted":
                self_s += seconds
            else:
                gh_s += seconds
            if lane == "main":
                main_s += seconds
                if job.get("completed"):
                    main_done.append(job["completed"])
            else:
                branch_s += seconds
            # A cancel in the first minute did not run the suite.
            if (job.get("conclusion") or "").lower() == "cancelled":
                continue
            kind = job.get("kind") or "other"
            if kind == "full":
                full_sources.append(f"ci:{job.get('name') or 'job'}")
            elif kind == "selected":
                selected += 1

        counts = Counter(full_sources)
        total_s = pregate_s + branch_s + main_s
        # schedule_s is reported beside the baseline total, not inside it.
        total_m = _minutes(total_s)
        full_n = len(full_sources)
        reasons = []
        if full_n > BASELINE_FULL:
            reasons.append(f"full-suite runs {full_n} > {BASELINE_FULL}")
        if total_m > BASELINE_MINUTES:
            reasons.append(f"runner-minutes {total_m} > {BASELINE_MINUTES}")
        wall_s = None
        if starts:
            end = max(main_done) if main_done else landing.get("committed_at")
            if end is not None:
                wall_s = int((end - min(starts)).total_seconds())
        rows.append(
            {
                "sha": landing["sha"],
                "subject": landing.get("subject") or "",
                "committed_at": _iso(landing.get("committed_at")),
                "full_suite_runs": full_n,
                "selected_suite_runs": selected,
                "pregate_runs": pregate_runs,
                "pregate_minutes": _minutes(pregate_s),
                "branch_ci_minutes": _minutes(branch_s),
                "main_ci_minutes": _minutes(main_s),
                "self_hosted_minutes": _minutes(self_s),
                "github_hosted_minutes": _minutes(gh_s),
                "runner_minutes": total_m,
                "schedule_minutes": _minutes(schedule_s),
                "pregate_checks": [f"{name} x{count}" for name, count in sorted(pregate_checks.items())],
                "wall_to_main_s": wall_s,
                "duplicated": full_n >= 2,
                "duplicate_sources": [f"{name} x{count}" for name, count in sorted(counts.items())],
                "over_baseline": bool(reasons),
                "over_reasons": reasons,
            }
        )
    return rows


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_report(
    rows: list[dict],
    github_ok: bool,
    github_note: str,
    job_classes: dict[str, str],
) -> dict:
    return {
        "baseline": BASELINE_TEXT,
        "baseline_full_suite_runs": BASELINE_FULL,
        "baseline_runner_minutes": BASELINE_MINUTES,
        "github_ok": github_ok,
        "github_note": github_note,
        "full_job_names": sorted(name for name, kind in job_classes.items() if kind == "full"),
        "landings": rows,
    }


def format_table(report: dict) -> str:
    lines = [
        f"Baseline: {report['baseline']}.",
        f"GitHub: {'ok' if report.get('github_ok') else 'degraded'}"
        + (f" ({report['github_note']})" if report.get("github_note") else ""),
        "",
        f"{'sha':<10} {'full':>4} {'sel':>4} {'pre':>7} {'branch':>7} {'main':>7} "
        f"{'self':>7} {'gh':>7} {'total':>7} {'wall_s':>8} {'dup':>3} {'over':>4}  subject",
    ]
    for row in report["landings"]:
        wall = "" if row["wall_to_main_s"] is None else str(row["wall_to_main_s"])
        subject = (row["subject"] or "").replace("\n", " ")
        if len(subject) > 48:
            subject = subject[:45] + "..."
        lines.append(
            f"{row['sha'][:10]:<10} {row['full_suite_runs']:>4} {row['selected_suite_runs']:>4} "
            f"{row['pregate_minutes']:>7.1f} {row['branch_ci_minutes']:>7.1f} {row['main_ci_minutes']:>7.1f} "
            f"{row['self_hosted_minutes']:>7.1f} {row['github_hosted_minutes']:>7.1f} "
            f"{row['runner_minutes']:>7.1f} {wall:>8} "
            f"{'yes' if row['duplicated'] else 'no':>3} "
            f"{'yes' if row['over_baseline'] else 'no':>4}  {subject}"
        )
    lines.append("")
    for row in report["landings"]:
        if row["duplicated"]:
            lines.append(
                f"DUP {row['sha'][:10]} full={row['full_suite_runs']} "
                + ", ".join(row["duplicate_sources"])
            )
        if row["over_baseline"]:
            lines.append(f"OVER {row['sha'][:10]} " + "; ".join(row["over_reasons"]))
    return "\n".join(lines).rstrip() + "\n"


class GitHubClient:
    """Unauthenticated GET with a file cache and a remaining-call floor."""

    def __init__(self, cache_dir: Path, opener=None, min_remaining: int = MIN_REMAINING):
        self.cache_dir = Path(cache_dir)
        self.opener = opener or urllib.request.urlopen
        self.min_remaining = min_remaining
        self.remaining = 60
        self.requests = 0
        self.note = ""
        self.ok = True
        self.last_headers: dict[str, str] = {}

    def _paths(self, url: str) -> tuple[Path, Path]:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
        return self.cache_dir / f"{digest}.json", self.cache_dir / f"{digest}.hdr.json"

    def _read_cache(self, url: str) -> dict | None:
        body_path, hdr_path = self._paths(url)
        if not body_path.is_file():
            return None
        try:
            payload = json.loads(body_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        self.last_headers = {}
        if hdr_path.is_file():
            try:
                loaded = json.loads(hdr_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self.last_headers = {str(k): str(v) for k, v in loaded.items()}
            except (OSError, json.JSONDecodeError):
                self.last_headers = {}
        return payload if isinstance(payload, dict) else None

    def get(self, url: str) -> dict | None:
        cached = self._read_cache(url)
        if cached is not None:
            return cached
        if self.remaining < self.min_remaining:
            self.note = "stopped to stay under the 60/hour unauthenticated limit"
            if cached is None:
                self.ok = False
            return cached
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": USER_AGENT,
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with self.opener(request, timeout=30) as response:
                raw = response.read()
                headers = {k: v for k, v in response.headers.items()}
                remaining = headers.get("X-RateLimit-Remaining")
                if remaining is not None and str(remaining).isdigit():
                    self.remaining = int(remaining)
        except urllib.error.HTTPError as exc:
            self.ok = False
            if exc.code in (403, 429):
                self.note = f"github rate limited (HTTP {exc.code}); using cache"
            else:
                self.note = f"github unavailable (HTTP {exc.code})"
            return cached
        except (urllib.error.URLError, TimeoutError, OSError):
            self.ok = False
            self.note = "github unavailable; using cache" if cached else "github unavailable; no cache"
            return cached
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.ok = False
            self.note = "github returned a non-json body"
            return cached
        if not isinstance(payload, dict):
            self.ok = False
            self.note = "github returned an unexpected body"
            return cached
        self.requests += 1
        self.last_headers = {str(k): str(v) for k, v in headers.items()}
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            body_path, hdr_path = self._paths(url)
            body_path.write_text(json.dumps(payload), encoding="utf-8")
            hdr_path.write_text(json.dumps(self.last_headers), encoding="utf-8")
        except OSError:
            pass
        return payload


def fetch_runs_and_jobs(
    client: GitHubClient,
    repo: str,
    wanted: set[str],
    stop_before: datetime | None,
) -> tuple[list[dict], set[str]]:
    """Return workflow runs for the wanted SHAs, plus the SHAs whose query returned.

    Each item is {"run": <workflow run>, "jobs": [job, ...]}.
    The set is every SHA the API answered, including an empty run list.
    A SHA left out of the set was not fetched. `stop_before` is unused.
    """
    del stop_before
    runs: list[dict] = []
    known: set[str] = set()
    seen_ids = set()
    for sha in sorted(wanted):
        payload = client.get(f"{API}/repos/{repo}/actions/runs?head_sha={sha}&per_page=20")
        if payload is None:
            continue
        known.add(sha)
        for run in payload.get("workflow_runs") or []:
            run_id = run.get("id")
            if run_id in seen_ids:
                continue
            seen_ids.add(run_id)
            runs.append(run)
    matched = runs
    out = []
    fetched = 0
    for run in matched:
        if fetched >= 40:
            client.note = (client.note + "; " if client.note else "") + "stopped after 40 job lists"
            break
        run_id = run.get("id")
        if not run_id:
            continue
        jobs_payload = client.get(f"{API}/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100")
        fetched += 1
        jobs = []
        if jobs_payload:
            jobs = jobs_payload.get("jobs") or []
        out.append({"run": run, "jobs": jobs})
    return out, known


def ci_jobs_from_payloads(items: list[dict], job_classes: dict[str, str]) -> list[dict]:
    jobs_out = []
    for item in items:
        run = item["run"]
        sha = (run.get("head_sha") or "").lower()
        event = run.get("event") or ""
        branch = run.get("head_branch") or ""
        if event == "schedule":
            lane = "schedule"
        elif event in ("push", "workflow_dispatch") and branch in ("main", "master"):
            lane = "main"
        else:
            lane = "branch"
        for job in item.get("jobs") or []:
            conclusion = (job.get("conclusion") or "").lower()
            if conclusion == "skipped":
                continue
            started = parse_utc(job.get("started_at"))
            completed = parse_utc(job.get("completed_at"))
            if started is None and conclusion == "":
                continue
            seconds = 0.0
            if started and completed:
                seconds = max(0.0, (completed - started).total_seconds())
            labels = [str(label).lower() for label in (job.get("labels") or [])]
            runner = str(job.get("runner_name") or "").lower()
            host = "self-hosted" if ("self-hosted" in labels or "self-hosted" in runner) else "github-hosted"
            name = job.get("name") or ""
            jobs_out.append(
                {
                    "sha": sha,
                    "name": name,
                    "host": host,
                    "seconds": seconds,
                    "lane": lane,
                    "kind": job_classes.get(name, "other"),
                    "started": started,
                    "completed": completed,
                    "conclusion": conclusion,
                    "run_id": run.get("id"),
                }
            )
    return jobs_out


def diag_self_hosted_shas(diag_dir: Path, shas: set[str], not_before: datetime | None) -> set[str]:
    """SHAs that are the job's own context sha in a self-hosted full-discover log.

    A landing sha that merely appears somewhere in the log does not count.
    The function returns shas only. It does not return log text.
    """
    found: set[str] = set()
    if not diag_dir.is_dir() or not shas:
        return found
    context_sha = re.compile(r'"k"\s*:\s*"sha"\s*,?\s*\n\s*"v"\s*:\s*"([0-9a-f]{40})"')
    files = sorted(diag_dir.glob("Worker_*.log"), key=lambda path: path.stat().st_mtime if path.exists() else 0)
    cutoff = None
    if not_before is not None:
        cutoff = not_before.timestamp() - 3 * 24 * 3600
    checked = 0
    for path in reversed(files):
        if checked >= 40:
            break
        try:
            stat = path.stat()
        except OSError:
            continue
        if cutoff is not None and stat.st_mtime < cutoff:
            continue
        if stat.st_size > 20_000_000:
            continue
        checked += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        normalized = text.replace("\\n", "\n")
        if "unittest discover -s tests" not in normalized:
            continue
        if "self-hosted" not in text and "G0 (self-hosted" not in text:
            continue
        for sha in context_sha.findall(text):
            if sha in shas:
                found.add(sha)
    return found


def git_output(repo: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout


def load_landings(repo: Path, limit: int, since: str | None) -> list[dict]:
    cmd = ["log", "--first-parent", "--format=%H%x1f%cI%x1f%P%x1f%s"]
    if since:
        cmd += ["--since", since]
    else:
        cmd += ["-n", str(limit)]
    ref = "origin/main"
    try:
        git_output(repo, ["rev-parse", "--verify", "--quiet", ref])
    except subprocess.CalledProcessError:
        ref = "main"
    raw = git_output(repo, cmd + [ref])
    landings = []
    shas = set()
    for line in raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\x1f", 3)
        if len(parts) < 4:
            continue
        sha, committed, parents, subject = parts
        sha = sha.strip().lower()
        shas.add(sha)
        parent_list = parents.split()
        extra = []
        if len(parent_list) >= 2:
            second = parent_list[1].lower()
            extra.append(second)
        landings.append(
            {
                "sha": sha,
                "committed_at": parse_utc(committed.strip()),
                "subject": subject.strip(),
                "extra_shas": extra,
            }
        )
    # A second parent that is itself a landing keeps its own CI. Do not steal it.
    for landing in landings:
        landing["extra_shas"] = [sha for sha in landing["extra_shas"] if sha not in shas]
    return landings


def pregate_roots(repo: Path) -> list[Path]:
    roots: list[Path] = []
    seen = set()

    def add(path: Path) -> None:
        try:
            key = str(path.resolve()) if path.exists() else str(path)
        except OSError:
            key = str(path)
        if key in seen:
            return
        seen.add(key)
        roots.append(path)

    add(repo / "tmp" / "pregate-runs")
    try:
        common = git_output(repo, ["rev-parse", "--path-format=absolute", "--git-common-dir"]).strip()
        main_root = Path(common).parent
        add(main_root / "tmp" / "pregate-runs")
        worktrees = main_root / "tmp"
        if worktrees.is_dir():
            for child in sorted(worktrees.iterdir()):
                if child.is_dir():
                    add(child / "tmp" / "pregate-runs")
    except (subprocess.CalledProcessError, OSError):
        pass
    return roots


def load_pregates(roots: list[Path]) -> list[dict]:
    seen_paths = set()
    seen_ids = set()
    out = []
    for root in roots:
        if not root.is_dir():
            continue
        for summary in sorted(root.glob("*/pregate-summary.md")):
            try:
                resolved = str(summary.resolve())
            except OSError:
                resolved = str(summary)
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)
            try:
                text = summary.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            parsed = parse_pregate_summary(text)
            if not parsed or not parsed.get("sha"):
                continue
            run_id = parsed.get("run_id") or resolved
            if run_id in seen_ids:
                continue
            seen_ids.add(run_id)
            out.append(parsed)
    return out


def load_progress(home: Path) -> list[dict]:
    folder = home / "DEVELOP"
    if not folder.is_dir():
        return []
    seen = set()
    rows = []
    for path in sorted(folder.glob("pfy-mentat-*-progress.md")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for row in parse_progress_text(text):
            if row["raw"] in seen:
                continue
            seen.add(row["raw"])
            rows.append(row)
    return rows


def cache_dir() -> Path:
    home_cache = Path.home() / ".cache" / "pfy" / "retro"
    try:
        home_cache.mkdir(parents=True, exist_ok=True)
        return home_cache
    except OSError:
        fallback = Path(os.environ.get("TMPDIR") or "/tmp") / "pfy-retro-cache"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def build_live_report(repo: Path, limit: int, since: str | None, offline: bool) -> dict:
    landings = load_landings(repo, limit, since)
    pregates = load_pregates(pregate_roots(repo))
    progress = load_progress(Path.home())
    classes = load_job_classes(repo / ".github" / "workflows")
    wanted = {landing["sha"] for landing in landings}
    for landing in landings:
        wanted.update(landing.get("extra_shas") or [])
    client = GitHubClient(cache_dir())
    items: list[dict] = []
    known: set[str] = set()
    if offline:
        def _offline(request, timeout=30):
            raise urllib.error.URLError("offline")

        client.opener = _offline
        client.note = "cached GitHub responses; network not contacted"
    oldest = None
    for landing in landings:
        stamp = landing.get("committed_at")
        if stamp is not None and (oldest is None or stamp < oldest):
            oldest = stamp
    stop = oldest - timedelta(days=2) if oldest else None
    try:
        items, known = fetch_runs_and_jobs(client, REPO_SLUG, wanted, stop)
    except Exception:
        client.ok = False
        if not client.note:
            client.note = "github unavailable; no cache"
        items, known = [], set()
    ci_jobs = ci_jobs_from_payloads(items, classes)
    # Diag fills a self-hosted run only when the API never answered for that SHA.
    # An empty run list is an answer. A sha that only appears in log noise is not.
    unknown = wanted - known
    diag_hits = diag_self_hosted_shas(Path.home() / "actions-runner" / "_diag", unknown, oldest)
    for sha in sorted(diag_hits):
        ci_jobs.append(
            {
                "sha": sha,
                "name": "G0 (self-hosted nimo)",
                "host": "self-hosted",
                "seconds": 0.0,
                "lane": "main",
                "kind": "full",
                "started": None,
                "completed": None,
                "run_id": "diag",
            }
        )
    if diag_hits:
        extra = f"diag filled {len(diag_hits)} self-hosted full-suite run(s) with unknown minutes"
        client.note = (client.note + "; " if client.note else "") + extra
    rows = build_landing_rows(landings, pregates, progress, ci_jobs)
    return make_report(rows, client.ok, client.note, classes)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pipeline retro for recent main landings.")
    parser.add_argument("-n", "--landings", type=int, default=10, help="last N first-parent landings (default 10)")
    parser.add_argument("--since", default=None, help="ISO date; landings at or after this date instead of -n")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    parser.add_argument("--offline", action="store_true", help="do not contact GitHub")
    parser.add_argument("--repo", type=Path, default=None, help="repo root (default: this script's repo)")
    args = parser.parse_args(argv)
    if args.landings < 1:
        print("pipeline_retro: --landings must be >= 1", file=sys.stderr)
        return 2
    root = args.repo or repo_root()
    report = build_live_report(root, args.landings, args.since, args.offline)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(format_table(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
