# 02 smoke131-timeout

Human: accept.

Why: `main` calls `timeout_problem` imported from `smoke_128_130` and returns 2 before the entry. The function was not copied. Only `examples/x-intake-local/smoke_131_133.py` changed. The gate was red before the edit and 2 tests OK after. Review accepted attempt 1.

Cloud commit: fc03f165b86645705af6af727fd3c311c4d4d905
Landed: 55ad1b1 (Built-by trailer added; author stays pfy-cloud-build)
Wall seconds: 63
Attempts: 1
Review: accept
Exit: 0

Fail: a set PFY_XINTAKE_TIMEOUT that is not a finite number of seconds > 0 exits 2 and the reason names the variable. The entry does not run.
Recover: unset or empty still calls the entry, so a missing jah reports `jah not found ($JAH_BIN, tmp/jevagentharness/.venv/bin/jah, PATH); see the handoff`.

Tests after land: `tests.test_smoke_131_bad_timeout` and `tests.test_x_intake_smoke_131_133`, 40 OK.
