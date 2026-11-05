# 05 smoke103-timeout

Human: accept.

Why: `timeout_problem` fail-closes a bad PFY_XINTAKE_TIMEOUT before the entry, `xintake_timeout` is unchanged, and only `examples/x-intake-local/smoke_103_105.py` changed. The gate was red before the edit and 2 tests OK after. Review accepted attempt 1.

Cloud commit: 94049ba4c728b3321e027d63979aeadb4db56b31
Landed: 775e34b (Built-by trailer added; author stays pfy-cloud-build)
Wall seconds: 82
Attempts: 1
Review: accept
Exit: 0

Fail: a set PFY_XINTAKE_TIMEOUT that is not a finite number of seconds > 0 exits 2 and the reason names the variable. The entry does not run.
Recover: unset or empty still calls the entry, so a missing bugpatrol reports the operator prereq string.

Tests after land: `tests.test_smoke_103_bad_timeout` and `tests.test_x_intake_smoke_103_105`, 9 OK.

The receipt prose had one em dash in the model tail. It was replaced with " - " before commit. Status, exit, and review verdict were unchanged.
