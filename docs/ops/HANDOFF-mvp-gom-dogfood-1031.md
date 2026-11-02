# Handoff mvp-gom-dogfood-1031

Wave 5 finished. The earlier goal-met paragraph below is the first six runs. Wave 5 merged `origin/bot/mvp-integrate-1031` (`d6d62db`) and landed six more cloud `./pfy build` runs, all different T-0034 slices, all human-accepted, all on `bot/gom-dogfood-1031`. No merge, no PR, no force push, no `--local`. No build 13.

Pfy branch: `bot/mvp-gom-dogfood-1031` in `~/DEVELOP/pfy-mentat/tmp/mvp-gom-dogfood-1031`.
Gom branch: `bot/gom-dogfood-1031` in `~/DEVELOP/jobbar-master/tmp/gom-dogfood-1031`.
Mark's `~/DEVELOP/jobbar-master/current` stayed `2d26630915783ada9f6631fed125b6c1b566da6c` on `main`. Journal mtime `1790360353`, size `1744896`, after every wave 5 land.

Exit: goal met. Turn cap was six new builds. The other open gom TODO rows stay skipped. Wall clock and host pressure did not fire. No run returned rate-limit.

## Wave 5 done

Pfy merge: `d6d62db6fa9e6b1d3a799a35b6fbefb32649cbe4` (merge, not a rebase). Exit card: `ccd639a5ea51921461855267f312dd4d67a2f46a`.

| n | cloud | gom test | gom product | wall_s |
|---|-------|----------|-------------|--------|
| 07 catch view to | `57e15700113ea1949526cb97a16f1f9a74db141a` | `915e80cfad5631b527494c65383a48f102a36739` | `fe88852978ec008dcab339f6296e23037eb90a28` | 112 |
| 08 catch view cc | `b2b1981c78666b0d7d55828545cc13feea3a11a4` | `af19c0c684ebf7698b5f92d1d70cfe67a058a0dd` | `1bb43270d46a6b18b466e8d1036a41da3ef63009` | 102 |
| 09 catch view date | `2987c4f30a35371ea739f25ada733cefc7153d34` | `4f6db0d370f3aa2aae5c920de953ff7892b9508a` | `c9885f829baad8ecce74705f76756de31e3ce6df` | 107 |
| 10 land mailbox parties | `973cedd1e4cc831d114e78e0734e04207f4fcb31` | `ef2692c00c39a24cc41a99f2f14e6892418a2cba` | `3ecf83f674e668ad064b4ed9c1a54cf154b8d4a8` | 121 |
| 11 land recipients | `5d1ecaa4a7a31ddf64307f2d832a0a7203812daa` | `7ebd92e46fa1cdd8f17dca663259649f9ea123f4` | `04d7ff206e21b7dd15cb8d1bc3f3c2e38e6c747b` | 81 |
| 12 capture list references | `855b079f6298a35214f1611334bb3dd6822c9a39` | `8c8ae3ecfe040da3bbe4f8d6171544304255e8a3` | `c6c42371195ee045ccc84965f1d2ce95085d02ab` | 135 |

Rates: 6/6 PASS, 6/6 review accept, 6/6 human accept, one attempt each, wall sum 658 s, mean 109.7 s. Detail: `eval/gom-dogfood-1031/REPORT.md` section Wave 5.

## Wave 5 how the changes fail and recover

07. `catch --view` hid `to`. Recover: print it only when the stored string is non-empty. Missing and empty stay hidden. `tests/test_catch_view_to.py`.

08. The view hid `cc`. Recover: the same rule for that field. `tests/test_catch_view_cc.py`.

09. The view hid `headers.date`, or a missing `headers` map would have crashed a careless read. Recover: print `date:` only when `headers` is a dict and `headers.date` is a non-empty string. Do not read `raw_source`. `tests/test_catch_view_date.py`.

10. `capture land` kept `message_id` and dropped `from` and `reply_to`, or a wide copy would store `raw_source` on the item. Recover: copy those two strings when they are non-empty, and leave `raw_source` on the catch. `tests/test_land_mailbox_parties.py`.

11. Land dropped `to` and `cc`. Recover: the same rule for the recipient fields. `tests/test_land_recipients.py`.

12. `format_item_line` hid a non-empty `references` list, or it would print the label for an empty list. Recover: append the ids separated by single spaces only when the list is non-empty, and keep `message_id` and `in_reply_to`. `tests/test_capture_list_references.py`.

Report checker. A wave 5 row can claim PASS, or a different attempt count, while the receipt disagrees. Recover: `check_report` names the run and the field. The planted exit on row 01 and the planted attempts on row 03 still fail.

## Wave 5 test evidence

Cloud gate, every run: before exit 1, after exit 0, attempt 1. Receipts under `eval/gom-dogfood-1031/07` through `12`.

Gom worktree after the twelfth land, cwd = the worktree, `JOURNAL_DB_PATH` under scratch: 12 passed in 3.79s.

Pfy: `nice -n 19 python3 -m unittest tests.test_gom_dogfood_1031_report`. The checker covers both tables.

## Wave 5 cross-lane requests (mvp-cloudfix-1031)

Full write-up: `eval/gom-dogfood-1031/REPORT.md` section Wave 5 findings. This lane did not edit the runner.

1. Seeded tests are still tamper. A new test file is no longer hashed. `--writable-test` exists and was not used, because it would let the model edit the red assertion.
2. Default gate is still `python3 -m unittest discover`.
3. Default base is still `origin/main` unless `--base` is set.
4. `_SECRET_EQ` still redacts `user_key` in receipt 07. The value was the fixture id `to-user`.
5. `child_env` still copies the parent environment. Wave 5 scans found no `AKIA`, private-key, `sk_`, `ghp_`, or `xai-` markers.
6. The cloud commit subject is the first 72 characters of the task, cut mid-word.

## Wave 5 gate

Pfy files this wave are the merge plus docs and eval. The report checker was already on the branch. Gate for this lane's docs and eval: pregate plus Reviewer.

pregate not run: host busy. At 2026-10-31T23:51:18Z, `Runner.Worker` pid 3751002 was running. MemAvailable 35.7 GiB, load 7.71, 32 cores, under the pressure line.

Gom `bot/gom-dogfood-1031` now also changes `gomjobbar/cli.py`, `gomjobbar/capture.py`, `docs/modules/capture.md`, and the twelve tests. That branch needs Tester plus Reviewer. Not a Feature GO. Do not merge it to gom `main`.

## Wave 5 next

Reviewer reads this branch at the wave 5 handoff SHA and the Wave 5 section of `eval/gom-dogfood-1031/REPORT.md`. mvp-cloudfix-1031 takes the six requests above. The gom operator reviews `bot/gom-dogfood-1031` at `63d97e302c5cd768a7e92213b2b9374857286cc4`. No further build from this lane. T-0034 stays open for UI surfacing. Parked rows stay parked.

## Earlier finish (first six runs)

Lane finished. Goal met: six real cloud `./pfy build` runs on Gom Jobbar, each recorded, human-accepted, and cherry-picked to `bot/gom-dogfood-1031`. No merge, no PR, no force push, no `--local`.

Pfy branch: `bot/mvp-gom-dogfood-1031` in `~/DEVELOP/pfy-mentat/tmp/mvp-gom-dogfood-1031`.
Gom branch: `bot/gom-dogfood-1031` in `~/DEVELOP/jobbar-master/tmp/gom-dogfood-1031`.
Mark's `~/DEVELOP/jobbar-master/current` stayed `2d26630915783ada9f6631fed125b6c1b566da6c` on `main`, with the same three dirty paths. Journal mtime `1790360353`, size `1744896`, after every land.

Exit: goal met, and the lane is empty of further items that fit the rules. Six of the eight build slots were used. The other open gom TODO rows are skips. Wall clock and host pressure did not fire. No run returned rate-limit.

## Done

Pfy commits on this branch after the exit card `86639b759ad3a9724df6da71a5e997c9d852e5ba`:

| SHA | what |
|-----|------|
| `a50c6cace2e39947926cbc767c8794de68113fed` | six T-0034 task briefs |
| `55c0466115139d18486a02cbd2bc3257fd5f3120` | eval 01 catch view thread |
| `59e15856fa76eb7eaa37fe6593f42ae9e0cbbb7b` | eval 02 catch view meta |
| `960010be901556bb9f3a0511dcd64af7797fdaf3` | eval 03 catch view index |
| `b49a4a6441d7b8f4dcc2e2a7c69300d05f08a56b` | eval 04 catch view parties |
| `3f5148dcd17c1999ec9940b4bab0748f99f0b851` | eval 05 land thread provenance |
| `93300b2d055e94a838bae6ceb7493792ae6a5e3b` | eval 06 capture list thread |
| `0597d274755aef04a0347607504e84e930b2e0de` | report plus `tests/test_gom_dogfood_1031_report.py` |

Gom product commits (trailer `Built-by: pfy-mentat ./pfy build (cloud)`). The test SHA is the parent. Tip `02e421de4cc1a7beca16846b2ac18acc1c28df5b` is the handoff section only.

| n | test | product | cloud |
|---|------|---------|-------|
| 01 | `38cacafe4a1b416b165d9ac0acec5bd024bab896` | `69d99ceb5c6016bd4b5330596dd9b1094fa45f92` | `ddb8e75693394b05e2a18880d68a6e309b1bb573` |
| 02 | `ca1a8fad130b1fba72663c214158079b138ca3f5` | `63ee84be73eb3d38d5e0cfdd7a657bf8455f41c0` | `86b67cae44e9a85eb7d3959040435fc78eddb919` |
| 03 | `4b2f29e72cd826b0da13363faa0a0c93c8113d7e` | `038e18cf69d0a2cc086c7a0e679ff27668b04e53` | `3960757fce438fe83adadafe0dc8ecba38160fba` |
| 04 | `bb69b6460f5489ed61cbf37294d3655593decb52` | `760a163f67c2ea236442b9e6a4261de089e0b2e6` | `26a6d07230c962068491ce7ffa6b6ace14f3bcc3` |
| 05 | `48644529f172ed8fac7822963dd1161be1fe9c54` | `b1288bc98421ecacd30b3359f13d32d31ff1f7fd` | `0c06365b9afbe7012f02cdd351d589e1c6502db6` |
| 06 | `213344387c16f3cfbdaaccebd60bd8e36c40fe41` | `3d9aac7b434e02d93ecab45a97457f5b2069dcb3` | `7600d6cf88477251bd80b56dca59dd8ef82d49c5` |

Rates: 6/6 PASS, 6/6 review accept, 6/6 human accept, one attempt each, wall sum 639 s, mean 106.5 s. Detail: `eval/gom-dogfood-1031/REPORT.md`.

## Skipped

| item | why |
|------|-----|
| T-0022 | parked, OQ-0006 |
| T-0023 | parked, OQ-0011 |
| T-0025 beyond the existing guest and freehire slice | scraper work, rejected |
| T-0027 | rejected (Remote In Tech) |
| T-0028 Playwright connectors | rejected. Local PDF already exists |
| T-0030 | OQ-0007, policy, needs a human |
| T-0031 | OQ-0008. Additive bands are not specified. This lane does not invent a Strong/Good/Moderate/Weak/Poor mapping |
| T-0032 | OQ-0009, out of MVP |
| T-0033 | OQ-0010, example only when the operator asks. Not asked |
| T-0050 | PyInstaller packaging |
| T-0051 | interview prep stays docs until the operator asks for a command |
| further header slices (`to`, `cc`, list `references`) | six slices already prove the runner. More of the same path is not a new gap |
| `scripts/pfy_build_cloud.py` | owned by mvp-cloudfix-1031 |

OQ draft, not a new ADR: T-0031 stays on gom OQ-0008. Do not add career-ops letter bands until that question names the mapping.

## How the changes fail and recover

01. `catch --view` hid `in_reply_to` and `references`. Recover: print them only when the stored string or list is non-empty. `tests/test_catch_view_thread.py`.

02. The view hid `has_attachments` and `size`. Recover: print `yes` or `no`, and an int size, else `0`. `tests/test_catch_view_meta.py`.

03. The last 20 rows were labeled `0..19`. Recover: the label is the journal index (`len(catches) - len(window)`). The red assertion was `[24]` on a 25-row journal. `tests/test_catch_view_index.py`.

04. The view hid `from` and `reply_to`, and a dump of the catch would show `raw_source`. Recover: print those parties only when non-empty, and keep a token that exists only in `raw_source` off the terminal. The test counts stripped lines, because `reply_to:` is a substring of `in_reply_to:`. `tests/test_catch_view_parties.py`.

05. `capture land` kept `message_id` and dropped the thread fields, or a wide copy would store `raw_source` on the item. Recover: copy a non-empty `in_reply_to` string and a non-empty `references` list, and leave `raw_source` on the catch. The test reloads the item through `capture_list`. `tests/test_land_thread_provenance.py`.

06. `format_item_line` hid provenance `message_id` and `in_reply_to`. Recover: append those labels only when the strings are non-empty, and keep id, kind, status, title, compute, and the source label. The test checks the function and `gomjobbar capture list`. `tests/test_capture_list_thread.py`.

Report checker. A row can claim PASS, or a different attempt count, while the receipt disagrees. Recover: `check_report` names the run and the field. `test_planted_mismatch_fails` plants exit `7` on row 01 and attempts `9` on row 03. Both must fail. The real table must produce no errors.

Lane miss, recovered: the task 02 land pytest first ran with the wrong cwd and exited 4 (`tests/test_catch_view_thread.py` not found) after the commit existed. Re-ran from the gom worktree (2 passed), then pushed. Later lands `cd` to the worktree first.

## Test evidence

Cloud gate, every run: before exit 1, after exit 0, attempt 1. Receipts under `eval/gom-dogfood-1031/<n>-<slug>/`.

Gom worktree after each land, cwd = the worktree, `JOURNAL_DB_PATH` under scratch: 1 passed, then 2, 3, 4, 5, then 6 passed in 1.10s.

Pfy: `nice -n 19 python3 -m unittest tests.test_gom_dogfood_1031_report` at 2026-10-31. Ran 2 tests, OK.

Default gom gate, recorded and not used: `python3 -m unittest discover -s tests -t .` on the gom worktree exited 1 (system Python 3.14, no `structlog`, no `pytest`, 35 errors). That is the cloudfix finding, not a product red on the bot branch.

Known pfy reds from the integrate handoff were not re-run and not edited: `tests.test_pfy_build_local.CloudBuildUnchangedTests.test_help_and_dry_run_stay_the_same`, and `tests.test_local_bench.OutdirPathTests.test_relative_outdir_log_path_safe` when `TMPDIR` is inside the repo.

## Cross-lane requests (mvp-cloudfix-1031)

Full write-up: `eval/gom-dogfood-1031/REPORT.md`. This lane did not edit the runner.

1. `tests_tampered` blocks a new test. The red test had to be committed before the build.
2. Default `python3 -m unittest discover` cannot import gom. A missing interpreter must be a usage error, not a product FAIL.
3. Default base `origin/main` on the throwaway clone was Mark's local `main` `2d26630915783ada9f6631fed125b6c1b566da6c`, not the bot branch. Refuse to start when HEAD and the default base differ, unless `--base` is set.
4. `_SECRET_EQ` redacts fixture names such as `user_key` and `token`.
5. `child_env` copies the parent environment into the gate. Scrub secret-named variables. These receipts had no `AKIA`, private-key, `sk_`, or `ghp_` markers.

## Gate

Pfy files are docs, eval, and one test. Gate: pregate plus Reviewer. Tester is not required for a pfy runtime change. No `scripts/` or `pfylib/` edit.

pregate not run: host busy. At 2026-10-31T21:54:47Z, `Runner.Worker` pid 2631906 was running. MemAvailable 57.8 GiB, load 4.53, 32 cores, under the pressure line.

Resume at 2026-10-31T22:07Z found `Runner.Worker` idle and the heavy lock already held, so one full pregate was queued on `3df284d`. At 2026-10-31T22:43:21Z `Runner.Worker` pid 3199955 was running again, and other lanes were waiting on the same lock (pregates for `0c3f133`, `fb759e9`, `4271dcb`, and `582414b`). The queued pregate was stopped before it acquired the lock. No `3df284d` pregate worktree was created. MemAvailable 55.3 GiB, load 3.80, 32 cores, under the pressure line. The six landed gom tests were re-run: 6 passed in 0.90s. The real journal stayed mtime `1790360353`, size `1744896`.

Resume at 2026-10-31T22:52:50Z re-checked both branches against origin (pfy `1352974736bb4cbac99e7f2247dd38e1e9950f8e`, gom `02e421de4cc1a7beca16846b2ac18acc1c28df5b`). `tests.test_gom_dogfood_1031_report`: 2 tests OK. The six landed gom tests: 6 passed in 1.06s. Journal mtime `1790360353`, size `1744896`. Receipt directories have command, diff, receipt, and meta, and a scan found no `AKIA`, private-key, `sk-`, or `ghp_` markers. MemAvailable 45.5 GiB, load 4.81, 32 cores. `Runner.Worker` pid 3199955 still running. pregate not run: host busy. No builds 07 or 08.

Gom `bot/gom-dogfood-1031` changes `gomjobbar/cli.py`, `gomjobbar/capture.py`, docs, and tests. That branch needs Tester plus Reviewer. Not a Feature GO. Do not merge it to gom `main`.

## Next

Superseded by the Wave 5 next section at the top of this file. The first six runs stopped at gom `02e421de4cc1a7beca16846b2ac18acc1c28df5b`. Wave 5 continued from there.
