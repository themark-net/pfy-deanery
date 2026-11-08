import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "catalog_counts.py"


def card(tool_id, stage, intent):
    return {
        "id": tool_id,
        "stage": stage,
        "intent": intent,
        "uses": [],
        "features": [],
        "tags": [],
    }


class IdempotentCountsTest(unittest.TestCase):
    def test_second_run_matches_bytes_and_does_not_rewrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cards = tmp / "stages"
            cards.mkdir()
            (cards / "alpha.json").write_text(json.dumps(card("alpha", "I2", "inspect")))
            (cards / "beta.json").write_text(json.dumps(card("beta", "I1", "generate")))
            registry = cards / "_registry.json"
            registry.write_text(json.dumps({
                "version": 1,
                "policy": "keep",
                "default_stage": "I0",
                "probe_path": "x",
                "handoff": "y",
                "coverage": "0 tools registered",
            }))
            dashboard = tmp / "dashboard.latest.md"
            progress = tmp / "counts.latest.json"

            def run():
                return subprocess.run(
                    [
                        "python3", str(SCRIPT),
                        "--cards", str(cards),
                        "--registry", str(registry),
                        "--dashboard", str(dashboard),
                        "--progress", str(progress),
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                )

            first = run()
            self.assertEqual(first.returncode, 0, first.stderr)
            before = {
                registry: registry.read_bytes(),
                dashboard: dashboard.read_bytes(),
                progress: progress.read_bytes(),
            }
            mtimes = {path: path.stat().st_mtime_ns for path in before}
            reg = json.loads(registry.read_text())
            self.assertEqual(reg["coverage"], "2 tools registered")
            self.assertEqual(reg["policy"], "keep")
            self.assertEqual(reg["version"], 1)
            second = run()
            self.assertEqual(second.returncode, 0, second.stderr)
            for path, payload in before.items():
                self.assertEqual(path.read_bytes(), payload)
                self.assertEqual(path.stat().st_mtime_ns, mtimes[path])


if __name__ == "__main__":
    unittest.main()
