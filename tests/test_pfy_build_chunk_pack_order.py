import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TestChunkPackOrder(unittest.TestCase):
    def test_sorted_greedy_pack(self):
        from pfylib.review_chunks import pack_review_prompts

        files = [
            {"path": "b.py", "text": "b" * 40},
            {"path": "c.py", "text": "c" * 40},
            {"path": "a.py", "text": "a" * 40},
        ]
        packs = pack_review_prompts(files, cap=100)
        self.assertEqual(
            [[item["path"] for item in pack] for pack in packs],
            [["a.py", "b.py"], ["c.py"]],
        )

    def test_oversize_file_splits_without_dropping_text(self):
        from pfylib.review_chunks import pack_review_prompts

        text = "\n".join(f"L{i}" for i in range(10))
        packs = pack_review_prompts([{"path": "big.py", "text": text}], cap=20)
        parts = [item for pack in packs for item in pack]
        self.assertGreater(len(parts), 1)
        self.assertEqual("".join(item["text"] for item in parts), text)
        self.assertEqual([item["path"] for item in parts], ["big.py"] * len(parts))
        self.assertEqual([item["part"] for item in parts], list(range(1, len(parts) + 1)))
        self.assertTrue(all(item["parts"] == len(parts) for item in parts))
