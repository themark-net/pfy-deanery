"""Measurement helpers for the LEANN GPU index trial.

How this fails: the BM25 sidecar is larger than the float32 matrix and gets
counted as stored embeddings, or a search row loses its path. How we recover:
sidecar names are ignored, and a row keeps id, path, text, and a numeric score.
The child is eval/evals/leann/gpu_once.py. It does not start a model.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
ONCE = ROOT / "eval" / "evals" / "leann" / "gpu_once.py"


def _load():
    spec = importlib.util.spec_from_file_location("leann_gpu_once", ONCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("missing gpu_once.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LeannGpuOnceTest(unittest.TestCase):
    def test_sidecar_is_not_a_stored_matrix_and_a_row_keeps_its_path(self):
        mod = _load()
        naive = 1000
        files = [
            {"name": "catalog.leann.bm25.sqlite", "bytes": naive * 3},
            {"name": "catalog.leann.passages.jsonl", "bytes": naive * 2},
            {"name": "catalog.index", "bytes": 100},
        ]
        self.assertFalse(mod._matrix_stored(files, naive))
        self.assertFalse(mod._matrix_stored(files, 0))
        files.append({"name": "catalog.vectors.bin", "bytes": int(naive * 0.8)})
        self.assertTrue(mod._matrix_stored(files, naive))

        hit = SimpleNamespace(id="", metadata={"path": "docs/ops/integration-stages.md"}, text="3 of 4", score="0.41")
        broken = SimpleNamespace(id="p9", metadata={}, text=None, score="nope")
        rows = mod._rows([hit, broken], {"p9": "src/missed.py"})
        self.assertEqual(rows[0]["path"], "docs/ops/integration-stages.md")
        self.assertEqual(rows[0]["score"], 0.41)
        self.assertEqual(rows[1]["path"], "src/missed.py")
        self.assertEqual(rows[1]["text"], "")
        self.assertEqual(rows[1]["score"], 0.0)


if __name__ == "__main__":
    unittest.main()
