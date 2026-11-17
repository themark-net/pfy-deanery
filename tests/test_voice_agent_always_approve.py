"""VOICE_AGENT_ALWAYS_APPROVE defaults off; --always-approve is opt-in only.

Fail: unset env still inserts --always-approve, so a voice Grok run would
auto-approve tools with no operator yes.
Recovery: default and explicit off never pass the flag; 1/true/yes/on does.
A fake grok records argv. No real paid call.
"""
from __future__ import annotations

import importlib.util
import os
import stat
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "examples" / "voice-stt-edge" / "agent_runner.py"


def _load():
    spec = importlib.util.spec_from_file_location("voice_agent_runner", RUNNER)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class VoiceAlwaysApproveTests(unittest.TestCase):
    def setUp(self):
        self.mod = _load()
        self._saved = os.environ.get("VOICE_AGENT_ALWAYS_APPROVE")
        os.environ.pop("VOICE_AGENT_ALWAYS_APPROVE", None)

    def tearDown(self):
        if self._saved is None:
            os.environ.pop("VOICE_AGENT_ALWAYS_APPROVE", None)
        else:
            os.environ["VOICE_AGENT_ALWAYS_APPROVE"] = self._saved

    def _run(self, env_value: str | None, td: Path) -> dict:
        bindir = td / "bin"
        bindir.mkdir()
        argv_log = td / "argv.txt"
        grok = bindir / "grok"
        grok.write_text(
            "#!/usr/bin/env bash\n"
            f"printf '%s\\n' \"$@\" > '{argv_log}'\n"
            "echo FAKE_GROK_OK\n",
            encoding="utf-8",
        )
        grok.chmod(grok.stat().st_mode | stat.S_IEXEC)
        if env_value is None:
            os.environ.pop("VOICE_AGENT_ALWAYS_APPROVE", None)
        else:
            os.environ["VOICE_AGENT_ALWAYS_APPROVE"] = env_value
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = str(bindir) + os.pathsep + old_path
        (td / "repo").mkdir()
        out = td / "out"
        out.mkdir()
        try:
            return self.mod.run_grok(
                "say hello",
                td / "repo",
                out,
                max_turns=2,
                timeout_s=5,
                run_id="t1",
            )
        finally:
            os.environ["PATH"] = old_path

    def _argv(self, td: Path) -> list[str]:
        return (td / "argv.txt").read_text(encoding="utf-8").splitlines()

    def test_default_off_does_not_pass_always_approve(self):
        with tempfile.TemporaryDirectory(prefix="voice-approve-") as raw:
            td = Path(raw)
            result = self._run(None, td)
            self.assertTrue((td / "argv.txt").exists(), result)
            argv = self._argv(td)
            self.assertNotIn("--always-approve", argv)
            self.assertIn("--prompt-file", argv)
            self.assertIn("FAKE_GROK_OK", result.get("reply") or "")

    def test_explicit_off_does_not_pass_always_approve(self):
        for value in ("0", "false", "no", "off", ""):
            with self.subTest(value=value):
                with tempfile.TemporaryDirectory(prefix="voice-approve-") as raw:
                    td = Path(raw)
                    self._run(value, td)
                    self.assertNotIn("--always-approve", self._argv(td))

    def test_opt_in_passes_always_approve_once(self):
        for value in ("1", "true", "yes", "on"):
            with self.subTest(value=value):
                with tempfile.TemporaryDirectory(prefix="voice-approve-") as raw:
                    td = Path(raw)
                    self._run(value, td)
                    argv = self._argv(td)
                    self.assertEqual(argv.count("--always-approve"), 1, argv)
