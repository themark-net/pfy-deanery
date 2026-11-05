#!/usr/bin/env python3
"""Enterable OpenCode session helpers — cite #162 (a).

Attach must open/focus a usable interactive terminal (not silent sidecar alone).
Launch env must arm/open enterable path or honest SKIP (copy alone insufficient).
"""
from __future__ import annotations

import json
import os
import secrets
import shlex
import shutil
import signal
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


HEADLESS_NAME = "headless-session.name"
HEADLESS_PID = "headless-session.pid"
HEADLESS_HARNESS = "headless-session.harness"
_HEADLESS_FILES = (
    HEADLESS_NAME,
    HEADLESS_PID,
    "headless-session.start",
    HEADLESS_HARNESS,
    "headless-spawn.pid",
)


def _flag_on(env, name) -> bool:
    for source in (env or {}, os.environ):
        val = str(source.get(name) or "").strip().lower()
        if val in ("1", "true", "yes", "on"):
            return True
    return False


def _want_headless(env) -> bool:
    """True for PFY_HEADLESS, or when this environment has no display."""
    if _flag_on(env, "PFY_HEADLESS"):
        return True
    return not _has_display(env or {})


def _state_text(state, name) -> str:
    try:
        return (Path(state) / name).read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""


def read_headless_session(state) -> dict:
    """Name, pid, and harness recorded for the headless session, if any."""
    pid = 0
    try:
        pid = int(_state_text(state, HEADLESS_PID) or 0)
    except ValueError:
        pid = 0
    return {
        "name": _state_text(state, HEADLESS_NAME),
        "pid": pid,
        "harness": _state_text(state, HEADLESS_HARNESS),
    }


def _clear_headless_files(state) -> None:
    state = Path(state)
    for name in _HEADLESS_FILES:
        path = state / name
        try:
            if path.is_file():
                path.unlink()
        except OSError:
            pass


def _clear_pid_files_matching(state, pid) -> None:
    """Unlink pid files that name this pid. Does not signal."""
    try:
        pid_s = str(int(pid))
    except (TypeError, ValueError):
        return
    state = Path(state)
    try:
        entries = list(state.iterdir())
    except OSError:
        return
    for path in entries:
        if not path.is_file() or not path.name.endswith(".pid"):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace").split()
        except OSError:
            continue
        if not text or text[0] != pid_s:
            continue
        try:
            path.unlink()
        except OSError:
            pass
        start = state / pid_start_name(path.name)
        try:
            if start.is_file():
                start.unlink()
        except OSError:
            pass


def _signal_recorded(pid) -> None:
    """SIGTERM one pid. Never a process group, never pid 1."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return
    if pid <= 1 or pid == os.getpid():
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(0.05)
    try:
        os.kill(pid, signal.SIGKILL)
    except OSError:
        pass


def _ppid(pid: int) -> int:
    fields = _stat_fields(pid)
    if len(fields) < 2 or not str(fields[1]).isdigit():
        return 0
    return int(fields[1])


def _direct_child_ancestor(pid) -> int:
    """Ancestor of pid whose parent is this process, including pid itself. Else 0."""
    me = os.getpid()
    try:
        cur = int(pid)
    except (TypeError, ValueError):
        return 0
    seen = set()
    while cur > 1 and cur not in seen and len(seen) < 32:
        seen.add(cur)
        parent = _ppid(cur)
        if parent == me:
            return cur
        if parent <= 1:
            return 0
        cur = parent
    return 0


def _still_under(pid, ancestor) -> bool:
    """True when pid is ancestor or a descendant of it. Does not signal."""
    try:
        cur = int(pid)
        ancestor = int(ancestor)
    except (TypeError, ValueError):
        return False
    if cur <= 1 or ancestor <= 1:
        return False
    seen = set()
    while cur > 1 and cur not in seen and len(seen) < 32:
        if cur == ancestor:
            return True
        seen.add(cur)
        cur = _ppid(cur)
    return False


def _headless_record_matches(state, pid, start) -> bool:
    """True when the headless files name this pid and the start ticks we saved."""
    try:
        recorded_pid = int(_state_text(state, HEADLESS_PID) or 0)
    except ValueError:
        return False
    if recorded_pid != int(pid) or not start:
        return False
    path = Path(state) / pid_start_name(HEADLESS_PID)
    try:
        recorded = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return False
    return recorded == start


def _clear_spawn_record(state, pid, start) -> None:
    """Unlink pid files that name this spawn. Does not signal."""
    matches = _headless_record_matches(state, pid, start)
    _clear_pid_files_matching(state, pid)
    if matches:
        _clear_headless_files(state)


def reap_failed_spawn(state, pid, start, pid_alive) -> None:
    """Stop a terminal this call just spawned after models-and-smoke failed.

    Signals the pid only when `start` is still its live start time and the pid
    is a descendant of this process or the headless process this call recorded.
    Descendants of that spawn are signalled too. A mismatch, a foreign pid,
    and pid <= 1 are not signalled. Session and pid files for this spawn are
    cleared. Recovery: fix the model or engine, then launch again.
    """
    try:
        pid = int(pid or 0)
    except (TypeError, ValueError):
        pid = 0
    start = str(start or "").strip()
    if pid <= 1 or pid == os.getpid() or not start:
        return
    recorded = _headless_record_matches(state, pid, start)
    live = proc_starttime(pid)
    still = bool(live) and live == start and _live_pid(pid, pid_alive)
    root = _direct_child_ancestor(pid) if still else 0
    if root <= 1 and not recorded:
        return
    if still:
        signal_root = root if root > 1 else pid
        if signal_root <= 1 or signal_root == os.getpid():
            signal_root = pid
        kids = [
            kid for kid in _descendants(signal_root)
            if kid > 1 and kid != os.getpid() and kid != pid
        ]
        for kid in reversed(kids):
            if _still_under(kid, signal_root):
                _signal_recorded(kid)
        if signal_root != pid and _ppid(signal_root) == os.getpid():
            _signal_recorded(signal_root)
        if proc_starttime(pid) == start and _live_pid(pid, pid_alive):
            _signal_recorded(pid)
        if recorded:
            _stop_private_mux(state, _state_text(state, HEADLESS_NAME))
    _clear_spawn_record(state, pid, start)


def _still_started_at(pid, start, pid_alive) -> bool:
    """True when pid is alive and its start ticks are still the ones we saved."""
    try:
        pid = int(pid or 0)
    except (TypeError, ValueError):
        return False
    if pid <= 1 or not start or not _live_pid(pid, pid_alive):
        return False
    return proc_starttime(pid) == start


def _owned_headless(state, pid_alive):
    """Pid, name, and start ticks when the recorded headless process is still ours."""
    info = read_headless_session(state)
    try:
        pid = int(info.get("pid") or 0)
    except (TypeError, ValueError):
        pid = 0
    name = info.get("name") or ""
    if pid <= 1 or not name or not same_recorded_process(state, HEADLESS_PID, pid, pid_alive):
        return 0, "", ""
    return pid, name, proc_starttime(pid)


def _snapshot_headless_files(state) -> dict:
    state = Path(state)
    snap = {}
    for name in _HEADLESS_FILES:
        path = state / name
        try:
            if path.is_file():
                snap[name] = path.read_bytes()
        except OSError:
            continue
    return snap


def _restore_headless_files(state, snap) -> None:
    _clear_headless_files(state)
    state = Path(state)
    for name, data in (snap or {}).items():
        try:
            (state / name).write_bytes(data)
        except OSError:
            pass


def _pids_looking_like(bin_path, pid_alive) -> set:
    """Live pids that already look like bin_path. A deny-list, not a search to adopt."""
    found = set()
    proc = Path("/proc")
    if not proc.is_dir():
        return found
    try:
        names = [entry.name for entry in proc.iterdir()]
    except OSError:
        return found
    for name in names:
        if not name.isdigit():
            continue
        pid = int(name)
        if _live_pid(pid, pid_alive) and _looks_like_bin(pid, bin_path):
            found.add(pid)
    return found


def _write_runner(state, bin_path, pid_file) -> Path:
    runner = Path(state) / "headless-run"
    body = "#!/bin/sh\necho $$ > %s\nexec %s\n" % (
        shlex.quote(str(pid_file)),
        shlex.quote(str(bin_path)),
    )
    runner.write_text(body, encoding="utf-8")
    runner.chmod(0o755)
    return runner


def _popen_logged(argv, cwd, env, log_path, new_session) -> subprocess.Popen:
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as handle:
        handle.write(("spawn: %s\n" % " ".join(argv)).encode("utf-8", "replace"))
        return subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=new_session,
        )


def _accept_new_pid(pid, bin_path, pid_alive, before) -> int:
    """Return pid when it is a new live harness. 0 if it is foreign or already gone."""
    try:
        pid = int(pid or 0)
    except (TypeError, ValueError):
        return 0
    if pid <= 1 or pid in before:
        return 0
    if not (_live_pid(pid, pid_alive) and _looks_like_bin(pid, bin_path)):
        return 0
    time.sleep(0.15)
    if pid in before or not (_live_pid(pid, pid_alive) and _looks_like_bin(pid, bin_path)):
        return 0
    real = resolve_enterable_pid(bin_path, pid, pid_alive)
    try:
        real = int(real or 0)
    except (TypeError, ValueError):
        return 0
    if real <= 1 or real in before or not _looks_like_bin(real, bin_path):
        return 0
    if not _live_pid(real, pid_alive):
        return 0
    return real


def _poll_direct(proc, bin_path, pid_alive, before) -> int:
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline:
        accepted = _accept_new_pid(proc.pid, bin_path, pid_alive, before)
        if accepted:
            return accepted
        if not _live_pid(proc.pid, pid_alive):
            return 0
        time.sleep(0.05)
    return 0


def _poll_pidfile(proc, pid_file, bin_path, pid_alive, before) -> int:
    deadline = time.monotonic() + 3.0
    started = time.monotonic()
    while time.monotonic() < deadline:
        candidate = 0
        try:
            candidate = int(Path(pid_file).read_text(encoding="utf-8", errors="replace").strip())
        except (OSError, ValueError):
            candidate = 0
        if candidate and candidate in before:
            return 0
        if candidate:
            accepted = _accept_new_pid(candidate, bin_path, pid_alive, before)
            if accepted:
                return accepted
            if not _live_pid(candidate, pid_alive):
                return 0
        if proc.poll() is not None and not candidate and time.monotonic() > started + 1.0:
            return 0
        time.sleep(0.05)
    return 0


def _spawned_by_us(pid, bin_path, runner) -> bool:
    """True for the harness, or for the runner script this call wrote. Not a process-table search."""
    if _looks_like_bin(pid, bin_path):
        return True
    runner_s = str(runner or "")
    if not runner_s:
        return False
    return any(runner_s in token for token in _argv(pid))


def _abandon(proc, pid_file, before, pid_alive, bin_path, runner) -> None:
    """Stop a spawn this call started. A pid from the deny-list is left alone."""
    candidate = 0
    try:
        candidate = int(Path(pid_file).read_text(encoding="utf-8", errors="replace").strip())
    except (OSError, ValueError):
        candidate = 0
    if (
        candidate
        and candidate not in before
        and _live_pid(candidate, pid_alive)
        and _spawned_by_us(candidate, bin_path, runner)
    ):
        _signal_recorded(candidate)
    if proc is None:
        return
    try:
        if proc.poll() is None and proc.pid > 1 and proc.pid not in before:
            os.kill(proc.pid, signal.SIGTERM)
    except OSError:
        return


def _record_headless(state, name, harness, pid, pid_alive) -> bool:
    state = Path(state)
    try:
        state.mkdir(parents=True, exist_ok=True)
        (state / HEADLESS_NAME).write_text(name + "\n", encoding="utf-8")
        (state / HEADLESS_HARNESS).write_text(harness + "\n", encoding="utf-8")
        (state / HEADLESS_PID).write_text(str(int(pid)) + "\n", encoding="utf-8")
    except OSError:
        return False
    write_recorded_start(state, HEADLESS_PID, int(pid))
    return same_recorded_process(state, HEADLESS_PID, int(pid), pid_alive)


def _stop_private_mux(state, name) -> None:
    """Best-effort stop of the private tmux socket or screen dir. Ignores stubs."""
    if not name:
        return
    state = Path(state)
    tmux = _which("tmux")
    sock = state / "headless-tmux.sock"
    if tmux and sock.exists():
        try:
            subprocess.run(
                [tmux, "-S", str(sock), "kill-session", "-t", name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    screen = _which("screen")
    screen_dir = state / "screen"
    if screen and screen_dir.is_dir():
        env = os.environ.copy()
        env["SCREENDIR"] = str(screen_dir)
        try:
            subprocess.run(
                [screen, "-S", name, "-X", "quit"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=2,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass


def _spawn_headless(bin_path, cwd, env, log_path, pid_alive):
    """Detach bin_path under tmux, else screen, else setsid. Returns (ok, pid, error)."""
    env = dict(env or {})
    env.pop("TMUX", None)
    env.pop("STY", None)
    log_path = Path(log_path)
    state = log_path.parent
    state.mkdir(parents=True, exist_ok=True)
    harness = Path(str(bin_path)).name or "harness"
    name = "pfy-%s-%s" % (harness, secrets.token_hex(3))
    pid_file = state / "headless-spawn.pid"
    try:
        if pid_file.is_file():
            pid_file.unlink()
    except OSError:
        pass
    runner = _write_runner(state, bin_path, pid_file)
    previous_pid, previous_name, previous_start = _owned_headless(state, pid_alive)
    saved = _snapshot_headless_files(state)
    before = _pids_looking_like(bin_path, pid_alive)
    tmux = _which("tmux")
    screen = _which("screen")
    proc = None
    try:
        if tmux:
            proc = _popen_logged(
                [tmux, "-S", str(state / "headless-tmux.sock"), "new-session", "-d", "-s", name, str(runner)],
                cwd, env, log_path, True,
            )
            pid = _poll_pidfile(proc, pid_file, bin_path, pid_alive, before)
        elif screen:
            screen_dir = state / "screen"
            screen_dir.mkdir(mode=0o700, exist_ok=True)
            os.chmod(screen_dir, 0o700)
            screen_env = dict(env)
            screen_env["SCREENDIR"] = str(screen_dir)
            proc = _popen_logged(
                [screen, "-dmS", name, str(runner)],
                cwd, screen_env, log_path, True,
            )
            pid = _poll_pidfile(proc, pid_file, bin_path, pid_alive, before)
        else:
            setsid_bin = _which("setsid")
            if setsid_bin:
                proc = _popen_logged([setsid_bin, str(runner)], cwd, env, log_path, False)
            else:
                proc = _popen_logged([str(runner)], cwd, env, log_path, True)
            pid = _poll_direct(proc, bin_path, pid_alive, before)
    except OSError as exc:
        _abandon(proc, pid_file, before, pid_alive, bin_path, runner)
        _stop_private_mux(state, name)
        _restore_headless_files(state, saved)
        return False, 0, str(exc)[:300]
    if not pid:
        _abandon(proc, pid_file, before, pid_alive, bin_path, runner)
        _stop_private_mux(state, name)
        _restore_headless_files(state, saved)
        return False, 0, "headless session exited"
    if not _record_headless(state, name, harness, pid, pid_alive):
        _signal_recorded(pid)
        _stop_private_mux(state, name)
        _restore_headless_files(state, saved)
        return False, 0, "headless session exited"
    if (
        previous_pid
        and previous_pid != int(pid)
        and previous_name
        and previous_name != name
        and _still_started_at(previous_pid, previous_start, pid_alive)
    ):
        _signal_recorded(previous_pid)
        _stop_private_mux(state, previous_name)
    return True, pid, ""


def headless_status(state, pid_alive=None) -> dict:
    """Report the recorded headless session when that process is still alive."""
    info = read_headless_session(state)
    pid = int(info.get("pid") or 0)
    if pid > 0 and same_recorded_process(state, HEADLESS_PID, pid, pid_alive):
        name = info.get("name") or ""
        harness = info.get("harness") or ""
        return {
            "ok": True,
            "live": "READY",
            "session": name,
            "pid": pid,
            "harness": harness,
            "copy": "headless session %s pid %s harness %s" % (name, pid, harness),
        }
    return {
        "ok": False,
        "live": "FAIL",
        "session": "",
        "pid": 0,
        "harness": "",
        "copy": "FAIL launch status -- no headless session",
    }


def headless_stop(state, pid_alive=None) -> dict:
    """Signal the recorded pid only when its start time still matches.

    A reused pid number is not signalled. The headless record is cleared either way.
    """
    info = read_headless_session(state)
    pid = int(info.get("pid") or 0)
    name = info.get("name") or ""
    owned = pid > 0 and same_recorded_process(state, HEADLESS_PID, pid, pid_alive)
    if owned:
        _signal_recorded(pid)
        _stop_private_mux(state, name)
        _clear_pid_files_matching(state, pid)
    _clear_headless_files(state)
    if not owned:
        return {
            "ok": False,
            "live": "FAIL",
            "session": "",
            "pid": 0,
            "harness": "",
            "stopped": False,
            "copy": "FAIL launch stop -- no headless session",
        }
    return {
        "ok": True,
        "live": "STOPPED",
        "session": name,
        "pid": pid,
        "harness": info.get("harness") or "",
        "stopped": True,
        "copy": "stopped %s pid %s" % (name, pid),
    }


def _cli_pid_alive(pid) -> bool:
    try:
        os.kill(int(pid), 0)
    except OSError:
        return False
    return True


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    state = Path(os.environ.get("PFY_STATE_DIR") or (Path.home() / ".pfy-mentat"))
    cmd = args[0] if args else ""
    if cmd == "--status":
        result = headless_status(state, _cli_pid_alive)
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    if cmd == "--stop":
        result = headless_stop(state, _cli_pid_alive)
        print(json.dumps(result))
        return 0 if result.get("ok") else 2
    print("usage: pfy_enterable_162_a.py --status|--stop", file=sys.stderr)
    return 2


def spawn_terminal_opencode(bin_path: str, cwd: str, env: dict, log_path: Path, pid_alive) -> tuple:
    """Spawn a native terminal running the harness. Returns (ok, pid, error).

    The pid is the terminal this call spawned, or a descendant of it. A harness
    that was already running is not adopted. A terminal that exits with no
    harness child is "terminal exited". With PFY_HEADLESS or no display, detach
    under tmux, screen, or setsid instead of a GUI terminal.
    """
    cwd = str(cwd)
    bin_path = str(bin_path)
    env = env or {}
    if _want_headless(env):
        return _spawn_headless(bin_path, cwd, env, log_path, pid_alive)
    last_err = "no terminal"
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


if __name__ == "__main__":
    raise SystemExit(main())
