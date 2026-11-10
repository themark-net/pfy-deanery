"""Keep integration_stage and tier_ceiling at the values already on the card."""

from __future__ import annotations

_FROZEN = ("integration_stage", "tier_ceiling")


def freeze_ceiling_fields(prior, proposed):
    written = dict(proposed)
    for key in _FROZEN:
        if isinstance(prior, dict) and key in prior:
            written[key] = prior[key]
        else:
            written.pop(key, None)
    return written
