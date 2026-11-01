# Handoff mvp-integrate-1031

Pass 3 goal met. No rebase, no force push, no PR, no merge to main, no tag. Not a Feature GO. Catalog HOLD 70-75 unchanged. No GitHub issue opened or closed. No local model. No `--local`. Pregate not run by this lane. The operator runs pregate on the final tip.

Pass 3 tree before this stamp: `918fa8e`. Demo receipt commit: `dd1db3b`. This stamp commit is the pass 3 tip. Pregate `origin/bot/mvp-integrate-1031` at this stamp (`git rev-parse origin/bot/mvp-integrate-1031` after the stamp push).

## Pass 3

| Item | Commit | Result |
|------|--------|--------|
| Exit card | `cf5a11c` | Pushed before the merges |
| `origin/bot/mvp-review-fix2-1031` | `d480516` | Tip `8c40087`. Clean. Local module 92 OK in 246.757s. Carries mvp3-review-retry at `582414b` |
| `origin/bot/mvp-cloudfix-1031` | `7c48022`, then `2021775` | Tips `d78ed00`, then `0dfc9d1` (docs only). 76 OK in 26.289s, skipped 1. One classifier import |
| `origin/bot/mvp-dogfood-fix-1031` | `be63148` | Tip `1fa9fd3`. `resolve_base` conflict. 74 OK in 17.115s |
| `origin/bot/mvp-mutate-preflight-1031` | `44bd7ae` | Tip `322cde0`. Clean. 45 OK in 4.931s |
| `origin/bot/mvp-ci-cover-1031` | `67e6658` | Tip `7391cd6`. Clean. 6 OK in 0.051s |
| `origin/bot/mvp-realfail3-1031` | `b6db528` | Tip `a4c80a1`. Clean. 6 OK in 0.014s |
| `origin/bot/mvp-followups-fix2-1031` | `4837247` | Tip `aea15bf`. Clean. 93 OK in 63.797s |
| `origin/bot/mvp-selfhost-1031` | `f5e7d4c` | Tip `5fb063e`. Included. 45 OK in 8.904s |
| `origin/bot/mvp-gom-dogfood-1031` | `1e282df`, then `ff3f3ba` | Tips `962e234`, then `731aae2`. 2 OK |
| `origin/bot/mvp-sixtask-1031` | `a92b08c` | Tip `177940e`. Clean. 10 OK in 0.006s |
| `origin/bot/mvp-sixtask-int-1031` | `f877c7d` | Tip `d642ec1`. Clean. 12 OK in 0.052s. Report VERDICT GO |
| `origin/bot/mvp-tmpclean2-1031` | `d078de6` | Tip `89f0564`. Five conflicts. 116 OK in 116.455s |
| `origin/bot/mvp-backlog-burn-1031` | `f39d64a` | Tip `84db544`. Clean merge. Entry 149 count was 28 against 36 methods |
| Entry 149 published count | `1bd1cb3` | Smoke line set to 36. Six backlog modules, 10 OK in 0.101s |
| Freeze log | `66a5500` | Item log pushed before the suite |
| Demo 3 receipt and report | `dd1db3b` | PASS. Checker exit 0. Cloud commit `1ed98a4d2d3c39b8099603e60dc87ed41e7340f4` |
| Backlog-burn report link | `918fa8e` | `tests.test_docs_hygiene` 2 OK in 0.029s |

Skipped: `bot/mvp3-followups-1031` seen at `0575f6c`. Extra `bot/mvp3-review-retry` tip `6664713` not merged. The copy already in review-fix2 is `582414b`.

## Demo 3

PASS. Checker `python3 eval/mvp-1031/check_receipt.py eval/mvp-1031/demo-receipt-pass3.json` exit 0. Receipt [../../eval/mvp-1031/demo-receipt-pass3.json](../../eval/mvp-1031/demo-receipt-pass3.json). Report [../../eval/mvp-1031/REPORT.md](../../eval/mvp-1031/REPORT.md).

Throwaway clone `tmp/demo3-target` at freeze `66a5500`, branch `demo-base`. One cloud `./pfy build`, no `--local`. Wall 421 seconds (2026-10-31T23:53:06Z to 2026-11-01T00:00:07Z). Exit 0. Attempts 1. Branch `cloud/stop-tests-test-x-intake-smoke-117-118-p-20261031T235306753011Z`. Commit `1ed98a4d2d3c39b8099603e60dc87ed41e7340f4`. Review accept. Human verdict yes. The integrate checkout stayed `bot/mvp-integrate-1031`. The cloud commit is not on this branch.

Task: the two smoke test modules for entries 117 and 119 wrote `pipelines/smoke` receipts inside the repo. The cloud commit points `_receipt` at a temp `PFY_SMOKE_RECEIPT_DIR` and adds `tests/test_x_intake_smoke_117_119_receipts.py`. On a detached worktree of that commit the new test passed in 0.209s. `git diff-tree --name-only` is those three test files.

Cloud-default daily use, from `eval/mvp-1031/sixtask-int/REPORT.md`: VERDICT GO. Two passes, 6/6 runner PASS, 6/6 review accept, 6/6 human accept, 6/6 gate PASS. Pass 1 wall 1243.8s. Pass 2 wall 1016.3s.

## Suite (pass 3)

Command: `TMPDIR=$PWD/tmp nice -n 19 flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock python3 -m unittest discover -s tests -t .`

The flock waited while another lane held the lock (a local t4 rerun, then `scripts/pregate.sh 0afea54`). This lane did not signal those processes. The discover then ran on the tree that already contained `dd1db3b`.

Ran 1243 tests in 890.586s. Failures 1, skipped 16. Exit 1.

The one failure was `tests.test_docs_hygiene.DocsHygieneTests.test_docs_relative_links_resolve`. `docs/ops/HANDOFF-mvp-backlog-burn-1031.md` linked `../eval/mvp-1031/backlog-burn/REPORT.md`, which resolves under `docs/eval/`. The file is `eval/mvp-1031/backlog-burn/REPORT.md`. Commit `918fa8e` changes that link to `../../eval/...`. Targeted re-run: 2 OK in 0.029s. No second discover.

The pass 2 help-contract failure and the TMPDIR local-bench failure did not return.

## How pass 3 fails and recovers

- `resolve_base`: a missing requested ref is `BaseMissing` (exit 1, recovery line). Omitting `--base` when HEAD is not `origin/main` is `UsageError` (exit 2, both short shas). One `classify_cloud_failure` import. No inline classifier.
- Image pin: container and digest checks stay, plus the duplicate-key loader and the ripgrep step check. Pregate still uses `command -v python3` and `PREGATE_IMAGE_PIN_ROOT`.
- Tmp cleanup: the separate-process hold stays. Scratch for that test is under the repo `tmp/`.
- Entry 149: the published stub count is the live `test_` method count. It was 28 after later lanes added methods. It is 36.
- Docs link: a `docs/ops/` link with one `../` too few fails hygiene. The recovery is the extra `../` to the repo `eval/` tree.
- Demo 3: a red before gate (the new test module is absent) and a green after gate. If the cloud call had been rate-limited or unauthenticated, the receipt would still be committed and the report would say it did not PASS. It PASSed. This lane did not start `--local`.

## Cross-lane requests

- Land cloud commit `1ed98a4d2d3c39b8099603e60dc87ed41e7340f4` from a lane that may edit `tests/test_x_intake_smoke_117_118.py` and `tests/test_x_intake_smoke_119_121.py`. It is not on this branch. This lane does not own those files.
- `bot/mvp3-followups-1031` at `0575f6c` and `bot/mvp3-review-retry` at `6664713` stay out. mvp3 is gated separately.

## Gate

Tester plus Reviewer. The merges brought runtime files (`scripts/pfy_build_cloud.py`, smoke scripts, pfylib). The pass 3 edits after the merges are the entry 149 count, the backlog-burn link, the demo receipt, and this handoff.

Pregate not run by this lane. The operator runs it on this stamp. At the suite start another pregate already held the heavy lock.

## Next

Operator pregates this stamp. No further gap in `origin/bot/mvp-plan-1031:docs/plans/MVP-PARALLEL-1031.md` fits this lane's owned files. Round 2 rows belong to mvp-dedupe (already done as the single import), mvp-sandbox-gate, mvp-local-t5, and mvp-daily-card. Exit: lane empty.

## Pass 2 (prior)

| Item | Commit | Result |
|------|--------|--------|
| Exit card before pass 2 merges | `6eb5d83` | Pushed |
| `origin/bot/backlog-catalog-1030` | already in at `e04e926` | No new commits |
| `origin/bot/pfy-followups-1030` | `0f478ed` | Tip `c0d38af`. Clean |
| `origin/bot/mvp3-review-retry` | already in at `d624535` | Pin held |
| `origin/bot/mvp-review-fix-1031` | already in at `1140434` | No new commits |
| `origin/bot/mvp-preflight-1031` | already in at `100348d` | No new commits |
| `origin/bot/mvp-surface-1031` | already in at `30cdd24` | No new commits |
| `origin/bot/mvp-eval-1031` | already in at `1768037` | No new commits |
| `origin/bot/mvp-cloud-1031` | already in at `d94d2b6` | No new commits |
| `origin/bot/mvp-cloudfix-1031` | `52354f0`, then `152448f` | First tip `57c6dad` conflicted in `scripts/pfy_build_cloud.py`. Took the cloudfix file. Catch-up tip `f316036` merged clean |
| `origin/bot/mvp-review-fix2-1031` | `21b8b57`, then `284c2c9` | Tips `23ea0cd`, then `187efde`. Clean |
| `origin/bot/mvp-intfix-1031` | `51eb0b3`, then `3fa6062` | Tips `13e967d` (drop-in), then `7209ff2` (exit card). Clean |
| `origin/bot/mvp-followups-fix2-1031` | `808bc6c` | Tip `c328da2`. Clean |
| `origin/bot/mvp-tmpclean-1031` | `0287ffb` | Tip `db1ca11` (drop-in only). Clean |
| `origin/bot/mvp-docs-1031` | `9af137d`, then `135eebb` | Tips `bc6d5e0` (drop-in), then `981f1d7` (exit card). Clean |
| `origin/bot/mvp-mutate-cloud-1031` | `791c682` | Tip `6e34a1b` (drop-in only). Contains cloudfix. Clean |
| `origin/bot/mvp-mutate-review-1031` | `280e12d` | Tip `a6fbf18` (exit card only). Clean |
| `origin/bot/mvp-realfail-1031` | `06fa79c` | Tip `d09647a`. Clean |
| `origin/bot/mvp-realfail2-1031` | `074f5e9` | Tip `884a16a` (drop-in only). Clean |
| `origin/bot/mvp-sixtask-1031` | `9dbf718`, then `31438fd` | Tips `a8a7ca4`, then `dbf104a`. Clean |
| `origin/bot/mvp-dogfood-1031` | `4d0991e` | Tip `e404b42`. Clean |
| `origin/bot/mvp-dogfood2-1031` | `94612ca` | Tip `b6d5b76` (drop-in only). Clean |
| `origin/bot/mvp-gom-dogfood-1031` | `6921552` | Tip `86639b7` (exit card). Clean |
| `origin/bot/mvp-selfhost-1031` | not merged | Seen at `62ae324`. Mark cherry-picks from it |
| Classifier proof | tree `135eebb` | One import. No inline classifier. `tests.test_pfy_build_cloud` and `tests.test_build_preflight`: 54 OK in 10.080s |
| Suite | tree `135eebb` | Ran 1098 in 731.925s. Failures 2, skipped 16 |
| Demo 2 receipt and report | `7997dd6` | PASS. Checker exit 0. Commit `535d000075744709b2752cec7511d087801f2aa5` |

Merge freeze is `135eebb`. One catch-up merged tips that moved during the first wave. This lane did not wait for lanes that were still on a drop-in or an exit card.

## Demo 2

PASS. Details are in `eval/mvp-1031/REPORT.md` under Pass 2.

- Command used `--repo tmp/demo2-target`, `--base demo-base`, `--test-cmd` the new test, `--writable-test tests/test_attach.py`, `--receipt-dir tmp/demo2-receipt`. No `--local`.
- Build exit 0. Wall 91 seconds. Attempts 1. Review accept. Human verdict yes.
- Checker: `python3 eval/mvp-1031/check_receipt.py eval/mvp-1031/demo-receipt-pass2.json` exit 0.
- Branch: `cloud/on-the-not-ok-branch-of-arm-launch-env-s-20261031T213959467597Z`
- Commit: `535d000075744709b2752cec7511d087801f2aa5` on the throwaway clone only.
- Caller during the run: `bot/mvp-integrate-1031` at `135eebb`, porcelain empty.

The behavior test fails without the one-line store (`enterable` stays in the id list) and passes on the cloud commit.

## Suite (pass 2)

```text
TMPDIR=$PWD/tmp nice -n 19 flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock python3 -m unittest discover -s tests -t .
```

Started 2026-10-31T21:23:55Z. Finished 2026-10-31T21:38:19Z. Ran 1098 tests in 731.925s. FAILED (failures=2, skipped=16).

Same two failures as pass 1. Not introduced by a conflict resolution in this pass. Not rewritten.

1. `tests.test_pfy_build_local.CloudBuildUnchangedTests.test_help_and_dry_run_stay_the_same`. Bare `./pfy build --help` is the cloud card. The test still expects `--prompt-file` there.
2. `tests.test_local_bench.OutdirPathTests.test_relative_outdir_log_path_safe`. `TMPDIR` is this worktree `tmp/`, so the out-of-tree assertion sees a relative path.

`tests.test_pfy_build_p` is not in the failure list. The dogfood path was not edited by this lane.

## How pass 2 fails and recovers

- Classifier: `scripts/pfy_build_cloud.py` imports `classify_cloud_failure` once and wraps "not signed in" in `classify_runner_failure`. There is no second copy of the phrase list. The 54 cloud and preflight tests cover that import. A bad import fails those tests.
- Cloudfix conflict: the resolved file matched tip `57c6dad`. The later tip `f316036` merged with no conflict.
- Demo 2: a rate limit or auth failure would still be committed, and the report would say the demo did not PASS. This run exited 0. No retry. No `--local`.
- The stale enterable fix is only on the throwaway commit. The integrate tree still returns before storing `next_steps`. Recovery is a later lane that owns `scripts/pfy_enterable_162.py` and `tests/test_attach.py`. This lane did not edit those files.
- Help clash and the local-bench path stay as recorded in pass 1.

## Cross-lane requests

- Land the two-file cloud commit `535d000075744709b2752cec7511d087801f2aa5` (one assignment in `arm_launch_env_session`, plus `test_not_ok_drops_stale_enterable_step`) from a lane that may edit those files. It is not on origin. The report describes the diff. This lane does not own the files.
- The pass 1 help-test request still stands. This lane did not edit `tests/test_pfy_build_local.py`.
- `bot/mvp-selfhost-1031` was not merged. Last seen tip `62ae324`.
- Lanes still at a drop-in or an exit card when frozen: mutate-cloud `6e34a1b`, mutate-review `a6fbf18`, realfail2 `884a16a`, dogfood2 `b6d5b76`, tmpclean `db1ca11`, intfix `7209ff2`, docs `981f1d7`, gom-dogfood `86639b7`. Later commits on those branches are not in this tip.

## Gate

Pass 2's own resolution took the cloudfix runner as-is. Runtime files arrived through the merges (cloud runner, local runner, followups fixes). Gate for this tip: Tester plus Reviewer. Pregate is not run here. The operator runs it on the final tip. Do not treat this handoff as a Feature GO.

## Next

Operator pregates `origin/bot/mvp-integrate-1031` at the stamp tip. Next work that is not this lane: land the stale-enterable test from the demo 2 report, then the help-test cross-lane request. Do not merge `bot/mvp-selfhost-1031` from this lane.

## Pass 1

Branch `bot/mvp-integrate-1031`. Base `origin/main` (`85c53dc`). No rebase, no force push, no PR, no merge to main, no tag. Not a Feature GO. Catalog HOLD 70-75 unchanged. No GitHub issue opened or closed. No local model. No `--local`.

Exit: lane empty, after the definition of done. Wall cap was 2026-11-01T04:42:00Z. This handoff is earlier than that.

## Done

| Item | Commit | Result |
|------|--------|--------|
| Exit card before any merge | `7bb1085` | Pushed |
| Merge `origin/bot/backlog-catalog-1030` | `c75ebcf` | Clean |
| Merge `origin/bot/pfy-followups-1030` | `dc8fdb2` | Conflict in `docs/modules/pfylib.md`. Both still-true facts kept |
| Merge `origin/bot/mvp3-review-retry` | `d97c4f6` | Conflict in `docs/TODO.md`. MVP-2 note and MVP-3 row kept |
| Merge `origin/bot/mvp-review-fix-1031` | `2c223bd` | Clean |
| Merge `origin/bot/mvp-preflight-1031` | `b34143d` | Clean |
| Merge `origin/bot/mvp-surface-1031` | `c17d4ef` | Clean |
| Merge `origin/bot/mvp-eval-1031` | `71fd74a` | Clean |
| Merge `origin/bot/mvp-cloud-1031` | `29bbad4` | Clean |
| Classifier import | `d966e83` | 30-line edit. `tests.test_pfy_build_cloud` and `tests.test_build_preflight`: 35 OK in 6.753s |
| Suite | tree `444af7b` | Ran 1048 in 668.761s. Failures 2, skipped 16 |
| Demo receipt and report | `a73e9ae` | PASS. Checker exit 0 |

No listed origin branch was missing.

## Demo

PASS.

```text
bash eval/mvp-1031/init_fixture.sh "$PWD/tmp/mvp-fixture-repo"
./pfy build "Make add return the sum of its two arguments so the fixture test passes." \
  --repo "$PWD/tmp/mvp-fixture-repo" \
  --base main \
  --test-cmd "python3 -m unittest test_add" \
  --receipt-dir "$PWD/tmp/mvp-fixture-receipt"
```

- Build exit code: 0
- Checker: `python3 eval/mvp-1031/check_receipt.py eval/mvp-1031/demo-receipt.json` exit 0
- Branch: `cloud/make-add-return-the-sum-of-its-two-argum-20261031T210933627529Z`
- Commit: `ebef4238a7eff8f938747623f7920b3fde74e586`
- Review verdict: accept
- Receipt: `eval/mvp-1031/demo-receipt.json`
- Report: `eval/mvp-1031/REPORT.md`
- `pushed`: false
- Integrate branch after the run: `bot/mvp-integrate-1031` at `444af7b` (the demo commit `a73e9ae` only records the receipt). The fixture repo was the task target. Its `main` stayed on the red seed `65ef19b`. The `cloud/` branch is the receipt commit. `add` there returns `a + b`, and `python3 -m unittest test_add` passes on that tree.

The fixture test was red before the build (`0 != 5`).

## Suite

```text
TMPDIR=$PWD/tmp nice -n 19 flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock python3 -m unittest discover -s tests -t .
```

`TMPDIR` is the worktree `tmp/` because this lane must not use `/tmp`. Queued at 2026-10-31T20:52:17Z behind another pregate. Discover itself: Ran 1048 tests in 668.761s. FAILED (failures=2, skipped=16).

Targeted, before the suite:

- `tests.test_pfy_build_cloud` and `tests.test_build_preflight`: 35 OK in 6.753s
- `tests.test_pfy_build_p`, `tests.test_pfy_build_local`, `tests.test_pfy_build_local_review`, `tests.test_pfy_build_docs`, `tests.test_mvp_1031_receipt`, `tests.test_docs_hygiene`: 107 tests, 1 failure, 1 skipped, 96.747s. The one failure is the help test below. `tests.test_pfy_build_p` passed in that run.

### Failure 1, recorded, not fixed

`tests.test_pfy_build_local.CloudBuildUnchangedTests.test_help_and_dry_run_stay_the_same`

Bare `./pfy build --help` is the cloud runner. The test still expects dogfood `--prompt-file` and `-p, --prompt` on that bare help. On `origin/main` the same test reaches `scripts/pfy_build_p.py`, so this is not a red base. The merge of `scripts/pfy` was clean. It is not a conflict hunk and not a bad classifier import. Both lane features stay as landed.

### Failure 2, recorded, not fixed

`tests.test_local_bench.OutdirPathTests.test_relative_outdir_log_path_safe`

`log_path_for_receipt` returns a relative path when the log is inside the repo. With `TMPDIR` under this worktree, `TemporaryDirectory` is inside the repo, so the out-of-tree assertion sees a relative path. `tests/test_local_bench.py` matches `origin/main`. Skipped. Not rewritten.

## How it fails and how we recover

- Classifier import: if `scripts/pfy_build_cloud.py` cannot see `pfylib`, the runner dies before a task. Recovery: `sys.path` inserts the repo root (`parents[1]` of the script). The 35 cloud and preflight tests cover rate-limit text, auth text, and rc 0. A bad import would fail those tests. The diff is 5 insertions and 25 deletions.
- pfylib conflict: a stale "OpenCode is still its own path" sentence would hide T-0124. Recovery: the doc now says `attach.open_opencode_session`, the shim, and that the four harnesses stay on `open_session`. `tests.test_attach` covers that path.
- TODO conflict: dropping MVP-3 would hide the measurement. Both the followups MVP-2 wording and the MVP-3 done row are in `docs/TODO.md`.
- Demo: a rate limit or auth failure would still be committed, and `REPORT.md` would say the demo did not PASS. This run got exit 0 and review accept. No second demo. No `--local`.
- Help clash: operators who want the dogfood flags use `./pfy build -p`. Bare `./pfy build --help` is the daily cloud card. Recovery is a later edit of the local test, not a rewrite here.
- Local-bench path: the helper still returns an absolute path for a temp dir outside the repo. This suite's `TMPDIR` put the temp dir inside the repo. Recovery for that assertion is a `TMPDIR` outside the repo. This lane does not use `/tmp`.

## Cross-lane requests

- `tests.test_pfy_build_local.CloudBuildUnchangedTests.test_help_and_dry_run_stay_the_same` should expect dogfood flags on `./pfy build -p --help`, and expect the cloud card on bare `./pfy build --help`. Plan decision D1. This lane did not edit `tests/test_pfy_build_local.py` or `scripts/pfy` beyond the classifier import.
- `mvp-daily-card-1031` can append this demo's command, exit 0, branch, and `eval/mvp-1031/demo-receipt.json` to `docs/ops/pfy-build-daily.md`. That file is not owned here. The demo did PASS. Do not invent a different transcript.
- `mvp-dedupe-1031` is not required for the inline copy. The import already replaced it. The shared function matches `429` as a substring. The removed cloud copy used a word boundary. Call sites pass an int and strings. Extend `tests/test_pfy_build_cloud.py` only if a later lane wants that boundary pinned. This lane does not own that test file.
- `mvp-sandbox-gate-1031` and `mvp-local-t5-1031` are other lanes. Local-t5 needs a local model. This lane did not start one.

## Gate

Runtime change: the classifier import in `scripts/pfy_build_cloud.py`. Gate: Tester plus Reviewer.

Docs, the receipt, and the report are in the same branch. Pregate not run: host busy (`Runner.Worker` was running). Do not treat this handoff as a Feature GO.

## Next

Lane empty for this worktree. Next work that is not this lane: the help-test cross-lane request, then `mvp-daily-card-1031` reading `eval/mvp-1031/REPORT.md`. Sandbox-gate and local-t5 stay on their own branches after this handoff is on `origin/bot/mvp-integrate-1031`.
