"""needs-mark rows name only the action still waiting, and closed slugs drop out.

Operator decision 2026-11-11: magpie's sandboxed eval is answered, a real
install is still a hard stop; Antigravity-Manager is closed as skip-install.
How this fails: the row keeps asking a question that was answered, or a
closed card keeps a row and gets re-queued. How we recover: hard_stop_scope
is appended to the row reason, and a slug in exclusions.tsv gets no card
hard-stop row and no queue row.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import catalog_needs_mark as nm  # noqa: E402
from scripts.catalog_eval_queue import build  # noqa: E402


class NeedsMarkScopeTest(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory()
        self.root = Path(self._td.name)
        self.stages = self.root / "data" / "stages"
        self.stages.mkdir(parents=True)
        self.excl = self.root / "eval" / "catalog-queue" / "exclusions.tsv"
        self.excl.parent.mkdir(parents=True)
        self._env = dict(os.environ)
        os.environ["PFY_OPS_ROOT"] = str(self.root / "ops")

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self._env)
        self._td.cleanup()

    def _card(self, slug: str, **extra) -> None:
        body = {"name": slug, "integration_stage": "I1", "tier_ceiling": "I1", "uses": "x"}
        body.update(extra)
        (self.stages / f"{slug}.json").write_text(json.dumps(body), encoding="utf-8")

    def test_scope_and_closed_slug(self) -> None:
        self._card("mp", risk_class="runtime-takeover", hard_stop_scope="real install only")
        self._card("ag", risk_class="secrets")
        self._card("plain", risk_class="secrets")
        self.excl.write_text("slug\treason\nag\tSkip-install: LiteLLM covers it.\n", encoding="utf-8")
        rows = nm.collect(self.stages, self.excl, self.root / "none.md", [], self.root)
        by = {row[0]: row for row in rows}
        self.assertEqual(by["mp"][2], "HS-runtime-takeover: risk_class runtime-takeover; real install only")
        self.assertEqual(by["plain"][2], "HS-secrets: risk_class secrets")
        self.assertNotIn("ag", by)
        payload, _count, omitted = build(self.stages, self.excl)
        self.assertNotIn(b"\tag\t", payload)
        self.assertIn(b"\tmp\t", payload)
        self.assertEqual(omitted, 1)

    def test_real_cards(self) -> None:
        magpie = json.loads((ROOT / "data/stages/magpie.json").read_text(encoding="utf-8"))
        self.assertIn("real install", magpie["hard_stop_scope"])
        self.assertIn("HS-runtime-takeover", [f["rule"] for f in magpie["promotion_history"][-1]["failed"]])
        excluded = (ROOT / "eval/catalog-queue/exclusions.tsv").read_text(encoding="utf-8")
        self.assertIn("antigravity-manager\tSkip-install", excluded)


if __name__ == "__main__":
    unittest.main()
