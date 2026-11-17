"""T-0094: optional short local TTS status is off until opted in.

Fail: a voice run speaks (or tries to download a voice model) with no
VOICE_TTS yes, or a missing binary / TTS crash fails the agent run.
Recovery: default is silence; opt-in with no binary skips and logs why;
opt-in with a fake binary is invoked once with the short status text;
a TTS error leaves the mock agent result unchanged. No model fetch, no
paid call, no GPU pull.
"""
from __future__ import annotations

import importlib.util
import os
import stat
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEAK = ROOT / "examples" / "voice-tts-status" / "speak_status.py"
RUNNER = ROOT / "examples" / "voice-stt-edge" / "agent_runner.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class SpeakStatusTests(unittest.TestCase):
    def setUp(self):
        self.mod = _load(SPEAK, "voice_speak_status")
        self._saved = {k: os.environ.get(k) for k in ("VOICE_TTS", "VOICE_TTS_MODE", "VOICE_TTS_PIPER_MODEL", "PATH")}
        os.environ.pop("VOICE_TTS", None)
        os.environ.pop("VOICE_TTS_MODE", None)
        os.environ.pop("VOICE_TTS_PIPER_MODEL", None)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _fake_bin(self, td: Path, name: str = "espeak-ng") -> Path:
        bindir = td / "bin"
        bindir.mkdir(exist_ok=True)
        log = td / "invoked.txt"
        path = bindir / name
        path.write_text(
            "#!/bin/sh\n"
            f"printf '%s\\n' \"$0\" \"$@\" > '{log}'\n"
            "exit 0\n",
            encoding="utf-8",
        )
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
        os.environ["PATH"] = str(bindir)
        return log

    def test_default_off_does_not_invoke_tts(self):
        with tempfile.TemporaryDirectory(prefix="voice-tts-") as raw:
            td = Path(raw)
            log = self._fake_bin(td)
            result = self.mod.speak_status("done")
            self.assertTrue(result.get("skipped"), result)
            self.assertFalse(log.exists())
            self.assertIn("off", (result.get("reason") or "").lower())

    def test_opt_in_without_binary_skips_and_logs(self):
        with tempfile.TemporaryDirectory(prefix="voice-tts-") as raw:
            td = Path(raw)
            os.environ["PATH"] = str(td / "empty")
            (td / "empty").mkdir()
            os.environ["VOICE_TTS"] = "1"
            result = self.mod.speak_status("done")
            self.assertTrue(result.get("skipped"), result)
            self.assertIn("binary", (result.get("reason") or "").lower())

    def test_opt_in_invokes_fake_once_with_status_text(self):
        with tempfile.TemporaryDirectory(prefix="voice-tts-") as raw:
            td = Path(raw)
            log = self._fake_bin(td, "espeak-ng")
            os.environ["VOICE_TTS"] = "1"
            result = self.mod.speak_status("fail")
            self.assertFalse(result.get("skipped"), result)
            self.assertTrue(result.get("ok"), result)
            lines = log.read_text(encoding="utf-8").splitlines()
            self.assertTrue(lines, result)
            self.assertEqual(sum(1 for line in lines if line.endswith("espeak-ng") or line.endswith("/espeak-ng")), 1)
            self.assertIn("fail", lines)

    def test_piper_without_model_file_is_not_used(self):
        with tempfile.TemporaryDirectory(prefix="voice-tts-") as raw:
            td = Path(raw)
            log = self._fake_bin(td, "piper")
            os.environ["VOICE_TTS"] = "1"
            os.environ.pop("VOICE_TTS_PIPER_MODEL", None)
            result = self.mod.speak_status("done")
            self.assertTrue(result.get("skipped"), result)
            self.assertFalse(log.exists())



    def test_default_mode_speaks_status_not_the_reply(self):
        """Fail: default opt-in would speak the full agent reply."""
        with tempfile.TemporaryDirectory(prefix="voice-tts-") as raw:
            td = Path(raw)
            log = self._fake_bin(td, "espeak-ng")
            os.environ["VOICE_TTS"] = "1"
            os.environ.pop("VOICE_TTS_MODE", None)
            phrase = self.mod.phrase_for_result(
                {"ok": True, "reply": "The tests passed and the branch is green."}
            )
            self.assertEqual(phrase, "done")
            result = self.mod.speak_status(phrase)
            self.assertFalse(result.get("skipped"), result)
            lines = log.read_text(encoding="utf-8").splitlines()
            self.assertIn("done", lines)
            self.assertNotIn("The tests passed and the branch is green.", lines)

    def test_reply_mode_speaks_clipped_reply_and_drops_the_tail(self):
        """Fail: reply mode speaks the unclipped tail, or status instead of the reply."""
        with tempfile.TemporaryDirectory(prefix="voice-tts-") as raw:
            td = Path(raw)
            log = self._fake_bin(td, "espeak-ng")
            os.environ["VOICE_TTS"] = "1"
            os.environ["VOICE_TTS_MODE"] = "reply"
            body = ("The agent finished the review. " * 40) + "UNIQUE_REPLY_TAIL"
            self.assertGreater(len(body), self.mod.REPLY_MAX)
            phrase = self.mod.phrase_for_result({"ok": True, "reply": body})
            result = self.mod.speak_status(phrase)
            self.assertFalse(result.get("skipped"), result)
            spoken = result.get("text") or ""
            self.assertLessEqual(len(spoken), self.mod.REPLY_MAX)
            self.assertTrue(spoken.endswith("…"), spoken)
            self.assertNotIn("UNIQUE_REPLY_TAIL", spoken)
            self.assertIn("The agent finished the review", spoken)
            lines = log.read_text(encoding="utf-8").splitlines()
            self.assertTrue(any("The agent finished the review" in line for line in lines), lines)
            self.assertFalse(any("UNIQUE_REPLY_TAIL" in line for line in lines), lines)

    def test_unknown_mode_does_not_switch_to_full_reply(self):
        os.environ["VOICE_TTS"] = "1"
        os.environ["VOICE_TTS_MODE"] = "repy"
        phrase = self.mod.phrase_for_result(
            {"ok": True, "reply": "A long agent reply that must stay unspoken in status mode."}
        )
        self.assertEqual(phrase, "done")

    def test_reply_mode_off_does_not_invoke_tts(self):
        with tempfile.TemporaryDirectory(prefix="voice-tts-") as raw:
            td = Path(raw)
            log = self._fake_bin(td, "espeak-ng")
            os.environ.pop("VOICE_TTS", None)
            os.environ["VOICE_TTS_MODE"] = "reply"
            result = self.mod.speak_status("A reply that must stay silent.")
            self.assertTrue(result.get("skipped"), result)
            self.assertFalse(log.exists())

class AgentTtsHookTests(unittest.TestCase):
    def setUp(self):
        self.runner = _load(RUNNER, "voice_agent_runner_tts")
        self._saved = {k: os.environ.get(k) for k in ("VOICE_TTS", "VOICE_TTS_MODE", "PATH")}
        os.environ.pop("VOICE_TTS", None)
        os.environ.pop("VOICE_TTS_MODE", None)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_hook_does_not_change_agent_result_when_tts_errors(self):
        with tempfile.TemporaryDirectory(prefix="voice-tts-hook-") as raw:
            td = Path(raw)
            bindir = td / "bin"
            bindir.mkdir()
            boom = bindir / "espeak-ng"
            boom.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            boom.chmod(boom.stat().st_mode | stat.S_IEXEC)
            os.environ["PATH"] = str(bindir)
            os.environ["VOICE_TTS"] = "1"
            payload = {
                "status": "ok",
                "ok": True,
                "run_id": "h1",
                "mode": "mock",
                "reply": "LOCAL_VOICE_AGENT_OK",
            }
            out = self.runner.maybe_speak_status(payload)
            self.assertEqual(payload["ok"], True)
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["reply"], "LOCAL_VOICE_AGENT_OK")
            self.assertTrue(out.get("skipped") or not out.get("ok"), out)
    def test_reply_mode_error_does_not_change_agent_result(self):
        with tempfile.TemporaryDirectory(prefix="voice-tts-hook-") as raw:
            td = Path(raw)
            bindir = td / "bin"
            bindir.mkdir()
            boom = bindir / "espeak-ng"
            boom.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            boom.chmod(boom.stat().st_mode | stat.S_IEXEC)
            os.environ["PATH"] = str(bindir)
            os.environ["VOICE_TTS"] = "1"
            os.environ["VOICE_TTS_MODE"] = "reply"
            payload = {
                "status": "ok",
                "ok": True,
                "run_id": "h2",
                "mode": "mock",
                "reply": "The long agent reply should not be lost if TTS fails.",
            }
            out = self.runner.maybe_speak_status(payload)
            self.assertEqual(payload["ok"], True)
            self.assertEqual(payload["reply"], "The long agent reply should not be lost if TTS fails.")
            self.assertTrue(out.get("skipped") or not out.get("ok"), out)

