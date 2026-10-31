# Run log mvp-cloudfix-1031

Lane: extra cloud lane. Harden the daily cloud runner. Branch `bot/mvp-cloudfix-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-cloudfix-1031`. Base `origin/bot/mvp-cloud-1031` at `d94d2b6` (that lane exited LANE EMPTY). This lane owns the cloud runner.

Launch: 2026-10-31T20:30:10Z.
Wall cap: 8 hours from launch, so 2026-11-01T04:30:10Z, or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z), whichever comes first. The 8 hour cap binds first. Leave 20 minutes to write the handoff. No new item after 2026-11-01T04:10:10Z.
Clock check before every item. Host at launch: MemAvailable about 64 GiB, 32 cores, load about 3.5. Pressure line is 16 GiB or load over 64 for 5 minutes.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     Every Functional MVP DoD line and failure-case row is locked by a behavior or fail/recover test on this branch, the inline classifier calls pfylib.build_preflight.classify_cloud_failure, and a gitignored helper the gate imported cannot produce a PASS. Real high findings from the parallel lanes are fixed first when a receipt shows them.
1 Goal met:                  nice -n 19 python3 -m unittest tests.test_pfy_build_cloud tests.test_pfy_build_p is OK after each item. A new assertion fails if the DoD line regresses.
2 Turn cap:                  16 items including the handoff. The agent-loops default of 8 is not the cap. The drop-in says keep taking the next gap until an exit fires.
3 Budget cap:                Cloud Grok only when a finding came from a real run and must be reproduced once. No local model. No --local. Fake grok for tests.
4 Wall clock:                2026-11-01T04:30:10Z, or 2026-11-02T02:00Z, whichever first. Handoff starts 20 minutes earlier (2026-11-01T04:10:10Z).
5 No-progress:               the same failure twice with no new information, or 3 items skipped in a row.
6 Human interrupt:           user says stop. Do not ask questions. Do not merge to main. Push of this bot/ branch is pre-authorized.
7 Error threshold:           3 consecutive same failures, then stop. A red base test is recorded and that area is skipped. It does not by itself stop the lane.
8 External event:            stop a line if origin/bot/mvp-cloud-1031 or origin/main already closed it. Re-read parallel reports with git fetch before every item.
Loop type:                   goal
Human gate:                  no merge, no PR, no tag. Tester plus Reviewer at handoff for runtime changes.
```

Orchestrator clock of about 6 hours does not apply. This drop-in sets the 8 hour cap.

## Exits (drop-in, written before code)

1. Wall cap: the clock above. On this exit, write the handoff and stop.
2. Lane empty: no item left that fits this lane and the drop-in rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped. Record and stop.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores (64) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before this lane's change. Record them and skip that area. Do not stop the lane.

Skip items that need special hardware, a human decision (an open OQ), a secret, or Mark's hands. Log each skip with a reason. An item that needs an ADR is an OQ draft in the handoff, then a skip. Do not invent architecture.

## Plan

Overview: The cloud runner on this base already implements the daily command, the PASS receipt, and the failure table with fake-grok tests. Parallel dogfood, realfail, and sixtask reports have no high findings yet. This lane locks the DoD rows that those tests do not yet pin, switches the classifier to the preflight module, then mirrors the two local G4 holes that can still mint a bad PASS (pathspec magic, gitignored helper the gate imported).

Phases:

- loop-card | `docs/ops/RUN-LOG-mvp-cloudfix-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp-cloudfix-1031.md` | exits and phases are in this file before any product edit | depends on nothing | general
- findings-scan | read-only `git fetch` plus `git show` of dogfood, realfail, sixtask, review-fix | high findings listed, or "none" | loop-card | general
- dod-spent-gate | `tests/test_pfy_build_cloud.py` | default retries, gate stays red, exit 1, reason `tests`, attempts length 3, no branch | findings-scan | general
- dod-sigint | `tests/test_pfy_build_cloud.py` | SIGINT exits 1, reason `interrupted`, grok group dead, no branch | dod-spent-gate | general
- dod-base | `tests/test_pfy_build_cloud.py` | default base is `origin/main` when that ref exists; `--base` selects another ref; caller HEAD stays | dod-sigint | general
- dod-staged-dirty | `tests/test_pfy_build_cloud.py` | a staged caller file stays staged and is absent from the new commit | dod-base | general
- dod-phrases | `tests/test_pfy_build_cloud.py` | each rate-limit phrase exits 4; each auth phrase exits 1 and does not suggest `--local`; rc 0 stays other | dod-staged-dirty | general
- dedupe | merge `origin/bot/mvp-preflight-1031`, then `scripts/pfy_build_cloud.py` calls `classify_cloud_failure` | cloud tests and `tests.test_pfy_build_p` stay green; inline copy is gone | dod-phrases | general
- g4-literal | `scripts/pfy_build_cloud.py`, cloud tests | a reviewed file whose name is pathspec magic is the file that commits | dedupe | general
- g4-recheck | `scripts/pfy_build_cloud.py`, cloud tests | a gitignored helper imported by the gate does not PASS; reason `commit-recheck-failed`; no branch | g4-literal | general
- rescan | same read-only fetches | any new high finding is fixed before the handoff, or recorded as none | g4-recheck | general
- handoff | `docs/ops/HANDOFF-mvp-cloudfix-1031.md`, final `state:` line | committed and pushed, no merge | rescan | general

One workstream. Every phase edits the same runner or its tests, so they run in order. No second editor.

Risks:

- Parallel lanes push new findings mid-run. Mitigation: `git fetch origin` before every item and read reports with `git show`. Do not merge those branches.
- A real grok reproduction could rate-limit. Mitigation: reproduce only a finding that came from a real run, once, on a throwaway clone under this worktree's `tmp/`. Never point `./pfy build` at Mark's checkout.
- Merging preflight could pull docs this lane does not own. Mitigation: merge that branch only (it adds `pfylib/build_preflight.py`, its test, and its own docs). Do not edit `pfylib/build_preflight.py` after the merge.
- Archive recheck could turn a good PASS red. Mitigation: the existing gitignored-extra test stays PASS when the gate does not need the ignored file. Only a helper the fresh tree cannot import fails.

## Item log

Format: `item | commit | tests | result`

- loop-card | 8614547 | docs only | PASS
- sigkill-reap | 6dd9e63 | tests.test_pfy_build_cloud tests.test_pfy_build_p | PASS, 44 tests OK, skipped 1. Before receipt: origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/sigkill-reap/receipt.json (agent_pgid was the dead gate, live grok survived reap). After receipt: tmp/sigkill-after/receipt.json (ABORTED / no-receipt, reap exit 0, grok 1786967 alive after SIGKILL and dead after reap).
- dod-rows | 9a7358f | tests.test_pfy_build_cloud tests.test_pfy_build_p | PASS, 50 tests OK, skipped 1. Spent gate is 3 attempts, SIGINT, origin/main base, staged dirty caller, rate-limit and auth phrases.
- dedupe | 37d2a3a | tests.test_pfy_build_cloud tests.test_pfy_build_p tests.test_build_preflight | PASS, 59 tests OK, skipped 1. Merge 6c22fc7. Inline classifier is gone. A grok line that contains 429, including 4291, is rate-limit.
- f1-new-test | 9f1b6be | tests.test_pfy_build_cloud tests.test_pfy_build_p | PASS, 53 tests OK, skipped 1. Before receipt: origin/bot/mvp-dogfood-1031:eval/mvp-1031/dogfood/02-enterable-test/receipt.json (FAIL tests-tampered, 3 attempts, branch null). After receipt: tmp/f1-after/receipt.json (PASS ok, attempt 1, review accept, commit 0693d66 adds tests/test_added.py, tests/test_keep.py unchanged, pushed false). Before gate exit 1, after gate GATE-OK.
- review-reject | eb13975 | tests.test_pfy_build_cloud tests.test_pfy_build_p | PASS, 54 tests OK, skipped 1. Before receipt: origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/review-reject/receipt.json (PASS ok, review accept, commit 9accbc1 adds danger.sh). After receipt: tmp/danger-after/receipt.json (FAIL review-rejected, 3 attempts, branch null, commit null, pushed false). The gate checked the file text and did not execute it.
- auth-failure | fb71e1e | tests.test_pfy_build_cloud tests.test_pfy_build_p tests.test_build_preflight | PASS, 63 tests OK, skipped 1. Before receipt: origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/auth-failure/receipt.json (FAIL no-change, recovery empty). After receipt: tmp/auth-after/receipt.json (FAIL unauthenticated, recovery tells Mark to run grok once, branch null, empty HOME created no auth.json). Preflight module was not edited.
- redaction | e558bd5 | tests.test_pfy_build_cloud tests.test_pfy_build_p | PASS, 56 tests OK, skipped 1. Before receipt: origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/redaction/receipt.json (PASS ok, planted xai- marker in task and output_tail). After receipt: tmp/redact-after/receipt.json (PASS ok, commit 597ac75, kept.py is value = 1, marker absent, [redacted] present, pushed false).
- g4-literal | 8c57694 | tests.test_pfy_build_cloud tests.test_pfy_build_p | PASS, 57 tests OK, skipped 1. A reviewed file named * commits, and the pyc beside it does not. Not a real-run finding, so no grok repro.
- writable-test | b06981d | tests.test_pfy_build_cloud tests.test_pfy_build_p | PASS, 59 tests OK, skipped 1. Before receipt: origin/bot/mvp-sixtask-1031:eval/mvp-1031/sixtask/t4-timeout-substep/receipt.json (FAIL tests-tampered, 3 attempts, branch null). After receipt: tmp/writable-after/receipt.json (PASS ok, commit 25f9e2a, tests/test_edit.py asserts 1 == 1, tests/test_keep.py unchanged, review accept, pushed false). A base test that is not named still fails.
- g4-recheck | ef0c845 | tests.test_pfy_build_cloud tests.test_pfy_build_p | PASS, 60 tests OK, skipped 1. A commit that imports a gitignored helper is reset and retried; the next attempt can land kept.py with no import. Not a real-run finding, so no grok repro.
- protect-globs | 8a2a73b | tests.test_pfy_build_cloud tests.test_pfy_build_p | PASS, 62 tests OK, skipped 1. A direct pipelines/dogfood/grok-home/token was committed before the glob treated ** as zero directories. After, that path, .env, and a pem are protected-path-changed, and a later attempt that removes them can land kept.py. Not a real-run finding, so no grok repro.
- t5-two-writable | 26b6d05 | tests.test_pfy_build_cloud tests.test_pfy_build_p | PASS, 63 tests OK, skipped 1. Before receipt: origin/bot/mvp-sixtask-1031:eval/mvp-1031/sixtask/t5-receipts-outside-repo/receipt.json (FAIL tests-tampered, 3 attempts, branch null). Same gap as t4. Two named base tests can change and a third still fails, then a restore can land. No second grok repro. The t4 after receipt is tmp/writable-after/receipt.json.
- redact-bearer | 1a4f067 | tests.test_pfy_build_cloud tests.test_pfy_build_p | PASS, 63 tests OK, skipped 1. A bearer value and an API_TOKEN assignment are absent from the receipt. kept.py stays value = 1. Not a real-run finding, so no grok repro.
- default-test-cmd | 469d285 | tests.test_pfy_build_cloud tests.test_pfy_build_p | PASS, 63 tests OK, skipped 1. Dry-run gate.cmd is python3 -m unittest discover -s tests -t . when --test-cmd is omitted. Not a real-run finding, so no grok repro.
- no-push | 61d539a | tests.test_pfy_build_cloud tests.test_pfy_build_p | PASS, 64 tests OK, skipped 1. A PASS against a bare origin leaves ls-remote empty and pushed false. The local cloud/ branch still matches the receipt commit. Not a real-run finding, so no grok repro.

Rescan at 2026-10-31T21:25:20Z: dogfood still only F1. Sixtask t6 PASS, variance t1 and t2 PASS. t4 and t5 remain the writable-test finding already locked here. No new high runner bug.

prior-state: LANE EMPTY | tests: tests.test_pfy_build_cloud tests.test_pfy_build_p, 64 OK, skipped 1, at 61d539a | files: scripts/pfy_build_cloud.py, tests/test_pfy_build_cloud.py | err: none | pregate not run: host busy

## Wave 4 (2026-10-31 15:40 PT)

The earlier lane-empty line is not an exit. Wave 4 resumed at 2026-10-31T22:39:26Z. Same launch clock: no new item after 2026-11-01T04:10:10Z, wall 2026-11-01T04:30:10Z. Host at resume: MemAvailable about 57 GiB, 32 cores, load about 3.7. Runner.Worker pid 3199955 was alive, so pregate stays unrun.

```text
LOOP EXIT CARD (wave 4)
Goal (success criteria):     origin/bot/mvp-integrate-1031 is merged (no rebase). A missing --base is exit 1, reason worktree-failed, with a recovery line, and the caller checkout is unchanged. Every failure reason from classify_cloud_failure (rate-limit, unauthenticated) and every non-PASS runner reason has a non-empty recovery on the receipt. New findings under eval/mvp-1031/*/findings/ on origin/bot/mvp-realfail3-1031 and origin/bot/mvp-sixtask-int-1031 are fixed or the poll has seen none for 60 minutes.
1 Goal met:                  nice -n 19 python3 -m unittest tests.test_pfy_build_cloud tests.test_pfy_build_p is OK after each code item.
2 Turn cap:                  the items below, then the 60 minute findings poll, then the handoff. Not the agent-loops default of 8.
3 Budget cap:                Cloud Grok only. A missing base returns before grok starts, so that repro does not call the model. No local model.
4 Wall clock:                2026-11-01T04:30:10Z, or 2026-11-02T02:00Z, whichever first. Handoff starts 20 minutes earlier (2026-11-01T04:10:10Z).
5 No-progress:               the same failure twice with no new information, or 3 items skipped in a row.
6 Human interrupt:           user says stop. Do not ask questions. Do not merge to main. Push of this bot/ branch is pre-authorized. The integrate merge is pre-authorized.
7 Error threshold:           3 consecutive same failures, then stop. A red base test is recorded and that area is skipped.
8 External event:            stop a line if origin/main already closed it. Poll the two branches every 20 minutes. Stop the poll when no new findings file for 60 minutes.
Loop type:                   goal
Human gate:                  no merge to main, no PR, no tag. Tester plus Reviewer at handoff for runtime changes.
```

## Wave 4 plan

Overview: Merge the integrate branch first so this lane sits on the collected tree. Then lock the realfail2 missing-base FINDING as worktree-failed with a recovery line, then give every failure reason a non-empty recovery (protected-path-changed is the observed empty one). Then poll realfail3 and sixtask-int for new findings files.

Phases:

- wave4-card | this run log and the decisions file | exits are recorded before the merge | depends on nothing | general
- merge-integrate | merge origin/bot/mvp-integrate-1031, never rebase | merge commit, cloud tests still OK | wave4-card | general
- base-missing | scripts/pfy_build_cloud.py, tests/test_pfy_build_cloud.py | missing --base exits 1, receipt reason worktree-failed, recovery tells Mark what to do, caller HEAD and status unchanged, grok not started | merge-integrate | general
- recovery-lines | scripts/pfy_build_cloud.py, tests/test_pfy_build_cloud.py | protected-path-changed recovery is non-empty; a test walks classify_cloud_failure rate-limit and unauthenticated plus every non-PASS runner reason and reads a receipt whose recovery is non-empty. PASS and DRY-RUN stay empty | base-missing | general
- findings-poll | read-only git fetch of origin/bot/mvp-realfail3-1031 and origin/bot/mvp-sixtask-int-1031 every 20 minutes | each new cloud-runner FINDING fixed with a test, or 60 minutes with no new findings file | recovery-lines | general
- handoff | docs/ops/HANDOFF-mvp-cloudfix-1031.md and a final state line | committed and pushed, no merge to main | findings-poll | general

One workstream. The code phases edit the same runner, so they run in order. No second editor.

Risks:

- The integrate merge brings other lanes' files. Mitigation: merge only, then edit only this lane's owned files. Do not rebase.
- A missing base could stay exit 2 if resolve_base still raises UsageError. Mitigation: a behavior test on a temp repo with --base pointing at a ref that is not there, asserted red before the fix.
- Filling recovery could change the DoD rate-limit and auth strings. Mitigation: those two keep the existing exact lines. PASS recovery stays empty.
- realfail3 and sixtask-int had only drop-in commits at 2026-10-31T22:39Z (43cdee4 and 4123dda). Mitigation: poll, do not invent findings.

## Item log (wave 4)

Format: `item | commit | tests | result`

- wave4-card | 848411c | docs only | PASS
- merge-integrate | da65338 | tests.test_pfy_build_cloud tests.test_pfy_build_p | PASS, 64 tests OK, skipped 1. Merge of origin/bot/mvp-integrate-1031, no rebase. Runner source matched this branch. The skipped line is the dogfood module's expected missing-grok message.
- base-missing | 3ee4819 | tests.test_pfy_build_cloud tests.test_pfy_build_p | PASS, 65 tests OK, skipped 1. Before: origin/bot/mvp-realfail2-1031:eval/mvp-1031/realfail2/worktree-failed/ (usage.txt, no receipt, exit 2). After: tmp/base-missing-after/receipt.json (FAIL worktree-failed, exit 1, recovery names the missing ref and tells Mark to fetch or pass --base). Caller HEAD and the dirty file stayed. ./pfy build returned before grok started.
- recovery-lines | 827b4b0 | tests.test_pfy_build_cloud tests.test_pfy_build_p | PASS, 66 tests OK, skipped 1. protected-path-changed names the path. Every terminal failure reason, including classify_cloud_failure rate-limit and unauthenticated, writes a non-empty recovery. other is not a failure. PASS stays empty. Before: origin/bot/mvp-realfail2-1031:eval/mvp-1031/realfail2/protected-paths/receipt.json (recovery empty). No second real grok. The model is not required to write auth.json.
- findings-poll-1 | none | read-only fetch at 22:50Z and 23:10Z | realfail3 and sixtask-int moved, but the findings/ blobs did not. realfail3 published two FINDING files beside the cases: tmp-unwritable and gate-hang. sixtask-int pass1 t1 through t5 are PASS. Those two FINDINGs are in scope.
- tmp-unwritable | 7276eee | tests.test_pfy_build_cloud tests.test_pfy_build_p | PASS, 67 tests OK, skipped 1. Before: origin/bot/mvp-realfail3-1031:eval/mvp-1031/realfail3/tmp-unwritable/receipt.json (runner-crash, recovery empty). After: tmp/tmp-unwritable-after/receipt.json (FAIL worktree-failed, exit 1, recovery tells Mark to make tmp writable). Caller unchanged. Grok was not called. The FINDING asked for an empty recovery. This lane keeps the non-empty line.
