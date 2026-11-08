import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LoopLatestGitignoreTest(unittest.TestCase):
    def test_status_snapshot_path_is_gitignored(self):
        text = (ROOT / ".gitignore").read_text()
        self.assertIn("pipelines/catalog/loop.latest.json", text)
