"""Behavior checks for the sixtask report and the trial command.

How this fails: a report row whose status, exit, or attempt count disagrees
with receipt.json, or a totals line that is not the sum of the rows.
How we recover: fix the report or replace the receipt, then re-run this module.
The trial argv fails closed if --local or --no-review is added.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIX = ROOT / "eval" / "mvp-1031" / "sixtask"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


CHECK = _load("sixtask_check_report", SIX / "check_report.py")
RUN = _load("sixtask_run_task", SIX / "run_task.py")


def _receipt(status: str, exit_code: int, attempts: int) -> dict:
    return {
        "schema": "pfy-cloud-build/1",
        "status": status,
        "reason": "ok" if status == "PASS" else "tests",
        "exit_code": exit_code,
        "attempts": [
            {"n": index + 1, "status": status, "reason": "ok"}
            for index in range(attempts)
        ],
        "review": {"verdict": "accept", "reasons": []},
    }


def _report(rows: list[dict], totals: dict) -> str:
    lines = [
        "# fixture",
        "",
        "| Task | Status | Exit | Attempts | Gate | Review | Human | Wall_s |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {Task} | {Status} | {Exit} | {Attempts} | {Gate} | {Review} | {Human} | {Wall_s} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "| Tasks | Gate_pass | Review_accept | Human_accept | Wall_s | Attempts | Exit_sum |",
            "| --- | --- | --- | --- | --- | --- | --- |",
            "| {Tasks} | {Gate_pass} | {Review_accept} | {Human_accept} | {Wall_s} | {Attempts} | {Exit_sum} |".format(
                **totals
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _write_tree(root: Path, rows: list[dict], receipts: dict, totals: dict) -> None:
    for task, receipt in receipts.items():
        dest = root / task
        dest.mkdir(parents=True)
        (dest / "receipt.json").write_text(
            json.dumps(receipt, indent=2) + "\n",
            encoding="utf-8",
        )
    (root / "REPORT.md").write_text(_report(rows, totals), encoding="utf-8")


class ReportCheckTests(unittest.TestCase):
    def test_consistent_rows_and_totals_pass(self) -> None:
        rows = [
            {
                "Task": "t1-smolvm-stderr-first",
                "Status": "PASS",
                "Exit": "0",
                "Attempts": "1",
                "Gate": "PASS",
                "Review": "accept",
                "Human": "accept",
                "Wall_s": "10.5",
            },
            {
                "Task": "t2-tree-sig-119",
                "Status": "FAIL",
                "Exit": "1",
                "Attempts": "3",
                "Gate": "FAIL",
                "Review": "reject",
                "Human": "reject",
                "Wall_s": "2.5",
            },
        ]
        receipts = {
            "t1-smolvm-stderr-first": _receipt("PASS", 0, 1),
            "t2-tree-sig-119": _receipt("FAIL", 1, 3),
        }
        totals = {
            "Tasks": "2",
            "Gate_pass": "1",
            "Review_accept": "1",
            "Human_accept": "1",
            "Wall_s": "13.0",
            "Attempts": "4",
            "Exit_sum": "1",
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            root = Path(tmp)
            _write_tree(root, rows, receipts, totals)
            self.assertEqual(CHECK.check_report(root), [])

    def test_planted_status_mismatch_fails(self) -> None:
        rows = [
            {
                "Task": "t1-smolvm-stderr-first",
                "Status": "PASS",
                "Exit": "0",
                "Attempts": "1",
                "Gate": "PASS",
                "Review": "accept",
                "Human": "accept",
                "Wall_s": "4.0",
            }
        ]
        totals = {
            "Tasks": "1",
            "Gate_pass": "1",
            "Review_accept": "1",
            "Human_accept": "1",
            "Wall_s": "4.0",
            "Attempts": "1",
            "Exit_sum": "0",
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            root = Path(tmp)
            _write_tree(
                root,
                rows,
                {"t1-smolvm-stderr-first": _receipt("FAIL", 1, 3)},
                totals,
            )
            errors = CHECK.check_report(root)
            self.assertTrue(errors)
            self.assertTrue(any("status" in item for item in errors))
            self.assertTrue(any("exit" in item for item in errors))
            self.assertTrue(any("attempts" in item for item in errors))

    def test_planted_totals_mismatch_fails(self) -> None:
        rows = [
            {
                "Task": "t1-smolvm-stderr-first",
                "Status": "PASS",
                "Exit": "0",
                "Attempts": "1",
                "Gate": "PASS",
                "Review": "accept",
                "Human": "accept",
                "Wall_s": "3.0",
            },
            {
                "Task": "t2-tree-sig-119",
                "Status": "PASS",
                "Exit": "0",
                "Attempts": "2",
                "Gate": "PASS",
                "Review": "accept",
                "Human": "accept",
                "Wall_s": "5.0",
            },
        ]
        receipts = {
            "t1-smolvm-stderr-first": _receipt("PASS", 0, 1),
            "t2-tree-sig-119": _receipt("PASS", 0, 2),
        }
        totals = {
            "Tasks": "2",
            "Gate_pass": "1",
            "Review_accept": "2",
            "Human_accept": "2",
            "Wall_s": "5.0",
            "Attempts": "1",
            "Exit_sum": "0",
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            root = Path(tmp)
            _write_tree(root, rows, receipts, totals)
            errors = CHECK.check_report(root)
            joined = "\n".join(errors)
            self.assertIn("Gate_pass", joined)
            self.assertIn("Wall_s", joined)
            self.assertIn("Attempts", joined)
            self.assertNotIn("status", joined)

    def test_missing_receipt_fails(self) -> None:
        rows = [
            {
                "Task": "t1-smolvm-stderr-first",
                "Status": "PASS",
                "Exit": "0",
                "Attempts": "1",
                "Gate": "PASS",
                "Review": "accept",
                "Human": "accept",
                "Wall_s": "1.0",
            }
        ]
        totals = {
            "Tasks": "1",
            "Gate_pass": "1",
            "Review_accept": "1",
            "Human_accept": "1",
            "Wall_s": "1.0",
            "Attempts": "1",
            "Exit_sum": "0",
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            root = Path(tmp)
            (root / "REPORT.md").write_text(_report(rows, totals), encoding="utf-8")
            errors = CHECK.check_report(root)
            self.assertTrue(any("receipt missing" in item for item in errors))

    def test_live_report_when_present(self) -> None:
        report = SIX / "REPORT.md"
        if not report.is_file():
            self.skipTest("REPORT.md not written yet")
        self.assertEqual(CHECK.check_report(SIX), [])

    def test_variance_report_when_present(self) -> None:
        root = SIX / "variance"
        if not (root / "REPORT.md").is_file():
            self.skipTest("variance REPORT.md not written yet")
        self.assertEqual(CHECK.check_report(root), [])


class TrialCommandTests(unittest.TestCase):
    def test_argv_targets_the_clone_and_keeps_review(self) -> None:
        repo = Path("/tmp-not-used/clone-t1")
        argv = RUN.build_argv(
            Path("/work/pfy"),
            "fix the function",
            repo,
            "demo-base",
            "python3 -m unittest tests.test_mvp2_t1_smolvm_evidence",
            Path("/work/eval/receipts/t1"),
        )
        self.assertEqual(argv[argv.index("--repo") + 1], str(repo))
        self.assertNotIn("--local", argv)
        self.assertNotIn("--no-review", argv)
        self.assertIn("--keep-worktree", argv)
        self.assertEqual(argv[2], "fix the function")

    def test_retries_zero_stays_reviewed(self) -> None:
        argv = RUN.build_argv(
            Path("/work/pfy"),
            "task",
            Path("/work/clone"),
            "demo-base",
            "python3 -m unittest tests.test_mvp2_t1_smolvm_evidence",
            Path("/work/out"),
            retries=0,
        )
        self.assertEqual(argv[argv.index("--retries") + 1], "0")
        self.assertNotIn("--no-review", argv)

    def test_secret_scan_counts_without_echoing_the_value(self) -> None:
        token = "bea" + "rer " + ("a" * 12)
        self.assertEqual(RUN.secret_hits("status PASS"), 0)
        self.assertEqual(RUN.secret_hits(token), 1)
        self.assertNotIn(token, RUN.redact_text(token))
        self.assertIn("[redacted]", RUN.redact_text(token))


if __name__ == "__main__":
    unittest.main()
