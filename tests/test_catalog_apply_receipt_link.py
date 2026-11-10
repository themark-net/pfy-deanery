"""Apply links a valid on-main receipt that the card does not cite yet.

How this fails: an integrate lane lands eval/integrate/<slug>/receipt.json on
origin/main but nothing adds receipt:... to the card, so every loop tick
refuses the I3 verdict (seven cards sat at I2 this way on 2026-11-09). Or
the link is added for a risky tool, an off-main receipt, or past the
tier_ceiling. How we recover: apply adds the item and writes I3 only for a
valid main-run receipt on a risk-none card at ceiling I3. Every refusal
leaves the card bytes unchanged.
"""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tests.test_catalog_apply_verdict_receipt import load_mod, make_repo, write_receipt
from tests._ledger import assert_only_ledger

VERDICT = {
    "metric": "probe_exit",
    "threshold": 0,
    "value": 0,
    "value_gate": "pass",
    "modularity_gate": "pass",
    "proposed_stage": "I3",
}


def card(repo: Path, slug: str, ceiling: str = "I3", **extra: object) -> Path:
    path = repo / "data" / "stages" / f"{slug}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    body = {
        "name": slug,
        "integration_stage": "I2",
        "tier_ceiling": ceiling,
        "uses": "Preview large JSON files for an agent.",
        "evidence": ["entry:sources/entries/001-x.md", f"eval/integrate/{slug}/fixture.json"],
    }
    body.update(extra)
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return path


def verdict(repo: Path, slug: str) -> Path:
    path = repo / "eval" / "integrate" / slug / "VERDICT.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(VERDICT), encoding="utf-8")
    return path


class ReceiptLinkTest(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = load_mod()
        self._td = tempfile.TemporaryDirectory()
        self.td = Path(self._td.name)
        self.repo, self.main_sha, self.side_sha = make_repo(self.td)

    def tearDown(self) -> None:
        self._td.cleanup()

    def _apply(self, slug: str, path: Path) -> tuple[int | None, str]:
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                rc = self.mod.apply_verdict(path, verdict(self.repo, slug), None, self.repo)
        except self.mod.Refuse as exc:
            return None, str(exc)
        return rc, out.getvalue()

    def test_valid_main_receipt_is_linked_and_promotes_to_i3(self) -> None:
        write_receipt(self.repo, "goodtool", self.main_sha)
        path = card(self.repo, "goodtool", risk_class="none")
        rc, out = self._apply("goodtool", path)
        self.assertEqual(rc, 0, out)
        self.assertIn("linked receipt:eval/integrate/goodtool/receipt.json", out)
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["integration_stage"], "I3")
        self.assertIn("receipt:eval/integrate/goodtool/receipt.json", data["evidence"])
        before = path.read_bytes()
        rc, out = self._apply("goodtool", path)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("linked", out)
        self.assertEqual(path.read_bytes(), before, "second apply must not rewrite the card")

    def test_refusals_link_nothing_and_keep_bytes(self) -> None:
        cases = []
        write_receipt(self.repo, "offmain", self.side_sha)
        cases.append(("offmain", card(self.repo, "offmain", risk_class="none")))
        write_receipt(self.repo, "sectool", self.main_sha)
        cases.append(("sectool", card(self.repo, "sectool", risk_class="security")))
        write_receipt(self.repo, "moneytool", self.main_sha)
        cases.append(("moneytool", card(self.repo, "moneytool", uses="Places trading orders through a broker.")))
        write_receipt(self.repo, "gputool", self.main_sha)
        cases.append(("gputool", card(self.repo, "gputool", risk_class="none", uses="Runs a ROCm gpu kernel.")))
        write_receipt(self.repo, "lowceil", self.main_sha)
        cases.append(("lowceil", card(self.repo, "lowceil", ceiling="I1", risk_class="none")))
        cases.append(("noreceipt", card(self.repo, "noreceipt", risk_class="none")))
        for slug, path in cases:
            with self.subTest(slug=slug):
                before = path.read_bytes()
                rc, msg = self._apply(slug, path)
                self.assertIsNone(rc, msg)
                self.assertIn("above-ceiling", msg)
                assert_only_ledger(self, path, before)


if __name__ == "__main__":
    unittest.main()
