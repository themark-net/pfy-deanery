# Handoff: backlog-catalog-1030 (2026-10-30 PT)

Status: stopped. Exit: lane empty. Branch `bot/backlog-catalog-1030`, worktree `~/DEVELOP/pfy-mentat/tmp/backlog-catalog-1030`, cut from `origin/main` `85c53dc`. Not merged. No Feature GO. Catalog HOLD 70-75 unchanged.

Cloud Grok only. MVP-3 pid 1695827 was alive at the stop (2026-10-30 20:56 PT), so this run did not call a local model, did not run a full suite, and did not run pregate.

pregate not run: host busy.

## Gate

Docs, eval, and test-only changes. Gate: pregate, then Reviewer. No Tester gate for product runtime. Run pregate only when pid 1695827 is gone, `ollama ps` lists no model, `pgrep -f 'Runner[.]Worker'` is empty, and no other pregate is running. Use `nice -n 19` under `flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock`.

GitHub issues were not closed, reopened, commented on, or created. Numbers below are notes only.

## Items done

| Item | Content commit | Result |
|------|----------------|--------|
| Hermes bake-off status | `e78d371` (log `99217af`) | Landed on main. Entry 134. Re-run NO-WIN. Flag default-off. No new entry. |
| T-0095 Stage 0 | `a632b23` (log `d8c08e3`) | Entries 150-152, FAIL / I0. No install. Issue #10 was already closed on the July stub. TODO done. |
| Issue #25 Laguna | `ce075bd` (log `c903141`) | Smoke note only. Pull box stays open. T-0062 stays todo. Issue stays open. |
| Issues #26, #27, #28 | already on main `7197200`, `57bc3d0` (log `f27d8a6`) | Pattern docs. No npm install. No evolve. Not a skip. |
| T-0005 stage facts | `0715085` (log `d422790`) | Kolibri-1 deterministic fields only. Stage stays I0. `--apply` not run. TODO stays doing. |
| T-0002 synthesis | `4e2cf80` (log `ab2c8b2`) | 2026-10-30 rollup, no new scores. Issue #16 stays closed. TODO done. |
| Docs hygiene | `a9d3987` (log `f5e50fd`) | T-0070 and T-0074 moved to done. Dead ADR-0017 links retargeted. ADR not written. |

## Skipped

One lane skip, commit `f78b3cb`. Twenty-one x-intake handoffs were read. The known gaps and recommended next steps need a local model, an install, Docker, Mark, or a new receipt design. Entry 148 and 149 code was left for Run A. Entry 149's date line was not edited. The 149 next step is a Reviewer delta gate, then a fast-forward of main. This run does not open a PR and does not merge.

Not taken, because they do not fit this lane:

- T-0005 promotion. OQ-0003. A stage letter is a human choice. The card facts were copied. The row stays doing.
- T-0091. The row still says TTS and VoIP are open. Issue #2 was not treated as done.
- T-0110. The row says partial. Issue #76 was not reopened.
- T-0062 and issue #25 lab. Hardware and a local model. Catalog text only.
- T-0094, T-0016, T-0081, T-0043, T-0064. Local TTS, a large-model lab, a cage smoke, or parked env work.
- T-0046. Re-evaluating AgenC is ADR-0010 territory.
- T-0124. Run A owns `pfylib/attach.py`.

## Test evidence

Targeted and niced. MVP-3 stayed alive, so no `unittest discover`, no `scripts/pregate.sh`, no `make eval-*`.

| Module | Result |
|--------|--------|
| `tests.test_voice_stage0_ref` `tests.test_catalog_entry_numbers` `tests.test_catalog_stage_eval` | 8 tests OK (T-0095) |
| `tests.test_laguna_smoke_note` | 1 test OK |
| `tests.test_catalog_stage_eval` `tests.test_catalog_entry_numbers` | 6 tests OK (after the Kolibri facts) |
| `tests.test_scoring_rollup` | 1 test OK |
| `tests.test_docs_hygiene` | 2 tests OK. Every relative link under `docs/` resolved. |

In-memory checks, disk left as committed: a Stage-0 PASS on entry 150 fails the Pipecat test; a dropped ATG receipt fails the stage test; `overall: 99` in the October rollup matches the score ban.

## How each change fails and how we recover

| Change | How it fails | Recovery |
|--------|--------------|----------|
| Hermes status line | A later reader treats `bot/hermes-eval` as still ahead of main | Re-check `git log origin/main..origin/bot/hermes-eval`. Do not add entry 150 for Hermes. |
| Entries 150-152 | A receipt says Stage-0 PASS while the quickstart still needs cloud keys or has no git pin | Put the receipt back to FAIL / I0. Do not add a TOOLS.md row. |
| Laguna note | The pull checkbox is marked done, or a weight file is tracked | Uncheck the box. Do not commit weights. T-0062 stays open until a real receipt. |
| Kolibri facts and the apply guard | `catalog_stage_eval.py --apply` replaces ATG `measured-probe` and drops `receipt:pipelines/dogfood/atg-compile/receipt-live-qwen36-35b.json` and `pipelines/dogfood/harness2-local/receipt.json` | Restore the cards from git. Do not re-apply. Update the test only after `evidence_for` keeps those paths. |
| T-0002 rollup | The October section assigns an overall number, or names a `tools.json` version other than the file | Delete the number. Point the version phrase at `data/tools.json`. Do not rescore the July table. |
| Docs links and eval rows | A `docs/` link 404s, or T-0070 / T-0074 is doing again while `7197200:scripts/eval-auto.sh` or `c0d9072:examples/eval-harness/tasks/013-stage-card/score.py` is missing | Fix the link, or move the row back only when the file is gone. Do not add `docs/adr/0017-*.md` only to satisfy a link. |
| Early CLI exit | The loop stops before the handoff | Relaunch from the last run-log line. |
| MVP-3 skew | A heavy job runs while pid 1695827 is alive | Stay on targeted niced tests. |
| Run A collision | This branch edits smoke_148, smoke_149, smoke_131_133, their tests, `scripts/pregate.sh`, `scripts/pfy_build_local.py`, `pfylib/attach.py`, or entry 149's date line | Leave those paths to Run A. |

## OQ drafts (not filed as OQ numbers)

ADR-0017 is cited from `pfylib` and `docs/design/pfy-launcher.md`, and there is no `docs/adr/0017-*.md`. This run did not write it. The two module links now point at the design note that already says the file is missing.

runx, from `docs/automation/x-intake-2026-10-11-handoff.md`: a skill-run receipt with subject, authority, execution boundary, exit, seal, and a verify step that refuses placeholder signatures. That is a new receipt schema. It needs an ADR before any file format.

`scripts/catalog_stage_eval.py --apply` keeps stage letters and still overwrites newer cards. On this tree it would set ATG potential back to `ambiguous`, drop the live ATG and harness2 receipts, lower the ATG tier ceiling from I2 to I1, and stamp `last_updated` back to 2026-09-25. A safe apply has to keep those receipt paths. The script was not changed and was not run.

## Next step

Reviewer on `bot/backlog-catalog-1030`, then pregate when the host is idle, as in the gate section. Do not merge from this run.

After that, the open catalog work is a human stage promotion (T-0005, OQ-0003), the Laguna lab (T-0062, issue #25) when no timing trial is loaded, and the two OQ drafts above. `docs/PENDING-HANDOFF.md` still has a 2026-10-19 bullet that says the Hermes branch lands on main. The current status is `docs/eval/HERMES-EVAL-HANDOFF.md`.
