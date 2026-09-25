"""Named ./pfy start ollama is health + default model (T-0101)."""
from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PFY = ROOT / "scripts" / "pfy"


def _ensure_chunk(state: str) -> str:
    text = PFY.read_text(encoding="utf-8")
    start = text.index("ollama_health()")
    end = text.index("\nllama_swap_health(")
    head = (
        'have() { command -v "$1" >/dev/null 2>&1; }\n'
        f'STATE_DIR="{state}"\n'
        'mkdir -p "$STATE_DIR"\n'
    )
    return head + text[start:end]


class OllamaAdapterTests(unittest.TestCase):
    def test_named_start_calls_ensure_before_exec(self):
        text = PFY.read_text(encoding="utf-8")
        arm = text.split("attach_operator_harness()", 1)[1].split("attach_operator_harness()", 1)[0]
        # The function body runs until the next top-level def-like cmd. Take the case arm.
        case = arm.split("ollama)", 1)[1].split("freetoken|shimmy", 1)[0]
        self.assertIn("ensure_ollama_adapter", case)
        self.assertLess(case.index("ensure_ollama_adapter"), case.index("exec_harness ollama"))
        spine = text.split("    ollama)\n", 1)[1].split("freetoken|shimmy", 1)[0]
        self.assertIn("ollama_health", spine)
        self.assertIn("http://127.0.0.1:11434/v1", spine)

    def test_missing_binary_is_stub(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env["PATH"] = "/bin"
            env.pop("LOCAL_OPENAI_BASE_URL", None)
            proc = subprocess.run(
                ["bash", "-c", _ensure_chunk(tmp) + "\nensure_ollama_adapter\n"],
                cwd=tmp,
                env=env,
                capture_output=True,
                text=True,
            )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("STUB: ollama not on PATH", proc.stdout)
        self.assertIn("ollama serve", proc.stdout)

    def test_starts_then_pulls_default_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            bind = Path(tmp) / "bin"
            bind.mkdir()
            log = Path(tmp) / "ollama.args"
            (bind / "ollama").write_text(
                textwrap.dedent(
                    """\
                    #!/bin/bash
                    printf '%s\\n' "$*" >> "$OLLAMA_LOG"
                    case "$1" in
                      show) exit 1 ;;
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
            env = os.environ.copy()
            env["PATH"] = f"{bind}:/bin"
            env["OLLAMA_LOG"] = str(log)
            env["PFY_OLLAMA_MODEL"] = "tiny-test"
            env.pop("LOCAL_OPENAI_BASE_URL", None)
            env.pop("LOCAL_CODER_MODEL", None)
            proc = subprocess.run(
                ["bash", "-c", _ensure_chunk(tmp) + "\nensure_ollama_adapter\n"],
                cwd=tmp,
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("ollama API healthy", proc.stdout)
            self.assertIn("pulling default model: tiny-test", proc.stdout)
            logged = log.read_text(encoding="utf-8")
            self.assertIn("serve", logged)
            self.assertIn("pull tiny-test", logged)


if __name__ == "__main__":
    unittest.main()
