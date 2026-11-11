"""Keep model-choice tests off the real ~/.config/pfy and ~/.local/state/pfy.

Call begin() in setUp and end() in tearDown. Subprocesses should use
subprocess_env() so XDG_CONFIG_HOME and XDG_STATE_HOME are the temp dirs too.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

# Names that can change resolve() or the compare ledger. Cleared, then the
# four paths below are pointed at the temp dir.
ISOLATED_KEYS = (
    "PFY_MODEL_CATALOG_FIT",
    "PFY_MODEL_EVAL_LANE",
    "PFY_MODEL_EVAL_SUITE",
    "PFY_MODEL_MATRIX",
    "PFY_MODEL_DECISION_ROUTE",
    "PFY_MODEL_BUILD_LANE",
    "PFY_CATFIT_MODEL",
    "EVAL_MODEL",
    "EVAL_GATE_MODEL",
    "EVAL_MODE",
    "EVAL_MODELS",
    "LITELLM_SMOKE_MODEL",
    "PFY_LOCAL_BUILD_MODEL",
    "PFY_JEV_MODEL",
    "PFY_MODEL_CHOICE_PATH",
    "PFY_COMPARE_STATE_PATH",
    "PFY_COMPARE_REMIND_DAYS",
    "PFY_MODEL_NO_PAID",
    "PFY_PRICE_REFRESH_STATE",
    "PFY_ROOT",
    "PFY_VENV",
    "TIKTOKEN_CACHE_DIR",
    "XDG_CONFIG_HOME",
    "XDG_STATE_HOME",
)


def begin(prefix: str = "pfy-mc-iso-") -> tuple[Path, dict]:
    tmp = Path(tempfile.mkdtemp(prefix=prefix))
    saved = {key: os.environ.get(key) for key in ISOLATED_KEYS}
    for key in ISOLATED_KEYS:
        os.environ.pop(key, None)
    os.environ["PFY_MODEL_NO_PAID"] = "1"
    os.environ["PFY_MODEL_CHOICE_PATH"] = str(tmp / "model-choice.json")
    os.environ["PFY_COMPARE_STATE_PATH"] = str(tmp / "model-compare.json")
    os.environ["XDG_CONFIG_HOME"] = str(tmp / "xdg-config")
    os.environ["XDG_STATE_HOME"] = str(tmp / "xdg-state")
    (tmp / "xdg-config").mkdir()
    (tmp / "xdg-state").mkdir()
    return tmp, saved


def end(tmp: Path, saved: dict) -> None:
    for key, value in saved.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    shutil.rmtree(tmp, ignore_errors=True)


def subprocess_env(base: dict | None = None, root: Path | None = None) -> dict:
    """Child env with the isolated paths. Creates the dirs when missing."""
    env = dict(os.environ if base is None else base)
    if root is None:
        choice = env.get("PFY_MODEL_CHOICE_PATH") or ""
        root = Path(choice).parent if choice else Path(tempfile.mkdtemp(prefix="pfy-mc-sub-"))
    root = Path(root)
    config = root / "xdg-config"
    state = root / "xdg-state"
    config.mkdir(parents=True, exist_ok=True)
    state.mkdir(parents=True, exist_ok=True)
    env["PFY_MODEL_NO_PAID"] = "1"
    env["PFY_MODEL_CHOICE_PATH"] = env.get("PFY_MODEL_CHOICE_PATH") or str(root / "model-choice.json")
    env["PFY_COMPARE_STATE_PATH"] = env.get("PFY_COMPARE_STATE_PATH") or str(root / "model-compare.json")
    env["XDG_CONFIG_HOME"] = env.get("XDG_CONFIG_HOME") or str(config)
    env["XDG_STATE_HOME"] = env.get("XDG_STATE_HOME") or str(state)
    return env
