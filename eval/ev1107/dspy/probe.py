#!/usr/bin/env python3
"""Score the #230 decision cases and apply the ev1107 DSPy verdict rule.

Stdlib only. The live optimizer is eval/ev1107/dspy/live.py. This file splits
the 48 cases, hides labels from the model payload, scores choice match, and
decides PROMOTE I2 versus STAY I1.

Verdict rule (fixed before the live numbers): each arm is scored twice on the
same held-out cases. Noise is the larger of the two run-to-run spreads.
Mean gain must be at least that noise plus 2 cases. A single score cannot
promote. Equality with the bar promotes.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

SEED = 230
TRAIN_N = 24
DEV_N = 8
HELD_N = 16
SPLIT_N = TRAIN_N + DEV_N + HELD_N


def load_bank(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {"conf_gate": 0.85, "cases": data}
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise ValueError(f"{path} has no cases list")
    return data


def case_ids(bank: dict) -> list[str]:
    return [str(case["id"]) for case in bank["cases"]]


def permutation(ids: list[str], seed: int = SEED) -> list[str]:
    ordered = sorted(ids)
    random.Random(seed).shuffle(ordered)
    return ordered


def split_ids(ids: list[str], seed: int = SEED) -> dict:
    """Seed-230 order. Held-out is the last 16, the same slice harness2 uses.

    Train is the first 24 of that order. Dev is the next 8. Dev is recorded
    and is not used to pick the program or the verdict.
    """
    if len(ids) < SPLIT_N:
        raise ValueError(f"need {SPLIT_N} cases to split, got {len(ids)}")
    order = permutation(ids, seed)
    train = order[:TRAIN_N]
    dev = order[TRAIN_N : TRAIN_N + DEV_N]
    heldout = order[TRAIN_N + DEV_N : SPLIT_N]
    groups = (train, dev, heldout)
    if len(heldout) != HELD_N or len({i for group in groups for i in group}) != SPLIT_N:
        raise ValueError("split overlap")
    return {"seed": seed, "train": train, "dev": dev, "heldout": heldout}


def by_id(bank: dict) -> dict[str, dict]:
    return {str(case["id"]): case for case in bank["cases"]}


def payload_for(case: dict) -> dict:
    """Model view. Labels and notes stay out."""
    return {
        "id": str(case["id"]),
        "task": case.get("instructions") or "",
        "state": case.get("state"),
        "criteria": case.get("criteria") or {},
    }


def normalize_choice(raw, criteria: dict) -> str | None:
    if raw is None or not isinstance(criteria, dict) or not criteria:
        return None
    text = str(raw).strip().strip("`\"'")
    if text in criteria:
        return text
    lowered = {str(key).lower(): key for key in criteria}
    return lowered.get(text.lower())


def parse_confidence(raw) -> float | None:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value > 1.0 and value <= 100.0:
        value = value / 100.0
    if value < 0.0 or value > 1.0:
        return None
    return value


def score_answer(case: dict, answer: dict, gate: float) -> dict:
    criteria = case.get("criteria") or {}
    choice = normalize_choice(answer.get("choice") if isinstance(answer, dict) else None, criteria)
    confidence = parse_confidence(answer.get("confidence") if isinstance(answer, dict) else None)
    parsed = choice is not None and confidence is not None
    correct = bool(parsed and choice == case.get("label"))
    escalate = (not parsed) or confidence < gate
    return {
        "id": str(case["id"]),
        "choice": choice,
        "label": case.get("label"),
        "confidence": confidence,
        "parse_ok": parsed,
        "correct": correct,
        "escalate": escalate,
        "wrong_but_confident": bool((not correct) and parsed and confidence >= gate),
    }


def summarize(rows: list[dict], gate: float) -> dict:
    n = len(rows)
    n_correct = sum(1 for row in rows if row["correct"])
    n_parse = sum(1 for row in rows if row["parse_ok"])
    n_escalate = sum(1 for row in rows if row["escalate"])
    n_wbc = sum(1 for row in rows if row["wrong_but_confident"])
    return {
        "n": n,
        "n_correct": n_correct,
        "n_parse_ok": n_parse,
        "parse_ok": 0.0 if n == 0 else n_parse / n,
        "n_escalate": n_escalate,
        "wrong_but_confident": n_wbc,
        "gate": gate,
    }


def _fmt_gain(twice: int) -> str:
    sign = "-" if twice < 0 else ""
    twice = abs(twice)
    if twice % 2 == 0:
        return f"{sign}{twice // 2}"
    whole, rem = divmod(twice, 2)
    return f"{sign}{whole}.5" if rem else f"{sign}{whole}"


def verdict(baseline: list[int], optimized: list[int]) -> dict:
    """Mean held-out gain must clear the larger run-to-run spread by 2 cases."""
    if len(baseline) != 2 or len(optimized) != 2:
        raise ValueError("need two baseline scores and two optimized scores")
    scores = list(baseline) + list(optimized)
    for score in scores:
        if isinstance(score, bool) or not isinstance(score, int) or score < 0:
            raise ValueError("scores must be non-negative ints")
    b0, b1 = baseline
    o0, o1 = optimized
    noise = max(abs(b0 - b1), abs(o0 - o1))
    twice = (o0 + o1) - (b0 + b1)
    need = noise + 2
    promote = twice >= 2 * need
    gain_text = _fmt_gain(twice)
    if promote:
        line = f"PROMOTE I2 held-out mean gain {gain_text} clears noise {noise} plus 2"
    else:
        line = f"STAY I1 held-out mean gain {gain_text} is under noise {noise} plus 2"
    return {
        "baseline": [b0, b1],
        "optimized": [o0, o1],
        "noise": noise,
        "gain": gain_text,
        "need": need,
        "promote": promote,
        "line": line,
    }


def _root_url(base: str) -> str:
    root = (base or "").strip().rstrip("/")
    if root.endswith("/v1"):
        root = root[: -len("/v1")]
    if "://" not in root:
        root = "http://" + root
    return root


def preflight_base(base: str, timeout: float = 3.0) -> tuple[bool, str]:
    url = _root_url(base) + "/api/version"
    req = urllib.request.Request(url, method="GET")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=timeout) as resp:
            if resp.status != 200:
                return False, f"unreachable {url} status {resp.status}"
            return True, "ok"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, f"unreachable {url} {exc}"


def _parse_pair(text: str, name: str) -> list[int]:
    parts = [part.strip() for part in text.split(",")]
    if len(parts) != 2 or any(part == "" for part in parts):
        raise ValueError(f"{name} needs two comma-separated scores")
    try:
        return [int(part) for part in parts]
    except ValueError as exc:
        raise ValueError(f"{name} scores must be ints") from exc


def _run_driver(driver: str, payload: dict, timeout: float) -> tuple[int, dict | None, str]:
    proc = subprocess.run(
        [driver],
        input=json.dumps(payload).encode("utf-8"),
        capture_output=True,
        timeout=timeout,
        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "TMPDIR": os.environ.get("TMPDIR", "/tmp")},
        check=False,
    )
    text = proc.stdout.decode("utf-8", "replace").strip()
    answer = None
    if text:
        line = text.splitlines()[-1]
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            answer = parsed
    err = proc.stderr.decode("utf-8", "replace").strip()
    return proc.returncode, answer, err


def run_driver(bank: dict, driver: str, timeout: float) -> dict:
    gate = float(bank.get("conf_gate") or 0.85)
    rows = []
    for case in bank["cases"]:
        payload = payload_for(case)
        if "label" in payload or "note" in payload:
            return {"ok": False, "error": "refusing to send label", "rows": rows}
        try:
            code, answer, err = _run_driver(driver, payload, timeout)
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "driver-timeout", "case_id": str(case["id"]), "rows": rows}
        if code != 0 or answer is None:
            return {
                "ok": False,
                "error": "driver-failed",
                "case_id": str(case["id"]),
                "returncode": code,
                "detail": err[:400],
                "rows": rows,
            }
        rows.append(score_answer(case, answer, gate))
    summary = summarize(rows, gate)
    return {"ok": True, "error": None, "rows": rows, **summary}


def _emit(data: dict) -> int:
    json.dump(data, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DSPy decision-probe scoring (no model)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    split_p = sub.add_parser("split")
    split_p.add_argument("--cases", type=Path, required=True)
    split_p.add_argument("--seed", type=int, default=SEED)

    payload_p = sub.add_parser("payload")
    payload_p.add_argument("--cases", type=Path, required=True)
    payload_p.add_argument("--id", required=True)

    verdict_p = sub.add_parser("verdict")
    verdict_p.add_argument("--baseline", required=True)
    verdict_p.add_argument("--optimized", required=True)

    pre_p = sub.add_parser("preflight")
    pre_p.add_argument("--base-url", required=True)
    pre_p.add_argument("--timeout", type=float, default=3.0)

    run_p = sub.add_parser("run")
    run_p.add_argument("--cases", type=Path, required=True)
    run_p.add_argument("--driver", required=True)
    run_p.add_argument("--out", type=Path, required=True)
    run_p.add_argument("--timeout", type=float, default=30.0)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "split":
            bank = load_bank(args.cases)
            return _emit(split_ids(case_ids(bank), args.seed))
        if args.cmd == "payload":
            bank = load_bank(args.cases)
            case = by_id(bank).get(args.id)
            if case is None:
                print(f"unknown id {args.id}", file=sys.stderr)
                return 2
            return _emit(payload_for(case))
        if args.cmd == "verdict":
            decided = verdict(_parse_pair(args.baseline, "baseline"), _parse_pair(args.optimized, "optimized"))
            print(decided["line"])
            return 0
        if args.cmd == "preflight":
            ok, detail = preflight_base(args.base_url, args.timeout)
            if ok:
                print(detail)
                return 0
            print(detail, file=sys.stderr)
            return 2
        receipt = run_driver(load_bank(args.cases), args.driver, args.timeout)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if not receipt["ok"]:
            print(receipt["error"], file=sys.stderr)
            return 2
        print(json.dumps({"ok": True, "n_correct": receipt["n_correct"], "n": receipt["n"]}))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
