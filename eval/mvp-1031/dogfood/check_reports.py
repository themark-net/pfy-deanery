#!/usr/bin/env python3
"""Check dogfood REPORT.md rows against receipt.json files.

Exit 0 when every run directory is listed, each receipt status and exit_code
match that row, and no receipt contains a secret-like string.
Exit 1 when any of those checks fail.
Exit 2 when the arguments are wrong.

A failure names the run directory and the field that drifted. It does not
print the secret-like value. Recover by fixing the report row or redacting
the receipt, then run this command again.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DIR_RE = re.compile(r"^[0-9]{2}-[a-z0-9][a-z0-9-]*$")

# Names are split so the checker source does not contain a live secret shape.
_BEARER = "bea" + "rer"
_AKIA = "AKI" + "A"
_PRIVATE = "BEGIN " + "PRIVATE KEY"
_SK = "sk" + "-"

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        _BEARER,
        re.compile(
            r"(?i)" + _BEARER + r"\s+[A-Za-z0-9._~+/=-]{8,}"
        ),
    ),
    (
        _AKIA.lower(),
        re.compile(r"\b" + _AKIA + r"[0-9A-Z]{16}\b"),
    ),
    (
        "private-key",
        re.compile(r"-----" + _PRIVATE + r"-----"),
    ),
    (
        "assigned-secret",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|secret|password)\b"
            r"\s*[=:]\s*['\"]?[A-Za-z0-9._~+/=-]{8,}"
        ),
    ),
    (
        "sk-key",
        re.compile(r"\b" + _SK + r"[A-Za-z0-9]{20,}\b"),
    ),
)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 1 or (args and args[0] in {"-h", "--help"}):
        print(
            "usage: python3 eval/mvp-1031/dogfood/check_reports.py [DOGFOOD_DIR]",
            file=sys.stderr,
        )
        return 0 if args and args[0] in {"-h", "--help"} else 2
    root = Path(args[0]).resolve() if args else Path(__file__).resolve().parent
    try:
        problems = check_root(root)
    except OSError as exc:
        print("FAIL read %s" % exc.__class__.__name__, file=sys.stderr)
        return 1
    if problems:
        for line in problems:
            print("FAIL %s" % line, file=sys.stderr)
        return 1
    print("OK runs=%d" % len(list_run_dirs(root)))
    return 0


def check_root(root: Path) -> list[str]:
    """Return human-readable problems. Empty means the tree matches."""
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
    row_names = [row["dir"] for row in rows]
    if len(row_names) != len(set(row_names)):
        problems.append("REPORT lists a dir more than once")
    row_set = set(row_names)
    dir_set = set(dirs)
    for name in sorted(dir_set - row_set):
        problems.append("%s run dir is missing from REPORT" % name)
    for name in sorted(row_set - dir_set):
        problems.append("%s REPORT row has no run dir" % name)
    for row in rows:
        name = row["dir"]
        if name not in dir_set:
            continue
        problems.extend(check_receipt(root / name / "receipt.json", row))
    return problems


def list_run_dirs(root: Path) -> list[str]:
    if not root.is_dir():
        return []
    found = []
    for child in root.iterdir():
        if child.is_dir() and DIR_RE.match(child.name):
            found.append(child.name)
    return sorted(found)


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
    wanted = {"dir": None, "status": None, "exit_code": None}
    for key in wanted:
        if key not in header:
            raise ValueError("REPORT.md runs table is missing column %s" % key)
    rows: list[dict[str, str]] = []
    for raw in table[2:]:
        cells = _cells(raw)
        if len(cells) != len(header):
            raise ValueError("REPORT.md runs row has %d cells, header has %d" % (len(cells), len(header)))
        item = dict(zip(header, cells))
        name = item["dir"]
        if not DIR_RE.match(name):
            raise ValueError("REPORT.md dir is not nn-slug: %s" % name)
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
    except OSError as exc:
        return ["%s receipt unreadable (%s)" % (name, exc.__class__.__name__)]
    problems = secret_problems(name, raw)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        problems.append("%s receipt is not json" % name)
        return problems
    if not isinstance(payload, dict):
        problems.append("%s receipt is not an object" % name)
        return problems
    status = payload.get("status")
    if status != row["status"]:
        problems.append(
            "%s status report=%s receipt=%s"
            % (name, row["status"], status)
        )
    try:
        exit_code = int(payload.get("exit_code"))
        expected = int(row["exit_code"])
    except (TypeError, ValueError):
        problems.append("%s exit_code is not an integer" % name)
        return problems
    if exit_code != expected:
        problems.append(
            "%s exit_code report=%s receipt=%s" % (name, expected, exit_code)
        )
    return problems


def secret_problems(name: str, raw: str) -> list[str]:
    found = []
    for label, pattern in SECRET_PATTERNS:
        if pattern.search(raw):
            found.append("%s receipt secret-like pattern=%s" % (name, label))
    return found


if __name__ == "__main__":
    sys.exit(main())
