# 04 smoke098-timeout

Human: accept.

Why: `timeout_problem` fail-closes a bad PFY_XINTAKE_TIMEOUT before the entry, `xintake_timeout` is unchanged, and only `examples/x-intake-local/smoke_098_100.py` changed. The gate was red before the edit and 2 tests OK after. Review accepted attempt 1.

Cloud commit: 5694106559ad8593b57b4a6ffecec544208e22c6
Landed: 4ef4c66 (Built-by trailer added; author stays pfy-cloud-build)
Wall seconds: 103
Attempts: 1
Review: accept
Exit: 0

Fail: a set PFY_XINTAKE_TIMEOUT that is not a finite number of seconds > 0 exits 2 and the reason names the variable. The entry does not run.
Recover: unset or empty still calls the entry, so a missing sponsio reports the operator prereq string.

Tests after land: `tests.test_smoke_098_bad_timeout` and `tests.test_x_intake_smoke_098_100`, 13 OK.
