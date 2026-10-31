# Handoff mvp-docs-1031

Branch `bot/mvp-docs-1031`. Base `origin/bot/mvp-integrate-1031` (`19c2710`). No rebase, no force push, no PR, no merge to main, no tag. Not a Feature GO. Catalog HOLD 70-75 unchanged. No local model. No `--local`.

Exit: lane empty. Wall cap was `2026-11-01T05:15:32Z` (8 hours from `2026-10-31T21:15:32Z`), with new items stopping at `2026-11-01T04:55:32Z`. This handoff is earlier. Host at the last check (`2026-10-31T21:29:55Z`): MemAvailable 61173784 kB, load 4.76, 32 cores.

## Done

| Item | Commit | Result |
|------|--------|--------|
| Exit card before item work | `981f1d7` | Pushed |
| Quickstart card | `b913a06` | `docs/QUICKSTART-pfy-build.md`. Commands run at `2026-10-31T21:21:27Z`. |
| DoD walkthrough | `a9cc74f` | `docs/ops/MVP-DOD-WALKTHROUGH.md`. Eight GAPs listed at the top. |
| Quickstart command test | `4f87ddf` | `tests/test_quickstart_commands.py`. 3 tests OK in 0.769s. |
| README links | `330faeb` | Two lines under the simple-path block. Root README was not owned by another lane. |
| GAP recheck | `1866938` | Cloudfix moved to `d35af20`. GAPs 1-8 still open. |

## Test evidence

- `nice -n 19 python3 -m unittest tests.test_docs_hygiene`: 2 tests OK (after the quickstart, and again after the walkthrough).
- `nice -n 19 python3 -m unittest tests.test_pfy_build_cloud tests.test_build_preflight tests.test_mvp_1031_receipt tests.test_pfy_build_docs tests.test_docs_hygiene`: 54 tests OK in 6.898s.
- `nice -n 19 python3 -m unittest tests.test_quickstart_commands -v`: 3 tests OK in 0.769s. The planted fence `exit=0` on `./pfy build` fails the checker with `exit 2 != documented 0`. `--local` and `--reap` are refused before `subprocess.run`.
- Same two modules after the recheck: 5 tests OK in 0.847s.

## Red base

`tests.test_pfy_build_local.CloudBuildUnchangedTests.test_help_and_dry_run_stay_the_same` fails on this branch before any of these commits. Re-run here: 1 test, FAILED in 0.058s. Bare `./pfy build --help` is the cloud card. The test still expects `--prompt-file`. Integrate recorded the same failure. This lane did not edit `tests/test_pfy_build_local.py`.

Integrate also recorded `tests.test_local_bench.OutdirPathTests.test_relative_outdir_log_path_safe` when `TMPDIR` is inside the repo. Not re-run here. Full `unittest discover` was not run.

## How each change fails and how it recovers

- Quickstart fence: a documented exit that disagrees with `./pfy` fails `tests.test_quickstart_commands`. Recovery: set `exit=` to the process code. A fence that would start a build, pass `--local`, or pass `--reap` is refused before the process starts. Recovery: keep those commands in `text` fences.
- Walkthrough link: a relative link to a file that is not on this branch fails `tests.test_docs_hygiene`. Recovery: cite `branch:path` as inline code. That is why the cloudfix handoff is not a markdown link.
- README: the two lines point at files on this branch. Recovery if a later lane rewrites the simple-path block: put the same two lines back.
- Dry-run receipt: `./pfy build "quickstart dry run" --dry-run --receipt-dir "$PWD/tmp/quickstart-dry-run"` writes under gitignored `tmp/`. `git status --porcelain` printed no lines. Recovery if a receipt lands in the tree: point `--receipt-dir` at `tmp/`.

## GAPs still open

See `docs/ops/MVP-DOD-WALKTHROUGH.md`. Short form: no branch holds a receipt for unauthenticated (the realfail auth receipt is `no-change`), review-rejected after the danger.sh fix, review-reject then accept, redaction of the planted `xai-` marker, SIGKILL reap of the live grok, `scope-commit-mismatch`, `worktree-failed`, or gate-red then a later PASS. Cloudfix `d35af20` fixes several of these in tests. Its after receipts are gitignored `tmp/` on that worktree.

## Skipped

- `./pfy build --local`: this lane must not pass `--local` to a real run.
- Pregate not run: host busy (`Runner.Worker` pid 2242260 at `2026-10-31T21:29:55Z`).
- `docs/TODO.md`, `docs/PENDING-HANDOFF.md`, `docs/ops/pfy-build-daily.md`, `docs/modules/**`: not owned. T-0110, T-0091, T-0081, and T-0005 do not fit these files. T-0091 stays shelved. T-0005 is a human stage decision (OQ-0003). T-0081 is the excluded cage item.
- No ADR. No open question blocked a fit item.

## Cross-lane requests

- `mvp-realfail2-1031`: commit the fixed receipts for the eight GAPs, or record that the rerun still fails. Tip was still the drop-in `884a16a`.
- `mvp-cloudfix-1031`: the after receipts named in `docs/ops/HANDOFF-mvp-cloudfix-1031.md` (`tmp/auth-after`, `tmp/danger-after`, `tmp/redact-after`, `tmp/sigkill-after`) are not on the branch. A copy under `eval/` would let this walkthrough drop those GAPs.
- `tests/test_pfy_build_local.py` `CloudBuildUnchangedTests.test_help_and_dry_run_stay_the_same`: expect the cloud card on bare `./pfy build --help`, and the dogfood flags on `./pfy build -p --help`. This lane did not edit that file.
- `mvp-daily-card-1031`: `docs/ops/pfy-build-daily.md` is untouched. The demo PASS transcript can still be appended there. This quickstart already quotes `eval/mvp-1031/demo-receipt.json`.

## Gate

Docs and one test module. No runtime change. Gate: pregate plus Reviewer. Pregate not run: host busy. Do not treat this handoff as a Feature GO.

## Next

Lane empty for this worktree. Next step on this branch is a walkthrough update when `origin/bot/mvp-realfail2-1031` or `origin/bot/mvp-cloudfix-1031` commits one of the eight missing receipts. Until then the GAP list at the top of `docs/ops/MVP-DOD-WALKTHROUGH.md` is the status.

Decisions: 8 lines in `docs/ops/AUTONOMOUS-DECISIONS-mvp-docs-1031.md`.
