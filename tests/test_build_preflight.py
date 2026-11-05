"""Behavior of classify_cloud_failure.

How this fails and how it recovers:

- A zero exit whose log mentions a quota must stay ``other``. Treating it as
  ``rate-limit`` would retry a success. Recovery: ``rc == 0`` returns other
  before any phrase match.
- A quota line that also says ``not logged in`` must stay ``rate-limit``.
  Matching auth first sends the operator to log in during an outage.
  Recovery: the rate-limit rule runs first.
- Gluing stdout to stderr without the required newline can invent a phrase.
  Recovery: the join is ``stdout + "\\n" + stderr``.
- Echoing grok text would return a private-key marker. Recovery: the return
  is only the enum, and this test rejects the marker strings.
- Opening ``auth.json`` would make classification depend on a credential
  file. Recovery: the function is pure. This test never creates or reads
  that file, and it fails if the function opens anything.
"""

from __future__ import annotations

import inspect
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib.build_preflight import classify_cloud_failure  # noqa: E402

RATE_PHRASES = (
    "rate limit",
    "usage limit",
    "quota exceeded",
    "too many requests",
    "429",
)
AUTH_PHRASES = (
    "unauthenticated",
    "not logged in",
    "please log in",
    "auth.json",
)
ENUM = {"rate-limit", "unauthenticated", "other"}


class ClassifyCloudFailureTests(unittest.TestCase):
    def test_each_rate_limit_phrase_wins_even_with_not_logged_in(self):
        for phrase in RATE_PHRASES:
            for text in (phrase, phrase.upper()):
                with self.subTest(phrase=phrase, text=text):
                    self.assertEqual(classify_cloud_failure(1, text, ""), "rate-limit")
                    mixed = text + "\nnot logged in"
                    self.assertEqual(classify_cloud_failure(1, mixed, ""), "rate-limit")
                    self.assertEqual(
                        classify_cloud_failure(1, "", mixed),
                        "rate-limit",
                    )

    def test_rate_limit_in_stdout_beats_auth_in_stderr(self):
        self.assertEqual(
            classify_cloud_failure(1, "rate limit", "not logged in"),
            "rate-limit",
        )
        self.assertEqual(classify_cloud_failure(2, "", "HTTP 429"), "rate-limit")

    def test_each_auth_phrase_without_a_rate_limit_phrase(self):
        for phrase in AUTH_PHRASES:
            for text in (phrase, phrase.upper()):
                with self.subTest(phrase=phrase, text=text):
                    self.assertNotIn("429", text.lower())
                    self.assertEqual(
                        classify_cloud_failure(1, text, "build failed"),
                        "unauthenticated",
                    )
                    self.assertEqual(
                        classify_cloud_failure(1, "build failed", text),
                        "unauthenticated",
                    )

    def test_unrelated_nonzero_exit_is_other(self):
        self.assertEqual(
            classify_cloud_failure(1, "AssertionError: 1 != 2", "quota remaining"),
            "other",
        )
        self.assertEqual(classify_cloud_failure(1, "", ""), "other")
        self.assertEqual(classify_cloud_failure(1, "time limit exceeded", ""), "other")

    def test_phrase_split_across_the_newline_join_is_other(self):
        # "rate " + "limit" would be a rate-limit phrase. The contract inserts
        # a newline, so a split log line must not look like a quota failure.
        self.assertEqual(classify_cloud_failure(1, "rate ", "limit"), "other")

    def test_zero_exit_is_other_even_when_the_text_matches(self):
        self.assertEqual(classify_cloud_failure(0, "rate limit", ""), "other")
        self.assertEqual(classify_cloud_failure(0, "", "not logged in"), "other")
        self.assertEqual(
            classify_cloud_failure(0, "429", "please log in\nauth.json"),
            "other",
        )

    def test_secret_markers_are_not_in_the_return_value(self):
        pem = "BEGIN PRIVATE KEY"
        token = "sk_" + "abcd1234"
        result = classify_cloud_failure(1, pem, token)
        self.assertIn(result, ENUM)
        self.assertEqual(result, "other")
        self.assertNotIn(pem, result)
        self.assertNotIn(token, result)
        self.assertNotIn("sk_", result)

    def test_classifier_takes_no_path_and_opens_no_file(self):
        params = list(inspect.signature(classify_cloud_failure).parameters)
        self.assertEqual(params, ["rc", "stdout", "stderr"])

        scratch = ROOT / "tmp" / "preflight-classify"
        scratch.mkdir(parents=True, exist_ok=True)
        work = Path(tempfile.mkdtemp(prefix="classify-", dir=scratch))
        self.addCleanup(shutil.rmtree, work, ignore_errors=True)
        previous = os.getcwd()
        self.addCleanup(os.chdir, previous)
        os.chdir(work)

        def refuse_open(*_args, **_kwargs):
            raise AssertionError("classify_cloud_failure opened a file")

        with patch("builtins.open", refuse_open), patch("os.open", refuse_open):
            result = classify_cloud_failure(1, "please log in", "")

        names = os.listdir(work)
        self.assertEqual(names, [])
        self.assertNotIn("auth.json", names)
        self.assertEqual(result, "unauthenticated")


if __name__ == "__main__":
    unittest.main()
