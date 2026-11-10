"""Stop a second qwen38-flash-next run before download or model start.

A completed verdict for the same next_gate is the claim. A missing verdict,
a failed verdict, or a different next_gate does not block.
"""

from __future__ import annotations


def duplicate_run_blocked(verdict, next_gate) -> bool:
    if not isinstance(verdict, dict):
        return False
    if verdict.get("status") != "complete":
        return False
    return verdict.get("next_gate") == next_gate
