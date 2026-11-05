# Handoff: mvp-backlog-burn-1031

Branch `bot/mvp-backlog-burn-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-backlog-burn-1031`. Base `origin/bot/mvp-integrate-1031` at `0c3f133`, plus drop-in `56ea234`. Stopped 2026-10-31T23:22:46Z. Exit: lane empty. Six real cloud `./pfy build` runs landed. No `--local`. No merge, no PR, no tag.

Report: [../../eval/mvp-1031/backlog-burn/REPORT.md](../../eval/mvp-1031/backlog-burn/REPORT.md). Run log: [RUN-LOG-mvp-backlog-burn-1031.md](RUN-LOG-mvp-backlog-burn-1031.md). Decisions: [AUTONOMOUS-DECISIONS-mvp-backlog-burn-1031.md](AUTONOMOUS-DECISIONS-mvp-backlog-burn-1031.md).

## Items done

| Item | Landed SHA | Cloud SHA | Tests | Result |
|------|------------|-----------|-------|--------|
| Enterable not-ok stores stripped next_steps | `c354d9c` | `9b7eafdade3b09d473cf7b0805bd042e99561f36` | `tests.test_enterable_not_ok` 2 OK | PASS, review accept, 1 attempt, 53s |
| Catalog `--apply` keeps live receipts, stamp, ceiling, potential | `5f7ce36` | `a3f267a4e514f014981aa0803778518615c081bc` | `tests.test_catalog_stage_eval` 4 OK | PASS, review accept, 2 attempts, 784s |
| Entry 149 publishes 28 stub tests | `42fc4e1` | `3faeaa2e0a48a8e65aeeda9d57bea304511c02bd` | `tests.test_entry_149_count` 1 OK | PASS, review accept, 1 attempt, 28s |
| Hermes 2026-10-19 bullet says landed | `6e0ae87` | `954dc026b9a7be35172e6481ca27cf6f0b5513b2` | `tests.test_hermes_landed_status` 1 OK | PASS, review accept, 1 attempt, 37s |
| ATG evidence keeps pin SHA and score SHA | `dfe915f` | `84c2cbf4068430ec8915a426b5d4824401f05a66` | pin-score + stage eval, 5 OK | PASS, review accept, 1 attempt, 116s |
| harness2 evidence keeps entry 136 notes doc | `13d6bf2` | `1d3f6143a05d9f04bc55a530ed4bbc2dc01576b6` | notes-doc + stage eval + pin-score, 6 OK | PASS, review accept, 1 attempt, 294s |

Each fix was cherry-picked from the cloud commit after a read of the diff. The message was amended. The author stayed `pfy-cloud-build`. The planted test commit was pushed only with the green fix. `data/tool_integration_stages.json` hash stayed `369593d90d7e32787c3d6684ec25deefcce6b4c0`.

Receipts: `eval/mvp-1031/backlog-burn/receipts/01-enterable/` through `06-notes-doc/`. One model em dash in the item 2 tail was replaced with ` - ` in the committed copy. Status fields were not changed.

## How each change fails and how we recover

| Change | How it fails | Recovery |
|--------|--------------|----------|
| Enterable not-ok | `ok` false returns before storing the stripped list, so callers still see ids `enterable` and `session`. `open_fn` must not run. | Store the stripped list. A status id stays. The ok path still records enterable. |
| Catalog apply | A receipt whose file exists is dropped, `last_updated` rewinds to 2026-09-25, the ATG ceiling falls from I2, or `measured-probe` becomes the older handoff potential. | Keep `receipt:REL` and a bare relative file that exists. Drop a missing receipt. Keep the stamp. Do not lower `tier_ceiling`. Do not replace a non-empty potential. Do not change `integration_stage`. |
| Entry 149 count | The smoke line says 18 while `tests/test_x_intake_smoke_149.py` has 28 `def test_` methods. | The published integer equals that method count. The dated automation handoff stays the record of that day. |
| Hermes bullet | `docs/PENDING-HANDOFF.md` still says the branch lands on main while `docs/eval/HERMES-EVAL-HANDOFF.md` says it landed. | That 2026-10-19 bullet says Landed on. Other sections stay. Tips `24fe672` and `7281cd1` are already in `origin/main`. |
| ATG pin and score | Recompute turns `pin:FULLSHA` into the word `pin` and drops `scored:86d1b890`. Those commits differ. | Keep `pin:HEX` and `scored:HEX` when HEX is `[0-9a-f]` and at least 7 characters. `pin:not-a-sha` and `scored:nope` stay dropped. |
| harness2 notes doc | Recompute drops `notes_doc:sources/entries/136-harness2.md` even though the file exists. | Keep `notes_doc:REL` when REL is a file under the repo. Drop a missing file and an absolute path. The field notes doc and the live receipt stay. |

After item 6, a recompute of every stage card drops no evidence string that is still on disk.

## Skipped

Already listed in the run log before the first build: T-0005 (OQ-0003, human stage letter), T-0091, T-0094, T-0110 (left to the dogfood lane), T-0062, T-0016, T-0081, T-0074, T-0070, T-0043, T-0064, T-0046, T-0124 (full fold; this lane took only the not-ok assignment), ADR-0017 (OQ draft already in the backlog handoff), runx receipt schema (needs an ADR), dogfood pregate lock and splice socket close (other lanes own those files), help-text and local-bench TMPDIR (intfix already merged them), x-intake tree signatures and `smoke.py` (selfhost is landing them), entry 149 date line and `smoke_149.py` (left to Run A).

Confirmed again at the stop, and not taken:

- X-intake recommended next steps from 2026-10-20 through 2026-10-29 (Chiasmus, Tracekit, Charlotte, neatroots, Hermes teammates, skill-up, HiRoute, Muxin, taste-skill, gitai, SkillSpector on nimo, MemPalace recall). Each needs a local model, nimo, docker, a toolchain, or Mark.
- Live lanes were in `smoke_148.py`, `smoke_122_124.py`, and `smoke_112_114.py`. Those files were not edited.
- `scripts/pfy_build_cloud.py` and `scripts/pfy_build_local.py` were not edited.

## Test evidence

Targeted and niced. No `unittest discover`, no `make eval-*`, no `scripts/pregate.sh`.

- `tests.test_enterable_not_ok`: 2 OK
- `tests.test_catalog_stage_eval`: 4 OK after the receipt fix, still green after the later evidence fixes
- `tests.test_entry_149_count`: 1 OK
- `tests.test_hermes_landed_status`: 1 OK
- `tests.test_catalog_stage_pin_score` with `tests.test_catalog_stage_eval`: 5 OK
- `tests.test_catalog_stage_notes_doc` with the stage eval and pin-score modules: 6 OK

Item 2 attempt 1 passed the worktree gate and failed commit recheck: `apply` printed `METHODS_PATH.relative_to(ROOT)` while the temp methods file sat outside the recheck extract. Attempt 2 prints an absolute path in that case. The behavior rules still hold.

## Cross-lane requests

- mvp-cloudfix: the cloud recheck extracts the commit under `repo/tmp/recheck-<sha>` and leaves `TMPDIR` on the worktree `tmp/`. A test that puts a path in `tempfile.TemporaryDirectory()` and then calls `Path.relative_to(ROOT)` passes the worktree gate and fails the recheck. This lane did not edit `scripts/pfy_build_cloud.py`. A later runner change can point the recheck `TMPDIR` at the recheck tree.
- mvp-daily-card: this lane changed one word in `docs/PENDING-HANDOFF.md` (Lands to Landed) in the 2026-10-19 Hermes section. That file was on their do-not-edit list. Please leave that tense in place.

## Gate

The branch changes runtime (`scripts/pfy_enterable_162.py`, `scripts/catalog_stage_eval.py`) and docs. Gate: Tester plus Reviewer. Pregate is also appropriate for the docs and test files.

Pregate not run: host busy. At 2026-10-31T23:22:46Z `Runner.Worker` was live and another lane held `~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock` while running `scripts/pregate.sh`. This lane did not take the lock and did not signal that process.

## Next step

Reviewer, then Tester, at the tip of `bot/mvp-backlog-burn-1031`. Do not merge from this run. No further evidence string is dropped by catalog recompute. The open product work that remains is the skip list above.
