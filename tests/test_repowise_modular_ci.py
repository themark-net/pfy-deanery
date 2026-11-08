import unittest
from pathlib import Path


class TestRepowiseModularCi(unittest.TestCase):
    def test_no_new_ci_job_or_model_lock(self):
        script = Path("eval/integrate/repowise/run-on-main.sh").read_text()
        self.assertNotIn("model_lock.sh", script)
        self.assertNotIn("auth.json", script)
        self.assertNotIn("config.toml", script)
        self.assertNotIn("systemctl", script)
        self.assertNotIn("ollama", script.lower())
        roots = [Path(".github/workflows"), Path("ci")]
        hits = []
        for root in roots:
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if path.is_file() and "repowise" in path.name:
                    hits.append(str(path))
        self.assertEqual(hits, [])
