# Handoff mvp-freshclone-1031

Lane: first-day experience on a fresh clone of `origin/bot/mvp-integrate-1031`. Branch `bot/mvp-freshclone-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-freshclone-1031`. Exit: lane empty. Launch `2026-10-31T23:25:38Z`. Handoff `2026-10-31T23:39:22Z`.

## Items done

| Item | SHA | Result |
|------|-----|--------|
| Exit card before the walk | `b98e3b5` | Eight exits and drop-in stops in `docs/ops/RUN-LOG-mvp-freshclone-1031.md` |
| Naive walk | `96fc710` | Clone `cf5a11c` in `tmp/fresh/`. Dry-run exit 0. One real fixture build PASS |
| First-day docs | `80e5752` | `README.md` Daily build section, one `make help` line, `tests/test_pfy_build_first_day.py` |

Real build (one cloud attempt, no `--local`, `--timeout 420`):

- Command shape: the copy-paste in `eval/mvp-1031/README.md` from the fresh clone
- Exit 0, receipt status `PASS`, reason `ok`, review `accept`, pushed false
- Branch `cloud/make-add-return-the-sum-of-its-two-argum-20261031T233257307009Z`
- Commit `af44f7df7e864ace57eb3f2cc16e286b6d4d9c39` (`add` returns `a + b`)
- Gate `python3 -m unittest test_add` before exit 1, after exit 0
- Receipt stays under gitignored `tmp/fresh/tmp/mvp-fixture-receipt/receipt.json`
- Wall about 30 seconds. `grok` 1.0.70 already on `PATH`. Existing login reused. Auth file not read and not printed.

## Test evidence

`nice -n 19 python3 -m unittest tests.test_pfy_build_first_day tests.test_pfy_build_cloud.CloudBuildSkeletonTests.test_help_exits_0_and_names_the_daily_command tests.test_pfy_build_cloud.CloudBuildDispatchTests.test_p_help_reaches_dogfood_and_positional_reaches_cloud tests.test_pfy_build_local.CloudBuildUnchangedTests.test_help_and_dry_run_stay_the_same`

5 tests, OK, about 2.4 seconds, before the doc commit. After the clone-section sentence, `tests.test_pfy_build_first_day` again: 2 OK.

Re-walk on this worktree after the README and Makefile edits: `make help` prints `./pfy build <task>`. `./pfy build` with no task exits 2 and prints the daily command. The first-day test dry-run writes `receipt.json` under the scratch repo, base `HEAD`, gate `python3 -m unittest discover -s tests -t .`, pushed false.

No red-base failure in those modules. `CloudBuildUnchangedTests.test_help_and_dry_run_stay_the_same` passed here.

## How it fails and how it recovers

The runner code did not change. The failure this lane closes is a reader who never finds the daily command, or who trusts the operator card's default repo.

- Fail: README and `make help` omit `./pfy build`, so day one follows the window path or `make env-init`. Or the reader believes the default repo is the directory that contains `./pfy`, and a build started in a scratch clone edits the catalog checkout.
- Recover: the Daily build section says the repo is the git toplevel of the current directory, the base is `origin/main` when that ref exists else `HEAD`, and the gate is the full unittest discover. It points at `--repo` and `--test-cmd`, at `eval/mvp-1031/README.md`, and at `grok login`. It says this command does not read `auth.json` and does not load `.env`. Where `docs/ops/pfy-build-daily.md` or `docs/modules/pfy-build.md` disagree on the default repo, trust `./pfy build --help`.
- Test: `tests.test_pfy_build_first_day` runs `./pfy build "<task>" --dry-run` with cwd set to a scratch git repo and no `--repo`. It fails if the receipt is not under that repo, if base is not `HEAD`, or if the gate command is not the one README quotes. It also fails if no-task exits something other than 2 or if that path prints the jev wrap help. A wrong default repo makes the scratch receipt missing and the test fails.

## Skipped

- `docs/QUICKSTART-pfy-build.md`: not on the integrate clone. Owned by mvp-docs-1031, which is DONE on its own branch. Not created here.
- Stale sentences in `docs/ops/pfy-build-daily.md` and `docs/modules/pfy-build.md`: owned by mvp-daily-card-1031 and mvp-surface-1031.
- `HELP_TEXT` in `scripts/pfy_build_cloud.py` (default gate, 1200 second timeout, receipt directory, already-logged-in grok): `origin/bot/mvp-cloudfix-1031` and `origin/bot/mvp-dogfood-fix-1031` both have large unmerged diffs on that file. `scripts/pfy` top-level help is already being edited by dogfood-fix.
- Bare `./pfy`, `board`, `start`, `launch`: they start inference or a window. This lane does not run a local model and does not leave a GUI up.
- `docs/TODO.md`: integration is the writer. Not edited.
- Pregate not run: host busy (`Runner.Worker` was present at handoff). This lane's drop-in also says not to run `scripts/pregate.sh`.

Three owned-file skips did not form a no-progress stop. There is no next unowned first-day edit.

## Cross-lane requests

1. mvp-docs-1031: land `docs/QUICKSTART-pfy-build.md`. This branch's README section does not link that file, because it is not on integrate. The new section sits after the simple-path prose, not on the two lines that branch inserts after the simple-path code fence.
2. mvp-daily-card-1031 and mvp-surface-1031: in `docs/ops/pfy-build-daily.md` and `docs/modules/pfy-build.md`, the default repo is the git toplevel of cwd, not the directory that contains `./pfy`. Delete the sentences that say the cloud runner is absent and that a bare `./pfy build` still reaches the jev wrap. State the HEAD fallback when `origin/main` is missing.
3. mvp-cloudfix-1031 or mvp-dogfood-fix-1031: extend `HELP_TEXT` so `./pfy build --help` states the default gate `python3 -m unittest discover -s tests -t .`, the 1200 second timeout, the receipt directory `pipelines/dogfood/build-cloud/<stamp>/`, and that grok must already be logged in. Do not start `--local` from that text.

## Gate

Docs and a behavior test. No runner change. Gate: Reviewer, plus pregate. Pregate not run: host busy.

## Next step

Reviewer reads the Daily build section against `./pfy build --help` and `tests.test_pfy_build_first_day`. Integration can merge `80e5752` after the docs-lane README lines, which should not overlap this hunk. The three cross-lane requests above are the remaining first-day gaps.
