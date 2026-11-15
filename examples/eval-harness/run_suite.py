#!/usr/bin/env python3
"""Eval v0.2: multi-task suite and optional multi-model matrix.

Exit: 0 if gate model passes all tasks; 1 if gate fails any; 2 skip (no models).
Matrix extra models are observational (failures logged, do not fail exit unless gate).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from run_scored_task import resolve_model, score_task


def list_tasks(tasks_root: Path) -> list[str]:
    tasks = sorted(
        p.name
        for p in tasks_root.iterdir()
        if p.is_dir() and (p / "prompt.txt").is_file() and (p / "test_task.py").is_file()
    )
    return tasks


def parse_models(raw: str | None) -> list[str]:
    if not raw or not raw.strip():
        return [resolve_model(probe=True)]
    out: list[str] = []
    for part in raw.split(","):
        m = part.strip()
        if m and m not in out:
            out.append(m)
    return out or [resolve_model(probe=True)]


def ollama_names(base: str) -> set[str] | None:
    """Best-effort model list from Ollama /api/tags (None if unreachable)."""
    import json as _json
    import urllib.error
    import urllib.request

    host = base.rstrip("/").removesuffix("/v1")
    url = f"{host}/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:  # noqa: S310
            data = _json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    return {m.get("name") for m in (data.get("models") or []) if m.get("name")}


def run_cell(task: str, model: str, tasks_root: Path, base: str) -> dict:
    print(f"\n==> cell task={task} model={model}", flush=True)
    r = score_task(task, tasks_root, model_name=model, base=base)
    status = "PASS" if r.get("pass") else "FAIL"
    print(f"    {status} failures={len(r.get('failures') or [])}", flush=True)
    if r.get("failures") and not r.get("pass"):
        for f in (r.get("failures") or [])[:3]:
            print(f"      - {f}", flush=True)
    return r


def markdown_matrix(tasks: list[str], models: list[str], cells: dict[tuple[str, str], dict]) -> str:
    header = "| model \\ task | " + " | ".join(tasks) + " | pass_rate |"
    sep = "|---|" + "|".join(["---"] * len(tasks)) + "|---|"
    rows = [header, sep]
    for model in models:
        marks = []
        ok = 0
        for t in tasks:
            r = cells.get((model, t))
            if r is None:
                marks.append("—")
            elif r.get("skip"):
                marks.append("SKIP")
            elif r.get("pass"):
                marks.append("PASS")
                ok += 1
            else:
                marks.append("FAIL")
        rate = f"{ok}/{len(tasks)}"
        rows.append(f"| `{model}` | " + " | ".join(marks) + f" | {rate} |")
    return "\n".join(rows) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tasks-root", type=Path, default=Path(__file__).resolve().parent / "tasks")
    ap.add_argument(
        "--tasks",
        default="",
        help="Comma-separated task names (default: all under tasks/)",
    )
    ap.add_argument(
        "--models",
        default="",
        help="Comma-separated Ollama model names (default: model-choice for this mode)",
    )
    ap.add_argument(
        "--gate-model",
        default="",
        help="Model that must pass all tasks for exit 0 (default: first model)",
    )
    ap.add_argument(
        "--matrix-md",
        type=Path,
        default=None,
        help="Append markdown matrix to this file",
    )
    ap.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Write full JSON report",
    )
    args = ap.parse_args()

    tasks_root = args.tasks_root
    if args.tasks.strip():
        tasks = [t.strip() for t in args.tasks.split(",") if t.strip()]
    else:
        tasks = list_tasks(tasks_root)
    if not tasks:
        print("error: no tasks found", file=sys.stderr)
        return 1

    models_raw = args.models.strip() or os.environ.get("EVAL_MODELS", "")
    models = parse_models(models_raw or None)
    gate = (args.gate_model or os.environ.get("EVAL_GATE_MODEL") or models[0]).strip()
    if gate not in models:
        models = [gate] + models

    base = os.environ.get("OPENAI_BASE_URL", "http://host.docker.internal:11435/v1").rstrip("/")
    print(f"eval suite: tasks={tasks} models={models} gate={gate} base={base}", flush=True)

    available = ollama_names(base)
    if available is not None:
        print(f"  ollama models visible: {len(available)}", flush=True)

    cells: dict[tuple[str, str], dict] = {}
    report_rows: list[dict] = []

    for model in models:
        if available is not None and model not in available:
            print(f"  skip model {model!r}: not on Ollama", flush=True)
            for t in tasks:
                r = {
                    "task": t,
                    "model": f"openai/{model}",
                    "pass": False,
                    "failures": [f"model {model!r} not on Ollama"],
                    "skip": True,
                }
                cells[(model, t)] = r
                report_rows.append(r)
            continue
        for t in tasks:
            r = run_cell(t, model, tasks_root, base)
            cells[(model, t)] = r
            report_rows.append(r)

    matrix_md = markdown_matrix(tasks, models, cells)
    print("\n=== matrix ===", flush=True)
    print(matrix_md, flush=True)

    # Gate: all non-skip tasks must pass for gate model
    gate_fails = []
    for t in tasks:
        r = cells.get((gate, t))
        if r is None or r.get("skip"):
            gate_fails.append(f"{t}: missing/skipped")
        elif not r.get("pass"):
            gate_fails.append(f"{t}: FAIL")

    stamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    summary = {
        "version": "v0.2",
        "timestamp": stamp,
        "tasks": tasks,
        "models": models,
        "gate_model": gate,
        "gate_pass": len(gate_fails) == 0,
        "gate_fails": gate_fails,
        "cells": report_rows,
        "matrix_md": matrix_md,
    }

    json_out = args.json_out
    if json_out is None and os.environ.get("EVAL_RESULT_JSON"):
        json_out = Path(os.environ["EVAL_RESULT_JSON"])
    if json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {json_out}", flush=True)

    md_out = args.matrix_md
    if md_out is None and os.environ.get("EVAL_MATRIX_MD"):
        md_out = Path(os.environ["EVAL_MATRIX_MD"])
    if md_out:
        md_out.parent.mkdir(parents=True, exist_ok=True)
        block = (
            f"\n### Suite/matrix {stamp}\n\n"
            f"Gate model: `{gate}` → **{'PASS' if not gate_fails else 'FAIL'}**\n\n"
            f"{matrix_md}"
        )
        with md_out.open("a", encoding="utf-8") as f:
            f.write(block)
        print(f"appended matrix to {md_out}", flush=True)

    if gate_fails:
        print(f"GATE: FAIL ({gate}) " + ", ".join(gate_fails), flush=True)
        return 1
    print(f"GATE: PASS ({gate}) all {len(tasks)} tasks", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
