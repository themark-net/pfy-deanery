# Local rerun

## t5-receipts-outside-repo

Receipt: eval/mvp-1031/local-rerun/t5-receipts-outside-repo/receipt.json
Exit code: 0
Runner exit code: 0
Gate: PASS ok
Gitignored path in the commit: no
Commit: 4aa36fd34d1b9007bbf4887dcd729977aded3ee2
Rerun: ok
Wrapper process exit before the diff check fix: 1
That first check matched pipelines/dogfood/local-bench-4/receipt-coder-next-nommap.json, pipelines/dogfood/local-bench-4/receipt-glm45air-nommap.json, and pipelines/dogfood/local-bench-4/receipt-gpt-oss-nommap.json.
Those paths are already in parent bc865e84e919bb4aac0ae630dd8a900af7bac37d. This commit's diff is only tests/test_x_intake_smoke_117_118.py and tests/test_x_intake_smoke_119_121.py. check-ignore on that diff is empty.
Model was loaded before run: false
Unloaded: true

## t4-timeout-substep

Receipt: eval/mvp-1031/local-rerun/t4-timeout-substep/receipt.json
Exit code: 3
Runner exit code: 3
Gate: TIMEOUT timeout
Gitignored path in the commit: no
Commit: none
Rerun: failed
Attempts: 3 (tests-failed, tests-failed, timeout). No commit, so no gitignored path could land.
Model was loaded before run: false
Unloaded: true
