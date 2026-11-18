"""T-0081: OpenAI-compat completion probe handles reasoning models.

No network, no paid keys. The helper must accept a fake response with
empty content plus reasoning_content, and must request a max_tokens
budget large enough for a short reply after hidden reasoning.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "examples" / "opencode-ollama" / "compat_completion.py"


def _load():
    spec = importlib.util.spec_from_file_location("compat_completion", HELPER)
    mod = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class CompatCompletion(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load()

    def test_helper_file_exists(self) -> None:
        self.assertTrue(HELPER.is_file(), "compat_completion.py must exist")

    def test_empty_content_plus_reasoning_is_accepted(self) -> None:
        text = self.mod.extract_completion_text(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "reasoning_content": "OPENCODE_SMOKE_OK",
                        }
                    }
                ]
            }
        )
        self.assertIn("OPENCODE_SMOKE_OK", text)

    def test_content_wins_when_present(self) -> None:
        text = self.mod.extract_completion_text(
            {
                "choices": [
                    {
                        "message": {
                            "content": "OPENCODE_SMOKE_OK",
                            "reasoning_content": "hidden chain",
                        }
                    }
                ]
            }
        )
        self.assertEqual(text, "OPENCODE_SMOKE_OK")

    def test_reasoning_and_thinking_fallbacks(self) -> None:
        for key in ("reasoning", "thinking"):
            text = self.mod.extract_completion_text(
                {"choices": [{"message": {"content": None, key: "  OK  "}}]}
            )
            self.assertIn("OK", text, key)

    def test_blank_content_and_blank_reasoning_is_empty(self) -> None:
        text = self.mod.extract_completion_text(
            {"choices": [{"message": {"content": "  ", "reasoning_content": ""}}]}
        )
        self.assertEqual(text.strip(), "")

    def test_request_budget_is_at_least_256(self) -> None:
        body = self.mod.request_body("qwen3.6:35b")
        self.assertGreaterEqual(int(body["max_tokens"]), 256)
        self.assertEqual(body["model"], "qwen3.6:35b")
        self.assertNotIn("think", body)
        messages = body["messages"]
        self.assertEqual(messages[0]["role"], "user")
        self.assertIn("OPENCODE_SMOKE_OK", messages[0]["content"])

    def test_judge_accepts_reasoning_only_reply(self) -> None:
        ok, reason = self.mod.judge_completion("OPENCODE_SMOKE_OK")
        self.assertTrue(ok, reason)
        ok, reason = self.mod.judge_completion("")
        self.assertFalse(ok)
        self.assertIn("empty", reason.lower())


if __name__ == "__main__":
    unittest.main()
