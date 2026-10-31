"""Classify a failed cloud grok exit.

Pure function. It takes no path, opens no file, and returns only the enum
``rate-limit``, ``unauthenticated``, or ``other``. It does not echo grok text.

Rules, in order, over ``stdout + "\\n" + stderr``, case insensitive, only when
``rc`` is not 0:

1. ``rate-limit`` on ``rate limit``, ``usage limit``, ``quota exceeded``,
   ``too many requests``, or ``429``.
2. ``unauthenticated`` on ``unauthenticated``, ``not logged in``,
   ``please log in``, or ``auth.json``.
3. Otherwise ``other``.

``rc`` 0 is always ``other``, even when the text contains those phrases.
"""

from __future__ import annotations

_RATE_LIMIT = (
    "rate limit",
    "usage limit",
    "quota exceeded",
    "too many requests",
    "429",
)
_UNAUTHENTICATED = (
    "unauthenticated",
    "not logged in",
    "please log in",
    "auth.json",
)


def classify_cloud_failure(rc, stdout, stderr) -> str:
    """Return rate-limit, unauthenticated, or other for one grok exit."""
    if rc == 0:
        return "other"
    text = f"{stdout}\n{stderr}".lower()
    if any(phrase in text for phrase in _RATE_LIMIT):
        return "rate-limit"
    if any(phrase in text for phrase in _UNAUTHENTICATED):
        return "unauthenticated"
    return "other"
