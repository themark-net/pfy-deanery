"""catalog_check fails an I3 or I4 CI, testing, or review tool with no self_pipeline.

Fail: a review or test tool reaches I3 with no record, or with applied and
blank evidence, and the check still exits 0.
Recovery: set applied plus a commit or doc path, or not_applicable plus a
reason. pending stays at I3 only when grace is true. A tool that does not
cover the job is left alone. The check does not demote the card.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "catalog_check_self_pipeline", ROOT / "scripts" / "catalog_check.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CatalogSelfPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_i3_review_tool_without_the_field_fails(self):
        row = {
            "integration_stage": "I3",
            "uses": "Per-file code review before merge.",
            "features": ["diff comments"],
            "catalog_tags": ["#skills"],
        }
        problems = self.mod.self_pipeline_problems("Review Bot", row)
        self.assertEqual(len(problems), 1)
        self.assertIn("Review Bot", problems[0])
        self.assertIn("self_pipeline is missing", problems[0])
        self.assertIn("I3", problems[0])

    def test_applied_evidence_passes_and_blank_evidence_fails(self):
        row = {
            "integration_stage": "I3",
            "uses": "Per-file code review before merge.",
            "self_pipeline": {
                "status": "applied",
                "evidence": "docs/ops/example.md",
            },
        }
        self.assertEqual(self.mod.self_pipeline_problems("Review Bot", row), [])
        row["self_pipeline"] = {"status": "applied", "evidence": "  "}
        problems = self.mod.self_pipeline_problems("Review Bot", row)
        self.assertEqual(len(problems), 1)
        self.assertIn("needs evidence", problems[0])

    def test_non_ci_tool_at_i3_is_unaffected(self):
        row = {
            "integration_stage": "I3",
            "uses": "Local vector store for notes.",
            "features": ["sqlite"],
            "catalog_tags": ["#local-first", "#pipeline"],
        }
        self.assertEqual(self.mod.self_pipeline_problems("Notes DB", row), [])

    def test_explicit_review_tag_classifies_when_the_uses_do_not(self):
        row = {
            "integration_stage": "I3",
            "uses": "Planning notes for a design doc.",
            "features": ["checklist"],
            "catalog_tags": ["#review"],
        }
        problems = self.mod.self_pipeline_problems("Tagged Review", row)
        self.assertEqual(len(problems), 1)
        self.assertIn("Tagged Review", problems[0])
        self.assertIn("self_pipeline is missing", problems[0])

    def test_pending_without_grace_fails_and_grace_keeps_the_stage(self):
        row = {
            "integration_stage": "I4",
            "uses": "Runs the test suite.",
            "self_pipeline": {"status": "pending"},
        }
        problems = self.mod.self_pipeline_problems("Suite Runner", row)
        self.assertEqual(len(problems), 1)
        self.assertIn("grace", problems[0])
        row["self_pipeline"] = {"status": "pending", "grace": True}
        self.assertEqual(self.mod.self_pipeline_problems("Suite Runner", row), [])

    def test_not_applicable_needs_a_reason(self):
        row = {
            "integration_stage": "I3",
            "catalog_tags": ["#tdd"],
            "uses": "Planning notes for a design doc.",
            "self_pipeline": {"status": "not_applicable"},
        }
        problems = self.mod.self_pipeline_problems("Tdd Skill", row)
        self.assertEqual(len(problems), 1)
        self.assertIn("needs a reason", problems[0])
        row["self_pipeline"] = {
            "status": "not_applicable",
            "reason": "The first-party eval ladder already covers this job.",
        }
        self.assertEqual(self.mod.self_pipeline_problems("Tdd Skill", row), [])

    def test_i2_ci_tool_does_not_need_the_field(self):
        row = {
            "integration_stage": "I2",
            "uses": "Per-file code review before merge.",
        }
        self.assertEqual(self.mod.self_pipeline_problems("Review Probe", row), [])


if __name__ == "__main__":
    unittest.main()
