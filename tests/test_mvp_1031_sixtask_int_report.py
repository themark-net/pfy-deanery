"""Behavior checks for the integration six-task report and the trial command.

How this fails: a report row disagrees with receipt.json or meta.json, the
totals are not the sum of the rows, the VERDICT line claims GO without both
passes at 6/6, or the recorded command contains --local or a writable path
the meta does not list.
How we recover: regenerate the report from the receipts, or replace the bad
receipt, then re-run this module. The trial argv fails closed if --local or
--no-review is added.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INT = ROOT / "eval" / "mvp-1031" / "sixtask-int"
TASKS = ROOT / "eval" / "mvp2" / "tasks"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


CHECK = _load("sixtask_int_check_report", INT / "check_report.py")
RUN = _load("sixtask_int_run_task", INT / "run_task.py")


def _receipt(status: str = "PASS", exit_code: int = 0, attempts: int = 1, review: str = "accept") -> dict:
    return {
        "schema": "pfy-cloud-build/1",
        "status": status,
        "reason": "ok" if status == "PASS" else "tests",
        "exit_code": exit_code,
        "attempts": [
            {"n": index + 1, "status": status, "reason": "ok"}
            for index in range(attempts)
        ],
        "review": {"verdict": review, "reasons": []},
    }


def _meta(label: str, task: str, writable: list[str], wall: float = 1.0, human: str = "accept") -> dict:
    argv = RUN.build_argv(
        Path("/work/pfy"),
        "task text",
        Path("/work/clone"),
        "demo-base",
        "python3 -m unittest tests.example",
        Path("/work/receipts") / label / task,
        writable=writable,
    )
    return {
        "task": task,
        "label": label,
        "command": argv,
        "writable_test": list(writable),
        "wall_s": wall,
        "human": human,
        "human_note": "matches the task",
        "receipt_reason": "ok",
        "commit": "a" * 40,
        "gate_rerun": {"exit": 0, "acceptance_unchanged": True},
    }


def _write_pair(root: Path, label: str, task: str, receipt: dict, meta: dict) -> None:
    dest = root / "receipts" / label / task
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "receipt.json").write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    (dest / "meta.json").write_text(json.dumps(meta) + "\n", encoding="utf-8")


def _full_green(root: Path) -> None:
    for label in ("pass1", "pass2"):
        for task in CHECK.TASK_IDS:
            writable = RUN.writable_for(task)
            _write_pair(
                root,
                label,
                task,
                _receipt(),
                _meta(label, task, writable),
            )


class ReportCheckTests(unittest.TestCase):
    def test_both_passes_green_is_go(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            root = Path(tmp)
            _full_green(root)
            CHECK.write_report(root)
            self.assertEqual(CHECK.check_report(root), [])
            self.assertIn("VERDICT: GO", (root / "REPORT.md").read_text(encoding="utf-8"))

    def test_planted_status_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            root = Path(tmp)
            _full_green(root)
            _write_pair(
                root,
                "pass1",
                "t1-smolvm-stderr-first",
                _receipt("FAIL", 1, 3, review="none"),
                _meta("pass1", "t1-smolvm-stderr-first", [], human="reject"),
            )
            CHECK.write_report(root)
            text = (root / "REPORT.md").read_text(encoding="utf-8")
            text = text.replace(
                "| pass1 | t1-smolvm-stderr-first | FAIL | 1 | 3 |",
                "| pass1 | t1-smolvm-stderr-first | PASS | 0 | 1 |",
                1,
            )
            (root / "REPORT.md").write_text(text, encoding="utf-8")
            errors = CHECK.check_report(root)
            joined = "\n".join(errors)
            self.assertIn("status", joined)
            self.assertIn("exit", joined)
            self.assertIn("attempts", joined)

    def test_planted_false_go_fails(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            root = Path(tmp)
            for task in CHECK.TASK_IDS:
                _write_pair(root, "pass1", task, _receipt(), _meta("pass1", task, RUN.writable_for(task)))
            CHECK.write_report(root)
            text = (root / "REPORT.md").read_text(encoding="utf-8")
            self.assertIn("VERDICT: NO-GO", text)
            (root / "REPORT.md").write_text(text.replace("VERDICT: NO-GO", "VERDICT: GO"), encoding="utf-8")
            errors = CHECK.check_report(root)
            self.assertTrue(any("verdict" in item for item in errors))

    def test_planted_false_nogo_fails_when_bar_is_met(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            root = Path(tmp)
            _full_green(root)
            CHECK.write_report(root)
            text = (root / "REPORT.md").read_text(encoding="utf-8").replace("VERDICT: GO", "VERDICT: NO-GO")
            (root / "REPORT.md").write_text(text, encoding="utf-8")
            errors = CHECK.check_report(root)
            self.assertTrue(any("wanted VERDICT: GO" in item for item in errors))

    def test_planted_writable_mismatch_fails(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            root = Path(tmp)
            _full_green(root)
            CHECK.write_report(root)
            text = (root / "REPORT.md").read_text(encoding="utf-8")
            needle = (
                "| pass1 | t4-timeout-substep | PASS | 0 | 1 | PASS | accept | accept | 1.0 | "
                "tests/test_x_intake_smoke_112_114.py |"
            )
            self.assertIn(needle, text)
            text = text.replace(
                needle,
                "| pass1 | t4-timeout-substep | PASS | 0 | 1 | PASS | accept | accept | 1.0 | - |",
                1,
            )
            (root / "REPORT.md").write_text(text, encoding="utf-8")
            errors = CHECK.check_report(root)
            self.assertTrue(any("writable" in item for item in errors))

    def test_recorded_local_flag_fails(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "tmp") as tmp:
            root = Path(tmp)
            _full_green(root)
            meta_path = root / "receipts" / "pass1" / "t2-tree-sig-119" / "meta.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["command"] = list(meta["command"]) + ["--local"]
            meta_path.write_text(json.dumps(meta) + "\n", encoding="utf-8")
            CHECK.write_report(root)
            errors = CHECK.check_report(root)
            self.assertTrue(any("--local" in item for item in errors))

    def test_live_report_when_present(self) -> None:
        report = INT / "REPORT.md"
        if not report.is_file():
            self.skipTest("REPORT.md not written yet")
        self.assertEqual(CHECK.check_report(INT), [])


class TrialCommandTests(unittest.TestCase):
    def test_writable_paths_are_only_the_ones_the_task_files_name(self) -> None:
        t4 = (TASKS / "t4-timeout-substep.md").read_text(encoding="utf-8")
        t5 = (TASKS / "t5-receipts-outside-repo.md").read_text(encoding="utf-8")
        t4_paths = RUN.writable_for("t4-timeout-substep")
        t5_paths = RUN.writable_for("t5-receipts-outside-repo")
        self.assertEqual(t4_paths, ["tests/test_x_intake_smoke_112_114.py"])
        self.assertEqual(
            t5_paths,
            [
                "tests/test_x_intake_smoke_117_118.py",
                "tests/test_x_intake_smoke_119_121.py",
            ],
        )
        for path in t4_paths:
            self.assertIn(path, t4)
        for path in t5_paths:
            self.assertIn(path, t5)
        self.assertNotIn("tests/test_mvp2_t4_timeout_step.py", t4_paths)
        self.assertNotIn("tests/test_mvp2_t5_receipts.py", t5_paths)
        for task in (
            "t1-smolvm-stderr-first",
            "t2-tree-sig-119",
            "t3-daemon-stop-fail",
            "t6-tree-sig-three",
        ):
            self.assertEqual(RUN.writable_for(task), [])
            text = (TASKS / (task + ".md")).read_text(encoding="utf-8")
            self.assertIn("Do not edit", text)

    def test_argv_keeps_review_and_names_only_the_allowed_tests(self) -> None:
        repo = Path("/tmp-not-used/clone-t4")
        argv = RUN.build_argv(
            Path("/work/pfy"),
            "fix the timeout text",
            repo,
            "demo-base",
            "python3 -m unittest tests.test_mvp2_t4_timeout_step",
            Path("/work/eval/receipts/t4"),
            writable=RUN.writable_for("t4-timeout-substep"),
        )
        self.assertEqual(argv[argv.index("--repo") + 1], str(repo))
        self.assertNotIn("--local", argv)
        self.assertNotIn("--no-review", argv)
        self.assertIn("--keep-worktree", argv)
        self.assertEqual(argv.count("--writable-test"), 1)
        self.assertEqual(
            argv[argv.index("--writable-test") + 1],
            "tests/test_x_intake_smoke_112_114.py",
        )
        plain = RUN.build_argv(
            Path("/work/pfy"),
            "fix the helper",
            Path("/work/clone-t1"),
            "demo-base",
            "python3 -m unittest tests.test_mvp2_t1_smolvm_evidence",
            Path("/work/eval/receipts/t1"),
            writable=RUN.writable_for("t1-smolvm-stderr-first"),
        )
        self.assertNotIn("--writable-test", plain)
        self.assertNotIn("--local", plain)

    def test_banned_flag_in_the_argv_is_refused(self) -> None:
        with self.assertRaises(SystemExit):
            RUN.build_argv(
                Path("/work/pfy"),
                "task",
                Path("/work/clone"),
                "demo-base",
                "python3 -m unittest tests.example",
                Path("/work/out"),
                writable=["--local"],
            )

    def test_secret_scan_counts_without_echoing_the_value(self) -> None:
        token = "bea" + "rer " + ("a" * 12)
        self.assertEqual(RUN.secret_hits("status PASS"), 0)
        self.assertEqual(RUN.secret_hits(token), 1)
        self.assertNotIn(token, RUN.redact_text(token))
        self.assertIn("[redacted]", RUN.redact_text(token))


if __name__ == "__main__":
    unittest.main()
