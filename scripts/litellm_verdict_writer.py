#!/usr/bin/env python3
"""Build a LiteLLM eval verdict. Never emits card stage fields."""

from __future__ import annotations

import json


def _leg(ok: bool) -> str:
    return "pass" if ok else "fail"


def build_verdict(tool: str, measured: dict) -> str:
    """Return VERDICT.json text. Omits integration_stage and tier_ceiling."""
    measured = dict(measured)
    timeout = bool(measured.get("timeout"))
    completion_ok = measured.get("completion_ok") is True
    product_lever = measured.get("product_lever") is True
    on_platform = measured.get("probe_on_platform_help") is True
    download_blocked = measured.get("download_blocked") is True
    started = measured.get("start_model") is True
    gpu_used = measured.get("gpu_used") is True

    gap = completion_ok
    leverage = completion_ok and not product_lever
    evidence = completion_ok and not timeout
    blast = not download_blocked
    value_n = sum(1 for ok in (gap, leverage, evidence, blast) if ok)
    trial_ok = (
        not timeout
        and completion_ok
        and not product_lever
        and on_platform
        and not download_blocked
        and started
        and gpu_used
    )
    local_code = measured.get("local_code_needed") is True
    bounded = measured.get("bounded_surface") is True
    isolatable = (not product_lever) and measured.get("isolatable") is True
    reversible = measured.get("reversible") is True
    modularity_ok = local_code and bounded and isolatable and reversible

    doc = {
        "metric": "probe_not_product_lever",
        "threshold": 1,
        "value": 1 if trial_ok else 0,
        "value_gate": "pass" if trial_ok and value_n >= 3 else "fail",
        "modularity_gate": "pass" if modularity_ok else "fail",
        "proposed_stage": "I3",
        "tool": tool,
        "measured": measured,
        "value_legs": {
            "gap_fill": _leg(gap),
            "operator_leverage": _leg(leverage),
            "evidence": _leg(evidence),
            "blast_radius": _leg(blast),
        },
        "modularity_legs": {
            "local_code_needed": _leg(local_code),
            "bounded_surface": _leg(bounded),
            "isolatable": _leg(isolatable),
            "reversible": _leg(reversible),
        },
    }
    return json.dumps(doc, indent=2) + "\n"
