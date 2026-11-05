# t5 117 and 119 tests must not write repo receipts

Level: slightly hard
Base SHA: 997d89264495861a178713ccf7d4447ea828afc4
Files likely touched: tests/test_x_intake_smoke_117_118.py, tests/test_x_intake_smoke_119_121.py
Gate: python3 -m unittest tests.test_mvp2_t5_receipts
files: tests/test_x_intake_smoke_117_118.py, tests/test_x_intake_smoke_119_121.py
require: PFY_SMOKE_RECEIPT_DIR in tests/test_x_intake_smoke_117_118.py, tests/test_x_intake_smoke_119_121.py

The acceptance test `tests/test_mvp2_t5_receipts.py` is already in the tree. Do not edit it. Do not commit. Do not change the smoke scripts.

`tests/test_x_intake_smoke_117_118.py` and `tests/test_x_intake_smoke_119_121.py` call the smoke without `PFY_SMOKE_RECEIPT_DIR`, so `write()` in `examples/x-intake-local/smoke.py` drops `pipelines/smoke/<entry>/latest.json` inside the repo. Later suites already avoid that. Match `tests/test_x_intake_smoke_112_114.py`: one temp directory per test, put it in `PFY_SMOKE_RECEIPT_DIR` on the env passed to the smoke, and read the receipt from that directory.

`test_wrong_kander_version_exits_2` and `test_agentdescent_wrong_version_exits_2` must still pass and must not create or modify `pipelines/smoke/kander/latest.json` or `pipelines/smoke/agentdescent/latest.json`. The gitignore tests in both modules must still pass. Do not skip tests. Do not weaken assertions. Only these two test modules may change.

Gate command: `python3 -m unittest tests.test_mvp2_t5_receipts`
