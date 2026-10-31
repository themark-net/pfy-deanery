# RUN-LOG backlog-catalog-1030

START: 2026-10-30 20:29 PT. Launch commit `ceb3294` at 2026-10-30 20:28:46 PT.
Worktree: `/home/mark/DEVELOP/pfy-mentat/tmp/backlog-catalog-1030`
Branch: `bot/backlog-catalog-1030` (cut from `origin/main` `85c53dc`)
HEAD at loop start: `ceb3294` (drop-in and handoff only).
Loop type: goal. Cloud Grok only. Run B catalog and docs lane.

## Exits (written before item work)

Binding exits from the drop-in. Check before every item. Leave 20 minutes to write the handoff.

1. Wall cap: 8 hours from launch, so 2026-10-31 04:28 PT, or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z), whichever comes first. Stop starting a new item at 2026-10-31 04:08 PT.
2. Lane empty: no item left that fits the catalog and docs lane and these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped. Record and stop.
4. Host pressure: MemAvailable under 32 GiB, or load over 2x cores (64) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on `origin/main` before the change. Record them and skip that area. Do not stop the loop.

Eight-exit card (agent-loops), mapped onto the five above:

```text
LOOP EXIT CARD
Goal: catalog and docs lane closed or skipped with a reason, handoff written, branch pushed, not merged.
1 Goal met:                  lane empty or every remaining row skipped; handoff committed
2 Turn cap:                  one implementation pass per item; a second identical failure is exit 3
3 Budget cap:                cloud Grok only; no local model, no install, no spend outside this session
4 Wall clock:                2026-10-31 04:28 PT (handoff buffer from 04:08 PT)
5 No-progress:               same failure twice, or 3 skips in a row
6 Human interrupt:           user stop; no question stops the loop
7 Error threshold:           same failure twice (stricter than 3)
8 External event:            item already on origin/main, or it needs an open OQ, a secret, hardware, or a local model
```

Host at start: MemAvailable 45.8 GiB. Load about 5.4 on 32 cores. MVP-3 pid 1695827 alive and `ollama ps` lists `qwen3.6:35b`, so MVP-3 is busy. Targeted niced tests only. No full suite, no pregate, no docker, no local model call.

## Plan

Overview: Verify the Hermes bake-off is already on main and say so, then close catalog and docs backlog rows that can be done from upstream docs and existing entries. No Run A files. No Feature GO. HOLD 70-75 stays.

Phases:
- hermes-status | docs/eval/HERMES-EVAL-HANDOFF.md | dated landing line, historical gate wording, commit and push | none | general
- t0095-stage0 | sources/entries next free numbers, docs/ops/voice-stack-stage0-ref.md, TODO | Stage 0 reference receipts for Pipecat, LiveKit, freeapp, no install | hermes-status | general
- catalog-followups | entries and ops notes for #25 Laguna, #26 asm, #27 claude-codex-settings, #28 MUE-X | catalog text only; skip if origin/main already has it; T-0062 stays hardware-gated | hermes-status | general
- t0005-stages | handoff cards via scripts/catalog_stage_eval.py | more cards filled from evidence; stage letter never auto-promoted | catalog-followups | general
- t0002-synthesis | sources/aggregates or the synthesis doc the TODO names | synthesis from existing entries, no new scores | t0005-stages | general
- x-intake-docs | docs/automation and docs/ops x-intake handoffs, not smoke_148/149 code | docs or catalog gaps closed or skipped | hermes-status | general
- docs-hygiene | docs/TODO.md doing rows, dead links in docs/ | stale doing rows moved with the evidence SHA | the catalog phases (shared TODO.md) | general
- handoff | docs/ops/HANDOFF-backlog-catalog-1030.md, this log | final state line, commit, push, no merge | all | general

Risks:
- Shared TODO.md and this log, so one writer. A parallel implementer would race. Project-map writes only gitignored `.project-map/`.
- MVP-3 is busy, so no full suite until the pid is dead and `ollama ps` is empty, and then only under `flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock`.
- Run A owns smoke_148.py, smoke_149.py, smoke_131_133.py, their tests, scripts/pregate.sh, scripts/pfy_build_local.py, pfylib/attach.py, MVP-2 docs, and entry 149's date line.
- An item that needs an ADR becomes an OQ draft in the handoff and is skipped.

## Items

Format: `item | commit | tests | result`

hermes-status | e78d371 | docs only; no test module reads this handoff; ancestry of 24fe672 and 7281cd1 confirmed on origin/main | landed
t0095-stage0 | a632b23 | nice -n 19 python3 -m unittest tests.test_voice_stage0_ref tests.test_catalog_entry_numbers tests.test_catalog_stage_eval: 8 tests OK in 0.195s; RED check flipped entry 150 to Stage-0 PASS and test_pipecat_fail_holds failed | FAIL/I0 receipts, no install
issue-25-laguna | ce075bd | nice -n 19 python3 -m unittest tests.test_laguna_smoke_note: 1 test OK; MVP-3 alive, MemAvailable 44.7 GiB | catalog note only, T-0062 still todo, issue stays open
issue-26-asm | 7197200 | no new tests; docs/ops/asm-skill-manager.md and make smoke-asm already on origin/main | pattern-only, HD #37, no npm install
issue-27-claude-codex | 57bc3d0 | no new tests; docs/ops/claude-codex-quality-hooks.md already on origin/main | pattern extract, no Claude runtime
issue-28-mue-x | 7197200 | no new tests; docs/ops/mue-x-patterns.md and T-0072 already done | pattern only, no evolve
t0005-stages | 0715085 | nice -n 19 python3 -m unittest tests.test_catalog_stage_eval tests.test_catalog_entry_numbers: 6 tests OK in 0.081s; in-memory RED (dropped ATG receipt) would fail; disk potential stays measured-probe; MVP-3 alive, MemAvailable 53.7 GiB | Kolibri-1 facts only, stage I0, --apply not run, T-0005 stays doing
t0002-synthesis | 4e2cf80 | nice -n 19 python3 -m unittest tests.test_scoring_rollup: 1 test OK in 0.001s; in-memory RED overall: 99 matches the ban; clean section does not | no new scores, TODO done, issue #16 stays closed
x-intake-docs | skipped | 21 handoffs read; no code change | no docs-only gap; local model, install, Mark, Docker, or a receipt ADR (runx)
docs-hygiene | a9d3987 | nice -n 19 python3 -m unittest tests.test_docs_hygiene: 2 tests OK in 0.052s; link scan clean; MVP-3 alive, MemAvailable 53.4 GiB | T-0070 and T-0074 moved to done; ADR-0017 not written; T-0091 and T-0110 left open

state: lane empty at 2026-10-30 20:56 PT. Last item commit f5e50fd. MVP-3 pid 1695827 alive. MemAvailable 53.2 GiB. Load 4.59 on 32 cores. pregate not run: host busy. No full suite. Not merged.
