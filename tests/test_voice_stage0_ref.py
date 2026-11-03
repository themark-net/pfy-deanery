"""T-0095 receipts stay I0. A pass while the documented cloud keys remain is a fail."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class VoiceStage0RefTests(unittest.TestCase):
    def test_stage_cards_stay_i0_and_catalog_rows_stay_absent(self):
        stages = json.loads(_read("data/tool_integration_stages.json"))
        tools = json.loads(_read("data/tools.json"))
        names = {row.get("name") for row in tools.get("tools") or []}
        for card_name, entry in (
            ("Pipecat", "sources/entries/150-pipecat.md"),
            ("LiveKit", "sources/entries/151-livekit.md"),
        ):
            card = stages["tools"][card_name]
            self.assertEqual(card["integration_stage"], "I0", card_name)
            self.assertEqual(card["intent"], "ref_only", card_name)
            self.assertEqual(card["entry"], entry)
            self.assertNotIn(card_name, names)
        self.assertNotIn("freeapp", {str(n).lower() for n in names})
        joined = _read("TOOLS.md")
        self.assertNotIn("150-pipecat", joined)
        self.assertNotIn("151-livekit", joined)
        self.assertNotIn("152-freeapp", joined)

    def test_pipecat_fail_holds_while_quickstart_needs_cloud_keys(self):
        text = _read("sources/entries/150-pipecat.md")
        for key in ("DEEPGRAM_API_KEY", "OPENAI_API_KEY", "CARTESIA_API_KEY"):
            self.assertIn(key, text)
        self.assertIn("Stage-0 FAIL", text)
        self.assertNotIn("Stage-0 PASS", text)

    def test_livekit_fail_holds_while_voice_sample_needs_cloud_env(self):
        text = _read("sources/entries/151-livekit.md")
        for key in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"):
            self.assertIn(key, text)
        self.assertIn("MODEL_LICENSE", text)
        self.assertIn("Stage-0 FAIL", text)
        self.assertNotIn("Stage-0 PASS", text)

    def test_freeapp_fail_holds_without_a_git_pin(self):
        text = _read("sources/entries/152-freeapp.md")
        self.assertIn("No git pin", text)
        self.assertIn("$299", text)
        self.assertIn("Stage-0 FAIL", text)
        self.assertNotIn("Stage-0 PASS", text)


if __name__ == "__main__":
    unittest.main()
