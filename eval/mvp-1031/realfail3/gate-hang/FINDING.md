# FINDING: a hung gate is recorded as tests

Lane mvp-realfail3-1031. This lane did not edit the runner.

## Command

Throwaway repo under this worktree's `tmp/realfail3-targets/gate-hang` (not committed). The gate script exits 0 on its first call and then sleeps. `--timeout` was 180. `--retries` was 0. `--no-review` was set.

```text
./pfy build "In app.py change the line value = 0 to value = 1. ..." \
  --repo <throwaway> --base HEAD --retries 0 --no-review --timeout 180 \
  --test-cmd "<python> eval/mvp-1031/realfail3/gates/hang_once.py <counter>" \
  --receipt-dir eval/mvp-1031/realfail3/gate-hang
```

## Receipt

`status` FAIL, `reason` tests, `exit_code` 1, `branch` null, `commit` null, `recovery` empty.

`gate.before.exit` is 0 and the tail is `pass-before`. The implement call finished and set `app.py` to `value = 1`. `gate.after.exit` is 124 and the tail is `gate timeout`. No `cloud/` branch. Caller porcelain stayed empty.

## Expected

The failure table's Timeout row: exit 3, `status` TIMEOUT, `reason` timeout, no commit. Recovery tells the operator to rerun with a longer `--timeout`.

The no-commit part held. Status, reason, exit, and recovery did not. The runner's `gate()` keeps a timeout as exit 124, and `execute` then treats any non-zero gate exit as `tests`.

## Suggested fix

In `CloudBuild.gate`, when `run_command` returns status `timeout`, mark the gate record aborted as `timeout`. In `execute`, if the before-gate or the after-gate aborted as `timeout`, return `fail("TIMEOUT", "timeout", EXIT_TIMEOUT, "Rerun with a longer --timeout.")`. Do not record `tests`. Do not commit. Do not start another attempt.

Add a behavior test with a gate that sleeps and a short `--timeout`. Assert exit 3, reason `timeout`, recovery containing `--timeout`, and no branch.

Do not apply this on the realfail3 branch. mvp-cloudfix-1031 owns the runner.
