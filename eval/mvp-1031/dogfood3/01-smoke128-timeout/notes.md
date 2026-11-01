# 01 smoke128-timeout

Human: accept.

Why: `timeout_problem` matches the smoke_140 check, `main` returns 2 before the entry, unset or empty still reports the missing node, and only `examples/x-intake-local/smoke_128_130.py` changed. The gate was red before the edit and 2 tests OK after. Review accepted attempt 1.

Cloud commit: d7c32ffbddd78d792094646d2cf0a394df241530
Landed: 2587cad (Built-by trailer added; author stays pfy-cloud-build)
Wall seconds: 63
Attempts: 1
Review: accept
Exit: 0

Fail: a set PFY_XINTAKE_TIMEOUT that is not a finite number of seconds > 0 exits 2 and the reason names the variable. The entry does not run.
Recover: unset or empty still calls the entry, so a missing node reports `node not found ($NODE_BIN, tmp/node/bin/node, PATH)`.

Tests after land: `tests.test_smoke_128_bad_timeout` and `tests.test_x_intake_smoke_128_130`, 44 OK.
