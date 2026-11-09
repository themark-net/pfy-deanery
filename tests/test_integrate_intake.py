import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def card(slug, stage, ceiling, evidence=None, ticket=None):
    body = {
        "slug": slug,
        "integration_stage": stage,
        "tier_ceiling": ceiling,
        "evidence": evidence or [],
    }
    if ticket is not None:
        body["integration_ticket"] = ticket
    return body


class IntakeTest(unittest.TestCase):
    def test_lists_only_open_i2_cards(self):
        script = ROOT / "scripts" / "integrate_intake.py"
        with tempfile.TemporaryDirectory() as td:
            stages = Path(td)
            cases = {
                "open-tool": card("open-tool", "I2", "I3"),
                "low-ceiling": card("low-ceiling", "I2", "I1"),
                "has-receipt": card(
                    "has-receipt",
                    "I2",
                    "I3",
                    ["receipt:eval/integrate/has-receipt/receipt.json"],
                ),
                "has-ticket": card(
                    "has-ticket", "I2", "I3", ticket="bot/integrate-has-ticket-1108"
                ),
                "already-i3": card("already-i3", "I3", "I3"),
            }
            for slug, body in cases.items():
                (stages / f"{slug}.json").write_text(json.dumps(body))
            cmd = [sys.executable, str(script), "--stages", str(stages), "--json"]
            first = subprocess.run(cmd, capture_output=True, text=True)
            second = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout, second.stdout)
            rows = json.loads(first.stdout)
            self.assertEqual([row["slug"] for row in rows], ["low-ceiling", "open-tool"])
            by = {row["slug"]: row for row in rows}
            self.assertEqual(by["low-ceiling"]["flag"], "tier_ceiling below I3: needs the operator")
            self.assertEqual(by["low-ceiling"]["tier_ceiling"], "I1")
            self.assertEqual(by["open-tool"]["flag"], "")
            for slug in cases:
                self.assertEqual(
                    (stages / f"{slug}.json").read_text(),
                    json.dumps(cases[slug]),
                )
