# Handoff mvp-cloud-perf-1031

Branch `bot/mvp-cloud-perf-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-cloud-perf-1031`. Base `origin/bot/mvp-integrate-1031`. No merge, no PR, no tag.

The head of this branch after the handoff commit is the SHA of that commit. A commit cannot record its own SHA. Product tip before this handoff is `0f87672da4e8ee0e1ec339590075e144cd6413f9`.

Exit: lane empty. The operator stopped the heavy-lock measurement at 2026-10-31 18:10:18 local. Phase timing and two overlap cuts are pushed. The six-build before/after wall comparison was not collected.

## Items done

| Item | SHA | Result |
| --- | --- | --- |
| exit card | `11cf824904163dca9b8f91ce51ce3806a80fe92e` | exits written before product code |
| phase timing | `bce574b1b32fd8523b5dfae646c473f2062cb1b8` | receipt `phases` and `wall_seconds`; 4 phase tests and 61 cloud tests OK |
| cut A | `11bcb7d7fb6bd1b9500d15f62cb5be72f8320310` | default-command after-gate overlaps the flake gate; 7 phase tests and 61 cloud tests OK |
| cut B | `f4a64ecc36a03f052ccaace71f9593c571181dcc` | review overlaps the clean-extract gate after the commit; 10 phase tests and 61 cloud tests OK |
| measure | `0f87672da4e8ee0e1ec339590075e144cd6413f9` | two TIMEOUT rows recorded; 71 tests OK in 25.821s on 2026-11-01T01:17Z |

Doc notes between those commits: `f3faa43` (cut A in the run log) and `44d8199dbbb256c0a76f5ffea10b6827b3747419` (cut B and the measurement plan).

Report: `eval/mvp-1031/perf/REPORT.md`. Rows: `eval/mvp-1031/perf/timeout-rows.json`.

## Measurement evidence

Checkout `bce574b` only. Default gate, `--timeout 600`, `--retries 0`, no `--local`.

| id | wall_s | gate_s | agent_s | before gate |
| --- | --- | --- | --- | --- |
| before-1-1 | 602.155 | 602.035 | 0.0 | exit 124, aborted timeout |
| before-1-2 | 602.147 | 602.016 | 0.0 | exit 124, aborted timeout |
| before-2-1 | 261.376 | 261.249 | 0.0 | exit -15, aborted interrupted |

The first two are the finding. The before-gate was still in unittest progress when the cap fired. After-gate, review, and commit did not start. The third row is the operator interrupt, not a timing. After checkout `f4a64ec` never ran. 602s is the cap, not a suite duration.

## Skipped

- Six-build before/after wall times. The operator wrote: do not rerun `tmp/perf-measure/run.py` under the heavy lock today. A longer `--timeout` would be a new measurement and would hold that lock for hours.
- A timed full `unittest discover` to learn the suite length. Same lock, same reason.
- Follow-on perf edits. The operator said finish, and another edit to `scripts/pfy_build_cloud.py` has no measurement window while mvp-cloudfix-1031 is live on that file.
- `docs/ops/pfy-build-daily.md`. mvp-cloudfix-1031 owns it. See the cross-lane request.
- `docs/TODO.md` and `docs/PENDING-HANDOFF.md`. This handoff is the lane record.
- Pregate. The lane drop-in says do not run `scripts/pregate.sh`. At 2026-11-01T01:18:37Z `Runner.Worker` was idle, MemAvailable was about 68 GiB, and load was about 4.1 on 32 cores. Pregate was still not run.

`origin/main` and `origin/bot/mvp-integrate-1031` have no `phase_clock` (fetched 2026-11-01T01:16Z). This lane did not rebase.

## How each change fails and how we recover

Phase clock (`pfylib/build_phase_clock.py`):

- A phase that never ran must stay 0. The TIMEOUT rows show agent, review, and commit at 0 while the before-gate burned the cap. The pass test fails if a phase key is missing.
- A gate inside commit must not also be billed to commit. Parent time pauses while the child runs. The nesting test fails if commit includes that gate.
- Overlapped review and extract are siblings. The wrappers suppress those names during the pair, then `PhaseClock.add` records each duration. The pass test allows the sum of phases to exceed `wall_seconds` by about the shorter of review and gate. The `--no-review` test still requires the sum to stay within 0.05s of the wall.

Cut A (default post-change gates):

- Custom `--test-cmd` stays serial. The cloud module's shared counter still sees the flake gate as the third invocation. Those 61 tests passed again at the measure commit.
- `PFY_BUILD_SERIAL_GATES=1`, an unchanged tree, or a failed tree copy returns to the serial order. The serial test fails if the two post gates overlap under that switch.
- The copy is `shutil.copytree` of the dirty worktree plus a private gitdir. A git clone would drop uncommitted agent edits. Hardlinks would share the index lock.
- A signal during the pair SIGTERMs both gate process groups. The signal test fails if either child is still alive.
- On the default command both post gates start together, so a red after-gate still runs the flake. A red custom command does not start the flake.

Cut B (review and clean extract):

- The runner commits first, then starts review and `recheck_sha` together. Review does not start before the commit exists.
- Review reject undoes the commit and keeps the worktree edits (`reset --soft` then mixed `reset`). No `cloud/` branch. The retry can still see the files.
- Extract failure undoes the commit with `reset --hard HEAD~1`, same as the old hard reset, so a gitignored helper that the worktree imported does not survive into the retry tree.
- If both fail, the receipt reason is `review-rejected`.
- Interrupt, timeout, rate-limit, unauthenticated, or missing grok after the commit undoes with edits kept, then the existing fail return. No branch.
- `--no-review` stays on serial `commit_paths` (commit, recheck, publish).

## Test evidence

At cut B, already pushed: `tests.test_pfy_build_phase_clock` 10 OK in 11.407s, `tests.test_pfy_build_cloud` 61 OK in 14.493s.

At the measure commit, re-run on this worktree: `nice -n 19 python3 -m unittest tests.test_pfy_build_phase_clock tests.test_pfy_build_cloud`, 71 tests, OK, 25.821s (2026-11-01T01:17Z). The FAIL lines in that run are the failure-path tests printing recovery text. The module result is OK.

No full `unittest discover` in this lane. The heavy lock was busy at survey time, and the operator later forbade another hold.

## Cross-lane requests

mvp-cloudfix-1031 owns `docs/ops/pfy-build-daily.md`. Please add, when that lane next touches the card:

- Receipt fields `phases` (preflight, worktree, agent, gate, review, commit) and `wall_seconds`. Schema stays `pfy-cloud-build/1`.
- `PFY_BUILD_SERIAL_GATES=1` forces the old serial post-change gates.
- The default command copies the dirty worktree for the flake gate (copytree plus a private gitdir). A custom `--test-cmd` stays serial.

No request to edit `tests/test_pfy_build_cloud.py`. The serial custom-command path is what those tests already require.

## Gate

Tester plus Reviewer. This branch changes `scripts/pfy_build_cloud.py` and adds `pfylib/build_phase_clock.py`. The measure commit is docs and eval only. Gate the runtime commits `bce574b`, `11bcb7d`, and `f4a64ec`, then the report at `0f87672`.

Pregate was not run. The drop-in forbids `scripts/pregate.sh` from this lane.

## Next step

When the heavy lock is free and mvp3 is not waiting, measure three file-create tasks on `bce574b` and the same three on `f4a64ec`. Default gate, review on, `--retries 0`, no `--local`. Set `--timeout` above one finished default discover on that host. Do not reuse 600s. Do not merge this branch from the lane.
