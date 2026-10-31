# Handoff mvp-integrate-1031

Pass 2 goal met. No rebase, no force push, no PR, no merge to main, no tag. Not a Feature GO. Catalog HOLD 70-75 unchanged. No GitHub issue opened or closed. No local model. No `--local`. Pregate not run by this lane. The operator runs pregate on the final tip.

Pass 2 content commit: `7997dd67e71ad3fcf50cd868f1667d462ca3aca3`. This stamp commit is the final tip. Pregate `origin/bot/mvp-integrate-1031` at this stamp (`git rev-parse origin/bot/mvp-integrate-1031` after the stamp push).

## Pass 2

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
