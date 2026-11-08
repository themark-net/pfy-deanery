#!/usr/bin/env python3
"""Drive the ngram-mod probe with stub binaries. No network and no model.

A missing server must skip. A server whose help lacks ngram-mod must not
be started. A server that exits before /health must skip and must not
record a decode speed.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "llama-cpp-ngram-mod" / "ngram_probe.py"

HELP_WITH_FLAG = textwrap.dedent(
    """\
    #!/bin/sh
    printf '%s\\n' "$@" >> "$STUB_LOG"
    if [ "$1" = "--help" ]; then
      echo "--spec-type ngram-mod"
      exit 0
    fi
    if [ "$1" = "--version" ]; then
      echo "version: test"
      exit 0
    fi
    echo "server down" >&2
    exit 1
    """
)

HELP_WITHOUT_FLAG = textwrap.dedent(
    """\
    #!/bin/sh
    printf '%s\\n' "$@" >> "$STUB_LOG"
    echo "speculative decoding is not in this build"
    exit 0
    """
)


class ProbeSkipTest(unittest.TestCase):
    def _run(self, script: str | None, server: Path | None) -> tuple[dict, Path]:
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            model = folder / "model.gguf"
            model.write_bytes(b"not a model")
            out = folder / "results.json"
            log = folder / "stub.log"
            cache = folder / "cache"
            env = os.environ.copy()
            env.update({
                "LLAMA_NGRAM_OUT": str(out),
                "LLAMA_NGRAM_MODEL": str(model),
                "LLAMA_NGRAM_CACHE": str(cache),
                "LLAMA_NGRAM_SKIP_OLLAMA": "1",
                "LLAMA_NGRAM_SKIP_WAIT": "1",
                "LLAMA_NGRAM_NO_GPU": "1",
                "LLAMA_NGRAM_HEALTH_S": "1",
                "LLAMA_NGRAM_START_TRIES": "2",
                "STUB_LOG": str(log),
            })
            if server is None:
                env["LLAMA_NGRAM_SERVER"] = str(folder / "missing-llama-server")
            else:
                server.write_text(script or "", encoding="utf-8")
                server.chmod(server.stat().st_mode | stat.S_IEXEC)
                env["LLAMA_NGRAM_SERVER"] = str(server)
            proc = subprocess.run(
                [sys.executable, str(PROBE), "live"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertTrue(out.is_file(), proc.stdout)
            payload = json.loads(out.read_text(encoding="utf-8"))
            # Copy the bits the assertions need before the temp dir goes away.
            payload["_stub_log"] = log.read_text(encoding="utf-8") if log.is_file() else ""
            return payload, folder

    def test_missing_server_skips(self) -> None:
        payload, _folder = self._run(None, None)
        self.assertEqual(payload["status"], "skipped")
        self.assertIn("missing", payload["reason"])
        self.assertNotIn("summary", payload)

    def test_flag_absent_does_not_start_server(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server = Path(tmp) / "llama-server"
            # _run creates its own temp dir; pass the script text and a path
            # that _run will rewrite inside that dir.
            payload, _folder = self._run(HELP_WITHOUT_FLAG, server)
        self.assertEqual(payload["status"], "skipped")
        self.assertIn("ngram-mod", payload["reason"])
        self.assertNotIn("--model", payload["_stub_log"])
        self.assertNotIn("summary", payload)

    def test_server_down_skips_without_a_speed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server = Path(tmp) / "llama-server"
            payload, _folder = self._run(HELP_WITH_FLAG, server)
        self.assertEqual(payload["status"], "skipped")
        self.assertIn("healthy", payload["reason"])
        self.assertIn("--model", payload["_stub_log"])
        summary = payload.get("summary") or {}
        self.assertIsNone(summary.get("ratio_on_over_off"))
        self.assertIsNone(summary.get("on_median_tok_s"))


if __name__ == "__main__":
    unittest.main()
