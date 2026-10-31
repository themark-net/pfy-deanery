# Handoff: mvp-crosslane-1031

Branch `bot/mvp-crosslane-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-crosslane-1031`. Tip `d6c5390`. Base at drop-in time was `origin/bot/mvp-integrate-1031` (`0c3f133`). This branch merged that ref at `cf5a11c` (`34b1de1`), then cloudfix `d78ed00`, then integrate `b6db528`. A later integrate tip `d078de6` was not merged: it does not change the two runners. No rebase, no force push, no PR, no merge, no tag. No local model. No `./pfy build --local` trial outside the stub tests.

Exit: lane empty. Every collected cross-lane note is in the table. Pregate not run: host busy (`Runner.Worker` pid 3751002, and the heavy lock was held).

## Request table

| Request | Source lane | Status |
|---------|-------------|--------|
| A new test file must be `tests-tampered` before the after-gate | mvp-gom-dogfood-1031 | already fixed `9f1b6be` |
| A missing interpreter, or a default unittest import error, is usage (exit 2), not a product FAIL | mvp-gom-dogfood-1031 | already fixed `36cda3c` |
| Refuse when HEAD is not `origin/main` unless `--base` is passed | mvp-gom-dogfood-1031 | already fixed `2348080` |
| Do not redact fixture ids that only look like secret assignments | mvp-gom-dogfood-1031 | already fixed `599d2d2` |
| The product gate must not see secret-named env vars. Grok still uses the parent env | mvp-gom-dogfood-1031 | already fixed `50ac9ba` (scrub is in `gate()` only) |
| A missing `--base` ref is exit 1, reason `worktree-failed`, with a receipt | mvp-realfail2-1031 | already fixed `3ee4819` |
| `protected-path-changed` recovery was an empty string (observation, not a FINDING) | mvp-realfail2-1031 | already fixed `827b4b0`. `finish()` fills an empty recovery, and the call sets `recovery_detail` to the paths |
| Sigkill reap, review-reject of `rm -rf /`, "Not signed in", `xai-` redact | mvp-realfail-1031 | already fixed `6dd9e63`, `eb13975`, `fb71e1e`, `e558bd5` |
| Review accept must not land a tree signature that stores `:target` instead of the linked file bytes | mvp-selfhost-1031 | fixed `10328e3` |
| Cloud runner had no `--writable-test` | mvp-selfhost-1031 | already fixed `b06981d` (and `26b6d05`) |
| t1: two tests want opposite winners (stderr pull vs the OCI cache line) | mvp-selfhost-1031 | left. `--writable-test` does not pick a winner. The test files are not this lane's scripts. Choosing a winner is a product decision. OQ draft below |
| `tests/test_pfy_build_local.py` skips the help test when `grok` is not on PATH, so ubuntu never checks it | mvp-ci-cover-1031 | fixed `7d12860` (fake `grok` prepended on PATH) |
| `scripts/pregate.sh` writes `tmp/pgs` on the main checkout via the git common dir | mvp-review-fix2-1031 | left. See the OQ draft. Not this lane's file. A longer worktree path breaks the 60-character rule |
| If the cloud runner copies the local review loop, also copy `reviewer-unavailable`, the cap, crash versus no-change, the label list, and stale-worktree | mvp-review-fix2-1031 | left. That is a port of the local loop, not a one-function defect. Cloud already has its own review path |
| Stderr and the top-level receipt must say `scope check skipped: no allow list` when there is no `files:` line and no `--allow-path` | mvp3-followups-1031 item 2 | fixed `f46d726` |
| One test-only env var, off by default, must gate the stub binds and the extra-stage inject | mvp3-followups-1031 item 3 | fixed `351cf1d`. The stub binds were already behind `PFY_LOCAL_BUILD_TEST_SEAM`. The inject hook now uses that same switch |
| Receipt `review.same_model: true` next to the model tag | mvp3-followups-1031 item 4 | fixed `f93e120` |
| Only excluded paths changed (empty reviewed name set) must not reach `git commit`. Reason `no-reviewable-change` | mvp3-followups-1031 item 5 | fixed `0e49e1c` |
| Pin `test_ignored_helper_is_not_committed` to `commit-recheck-failed` only | mvp3-followups-1031 item 6 | fixed `bae035f` |
| A poster that writes no `pfy-review-out.json` is `review-crashed` or `review-http-error`, one attempt, no commit | mvp3-followups-1031 item 7 | fixed `d6c5390` (`review-crashed`) |
| Mark the stale scope-vs-`git add -A -f` sentences in `docs/ops/HANDOFF-mvp3-review-retry.md` | mvp3-followups-1031 item 8 | left. That handoff is not a file this lane may edit. Lines 42, 49, and 55 still describe the old gap. The stage path commits only reviewed names |
| A TODO row for the reviewer follow-ups | mvp3-followups-1031 | left. `docs/TODO.md` is owned by integrate |
| Update `docs/ops/PREGATE.md` and `sources/entries/149-mempalace.md` | mvp-followups-fix2-1031 | left. Neither file is owned here |
| Append the demo command to `docs/ops/pfy-build-daily.md` | mvp-daily-card-1031 (asked by demo lanes) | left. That card file is owned by mvp-daily-card |
| `/tmp` cleanup in pfylib and the x-intake smokes | mvp-tmpclean lanes | left. Not these runners |
| `test_relative_outdir_log_path_safe` when `TMPDIR` is inside the repo | mvp-local-bench | left. `tests/test_local_bench.py` is not owned here |
| Failed launch must drop a stale enterable step | mvp-selfhost-1031 / integrate | already fixed on `origin/bot/mvp-integrate-1031` at `f2d4f40`. Not in this branch, because `d078de6` was not merged |
| Archive recheck gate used the worktree `TMPDIR`, so `TemporaryDirectory` failed `relative_to` on the extract | found in `scripts/pfy_build_cloud.py` `gate()` while checking the selfhost review path | fixed `7667b2e` |

## Done on this branch

| Item | Commit | What landed |
|------|--------|-------------|
| Exit card | `8053630` | Run log and the first decisions, before product code |
| Help test without grok | `7d12860` | Fake `grok` is always prepended. The help and `-p --dry-run` checks run |
| `:target` review miss | `10328e3` | `diff_drops_linked_content`. Review accept does not land that diff |
| Recheck `TMPDIR` | `7667b2e` | `gate()` sets `TMPDIR` to the directory it is running in |
| Ignored-helper reason | `bae035f` | Assertion is `commit-recheck-failed` only |
| Inject seam | `351cf1d` | Extra-stage inject requires `PFY_LOCAL_BUILD_TEST_SEAM=1` |
| Empty reviewed set | `0e49e1c` | `_stage_reviewed` returns `no-reviewable-change` and does not commit |
| Scope warning | `f46d726` | Phrase `scope check skipped: no allow list` on stderr and the receipt |
| Same model | `f93e120` | `review.same_model` is true |
| Review crash | `d6c5390` | Missing out file is `review-crashed`, one attempt |

## How each change fails and recovers

| Change | How it fails | Recovery |
|--------|--------------|----------|
| Help test | Ubuntu has no `grok`, so the help check never ran | A fake `grok` on PATH lets help and dry-run run. Dry-run does not exec grok |
| `:target` | Review prints accept for a signature that records `is_symlink` or `readlink` and writes `:target`. A later content edit is invisible | Reason `review-rejected`, exit 1, no `cloud/` branch, caller HEAD unchanged. A diff that hashes file bytes is not this case |
| Recheck `TMPDIR` | The worktree gate passes, then the extract gate's temp dir is outside the extract and `relative_to` fails | `TMPDIR` for that gate is the extract `tmp`. The same command passes and the file lands. If the directory cannot be created, the previous `TMPDIR` stays |
| Ignored helper | The assertion stayed green for `scope-commit-mismatch`, which this path does not return | The receipt reason is `commit-recheck-failed`. The helper is not in the commit. The caller checkout is unchanged |
| Inject seam | `PFY_LOCAL_BUILD_INJECT_EXTRA_STAGE=1` alone staged `injected-extra.txt` and a green fix became `scope-commit-mismatch` | Seam off: the fix commits and that name is absent. Seam on: the index resets, no branch |
| Empty reviewed set | A `.pytest_cache` only change reached `git commit` and came back `commit-failed` | Reason `no-reviewable-change`, exit 1, no branch, caller HEAD unchanged |
| Scope phrase | Operators saw a different warning, and only on the receipt | Bare task: the phrase is on stderr and in `warnings`. A `files:` line or `--allow-path` omits it. The run still PASSes |
| Same model | A reader treated the model accept as a second person | The receipt says `review.same_model` true next to `model` |
| Review crash | No out file became `review-unparseable` and the loop retried | Reason `review-crashed`, exit 1, one attempt, no commit. A real unparseable body is still a reject and is still retried |

## Test evidence

Targeted `nice -n 19 python3 -m unittest` with `TMPDIR` under this worktree. Final run of each new test passed.

| Commit | Tests | Result |
|--------|-------|--------|
| `7d12860` | help test, in a six-test run with the cloud checks | 2.608s OK |
| `10328e3` | target-marker and root-delete | 0.830s OK |
| `7667b2e` | recheck tmpdir, then the two secret-env receipt tests | OK |
| `bae035f` | `test_ignored_helper_is_not_committed` | 1.898s OK |
| `351cf1d` | inject off, inject on, stub binds | 5.093s OK |
| `0e49e1c` | excluded-only change, then inject off and mismatch | 1.320s and 3.318s OK. The first attempt failed because the stand-in gate printed no parseable summary |
| `f46d726` | bare task, `files:` task, `--allow-path` | 3.442s OK |
| `f93e120` | no-review receipt | 1.594s OK |
| `d6c5390` | missing out file. Unparseable review still retried in the run before the fake-python import fix | 1.396s OK |

Full `unittest discover` was not run. Pregate was not run.

## OQ drafts (not filed in the central index)

These need a person or an ADR. This lane did not add an ADR and did not edit `docs/OPEN_QUESTIONS.md` (integrate owns that index).

1. Pregate scratch. `scripts/pregate.sh` sets the run root from `git rev-parse --git-common-dir`, so a linked worktree writes `tmp/pgs` on the main checkout. `docs/ops/PREGATE.md` refuses a root over 60 characters so harness2 sockets fit `sun_path` (108 bytes). Putting scratch inside a long worktree path such as `tmp/mvp-crosslane-1031` would exceed that cap. A design has to keep the short root and still avoid the main checkout. Do not move the path until that design exists.

2. Selfhost t1. One test wants a same-image stderr pull to win. Another wants the OCI cache stub to print the stdout cache line whenever it also prints pull progress. `--writable-test` lets a cloud task name a base test. It does not decide which assertion is the product. Leave both tests until someone picks the winner.

## Cross-lane requests still open

- `docs/ops/HANDOFF-mvp3-review-retry.md` lines 42, 49, and 55. Mark them superseded. The commit path stages reviewed names only (`0f0d889` in the integrated history, plus `0e49e1c` and `bae035f` here). This lane did not edit that file.
- `docs/TODO.md`. One row if integrate wants it: the reviewer follow-ups in the table above are on `bot/mvp-crosslane-1031`.
- `docs/ops/PREGATE.md` and `sources/entries/149-mempalace.md`. Still named by mvp-followups-fix2. Not edited here.
- `docs/ops/pfy-build-daily.md`. Daily-card lane.
- Selfhost t1 contradiction. Needs a product choice. See OQ draft 2.
- Pregate scratch location. See OQ draft 1.

## Gate

Runtime changes: Tester plus Reviewer. The commits from `7d12860` through `d6c5390` change the cloud runner, the local runner, or their tests.

Pregate not run: host busy.

Do not treat this handoff as a Feature GO. `./pfy build --local` stays opt-in. The local default stays NO-GO. Do not merge to main from this lane.

## Next

Integrator: merge `bot/mvp-crosslane-1031` at `d6c5390` (or later, if this handoff commit is the tip) into the integrate branch. Do not Feature GO. Tester runs the modules named above. Reviewer reads the one-function diffs. Then mark the three stale sentences in `docs/ops/HANDOFF-mvp3-review-retry.md` when that file is free, and decide the t1 contradiction and the pregate scratch OQ.

## Finish

state: lane empty | tests: targeted modules in the table, final runs OK | files: two runners, their tests, this handoff, the run log, decisions | err: none | pregate not run: host busy
