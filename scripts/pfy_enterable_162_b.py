#!/usr/bin/env python3
"""Enterable OpenCode open_enterable -- cite #162 (shim).

Body lives in ``pfylib/attach.py`` ``open_opencode_session`` (T-0124).
The names ``scripts/pfy_enterable_162.py`` and the board load stay here.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pfylib import _legacy, attach  # noqa: E402

_a = _legacy.enterable_helpers()
_u = _legacy.attach_prove()
SESSION_REACH_OK = _u.SESSION_REACH_USABLE
SESSION_FILE = _a.SESSION_FILE
read_session_reach = _a.read_session_reach
write_session_reach = _a.write_session_reach
clear_session_reach = _a.clear_session_reach
spawn_terminal_opencode = _a.spawn_terminal_opencode
_focus_pid = _a._focus_pid
write_terminal_pid = _a.write_terminal_pid
read_terminal_pid = _a.read_terminal_pid
resolve_enterable_pid = _a.resolve_enterable_pid
prove_developer_usable = _u.prove_developer_usable
fail_not_usable = _u.fail_not_usable
openai_compat_root = _u.openai_compat_root


def open_enterable_opencode_session(**deps):
    return attach.open_opencode_session(**deps)
