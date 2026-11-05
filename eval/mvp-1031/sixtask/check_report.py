#!/usr/bin/env python3
"""Check a sixtask REPORT.md against the receipt next to each row.

Empty return means every task row matches its receipt (status, exit_code,
attempt count) and the totals line equals the sum of those rows.
A planted mismatch must produce a non-empty error list.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TASK_HEADER = [
    "Task",
    "Status",
    "Exit",
    "Attempts",
    "Gate",
    "Review",
    "Human",
    "Wall_s",
]
TOTAL_HEADER = [
    "Tasks",
    "Gate_pass",
    "Review_accept",
    "Human_accept",
    "Wall_s",
    "Attempts",
    "Exit_sum",
]


def _tables(text: str) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            if current:
                tables.append(current)
                current = []
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and all(cell and set(cell) <= set("-: ") for cell in cells):
            continue
        current.append(cells)
    if current:
        tables.append(current)
    return tables


def _find_table(text: str, header: list[str]) -> list[list[str]] | None:
    for table in _tables(text):
        if table and table[0] == header:
            return table
    return None


def _int(cell: str) -> int:
    return int(cell.strip())


def _wall(cell: str) -> float:
    return round(float(cell.strip()), 1)


def check_report(root: Path) -> list[str]:
    """Return human-readable errors. Empty means the report matches."""
    root = Path(root)
    report_path = root / "REPORT.md"
    errors: list[str] = []
    if not report_path.is_file():
        return ["REPORT.md is missing"]
    text = report_path.read_text(encoding="utf-8")
    tasks = _find_table(text, TASK_HEADER)
    totals = _find_table(text, TOTAL_HEADER)
    if tasks is None:
        errors.append("tasks table missing or header mismatch")
        return errors
    if totals is None:
        errors.append("totals table missing or header mismatch")
    rows = tasks[1:]
    if not rows:
        errors.append("tasks table has no rows")
        return errors

    sum_gate = 0
    sum_review = 0
    sum_human = 0
    sum_wall = 0.0
    sum_attempts = 0
    sum_exit = 0
    seen: set[str] = set()

    for cells in rows:
        if len(cells) != len(TASK_HEADER):
            errors.append("task row width %s" % len(cells))
            continue
        row = dict(zip(TASK_HEADER, cells))
        task = row["Task"]
        if not task or task in seen:
            errors.append("bad task id %s" % task)
            continue
        seen.add(task)
        receipt_path = root / task / "receipt.json"
        if not receipt_path.is_file():
            errors.append("%s receipt missing" % task)
            continue
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append("%s receipt is not json" % task)
            continue
        if not isinstance(receipt, dict):
            errors.append("%s receipt is not an object" % task)
            continue
        status = receipt.get("status")
        if row["Status"] != status:
            errors.append("%s status report %s receipt %s" % (task, row["Status"], status))
        try:
            exit_code = int(receipt.get("exit_code"))
        except (TypeError, ValueError):
            errors.append("%s exit_code missing" % task)
            exit_code = None
        try:
            row_exit = _int(row["Exit"])
        except ValueError:
            errors.append("%s exit cell not an int" % task)
            row_exit = None
        if exit_code is not None and row_exit is not None and row_exit != exit_code:
            errors.append("%s exit report %s receipt %s" % (task, row_exit, exit_code))
        attempts = receipt.get("attempts")
        if not isinstance(attempts, list):
            errors.append("%s attempts is not a list" % task)
            attempt_count = None
        else:
            attempt_count = len(attempts)
        try:
            row_attempts = _int(row["Attempts"])
        except ValueError:
            errors.append("%s attempts cell not an int" % task)
            row_attempts = None
        if attempt_count is not None and row_attempts is not None and row_attempts != attempt_count:
            errors.append(
                "%s attempts report %s receipt %s" % (task, row_attempts, attempt_count)
            )
        if row["Gate"] == "PASS":
            sum_gate += 1
        if row["Review"] == "accept":
            sum_review += 1
        if row["Human"] == "accept":
            sum_human += 1
        try:
            sum_wall += _wall(row["Wall_s"])
        except ValueError:
            errors.append("%s wall cell not a number" % task)
        if row_attempts is not None:
            sum_attempts += row_attempts
        if row_exit is not None:
            sum_exit += row_exit

    if totals is None or len(totals) < 2:
        return errors
    total_cells = totals[1]
    if len(total_cells) != len(TOTAL_HEADER):
        errors.append("totals row width %s" % len(total_cells))
        return errors
    total = dict(zip(TOTAL_HEADER, total_cells))
    expect = {
        "Tasks": str(len(rows)),
        "Gate_pass": str(sum_gate),
        "Review_accept": str(sum_review),
        "Human_accept": str(sum_human),
        "Attempts": str(sum_attempts),
        "Exit_sum": str(sum_exit),
    }
    for key, wanted in expect.items():
        if total[key] != wanted:
            errors.append("totals %s is %s sum is %s" % (key, total[key], wanted))
    try:
        if _wall(total["Wall_s"]) != round(sum_wall, 1):
            errors.append(
                "totals Wall_s is %s sum is %s" % (total["Wall_s"], round(sum_wall, 1))
            )
    except ValueError:
        errors.append("totals Wall_s is not a number")
    return errors


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else Path(__file__).resolve().parent)
    errors = check_report(root)
    for item in errors:
        print(item)
    if errors:
        print("CHECK_FAIL %s" % len(errors))
        return 1
    print("CHECK_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
