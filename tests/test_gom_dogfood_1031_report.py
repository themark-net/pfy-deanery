"""Report rows for the gom dogfood must match the receipts on disk.

How this fails: a row says PASS, or a wall time, while the receipt or
meta.json says something else. How we recover: check_report names the
run and the field. A planted mismatch must fail. The real report must
produce no errors.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tests._ops import OPS, require  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EVAL = OPS / "eval" / "gom-dogfood-1031"
REPORT = EVAL / "REPORT.md"

COLUMNS = (
    "n",
    "slug",
    "exit",
    "status",
    "attempts",
    "review",
    "human",
    "wall_s",
    "commit",
)


def parse_rows(text: str) -> dict[tuple[str, str], dict[str, str]]:
    rows: dict[tuple[str, str], dict[str, str]] = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(COLUMNS) or not cells[0].isdigit():
            continue
        row = dict(zip(COLUMNS, cells))
        rows[(row["n"], row["slug"])] = row
    return rows


def check_report(report_text: str, root: Path) -> list[str]:
    """Return one string per disagreement. Empty means the table matches."""
    errors: list[str] = []
    rows = parse_rows(report_text)
    seen: set[tuple[str, str]] = set()
    runs = sorted(
        path
        for path in root.iterdir()
        if path.is_dir() and (path / "receipt.json").is_file() and (path / "meta.json").is_file()
    )
    if not runs:
        errors.append("no receipt directories under %s" % root)
    for path in runs:
        receipt = json.loads((path / "receipt.json").read_text(encoding="utf-8"))
        meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
        key = (str(meta["n"]), str(meta["slug"]))
        seen.add(key)
        expected_dir = "%s-%s" % key
        if path.name != expected_dir:
            errors.append("%s directory is %s" % (key[0], path.name))
        row = rows.get(key)
        if row is None:
            errors.append("%s %s missing row" % key)
            continue
        pairs = (
            ("exit", row["exit"], str(receipt["exit_code"]), "receipt"),
            ("status", row["status"], str(receipt["status"]), "receipt"),
            ("attempts", row["attempts"], str(len(receipt["attempts"])), "receipt"),
            ("review", row["review"], str(receipt["review"]["verdict"]), "receipt"),
            ("human", row["human"], str(meta["human_verdict"]), "meta"),
            ("wall_s", row["wall_s"], str(meta["wall_s"]), "meta"),
            ("commit", row["commit"], str(receipt["commit"]), "receipt"),
        )
        for field, got, want, source in pairs:
            if got != want:
                errors.append(
                    "%s %s %s report=%s %s=%s" % (key[0], key[1], field, got, source, want)
                )
        if str(meta.get("cloud_commit")) != str(receipt["commit"]):
            errors.append(
                "%s %s cloud_commit meta=%s receipt=%s"
                % (key[0], key[1], meta.get("cloud_commit"), receipt["commit"])
            )
    for key in sorted(set(rows) - seen):
        errors.append("%s %s extra row" % key)
    return errors


def setUpModule() -> None:
    require(REPORT)


class GomDogfoodReportTests(unittest.TestCase):
    def test_rows_match_receipts(self) -> None:
        errors = check_report(REPORT.read_text(encoding="utf-8"), EVAL)
        self.assertEqual(errors, [])

    def test_planted_mismatch_fails(self) -> None:
        text = REPORT.read_text(encoding="utf-8")
        planted_exit = text.replace(
            "| 01 | catch-view-thread | 0 |",
            "| 01 | catch-view-thread | 7 |",
            1,
        )
        self.assertNotEqual(planted_exit, text)
        exit_errors = check_report(planted_exit, EVAL)
        self.assertIn(
            "01 catch-view-thread exit report=7 receipt=0",
            exit_errors,
        )

        planted_attempts = text.replace(
            "| 03 | catch-view-index | 0 | PASS | 1 |",
            "| 03 | catch-view-index | 0 | PASS | 9 |",
            1,
        )
        self.assertNotEqual(planted_attempts, text)
        attempt_errors = check_report(planted_attempts, EVAL)
        self.assertIn(
            "03 catch-view-index attempts report=9 receipt=1",
            attempt_errors,
        )


if __name__ == "__main__":
    unittest.main()
