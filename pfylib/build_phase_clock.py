"""Exclusive wall clock for one cloud build.

A nested phase is not also billed to its parent. Billing both would hide
the gate that runs inside the commit recheck and would rank the wrong
overhead.

Phases: preflight, worktree, agent, gate, review, commit.
"""

from __future__ import annotations

import time

PHASES = ("preflight", "worktree", "agent", "gate", "review", "commit")


class PhaseClock:
    """Monotonic totals. `monotonic` is injectable so a test can script time."""

    def __init__(self, monotonic=None) -> None:
        self._now = monotonic or time.monotonic
        self._t0 = self._now()
        self._totals = {name: 0.0 for name in PHASES}
        # (name, started_or_None). None means a child is running.
        self._stack: list[tuple[str, float | None]] = []

    def phase(self, name: str):
        if name not in self._totals:
            raise KeyError(name)
        return _Phase(self, name)

    def _enter(self, name: str) -> None:
        now = self._now()
        if self._stack:
            parent, started = self._stack[-1]
            if started is not None:
                self._totals[parent] += now - started
            self._stack[-1] = (parent, None)
        self._stack.append((name, now))

    def _leave(self, name: str) -> None:
        now = self._now()
        if not self._stack:
            return
        top, started = self._stack.pop()
        if started is not None and top == name:
            self._totals[top] += now - started
        elif started is not None:
            # Mismatched leave still keeps the time on the frame that ran.
            self._totals[top] += now - started
        if self._stack:
            parent, _paused = self._stack[-1]
            self._stack[-1] = (parent, now)

    def report(self) -> dict[str, float]:
        totals = dict(self._totals)
        if self._stack:
            name, started = self._stack[-1]
            if started is not None:
                totals[name] += self._now() - started
        return {name: round(max(0.0, totals[name]), 3) for name in PHASES}

    def wall_seconds(self) -> float:
        return round(max(0.0, self._now() - self._t0), 3)


class _Phase:
    def __init__(self, clock: PhaseClock, name: str) -> None:
        self._clock = clock
        self._name = name

    def __enter__(self):
        self._clock._enter(self._name)
        return self

    def __exit__(self, *_exc) -> bool:
        self._clock._leave(self._name)
        return False


def install_build_phases(build, clock: PhaseClock, grok_phase) -> None:
    """Time the runner methods that match the six phases.

    `grok_phase(prompt)` returns "agent" or "review". The implement and
    review prompts are different, so the wrapper can bill the right phase
    without a new argument on grok_call.
    """
    if getattr(build, "_phases_installed", False):
        return
    build.phase_clock = clock

    def wrap(method_name: str, phase: str) -> None:
        original = getattr(build, method_name)

        def wrapped(*args, **kwargs):
            with clock.phase(phase):
                return original(*args, **kwargs)

        setattr(build, method_name, wrapped)

    wrap("prepare_worktree", "worktree")
    wrap("gate", "gate")
    wrap("commit_paths", "commit")
    original_grok = build.grok_call

    def grok_wrapped(prompt, *args, **kwargs):
        name = grok_phase(prompt)
        with clock.phase(name):
            return original_grok(prompt, *args, **kwargs)

    build.grok_call = grok_wrapped
    build._phases_installed = True
