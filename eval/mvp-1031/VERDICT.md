# Verdict: cloud-default `./pfy build`

Read at 2026-11-01T00:08:54Z from `origin/bot/mvp-*-1031` tips. This file is a snapshot of those SHAs. It is not a Feature GO. Catalog HOLD 70-75 stays.

## Headline

GO for Mark's daily use.

The daily command is cloud Grok, review on, nothing pushed:

```text
./pfy build "<task>"
```

`--local` stays the opt-in fallback. It is not the default.

Three flags are part of this GO, because the measured passes used them when the defaults did not match the repo:

- Pass `--base REF` when HEAD is not `origin/main`. Help text already says the flag is required in that case. `./pfy build --help` on this branch exits 0 and names it.
- Pass `--test-cmd CMD` when the repo is not the default `python3 -m unittest discover -s tests -t .`. An import error on that default command is `gate-unusable` (exit 2, no grok) in `scripts/pfy_build_cloud.py` `before_gate_block`. A foreign pytest suite still needs an explicit command, as the gom runs did.
- Pass `--writable-test PATH` (repeatable) when an existing test file must change. Other base tests stay hashed. Without the flag, a test edit is `tests-tampered` and the run does not commit.

`./pfy build` with no task exits 2 and prints the daily command, the `-p` dogfood line, and the `--local` line. Help text was checked and left unchanged. `scripts/pfy` is owned by the live cloudfix lane.

## DoD PASS lines

The Functional MVP PASS lines are the six observables in `docs/plans/MVP-PARALLEL-1031.md` on `origin/bot/mvp-plan-1031`. The line-by-line check that quotes each one is integrate pass 2 and pass 3.

Evidence for lines 1-6: `git show dd1db3b3880ac6785b1564a0c486e9622945ce17:eval/mvp-1031/REPORT.md` (blob `698092f0b760`). Pass 2 is the `arm_launch_env_session` task (91 s, commit `535d000075744709b2752cec7511d087801f2aa5`). Pass 3 is the MVP-2 t5 receipt task (421 s, commit `1ed98a4d2d3c39b8099603e60dc87ed41e7340f4`). Both say Demo PASS, human verdict yes, checker exit 0. The copy of `eval/mvp-1031/REPORT.md` on this branch is blob `393c7cb812dc` and does not contain pass 3. Use the tip.

| Line | What PASS requires | Result | Evidence |
|------|--------------------|--------|----------|
| 1 | Process exit code 0 | PASS | Pass 2 and pass 3 both record exit code 0 in that report. [sixtask-int](sixtask-int/REPORT.md) is 12/12 exit 0 (`d642ec1381c534962e628f48028eda602a4f32a3`). |
| 2 | Stdout summary `PASS ok branch=cloud/<slug>-<stamp> receipt=<path>` | PASS | The same report quotes that line for pass 2 and for pass 3. |
| 3 | `receipt.json` schema `pfy-cloud-build/1` with the PASS fields | PASS | Checker `eval/mvp-1031/check_receipt.py` exit 0 on `eval/mvp-1031/demo-receipt.json`, on `eval/mvp-1031/demo-receipt-pass2.json`, and on the pass 3 receipt named in the tip report. The report lists schema, status PASS, reason ok, exit_code 0, branch prefix `cloud/`, 40-hex commit, review.verdict accept, review.reasons list, attempts length 1 last status PASS, gate.cmd, gate.before exit 1, gate.after exit 0, recovery empty, pushed false, worktree_removed true. |
| 4 | `git rev-parse <branch>` equals `commit`. That commit is not the caller's previous HEAD. Caller branch and `git status --porcelain` stay unchanged. No stash, reset, or commit in the caller checkout. | PASS | Pass 2: caller stayed `bot/mvp-integrate-1031` at `135eebb` with empty porcelain. Pass 3: caller stayed at `66a5500` with empty porcelain. The clone stayed on `demo-base`. [realfail](realfail/REPORT.md) row `dirty-caller` matches the same rule (`d09647a37ca8715c75c10aa22a4915fce1cfaaea`). |
| 5 | The commit tree contains only paths the review saw. A gitignored file outside that set is absent. | PASS | Pass 2 `git diff-tree --name-only` is the two task paths. Pass 3 is the three test paths. [realfail](realfail/REPORT.md) row `gitignored-extra`: `ignored-extra.txt` was absent from commit `696dc4e`. `git show 44b28d48624b7724356dd2ccfe49a93ab66bd4ce:eval/mvp-1031/realfail2/REPORT.md` row `scope-commit-mismatch` matches (exit 1, no branch). realfail2 is not on this branch. |
| 6 | Nothing pushed. No PR. `pushed` is false. | PASS | Pass 2 and pass 3 say nothing was pushed, no PR, and the integrate repo has no `cloud/` branch from the run. [sixtask-int](sixtask-int/REPORT.md) and [selfhost](../selfhost-1031/REPORT.md) record the same for their throwaway clones. |

The first integrate demo (fixture `add`, commit `ebef4238a7eff8f938747623f7920b3fde74e586`, checker exit 0 on `eval/mvp-1031/demo-receipt.json`) records exit 0, review accept, and `pushed` false. It does not walk lines 4 and 5 in prose. Those two lines rest on pass 2 and pass 3.

## Older six-task NO-GO, and why it moved

[sixtask/REPORT.md](sixtask/REPORT.md) on `177940ed09cd11edad7ad214216e42bbbabfebcb` is NO-GO for cloud-default `./pfy build` as the daily command, against the MVP-2 bar of 6/6 gate and 6/6 review accept.

That pass used the cloud runner before `--writable-test`. t1, t2, t3, and t6 were runner PASS, review accept, human accept, one attempt. t4 and t5 exited 1, reason `tests-tampered`, three attempts, no commit, review never stored. The canonical MVP-2 gate rerun was 0 on all six trees, and a human accepted all six diffs. Runner PASS 4/6, review accept 4/6, human accept 6/6, wall 2778.0 s. The variance pass repeated 4/6 (wall 2356.0 s). `--retries 0` repeated 4/6 (wall 944.3 s). Extra attempts did not create a commit for t4 or t5. Detail: [sixtask/findings/writable-test.md](sixtask/findings/writable-test.md).

[sixtask-int/REPORT.md](sixtask-int/REPORT.md) on `d642ec1381c534962e628f48028eda602a4f32a3` is VERDICT GO. Two passes of t1 through t6 on `./pfy build`, review on, no `--local`, no `--no-review`, `--timeout 900`. `--writable-test` was passed only for t4 (`tests/test_x_intake_smoke_112_114.py`) and t5 (the 117 and 119 test modules). t1, t2, t3, and t6 passed no writable path. Each task was one attempt.

| Pass | Runner PASS | Review accept | Human accept | Canonical gate | Wall |
|------|-------------|---------------|--------------|----------------|------|
| 1 | 6/6 | 6/6 | 6/6 | 6/6 | 1243.8 s |
| 2 | 6/6 | 6/6 | 6/6 | 6/6 | 1016.3 s |

That is the bar the older trial missed, met twice on the integration tip.

## Other measured use

| Lane | Tip | What was measured |
|------|-----|-------------------|
| selfhost | `5fb063e17e9c4f18b18239e66b4e7cb090b99327` | [selfhost REPORT](../selfhost-1031/REPORT.md): tried 15, runner PASS 14, human accept 13. Median wall of the 13 accepts is 119 s. Item 03 was runner PASS and review accept, then human reject: the diff dropped the content hash of a regular file a symlink names. Item 08 was runner FAIL and review reject: the pull-wins task and `test_h` encode opposite priorities, and that runner could not edit tests. |
| backlog-burn | `84db544488af6d3970e1231834d55b04469c54a2` | [backlog-burn REPORT](backlog-burn/REPORT.md): 6/6 receipt PASS, review accept, human accept. Walls 53, 784, 28, 37, 116, 294 s. |
| gom dogfood | `88a841babc958726d990fdc790f56ee6b4d48abc` | `git show 88a841babc958726d990fdc790f56ee6b4d48abc:eval/gom-dogfood-1031/REPORT.md`. Wave 1 is 6/6 and wave 5 is 6/6. Together 12/12 PASS, review accept, human accept, one attempt each. Wall sums 639 s and 658 s. The copy of that report on this branch is blob `bde8e2888942` and does not include wave 5. |
| dogfood | `e404b42b2c36b6e70582a4be85429d3c83b9694f` | [dogfood REPORT](dogfood/REPORT.md): 9/10 gate, review, and human. Median wall 112 s. Run 02 is `tests-tampered` on a new test file ([F1](dogfood/findings/F1-tests-tampered-new-file.md)). Gom wave 5, on a later runner, says a brand-new test file is no longer in the tamper hash. An edit of an existing test still needs `--writable-test`. |
| dogfood2 | `b90ae61ee7d46abc8d32dc318d964f0bc2260a18` | `git show b90ae61ee7d46abc8d32dc318d964f0bc2260a18:eval/dogfood2-1031/REPORT.md`. 7/8 gate, review, and human. Median wall 529 s. Run 07 is TIMEOUT exit 3 after a review reject (high finding F3: the receipt lost the unified diff when the worktree was removed). Run 08 PASS. This lane was still running at read time, so the count can move. The report is not on this branch. |
| realfail | `d09647a37ca8715c75c10aa22a4915fce1cfaaea` | [realfail REPORT](realfail/REPORT.md). Matching rows include dirty caller, gitignored extra, gate red, no-change, timeout, both interrupts, and simulated rate-limit (exit 4, recovery names `./pfy build --local`, and that command was not started). Findings on that first pass: reap left grok alive, review accepted `danger.sh` as `rm -rf /`, empty HOME became `no-change`, and a planted marker survived in the receipt. |
| realfail2 | `44b28d48624b7724356dd2ccfe49a93ab66bd4ce` | `git show 44b28d48624b7724356dd2ccfe49a93ab66bd4ce:eval/mvp-1031/realfail2/REPORT.md`. Not on this branch. Those four findings are marked fixed. Review rejected `danger.sh` and it was not committed. One finding remains: a missing `--base` exits 2 with `base ref not found` and writes no receipt. The failure table wants exit 1, reason `worktree-failed`. Caller HEAD and status stayed unchanged. |
| realfail3 | `a4c80a12b4dd416470441bef9c6a80489193c15d` | [realfail3 REPORT](realfail3/REPORT.md). Two findings: a hung gate was recorded as `tests` (exit 1), not `timeout` (exit 3). `tmp` mode 555 was `runner-crash`, not `worktree-failed`. The other rows match, including dirty tree, detached HEAD, and two concurrent builds. |
| review-quality | `d69967b54a88c9205bb26321e6e26c4eb87b1cd5` | Planted set is on that tip under `eval/mvp-1031/review-quality/`. No `REPORT.md` with false-accept or false-reject counts. The lane was running `run_review.py --round before` at read time. |
| cloud-perf | `bce574b1b32fd8523b5dfae646c473f2062cb1b8` | No `eval/mvp-1031/perf/REPORT.md` on that tip. Phase seconds may be on the receipt. A before/after wall measurement is not published. |
| selfhost2 | `1b7722dd22318d3a78e72541fa2067077de7b6c5` | No report. One receipt path, `eval/selfhost2-1031/01-ad-snap/receipt.json`. The lane was still running. |
| MVP-2 | `origin/main` | [eval/mvp2/REPORT.md](../mvp2/REPORT.md). Cloud arm 6/6 gate and 6/6 review accept in 583.6 s. Local arm 5/6 gate and 4/6 review accept in 1694.0 s. |
| MVP-3 | this branch | [eval/mvp3/REPORT.md](../mvp3/REPORT.md). Local review-and-retry: gate 5/6, human accept 4/6, wall 3859.9 s. Local stays NO-GO as the default. |

Integrate pass 3 on the tip above also records the sixtask-int GO in its own closing paragraph.

## Open risks

These do not flip lines 1-6 on pass 2, pass 3, or the two sixtask-int passes. They are why a review accept is not a substitute for reading the diff, and why a few failure-table rows are still wrong.

1. Review false accept, once, on selfhost item 03 (content hash replaced by a `:target` marker). The later `danger.sh` / `rm -rf /` case was fixed on realfail2: the reviewer rejected and the file was not committed. review-quality has not published a rate.
2. A missing base ref is exit 2 usage with no receipt (realfail2). The operator card's `worktree-failed` row is the intended recovery. The runner behavior is the cross-lane request already filed for mvp-cloudfix-1031.
3. A hung gate is recorded as `tests`, not `timeout` (realfail3). An unwritable `tmp` is `runner-crash`, not `worktree-failed` (realfail3).
4. dogfood2 run 07 timed out after a review reject, and the receipt dropped the unified diff (F3). Run 08 then passed the corrected task.
5. Commit subjects are the task text cut at 72 characters, often mid-word (dogfood2 F1, gom wave 5). Subjects are not a PASS line.
6. Gom still needed `--base`, an explicit pytest command, and a pre-seeded red test. `--writable-test` was not used there, because it would let the model edit the assertion the lane wanted frozen.
7. cloud-perf has no published before/after numbers. sixtask-int walls are 1016.3 s and 1243.8 s for six tasks, against MVP-2 cloud 583.6 s for six tasks with no review loop in that older arm. Four of the old sixtask PASS tasks summed to 630.6 s. Daily small tasks in selfhost, gom, and dogfood are often near 100 s, with outliers (backlog-burn 784 s, dogfood2 1490 s and 2942 s).
8. The integrate process was still running at read time. A later pass on that branch can add rows this snapshot does not have. dogfood2 and selfhost2 were also still running.

## How this verdict fails and how to recover

This file fails if a later tip reverses a cited PASS and a reader still treats the headline as current. Recovery: re-read the tip named in the table, replace the row, and change the headline if lines 1-6 or the six-task bar no longer hold. Do not edit the historical sixtask or selfhost reports to match this file.

A second failure is citing the worktree copy of `eval/mvp-1031/REPORT.md` or `eval/gom-dogfood-1031/REPORT.md`. Those blobs are older than the tips above. Recovery: use the `git show <sha>:<path>` lines in this file.
