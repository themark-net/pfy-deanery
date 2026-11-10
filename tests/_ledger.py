"""Shared check for rule refusals (data/promotion-rules.json ledger).

A refusal may write one promotion_history entry and nothing else: the
stage, ceiling, and evidence stay as they were.
"""
from __future__ import annotations

import json
from pathlib import Path


def assert_only_ledger(test, path: Path, before: bytes) -> None:
    after = Path(path).read_bytes()
    if after == before:
        return
    old = json.loads(before.decode("utf-8"))
    new = json.loads(after.decode("utf-8"))
    old_history = old.pop("promotion_history", [])
    history = new.pop("promotion_history", None)
    test.assertEqual(new, old, "a refusal may only add promotion_history")
    test.assertIsInstance(history, list)
    test.assertEqual(history[: len(old_history)], old_history)
    test.assertEqual(history[-1]["result"], "refuse")
    test.assertTrue(history[-1]["failed"], "a refusal names the failed rule")
