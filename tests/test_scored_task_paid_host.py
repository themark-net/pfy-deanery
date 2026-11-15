"""A non-local OPENAI_BASE_URL does not spend until the estimate is accepted.

Fail: score_task posts the task prompt to a public host with no cost line.
Recover: the result names the local default at $0 and does not call the
chat helper. A priced cloud model then follows the yes rules. Local hosts,
including the harness default, still call the helper with no price ask.
"""
from __future__ import annotations

import importlib.util
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
CODE = "def is_palindrome(s):\n    return s == s[::-1]\n"


def _load():
    spec = importlib.util.spec_from_file_location(
        "run_scored_task_paid_host",
        ROOT / "examples" / "eval-harness" / "run_scored_task.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class ScoredTaskPaidHostTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="scored-paid-"))
        self.tasks = self.tmp / "tasks"
        task = self.tasks / "tiny"
        task.mkdir(parents=True)
        (task / "prompt.txt").write_text("Write is_palindrome.\n", encoding="utf-8")
        (task / "test_task.py").write_text(
            "def run_tests(ns):\n"
            "    fn = ns['is_palindrome']\n"
            "    ok = fn('aba') is True and fn('ab') is False\n"
            "    return [] if ok else ['bad']\n",
            encoding="utf-8",
        )
        self.mod = _load()
        self.calls: list[str] = []
        self.saved = {
            key: os.environ.get(key)
            for key in ("OPENAI_BASE_URL", "EVAL_MODEL", "PFY_MODEL_NO_PAID", "PFY_LLAMA_NGRAM")
        }
        os.environ.pop("PFY_MODEL_NO_PAID", None)
        os.environ.pop("PFY_LLAMA_NGRAM", None)

        def chat(**kwargs):
            self.calls.append(kwargs.get("base") or "")
            return CODE

        self.patch = mock.patch.object(self.mod, "_chat_completion", side_effect=chat)
        self.patch.start()

    def tearDown(self) -> None:
        self.patch.stop()
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def _score(self, **kwargs):
        buf = io.StringIO()
        with redirect_stderr(buf):
            rec = self.mod.score_task("tiny", self.tasks, **kwargs)
        return rec, buf.getvalue()

    def test_public_host_does_not_send_until_the_estimate_is_accepted(self) -> None:
        base = "https://api.openai.com/v1"
        with mock.patch("builtins.input", side_effect=AssertionError("prompted")):
            rec, err = self._score(model_name="gpt-6.1-sol", base=base)
        self.assertEqual(self.calls, [], err)
        blob = "\n".join(rec.get("failures") or []) + "\n" + err
        self.assertFalse(rec.get("pass"))
        self.assertEqual(rec.get("error"), "paid_host")
        self.assertIn("cost estimate: $", blob)
        self.assertIn("gpt-6.1-sol", blob)
        self.assertIn("no TTY", blob)
        self.assertIn("No model was called", blob)
        self.assertIn("host.docker.internal:11435", blob)
        self.assertIn("$0", blob)

        self.calls.clear()
        rec, err = self._score(model_name="gpt-6.1-sol", base=base, yes=True, isatty=False)
        self.assertEqual(self.calls, [])
        self.assertIn("--yes requires --max-usd", "\n".join(rec.get("failures") or []) + err)

        self.calls.clear()
        rec, err = self._score(model_name="gpt-6.1-sol", base=base, yes=True, max_usd=0, isatty=False)
        self.assertEqual(self.calls, [])
        self.assertIn("exceeds --max-usd", "\n".join(rec.get("failures") or []) + err)

        self.calls.clear()
        rec, err = self._score(
            model_name="qwen2.5:14b", base=base, yes=True, max_usd=50, isatty=False,
        )
        self.assertEqual(self.calls, [])
        blob = "\n".join(rec.get("failures") or []) + "\n" + err
        self.assertIn("no paid price", blob)
        self.assertIn("No model was called", blob)

        self.calls.clear()
        os.environ["PFY_MODEL_NO_PAID"] = "1"
        rec, err = self._score(model_name="gpt-6.1-sol", base=base, yes=True, max_usd=50, isatty=False)
        self.assertEqual(self.calls, [])
        self.assertIn("paid cloud call blocked", "\n".join(rec.get("failures") or []) + err)
        os.environ.pop("PFY_MODEL_NO_PAID", None)

        self.calls.clear()
        with mock.patch("builtins.input", return_value="n") as asked:
            rec, err = self._score(model_name="gpt-6.1-sol", base=base, isatty=True)
        self.assertEqual(asked.call_count, 1)
        self.assertEqual(self.calls, [])
        self.assertIn("declined", "\n".join(rec.get("failures") or []) + err)

        self.calls.clear()
        with mock.patch("builtins.input", return_value="y") as asked:
            rec, err = self._score(model_name="gpt-6.1-sol", base=base, isatty=True)
        self.assertEqual(asked.call_count, 1)
        self.assertEqual(self.calls, [base])
        self.assertTrue(rec.get("pass"), rec)

        self.calls.clear()
        rec, err = self._score(model_name="gpt-6.1-sol", base=base, yes=True, max_usd=50, isatty=False)
        self.assertEqual(self.calls, [base])
        self.assertTrue(rec.get("pass"), rec)

    def test_local_hosts_send_without_a_price_ask(self) -> None:
        for base in (
            "http://127.0.0.1:9/v1",
            "http://host.docker.internal:11435/v1",
            "http://192.168.1.9:11434/v1",
        ):
            self.calls.clear()
            buf = io.StringIO()
            with redirect_stderr(buf):
                with mock.patch("builtins.input", side_effect=AssertionError("prompted")):
                    rec = self.mod.score_task("tiny", self.tasks, model_name="qwen2.5:14b", base=base)
            self.assertEqual(self.calls, [base], buf.getvalue())
            self.assertTrue(rec.get("pass"), rec)
            self.assertNotIn("No model was called", buf.getvalue())
            self.assertNotIn("cost estimate:", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
