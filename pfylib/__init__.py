"""pfylib -- toolset x harness handoff + hedge (ADR-0017).

Named ``pfylib`` because the repo root already has an executable file ``pfy``;
``./pfy`` stays the user-facing name and ``scripts/pfy`` dispatches the
``toolset`` / ``hedge`` verbs to :mod:`pfylib.cli`.

Modules:
  registry  -- load data/harnesses.json + data/toolsets.json; validate shape
  stage_registry -- one data/stages/<slug>.json per tool; load_stages() is the old document
  toolsets  -- matrix() / plan() / apply(); planners wrap scripts/pfy_*_NNN.py via _legacy (T-0121)
  hedge     -- deterministic local-first lane policy + ledger
  loop_paint -- Loop UI fragment: modules + local/cloud hedge (not a harness picker)
  attach    -- one harness-parameterised Attach (data/harnesses.json[].attach); the
               scripts/pfy_attach_usable_*.py files are thin shims over it (T-0121)
  cli       -- argparse front end used by ``./pfy toolset`` and ``./pfy hedge``
  bot_interface -- ``./pfy bot`` one-shot. Default opencode. PFY_BOT_INTERFACE=hermes opts in.
  setup     -- phase-1 setup / doctor / uninstall (adapters + ledger)
  adapters  -- harness path resolution (no launch)
  _legacy   -- path-import bridge to scripts/pfy_*_NNN.py (see its docstring for who still uses it)

Stdlib only. Python >= 3.12.
"""
from __future__ import annotations

__all__ = ["registry", "toolsets", "hedge", "attach", "loop_paint", "cli", "setup", "adapters"]
__version__ = "0.1.0"
