"""Shared secret redaction for traces.

scripts/grok_trace_export.py and pfylib.otel both call redact(). Patterns that
grok_trace_export already applied stay here so the two paths cannot drift.
OTel passes limit=2000. The Grok exporter still clips later in bound().
"""

from __future__ import annotations

import math
import re
from collections import Counter

# Attribute / env names whose values are secrets. KEY is a whole component
# (api_key, KEY), not a substring of an ordinary word (monkey).
_SECRET_COMPONENT = (
    r"(?:AUTHORIZATION|TOKEN|SECRET|PASSWORD|COOKIE|BEARER|API[_-]?KEY|AUTH|KEY)"
)
_NAME = (
    r"((?:[A-Za-z0-9]+[_-])*"
    + _SECRET_COMPONENT
    + r"(?:[_-][A-Za-z0-9]+)*)"
)

_PATTERNS = [
    re.compile(
        r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----.*?-----END [A-Z0-9 ]*PRIVATE KEY-----",
        re.S,
    ),
    re.compile(r"\bxai-[A-Za-z0-9_-]{8,}"),
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"xox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(
        r"(?i)([a-z][a-z0-9+.-]*://)[^/\s:@]+:[^/\s@]+@"
    ),
    re.compile(
        r"(?i)([?&](?:access_token|id_token|refresh_token|token|api_key|apikey|key|secret|password|auth|sig|signature)=)[^&#\s]+"
    ),
    re.compile(
        r'(?i)(?<![A-Za-z0-9])"?'
        + _NAME
        + r'"?\s*[=:]\s*"?([^"\'\s,;&]+)"?'
    ),
]

_BLOB = re.compile(r"\b[A-Za-z0-9+/_=-]{40,}\b")
_SECRET_KEY = re.compile(
    r"(?i)(?:^|[._-])(?:authorization|token|secret|password|cookie|bearer|api[_-]?key|auth|key)(?:$|[._-])"
)


def _sub(match: re.Match[str]) -> str:
    # URL scheme is group 1 on the userinfo pattern (ends with ://).
    # Query pattern group 1 ends with '='.
    # KEY=VALUE group 1 is the name and group 2 is the value.
    groups = match.groups()
    if not groups or groups[0] is None:
        return "[REDACTED]"
    head = groups[0]
    if head.endswith("://"):
        return head + "[REDACTED]@"
    if head.endswith("=") or head.endswith("= "):
        return head + "[REDACTED]"
    if len(groups) >= 2 and groups[1] is not None and not head.endswith("://"):
        return head + "=[REDACTED]"
    return "[REDACTED]"


def _entropy(text: str) -> float:
    if not text:
        return 0.0
    counts = Counter(text)
    total = len(text)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def _blob_sub(match: re.Match[str]) -> str:
    token = match.group(0)
    classes = 0
    if any(ch.islower() for ch in token):
        classes += 1
    if any(ch.isupper() for ch in token):
        classes += 1
    if any(ch.isdigit() for ch in token):
        classes += 1
    if classes >= 2 and _entropy(token) >= 3.5:
        return "[REDACTED]"
    return token


def secret_attr_key(key: str) -> bool:
    """True when an attribute name itself is secret-bearing and must be dropped.

    Token-count keys contain the component "token" but are counts, not secrets.
    """
    if not key:
        return False
    if key.startswith("llm.token_count") or key.startswith("gen_ai.usage"):
        return False
    return _SECRET_KEY.search(key.replace(" ", "_")) is not None


def redact(text: str, limit: int | None = None) -> str:
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)
    for pat in _PATTERNS:
        text = pat.sub(_sub, text)
    text = _BLOB.sub(_blob_sub, text)
    text = text.replace("REDACTME", "[REDACTED]")
    if limit is not None and limit >= 0 and len(text) > limit:
        text = text[:limit] + "...[truncated]"
    return text
