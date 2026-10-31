# t4 timeout reasons name the sub-step

Level: medium
Base SHA: 997d89264495861a178713ccf7d4447ea828afc4
Files likely touched: examples/x-intake-local/smoke_112_114.py, tests/test_x_intake_smoke_112_114.py
Gate: python3 -m unittest tests.test_mvp2_t4_timeout_step tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_overtime_timeout_reason_is_shared_text tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_festival_timeout_reason_is_shared_text tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_overtime_daemon_stop_timeout_uses_shared_text
files: examples/x-intake-local/smoke_112_114.py, tests/test_x_intake_smoke_112_114.py

The acceptance test `tests/test_mvp2_t4_timeout_step.py` is already in the tree. Do not edit that file. Do not commit.

Timeouts in `examples/x-intake-local/smoke_112_114.py` name the entry (`overtime`, `festival`) instead of the sub-step that actually timed out.

Required behavior, with `PFY_XINTAKE_TIMEOUT=0.4`:

- The overtime smoke's `new` command times out: exit 1, receipt reason exactly `new timeout after 0.4s`.
- Festival's `fest --version` times out: exit 1, receipt reason exactly `version timeout after 0.4s`.

Use `timeout_reason` so the text stays the shared form. Catch the timeout at that command. Do not relabel every timeout in `main` with one fixed word.

You may edit only these two assertions in `tests/test_x_intake_smoke_112_114.py`, and no other line in that file:

- `test_overtime_timeout_reason_is_shared_text` expects `overtime timeout after 0.4s`. Change that expected string to `new timeout after 0.4s`.
- `test_festival_timeout_reason_is_shared_text` expects `festival timeout after 0.4s`. Change that expected string to `version timeout after 0.4s`.

Leave `test_overtime_daemon_stop_timeout_uses_shared_text` and every other test unchanged.

Gate command: `python3 -m unittest tests.test_mvp2_t4_timeout_step tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_overtime_timeout_reason_is_shared_text tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_festival_timeout_reason_is_shared_text tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_overtime_daemon_stop_timeout_uses_shared_text`
