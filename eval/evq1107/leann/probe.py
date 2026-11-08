#!/usr/bin/env python3
"""Measure LEANN against BM25 on the same passages and against codebase-memory.

The leann binary is a subprocess (LEANN_RUN, or the cache venv). Tests pass a
stub. codebase-memory is also a subprocess. No network and no model in this file.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT_DEFAULT = Path(__file__).resolve().parents[3]
ADAPTER = Path(__file__).resolve().parent / "leann_once.py"
QUESTIONS_DEFAULT = Path(__file__).resolve().parent / "questions.json"
LEANN_PY_DEFAULT = "/home/mark/.cache/pfy/tools/leann/venv/bin/python"
CBM_CACHE_DEFAULT = "/home/mark/.cache/pfy/cbm-shadow/db"
CBM_PROJECT_DEFAULT = "pfy-mentat-cbm-shadow"

DOCS = (
    "docs/ops/memory-assist-patterns.md",
    "docs/ops/integration-stages.md",
    "docs/eval/TOOLSET-RANKING.md",
    "scripts/test_select.py",
    "scripts/catalog_check.py",
    "scripts/cbm_shadow.py",
)
OVERLAP_TOKENS = (
    "rag",
    "compression",
    "embedding",
    "embeddings",
    "vector",
    "memory",
    "code-memory",
    "code memory",
)
# A BM25 sqlite, the passage store, and meta files are not an embedding matrix.
_SIDECAR_SUFFIXES = (".sqlite", ".jsonl", ".idx", ".txt", ".json")


def matrix_from_files(files, naive) -> bool:
    """True only when a non-sidecar file is at least 80% of a float32 matrix."""
    try:
        naive_n = int(naive or 0)
    except (TypeError, ValueError):
        return False
    if naive_n <= 0:
        return False
    threshold = int(naive_n * 0.8)
    for item in files or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        if name.endswith(_SIDECAR_SUFFIXES):
            continue
        try:
            size = int(item.get("bytes") or 0)
        except (TypeError, ValueError):
            continue
        if size >= threshold:
            return True
    return False


def _chunk_text(text: str, kind: str) -> list[str]:
    body = text.strip()
    if not body:
        return []
    if kind == "md" and len(body) > 4000:
        parts = re.split(r"\n(?=## )", body)
    elif kind == "py":
        parts = re.split(r"\n(?=(?:def |class ))", body)
    else:
        parts = [body]
    out: list[str] = []
    for part in parts:
        part = part.strip()
        if len(part) < 40:
            continue
        while len(part) > 1800:
            out.append(part[:1800].strip())
            part = part[1600:].strip()
        if len(part) >= 40:
            out.append(part)
    return out


def _entry_052(text: str) -> str:
    start = text.find("### Entry 052:")
    if start < 0:
        return ""
    end = text.find("### Entry 053:", start)
    if end < 0:
        end = start + 2500
    return text[start:end].strip()


def build_passages(root: Path) -> list[dict]:
    passages: list[dict] = []

    def add(rel: str, text: str, kind: str) -> None:
        for chunk in _chunk_text(text, kind):
            passages.append(
                {
                    "id": "p%04d" % len(passages),
                    "path": rel,
                    "text": chunk,
                }
            )

    for rel in DOCS:
        path = root / rel
        if not path.is_file():
            continue
        kind = "py" if rel.endswith(".py") else "md"
        add(rel, path.read_text(encoding="utf-8", errors="replace"), kind)
    stages = root / "data" / "stages"
    if stages.is_dir():
        for path in sorted(stages.glob("*.json")):
            if path.name.startswith("_"):
                continue
            if path.stat().st_size > 20000:
                continue
            rel = "data/stages/" + path.name
            add(rel, path.read_text(encoding="utf-8", errors="replace"), "json")
    posts = root / "sources" / "x-posts.md"
    if posts.is_file():
        slice_text = _entry_052(posts.read_text(encoding="utf-8", errors="replace"))
        if slice_text:
            add("sources/x-posts.md", slice_text, "md")
    return passages


def load_passages(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_passages(path: Path, passages: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, ensure_ascii=True) for row in passages]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _path_hit(rows: list[dict], expect_path: str) -> bool:
    for row in rows:
        path = str(row.get("path") or "").replace("\\", "/")
        if path == expect_path or path.endswith("/" + expect_path):
            return True
    return False


def _passage_hit(rows: list[dict], expect_path: str, expect_substr: str) -> bool:
    for row in rows:
        path = str(row.get("path") or "").replace("\\", "/")
        if path != expect_path and not path.endswith("/" + expect_path):
            continue
        if expect_substr in str(row.get("text") or ""):
            return True
    return False


def _top_paths(rows: list[dict]) -> list[str]:
    paths = []
    for row in rows or []:
        path = str(row.get("path") or "")
        if not path:
            continue
        paths.append(path)
        if len(paths) >= 5:
            break
    return paths


def _clip_rows(rows: list[dict]) -> list[dict]:
    clipped = []
    for row in rows[:5]:
        text = str(row.get("text") or "").replace("\n", " ")
        clipped.append(
            {
                "id": row.get("id", ""),
                "path": row.get("path", ""),
                "score": row.get("score", 0),
                "text": text[:180],
            }
        )
    return clipped


def _leann_command() -> list[str]:
    raw = os.environ.get("LEANN_RUN", "").strip()
    if raw:
        return shlex.split(raw)
    py = os.environ.get("LEANN_PY", LEANN_PY_DEFAULT)
    return [py, str(ADAPTER)]


def run_leann(passages_path: Path, questions_path: Path, index_dir: Path, out_path: Path) -> tuple[dict, str]:
    cmd = _leann_command() + [
        "--passages",
        str(passages_path),
        "--questions",
        str(questions_path),
        "--index-dir",
        str(index_dir),
        "--out",
        str(out_path),
    ]
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = ""
    env.setdefault("LEANN_EMBEDDING_DEVICE", "cpu")
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT_DEFAULT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=900,
    )
    note = (proc.stderr or proc.stdout or "")[-500:]
    payload = None
    if out_path.is_file():
        try:
            payload = json.loads(out_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            payload = {"ok": False, "error": "adapter json: %s" % exc}
    if isinstance(payload, dict) and payload.get("ok") and proc.returncode == 0:
        return payload, note
    err = ""
    if isinstance(payload, dict):
        err = str(payload.get("error") or "")
    return {"ok": False, "error": err or note or ("exit %s" % proc.returncode)}, note


def _cm_call(tool: str, payload: dict, args_path: Path) -> dict:
    binary = os.environ.get("CBM_BIN", "codebase-memory-mcp")
    args_path.write_text(json.dumps(payload), encoding="utf-8")
    env = os.environ.copy()
    env["CBM_CACHE_DIR"] = os.environ.get("CBM_CACHE_DIR", CBM_CACHE_DEFAULT)
    env["CBM_LOG_LEVEL"] = "error"
    env.setdefault("CBM_MEM_BUDGET_MB", "2048")
    proc = subprocess.run(
        [binary, "cli", "--json", tool, "--args-file", str(args_path)],
        cwd=str(ROOT_DEFAULT),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    if proc.returncode != 0:
        return {"ok": False, "error": (proc.stderr or proc.stdout or "")[-300:], "rows": []}
    try:
        doc = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": "cm json: %s" % exc, "rows": []}
    structured = doc.get("structuredContent") if isinstance(doc, dict) else None
    if not isinstance(structured, dict):
        structured = doc if isinstance(doc, dict) else {}
    rows = []
    for item in structured.get("results") or []:
        if isinstance(item, dict):
            rows.append({"path": item.get("file_path") or item.get("path") or ""})
    for item in structured.get("files") or []:
        if isinstance(item, str):
            rows.append({"path": item})
    return {"ok": True, "error": "", "rows": rows}


def run_cm(questions: list[dict], work: Path) -> dict[str, dict]:
    if os.environ.get("LEANN_SKIP_CM", "") == "1":
        return {}
    project = os.environ.get("CBM_PROJECT", CBM_PROJECT_DEFAULT)
    found: dict[str, dict] = {}
    for question in questions:
        graph = _cm_call(
            "search_graph",
            {"project": project, "query": question["query"], "limit": 5},
            work / ("cm-graph-%s.json" % question["id"]),
        )
        grep = _cm_call(
            "search_code",
            {
                "project": project,
                "pattern": question["query"],
                "mode": "files",
                "limit": 5,
            },
            work / ("cm-grep-%s.json" % question["id"]),
        )
        found[question["id"]] = {"graph": graph, "grep": grep}
    return found


def _count(questions: list[dict], kind: str, field: str) -> tuple[int, int]:
    rows = [q for q in questions if q["kind"] == kind and q.get(field) is not None]
    hits = sum(1 for q in rows if q.get(field))
    return hits, len(rows)


def overlap(root: Path) -> list[dict]:
    stages = root / "data" / "stages"
    rows = []
    if not stages.is_dir():
        return rows
    for path in sorted(stages.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            card = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if not isinstance(card, dict):
            continue
        name = str(card.get("name") or path.stem)
        if name.lower() == "leann":
            continue
        blob_parts = [str(card.get("uses") or "")]
        for feature in card.get("features") or []:
            blob_parts.append(str(feature))
        for tag in (card.get("catalog_tags") or []) + (card.get("tags") or []):
            blob_parts.append(str(tag).lstrip("#"))
        blob = " ".join(blob_parts).lower()
        hits = [token for token in OVERLAP_TOKENS if token in blob]
        if not hits:
            continue
        rows.append(
            {
                "name": name,
                "slug": path.stem,
                "integration_stage": card.get("integration_stage"),
                "uses": str(card.get("uses") or "")[:240],
                "tokens": hits,
            }
        )
    return rows


def grade(questions: list[dict], adapter: dict, cm: dict[str, dict], raw_bytes: int) -> dict:
    if not adapter.get("ok"):
        graded = []
        for question in questions:
            graded.append(
                {
                    "id": question["id"],
                    "kind": question["kind"],
                    "query": question["query"],
                    "expect_path": question["expect_path"],
                    "vector_hit": None,
                    "bm25_hit": None,
                    "vector_passage_hit": None,
                    "bm25_passage_hit": None,
                    "cm_graph_hit": None,
                    "cm_grep_hit": None,
                    "cm_hit": None,
                    "cm_graph_top": None,
                    "cm_grep_top": None,
                    "recovered_by_bm25": None,
                }
            )
        return {
            "status": "skipped",
            "measured": False,
            "skip_reason": str(adapter.get("error") or "adapter failed")[:500],
            "compression_beats_raw": None,
            "savings_vs_naive": None,
            "questions": graded,
        }
    by_id = {row["id"]: row for row in adapter.get("questions") or []}
    index_bytes = int(adapter.get("index_bytes") or 0)
    naive = int(adapter.get("naive_embedding_bytes") or 0)
    graded = []
    for question in questions:
        row = by_id.get(question["id"]) or {"vector": [], "bm25": []}
        vector_rows = row.get("vector") or []
        bm25_rows = row.get("bm25") or []
        vector_hit = _path_hit(vector_rows, question["expect_path"])
        bm25_hit = _path_hit(bm25_rows, question["expect_path"])
        cm_row = cm.get(question["id"]) or {}
        graph = cm_row.get("graph") or {}
        grep = cm_row.get("grep") or {}
        if not cm:
            graph_hit = None
            grep_hit = None
            cm_hit = None
        else:
            graph_hit = _path_hit(graph.get("rows") or [], question["expect_path"]) if graph.get("ok") else False
            grep_hit = _path_hit(grep.get("rows") or [], question["expect_path"]) if grep.get("ok") else False
            cm_hit = bool(graph_hit or grep_hit)
        graded.append(
            {
                "id": question["id"],
                "kind": question["kind"],
                "query": question["query"],
                "expect_path": question["expect_path"],
                "vector_hit": vector_hit,
                "bm25_hit": bm25_hit,
                "vector_passage_hit": _passage_hit(
                    vector_rows, question["expect_path"], question["expect_substr"]
                ),
                "bm25_passage_hit": _passage_hit(
                    bm25_rows, question["expect_path"], question["expect_substr"]
                ),
                "recovered_by_bm25": (not vector_hit) and bm25_hit,
                "cm_graph_hit": graph_hit,
                "cm_grep_hit": grep_hit,
                "cm_hit": cm_hit,
                "cm_graph_top": _top_paths(graph.get("rows") or []) if cm else None,
                "cm_grep_top": _top_paths(grep.get("rows") or []) if cm else None,
                "vector_top": _clip_rows(vector_rows),
                "bm25_top": _clip_rows(bm25_rows),
            }
        )
    beats = index_bytes < raw_bytes if raw_bytes else False
    savings = None
    if naive > 0:
        savings = round((naive - index_bytes) / naive, 4)
    return {
        "status": "ok",
        "measured": True,
        "skip_reason": "",
        "compression_beats_raw": beats,
        "savings_vs_naive": savings,
        "questions": graded,
    }


def summarize(graded: list[dict]) -> dict:
    summary = {}
    for kind in ("prose", "code"):
        for field in (
            "vector_hit",
            "bm25_hit",
            "vector_passage_hit",
            "bm25_passage_hit",
            "cm_graph_hit",
            "cm_grep_hit",
            "cm_hit",
        ):
            hits, total = _count(graded, kind, field)
            summary["%s_%s" % (kind, field)] = {"hits": hits, "n": total}
    recovered = [
        q for q in graded if q.get("recovered_by_bm25") is True
    ]
    summary["recovered_by_bm25"] = len(recovered)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT_DEFAULT))
    parser.add_argument("--questions", default=str(QUESTIONS_DEFAULT))
    parser.add_argument("--passages", default="")
    parser.add_argument("--out", required=True)
    parser.add_argument("--index-dir", required=True)
    args = parser.parse_args(argv)
    root = Path(args.root)
    questions = json.loads(Path(args.questions).read_text(encoding="utf-8"))
    index_dir = Path(args.index_dir)
    index_dir.mkdir(parents=True, exist_ok=True)
    if args.passages:
        passages = load_passages(Path(args.passages))
        passages_path = Path(args.passages)
    else:
        passages = build_passages(root)
        passages_path = index_dir / "passages.jsonl"
        write_passages(passages_path, passages)
    raw_bytes = sum(len(str(p.get("text", "")).encode("utf-8")) for p in passages)
    adapter_out = index_dir / "adapter.json"
    adapter, note = run_leann(passages_path, Path(args.questions), index_dir, adapter_out)
    cm = run_cm(questions, index_dir) if adapter.get("ok") else {}
    graded = grade(questions, adapter, cm, raw_bytes)
    doc = {
        "status": graded["status"],
        "measured": graded["measured"],
        "skip_reason": graded["skip_reason"],
        "adapter_note": note[-300:] if not adapter.get("ok") else "",
        "passages": len(passages),
        "raw_bytes": raw_bytes,
        "index_bytes": adapter.get("index_bytes"),
        "dim": adapter.get("dim"),
        "naive_embedding_bytes": adapter.get("naive_embedding_bytes"),
        "embedding_matrix_stored": (
            matrix_from_files(adapter.get("files") or [], adapter.get("naive_embedding_bytes"))
            if adapter.get("ok")
            else None
        ),
        "compression_beats_raw": graded["compression_beats_raw"],
        "savings_vs_naive": graded["savings_vs_naive"],
        "build_s": adapter.get("build_s"),
        "search_s": adapter.get("search_s"),
        "files": adapter.get("files") or [],
        "backend": adapter.get("backend"),
        "embedding_model": adapter.get("embedding_model"),
        "summary": summarize(graded["questions"]),
        "questions": graded["questions"],
        "overlap": overlap(root),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(
        "status=%s passages=%s raw=%s index=%s beats_raw=%s"
        % (
            doc["status"],
            doc["passages"],
            doc["raw_bytes"],
            doc["index_bytes"],
            doc["compression_beats_raw"],
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
