"""Shimmy is the last engine ./pfy up will start (ADR-0014)."""
from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PFY = ROOT / "scripts" / "pfy"


def _chunk(state: str) -> str:
    text = PFY.read_text(encoding="utf-8")
    start = text.index("shimmy_health()")
    end = text.index("\nprint_live_models(")
    head = (
        'have() { command -v "$1" >/dev/null 2>&1; }\n'
        f'STATE_DIR="{state}"\n'
        'mkdir -p "$STATE_DIR"\n'
    )
    return head + text[start:end]


class ShimmyEnsureTests(unittest.TestCase):
    def test_cold_start_tries_shimmy_after_ollama(self):
        text = PFY.read_text(encoding="utf-8")
        cold = text.split("Cold start", 1)[1].split("rt=$(local_runtime)", 1)[0]
        self.assertLess(cold.index("ensure_ollama_adapter"), cold.index("ensure_shimmy"))
        self.assertIn("shimmy) ensure_shimmy", text)

    def test_missing_binary_is_stub(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PATH"] = "/usr/bin:/bin"
            env["PFY_STATE_DIR"] = tmp
            env.pop("LOCAL_OPENAI_BASE_URL", None)
            proc = subprocess.run(
                ["bash", "-c", _chunk(tmp) + "\nensure_shimmy\n"],
                cwd=tmp,
                env=env,
                capture_output=True,
                text=True,
            )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("STUB: shimmy not on PATH", proc.stdout)
        self.assertIn("shimmy serve --bind 127.0.0.1:11435", proc.stdout)

    def test_starts_bound_to_11435_then_healthy(self):
        with tempfile.TemporaryDirectory() as tmp:
            bind = Path(tmp) / "bin"
            bind.mkdir()
            log = Path(tmp) / "shimmy.args"
            (bind / "shimmy").write_text(
                textwrap.dedent(
                    """\
                    #!/bin/bash
                    printf '%s\\n' "$*" >> "$SHIMMY_LOG"
                    exit 0
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
                    if [[ "$url" == *11435* ]] && grep -q 'serve --bind 127.0.0.1:11435' "$SHIMMY_LOG" 2>/dev/null; then
                      exit 0
                    fi
                    exit 1
                    """
                ),
                encoding="utf-8",
            )
            os.chmod(bind / "shimmy", 0o755)
            os.chmod(bind / "curl", 0o755)
            env = os.environ.copy()
            env["PATH"] = f"{bind}:/usr/bin:/bin"
            env["PFY_STATE_DIR"] = tmp
            env["SHIMMY_LOG"] = str(log)
            env.pop("LOCAL_OPENAI_BASE_URL", None)
            proc = subprocess.run(
                ["bash", "-c", _chunk(tmp) + "\nensure_shimmy\n"],
                cwd=tmp,
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("shimmy API healthy", proc.stdout)
            self.assertIn("serve --bind 127.0.0.1:11435", log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
