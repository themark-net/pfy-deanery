#!/usr/bin/env python3
"""Measure the harness2 held-out gain from the committed dogfood receipt.

Does not install harness2, does not start a model, and does not open a
proposal branch. The receipt is the trial. This probe only checks that the
scores, the pin, and the written gate reason agree.

Exit 0: the receipt is consistent. Gain may still be under the threshold.
Exit 1: the receipt is readable and a score, the pin, or the gate reason disagrees.
Exit 2: the receipt or a pin source is missing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RECEIPT_REL = "pipelines/dogfood/harness2-local/receipt.json"
CARD_REL = "data/stages/harness2.json"
PROPOSE_REL = "examples/harness2-local/propose.py"
COMMON_REL = "examples/harness2-local/common.py"
METRIC = "heldout_gain"


def _load(path: Path) -> tuple[dict | None, str | None]:
    if not path.is_file():
        return None, "missing"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"malformed: {exc.msg}"
    if not isinstance(data, dict):
        return None, "malformed: top level is not an object"
    return data, None


def _line_int(text: str, name: str) -> int | None:
    match = re.search(rf"^{re.escape(name)} = (\d+)\s*$", text, re.M)
    if match is None:
        return None
    return int(match.group(1))


def _line_pin(text: str, name: str) -> str | None:
    match = re.search(rf'^{re.escape(name)} = "([0-9a-f]{{40}})"\s*$', text, re.M)
    if match is None:
        return None
    return match.group(1)


def _run(block: object) -> dict | None:
    if not isinstance(block, dict):
        return None
    try:
        correct = int(block["n_correct"])
        n = int(block["n"])
        wbc = int(block["wrong_but_confident"])
        parse_ok = float(block["parse_ok"])
    except (KeyError, TypeError, ValueError):
        return None
    return {"correct": correct, "n": n, "wbc": wbc, "parse_ok": parse_ok}


def _better(a1: dict, a2: dict) -> dict:
    if a1["correct"] != a2["correct"]:
        return a1 if a1["correct"] > a2["correct"] else a2
    return a1 if a1["wbc"] <= a2["wbc"] else a2


def measure() -> tuple[dict, int]:
    """Return a result object and an exit code. Never invents a gain."""
    receipt_path = ROOT / RECEIPT_REL
    card_path = ROOT / CARD_REL
    propose_path = ROOT / PROPOSE_REL
    common_path = ROOT / COMMON_REL
    missing = [
        rel
        for rel, path in (
            (RECEIPT_REL, receipt_path),
            (CARD_REL, card_path),
            (PROPOSE_REL, propose_path),
            (COMMON_REL, common_path),
        )
        if not path.is_file()
    ]
    if missing:
        return {"metric": METRIC, "consistent": False, "error": "missing", "missing": missing, "runs": 0}, 2

    receipt, receipt_err = _load(receipt_path)
    card, card_err = _load(card_path)
    if receipt is None or card is None:
        return {
            "metric": METRIC,
            "consistent": False,
            "error": "malformed",
            "receipt": receipt_err,
            "card": card_err,
            "runs": 0,
        }, 1

    threshold = _line_int(propose_path.read_text(encoding="utf-8"), "GAIN_MIN")
    source_pin = _line_pin(common_path.read_text(encoding="utf-8"), "H2_PIN")
    card_pin = card.get("pinned_commit") if isinstance(card.get("pinned_commit"), str) else None
    pins = receipt.get("pins") if isinstance(receipt.get("pins"), dict) else {}
    receipt_pin = pins.get("harness2") if isinstance(pins.get("harness2"), str) else None
    bases = receipt.get("bases") if isinstance(receipt.get("bases"), dict) else {}
    a1 = _run(bases.get("a1"))
    a2 = _run(bases.get("a2"))
    final = _run(receipt.get("heldout_score"))
    problems: list[str] = []
    if threshold is None:
        problems.append("GAIN_MIN missing")
    if not source_pin or not card_pin or not receipt_pin:
        problems.append("pin missing")
    elif not (source_pin == card_pin == receipt_pin):
        problems.append("pin mismatch")
    if a1 is None or a2 is None or final is None:
        problems.append("score missing")
        return _finish(problems, threshold, source_pin, card_pin, receipt_pin, None), 1

    better = _better(a1, a2)
    gain = final["correct"] - better["correct"]
    gap = abs(a1["correct"] - a2["correct"])
    if threshold is None:
        return _finish(problems, None, source_pin, card_pin, receipt_pin, None), 1
    expected = (
        f"final {final['correct']}/{final['n']}, "
        f"better base {better['correct']}/{better['n']}, "
        f"gain {gain}, need {threshold}. "
        f"base-to-base correct gap is {gap}."
    )
    if receipt.get("gate_reason") != expected:
        problems.append("gate_reason mismatch")
    if any(row["n"] != 16 for row in (a1, a2, final)):
        problems.append("held-out n is not 16")
    if receipt.get("install_mode") != "workspace_config":
        problems.append("install_mode")
    if pins.get("temperature") != 0 or pins.get("seed") != 230:
        problems.append("temperature or seed")
    if receipt.get("relay_posts_bad_seed") != 0 or receipt.get("relay_posts_bad_temperature") != 0:
        problems.append("relay settings")
    if receipt.get("status") != "DONE":
        problems.append("status")
    under = gain < threshold or (gap >= 2 and gain <= gap)
    if under:
        if receipt.get("gate") != "fail":
            problems.append("gate")
        if receipt.get("negative_finding") != "gain":
            problems.append("negative_finding")
        if receipt.get("branch") is not None:
            problems.append("branch")
    elif receipt.get("gate") == "fail" or receipt.get("negative_finding") == "gain":
        problems.append("gate")
    if final["wbc"] > better["wbc"]:
        problems.append("wrong_but_confident rose")
    if final["parse_ok"] < better["parse_ok"]:
        problems.append("parse_ok dropped")

    result = {
        "metric": METRIC,
        "threshold": threshold,
        "heldout_gain": gain,
        "heldout_n": final["n"],
        "better_base_correct": better["correct"],
        "final_correct": final["correct"],
        "base_a1_correct": a1["correct"],
        "base_a2_correct": a2["correct"],
        "base_gap": gap,
        "gate": receipt.get("gate"),
        "negative_finding": receipt.get("negative_finding"),
        "gate_reason_ok": receipt.get("gate_reason") == expected,
        "pin": receipt_pin,
        "pin_match": bool(source_pin and source_pin == card_pin == receipt_pin),
        "install_mode": receipt.get("install_mode"),
        "temperature": pins.get("temperature"),
        "seed": pins.get("seed"),
        "relay_posts": receipt.get("relay_posts"),
        "relay_posts_bad_seed": receipt.get("relay_posts_bad_seed"),
        "relay_posts_bad_temperature": receipt.get("relay_posts_bad_temperature"),
        "wrong_but_confident_rose": final["wbc"] > better["wbc"],
        "parse_ok_dropped": final["parse_ok"] < better["parse_ok"],
        "branch": receipt.get("branch"),
        "chain_adopted": receipt.get("chain_adopted"),
        "proposal_branch": receipt.get("branch") is not None,
        "met_threshold": gain >= threshold and not (gap >= 2 and gain <= gap),
        "consistent": not problems,
        "problems": problems,
        "runs": 0,
    }
    return result, 0 if result["consistent"] else 1


def _finish(
    problems: list[str],
    threshold: int | None,
    source_pin: str | None,
    card_pin: str | None,
    receipt_pin: str | None,
    extra: dict | None,
) -> dict:
    result = {
        "metric": METRIC,
        "threshold": threshold,
        "pin": receipt_pin,
        "source_pin": source_pin,
        "card_pin": card_pin,
        "pin_match": False,
        "consistent": False,
        "problems": problems,
        "runs": 0,
    }
    if extra:
        result.update(extra)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score the harness2 dogfood receipt.")
    parser.add_argument("--out", default="", help="Write results JSON here. Default: beside this probe.")
    args = parser.parse_args(argv)
    result, code = measure()
    out = Path(args.out) if args.out else Path(__file__).resolve().parent / "results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    gain = result.get("heldout_gain")
    threshold = result.get("threshold")
    print(
        f"heldout_gain={gain} threshold={threshold} "
        f"met={result.get('met_threshold')} consistent={result.get('consistent')}"
    )
    if result.get("problems"):
        print("problems=" + ",".join(result["problems"]), file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
