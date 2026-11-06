# Handoff: headless bot use (2026-11-05)

How a bot launches a pfy session with no display, checks it, stops it, and runs the daily cloud build. The feature commits below are on main. This note does not change those commands.

Prior MVP note: [HANDOFF-mvp-1104.md](HANDOFF-mvp-1104.md).

## Commands a bot runs

Launch, status, and stop talk to the session this launch recorded. They do not adopt or signal a process the launch did not start. Set `PFY_STATE_DIR` when the bot must not share the operator state. The default is `~/.pfy-mentat`.

```bash
./pfy launch --headless
./pfy launch status
./pfy launch stop
```

`./pfy launch --headless` exports `PFY_HEADLESS=1` and runs the same Launch session as `./pfy launch` (`scripts/pfy-board.py --launch`). The harness is detached instead of opened in a GUI terminal. Pass the flag. On macOS the display check is always true, so a bare `./pfy launch` stays on the GUI path there. On Linux, `./pfy launch` with both `DISPLAY` and `WAYLAND_DISPLAY` unset takes the headless path without the flag. With either display variable set, and without the flag, launch keeps the GUI terminal path.

Detach order, first match on `PATH`:

1. `tmux`, on a private socket `$PFY_STATE_DIR/headless-tmux.sock` (`new-session -d`). The caller's `TMUX` and `STY` are dropped.
2. Else `screen`, with `SCREENDIR=$PFY_STATE_DIR/screen` (mode 0700) and `-dmS`.
3. Else `setsid` of the harness runner. That path sends the harness stdout and stderr to `$PFY_STATE_DIR/sidecar-<session id>.log` (grok writes `sidecar-grok.log`). If `setsid` is absent, the runner is started in a new session instead. tmux and screen keep the session output in the multiplexer. Every path appends a `spawn:` line to that log.

Checked on nimo on 2026-11-05: `tmux` is not on `PATH`. `/usr/bin/screen` and `/usr/bin/setsid` are, so launch uses screen. Do not install tmux for this path.

The session name is `pfy-<harness>-<6 hex chars>`. Files under `$PFY_STATE_DIR`: `headless-session.name`, `headless-session.pid`, `headless-session.harness`, and `headless-session.start` when `/proc` start ticks can be read. Launch does not start an engine daemon. The local engine must already be ready. A missing engine FAILs. Next step: `Launch env or ./pfy up`.

A second `./pfy launch --headless` while that recorded process is still the same one, on the same engine base, reuses it. It does not start a second harness. A different live engine base starts a new session and then stops the previous owned headless pid when its start ticks still match. A models-and-smoke FAIL on a reuse leaves the live session up. A models-and-smoke FAIL after a new spawn stops only that spawn when its start ticks still match, or a descendant of that spawn, clears the pid files, and returns FAIL with the smoke reason and the same next step.

Each command prints one JSON object. Exit 0 when `ok` is true, exit 2 otherwise.

`./pfy launch status` reports the record only when that pid is alive and the start ticks still match. Copy: `headless session <name> pid <pid> harness <harness>`. Otherwise exit 2 and `FAIL launch status -- no headless session`. Status does not signal and does not delete the record, live or stale.

`./pfy launch stop` signals that pid only when the start ticks still match. It clears the headless files either way. Exit 0 copy: `stopped <name> pid <pid>`. A reused pid number is not signalled. Exit 2 copy: `FAIL launch stop -- no headless session`. That failure has already cleared the record.

On success the launch JSON has `headless` true and `session` set to the recorded name, along with `pid` and `harness`.

## Daily headless build

The cloud build command was not changed by the headless launch commits. A bot runs:

```bash
./pfy build "<task>"
```

That is the daily headless cloud build: a worktree, cloud Grok, the gate, review, and a commit on `cloud/<slug>-<stamp>`. Nothing is pushed. There is no `--headless` flag on `build`. Operator card: [QUICKSTART-pfy-build.md](QUICKSTART-pfy-build.md) and [ops/pfy-build-daily.md](ops/pfy-build-daily.md). Where those disagree with `./pfy build --help` on the default repo, trust the help text.

## What landed

Both commits are on main.

- `343daf1dd2924117a63bcea4ce4e334c3b806dd8` (`343daf1`) Launch headless sessions without DISPLAY for bot use. `./pfy launch --headless`, or Linux `./pfy launch` when `DISPLAY` and `WAYLAND_DISPLAY` are unset, detaches the harness under tmux, else screen, else setsid. Status and stop cover only the session this launch recorded. A foreign process is not adopted or signalled. GUI launch with a display and without the flag is unchanged. Test: `tests/test_launch_headless_e2e.py`.
- `2067877529a787f8cd36a14538fba44fc7537765` (`2067877`) Reap the launch terminal when smoke fails after spawn. A models-and-smoke FAIL after a new GUI or headless spawn stops only that process when its start time still matches, or a descendant of that spawn, then clears the session pid files and returns FAIL with the smoke reason and next step `Launch env or ./pfy up`. A pretender and an already-recorded live session are left alone.

The 2026-11-04 gaps "no DISPLAY" and "a smoke failure leaves the terminal open" are closed by those two commits.

## Still open

- `./pfy launch status` and `./pfy launch stop` see only the headless record. They do not report or stop a GUI terminal started with a display and without `--headless`.
- Stop sends SIGTERM, waits up to 2 seconds, then SIGKILL that same pid number. The start-time check runs before SIGTERM. A pid number reused in that window can receive SIGKILL. The smoke-failure reap uses the same helper. Do not widen stop to a process group.
- The Tauri operator window is still not built on nimo (`gui/operator/src-tauri/target/{release,debug}/pfy-operator` is absent). Headless launch does not use it. Unchanged from [HANDOFF-mvp-1104.md](HANDOFF-mvp-1104.md): webkit or tk remains the window path.
- Issues #305 and #309 stay as in the 2026-11-04 handoff: not blockers for these commands.
