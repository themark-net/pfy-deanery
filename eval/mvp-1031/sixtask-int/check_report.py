#!/usr/bin/env python3
"""Check sixtask-int REPORT.md against receipts/<pass>/<task>/.

Empty return means every row matches its receipt and meta, the per-pass
totals equal the rows, and the VERDICT line matches the 6/6 bar on both passes.
A planted mismatch must produce a non-empty error list.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

TASK_HEADER = [
    "Pass",
    "Task",
    "Status",
    "Exit",
    "Attempts",
    "Gate",
    "Review",
    "Human",
    "Wall_s",
    "Writable",
]
TOTAL_HEADER = [
    "Pass",
    "Tasks",
    "Runner_pass",
    "Review_accept",
    "Human_accept",
    "Gate_pass",
    "Wall_s",
]
TASK_IDS = [
    "t1-smolvm-stderr-first",
    "t2-tree-sig-119",
    "t3-daemon-stop-fail",
    "t4-timeout-substep",
    "t5-receipts-outside-repo",
    "t6-tree-sig-three",
]
PASSES = ("pass1", "pass2")


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


def writable_cell(paths: list) -> str:
    if not paths:
        return "-"
    return ", ".join(str(path) for path in paths)


def writable_from_command(command: list) -> list[str]:
    found: list[str] = []
    index = 0
    while index < len(command):
        if command[index] == "--writable-test":
            if index + 1 >= len(command):
                found.append("")
            else:
                found.append(str(command[index + 1]))
                index += 1
        index += 1
    return found


def _load_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _review_cell(receipt: dict) -> str:
    review = receipt.get("review")
    if not isinstance(review, dict):
        return "none"
    verdict = review.get("verdict")
    if verdict in (None, ""):
        return "none"
    return str(verdict)


def _gate_cell(meta: dict) -> str:
    gate = meta.get("gate_rerun")
    if not isinstance(gate, dict):
        return "FAIL"
    if gate.get("exit") == 0:
        return "PASS"
    return "FAIL"


def bar_met(rows: list[dict]) -> bool:
    """True only when both passes have all six tasks, runner PASS, review accept, human accept."""
    seen: dict[str, set[str]] = {label: set() for label in PASSES}
    for row in rows:
        label = row.get("Pass")
        task = row.get("Task")
        if label not in seen or task not in TASK_IDS:
            return False
        if task in seen[label]:
            return False
        seen[label].add(task)
        if row.get("Status") != "PASS":
            return False
        if row.get("Review") != "accept":
            return False
        if row.get("Human") != "accept":
            return False
    return all(seen[label] == set(TASK_IDS) for label in PASSES)


def _verdict_line(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("VERDICT:"):
            return line.strip()
    return None


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

    parsed: list[dict] = []
    sums: dict[str, dict] = {}
    seen: set[tuple[str, str]] = set()

    for cells in rows:
        if len(cells) != len(TASK_HEADER):
            errors.append("task row width %s" % len(cells))
            continue
        row = dict(zip(TASK_HEADER, cells))
        label = row["Pass"]
        task = row["Task"]
        key = (label, task)
        if not label or not task or key in seen:
            errors.append("bad task id %s %s" % (label, task))
            continue
        seen.add(key)
        parsed.append(row)
        receipt_path = root / "receipts" / label / task / "receipt.json"
        meta_path = root / "receipts" / label / task / "meta.json"
        if not receipt_path.is_file():
            errors.append("%s %s receipt missing" % (label, task))
            continue
        if not meta_path.is_file():
            errors.append("%s %s meta missing" % (label, task))
            continue
        receipt = _load_json(receipt_path)
        meta = _load_json(meta_path)
        if receipt is None:
            errors.append("%s %s receipt is not json" % (label, task))
            continue
        if meta is None:
            errors.append("%s %s meta is not json" % (label, task))
            continue
        status = receipt.get("status")
        if row["Status"] != status:
            errors.append("%s %s status report %s receipt %s" % (label, task, row["Status"], status))
        try:
            exit_code = int(receipt.get("exit_code"))
        except (TypeError, ValueError):
            errors.append("%s %s exit_code missing" % (label, task))
            exit_code = None
        try:
            row_exit = _int(row["Exit"])
        except ValueError:
            errors.append("%s %s exit cell not an int" % (label, task))
            row_exit = None
        if exit_code is not None and row_exit is not None and row_exit != exit_code:
            errors.append("%s %s exit report %s receipt %s" % (label, task, row_exit, exit_code))
        attempts = receipt.get("attempts")
        if not isinstance(attempts, list):
            errors.append("%s %s attempts is not a list" % (label, task))
            attempt_count = None
        else:
            attempt_count = len(attempts)
        try:
            row_attempts = _int(row["Attempts"])
        except ValueError:
            errors.append("%s %s attempts cell not an int" % (label, task))
            row_attempts = None
        if attempt_count is not None and row_attempts is not None and row_attempts != attempt_count:
            errors.append(
                "%s %s attempts report %s receipt %s" % (label, task, row_attempts, attempt_count)
            )
        if row["Review"] != _review_cell(receipt):
            errors.append(
                "%s %s review report %s receipt %s" % (label, task, row["Review"], _review_cell(receipt))
            )
        if row["Gate"] != _gate_cell(meta):
            errors.append("%s %s gate report %s meta %s" % (label, task, row["Gate"], _gate_cell(meta)))
        human = meta.get("human")
        if row["Human"] != human:
            errors.append("%s %s human report %s meta %s" % (label, task, row["Human"], human))
        try:
            row_wall = _wall(row["Wall_s"])
        except ValueError:
            errors.append("%s %s wall cell not a number" % (label, task))
            row_wall = None
        try:
            meta_wall = _wall(str(meta.get("wall_s")))
        except (TypeError, ValueError):
            errors.append("%s %s meta wall missing" % (label, task))
            meta_wall = None
        if row_wall is not None and meta_wall is not None and row_wall != meta_wall:
            errors.append("%s %s wall report %s meta %s" % (label, task, row_wall, meta_wall))
        paths = meta.get("writable_test")
        if not isinstance(paths, list):
            errors.append("%s %s writable_test is not a list" % (label, task))
            paths = []
        if row["Writable"] != writable_cell(paths):
            errors.append(
                "%s %s writable report %s meta %s" % (label, task, row["Writable"], writable_cell(paths))
            )
        command = meta.get("command")
        if not isinstance(command, list):
            errors.append("%s %s command is not a list" % (label, task))
        else:
            if "--local" in command:
                errors.append("%s %s command contains --local" % (label, task))
            if "--no-review" in command:
                errors.append("%s %s command contains --no-review" % (label, task))
            flagged = writable_from_command([str(item) for item in command])
            if flagged != [str(path) for path in paths]:
                errors.append("%s %s command writable %s meta %s" % (label, task, flagged, paths))

        bucket = sums.setdefault(
            label,
            {
                "Tasks": 0,
                "Runner_pass": 0,
                "Review_accept": 0,
                "Human_accept": 0,
                "Gate_pass": 0,
                "Wall_s": 0.0,
            },
        )
        bucket["Tasks"] += 1
        if row["Status"] == "PASS":
            bucket["Runner_pass"] += 1
        if row["Review"] == "accept":
            bucket["Review_accept"] += 1
        if row["Human"] == "accept":
            bucket["Human_accept"] += 1
        if row["Gate"] == "PASS":
            bucket["Gate_pass"] += 1
        if row_wall is not None:
            bucket["Wall_s"] = round(bucket["Wall_s"] + row_wall, 1)

    if totals is not None:
        total_rows = totals[1:]
        if len(total_rows) != len(sums):
            errors.append("totals rows %s passes %s" % (len(total_rows), len(sums)))
        for cells in total_rows:
            if len(cells) != len(TOTAL_HEADER):
                errors.append("totals row width %s" % len(cells))
                continue
            total = dict(zip(TOTAL_HEADER, cells))
            bucket = sums.get(total["Pass"])
            if bucket is None:
                errors.append("totals pass %s has no task rows" % total["Pass"])
                continue
            expect = {
                "Tasks": str(bucket["Tasks"]),
                "Runner_pass": str(bucket["Runner_pass"]),
                "Review_accept": str(bucket["Review_accept"]),
                "Human_accept": str(bucket["Human_accept"]),
                "Gate_pass": str(bucket["Gate_pass"]),
            }
            for key, wanted in expect.items():
                if total[key] != wanted:
                    errors.append("totals %s %s is %s sum is %s" % (total["Pass"], key, total[key], wanted))
            try:
                if _wall(total["Wall_s"]) != bucket["Wall_s"]:
                    errors.append(
                        "totals %s Wall_s is %s sum is %s" % (total["Pass"], total["Wall_s"], bucket["Wall_s"])
                    )
            except ValueError:
                errors.append("totals %s Wall_s is not a number" % total["Pass"])

    wanted = "VERDICT: GO" if bar_met(parsed) else "VERDICT: NO-GO"
    found = _verdict_line(text)
    if found != wanted:
        errors.append("verdict line %s wanted %s" % (found, wanted))
    return errors


def _row_from_files(label: str, task: str, receipt: dict, meta: dict) -> dict:
    attempts = receipt.get("attempts")
    attempt_count = len(attempts) if isinstance(attempts, list) else 0
    try:
        exit_code = int(receipt.get("exit_code"))
    except (TypeError, ValueError):
        exit_code = -1
    paths = meta.get("writable_test") if isinstance(meta.get("writable_test"), list) else []
    try:
        wall = "%.1f" % _wall(str(meta.get("wall_s")))
    except (TypeError, ValueError):
        wall = "0.0"
    return {
        "Pass": label,
        "Task": task,
        "Status": str(receipt.get("status")),
        "Exit": str(exit_code),
        "Attempts": str(attempt_count),
        "Gate": _gate_cell(meta),
        "Review": _review_cell(receipt),
        "Human": str(meta.get("human")),
        "Wall_s": wall,
        "Writable": writable_cell(paths),
    }


def collect_rows(root: Path) -> list[dict]:
    rows: list[dict] = []
    receipt_root = root / "receipts"
    if not receipt_root.is_dir():
        return rows
    labels = sorted(path.name for path in receipt_root.iterdir() if path.is_dir())
    for label in labels:
        for task in TASK_IDS:
            receipt = _load_json(receipt_root / label / task / "receipt.json")
            meta = _load_json(receipt_root / label / task / "meta.json")
            if receipt is None or meta is None:
                continue
            rows.append(_row_from_files(label, task, receipt, meta))
    return rows


def render_report(rows: list[dict]) -> str:
    lines = [
        "# Six-task bar on the integration tip",
        "",
        "Two passes of MVP-2 t1 through t6 through `./pfy build` on branch `bot/mvp-sixtask-int-1031`.",
        "Review stays on. No `--local`. No `--no-review`. `--timeout 900`. `--keep-worktree`.",
        "Each task is a throwaway clone at `997d89264495861a178713ccf7d4447ea828afc4` with the canonical MVP-2 gate planted on `demo-base`.",
        "",
        "`--writable-test` is passed only where the task file says a test must change.",
        "t4: `tests/test_x_intake_smoke_112_114.py`.",
        "t5: `tests/test_x_intake_smoke_117_118.py`, `tests/test_x_intake_smoke_119_121.py`.",
        "t1, t2, t3, and t6 pass no writable path. The planted acceptance tests stay hashed.",
        "",
        "`Status`, `Exit`, and `Attempts` are the receipt.",
        "`Gate` is the canonical MVP-2 gate re-run (PASS only when that exit is 0).",
        "`Review` is `review.verdict`, or `none` when the runner stored none.",
        "`Human` is a read of the diff against the task text, stored on `meta.json` before this file is rendered.",
        "`Writable` is the exact path list on that command.",
        "`Wall_s` is the `./pfy build` process only.",
        "",
        "| " + " | ".join(TASK_HEADER) + " |",
        "| " + " | ".join("---" for _ in TASK_HEADER) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row[key] for key in TASK_HEADER) + " |")
    lines.extend(
        [
            "",
            "| " + " | ".join(TOTAL_HEADER) + " |",
            "| " + " | ".join("---" for _ in TOTAL_HEADER) + " |",
        ]
    )
    by_pass: dict[str, list[dict]] = {}
    for row in rows:
        by_pass.setdefault(row["Pass"], []).append(row)
    for label in sorted(by_pass):
        group = by_pass[label]
        wall = round(sum(_wall(row["Wall_s"]) for row in group), 1)
        cells = [
            label,
            str(len(group)),
            str(sum(1 for row in group if row["Status"] == "PASS")),
            str(sum(1 for row in group if row["Review"] == "accept")),
            str(sum(1 for row in group if row["Human"] == "accept")),
            str(sum(1 for row in group if row["Gate"] == "PASS")),
            "%.1f" % wall,
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines.extend(["", ("VERDICT: GO" if bar_met(rows) else "VERDICT: NO-GO"), ""])
    lines.append("## Per task")
    lines.append("")
    for row in rows:
        lines.append(
            "%s %s: status %s, review %s, human %s, writable %s."
            % (row["Pass"], row["Task"], row["Status"], row["Review"], row["Human"], row["Writable"])
        )
    lines.append("")
    return "\n".join(lines)


def write_report(root: Path) -> Path:
    root = Path(root)
    rows = collect_rows(root)
    notes: list[str] = []
    for row in rows:
        meta = _load_json(root / "receipts" / row["Pass"] / row["Task"] / "meta.json") or {}
        note = str(meta.get("human_note") or "").strip()
        reason = str(meta.get("receipt_reason") or "")
        commit = meta.get("commit") or "none"
        if note or reason:
            notes.append(
                "%s %s: reason %s, commit %s. %s" % (row["Pass"], row["Task"], reason, commit, note)
            )
    text = render_report(rows)
    if notes:
        text += "\n".join(notes) + "\n"
    path = root / "REPORT.md"
    path.write_text(text, encoding="utf-8")
    return path


def main(argv: list[str]) -> int:
    args = [item for item in argv[1:] if item != "--write"]
    root = Path(args[0]) if args else Path(__file__).resolve().parent
    if "--write" in argv:
        write_report(root)
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
