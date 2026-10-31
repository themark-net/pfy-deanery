"""Path-import bridge to ``scripts/pfy_*_NNN.py`` (T-0121 bridge; stays until the bodies move).

The issue-numbered modules are not a package, so ``pfylib`` loads them by
file path exactly once and caches the module object. Nothing in here
duplicates logic from those files -- callers import a function and use it.

Scripts that still go through this bridge (and who calls them):

  pfy_jev_230            toolsets._plan_jev            decision layer constants + gates
  pfy_gab_228            toolsets._plan_gab            apply_cloud_env (key gate, env shape)
  pfy_opencontext_205    toolsets._plan_opencontext    apply_child_env (oc env); attach child env
                         attach.open_session
  pfy_code_graph_215     toolsets._plan_code_graph     resolve / handoff + prompt text / apply_grok_mcp
  pfy_orchestration_213  (via 208.apply_child_env)     loop card env at attach time
  pfy_attach_mode_208    toolsets._plan_orchestration  mode texts, _agent_loops_skill, _link_skill
                         attach.prepare/open_session   apply_child_env (mode handoff into child)
  pfy_catalog_ask_queue_209  toolsets._plan_catalog_ask  apply_child_env (prompt/handoff paths)
  pfy_attach_usable_193  attach                        prove_developer_usable / openai_compat_root
  pfy_enterable_162_a    attach                        spawn_terminal_opencode / _focus_pid /
                                                       resolve_enterable_pid (OpenCode-shaped helpers)

Not bridged (still their own entry points): pfy_session_compose_224, pfy_launch_wizard_225,
pfy_recommend_models_207, pfy_live_org_queue_214, pfy_usage_165, pfy_verify_159.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from . import registry

_CACHE: dict[str, ModuleType] = {}


def load(name: str, root_dir: Path | None = None) -> ModuleType:
    """Import ``scripts/<name>.py`` by path; raise FileNotFoundError if absent."""
    key = "%s@%s" % (name, registry.root(root_dir))
    if key in _CACHE:
        return _CACHE[key]
    path = registry.root(root_dir) / "scripts" / ("%s.py" % name)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    spec = importlib.util.spec_from_file_location("pfylib_legacy_%s" % name, path)
    if spec is None or spec.loader is None:
        raise ImportError(name)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    _CACHE[key] = mod
    return mod


def optional(name: str, root_dir: Path | None = None) -> ModuleType | None:
    """Like :func:`load` but ``None`` when the script is absent (mirrors the old ``if not path.is_file(): return env`` guards)."""
    try:
        return load(name, root_dir)
    except FileNotFoundError:
        return None


def jev(root_dir: Path | None = None) -> ModuleType:
    return load("pfy_jev_230", root_dir)


def gab(root_dir: Path | None = None) -> ModuleType:
    return load("pfy_gab_228", root_dir)


def opencontext(root_dir: Path | None = None) -> ModuleType:
    return load("pfy_opencontext_205", root_dir)


def code_graph(root_dir: Path | None = None) -> ModuleType:
    return load("pfy_code_graph_215", root_dir)


def attach_mode(root_dir: Path | None = None) -> ModuleType:
    return load("pfy_attach_mode_208", root_dir)


def catalog_ask(root_dir: Path | None = None) -> ModuleType:
    return load("pfy_catalog_ask_queue_209", root_dir)


def attach_prove(root_dir: Path | None = None) -> ModuleType:
    return load("pfy_attach_usable_193", root_dir)


def enterable_helpers(root_dir: Path | None = None) -> ModuleType:
    return load("pfy_enterable_162_a", root_dir)
