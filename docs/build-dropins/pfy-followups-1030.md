# pfy follow-ups 2026-10-30 (Run A): reviewer follow-ups, then the MVP-adjacent backlog

Branch `bot/pfy-followups-1030`, worktree `~/DEVELOP/pfy-mentat/tmp/pfy-followups-1030`, cut from `origin/main` 85c53dc. Run log: `docs/ops/RUN-LOG-pfy-followups-1030.md`. Decisions: `docs/ops/AUTONOMOUS-DECISIONS-pfy-followups-1030.md`. Handoff: `docs/ops/HANDOFF-pfy-followups-1030.md`.

A parallel run (Run B, branch `bot/backlog-catalog-1030`) owns catalog, X-intake and docs-only backlog items. Stay out of `sources/entries/`, `TOOLS.md` and `data/tools.json` so the two runs do not collide.

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

## Listed items (do these first, in order)

### 1. MVP-2 Reviewer follow-ups (docs only)

The Reviewer verdict is at `tmp/verdict-mvp2-85c53dc.md` in this worktree (gitignored, read it; do not commit it). Its "Follow-ups (non-blocking)" items:

1. Name the landing default in `docs/ops/HANDOFF-mvp2-trial.md` (around line 36, "Mark chooses what to land") and in `docs/build-dropins/pfy-local-build-mvp2-trial.md` (around line 19). The default is: prefer the cloud (C) patches; never land the local t4/t5 patches. This matches `eval/mvp2/REPORT.md` (around line 65). Keep it as an owner override, not a question.
2. Add a one-line note at the top of `docs/ops/HANDOFF-mvp2-trial.md` and `docs/ops/RUN-LOG-mvp2-trial.md` saying the "Do not merge to main" and `bot/mvp2-trial` branch text is historical and the report now lives on main. Do the same for the MVP-2 row in `docs/TODO.md` ("done on `bot/mvp2-trial`").
3. Fix the dead link to `docs/build-dropins/pfy-local-build-mvp3.md` in the handoff Landing section: keep the link and add a note that the file lands with MVP-3 (branch `bot/mvp3-review-retry`). Do not copy the MVP-3 file onto this branch.
4. Prove-red has no standalone receipt (it is backed only by the local `tests_before` field; cloud receipts lack it). Document this gap honestly in the MVP-2 handoff "Known gaps". Do not fabricate a receipt.
5. "none reported a truncated prompt" (REPORT around line 51) and "Weekly Build percent was not readable" have no receipt field. Reword both in the report and handoff so they say they are operator observations with no receipt field.

### 2. Entry 149 (MemPalace) follow-ups (code and tests)

Files: `examples/x-intake-local/smoke_149.py`, `tests/test_x_intake_smoke_149.py`, `sources/entries/149-mempalace.md`, `docs/ops/HANDOFF-x-intake-149-b2.md`. Entry 148 shares some code (`smoke_148.py`, `smoke_131_133.py`); change shared behavior there only if needed and keep its tests green.

1. Add a behavior test for `version_of()` (the version probe): a real fake binary on PATH that prints a version, plus a broken one (non-zero exit, garbage output), asserting what the smoke does with each.
2. Make `test_version_pin_exit_2` assert the reason text in the receipt, not only the exit code.
3. Remove the `PFY_SMOKE_REAL_HOME_BIND` hook from the production code path. Tests that need a writable real HOME must get it through a test-only seam (for example a fixture-only parameter or a test harness wrapper), not an env var the production smoke reads. Keep the real-HOME tests meaningful and record how the change fails and recovers.
4. Guard the `/proc` and `/dev/shm` binds: only bind them when they exist and are usable, and fail closed (exit 2 with a reason) when a required bind cannot be made. Never add an unsandboxed fallback. Add tests for both paths.
5. Give the entry date in `sources/entries/149-mempalace.md` an explicit time zone if any date still lacks one. (This is the single allowed edit under `sources/entries/`.)
6. Add a test where a fake `bwrap` exits 1: the smoke must fail closed with exit 2 and a reason, never run unsandboxed.
7. Fix the mutation table count in the 149 handoff so it matches the actual mutants and kills. Recompute; do not guess.

Tests: `tests/test_x_intake_smoke_149.py` and `tests/test_x_intake_smoke_148.py` (and `131_133` if touched), targeted and niced. Tests needing real bwrap must keep the existing `needs_bwrap` style skip so GitHub's no-bwrap runner still passes.

### 3. CI: workflow image-pin lint with real YAML parsing

`scripts/pregate.sh` around line 385 ("== workflow image pin ==") checks that GitHub-hosted jobs pin `ubuntu-24.04` with text matching. Replace it with real YAML parsing (a small Python helper under `scripts/`, called from pregate): load every `.github/workflows/*.yml`, walk `jobs.*.runs-on` (string, list and matrix-expression forms), and fail when a GitHub-hosted job uses `ubuntu-latest` or an unpinned image. Self-hosted label lists are allowed.

- Check if PyYAML is importable on nimo and in the CI image (verify whether the `ubuntu-24.04` image ships python3-yaml; do not assume). If it may be missing, fail closed with a clear message rather than silently passing, and record the decision.
- Behavior tests in `tests/` with fixture workflow files: pinned passes; `ubuntu-latest` fails; a list containing `ubuntu-latest` fails; a matrix expression that resolves to `ubuntu-latest` fails; self-hosted passes; malformed YAML fails closed. Test the real helper and the pregate lint call (`scripts/pregate.sh --only lint` may run while MVP-3 is busy only if it is light; if it runs the full suite, do not).

## Backlog lane (after the listed items)

Take items from `docs/TODO.md` in this order, skipping per the rules above:

1. MVP-adjacent: `pfy build --local` hardening that does not need a model run (receipts, flags, error text, tests), loose ends named in `docs/ops/HANDOFF-pfy-local-build-mvp.md` and `docs/ops/HANDOFF-mvp2-trial.md` "not done" lists. Do not touch `scripts/pfy_build_local.py` areas that `bot/mvp3-review-retry` changed (the review-and-retry loop); read `git diff origin/main origin/bot/mvp3-review-retry -- scripts/pfy_build_local.py` first and stay clear of those hunks.
2. Active design/coding rows: T-0124 (fold OpenCode enterable behind `pfylib/attach.py`), T-0070 (structural eval scorers), T-0081 (OpenCode-in-cage smoke, only if it needs no local model and no docker while MVP-3 is busy), T-0074 (only parts that need no local model).
3. Open follow-ups named in recent `docs/ops/HANDOFF-*.md` "Known gaps" or "Next step" sections that are code or test work (not catalog).

Leave catalog, X-intake entries, TOOLS.md and `data/tools.json` to Run B.
