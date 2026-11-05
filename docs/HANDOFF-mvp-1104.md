# Handoff: pfy-mentat MVP (2026-11-04)

## What the MVP is

Sources: README "Simple path", Epic #53 success line, issue #307, docs/ops/simple-launch.md.

1. On a clone, `./pfy setup && ./pfy status && ./pfy` works for Grok plus local inference.
2. Bare `./pfy` opens the native operator window. It never execs a harness into that window and never starts an engine daemon unless the operator opts in.
3. Launch session (`./pfy launch`, or the window's Launch session button, same backend) applies the enabled modules and opens an enterable TUI of the chosen harness against the live local engine. The session it reports is one it started. Otherwise it FAILs with a reason and a next step.
4. `./pfy build "<task>"` is the daily cloud build. It landed before today (see docs/ops/MVP-DOD-WALKTHROUGH.md) and was not changed here.

## Gaps found on nimo at 8c9388c (all reproduced by running the app)

| Gap | Observed | Fixed in |
|-----|----------|----------|
| G1 | Launch smoke used the first listed model (qwen3.6:35b, a reasoning model) with max_tokens 32, so content was empty and every launch FAILed "smoke empty completion". | 484c55f |
| G2 | Launch adopted an already-running grok TUI that it did not start (the operator's own session) and wrote that pid to sidecar-grok.pid and grok-terminal.pid, so a later stop could signal it. | 484c55f |
| G3 | From a fresh state, `./pfy launch` FAILed "incomplete (lane, toolsets, harness)" until four wizard commands were run. | 7025fbd |
| G4 | #307: bare `./pfy` started `ollama serve` in the background with no prompt. | 7025fbd |
| G5 | No behavior test drove `./pfy launch` end to end. | 484c55f, 7025fbd |

Catalog check: sources/entries 066 to 153 were read for anything that closes G1 to G5. None does. All five were bugs in pfy's own launch code, so no catalog entry was pulled in.

## What landed on main

- 484c55f Launch owns the pid it spawned, and smoke accepts a reasoning reply. Adds tests/test_launch_session_e2e.py.
- 7025fbd Launch fills wizard defaults and bare pfy does not start an engine. Adds tests/test_launch_defaults_e2e.py and tests/test_bare_pfy_no_daemon.py.
- Evidence: full suite (see the progress notes below), pregate PASS, eval-structural run 41876025945 on 7025fbd (it contains 484c55f).
- Real run on nimo at 7025fbd, fresh PFY_STATE_DIR: `./pfy launch` filled "lane local, toolsets bare, harness grok", the smoke passed on qwen3.6:35b (field content), and it spawned a new xterm running grok whose pid was recorded. The operator's own grok was not touched.

Merge rule used: Grok Build wrote each change, ran the tests, and reviewed its own diff in the same session. No Tester or Reviewer bot. Main was fast-forwarded after the suite, pregate and CI were green.

## How to run it

```bash
cd ~/DEVELOP/pfy-mentat && git pull --ff-only
./pfy status          # engine and harness table
./pfy launch          # fills defaults, smokes the local model, opens a terminal with grok
./pfy                 # native operator window; Launch session button does the same thing
```

Choose another harness or model: `./pfy launch harness opencode`, `PFY_OLLAMA_MODEL=qwen3-coder:30b ./pfy launch`. Start an engine from the bare command only on purpose: `PFY_START_ENGINE=1 ./pfy` or `./pfy --start-engine`.

## Still open

- A smoke failure after the terminal spawned leaves that terminal open (it is ours, so it is safe, but it is not reaped).
- With no DISPLAY, `./pfy launch` FAILs "no DISPLAY" by design. A tmux fallback for SSH use is not built.
- The Tauri window is not built on nimo; the webkit or tk window is used. tk selftest passes.
- #309 and #305 follow-ups are unchanged and not MVP blockers.
