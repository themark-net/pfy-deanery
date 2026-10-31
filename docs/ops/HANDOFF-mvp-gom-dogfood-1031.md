# Handoff mvp-gom-dogfood-1031

Lane finished. Goal met: six real cloud `./pfy build` runs on Gom Jabbar, each recorded, human-accepted, and cherry-picked to `bot/gom-dogfood-1031`. No merge, no PR, no force push, no `--local`.

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

Gom `bot/gom-dogfood-1031` changes `gomjobbar/cli.py`, `gomjobbar/capture.py`, docs, and tests. That branch needs Tester plus Reviewer. Not a Feature GO. Do not merge it to gom `main`.

## Next

Reviewer reads this branch at the handoff SHA and `eval/gom-dogfood-1031/REPORT.md`. mvp-cloudfix-1031 takes the five requests. The gom operator reviews `bot/gom-dogfood-1031` at `02e421de4cc1a7beca16846b2ac18acc1c28df5b`. No further build from this lane unless a slice is rejected.
