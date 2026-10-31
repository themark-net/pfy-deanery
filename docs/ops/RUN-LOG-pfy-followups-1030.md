# RUN-LOG pfy-followups-1030 (Run A)

Start: 2026-10-30T20:28:44-07:00 (drop-in commit `53aae59`; outer pid 1794517).
Worktree: `/home/mark/DEVELOP/pfy-mentat/tmp/pfy-followups-1030`
Branch: `bot/pfy-followups-1030`
Base: `origin/main` `85c53dc70e7db905fbfb4951c87bbae70ca2d6c2`
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-pfy-followups-1030.md`
Handoff: `docs/ops/HANDOFF-pfy-followups-1030.md`
Lane: reviewer follow-ups, then MVP-adjacent code. Run B (`bot/backlog-catalog-1030`) owns catalog, X-intake entries, `TOOLS.md`, and `data/tools.json`. This run may edit `sources/entries/149-mempalace.md` once (time zone only).

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria): listed items 1-3 closed, then backlog lane items closed until an exit fires. Each code change has a behavior or fail/recover test. Each item is committed and pushed on bot/pfy-followups-1030.
1 Goal met:          lane empty, or every taken item is done or skipped with a reason, and the handoff is pushed
2 Turn cap:          not a fixed iteration count; stop when the wall cap or no-progress exit fires
3 Budget cap:        cloud Grok only; no local model; no spend beyond this session
4 Wall clock:        8 hours from 2026-10-30T20:28:44-07:00, so stop new items at 2026-10-31T04:08:44-07:00 (20 minute handoff buffer). Hard stop 2026-10-31T04:28:44-07:00. Also stop at 2026-11-02T02:00:00Z if that is sooner (it is not).
5 No progress:       the same failure twice with no new information, or 3 items in a row skipped
6 Human interrupt:   user stop. No questions. Conservative decision, one line in the decisions file, keep going.
7 Error threshold:   same as exit 5 (same failure twice, or 3 skips in a row)
8 External event:    item already done on origin/main: skip that item. Red tests on origin/main: record and skip that area. Do not stop the run for a red base.
Loop type:           goal, with a wall-clock cap (time bound on a goal loop)
Human gate:          no merge, no PR. Tester plus Reviewer for runtime changes. Pregate plus Reviewer for docs, eval, or test-only changes.
```

Operator exits (same card, checked before every item):

1. Wall cap: 8 hours from launch, or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00:00Z), whichever comes first. Leave 20 minutes to write the handoff.
2. Lane empty: no item left that fits the lane and these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped.
4. Host pressure: MemAvailable under 32 GiB, or load over 2x cores (64) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on origin/main before the change. Record them and skip that area. Do not stop the run.

## Plan

Overview: Close the MVP-2 reviewer follow-ups (docs), then the MemPalace smoke 149 follow-ups (code and tests), then replace the workflow image-pin text match with real YAML parsing. After that, take MVP-adjacent `pfy build --local` hardening that does not run a model, then T-0124, T-0070, T-0081, T-0074, then code or test follow-ups named in recent handoffs. Stay off Run B files and off the MVP-3 review-and-retry hunks in `scripts/pfy_build_local.py`.

Phases:
- item-1-mvp2-reviewer-docs | `docs/ops/HANDOFF-mvp2-trial.md`, `docs/ops/RUN-LOG-mvp2-trial.md`, `docs/build-dropins/pfy-local-build-mvp2-trial.md`, `eval/mvp2/REPORT.md`, `docs/TODO.md` | landing default named, historical branch note, dead MVP-3 link noted, prove-red gap documented, two observations labeled as having no receipt field | none | lead
- item-2-smoke-149 | `examples/x-intake-local/smoke_149.py`, `tests/test_x_intake_smoke_149.py`, `sources/entries/149-mempalace.md`, `docs/ops/HANDOFF-x-intake-149-b2.md`, shared smoke only if required | version probe, receipt reason, no production real-HOME env hook, proc/shm bind guard, time zone, bwrap exit 1 fails closed, mutation table recomputed. Tests: `tests.test_x_intake_smoke_149` and `tests.test_x_intake_smoke_148` | item-1 (same branch, push order) | lead
- item-3-workflow-image-pin | `scripts/` helper, `scripts/pregate.sh`, `tests/` | real YAML walk of `jobs.*.runs-on`; ubuntu-latest and unpinned images fail; self-hosted passes; missing PyYAML fails closed | item-2 | lead
- backlog | `docs/TODO.md` lane order, avoiding `scripts/pfy_build_local.py` hunks that `origin/bot/mvp3-review-retry` changed | each closed item has a test, a commit, and a push | item-3 | lead
- handoff | `docs/ops/HANDOFF-pfy-followups-1030.md`, this log | SHAs, skips, evidence, fail/recover, gate, next step, final `state:` line | all prior | lead

Risks:
- MVP-3 pid 1695827 is alive and `ollama ps` lists `qwen3.6:35b`, so the host is busy. Mitigation: targeted `nice -n 19 python3 -m unittest tests.test_x` only. No discover, no pregate, no docker, no builds, no local model calls.
- Two runs share the host. Mitigation: heavy jobs only under `flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock` when MVP-3 is idle. This run does not start heavy jobs while MVP-3 is busy.
- Shared branch. Mitigation: the lead commits and pushes each item itself. No implementation sub-agent on this checkout.
- Image-pin lint may lack PyYAML. Mitigation: fail closed with a clear message if the import is missing. Do not treat a missing parser as a pass.

## Host at plan time (2026-10-31T03:29:28Z)

- MemAvailable: 50889576 kB (about 48.5 GiB). Floor is 32 GiB. Not pressured.
- Load: 5.70, 5.35, 4.63. Cores: 32. Threshold: 64. Not pressured.
- MVP-3: busy (pid 1695827 alive; `ollama ps` lists `qwen3.6:35b`).

## Items

(one line per finished item: `item | commit | tests | result`)

item-1-mvp2-reviewer-docs | 6b63b4d | none (docs only; MVP-3 busy, no pregate) | landing default named, historical note on handoff run log and TODO, MVP-3 link kept with a lands-with-MVP-3 note, prove-red gap in Known gaps, truncated-prompt and weekly-percent labeled as operator observations with no receipt field
item-2-smoke-149 | a1e7a47 | nice -n 19 python3 -m unittest tests.test_x_intake_smoke_149 tests.test_x_intake_smoke_148: 39 OK in 4.312s; PATH=/nonexistent /usr/bin/python3 -m unittest tests.test_x_intake_smoke_149: 25 OK skipped=16 | version probe, pin reason, no production HOME env hook, proc/shm fail closed, bwrap exit 1 fail closed, date 2026-10-25T04:41:28Z, mutations 13 applied 13 killed 0 survived
item-3-workflow-image-pin | 53933b3 | nice -n 19 python3 -m unittest tests.test_workflow_image_pin: 15 OK in 8.380s | YAML walk of runs-on; ubuntu-latest, a list containing it, a matrix that resolves to it, an unpinned image, malformed YAML, a missing runs-on, and a missing PyYAML fail closed; pinned, self-hosted, reusable, and the real workflows pass; pregate --only lint OVERALL=PASS and the lint log contains the helper PASS line
mvp-local-build-loose-ends | skipped | none | origin/bot/mvp3-review-retry rewrites build_local and parse_args; the named gaps are --reap, a model run, or a deliberate known gap
T-0124 | 6c8d00a | nice -n 19 python3 -m unittest tests.test_attach tests.test_registry: 33 OK in 0.061s | OpenCode open path is attach.open_opencode_session; pfy_enterable_162_b.py is a shim; a tools-env pin does not override the probed base; missing binary, a dead terminal, and a failed prove stay FAIL
T-0070 | skipped | none | 013-stage-card scorer and pass/fail fixtures are already on main; run_structural.py already runs them; no next scorer is named
T-0081 | skipped | none | OpenCode-in-cage smoke needs docker; MVP-3 pid 1695827 is alive, so no docker
T-0074 | skipped | none | candidate fallback is already in scripts/eval_auto_candidates.py and tests/test_eval_auto_candidates.py; the rest is make eval-auto, which runs a local model

state: stopped | exit 3 no progress | T-0070, T-0081, and T-0074 skipped in a row after T-0124 | pregate not run: host busy | do not merge
