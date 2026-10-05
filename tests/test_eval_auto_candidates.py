"""eval-auto tries fit-select candidates, then the lab-proven coder (T-0074)."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("eval_auto_candidates", ROOT / "scripts" / "eval_auto_candidates.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class EvalAutoCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_default_is_the_lab_coder(self):
        self.assertEqual(
            self.mod.gate_candidates({}),
            ["deepseek-coder:6.7b-instruct", "deepseek-coder:6.7b"],
        )

    def test_explicit_list_wins_and_drops_blanks(self):
        env = {"EVAL_GATE_CANDIDATES": " qwen2.5-coder:7b , , deepseek-coder:6.7b "}
        self.assertEqual(
            self.mod.gate_candidates(env),
            ["qwen2.5-coder:7b", "deepseek-coder:6.7b"],
        )

    def test_single_gate_model_is_one_candidate(self):
        self.assertEqual(
            self.mod.gate_candidates({"EVAL_GATE_MODEL": "deepseek-coder:6.7b"}),
            ["deepseek-coder:6.7b"],
        )


if __name__ == "__main__":
    unittest.main()
