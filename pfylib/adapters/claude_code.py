"""Claude Code adapter. Launch planning is pfylib.launch (Phase 2 first slice)."""
# resolution follows morluto/rea SupportedClients, MIT
from __future__ import annotations

import os
from pathlib import Path

from .base import Adapter, render_json_mcp


def _parent(data: dict) -> dict:
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}
        data["mcpServers"] = servers
    return servers


class ClaudeCodeAdapter(Adapter):
    id = "claude-code"
    config_kind = "json"

    def marker_dir(self) -> Path:
        env = os.environ.get("CLAUDE_CONFIG_DIR")
        if env:
            return Path(env).expanduser()
        return Path.home() / ".claude"

    def config_path(self) -> Path:
        env = os.environ.get("CLAUDE_CONFIG_DIR")
        if env:
            return Path(env).expanduser() / ".claude.json"
        return Path.home() / ".claude.json"

    def skills_dir(self) -> Path:
        return self.marker_dir() / "skills"

    def render_config(self, current: bytes | None, item_id: str, entry: dict) -> bytes:
        return render_json_mcp(current, item_id, entry, _parent)
