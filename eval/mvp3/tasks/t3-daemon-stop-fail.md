# t3 overtime daemon-stop timeout is a failure

Level: medium
Base SHA: 997d89264495861a178713ccf7d4447ea828afc4
Files likely touched: examples/x-intake-local/smoke_112_114.py
Gate: python3 -m unittest tests.test_mvp2_t3_daemon_stop tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_overtime_daemon_stop_timeout_uses_shared_text
files: examples/x-intake-local/smoke_112_114.py

The acceptance test `tests/test_mvp2_t3_daemon_stop.py` is already in the tree. Do not edit it. Do not edit `tests/test_x_intake_smoke_112_114.py`. Do not commit.

In `smoke_overtime` (`examples/x-intake-local/smoke_112_114.py`), a `daemon stop` that raises `subprocess.TimeoutExpired` is recorded on the step and then ignored. If no `overtimed.lock` is left behind, the smoke still returns 0 and the reason says the daemon stopped. That success sentence is wrong.

When `daemon stop` times out and the lock is not alive, return 1 and set the receipt reason to the same timeout text already stored on the step: `overtime daemon stop timeout after <seconds>s` from `timeout_reason("overtime daemon stop", ...)`. Keep the existing step record. A stop that returns and a still-live lock must still fail with the existing "daemon still running" reason. A clean stop with no live lock must still pass.

Gate command: `python3 -m unittest tests.test_mvp2_t3_daemon_stop tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_overtime_daemon_stop_timeout_uses_shared_text`
