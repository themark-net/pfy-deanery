# Handoff mvp-integrate-1031

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
