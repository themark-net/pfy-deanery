"""Bound a busy-GPU wait. A timeout is not a pass.

The last sample is the measurement. This module never signals a process.
"""

from __future__ import annotations


def wait_expired_verdict(samples, timed_out):
    if not timed_out:
        return None
    last = samples[-1] if samples else {}
    return {
        "status": "fail",
        "gpu_use_pct": last.get("gpu_use_pct"),
        "avail_ram_gib": last.get("avail_ram_gib"),
        "signaled_pids": [],
    }
