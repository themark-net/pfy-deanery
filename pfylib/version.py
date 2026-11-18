"""Product version from the PEP 621 pyproject.toml SoT (or the installed dist)."""
from __future__ import annotations

import importlib.metadata
import os
import tomllib
from pathlib import Path

DIST_NAME = "pfy-deanery"


def repo_root(explicit: str | os.PathLike | None = None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    env = os.environ.get("PFY_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[1]


def pyproject_path(root: str | os.PathLike | None = None) -> Path:
    return repo_root(root) / "pyproject.toml"


def version_from_pyproject(root: str | os.PathLike | None = None) -> str:
    path = pyproject_path(root)
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    version = str((data.get("project") or {}).get("version") or "").strip()
    if not version:
        raise RuntimeError("pyproject.toml is missing [project].version")
    return version


def version_from_metadata() -> str | None:
    try:
        return importlib.metadata.version(DIST_NAME)
    except importlib.metadata.PackageNotFoundError:
        return None


def product_version(root: str | os.PathLike | None = None) -> str:
    """Checkout pyproject wins when present; otherwise the installed distribution."""
    try:
        return version_from_pyproject(root)
    except FileNotFoundError:
        installed = version_from_metadata()
        if installed:
            return installed
        raise RuntimeError("pfy version SoT not found (no pyproject.toml, dist not installed)") from None
