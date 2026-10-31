#!/usr/bin/env python3
"""Check dogfood2 REPORT.md rows against receipt.json files and Built-by trailers.

Exit 0 when every run directory is listed, status, exit_code, and review
match the receipt, the rate and median lines match the table, and each
human-accept PASS row's commit trailer names that receipt.
Exit 1 when any of those checks fail.
Exit 2 when the arguments are wrong.

A failure names the run directory and the field that drifted. Recover by
fixing the report row or the trailer, then run this command again.
"""
from __future__ import annotations

import json
import re
import statistics
import subprocess
import sys
from pathlib import Path

DIR_RE = re.compile(r"^[0-9]{2}-[a-z0-9][a-z0-9-]*$")
RATE_RE = re.compile(r"^- ([a-z_]+): (\S+)\s*$", re.M)
TRAILER_RE = re.compile(
    r"^Built-by: \./pfy build \(cloud\) receipt (\S+)\s*$",
    re.M,
)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 2 or (args and args[0] in {"-h", "--help"}):
        print(
            "usage: python3 eval/dogfood2-1031/check_reports.py [DOGFOOD_DIR] [REPO]",
            file=sys.stderr,
        )
        return 0 if args and args[0] in {"-h", "--help"} else 2
    here = Path(__file__).resolve()
    root = Path(args[0]).resolve() if args else here.parent
    repo = Path(args[1]).resolve() if len(args) == 2 else here.parents[2]
    try:
        problems = check_root(root, repo)
    except OSError as exc:
        print("FAIL read %s" % exc.__class__.__name__, file=sys.stderr)
        return 1
    if problems:
        for line in problems:
            print("FAIL %s" % line, file=sys.stderr)
        return 1
    print("OK runs=%d" % len(list_run_dirs(root)))
    return 0


def check_root(root: Path, repo: Path) -> list[str]:
    report = root / "REPORT.md"
    if not report.is_file():
        return ["missing REPORT.md under %s" % root.name]
    try:
        text = report.read_text(encoding="utf-8")
    except OSError as exc:
        return ["REPORT.md unreadable (%s)" % exc.__class__.__name__]
    try:
        rows = parse_runs_table(text)
    except ValueError as exc:
        return [str(exc)]
    dirs = list_run_dirs(root)
    problems: list[str] = []
    names = [row["dir"] for row in rows]
    if len(names) != len(set(names)):
        problems.append("REPORT lists a dir more than once")
    row_set = set(names)
    dir_set = set(dirs)
    for name in sorted(dir_set - row_set):
        problems.append("%s run dir is missing from REPORT" % name)
    for name in sorted(row_set - dir_set):
        problems.append("%s REPORT row has no run dir" % name)
    for row in rows:
        if row["dir"] not in dir_set:
            continue
        problems.extend(check_receipt(root / row["dir"] / "receipt.json", row))
        problems.extend(check_trailer(repo, root, row))
    problems.extend(check_summary(text, rows))
    return problems


def list_run_dirs(root: Path) -> list[str]:
    if not root.is_dir():
        return []
    return sorted(
        child.name
        for child in root.iterdir()
        if child.is_dir() and DIR_RE.match(child.name)
    )


def parse_runs_table(text: str) -> list[dict[str, str]]:
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == "## Runs":
            start = index + 1
            break
    if start is None:
        raise ValueError("REPORT.md has no ## Runs section")
    table: list[str] = []
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped:
            if table:
                break
            continue
        if not stripped.startswith("|"):
            if table:
                break
            continue
        table.append(stripped)
    if len(table) < 2:
        raise ValueError("REPORT.md ## Runs table is missing a header")
    header = _cells(table[0])
    for key in ("dir", "status", "exit_code", "review", "human", "wall_s", "commit"):
        if key not in header:
            raise ValueError("REPORT.md runs table is missing column %s" % key)
    rows: list[dict[str, str]] = []
    for raw in table[2:]:
        cells = _cells(raw)
        if len(cells) != len(header):
            raise ValueError(
                "REPORT.md runs row has %d cells, header has %d" % (len(cells), len(header))
            )
        item = dict(zip(header, cells))
        if not DIR_RE.match(item["dir"]):
            raise ValueError("REPORT.md dir is not nn-slug: %s" % item["dir"])
        rows.append(item)
    return rows


def _cells(line: str) -> list[str]:
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [cell.strip() for cell in body.split("|")]


def check_receipt(path: Path, row: dict[str, str]) -> list[str]:
    name = row["dir"]
    if not path.is_file():
        return ["%s missing receipt.json" % name]
    try:
        raw = path.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        return ["%s receipt unreadable (%s)" % (name, exc.__class__.__name__)]
    if not isinstance(payload, dict):
        return ["%s receipt is not an object" % name]
    problems: list[str] = []
    status = payload.get("status")
    if status != row["status"]:
        problems.append("%s status report=%s receipt=%s" % (name, row["status"], status))
    try:
        exit_code = int(payload.get("exit_code"))
        expected = int(row["exit_code"])
    except (TypeError, ValueError):
        problems.append("%s exit_code is not an integer" % name)
    else:
        if exit_code != expected:
            problems.append("%s exit_code report=%s receipt=%s" % (name, expected, exit_code))
    verdict = ((payload.get("review") or {}) if isinstance(payload.get("review"), dict) else {}).get("verdict") or "none"
    if str(verdict) != row["review"]:
        problems.append("%s review report=%s receipt=%s" % (name, row["review"], verdict))
    return problems


def check_trailer(repo: Path, root: Path, row: dict[str, str]) -> list[str]:
    name = row["dir"]
    if row["status"] != "PASS" or row["human"] != "yes":
        return []
    sha = row["commit"]
    if not re.fullmatch(r"[0-9a-f]{7,40}", sha):
        return ["%s commit is not a sha" % name]
    proc = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%B", sha],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return ["%s commit %s is not in the repo" % (name, sha)]
    found = TRAILER_RE.findall(proc.stdout)
    rel = str((root / name / "receipt.json").resolve().relative_to(repo.resolve()))
    # Receipt paths in trailers are repo-relative with forward slashes.
    rel = rel.replace("\\", "/")
    if rel not in found:
        shown = found[0] if found else "none"
        return ["%s trailer report=%s commit=%s" % (name, rel, shown)]
    return []


def check_summary(text: str, rows: list[dict[str, str]]) -> list[str]:
    rates = dict(RATE_RE.findall(text))
    problems: list[str] = []
    runs = len(rows)
    if rates.get("runs") != str(runs):
        problems.append("runs line report=%s table=%s" % (rates.get("runs"), runs))
    gate = sum(1 for row in rows if row["status"] == "PASS")
    review = sum(1 for row in rows if row["review"] == "accept")
    human = sum(1 for row in rows if row["human"] == "yes")
    for key, got in (
        ("gate_pass_rate", "%d/%d" % (gate, runs) if runs else "0/0"),
        ("review_accept_rate", "%d/%d" % (review, runs) if runs else "0/0"),
        ("human_accept_rate", "%d/%d" % (human, runs) if runs else "0/0"),
    ):
        if rates.get(key) != got:
            problems.append("%s line report=%s table=%s" % (key, rates.get(key), got))
    try:
        walls = [int(row["wall_s"]) for row in rows]
    except ValueError:
        return problems + ["wall_s is not an integer"]
    if not walls:
        return problems
    ordered = sorted(walls)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        median = ordered[mid]
    else:
        median = int(statistics.mean((ordered[mid - 1], ordered[mid])))
    if rates.get("median_wall_s") != str(median):
        problems.append(
            "median_wall_s line report=%s table=%s" % (rates.get("median_wall_s"), median)
        )
    return problems


if __name__ == "__main__":
    sys.exit(main())
