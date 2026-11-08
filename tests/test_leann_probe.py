"""LEANN probe: oversized index, vector miss, and a dead adapter.

The child is eval/evq1107/leann/probe.py. Each test runs that script
against a stub searcher in a temp dir. No network, no model, no real binary.
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
PROBE = ROOT / "eval" / "evq1107" / "leann" / "probe.py"

QUESTIONS = [
    {
        "id": "p1",
        "kind": "prose",
        "query": "where is the primary graph documented",
        "expect_path": "docs/ops/memory-assist-patterns.md",
        "expect_substr": "CM remains primary",
    },
    {
        "id": "c1",
        "kind": "code",
        "query": "select tests from a diff",
        "expect_path": "scripts/test_select.py",
        "expect_substr": "def select(",
    },
]

PASSAGES = [
    {
        "id": "p0000",
        "path": "docs/ops/memory-assist-patterns.md",
        "text": "CM remains primary. Extreme index compression can wait.",
    },
    {
        "id": "p0001",
        "path": "scripts/test_select.py",
        "text": "def select(root, changes):\n    return changes",
    },
]

STUB = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import json, os, sys
    args = sys.argv[1:]

    def flag(name):
        return args[args.index(name) + 1]

    mode = os.environ.get("STUB_MODE", "miss")
    if mode == "crash":
        sys.stderr.write("hnsw backend failed to open\\n")
        raise SystemExit(2)
    passages = []
    for line in open(flag("--passages"), encoding="utf-8"):
        if line.strip():
            passages.append(json.loads(line))
    questions = json.loads(open(flag("--questions"), encoding="utf-8").read())
    raw = sum(len(str(p.get("text", "")).encode("utf-8")) for p in passages)
    scored = []
    for question in questions:
        right = [{"id": "hit", "path": question["expect_path"], "text": question["expect_substr"], "score": 1.0}]
        wrong = [{"id": "miss", "path": "other.txt", "text": "unrelated", "score": 0.2}]
        if mode == "big":
            vector, bm25 = wrong, right
        elif mode == "miss":
            vector, bm25 = wrong, right
        else:
            vector, bm25 = right, right
        scored.append({"id": question["id"], "vector": vector, "bm25": bm25})
    index_bytes = raw + 5000 if mode == "big" else max(1, raw // 2)
    naive = len(passages) * 8 * 4
    if mode == "big":
        # SQLite is larger than a float32 matrix. The adapter calls that a
        # stored matrix. The probe must not.
        files = [
            {"name": "catalog.index", "bytes": 10},
            {"name": "catalog.leann.bm25.sqlite", "bytes": naive * 3},
            {"name": "catalog.leann.passages.jsonl", "bytes": raw},
            {"name": "catalog.leann.meta.json", "bytes": 80},
        ]
        matrix = True
    else:
        files = [{"name": "catalog.index", "bytes": index_bytes}]
        matrix = False
    doc = {
        "ok": True,
        "passages": len(passages),
        "raw_bytes": raw,
        "index_bytes": index_bytes,
        "dim": 8,
        "naive_embedding_bytes": naive,
        "embedding_matrix_stored": matrix,
        "build_s": 0.01,
        "search_s": 0.01,
        "files": files,
        "backend": "hnsw",
        "embedding_model": "stub",
        "questions": scored,
    }
    open(flag("--out"), "w", encoding="utf-8").write(json.dumps(doc))
    """
)


class LeannProbeTests(unittest.TestCase):
    def _run(self, mode: str, home: Path) -> dict:
        stub = home / "stub-leann.py"
        stub.write_text(STUB, encoding="utf-8")
        stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
        passages = home / "passages.jsonl"
        lines = [json.dumps(row) for row in PASSAGES]
        passages.write_text("\n".join(lines) + "\n", encoding="utf-8")
        questions = home / "questions.json"
        questions.write_text(json.dumps(QUESTIONS), encoding="utf-8")
        out = home / "out.json"
        env = os.environ.copy()
        env["HOME"] = str(home)
        env["LEANN_RUN"] = str(stub)
        env["LEANN_SKIP_CM"] = "1"
        env["STUB_MODE"] = mode
        env["PATH"] = "/usr/bin:/bin"
        proc = subprocess.run(
            [
                sys.executable,
                str(PROBE),
                "--root",
                str(home),
                "--passages",
                str(passages),
                "--questions",
                str(questions),
                "--out",
                str(out),
                "--index-dir",
                str(home / "index"),
            ],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertTrue(out.is_file(), proc.stdout)
        return json.loads(out.read_text(encoding="utf-8"))

    def test_oversized_index_is_not_a_compression_win_and_bm25_recovers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="leann-big-") as tmp:
            doc = self._run("big", Path(tmp))
        self.assertEqual(doc["status"], "ok")
        self.assertTrue(doc["measured"])
        self.assertFalse(doc["compression_beats_raw"])
        self.assertFalse(doc["embedding_matrix_stored"])
        self.assertGreater(doc["index_bytes"], doc["raw_bytes"])
        prose = next(row for row in doc["questions"] if row["id"] == "p1")
        self.assertFalse(prose["vector_hit"])
        self.assertTrue(prose["bm25_hit"])
        self.assertTrue(prose["recovered_by_bm25"])
        self.assertTrue(prose["bm25_passage_hit"])
        self.assertFalse(prose["vector_passage_hit"])
        self.assertGreaterEqual(doc["summary"]["recovered_by_bm25"], 1)

    def test_vector_miss_stays_a_miss_when_the_index_is_smaller(self) -> None:
        with tempfile.TemporaryDirectory(prefix="leann-miss-") as tmp:
            doc = self._run("miss", Path(tmp))
        self.assertEqual(doc["status"], "ok")
        self.assertTrue(doc["compression_beats_raw"])
        self.assertLess(doc["index_bytes"], doc["raw_bytes"])
        code = next(row for row in doc["questions"] if row["id"] == "c1")
        self.assertFalse(code["vector_hit"])
        self.assertTrue(code["bm25_hit"])
        self.assertTrue(code["recovered_by_bm25"])
        self.assertIsNone(code["cm_hit"])
        self.assertEqual(doc["summary"]["code_vector_hit"]["hits"], 0)
        self.assertEqual(doc["summary"]["code_bm25_hit"]["hits"], 1)

    def test_dead_adapter_is_skipped_and_not_counted_as_a_hit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="leann-crash-") as tmp:
            doc = self._run("crash", Path(tmp))
        self.assertEqual(doc["status"], "skipped")
        self.assertFalse(doc["measured"])
        self.assertIn("hnsw", doc["skip_reason"])
        self.assertIsNone(doc["compression_beats_raw"])
        for row in doc["questions"]:
            self.assertIsNone(row["vector_hit"])
            self.assertIsNone(row["bm25_hit"])
            self.assertIsNone(row["cm_hit"])
            self.assertIsNone(row["cm_graph_top"])
            self.assertIsNone(row["cm_grep_top"])
        self.assertEqual(doc["summary"]["prose_vector_hit"]["n"], 0)
        self.assertEqual(doc["summary"]["code_vector_hit"]["hits"], 0)


if __name__ == "__main__":
    unittest.main()
