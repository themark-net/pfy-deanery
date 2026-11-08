#!/usr/bin/env python3
"""Build one HNSW index and search it. No chat, no hosted model.

Called by probe.py with the cache venv. Stdlib plus leann.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path


def _rows(results, id_to_path: dict[str, str]) -> list[dict]:
    out = []
    for item in results or []:
        meta = getattr(item, "metadata", None) or {}
        if not isinstance(meta, dict):
            meta = {}
        ident = str(getattr(item, "id", "") or meta.get("id") or "")
        path = str(meta.get("path") or id_to_path.get(ident) or "")
        text = getattr(item, "text", "") or ""
        if not isinstance(text, str):
            text = str(text)
        score = getattr(item, "score", 0.0)
        try:
            score_n = float(score)
        except (TypeError, ValueError):
            score_n = 0.0
        out.append({"id": ident, "path": path, "text": text, "score": score_n})
    return out


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


_SIDECAR_SUFFIXES = (".sqlite", ".jsonl", ".idx", ".txt", ".json")


def _matrix_stored(files: list[dict], naive: int) -> bool:
    if naive <= 0:
        return False
    threshold = int(naive * 0.8)
    for item in files:
        name = str(item.get("name") or "")
        if name.endswith(_SIDECAR_SUFFIXES):
            continue
        if int(item.get("bytes") or 0) >= threshold:
            return True
    return False


def run(passages_path: Path, questions_path: Path, index_dir: Path, out_path: Path) -> int:
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ.setdefault("LEANN_EMBEDDING_DEVICE", "cpu")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    passages = []
    for line in passages_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            passages.append(json.loads(line))
    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    id_to_path = {str(p["id"]): p.get("path", "") for p in passages}
    raw_bytes = sum(len(str(p.get("text", "")).encode("utf-8")) for p in passages)
    index_dir.mkdir(parents=True, exist_ok=True)
    index_path = str(index_dir / "catalog.leann")
    try:
        from leann import LeannBuilder, LeannSearcher

        started = time.perf_counter()
        builder = LeannBuilder(
            backend_name="hnsw",
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
            embedding_mode="sentence-transformers",
            is_recompute=True,
            is_compact=True,
        )
        for passage in passages:
            builder.add_text(
                passage["text"],
                metadata={"id": passage["id"], "path": passage["path"]},
            )
        builder.build_index(index_path)
        build_s = round(time.perf_counter() - started, 4)
        dim = int(builder.dimensions or 0)
        produced = []
        for path in sorted(index_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.name == passages_path.name and path.resolve() == passages_path.resolve():
                continue
            # Harness files (cm-*.json, adapter.json) sit in this directory
            # after a rerun. Only the build products are the index.
            if not path.name.startswith("catalog"):
                continue
            produced.append(path)
        index_bytes = sum(path.stat().st_size for path in produced)
        files = [
            {"name": path.name, "bytes": path.stat().st_size}
            for path in produced
        ]
        naive = len(passages) * dim * 4 if dim else 0
        matrix = _matrix_stored(files, naive)
        # In-process server. A daemon inherits this process's pipes and the
        # parent probe then waits until the daemon TTL (default 900s).
        searcher = LeannSearcher(
            index_path,
            use_daemon=False,
            daemon_ttl_seconds=30,
        )
        scored = []
        search_s = 0.0
        try:
            for question in questions:
                t0 = time.perf_counter()
                vector = searcher.search(question["query"], top_k=5, vector_weight=1.0)
                keyword = searcher.search(question["query"], top_k=5, vector_weight=0.0)
                search_s += time.perf_counter() - t0
                scored.append(
                    {
                        "id": question["id"],
                        "vector": _rows(vector, id_to_path),
                        "bm25": _rows(keyword, id_to_path),
                    }
                )
        finally:
            try:
                searcher.cleanup()
            except Exception:
                pass
        payload = {
            "ok": True,
            "error": "",
            "passages": len(passages),
            "raw_bytes": raw_bytes,
            "index_bytes": index_bytes,
            "dim": dim,
            "naive_embedding_bytes": naive,
            "embedding_matrix_stored": matrix,
            "build_s": build_s,
            "search_s": round(search_s, 4),
            "files": files,
            "backend": "hnsw",
            "is_recompute": True,
            "is_compact": True,
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "questions": scored,
        }
        _write(out_path, payload)
        return 0
    except Exception as exc:  # noqa: BLE001 - one record for the harness, then stop
        err = traceback.format_exc(limit=8)
        _write(
            out_path,
            {
                "ok": False,
                "error": ("%s: %s" % (type(exc).__name__, exc))[:500],
                "trace": err[-1500:],
                "passages": len(passages),
                "raw_bytes": raw_bytes,
                "questions": [],
            },
        )
        return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--passages", required=True)
    parser.add_argument("--questions", required=True)
    parser.add_argument("--index-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    return run(Path(args.passages), Path(args.questions), Path(args.index_dir), Path(args.out))


if __name__ == "__main__":
    sys.exit(main())
