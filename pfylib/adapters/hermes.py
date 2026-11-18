"""Hermes Agent adapter. Launch planning is pfylib.launch."""
# resolution follows morluto/rea SupportedClients, MIT
from __future__ import annotations

import os
from pathlib import Path

from .base import Adapter, render_yaml_mcp


class HermesAdapter(Adapter):
    id = "hermes"
    config_kind = "yaml"

    def _home(self) -> Path:
        env = os.environ.get("HERMES_HOME")
        if env:
            return Path(env).expanduser()
        return Path.home() / ".hermes"

    def marker_dir(self) -> Path:
        return self._home()

    def config_path(self) -> Path:
        return self._home() / "config.yaml"

    def skills_dir(self) -> Path:
        return self._home() / "skills"

    def render_config(self, current: bytes | None, item_id: str, entry: dict) -> bytes:
        return render_yaml_mcp(current, item_id, entry)
