#!/usr/bin/env python3
"""Eval v0.2: multi-task suite and optional multi-model matrix.

Exit: 0 if gate model passes all tasks; 1 if gate fails any; 2 skip (no models).
Matrix extra models are observational (failures logged, do not fail exit unless gate).

A public OPENAI_BASE_URL prints one suite estimate and does not open a socket
until the same yes rules as run_scored_task.py accept it. A cap must cover
the sum of the cells. One local-priced tag refuses the whole suite.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from run_scored_task import _host_is_local, _local_alternative, _public_quote, resolve_model, score_task


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


def run_cell(
    task: str,
    model: str,
    tasks_root: Path,
    base: str,
    *,
    yes: bool = False,
    max_usd: float | None = None,
    paid_ok: bool = False,
    isatty: bool = False,
    answer: str | None = None,
) -> dict:
    print(f"\n==> cell task={task} model={model}", flush=True)
    r = score_task(
        task,
        tasks_root,
        model_name=model,
        base=base,
        yes=yes,
        max_usd=max_usd,
        paid_ok=paid_ok,
        isatty=isatty,
        answer=answer,
    )
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


def _suite_public_block(
    base: str,
    tasks: list[str],
    models: list[str],
    tasks_root: Path,
    *,
    yes: bool,
    max_usd: float | None,
    isatty: bool,
    answer: str | None = None,
    max_tokens: int = 512,
) -> str | None:
    """None when cells may run. Otherwise the refusal, already printed.

    A local host is not asked. A public host sums one quote per cell and
    does not open a socket here. One unpriced model refuses the whole suite.
    A cap must cover the sum, not a single cell.
    """
    if _host_is_local(base):
        return None
    from decimal import Decimal, ROUND_HALF_UP

    local_alt = _local_alternative(base)
    total = Decimal("0")
    cells = 0
    stale = False
    sample: dict | None = None
    for model in models:
        for task in tasks:
            task_dir = tasks_root / task
            prompt_path = task_dir / "prompt.txt"
            tests_path = task_dir / "test_task.py"
            if not prompt_path.is_file() or not tests_path.is_file():
                text = "task incomplete: %s. No model was called. %s" % (task_dir, local_alt)
                print(text, file=sys.stderr)
                return text
            quoted = _public_quote(
                model, prompt_path.read_text(encoding="utf-8"), max_tokens,
            )
            if "block" in quoted:
                text = "%s %s" % (quoted["block"], local_alt)
                print(text, file=sys.stderr)
                return text
            total += Decimal(quoted["priced"]["cost_text"])
            cells += 1
            stale = stale or bool(quoted["stale"])
            sample = quoted
    if sample is None or cells == 0:
        text = "error: no tasks found. No model was called. %s" % local_alt
        print(text, file=sys.stderr)
        return text
    total_q = total.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    priced = sample["priced"]
    shown = ", ".join(models)
    line = (
        "suite cost estimate: $%s for %s cells on %s (%s $%.2f/$%.2f per 1M, %s, fetched %s). "
        "No call is sent until you say yes."
        % (
            f"{total_q:.4f}",
            f"{cells:,}",
            shown,
            priced.get("provider") or "",
            priced["price_in"],
            priced["price_out"],
            priced["source_short"],
            priced["fetched"],
        )
    )
    print(local_alt, file=sys.stderr)
    print(line, file=sys.stderr)
    if stale:
        print(
            "Price for %s was fetched %s (older than %s days)."
            % (shown, priced["fetched"], priced["stale_after_days"]),
            file=sys.stderr,
        )
    if bool(isatty) and not yes and answer is None and max_usd is None and not stale:
        try:
            answer = input("").strip()
        except EOFError:
            answer = ""
    from pfylib.model_choice import ModelCallError, _confirm, _paid_blocked

    try:
        block = _confirm(
            yes=bool(yes),
            max_usd=max_usd,
            cost=float(total_q),
            cost_text=f"{total_q:.4f}",
            isatty=bool(isatty),
            answer=answer,
            stale=stale,
            accept_stale=False,
        )
    except ModelCallError as exc:
        text = "%s. No model was called. %s" % (exc, local_alt)
        print(text, file=sys.stderr)
        return text
    if block:
        text = "%s. No model was called. %s %s" % (block, line, local_alt)
        print(text, file=sys.stderr)
        return text
    if _paid_blocked():
        text = "paid cloud call blocked. No model was called. %s %s" % (line, local_alt)
        print(text, file=sys.stderr)
        return text
    return None


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
    ap.add_argument("--yes", action="store_true", help="accept the printed suite estimate")
    ap.add_argument("--approve-cost", action="store_true", help="same as --yes; still needs a cap")
    ap.add_argument("--max-usd", type=float, default=None, help="USD cap; at or above the suite estimate is approval")
    ap.add_argument("--max-cost", type=float, default=None, help="alias of --max-usd")
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
    try:
        tty = sys.stdin.isatty()
    except Exception:
        tty = False
    cap = args.max_usd if args.max_usd is not None else args.max_cost
    approved = bool(args.yes or args.approve_cost)
    blocked = _suite_public_block(
        base,
        tasks,
        models,
        tasks_root,
        yes=approved,
        max_usd=cap,
        isatty=tty,
    )
    if blocked:
        print(f"GATE: FAIL ({gate}) spend blocked", flush=True)
        return 1

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
            r = run_cell(
                t,
                model,
                tasks_root,
                base,
                yes=approved,
                max_usd=cap,
                paid_ok=not _host_is_local(base),
                isatty=tty,
            )
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
