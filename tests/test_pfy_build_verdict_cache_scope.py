import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TestVerdictCacheScope(unittest.TestCase):
    def test_disk_snapshot_does_not_reuse_and_memory_does(self):
        from pfylib.review_chunks import review_reuse_allowed

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "review-verdicts.json").write_text('{"a.py": "deadbeef"}')
            self.assertFalse(review_reuse_allowed(root, "a.py", "deadbeef", memory={}))
            memory = {("a.py", "deadbeef"): "accept"}
            self.assertTrue(review_reuse_allowed(root, "a.py", "deadbeef", memory=memory))
            self.assertFalse(review_reuse_allowed(root, "a.py", "other", memory=memory))
            self.assertFalse(review_reuse_allowed(root, "b.py", "deadbeef", memory=memory))
