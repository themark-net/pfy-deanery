# Handoff mvp-sixtask-int-1031

Branch `bot/mvp-sixtask-int-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-sixtask-int-1031`. Base `origin/bot/mvp-integrate-1031` at `0c3f133`. No merge, no PR, no tag.

VERDICT: GO. Two passes of MVP-2 t1 through t6 through cloud `./pfy build` on this tip. Each pass is 6/6 runner PASS, 6/6 review accept, and 6/6 human accept. Report: `eval/mvp-1031/sixtask-int/REPORT.md` (`af53460`). No findings file. The runner was not edited.

## Items done

| Item | SHA | Result |
| --- | --- | --- |
| loop card | `627fd6d` | exits written before any build |
| report checker | `cc3b275` | 11 tests, 1 skipped, OK |
| pass1 t1 | `6f1c568` | PASS, 163.4s, 1 attempt, review accept, human accept |
| pass1 t2 | `f573cf3` | PASS, 65.7s, 1 attempt, review accept, human accept |
| pass1 t3 | `39cc194` | PASS, 366.3s, 1 attempt, review accept, human accept |
| pass1 t4 | `5c14473` | PASS, 337.8s, 1 attempt, review accept, human accept |
| pass1 t5 | `5df0448` | PASS, 215.3s, 1 attempt, review accept, human accept |
| pass1 t6 | `d12ba6a` | PASS, 95.3s, 1 attempt, review accept, human accept |
| pass2 t1 | `53b7e22` | PASS, 150.5s, 1 attempt, review accept, human accept |
| pass2 t2 | `da98b97` | PASS, 58.4s, 1 attempt, review accept, human accept |
| pass2 t3 | `ef66025` | PASS, 208.1s, 1 attempt, review accept, human accept |
| pass2 t4 | `1d1507f` | PASS, 349.0s, 1 attempt, review accept, human accept |
| pass2 t5 | `a3aa54e` | PASS, 174.3s, 1 attempt, review accept, human accept |
| pass2 t6 | `399408a` | PASS, 76.0s, 1 attempt, review accept, human accept |
| report | `af53460` | VERDICT GO. Checker 12 tests OK |

Pass 1 wall 1243.8 s. Pass 2 wall 1016.3 s. Twelve cloud builds. No `--local`. No `--no-review`. No rate-limit retry. Receipts: `eval/mvp-1031/sixtask-int/receipts/<pass>/<task>/`.

## Writable paths

Passed only where the task file says a test must change.

- t4, both passes: `--writable-test tests/test_x_intake_smoke_112_114.py`
- t5, both passes: `--writable-test tests/test_x_intake_smoke_117_118.py` and `--writable-test tests/test_x_intake_smoke_119_121.py`
- t1, t2, t3, t6: no `--writable-test`

The planted `tests/test_mvp2_t*.py` gates stayed hashed. Every meta has `acceptance_unchanged` true and canonical gate rerun exit 0.

## What the prior NO-GO was

`eval/mvp-1031/sixtask/REPORT.md` was NO-GO because t4 and t5 exited `tests-tampered` on a runner with no `--writable-test`. Those two tasks pass on this tip when the flag names the files above. The outcome class held across both passes. Comment wording and the t3/t4 control flow differed between passes. Both diffs still match the task text. Detail is in the report section "What moved".

## Skipped

- Pregate not run. The drop-in says the operator runs `scripts/pregate.sh`. `Runner.Worker` was also live (pid 3751002), so the host was busy.
- No `--retries 0` arm. The drop-in asks for two passes. That arm already exists under `eval/mvp-1031/sixtask/retries0/`.
- `docs/TODO.md` and `docs/PENDING-HANDOFF.md` were not edited. This handoff is the lane record.
- No third pass. Both passes met the bar.

## Test evidence

`nice -n 19 python3 -m unittest tests.test_mvp_1031_sixtask_int_report`: 12 tests, OK, including the live `REPORT.md`.

`python3 eval/mvp-1031/sixtask-int/check_report.py eval/mvp-1031/sixtask-int`: `CHECK_OK`.

Cloud evidence is the twelve receipts. Each `run.log` was secret-scanned before commit (0 hits).

## How this fails and how we recover

- A report row that disagrees with `receipt.json` or `meta.json`, a totals line that is not the sum, a `VERDICT: GO` without both passes at 6/6, or a recorded command that contains `--local` or a different writable list, makes `check_report` exit 1. Recover: fix the receipt or run `python3 eval/mvp-1031/sixtask-int/check_report.py --write eval/mvp-1031/sixtask-int`, then re-run the unittest.
- `check_report.py --write <root>` used to take `--write` itself as the directory and raised `FileNotFoundError` on `./--write/REPORT.md`. The flag is now skipped when choosing the root. The new test fails if that directory appears.
- Running t4 or t5 without the paths above fails `tests-tampered` before review, which is the prior NO-GO. Recover: pass only those paths. This lane did not change `scripts/pfy_build_cloud.py`.

## Cross-lane requests

None. No file owned by another lane needed an edit.

## Gate

Pregate plus Reviewer. This lane is eval, test, and docs. It does not change the runtime runner. Pregate was not run here.

## Next step

Integration can cite `eval/mvp-1031/sixtask-int/REPORT.md` as GO for the six-task bar on tip `0c3f133` plus this lane. The operator runs pregate when `Runner.Worker` is idle. Do not merge this branch from the lane.
