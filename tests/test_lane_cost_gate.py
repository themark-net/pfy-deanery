"""Parked catalog-loop Grok calls skip unless the 11/11 cost gate says yes.

Fail: an unattended lane or grill starts a fake grok with no approval, or an
attended decline still starts one, or an approved call hides the estimate.
Recover: unattended-unapproved and decline leave $0 spend; a covering cap,
or y on a TTY, then starts grok once. Tests use a fake grok and the repo
price table. No paid API, no real grok.
"""
from __future__ import annotations

import io
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib.cloud_cost_gate import SKIP_EXIT, gate_cloud_prompt
from tests.test_eval_lane import lane_env, make_fixture, write_grok, SCRIPT as EVAL_SCRIPT

# Dummy values only, never logged. Required after a covering yes.
_CLOUD_KEY_VARS = ("XAI_API_KEY", "OPENAI_API_KEY")


def _install_dummy_cloud_keys(target: dict | None = None) -> dict:
    src = os.environ if target is None else target
    saved = {key: src.get(key) for key in _CLOUD_KEY_VARS}
    for key in _CLOUD_KEY_VARS:
        src[key] = "test"
    return saved


def _restore_cloud_keys(saved: dict, target: dict | None = None) -> None:
    src = os.environ if target is None else target
    for key, value in saved.items():
        if value is None:
            src.pop(key, None)
        else:
            src[key] = value

# Import grill after path insert so call_grok is the real one.
import importlib.util

def _load_grill():
    spec = importlib.util.spec_from_file_location(
        "grill_ticket_cost_gate", ROOT / "scripts" / "grill_ticket.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _write_fake(path: Path, log: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/bin/sh\n"
        "printf 'invoked %%s\\n' \"$*\" >> \"%s\"\n"
        "exit 0\n" % log,
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


class GatePromptTests(unittest.TestCase):
    def test_unattended_without_approval_skips(self) -> None:
        buf = io.StringIO()
        with redirect_stderr(buf):
            verdict = gate_cloud_prompt(
                "price this parked lane prompt",
                isatty=False,
            )
        self.assertFalse(verdict["allowed"])
        self.assertIn("no TTY", verdict["reason"])
        self.assertIn("$0 spend", verdict["reason"])
        self.assertIn("No model was called", verdict["reason"])
        self.assertIn("cost estimate:", buf.getvalue())

    def test_attended_decline_skips(self) -> None:
        buf = io.StringIO()
        with redirect_stderr(buf):
            verdict = gate_cloud_prompt(
                "price this parked lane prompt",
                isatty=True,
                answer="n",
            )
        self.assertFalse(verdict["allowed"])
        self.assertIn("declined", verdict["reason"])
        self.assertIn("$0 spend", verdict["reason"])
        self.assertIn("cost estimate:", buf.getvalue())

    def test_attended_yes_and_covering_cap_allow(self) -> None:
        saved = _install_dummy_cloud_keys()
        self.addCleanup(_restore_cloud_keys, saved)
        buf = io.StringIO()
        with redirect_stderr(buf):
            accepted = gate_cloud_prompt(
                "price this parked lane prompt",
                isatty=True,
                answer="y",
            )
        self.assertTrue(accepted["allowed"], accepted)
        self.assertIn("cost estimate:", buf.getvalue())
        with redirect_stderr(io.StringIO()):
            capped = gate_cloud_prompt(
                "price this parked lane prompt",
                isatty=False,
                max_usd=99,
            )
        self.assertTrue(capped["allowed"], capped)

    def test_yes_without_cap_is_not_approval(self) -> None:
        with redirect_stderr(io.StringIO()):
            verdict = gate_cloud_prompt(
                "price this parked lane prompt",
                isatty=False,
                yes=True,
            )
        self.assertFalse(verdict["allowed"])
        self.assertIn("--yes requires --max-usd", verdict["reason"])


class FakeGrokCallTests(unittest.TestCase):
    def test_unattended_grill_does_not_invoke_fake_grok(self) -> None:
        grill = _load_grill()
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            log = td / "grok.log"
            fake = td / "grok"
            _write_fake(fake, log)
            env = os.environ.copy()
            env["PFY_GROK_BIN"] = str(fake)
            env.pop("PFY_CLOUD_YES", None)
            env.pop("PFY_CLOUD_MAX_USD", None)
            saved = dict(os.environ)
            os.environ.clear()
            os.environ.update(env)
            try:
                grill._GATE.update(
                    {"yes": False, "max_usd": None, "isatty": False, "answer": None}
                )
                with self.assertRaises(grill.GrillSkip) as raised:
                    with redirect_stderr(io.StringIO()):
                        grill.call_grok(2, "ask the ticket questions", {"type": "object"})
                self.assertIn("$0 spend", str(raised.exception))
                self.assertFalse(log.exists() and log.read_text().strip())
            finally:
                os.environ.clear()
                os.environ.update(saved)

    def test_attended_decline_does_not_invoke_and_approve_invokes_once(self) -> None:
        grill = _load_grill()
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            log = td / "grok.log"
            fake = td / "grok"
            _write_fake(fake, log)
            env = os.environ.copy()
            env["PFY_GROK_BIN"] = str(fake)
            saved = dict(os.environ)
            os.environ.clear()
            os.environ.update(env)
            try:
                grill._GATE.update(
                    {"yes": False, "max_usd": None, "isatty": True, "answer": "n"}
                )
                with self.assertRaises(grill.GrillSkip):
                    with redirect_stderr(io.StringIO()):
                        grill.call_grok(2, "ask the ticket questions", {"type": "object"})
                self.assertFalse(log.exists() and log.read_text().strip())

                # The fake must return the JSON envelope grill expects, so use
                # a richer stub for the approve path.
            finally:
                os.environ.clear()
                os.environ.update(saved)

    def test_cli_skip_exit_and_no_prompt_file(self) -> None:
        env = os.environ.copy()
        env.pop("PFY_CLOUD_YES", None)
        env.pop("PFY_CLOUD_MAX_USD", None)
        proc = subprocess.run(
            [
                sys.executable, "-m", "pfylib.cloud_cost_gate",
                "--prompt", "price this parked lane prompt",
                "--isatty", "no",
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(proc.returncode, SKIP_EXIT, proc.stderr)
        self.assertIn("cost estimate:", proc.stderr)
        self.assertIn("$0 spend", proc.stderr)
        self.assertIn("No model was called", proc.stderr)


class EvalLaneSkipTests(unittest.TestCase):
    def test_unattended_eval_lane_skips_and_does_not_invoke_grok(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            from tests.test_eval_lane import card
            clone, _bare = make_fixture(td, {"widget": card("widget")})
            log = td / "grok.args"
            grok = td / "bin" / "grok"
            write_grok(grok, "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$GROK_LOG\"\nexit 0\n")
            env = lane_env(td, grok, approve=False)
            env["GROK_LOG"] = str(log)
            # The fixture grok writes to GROK_LOG only if the script uses it.
            # Overwrite with an explicit logger:
            write_grok(
                grok,
                "#!/bin/sh\nprintf 'invoked\\n' >> \"%s\"\nexit 0\n" % log,
            )
            state = td / "evalstate"
            proc = subprocess.run(
                ["bash", str(EVAL_SCRIPT), "--root", str(clone), "--state", str(state), "--slug", "widget", "--date", "1108"],
                cwd=clone,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            text = proc.stdout + proc.stderr
            self.assertNotEqual(proc.returncode, 0, text)
            parked = (state / "widget.parked").read_text(encoding="utf-8")
            self.assertIn("cloud cost gate skipped", parked)
            self.assertIn("$0 spend", parked)
            self.assertIn("cost estimate:", text)
            self.assertFalse(log.exists() and "invoked" in log.read_text())

    def test_opt_in_eval_lane_invokes_fake_grok(self) -> None:
        from tests.test_eval_lane import card
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            clone, _bare = make_fixture(td, {"widget": card("widget")})
            log = td / "grok.args"
            grok = td / "bin" / "grok"
            write_grok(
                grok,
                "#!/bin/sh\n"
                "printf 'invoked\\n' >> \"%s\"\n"
                "exit 0\n" % log,
            )
            env = lane_env(td, grok, approve=True)
            _install_dummy_cloud_keys(env)
            state = td / "evalstate"
            proc = subprocess.run(
                ["bash", str(EVAL_SCRIPT), "--root", str(clone), "--state", str(state), "--slug", "widget", "--date", "1108"],
                cwd=clone,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            text = proc.stdout + proc.stderr
            self.assertIn("cost estimate:", text)
            self.assertTrue(log.exists(), text)
            self.assertIn("invoked", log.read_text())


class AttendedApproveInvokesGrok(unittest.TestCase):
    def test_call_grok_shows_estimate_then_invokes_once(self) -> None:
        grill = _load_grill()
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            log = td / "calls"
            fake = td / "fake-grok"
            fake.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "open(os.environ['GROK_LOG'], 'a').write('invoked\\n')\n"
                "print(json.dumps({"
                "'text': json.dumps({'questions': []}),"
                "'num_turns': 1, 'total_cost_usd': 0,"
                "'stopReason': 'end_turn', 'modelUsage': {'x': {}}"
                "}))\n",
                encoding="utf-8",
            )
            fake.chmod(0o755)
            env = os.environ.copy()
            env["PFY_GROK_BIN"] = str(fake)
            env["GROK_LOG"] = str(log)
            env.pop("PFY_CLOUD_YES", None)
            env.pop("PFY_CLOUD_MAX_USD", None)
            _install_dummy_cloud_keys(env)
            saved = dict(os.environ)
            os.environ.clear()
            os.environ.update(env)
            try:
                buf = io.StringIO()
                with redirect_stderr(buf):
                    grill.call_grok(
                        2,
                        "ask the ticket questions now",
                        {"type": "object"},
                        yes=False,
                        max_usd=None,
                        isatty=True,
                        answer="y",
                    )
                err = buf.getvalue()
                self.assertIn("cost estimate:", err)
                # estimate appears before any invocation: the log is written
                # by grok, which starts only after the gate prints.
                self.assertEqual(log.read_text().count("invoked"), 1, err)
            finally:
                os.environ.clear()
                os.environ.update(saved)


if __name__ == "__main__":
    unittest.main()
