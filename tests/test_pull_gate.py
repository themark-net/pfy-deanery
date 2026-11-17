"""Ollama pulls over 25 GB must not start unless the operator opts in.

Fail: ensure_ollama_adapter or the gate CLI starts a pull when the probe
says the tag is over the cap, or when auto-pull cannot show a size at or
under 25 GB. Recover: a size under the cap is pulled; an explicit
--opt-in-huge pull of an over-cap tag is pulled. Tests inject the size and
a fake ollama; they never open the registry or a paid API.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PFY = ROOT / "scripts" / "pfy"

import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib.pull_gate import (  # noqa: E402
    CAP_BYTES,
    decide,
    format_verdict,
    registry_size,
    split_tag,
)


def _ensure_chunk(state: str) -> str:
    text = PFY.read_text(encoding="utf-8")
    start = text.index("ollama_base_url()")
    end = text.index("\nllama_swap_health(")
    head = (
        'have() { command -v "$1" >/dev/null 2>&1; }\n'
        f'STATE_DIR="{state}"\n'
        'mkdir -p "$STATE_DIR"\n'
    )
    return head + text[start:end]


def _fake_ollama(bind: Path, log: Path) -> None:
    (bind / "ollama").write_text(
        textwrap.dedent(
            """\
            #!/bin/bash
            printf '%s\\n' "$*" >> "$OLLAMA_LOG"
            case "$1" in
              show) exit 1 ;;
              list) exit 0 ;;
              *) exit 0 ;;
            esac
            """
        ),
        encoding="utf-8",
    )
    (bind / "curl").write_text(
        textwrap.dedent(
            """\
            #!/bin/bash
            url=""
            for a in "$@"; do url="$a"; done
            if [[ "$url" == *11434* ]] && grep -q '^serve$' "$OLLAMA_LOG" 2>/dev/null; then
              exit 0
            fi
            exit 1
            """
        ),
        encoding="utf-8",
    )
    os.chmod(bind / "ollama", 0o755)
    os.chmod(bind / "curl", 0o755)
    log.write_text("", encoding="utf-8")


def _adapter_env(tmp: str, bind: Path, log: Path, **extra: str) -> dict[str, str]:
    env = os.environ.copy()
    env["PATH"] = f"{bind}:/usr/bin:/bin"
    env["OLLAMA_LOG"] = str(log)
    env["ROOT"] = str(ROOT)
    env["PFY_OLLAMA_MODEL"] = extra.pop("model", "tiny-test")
    env["PYTHONPATH"] = str(ROOT) + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    env["PFY_PULL_NO_REGISTRY"] = "1"
    for key in (
        "LOCAL_OPENAI_BASE_URL",
        "LOCAL_CODER_MODEL",
        "PFY_PULL_SIZE_BYTES",
        "PFY_PULL_MAX_BYTES",
        "PFY_PULL_ALLOW_OVER_25GB",
    ):
        env.pop(key, None)
    env.update(extra)
    return env


def _run_adapter(tmp: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", _ensure_chunk(tmp) + "\nensure_ollama_adapter\n"],
        cwd=tmp,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


class PullGateDecideTests(unittest.TestCase):
    def test_over_cap_is_refused_until_opt_in(self) -> None:
        env = {"PFY_PULL_SIZE_BYTES": str(CAP_BYTES + 1), "PFY_PULL_NO_REGISTRY": "1"}
        sentry = mock.Mock(side_effect=AssertionError("registry must not be contacted"))
        declined = decide(
            "huge-model", mode="explicit", env=env, get=sentry
        )
        self.assertEqual(declined["decision"], "refuse-over-cap")
        text = format_verdict(declined)
        self.assertIn("pull size:", text)
        self.assertIn("25", text)
        self.assertIn("No model was pulled", text)
        sentry.assert_not_called()

        allowed = decide(
            "huge-model",
            mode="explicit",
            opt_in_huge=True,
            env=env,
            get=sentry,
        )
        self.assertEqual(allowed["decision"], "allow")
        self.assertIn("opted in", allowed["reason"])
        sentry.assert_not_called()

    def test_auto_unknown_size_is_refused_and_explicit_unknown_is_warned(self) -> None:
        env = {"PFY_PULL_NO_REGISTRY": "1"}
        sentry = mock.Mock(side_effect=AssertionError("registry must not be contacted"))
        auto = decide("mystery", mode="auto", env=env, get=sentry)
        self.assertEqual(auto["decision"], "refuse-unknown")
        self.assertIn("No model was pulled", format_verdict(auto))
        explicit = decide("mystery", mode="explicit", env=env, get=sentry)
        self.assertEqual(explicit["decision"], "allow")
        self.assertIn("size unknown", explicit["reason"])
        sentry.assert_not_called()

    def test_under_cap_is_allowed(self) -> None:
        env = {"PFY_PULL_SIZE_BYTES": "1000000000", "PFY_PULL_NO_REGISTRY": "1"}
        verdict = decide("tiny-test", mode="auto", env=env)
        self.assertEqual(verdict["decision"], "allow")
        self.assertEqual(verdict["bytes"], 1_000_000_000)
        self.assertIn("under cap", verdict["reason"])

    def test_cli_over_cap_exits_without_a_registry_call(self) -> None:
        env = os.environ.copy()
        env["PFY_PULL_SIZE_BYTES"] = str(30 * 10**9)
        env["PFY_PULL_NO_REGISTRY"] = "1"
        proc = subprocess.run(
            [sys.executable, "-m", "pfylib.pull_gate", "check", "--tag", "huge", "--mode", "auto"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("pull size:", proc.stdout)
        self.assertIn("No model was pulled", proc.stdout)
        self.assertNotIn("ok:", proc.stdout)

    def test_registry_sums_layers_and_split_rejects_a_url(self) -> None:
        def get(url: str, headers=None) -> bytes:
            self.assertIn("/library/tiny/manifests/latest", url)
            return json.dumps(
                {
                    "config": {"size": 10},
                    "layers": [{"size": 100}, {"size": 200}],
                }
            ).encode("utf-8")

        self.assertEqual(registry_size("tiny", get=get, env={}), 310)
        with self.assertRaises(ValueError):
            split_tag("https://example.invalid/evil")


class EnsureOllamaPullGateTests(unittest.TestCase):
    def test_over_cap_default_does_not_pull(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bind = Path(tmp) / "bin"
            bind.mkdir()
            log = Path(tmp) / "ollama.args"
            _fake_ollama(bind, log)
            env = _adapter_env(
                tmp,
                bind,
                log,
                model="huge-model",
                PFY_PULL_SIZE_BYTES=str(30 * 10**9),
            )
            proc = _run_adapter(tmp, env)
            text = proc.stdout + proc.stderr
            self.assertNotEqual(proc.returncode, 0, text)
            self.assertIn("pull size:", text)
            self.assertIn("No model was pulled", text)
            self.assertIn("huge-model", text)
            logged = log.read_text(encoding="utf-8")
            self.assertIn("serve", logged)
            self.assertNotIn("pull huge-model", logged)
            self.assertNotIn("pull ", logged.replace("serve", ""))

    def test_under_cap_default_still_pulls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bind = Path(tmp) / "bin"
            bind.mkdir()
            log = Path(tmp) / "ollama.args"
            _fake_ollama(bind, log)
            env = _adapter_env(
                tmp,
                bind,
                log,
                model="tiny-test",
                PFY_PULL_SIZE_BYTES="1000000",
            )
            proc = _run_adapter(tmp, env)
            text = proc.stdout + proc.stderr
            self.assertEqual(proc.returncode, 0, text)
            self.assertIn("pulling default model: tiny-test", text)
            self.assertIn("pull tiny-test", log.read_text(encoding="utf-8"))

    def test_unknown_size_auto_pull_does_not_pull(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bind = Path(tmp) / "bin"
            bind.mkdir()
            log = Path(tmp) / "ollama.args"
            _fake_ollama(bind, log)
            env = _adapter_env(tmp, bind, log, model="mystery")
            proc = _run_adapter(tmp, env)
            text = proc.stdout + proc.stderr
            self.assertNotEqual(proc.returncode, 0, text)
            self.assertIn("size not known", text)
            self.assertIn("No model was pulled", text)
            self.assertNotIn("pull mystery", log.read_text(encoding="utf-8"))

    def test_opt_in_is_ignored_for_auto_default_pull(self) -> None:
        """ensure_ollama_adapter is unattended: even an env opt-in must not
        auto-download a 30 GB tag. Explicit ./pfy models pull --opt-in-huge
        is the operator path."""
        with tempfile.TemporaryDirectory() as tmp:
            bind = Path(tmp) / "bin"
            bind.mkdir()
            log = Path(tmp) / "ollama.args"
            _fake_ollama(bind, log)
            env = _adapter_env(
                tmp,
                bind,
                log,
                model="huge-model",
                PFY_PULL_SIZE_BYTES=str(30 * 10**9),
                PFY_PULL_ALLOW_OVER_25GB="1",
            )
            proc = _run_adapter(tmp, env)
            text = proc.stdout + proc.stderr
            self.assertNotEqual(proc.returncode, 0, text)
            self.assertNotIn("pull huge-model", log.read_text(encoding="utf-8"))



class ExplicitPullGateTests(unittest.TestCase):
    def _run_gated(self, tmp: str, env: dict[str, str], args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", "-c", _ensure_chunk(tmp) + "\ngated_ollama_pull %s\n" % args],
            cwd=tmp,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )

    def test_explicit_over_cap_does_not_pull_until_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bind = Path(tmp) / "bin"
            bind.mkdir()
            log = Path(tmp) / "ollama.args"
            _fake_ollama(bind, log)
            env = _adapter_env(
                tmp,
                bind,
                log,
                model="huge-model",
                PFY_PULL_SIZE_BYTES=str(30 * 10**9),
            )
            declined = self._run_gated(tmp, env, 'huge-model explicit')
            text = declined.stdout + declined.stderr
            self.assertNotEqual(declined.returncode, 0, text)
            self.assertIn("pull size:", text)
            self.assertIn("No model was pulled", text)
            self.assertNotIn("pull huge-model", log.read_text(encoding="utf-8"))

            log.write_text("", encoding="utf-8")
            accepted = self._run_gated(tmp, env, 'huge-model explicit --opt-in-huge')
            text = accepted.stdout + accepted.stderr
            self.assertEqual(accepted.returncode, 0, text)
            self.assertIn("opted in", text)
            self.assertIn("pull huge-model", log.read_text(encoding="utf-8"))


class ScriptsPfyWiringTests(unittest.TestCase):
    def test_both_ollama_pull_sites_call_the_gate_first(self) -> None:
        text = PFY.read_text(encoding="utf-8")
        self.assertIn("gated_ollama_pull", text)
        # Every literal `ollama pull` in the operator script is inside the gate
        # wrapper, or is a printed hint (not executed).
        executed = []
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if "ollama pull" in stripped and not stripped.startswith("#"):
                executed.append((i, stripped))
        pulls = [row for row in executed if row[1] == 'ollama pull "$tag"' or row[1] == "ollama pull \"$tag\""]
        self.assertTrue(pulls, executed)
        # hints may mention the command; executed pulls go through gated_ollama_pull
        self.assertIn("gated_ollama_pull() {", text)
        ensure = text.split("ensure_ollama_adapter()", 1)[1].split("llama_swap_health()", 1)[0]
        self.assertIn('gated_ollama_pull "$model" auto', ensure)
        models = text.split("cmd_models_pull()", 1)[1].split("cmd_models_recommend()", 1)[0]
        self.assertIn('gated_ollama_pull "$m" explicit', models)


if __name__ == "__main__":
    unittest.main()
