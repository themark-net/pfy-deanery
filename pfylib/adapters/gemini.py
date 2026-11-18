"""Gemini CLI adapter. Launch planning is pfylib.launch."""
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


class GeminiAdapter(Adapter):
    id = "gemini"
    config_kind = "json"

    def _home(self) -> Path:
        env = os.environ.get("GEMINI_CLI_HOME")
        if env:
            return Path(env).expanduser() / ".gemini"
        return Path.home() / ".gemini"

    def marker_dir(self) -> Path:
        return self._home()

    def config_path(self) -> Path:
        return self._home() / "settings.json"

    def skills_dir(self) -> Path:
        env = os.environ.get("GEMINI_CLI_HOME")
        if env:
            return Path(env).expanduser() / ".agents" / "skills"
        return Path.home() / ".agents" / "skills"

    def render_config(self, current: bytes | None, item_id: str, entry: dict) -> bytes:
        return render_json_mcp(current, item_id, entry, _parent)
