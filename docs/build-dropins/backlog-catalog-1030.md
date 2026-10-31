# Backlog loop 2026-10-30 (Run B): Hermes status, then the catalog and docs backlog

Branch `bot/backlog-catalog-1030`, worktree `~/DEVELOP/pfy-mentat/tmp/backlog-catalog-1030`, cut from `origin/main` 85c53dc. Run log: `docs/ops/RUN-LOG-backlog-catalog-1030.md`. Decisions: `docs/ops/AUTONOMOUS-DECISIONS-backlog-catalog-1030.md`. Handoff: `docs/ops/HANDOFF-backlog-catalog-1030.md`.

A parallel run (Run A, branch `bot/pfy-followups-1030`) owns code follow-ups: `examples/x-intake-local/smoke_148.py`, `smoke_149.py`, `smoke_131_133.py`, their tests, `scripts/pregate.sh`, `scripts/pfy_build_local.py`, `pfylib/attach.py` and the MVP-2 docs. Do not edit those files. Entry 149's date line is also Run A's.

## Hard rules (pre-authorized, no questions)

- Follow the orchestrator skill (`~/.grok/skills/orchestrator/SKILL.md`) and the repo skills `prefer-behavior-and-fail-recover-tests`, `repo-handoff-doc-required` and `write-loop-exits-first`. Do not ask questions. Decide conservatively, log each decision as one line in this run's decisions file, and keep going.
- Work only in this worktree. Never touch Mark's main checkout `~/DEVELOP/pfy-mentat`, any other worktree under `tmp/` (especially `tmp/mvp3`, the live MVP-3 trial), or Mark's processes. Never stop or signal a process you did not start.
- No sudo and no system changes. Do not use `/tmp`: scratch goes under this worktree's `tmp/` (gitignored), with `TMPDIR` pointed there.
- Never print, log or commit secret values. Do not read `~/.grok/auth.json`.
- Push only this run's own `bot/` branch, as new commits. No force push, no PR, no merge to main, no tags.
- No em dashes or en dashes in anything you write.
- Every item gets a behavior or fail/recover test when code changes (no tautological unit tests), a commit, and a push. Push after every item.
- Do not end your turn while any process you started is still running. Run long commands in the foreground with bounded waits, or detached with a pid file and a foreground poll loop.

## Cloud only: protect the MVP-3 timing trial

MVP-3 run 2 (pid 1695827, worktree `tmp/mvp3`) is timing a local model trial on this host. MVP-3 is "busy" while that pid is alive or `ollama ps` lists any model.

- Never load or call a local model: no `ollama run/pull/serve`, no requests to `127.0.0.1:11434` or any local inference server, no `pfy build --local`, no local-model evals. Use cloud Grok only.
- While MVP-3 is busy, run only targeted test modules (`nice -n 19 python3 -m unittest tests.test_x`). No full `unittest discover`, no `scripts/pregate.sh`, no `make eval-*`, no builds, no docker.
- When MVP-3 is not busy, a full suite is allowed: run it with `nice -n 19` under `flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock`, so two runs never run heavy jobs at once.
- Pregate: at most once, at the end, and only if MVP-3 is not busy, the GitHub runner is idle (`pgrep -f 'Runner[.]Worker'` is empty), and no other pregate is running. Use the same flock. Otherwise record "pregate not run: host busy" in the handoff.

## Loop and exits (write these into the run log before any work)

This is a long orchestrator loop, not a single slice. After the listed items, keep taking the next item from this run's backlog lane in `docs/TODO.md` until an exit fires.

1. Wall cap: 8 hours from launch, or Sunday 2026-11-01 18:00 PT (PST, 2026-11-02T02:00Z), whichever comes first. Check before every item. Leave 20 minutes to write the handoff.
2. Lane empty: no item left that fits the lane and these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped. Record and stop.
4. Host pressure: MemAvailable under 32 GiB, or load over 2x cores for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on `origin/main` before your change. Record them and skip that area, but do not stop.

Skip items that need a local model, special hardware, a human decision (an open OQ), a secret, or Mark's hands. Log each skip with a reason. Do not invent architecture: if an item needs an ADR, write it up as an OQ draft in the handoff and skip it.

## Per item

1. Read the item and its linked docs. Check it is not already done on `origin/main`.
2. Make the smallest change that closes it, plus behavior or fail/recover tests where code changes.
3. Run the affected test modules (targeted, niced).
4. Commit with a clear message naming the item. Push. Append one line to the run log: `item | commit | tests | result`.
5. Update a `docs/TODO.md` row status only for an item you fully closed, in the same commit.

## Finish (on any exit)

Write or update this run's handoff in `docs/ops/`: items done with SHAs, items skipped and why, test evidence, how each change fails and recovers, the gate needed (Tester plus Reviewer for runtime changes; pregate plus Reviewer for docs, eval or test-only changes), and the next step. Finish the run log with a final `state:` line. Commit and push. Do not merge.

## Catalog rules

- Catalog HOLD 70-75 stays unchanged. No Feature GO. Do not rescore existing entries unless the item says so.
- New catalog entries take the next free number under `sources/entries/` on this branch (149 is the last on main, so start at 150) and follow the format of the newest entries (for example `149-mempalace.md`, `148-skillspector.md`): dated with an explicit time zone, sources cited, no invented scores.
- No local installs or local-model smokes while MVP-3 is busy. Research is by reading upstream docs and repos (web fetch is fine).
- Do not close, reopen, comment on, or create GitHub issues. Note issue numbers in the handoff instead.

## Listed item 1: Hermes bake-off status (docs only)

Findings from the dispatcher, verify them before writing:

- `bot/hermes-eval` (old tip 9b4c8f9, final tip 24fe672) is fully contained in `origin/main`. The catalog entry was already renumbered 131 to 134 (`73ff535`, because #304 took 131) and lives at `sources/entries/134-hermes-agent.md`. No new renumber is needed; do not create a 150 copy.
- `bot/hermes-wire` (7281cd1), with the meta-tools-off re-run (NO-WIN, 2026-10-21) and the default-off `PFY_BOT_INTERFACE=hermes` flag, is also in `origin/main`.

Write a short dated status line (PT) at the top of `docs/eval/HERMES-EVAL-HANDOFF.md`: landed on main, entry 134, re-run done, flag default-off, nothing left on these branches. Fix any remaining text there that says "lands on main after the gate" or "do not merge from this run" so it reads as historical. Commit and push.

## Backlog lane (after the listed item)

Take items in this order, skipping per the rules:

1. Catalog and research rows in `docs/TODO.md`: T-0095 (Catalog Stage 0 for Pipecat, LiveKit, freeapp, reference only, no install); the catalog follow-ups #25 Laguna, #26 asm, #27 claude-codex-settings, #28 MUE-X (check each is not already done on main; Laguna's local model DoD T-0062 is hardware-gated, so only the catalog text); T-0005 (apply integration stages to more handoff cards, using `scripts/catalog_stage_eval.py`; never auto-promote a stage letter); T-0002 (aggregate synthesis) if it can be done from existing entries without new scores.
2. X-intake follow-ups named in `docs/automation/x-intake-*-handoff.md` and `docs/ops/HANDOFF-x-intake-*.md` "Known gaps" or "Next step" sections that are docs or catalog work, except entry 148 and 149 code (Run A).
3. Docs hygiene: stale "doing" rows in `docs/TODO.md` whose work is shown done on main (move them to Done with the evidence SHA), dead links in `docs/`, em dashes in files you otherwise touch.

Tests: run the catalog and structural test modules that cover what you changed (for example `tests.test_catalog*`, the smoke_contract lint pieces), targeted and niced. When MVP-3 is not busy, one full suite under the flock before the handoff.
