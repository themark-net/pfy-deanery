"""A missing committed eval tag retries the local fallback once.

Fail: score_task stays on qwen3.6:35b after the local host says that tag is
missing, or it retries an explicit other tag, a timeout, or a public host.
Recover: one more local call on qwen2.5:14b. A second miss stops. The result
model is the tag that actually ran.
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
MISSING = "chat failed openai=HTTP Error 404 ollama=model not found"
LOCAL = "http://127.0.0.1:9/v1"
PUBLIC = "https://api.openai.com/v1"


def _load():
    spec = importlib.util.spec_from_file_location(
        "run_scored_task_fallback",
        ROOT / "examples" / "eval-harness" / "run_scored_task.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


class ScoredTaskFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="scored-fallback-"))
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
            for key in ("EVAL_MODE", "EVAL_MODEL", "PFY_MODEL_NO_PAID", "PFY_LLAMA_NGRAM")
        }
        for key in self.saved:
            os.environ.pop(key, None)

        def chat(**kwargs):
            name = kwargs.get("model_name") or ""
            self.calls.append(name)
            script = self.script.get(name)
            if isinstance(script, Exception):
                raise script
            if script is None:
                raise RuntimeError(MISSING)
            return script

        self.script: dict[str, object] = {}
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

    def test_missing_default_retries_the_fallback_once(self) -> None:
        self.script = {"qwen2.5:14b": CODE}
        rec, err = self._score(model_name="qwen3.6:35b", base=LOCAL)
        self.assertEqual(self.calls, ["qwen3.6:35b", "qwen2.5:14b"], err)
        self.assertTrue(rec.get("pass"), rec)
        self.assertEqual(rec.get("model"), "openai/qwen2.5:14b")
        self.assertIn("eval-suite: fallback qwen3.6:35b -> qwen2.5:14b", err)

        self.calls.clear()
        os.environ["EVAL_MODE"] = "matrix"
        rec, err = self._score(model_name="qwen3.6:35b", base=LOCAL)
        self.assertEqual(self.calls, ["qwen3.6:35b", "qwen2.5:14b"])
        self.assertIn("matrix: fallback qwen3.6:35b -> qwen2.5:14b", err)
        self.assertTrue(rec.get("pass"), rec)
        os.environ.pop("EVAL_MODE", None)

        self.calls.clear()
        self.script = {}
        rec, err = self._score(model_name="qwen3.6:35b", base=LOCAL)
        self.assertEqual(self.calls, ["qwen3.6:35b", "qwen2.5:14b"], err)
        self.assertFalse(rec.get("pass"))
        self.assertEqual(rec.get("error"), "completion")
        self.assertIn("not found", "\n".join(rec.get("failures") or []))

    def test_explicit_tag_timeout_and_public_host_do_not_retry(self) -> None:
        self.script = {}
        rec, err = self._score(model_name="custom:9b", base=LOCAL)
        self.assertEqual(self.calls, ["custom:9b"], err)
        self.assertNotIn("fallback", err)
        self.assertFalse(rec.get("pass"))

        self.calls.clear()
        self.script = {"qwen3.6:35b": RuntimeError("chat failed openai=timed out ollama=timed out")}
        rec, err = self._score(model_name="qwen3.6:35b", base=LOCAL)
        self.assertEqual(self.calls, ["qwen3.6:35b"], err)
        self.assertNotIn("fallback", err)
        self.assertIn("timed out", "\n".join(rec.get("failures") or []))

        self.calls.clear()
        self.script = {"gpt-6.1-sol": RuntimeError(MISSING)}
        with mock.patch("builtins.input", side_effect=AssertionError("prompted")):
            rec, err = self._score(
                model_name="gpt-6.1-sol",
                base=PUBLIC,
                yes=True,
                max_usd=50,
                isatty=False,
            )
        self.assertEqual(self.calls, ["gpt-6.1-sol"], err)
        self.assertNotIn("fallback", err)
        self.assertFalse(rec.get("pass"))
        self.assertEqual(rec.get("model"), "openai/gpt-6.1-sol")


if __name__ == "__main__":
    unittest.main()
