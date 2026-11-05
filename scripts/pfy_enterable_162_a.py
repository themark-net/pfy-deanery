#!/usr/bin/env python3
"""Enterable OpenCode session helpers — cite #162 (a).

Attach must open/focus a usable interactive terminal (not silent sidecar alone).
Launch env must arm/open enterable path or honest SKIP (copy alone insufficient).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

SESSION_REACH_OK = "terminal · OpenCode"
SESSION_FILE = "opencode-session-reach"
TERMINAL_PID_FILE = "opencode-terminal.pid"


def _which(*names):
    for n in names:
        found = shutil.which(n)
        if found:
            return found
    return ""


def read_session_reach(STATE) -> str:
    path = Path(STATE) / SESSION_FILE
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()[:80]
    except OSError:
        return ""


def write_session_reach(STATE, text: str) -> None:
    STATE = Path(STATE)
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / SESSION_FILE).write_text((text or "").strip()[:80] + "\n", encoding="utf-8")


def clear_session_reach(STATE) -> None:
    STATE = Path(STATE)
    names = (SESSION_FILE, TERMINAL_PID_FILE, pid_start_name(TERMINAL_PID_FILE))
    for name in names:
        path = STATE / name
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass


def write_terminal_pid(STATE, pid: int) -> None:
    STATE = Path(STATE)
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / TERMINAL_PID_FILE).write_text(str(int(pid)) + "\n", encoding="utf-8")
    write_recorded_start(STATE, TERMINAL_PID_FILE, pid)


def read_terminal_pid(STATE):
    path = Path(STATE) / TERMINAL_PID_FILE
    if not path.is_file():
        return 0
    try:
        return int(path.read_text(encoding="utf-8", errors="replace").strip())
    except (ValueError, OSError):
        return 0


def _focus_pid(pid: int) -> bool:
    """Best-effort focus an existing terminal/process window. True only if a window was activated."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    wmctrl = _which("wmctrl")
    if wmctrl:
        try:
            proc = subprocess.run(
                [wmctrl, "-lp"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            for line in (proc.stdout or "").splitlines():
                parts = line.split()
                if len(parts) >= 3 and parts[2] == str(pid):
                    wid = parts[0]
                    r = subprocess.run([wmctrl, "-ia", wid], capture_output=True, timeout=5, check=False)
                    if r.returncode == 0:
                        return True
        except Exception:
            pass
    xdotool = _which("xdotool")
    if xdotool:
        try:
            proc = subprocess.run(
                [xdotool, "search", "--pid", str(pid)],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            wids = [w for w in (proc.stdout or "").split() if w.strip()]
            if wids:
                r = subprocess.run(
                    [xdotool, "windowactivate", "--sync", wids[0]],
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
                if r.returncode == 0:
                    return True
        except Exception:
            pass
    return False


def _has_display(env: dict) -> bool:
    if sys.platform == "darwin":
        return True
    display = (env.get("DISPLAY") or os.environ.get("DISPLAY") or "").strip()
    wayland = (env.get("WAYLAND_DISPLAY") or os.environ.get("WAYLAND_DISPLAY") or "").strip()
    return bool(display or wayland)


# argv0 of a shebang wrapper is the interpreter, not the script name.
_INTERPRETERS = frozenset({"sh", "bash", "dash", "python", "python3", "env"})


def pid_start_name(pid_file_name: str) -> str:
    """Sibling that stores the /proc start time for a pid file."""
    name = str(pid_file_name or "")
    if name.endswith(".pid"):
        return name[:-4] + ".start"
    return name + ".start"


def _stat_fields(pid: int):
    """Tokens after comm in /proc/<pid>/stat. Empty when the pid is gone."""
    try:
        raw = Path("/proc/%d/stat" % int(pid)).read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        return []
    end = raw.rfind(")")
    if end < 0:
        return []
    return raw[end + 1:].split()


def is_zombie(pid: int) -> bool:
    fields = _stat_fields(pid)
    return bool(fields) and fields[0] == "Z"


def proc_starttime(pid: int) -> str:
    """Clock ticks since boot, field 22. Empty when /proc cannot be read."""
    fields = _stat_fields(pid)
    if len(fields) <= 19:
        return ""
    return fields[19]


def write_recorded_start(state, pid_file_name: str, pid: int) -> None:
    """Record the start time of the pid we are about to store. No-op if unreadable."""
    start = proc_starttime(pid)
    if not start:
        return
    state = Path(state)
    try:
        state.mkdir(parents=True, exist_ok=True)
        (state / pid_start_name(pid_file_name)).write_text(start + "\n", encoding="utf-8")
    except OSError:
        pass


def same_recorded_process(state, pid_file_name: str, pid, pid_alive) -> bool:
    """True only when pid is alive, not a zombie, and its start time matches the file.

    A missing start file is not a match: pid numbers are reused by the kernel.
    """
    try:
        pid = int(pid or 0)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    try:
        if callable(pid_alive) and not pid_alive(pid):
            return False
    except Exception:
        return False
    if is_zombie(pid):
        return False
    path = Path(state) / pid_start_name(pid_file_name)
    try:
        recorded = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return False
    live = proc_starttime(pid)
    return bool(recorded) and recorded == live


def _argv(pid: int) -> list:
    try:
        raw = Path("/proc/%d/cmdline" % int(pid)).read_bytes()
    except (OSError, ValueError):
        return []
    return [piece.decode("utf-8", errors="replace") for piece in raw.split(b"\x00") if piece]


def _is_interpreter(argv0: str) -> bool:
    base = Path(argv0).name
    return base in _INTERPRETERS or base.startswith("python")


def _looks_like_bin(pid: int, bin_path: str) -> bool:
    """True when this process is the harness binary or a shebang wrapper for it.

    The script token is the first non-option argument. A terminal whose later
    argv only mentions the harness is not the harness.
    """
    want = Path(str(bin_path or "")).name
    if not want:
        return False
    argv = _argv(pid)
    if not argv:
        return False
    if Path(argv[0]).name == want:
        return True
    if not _is_interpreter(argv[0]):
        return False
    for token in argv[1:]:
        if token == "--" or token.startswith("-"):
            continue
        return Path(token).name == want
    return False


def _ppid_map() -> dict:
    ppid_of = {}
    proc = Path("/proc")
    if not proc.is_dir():
        return ppid_of
    try:
        entries = list(proc.iterdir())
    except OSError:
        return ppid_of
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            pid = int(entry.name)
            status = (entry / "status").read_text(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            continue
        ppid = 0
        for line in status.splitlines():
            if line.startswith("PPid:"):
                parts = line.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    ppid = int(parts[1])
                break
        ppid_of[pid] = ppid
    return ppid_of


def _descendants(parent_pid: int) -> list:
    """Pids whose parent chain reaches parent_pid. The parent itself is excluded."""
    try:
        parent_pid = int(parent_pid)
    except (TypeError, ValueError):
        return []
    if parent_pid <= 0:
        return []
    children = {}
    for pid, ppid in _ppid_map().items():
        children.setdefault(ppid, []).append(pid)
    found = []
    frontier = [parent_pid]
    seen = {parent_pid}
    while frontier:
        cur = frontier.pop(0)
        for kid in children.get(cur, []):
            if kid in seen:
                continue
            seen.add(kid)
            found.append(kid)
            frontier.append(kid)
    return found


def _live_pid(pid, pid_alive) -> bool:
    try:
        pid = int(pid or 0)
    except (TypeError, ValueError):
        return False
    if pid <= 0 or is_zombie(pid):
        return False
    if not callable(pid_alive):
        return True
    try:
        return bool(pid_alive(pid))
    except Exception:
        return False


def resolve_enterable_pid(bin_path: str, candidate: int, pid_alive) -> int:
    """Pid spawned for this candidate: itself, or a descendant of it.

    Does not scan the process table for a matching binary. A harness that
    was already running is not a descendant, so it is not adopted.
    """
    try:
        candidate = int(candidate or 0)
    except (TypeError, ValueError):
        candidate = 0
    if candidate <= 0:
        return 0
    if _live_pid(candidate, pid_alive) and _looks_like_bin(candidate, bin_path):
        return candidate
    kids = _descendants(candidate)
    for pid in kids:
        if _live_pid(pid, pid_alive) and _looks_like_bin(pid, bin_path):
            return pid
    if _live_pid(candidate, pid_alive):
        return candidate
    for pid in kids:
        if _live_pid(pid, pid_alive):
            return pid
    return 0


def _terminal_cmds(bin_path: str, cwd: str):
    """Yield argv lists to spawn a native terminal running opencode."""
    xte = _which("xdg-terminal-exec")
    if xte:
        yield [xte, bin_path]
    # Prefer terminals that keep a long-lived process when possible
    kitty = _which("kitty")
    if kitty:
        yield [kitty, "--directory", cwd, bin_path]
    alacritty = _which("alacritty")
    if alacritty:
        yield [alacritty, "--working-directory", cwd, "-e", bin_path]
    wezterm = _which("wezterm")
    if wezterm:
        yield [wezterm, "start", "--cwd", cwd, "--", bin_path]
    xterm = _which("xterm")
    if xterm:
        yield [xterm, "-e", "cd %s && exec %s" % (cwd, bin_path)]
    konsole = _which("konsole")
    if konsole:
        yield [konsole, "--workdir", cwd, "-e", bin_path]
    # Wrappers that often exit after spawn. A child is claimed only while it
    # still descends from that process. An already-running harness is not adopted.
    gnome = _which("gnome-terminal")
    if gnome:
        yield [gnome, "--working-directory=" + cwd, "--", bin_path]
    xfce = _which("xfce4-terminal")
    if xfce:
        yield [xfce, "--working-directory=" + cwd, "-e", bin_path]
    if sys.platform == "darwin":
        osa = _which("osascript")
        if osa:
            script = (
                'tell application "Terminal"\n'
                "  activate\n"
                '  do script "cd " & quoted form of "%s" & " && %s"\n'
                "end tell\n" % (cwd.replace('"', ""), bin_path)
            )
            yield [osa, "-e", script]


def spawn_terminal_opencode(bin_path: str, cwd: str, env: dict, log_path: Path, pid_alive) -> tuple:
    """Spawn a native terminal running the harness. Returns (ok, pid, error).

    The pid is the terminal this call spawned, or a descendant of it. A harness
    that was already running is not adopted. A terminal that exits with no
    harness child is "terminal exited".
    """
    cwd = str(cwd)
    bin_path = str(bin_path)
    last_err = "no terminal"
    if not _has_display(env):
        return False, 0, "no DISPLAY · cannot open terminal"
    cmds = list(_terminal_cmds(bin_path, cwd))
    if not cmds:
        return False, 0, "no terminal binary on PATH"
    for argv in cmds:
        proc = None
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("ab") as f:
                f.write(("spawn: %s\n" % " ".join(argv)).encode("utf-8", errors="replace"))
                proc = subprocess.Popen(
                    argv,
                    cwd=cwd,
                    env=env,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            deadline = time.monotonic() + 0.6
            while True:
                real = resolve_enterable_pid(bin_path, proc.pid, pid_alive)
                if (
                    real
                    and real != proc.pid
                    and _live_pid(real, pid_alive)
                    and _looks_like_bin(real, bin_path)
                ):
                    return True, real, ""
                if _live_pid(proc.pid, pid_alive) and _looks_like_bin(proc.pid, bin_path):
                    return True, proc.pid, ""
                if not _live_pid(proc.pid, pid_alive):
                    try:
                        proc.wait(timeout=0.2)
                    except Exception:
                        pass
                    last_err = "terminal exited without enterable OpenCode session"
                    break
                if time.monotonic() >= deadline:
                    # Terminal stayed up. Report it when no harness child appeared.
                    if _live_pid(proc.pid, pid_alive):
                        return True, proc.pid, ""
                    last_err = "terminal exited without enterable OpenCode session"
                    break
                time.sleep(0.05)
        except OSError as e:
            last_err = str(e)[:300]
            continue
        except Exception as e:
            last_err = str(e)[:300]
            continue
    return False, 0, last_err or "terminal cannot start"
