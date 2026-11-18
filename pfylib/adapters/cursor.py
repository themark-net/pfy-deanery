"""Cursor CLI adapter. Launch planning is pfylib.launch."""
# resolution follows morluto/rea SupportedClients, MIT
# Official user-level paths: https://cursor.com/docs/mcp , https://cursor.com/docs/skills
# ~/.cursor/mcp.json and ~/.cursor/skills/. Project-level is a later --scope project.
from __future__ import annotations

from pathlib import Path

from .base import Adapter, render_json_mcp


def _parent(data: dict) -> dict:
    servers = data.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}
        data["mcpServers"] = servers
    return servers


class CursorAdapter(Adapter):
    id = "cursor"
    config_kind = "json"

    def _home(self) -> Path:
        return Path.home() / ".cursor"

    def marker_dir(self) -> Path:
        return self._home()

    def config_path(self) -> Path:
        return self._home() / "mcp.json"

    def skills_dir(self) -> Path:
        return self._home() / "skills"

    def render_config(self, current: bytes | None, item_id: str, entry: dict) -> bytes:
        return render_json_mcp(current, item_id, entry, _parent)
