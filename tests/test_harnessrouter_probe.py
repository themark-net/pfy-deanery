"""HarnessRouter wiring probe: a fixture tree returns counts, a broken tree does not.

The child is the eval probe. The fixture is the only tree it reads. No network,
no docker, no model, no cache checkout.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "harnessrouter" / "probe.py"


def _tree(root: Path) -> None:
    gateway = root / "gateway"
    runner = root / "runner"
    docker = root / "docker"
    gateway.mkdir(parents=True)
    runner.mkdir(parents=True)
    docker.mkdir(parents=True)
    (gateway / "app.py").write_text(
        "_INTEGRATION_WIRING: dict[tuple[str, str], str] = {\n"
        '    ("custom", "hermes"): "openai-api",\n'
        '    ("custom", "codex"): "tokenrouter",\n'
        '    ("custom", "gemini"): "google",\n'
        '    ("openai", "hermes"): "openai-api",\n'
        "}\n",
        encoding="utf-8",
    )
    (runner / "server.py").write_text(
        'HERMES_PROVIDERS = {"anthropic", "openai-api"}\n'
        "CODEX_PROVIDERS = {\n"
        '    "openai": {"name": "OpenAI"},\n'
        '    "tokenrouter": {"name": "TokenRouter"},\n'
        "}\n"
        'GEMINI_PROVIDERS = {"google"}\n'
        "QODER_PROVIDERS = set(GEMINI_PROVIDERS)\n",
        encoding="utf-8",
    )
    (docker / "entrypoint.sh").write_text(
        'export HR_BACKENDS="${HR_BACKENDS:-hermes,codex,gemini,qoder}"\n',
        encoding="utf-8",
    )


class ProbeTest(unittest.TestCase):
    def test_fixture_counts_and_a_missing_tree_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-hr-probe-") as tmp:
            root = Path(tmp)
            src = root / "src"
            out = root / "out" / "results.json"
            _tree(src)
            proc = subprocess.run(
                [sys.executable, str(PROBE), "--src", str(src), "--out", str(out)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            doc = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(doc["default_backend_count"], 4)
            self.assertEqual(doc["local_base_url_backends"], ["hermes", "codex"])
            self.assertEqual(doc["local_base_url_count"], 2)
            self.assertEqual(doc["custom_missing"], ["qoder"])
            self.assertEqual(doc["custom_by_target"]["google"], ["gemini"])
            self.assertEqual(doc["openai_api_provider_backends"], ["hermes"])
            self.assertEqual(doc["weight_file_count"], 0)
            self.assertEqual(doc["engines_added"], 0)

            broken = root / "broken.json"
            (src / "gateway" / "app.py").unlink()
            fail = subprocess.run(
                [sys.executable, str(PROBE), "--src", str(src), "--out", str(broken)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(fail.returncode, 2, fail.stderr)
            self.assertFalse(broken.exists())
            self.assertIn("probe failed", fail.stderr)


if __name__ == "__main__":
    unittest.main()
