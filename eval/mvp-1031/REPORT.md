# mvp-1031 integrate demo

One real cloud `./pfy build` from the integrate worktree. No `--local`. The task target was a temp fixture repo, not this checkout.

Command:

```text
bash eval/mvp-1031/init_fixture.sh "$PWD/tmp/mvp-fixture-repo"
./pfy build "Make add return the sum of its two arguments so the fixture test passes." \
  --repo "$PWD/tmp/mvp-fixture-repo" \
  --base main \
  --test-cmd "python3 -m unittest test_add" \
  --receipt-dir "$PWD/tmp/mvp-fixture-receipt"
```

The fixture test was red before the build (`add(2, 3)` returned 0).

| Field | Value |
|-------|--------|
| Exit code | 0 |
| Branch | `cloud/make-add-return-the-sum-of-its-two-argum-20261031T210933627529Z` |
| Commit | `ebef4238a7eff8f938747623f7920b3fde74e586` |
| Review verdict | accept |
| Receipt path | `eval/mvp-1031/demo-receipt.json` |
| Checker | `python3 eval/mvp-1031/check_receipt.py eval/mvp-1031/demo-receipt.json` exit 0 |

Demo: PASS.

`git -C` the fixture repo shows that `cloud/` branch at the receipt commit. `add` on that commit returns `a + b`, and `python3 -m unittest test_add` passes on that tree. `pushed` is false. The integrate branch stayed `bot/mvp-integrate-1031`.

## Pass 2

One real cloud `./pfy build` on a throwaway clone of this worktree. No `--local`. No second cloud call. The integrate checkout was not the task target.

Task: on the not-ok branch of `arm_launch_env_session` in `scripts/pfy_enterable_162.py`, store the stripped `next_steps` before returning, and add `tests.test_attach.OpenCodeEnterableTests.test_not_ok_drops_stale_enterable_step`.

Why picked: the not-ok return drops the stripped list, so a stale `enterable` id stays. A local call on this tree before the build printed `STALE_SURVIVES True` with ids `enterable` and `status`. Dogfood run 01 named that bug. The change is two files, the shim plus a behavior test. Neither file is owned by an MVP lane. T-0124 already folded the OpenCode open path. This is the leftover fail path in the shim.

Command (from this worktree):

```text
./pfy build "On the not-ok branch of arm_launch_env_session in scripts/pfy_enterable_162.py, store the stripped next_steps on the result before returning. A caller that passed next_steps with id enterable or session must not see those ids when ok is false. Add tests.test_attach.OpenCodeEnterableTests.test_not_ok_drops_stale_enterable_step in tests/test_attach.py. The test calls arm_launch_env_session with ok false, live FAIL, and a next_steps entry whose id is enterable, then asserts that id is absent, session_reach is FAIL, and enterable is false. The test fails if the early return keeps the stale id. Edit only those two files." \
  --repo "$PWD/tmp/demo2-target" \
  --base demo-base \
  --test-cmd "python3 -m unittest tests.test_attach.OpenCodeEnterableTests.test_not_ok_drops_stale_enterable_step" \
  --writable-test tests/test_attach.py \
  --receipt-dir "$PWD/tmp/demo2-receipt"
```

`--base demo-base` keeps the clone off `origin/main`. `--test-cmd` is the new test, because the default discover is red on two recorded failures outside this task. `--writable-test` allows the edit of the existing test module. `--receipt-dir` is the copy source. The clone was `git clone --local` of this worktree, then `checkout -B demo-base`.

| Field | Value |
|-------|--------|
| Wall time | 91 seconds (2026-10-31T21:39:59Z to 2026-10-31T21:41:30Z) |
| Exit code | 0 |
| Attempts | 1 (status PASS, reason ok) |
| Branch | `cloud/on-the-not-ok-branch-of-arm-launch-env-s-20261031T213959467597Z` |
| Commit | `535d000075744709b2752cec7511d087801f2aa5` |
| Review verdict | accept (reasons empty) |
| Human verdict | yes |
| Receipt path | `eval/mvp-1031/demo-receipt-pass2.json` |
| Checker | `python3 eval/mvp-1031/check_receipt.py eval/mvp-1031/demo-receipt-pass2.json` exit 0 |

Demo 2: PASS.

Human verdict: the cloud commit adds one assignment, `out["next_steps"] = next_steps`, on the not-ok branch, and a test that fails while those ids remain. On the clone, that test passes at the receipt commit. With only the test file and the pre-fix shim, the same test fails: `enterable` is still in `['enterable', 'session', 'env']`. The commit touches only `scripts/pfy_enterable_162.py` and `tests/test_attach.py`. It is not on `bot/mvp-integrate-1031`. This lane does not land it. `pushed` is false.

Functional MVP DoD lines:

1. PASS. Process exit code 0.
2. PASS. Stdout is one line: `PASS ok branch=cloud/on-the-not-ok-branch-of-arm-launch-env-s-20261031T213959467597Z receipt=.../tmp/demo2-receipt/receipt.json`.
3. PASS. Receipt schema `pfy-cloud-build/1`, status PASS, reason ok, exit_code 0, branch starts with `cloud/`, commit is 40 hex chars, review.verdict accept, review.reasons is a list, attempts length 1 and the last status is PASS, gate.cmd is set, gate.before exit 1, gate.after exit 0, recovery is empty, pushed is false, worktree_removed is true.
4. PASS. `git -C tmp/demo2-target rev-parse` of that branch equals `535d000075744709b2752cec7511d087801f2aa5`. During the run the caller stayed `bot/mvp-integrate-1031` at `135eebb` with an empty porcelain. The cloud commit is not that HEAD. The clone stayed on `demo-base`.
5. PASS. `git diff-tree --name-only` of the commit is only the two task paths. No gitignored extra file is in the tree.
6. PASS. Nothing was pushed. No PR was opened. `pushed` is false. The integrate repo has no `cloud/` branch from this run.

## Pass 3

One real cloud `./pfy build` on a throwaway clone of this worktree. No `--local`. No second cloud call. The integrate checkout was not the task target.

Task: stop `tests/test_x_intake_smoke_117_118.py` and `tests/test_x_intake_smoke_119_121.py` from writing `pipelines/smoke` receipts inside the repo, and add `tests/test_x_intake_smoke_117_119_receipts.py` that fails if those bytes change.

Why picked: MVP-2 t5. Those two modules call the smoke with no `PFY_SMOKE_RECEIPT_DIR`, and `_receipt` reads `pipelines/smoke/<entry>/latest.json` in the repo. On this tree, before the build, `test_wrong_kander_version_exits_2` rewrote `pipelines/smoke/kander/latest.json` (1216 bytes to 1179) and `test_agentdescent_wrong_version_exits_2` rewrote `pipelines/smoke/agentdescent/latest.json` (618 bytes to 581). Both files were restored. The third file is the guard test. The smoke scripts stay. This is not the enterable fix (backlog-burn already landed that on this branch). Another lane was running the t4 timeout task locally, so this lane did not pick t4.

Command (from this worktree):

```text
./pfy build "Stop tests/test_x_intake_smoke_117_118.py and tests/test_x_intake_smoke_119_121.py from writing pipelines/smoke receipts inside the repo. Match the setUp in tests/test_x_intake_smoke_112_114.py: each test class creates one temp directory, sets PFY_SMOKE_RECEIPT_DIR on the env passed to the smoke, and _receipt reads that directory. Do not read ROOT/pipelines/smoke for the receipt body. Keep the git check-ignore tests. Do not skip tests or weaken assertions. Do not edit the smoke scripts. Add tests/test_x_intake_smoke_117_119_receipts.py. That test runs tests.test_x_intake_smoke_117_118.XIntakeSmoke117118Tests.test_wrong_kander_version_exits_2 and tests.test_x_intake_smoke_119_121.XIntakeSmoke119121Tests.test_agentdescent_wrong_version_exits_2. It fails if either child is not OK, if either says skipped, or if pipelines/smoke/kander/latest.json or pipelines/smoke/agentdescent/latest.json changes bytes. Today both named tests rewrite those repo files. Edit only those three test files." \
  --repo "$PWD/tmp/demo3-target" \
  --base demo-base \
  --test-cmd "python3 -m unittest tests.test_x_intake_smoke_117_119_receipts" \
  --writable-test tests/test_x_intake_smoke_117_118.py \
  --writable-test tests/test_x_intake_smoke_119_121.py \
  --receipt-dir "$PWD/tmp/demo3-receipt"
```

`--base demo-base` keeps the clone off `origin/main`. `--test-cmd` is the new module, which is absent on the base, so the before gate is red. `--writable-test` names the two existing modules. The clone was `git clone --local` of this worktree at `66a5500`, then `checkout -B demo-base`.

| Field | Value |
|-------|--------|
| Wall time | 421 seconds (2026-10-31T23:53:06Z to 2026-11-01T00:00:07Z) |
| Exit code | 0 |
| Attempts | 1 (status PASS, reason ok) |
| Branch | `cloud/stop-tests-test-x-intake-smoke-117-118-p-20261031T235306753011Z` |
| Commit | `1ed98a4d2d3c39b8099603e60dc87ed41e7340f4` |
| Review verdict | accept (reasons empty) |
| Human verdict | yes |
| Receipt path | `eval/mvp-1031/demo-receipt-pass3.json` |
| Checker | `python3 eval/mvp-1031/check_receipt.py eval/mvp-1031/demo-receipt-pass3.json` exit 0 |

Demo 3: PASS.

Human verdict: the cloud commit adds `setUp` on each test class, sets `PFY_SMOKE_RECEIPT_DIR` in `_env`, and points `_receipt` at that temp directory. The new test runs the two named cases and compares the bytes of the two repo receipts. On a detached worktree of `1ed98a4`, that test passed in 0.209s. The commit touches only the three test paths. It is not on `bot/mvp-integrate-1031`. This lane does not land it. `pushed` is false. The caller stayed `bot/mvp-integrate-1031` at `66a5500` with an empty porcelain. The clone stayed on `demo-base`.

Functional MVP DoD lines:

1. PASS. Process exit code 0.
2. PASS. Stdout is one line: `PASS ok branch=cloud/stop-tests-test-x-intake-smoke-117-118-p-20261031T235306753011Z receipt=.../tmp/demo3-receipt/receipt.json`.
3. PASS. Receipt schema `pfy-cloud-build/1`, status PASS, reason ok, exit_code 0, branch starts with `cloud/`, commit is 40 hex chars, review.verdict accept, review.reasons is a list, attempts length 1 and the last status is PASS, gate.cmd is set, gate.before exit 1, gate.after exit 0, recovery is empty, pushed is false, worktree_removed is true.
4. PASS. `git -C tmp/demo3-target rev-parse` of that branch equals `1ed98a4d2d3c39b8099603e60dc87ed41e7340f4`. During the run the caller stayed `bot/mvp-integrate-1031` at `66a5500` with an empty porcelain. The cloud commit is not that HEAD. The clone stayed on `demo-base`.
5. PASS. `git diff-tree --name-only` of the commit is only the three task paths. No gitignored extra file is in the tree.
6. PASS. Nothing was pushed. No PR was opened. `pushed` is false. The integrate repo has no `cloud/` branch from this run.

Cloud-default daily use, from `eval/mvp-1031/sixtask-int/REPORT.md`: VERDICT GO. Two passes of MVP-2 t1 through t6 on `./pfy build`, review on, no `--local`, no `--no-review`. Pass 1 wall 1243.8s and pass 2 wall 1016.3s. Each pass is 6/6 runner PASS, 6/6 review accept, 6/6 human accept, 6/6 gate PASS.
