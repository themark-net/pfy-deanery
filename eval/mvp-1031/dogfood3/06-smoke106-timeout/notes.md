# 06 smoke106-timeout

Human: accept.

Why: `timeout_problem` fail-closes a bad PFY_XINTAKE_TIMEOUT before the entry, `xintake_timeout` is unchanged, and only `examples/x-intake-local/smoke_106_108.py` changed. The gate was red before the edit and 2 tests OK after. Review accepted attempt 1.

Cloud commit: 8d09aef936e2cc6d122733431e9b62e861deb128
Landed: 98e5795fcc1a85a6c2b02a42f78c47456e80ca10 (Built-by trailer added; author stays pfy-cloud-build)
Wall seconds: 72
Attempts: 1
Review: accept
Exit: 0

Fail: a set PFY_XINTAKE_TIMEOUT that is not a finite number of seconds > 0 exits 2 and the reason names the variable. The entry does not run.
Recover: unset or empty still calls the entry, so a missing rulora package reports the operator prereq string.

Tests after land: `tests.test_smoke_106_bad_timeout` and `tests.test_x_intake_smoke_106_108`, 13 OK.
