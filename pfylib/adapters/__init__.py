"""Harness adapters for pfy setup. Phase 2 launch planning lives in pfylib.launch."""
# resolution follows morluto/rea SupportedClients, MIT
from __future__ import annotations

from .claude_code import ClaudeCodeAdapter
from .codex import CodexAdapter
from .gemini import GeminiAdapter
from .grok import GrokAdapter
from .hermes import HermesAdapter
from .opencode import OpenCodeAdapter

ADAPTERS = (
    GrokAdapter(),
    ClaudeCodeAdapter(),
    CodexAdapter(),
    OpenCodeAdapter(),
    HermesAdapter(),
    GeminiAdapter(),
)


def by_id(hid: str):
    for adapter in ADAPTERS:
        if adapter.id == hid:
            return adapter
    return None
