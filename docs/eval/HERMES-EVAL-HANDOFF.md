# Handoff: Hermes Agent bake-off (2026-10-19)

**Status (2026-10-30 PT):** Landed on main. Entry 134 (`sources/entries/134-hermes-agent.md`, renumber 131 to 134 is `73ff535`). Meta-tools-off re-run done (NO-WIN, 2026-10-21). `PFY_BOT_INTERFACE=hermes` stays default-off (opencode unless that flag is set). `origin/bot/hermes-eval` (final tip `24fe672`, earlier tip `9b4c8f9`) and `origin/bot/hermes-wire` (`7281cd1`) have no commits outside `origin/main`. Nothing left on these branches. Not a Feature GO. Catalog HOLD 70-75 unchanged. Sections below are the 2026-10-19 and 2026-10-21 record.

## Wire run status (2026-10-20, branch `bot/hermes-wire`)

Live status for the meta-tools-off re-run and the bot-interface flag. The sections below stay the 2026-10-19 eval record. Run log: [RUN-LOG-hermes-wire.md](../ops/RUN-LOG-hermes-wire.md).

| Prerequisite | Status |
|---|---|
| R1 process boundary wording | done in this branch (Hermes is one subprocess per task, library call inside it) |
| R2 "much faster" caveat | done; link to the not-like-for-like note |
| R3 sub-second TTFT | done; whole-second stamps are rejected |
| 1. Scorer mutants / aggregate, wilson, percentile | done; 20 mutants restored after RED (see run log) |
| 2. Fetch/chain oracle comparison | done; live fixture must match the label or the task fails closed |
| 3. `labels_written` not hardcoded | done; newest source stamp `2026-10-06T16:01:36Z` |
| 4. Run start time at the start | done; `meta.started` is stamped before the closing `ollama ps` |
| 5. Choice oracle rejects scattershot | done; distinct choices fail even if one matches the label |
| 6. Rescore from git | done; `run.py --rescore` reads the committed JSON only |
| 7. Tool-name mismatch | done; `mcp__bakeoff__*` and `bakeoff_*` score as the short name |
| Re-run (meta tools off, matched thinking) | done 2026-10-21. Receipt `pipelines/dogfood/hermes-bakeoff/results-rerun.json`. NO-WIN: 26/27 vs 26/27, valid 36/36 vs 36/36, p50 7.011s vs 7.191s, TTFT p50 4.877s vs 5.364s, peak 239.8 MiB vs 1.03 GiB, meta calls 0. Thinking off on both arms. `tool_search` off. Requested num_ctx 65536, observed context_length 262144. Does not block the flag |
| `scripts/pfy` Hermes flag | done. `PFY_BOT_INTERFACE=hermes` opts in. Default remains opencode. Plan `docs/plans/hermes-bot-interface.md`. Not a Feature GO. Catalog HOLD 70-75 unchanged |

**Branch:** `bot/hermes-eval` (worktree `/home/mark/DEVELOP/pfy-mentat/tmp/hermes-eval`), cut from `origin/main` @ `b36234b` (#303). This paragraph was written while the branch was still ahead of the gate. It has since landed on `main` (final tip `24fe672` is contained in `origin/main`; see the status line). The plan at the time was a fast-forward after the Tester and Reviewer gate (no-PR flow); `origin/main` was merged in on 2026-10-20. Not a Feature GO. No production wiring. Catalog HOLD 70-75 unchanged.

**History on this branch:** entry `03cfbec`, bake-off `b48d634`, handoff `9b4c8f9`, merge of `origin/main` @ `aed526d` `09b1c16` (no rebase), renumber 131 to 134 `73ff535`, founder decision `02dd0af`, then the Reviewer docs fixes on top. The gated tip was the SHA in the gate request. That fast-forward happened: the tip is on `main`.

## What shipped vs open

- **A shipped.** `sources/entries/134-hermes-agent.md` (first written as 131; renumbered on 2026-10-20 because #304, `a393a91`, took 131). TOOLS.md notes only. No new `data/tools.json` row. Scores not invented.
- **B shipped.** Harness `examples/hermes-bakeoff/`, tasks `data/decision-gates/hermes-bakeoff.tasks.v0.json` (27, labels before the run), results `pipelines/dogfood/hermes-bakeoff/results.json`, write-up [hermes-vs-current.md](hermes-vs-current.md).
- **C skipped.** Verdict is NO-WIN. No `docs/plans/hermes-bot-interface.md`. What would have to change for a re-run is in the eval doc.
- **D this file.** Pointer at the top of `docs/PENDING-HANDOFF.md`. Row for `hermes-eval.md` in `docs/build-dropins/README.md`.

## Verdict

**NO-WIN** on `qwen3.6:35b` (Ollama 0.30.8).

| | Hermes `AIAgent.run_conversation` `ddabd383` | `opencode run` 1.18.32 |
|---|---:|---:|
| Task success | 26/27 = 96.30% (Wilson 81.7-99.3%) | 25/27 = 92.59% (Wilson 76.6-97.9%) |
| Valid tool-call rate | 82.61% (38/46) | 97.83% (45/46) |
| Narrate rate | 0 | 0 |
| p50 latency | 8.75s | 47.38s |
| Agent peak RSS | 221 MiB | 1.04 GiB |

Failed the +10 pp success bar (+3.70 pp) and the valid-rate bar (−15.2 pp). Intervals overlap. Hermes was faster and lighter. A first scoring pass that counted Hermes `tool_search` / `tool_call` envelopes as invalid attempts said 42% valid; the published rate excludes those meta calls. NO-WIN either way. One scored pass. No second model pass.

Requested `num_ctx` 65536 after Hermes refused 32768. `ollama ps` `context_length` stayed 262144 for both arms.

## Founder decision (2026-10-20)

Mark lands this eval as-is and **chooses Hermes as the bot interface (wiring pending)**, for speed and RAM: p50 latency 8.75s vs 47.38s, agent peak RSS 221 MiB vs 1.04 GiB. This is a product choice made despite the NO-WIN verdict, which stands: task success missed the +10 pp bar (26/27 vs 25/27, +3.70 pp, intervals overlap) and the valid tool-call rate was 15.2 pp worse (82.61% vs 97.83%). The verdict and the numbers above are not changed.

**The speed and RAM rows are not like-for-like.** Hermes ran with reasoning off (`reasoning_effort: "none"` in its config and `reasoning_config={"enabled": False, ...}`, `examples/hermes-bakeoff/hermes_arm.py:47,136`), and the opencode arm did not turn thinking off. `opencode run` pays a CLI cold start on every task. The Hermes arm is also one process per task: `run.py` launches `hermes_arm.py` through `subprocess` (`_arm_cmd` and `_run_sampled` in `examples/hermes-bakeoff/run.py`). Inside that process the driver is the library call `AIAgent.run_conversation`, not the Hermes CLI. That process still pays Python startup, the Hermes import, and a child MCP server, and it does not stay up across tasks. The RSS row is the agent process only and leaves out the model itself (about 23 GB for `qwen3.6:35b`, the same for both arms). So part of the latency gap is thinking and process start, not the interface.

- **Follow-up:** re-run the bake-off with Hermes `tool_search`, `tool_describe` and the `tool_call` batch tool turned off, so the model emits MCP calls directly, and recompute the valid tool-call rate (re-run item 1 in [hermes-vs-current.md](hermes-vs-current.md)). The re-run must use the same thinking setting on both arms and record it.
  Prerequisites to fix before that re-run (listed only; not done in this change):
  1. Stronger scoring tests: 14 of 20 mutants of the scorer survive, and `aggregate`, `wilson` and `percentile` have no tests.
  2. The fetch/chain oracle comparison.
  3. `labels_written` is hardcoded at `examples/hermes-bakeoff/make_tasks.py:273`.
  4. The run start time is recorded at the end of the run (`examples/hermes-bakeoff/run.py:417`).
  5. The choice oracle accepts scattershot answers.
  6. Make the rescore re-runnable from git (no dependence on `./tmp` transcripts).
  7. The tool-name mismatch between `mcp__bakeoff__*` and `bakeoff_*`.
- **Not in this change:** no `scripts/pfy` or `pfylib/` wiring and no catalog rescore. Wiring Hermes in as the bot interface is a separate change with its own gate.

## Reproduce

```bash
python3 -m unittest tests.test_hermes_bakeoff
python3 examples/hermes-bakeoff/run.py --check --base-url http://127.0.0.1:9
python3 examples/hermes-bakeoff/run.py --live --skip-ctx-probe --num-ctx 65536 \
  --work ./tmp/bakeoff/full1 \
  --out pipelines/dogfood/hermes-bakeoff/results.json
```

Offline: unittest 9 OK. pytest `-m "not live"` 9 passed, 1 deselected (`PytestUnknownMarkWarning` on `live`). The live mark stays deselected unless `HERMES_BAKEOFF_LIVE=1`.

## Isolation

- `~/.hermes` untouched: **yes**. Snapshot before install vs after cleanup, 153 paths, diff empty. This run did not read Mark's `~/.hermes` or `~/.local/bin/hermes`. `HERMES_HOME` was `./tmp/hermes-home`. `HERMES_IGNORE_USER_CONFIG` was left unset because the value `1` also skips that home's `config.yaml`.
- `~/.config/opencode` mtime stayed 2026-04-30. opencode XDG homes were under `./tmp/opencode-xdg` and per-task dirs under `./tmp/bakeoff/full1`.
- No Hermes gateway, dashboard, API server, or cron. No leftover `hermes_arm`, `opencode run`, or `mcp_server.py` from this run.
- `openclaw-gateway.service`: **inactive**, **disabled**. Not started.
- `qwen3.6:35b` was not in `ollama ps` at session start. This eval loaded it. The scored run did **not** unload it: it found the model already resident from the probes, so `results.json` records `model_unloaded: false` and `model_left_loaded: true`, which is true for that run. The session's cleanup step after the run (outside `run.py`, so not in `results.json`) sent `keep_alive: 0`, and `ollama ps` was empty afterwards; it was also empty on 2026-10-20 at 03:31 and 11:19 PT. No `qwen3.6-hermes-eval-*` tag was created.
- `./tmp/` left in place (git-ignored), including the pin checkout and per-task transcripts.

## Blockers

None that stopped the ship. Driver bugs fixed before the scored pass, each once: Ollama tag check was calling `/v1/api/tags`; relative `--out` was written after `chdir` into the checkout; the MCP server spoke Content-Length and this pin's SDK reads newline JSON. No identical failure three times.

## Next

2026-10-21: the re-run receipt and the default-off `./pfy bot` flag were on `bot/hermes-wire`. See the status table above and [hermes-vs-current.md](hermes-vs-current.md). At that date, Tester and Reviewer still gated the merge (no-PR flow: on a double PASS, main would be fast-forwarded to the gated SHA), and that run said not to merge from the run. Both tips are now in `origin/main` (status line, 2026-10-30 PT). Do not rescore Hermes in the catalog. The 2026-10-19 instruction not to wire `scripts/pfy` was superseded by the flag, which stays off unless `PFY_BOT_INTERFACE=hermes`.
