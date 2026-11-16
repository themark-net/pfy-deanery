"""A public eval suite quotes every cell before it opens a socket.

Fail: run_suite.py contacts a public OPENAI_BASE_URL, or spends, before one
suite estimate is accepted. A cap that covers a single cell must not approve
two cells. Recover: no flags, --yes alone, a short cap, or a declined TTY
leaves the socket closed and names the local $0 host. A covering cap, or y
on a TTY, then runs the cells. A local host still sends and does not ask.
"""
from __future__ import annotations

import importlib.util
import io
import os
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "examples" / "eval-harness"
CODE = "def is_palindrome(s):\n    return s == s[::-1]\n"
PUBLIC = "https://api.openai.com/v1"
LOCAL = "http://127.0.0.1:9/v1"


def _load_suite():
    if str(HARNESS) not in sys.path:
        sys.path.insert(0, str(HARNESS))
    spec = importlib.util.spec_from_file_location(
        "eval_run_suite_cost_gate", HARNESS / "run_suite.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class SuiteCostGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="suite-cost-"))
        self.tasks = self.tmp / "tasks"
        self.prompts = {
            "tiny": "Write is_palindrome.\n",
            "other": "Write is_palindrome for the suite gate.\n",
        }
        for name, prompt in self.prompts.items():
            task = self.tasks / name
            task.mkdir(parents=True)
            (task / "prompt.txt").write_text(prompt, encoding="utf-8")
            (task / "test_task.py").write_text(
                "def run_tests(ns):\n"
                "    fn = ns['is_palindrome']\n"
                "    ok = fn('aba') is True and fn('ab') is False\n"
                "    return [] if ok else ['bad']\n",
                encoding="utf-8",
            )
        self.mod = _load_suite()
        self.saved = {
            key: os.environ.get(key)
            for key in (
                "OPENAI_BASE_URL", "EVAL_MODEL", "EVAL_MODELS", "EVAL_MODE",
                "EVAL_GATE_MODEL", "PFY_MODEL_NO_PAID", "PFY_LLAMA_NGRAM",
                "LITELLM_SMOKE_MODEL", "PFY_MODEL_EVAL_SUITE", "PFY_MODEL_MATRIX",
            )
        }
        for key in self.saved:
            os.environ.pop(key, None)
        self.log: list[str] = []
        self.chats: list[str] = []

        def chat(**kwargs):
            self.log.append("chat")
            self.chats.append(kwargs.get("model_name") or "")
            return CODE

        def urlopen(*_a, **_k):
            self.log.append("open")
            raise urllib.error.URLError("suite gate blocked the socket")

        scored = self.mod.score_task.__globals__
        self.chat_patch = mock.patch.dict(scored, {"_chat_completion": chat})
        self.open_patch = mock.patch("urllib.request.urlopen", side_effect=urlopen)
        self.chat_patch.start()
        self.open_patch.start()

    def tearDown(self) -> None:
        self.chat_patch.stop()
        self.open_patch.stop()
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def _quote_sum(self, names: list[str]) -> str:
        from pfylib.model_choice import count_tokens, quote

        total = Decimal("0")
        for name in names:
            tokens, _method = count_tokens(self.prompts[name])
            total += Decimal(quote("gpt-6.1-sol", tokens, 512)["cost_text"])
        return f"{total.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP):.4f}"

    def _run(self, extra: list[str], *, base: str, tty: bool = False, answer: str = ""):
        os.environ["OPENAI_BASE_URL"] = base
        argv = [
            "run_suite.py",
            "--tasks-root", str(self.tasks),
            "--tasks", "tiny,other",
            *extra,
        ]
        buf = io.StringIO()
        code = 1
        with mock.patch.object(sys, "argv", argv):
            with mock.patch.object(sys.stdin, "isatty", return_value=tty):
                with mock.patch("builtins.input", return_value=answer) as asked:
                    with redirect_stderr(buf):
                        try:
                            code = self.mod.main()
                        except SystemExit as exc:
                            code = exc.code if isinstance(exc.code, int) else 1
        return code, buf.getvalue(), asked

    def test_public_suite_stays_closed_until_the_sum_is_covered(self) -> None:
        one = self._quote_sum(["tiny"])
        both = self._quote_sum(["tiny", "other"])
        self.assertNotEqual(one, both)

        code, err, asked = self._run(["--models", "gpt-6.1-sol"], base=PUBLIC)
        self.assertEqual(self.log, [], err)
        self.assertEqual(code, 1)
        self.assertEqual(asked.call_count, 0)
        self.assertIn("suite cost estimate: $%s" % both, err)
        self.assertIn("for 2 cells", err)
        self.assertIn("gpt-6.1-sol", err)
        self.assertIn("No call is sent until you say yes", err)
        self.assertIn("host.docker.internal:11435", err)
        self.assertIn("$0", err)
        self.assertIn("No model was called", err)

        self.log.clear()
        code, err, asked = self._run(
            ["--models", "gpt-6.1-sol", "--yes"], base=PUBLIC,
        )
        self.assertEqual(self.log, [], err)
        self.assertEqual(code, 1)
        self.assertIn("--yes requires --max-usd", err)
        self.assertIn("No model was called", err)

        self.log.clear()
        code, err, _asked = self._run(
            ["--models", "gpt-6.1-sol", "--yes", "--max-usd", one], base=PUBLIC,
        )
        self.assertEqual(self.log, [], err)
        self.assertEqual(code, 1)
        self.assertIn("exceeds --max-usd", err)
        self.assertIn(both, err)

        self.log.clear()
        code, err, _asked = self._run(
            ["--models", "gpt-6.1-sol", "--max-cost", both], base=PUBLIC,
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(self.chats, ["gpt-6.1-sol", "gpt-6.1-sol"])
        self.assertEqual(self.log[0], "open")
        self.assertEqual(self.log.count("chat"), 2)

    def test_tty_answer_and_unpriced_tag_and_local_host(self) -> None:
        both = self._quote_sum(["tiny", "other"])

        code, err, asked = self._run(
            ["--models", "gpt-6.1-sol"], base=PUBLIC, tty=True, answer="n",
        )
        self.assertEqual(asked.call_count, 1)
        self.assertEqual(self.log, [], err)
        self.assertEqual(code, 1)
        self.assertIn("declined", err)
        self.assertIn(both, err)

        self.log.clear()
        self.chats.clear()
        code, err, asked = self._run(
            ["--models", "gpt-6.1-sol"], base=PUBLIC, tty=True, answer="y",
        )
        self.assertEqual(asked.call_count, 1)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.chats, ["gpt-6.1-sol", "gpt-6.1-sol"])

        self.log.clear()
        self.chats.clear()
        code, err, asked = self._run(
            ["--models", "qwen2.5:14b"], base=PUBLIC,
        )
        self.assertEqual(asked.call_count, 0)
        self.assertEqual(self.log, [], err)
        self.assertEqual(code, 1)
        self.assertIn("no paid price", err)
        self.assertIn("qwen2.5:14b", err)
        self.assertIn("No model was called", err)
        self.assertNotIn("suite cost estimate:", err)

        self.log.clear()
        self.chats.clear()
        code, err, asked = self._run(
            ["--models", "qwen3.6:35b"], base=LOCAL,
        )
        self.assertEqual(asked.call_count, 0)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.chats, ["qwen3.6:35b", "qwen3.6:35b"])
        self.assertNotIn("suite cost estimate:", err)
        self.assertNotIn("No model was called", err)
        self.assertEqual(self.log[0], "open")


if __name__ == "__main__":
    unittest.main()
