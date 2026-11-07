"""harness2 evidence must keep a notes doc whose file still exists.

The card notes_doc field points at the local README. The evidence list
also cites sources/entries/136-harness2.md. Recompute drops that citation
because it is not the field and it is not a receipt.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY = "notes_doc:sources/entries/136-harness2.md"


def _stage_snapshot() -> dict[str, bytes]:
    base = ROOT / "data" / "stages"
    return {p.name: p.read_bytes() for p in sorted(base.glob("*.json"))}
FIELD = "notes_doc:examples/harness2-local/README.md"
RECEIPT = "pipelines/dogfood/harness2-local/receipt.json"


def _load():
    spec = importlib.util.spec_from_file_location(
        "catalog_stage_eval_notes", ROOT / "scripts" / "catalog_stage_eval.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CatalogStageNotesDocTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_harness2_keeps_entry_notes_doc(self):
        """Fail: recompute drops notes_doc:sources/entries/136-harness2.md.
        Recovery: keep a notes_doc evidence path whose file is under the repo.
        A missing file and an absolute path are not kept.
        The field notes_doc and the live receipt stay.
        The stage files on disk are not written."""
        before = _stage_snapshot()
        self.assertTrue((ROOT / "sources" / "entries" / "136-harness2.md").is_file())
        self.assertTrue((ROOT / "examples" / "harness2-local" / "README.md").is_file())
        by = {row["name"]: row for row in self.mod.evaluations()}
        evidence = by["harness2"]["evidence"]
        self.assertIn(ENTRY, evidence)
        self.assertIn(FIELD, evidence)
        self.assertIn(RECEIPT, evidence)
        found = self.mod.evidence_for(
            "harness2",
            {
                "notes_doc": "examples/harness2-local/README.md",
                "evidence": [ENTRY, "notes_doc:does-not-exist.md", "notes_doc:/etc/passwd"],
            },
            "",
            set(),
        )
        self.assertIn(ENTRY, found)
        self.assertIn(FIELD, found)
        self.assertNotIn("notes_doc:does-not-exist.md", found)
        self.assertNotIn("notes_doc:/etc/passwd", found)
        self.assertEqual(_stage_snapshot(), before)


if __name__ == "__main__":
    unittest.main()
