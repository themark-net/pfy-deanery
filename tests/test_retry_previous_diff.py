"""Retry implement prompts must not silently cut the previous diff.

A previous change that fits the cap is pasted in full. One that is over
the cap is omitted with the actual length and the cap named. The marker
...[diff truncated] must not appear. Covers local _agent_prompt and
cloud implement_prompt.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "scripts" / "pfy_build_local.py"
CLOUD = ROOT / "scripts" / "pfy_build_cloud.py"
CUT_MARK = "...[diff truncated]"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load %s" % path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


LOCAL_MOD = _load(LOCAL, "pfy_build_local_retry_prompt")
CLOUD_MOD = _load(CLOUD, "pfy_build_cloud_retry_prompt")


def _over_cap_diff(cap: int) -> tuple[str, str, str]:
    head = "HEAD_UNIQUE_TOKEN_AAA"
    tail = "TAIL_UNIQUE_TOKEN_ZZZ"
    # Pad so the redacted length is strictly over the cap, and the tail
    # starts after the cut point of a silent prefix.
    pad = "x" * (cap + 80)
    return head + pad + tail, head, tail


class LocalRetryPreviousDiff(unittest.TestCase):
    def test_under_cap_previous_diff_is_pasted_in_full(self):
        body = "return a + b + 1  # UNIQUE_UNDER_CAP_LOCAL\n"
        prompt = LOCAL_MOD._agent_prompt(
            "fix add", "python3 -m unittest", feedback="too broad", previous_diff=body
        )
        self.assertIn("too broad", prompt)
        self.assertIn("Previous diff:", prompt)
        self.assertIn(body.strip(), prompt)
        self.assertLess(prompt.index("Previous diff:"), prompt.index("UNIQUE_UNDER_CAP_LOCAL"))
        self.assertNotIn(CUT_MARK, prompt)

    def test_over_cap_previous_diff_is_omitted_not_cut(self):
        cap = LOCAL_MOD.DIFF_PROMPT_CAP
        diff, head, tail = _over_cap_diff(cap)
        self.assertGreater(len(diff), cap)
        prompt = LOCAL_MOD._agent_prompt(
            "fix add", "python3 -m unittest", feedback="too broad", previous_diff=diff
        )
        self.assertIn("too broad", prompt)
        self.assertNotIn(CUT_MARK, prompt)
        self.assertNotIn(head, prompt)
        self.assertNotIn(tail, prompt)
        self.assertIn("Previous diff omitted:", prompt)
        self.assertIn("%d characters" % len(diff), prompt)
        self.assertIn("%d character cap" % cap, prompt)
        self.assertIn("Do not assume its contents", prompt)


class CloudRetryPreviousDiff(unittest.TestCase):
    def test_under_cap_previous_diff_is_pasted_in_full(self):
        body = "return a + b + 1  # UNIQUE_UNDER_CAP_CLOUD\n"
        prompt = CLOUD_MOD.implement_prompt(
            "fix add", "python3 -m unittest", feedback="too broad", previous_diff=body
        )
        self.assertIn("too broad", prompt)
        self.assertIn("Previous diff:", prompt)
        self.assertIn(body.strip(), prompt)
        self.assertLess(prompt.index("Previous diff:"), prompt.index("UNIQUE_UNDER_CAP_CLOUD"))
        self.assertNotIn(CUT_MARK, prompt)

    def test_over_cap_previous_diff_is_omitted_not_cut(self):
        cap = CLOUD_MOD.DIFF_CAP
        diff, head, tail = _over_cap_diff(cap)
        self.assertGreater(len(diff), cap)
        prompt = CLOUD_MOD.implement_prompt(
            "fix add", "python3 -m unittest", feedback="too broad", previous_diff=diff
        )
        self.assertIn("too broad", prompt)
        self.assertNotIn(CUT_MARK, prompt)
        self.assertNotIn(head, prompt)
        self.assertNotIn(tail, prompt)
        self.assertIn("Previous diff omitted:", prompt)
        self.assertIn("%d characters" % len(diff), prompt)
        self.assertIn("%d character cap" % cap, prompt)
        self.assertIn("Do not assume its contents", prompt)


class CloudNulIsNonText(unittest.TestCase):
    def test_non_utf8_file_treats_nul_as_non_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plain = root / "plain.txt"
            nul = root / "nul.txt"
            bad = root / "latin1.txt"
            plain.write_bytes(b"hello world\n")
            nul.write_bytes(b"hello\x00world\n")
            bad.write_bytes(b"caf\xe9 latin-1\n")
            self.assertFalse(CLOUD_MOD._non_utf8_file(root, "plain.txt"))
            self.assertTrue(CLOUD_MOD._non_utf8_file(root, "nul.txt"))
            self.assertTrue(CLOUD_MOD._non_utf8_file(root, "latin1.txt"))


if __name__ == "__main__":
    unittest.main()
