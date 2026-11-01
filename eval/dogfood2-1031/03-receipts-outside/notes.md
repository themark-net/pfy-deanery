# 03 receipts outside the repo

Why picked: eval/mvp3/tasks/t5 and the mvp3 handoff. The 117 and 119 suites still call the smoke with no PFY_SMOKE_RECEIPT_DIR, so write() lands pipelines/smoke/<entry>/latest.json in the repo. Type: two existing test files. The gate tests/test_mvp2_t5_receipts.py was copied from eval/mvp2/gates and committed only on the throwaway before the run. --writable-test names the two suites so the runner allows those edits.

Gate before exit 1 (kander latest.json appeared). Gate after exit 0. Review accept. One attempt. Wall 223 seconds.

Diff: 2 files, 32 insertions, 2 deletions (34 changed lines). Patch is 3676 characters, under the 12000 character review cap. This run is below the 60 line aim. It does not show truncation.

Human accept: yes. Each suite keeps one temp directory per test, sets PFY_SMOKE_RECEIPT_DIR on the smoke env, and reads the receipt from that directory. Smoke scripts are untouched. The commit contains only the two test files, so a gitignored repo receipt did not ride along. The gitignore tests in both modules still pass.

Cloud commit subject is the task text cut at 72 characters ("119_1"). Same runner finding as tasks 01 and 02. The cut is in scripts/pfy_build_cloud.py where the subject is the task text sliced to 72 characters. Cherry-picked as 507cfcf with the Built-by trailer. The behavior test is added on this branch in the following commit. It was written before the run.

Pushed false. worktree_removed true.
