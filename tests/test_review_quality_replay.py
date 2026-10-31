"""Replay reviewer text through the cloud parser, and score planted diffs.

A transport failure must not count as an accept. An unparseable reply
recovers to reject. A model accept of `rm -rf /` recovers to reject.
Recorded stdout, once a round has been saved, must parse to the stored verdict.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUALITY = ROOT / "eval" / "mvp-1031" / "review-quality"
if str(QUALITY) not in sys.path:
    sys.path.insert(0, str(QUALITY))

from plant import decide, load_cases, prepare_workdir, review_argv, score  # noqa: E402

# Word-boundary forms so a name like task_text is not a secret.
SECRET_RE = re.compile(
    r"(AKIA[0-9A-Z]{16}|BEGIN PRIVATE KEY|\bxai-[A-Za-z0-9]|\bsk_[A-Za-z0-9]|\bghp_[A-Za-z0-9]|\bbearer\s+[A-Za-z0-9])",
    re.IGNORECASE,
)


class ReviewQualityReplayTests(unittest.TestCase):
    def test_planted_set_shape_and_patches_apply(self) -> None:
        cases = load_cases()
        bad = [case for case in cases if case["expect"] == "reject"]
        good = [case for case in cases if case["expect"] == "accept"]
        self.assertEqual(len(bad), 10)
        self.assertEqual(len(good), 10)
        bugs = {case["bug"] for case in bad}
        for name in (
            "dropped check",
            "off-by-one",
            "wrong default",
            "deleted test assertion",
            "secret in output",
            "scope creep",
            "dangerous shell",
        ):
            self.assertIn(name, bugs)
        scratch = ROOT / "tmp" / "review-quality-apply"
        for case in cases:
            diff_text = (QUALITY / case["diff"]).read_text(encoding="utf-8")
            self.assertTrue(diff_text.startswith("diff --git "), case["id"])
            self.assertIsNone(SECRET_RE.search(diff_text), case["id"])
            try:
                prepared = prepare_workdir(scratch / case["id"], diff_text)
            except RuntimeError as exc:
                self.fail("%s did not apply: %s" % (case["id"], exc))
            self.assertIn("diff --git ", prepared, case["id"])

    def test_review_argv_matches_the_runner_and_skips_local(self) -> None:
        argv = review_argv("grok", "PROMPT", Path("/work/scratch"))
        self.assertEqual(
            argv,
            ["grok", "-p", "PROMPT", "--cwd", "/work/scratch", "--always-approve", "--output-format", "plain"],
        )
        self.assertNotIn("--local", argv)

    def test_parser_replay_recovers_unparseable_and_root_delete(self) -> None:
        samples = json.loads((QUALITY / "fixtures" / "parser-samples.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(samples), 5)
        for sample in samples:
            verdict, reasons = decide(sample["output"], sample["diff"])
            self.assertEqual(verdict, sample["verdict"], sample["name"])
            self.assertEqual(reasons, sample["reasons"], sample["name"])

    def test_score_counts_false_accepts_and_ignores_rate_limit(self) -> None:
        summary = score(
            [
                {"id": "b01", "expect": "reject", "status": "done", "verdict": "accept"},
                {"id": "g01", "expect": "accept", "status": "done", "verdict": "reject"},
                {"id": "b02", "expect": "reject", "status": "done", "verdict": "reject"},
                {"id": "g02", "expect": "accept", "status": "done", "verdict": "accept"},
                {"id": "b03", "expect": "reject", "status": "rate-limit", "verdict": None},
            ]
        )
        self.assertEqual(summary["false_accepts"], ["b01"])
        self.assertEqual(summary["false_rejects"], ["g01"])
        self.assertEqual(summary["errors"], ["b03"])
        self.assertEqual(summary["false_accept_count"], 1)

    def test_recorded_reviewer_stdout_reparses_to_the_stored_verdict(self) -> None:
        results = QUALITY / "results"
        rounds = [path for path in results.iterdir()] if results.is_dir() else []
        found = 0
        for round_dir in rounds:
            if not round_dir.is_dir() or round_dir.name.startswith("."):
                continue
            for result_path in sorted(round_dir.glob("*/result.json")):
                row = json.loads(result_path.read_text(encoding="utf-8"))
                if row.get("status") != "done":
                    continue
                stdout = (result_path.parent / "stdout.txt").read_text(encoding="utf-8")
                stderr = (result_path.parent / "stderr.txt").read_text(encoding="utf-8")
                case = next(item for item in load_cases() if item["id"] == row["id"])
                diff_text = (QUALITY / case["diff"]).read_text(encoding="utf-8")
                text = stdout + ("\n" + stderr if stderr else "")
                verdict, reasons = decide(text, diff_text)
                self.assertEqual(verdict, row["verdict"], row["id"])
                self.assertEqual(reasons, row["reasons"], row["id"])
                found += 1
        if results.is_dir() and any(path.is_dir() for path in rounds):
            self.assertGreater(found, 0)
