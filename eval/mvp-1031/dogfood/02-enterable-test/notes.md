# 02 enterable test

Why picked: rotate to a new test. The same not-ok bug as run 01 is still on this branch (the cloud commit stayed in the throwaway). There is no test that a failed launch drops stale enterable steps. Type: new test.

Result: FAIL tests-tampered, exit 1, three attempts, no branch, review verdict null. Gate before exited 1 because the test module did not exist yet. Gate after did not run. That matches the runner: a new test file is rejected before the after-gate.

The attempt 1 snapshot (attempt.diff) is the right one-line assignment plus a test that fails when the stale id remains and recovers when the stripped list is stored. The runner deleted that tree.

Human accept: no. There is no commit to hand to Mark. The discarded diff would have been acceptable. The blocker is the runner rule, not the edit.

Do not run a second new-test task. Three identical tamper attempts already showed that retry does not escape the rule. Another new-test item would be the same failure with no new information (exit 5).
