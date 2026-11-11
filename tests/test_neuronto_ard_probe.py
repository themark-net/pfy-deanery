"""Offline checks for the Neuronto tool-search probe.

The child is eval/evals/neuronto-ard-registry/probe.py.
Cases live in eval/evals/neuronto-ard-registry/fixtures/intent.json.
The recorded measurement is eval/evals/neuronto-ard-registry/results.json.
This test does not call the network. A moving-company route must stay off intent.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval/evals/neuronto-ard-registry/probe.py"
FIXTURE = ROOT / "eval/evals/neuronto-ard-registry/fixtures/intent.json"
RESULTS = ROOT / "eval/evals/neuronto-ard-registry/results.json"


class NeurontoArdProbeTests(unittest.TestCase):
    def test_self_check_matches_the_fixture(self) -> None:
        self.assertTrue(FIXTURE.is_file(), "intent fixture missing")
        proc = subprocess.run(
            [sys.executable, str(PROBE), "--self-check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("self-check ok", proc.stdout)

    def test_recorded_search_keeps_false_friends_out(self) -> None:
        data = json.loads(RESULTS.read_text(encoding="utf-8"))
        self.assertGreaterEqual(data["on_intent_novel_servers"], data["threshold"])
        self.assertEqual(data["catalog_hits"], 0)
        self.assertFalse(data["installed"])
        self.assertTrue(data["pin_matches_main"])
        routing = next(row for row in data["queries"] if row["q"] == "local model routing")
        off = [hit for hit in routing["hits"] if not hit["on_intent"]]
        self.assertTrue(any(hit["tool"] == "get_route" for hit in off))
        self.assertTrue(all(hit["tool"] != "get_route" or "model" in hit["missed"] for hit in off))
