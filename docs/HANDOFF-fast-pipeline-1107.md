# Handoff: fast pipeline slice 1 (2026-11-07)

Branch `bot/fastpipe-1107`. Not pushed. The landing path selects tests from the diff, runs that list once in parallel, and caches a PASS for the git tree. The full suite remains the nightly backstop.

Contract and risk table: [ops/MODULAR-CI.md](ops/MODULAR-CI.md). Pregate flags: [ops/PREGATE.md](ops/PREGATE.md).

## What changed

- `scripts/run_tests.py`: one subprocess per unittest module, fresh `TMPDIR` and `PFY_STATE_DIR` (and XDG dirs) under a run directory. `-j` defaults to `min(16, cpu count)` or `PFY_TEST_JOBS`. `-j 1` runs the same subprocesses one at a time, in sorted order, then the serial list.
- `scripts/test_select.py`: stdlib `ast` import graph over `tests/`, `scripts/`, `pfylib/`, `harness/`, `examples/`, `eval/`, `bootstrap/`, `gui/`, plus root `*.py`. JSON field `source` is `ast`.
- `scripts/test_cache.py`: PASS cache. `affected` and `full` require a receipt whose `rc` is 0.
- `config/test_select.json`: `core_globs`, `risky_globs`, `structural_globs`. Risky globs stay until Tester and Reviewer both agree to remove one.
- `scripts/ci_selected_tests.sh`: the one G0 test step. Ubuntu does not use the cache. Nimo does.
- `examples/eval-harness/run_structural.py --skip-unittests` (or `PFY_SKIP_UNITTESTS=1`) reports `pfylib_unittests` as `SKIP`.
- `.github/workflows/eval-structural.yml`: both G0 jobs skip the embedded discover and call the selector once. Concurrency cancels a superseded branch run and leaves `main` and `master` running.
- `.github/workflows/full-suite-nightly.yml`: hosted `ubuntu-24.04`, cron `17 9 * * *`, plus `workflow_dispatch`. The command is `python3 scripts/run_tests.py` with no module arguments.
- `scripts/pregate.sh`: `--full`, one bwrap-hidden pass of the selection, then only bwrap-sensitive modules again on the host PATH. The summary prints the selection mode and the module count.

`make eval-structural` and the default `pfy build` test command still run a full discover. The heavy lock is unchanged.

## How to use the scripts

From the repo root.

### run_tests.py

```bash
python3 scripts/run_tests.py
python3 scripts/run_tests.py -j 16
python3 scripts/run_tests.py -j 1
python3 scripts/run_tests.py tests.test_catalog_entry_numbers
python3 scripts/run_tests.py --list
python3 scripts/run_tests.py --print-bwrap
python3 scripts/run_tests.py --receipt /tmp/pfy-tests-receipt.json
PFY_TEST_JOBS=4 python3 scripts/run_tests.py
```

Each child is `python3 -m unittest -q <module>`. The child gets its own `TMPDIR`, `TMP`, `PFY_STATE_DIR`, and `XDG_*` directories. `HOME` stays the caller unless `PFY_TEST_ISOLATE_HOME=1`.

Stdout is one line per module: `PASS|FAIL <module> <seconds>s skips=<n>`. A failure also prints the last 40 lines of that module. The last lines are the totals and `receipt: <path>`.

Exit 0 when every module passes. Exit 1 when any module fails. Exit 2 when the list is empty or `-j` is not a positive integer.

The receipt JSON has `modules`, `rc`, `seconds`, `skips`, `jobs`, `serial`, and `results` (no captured output). Skip count is the last `skipped=N` in the unittest output.

Modules in the `SERIAL` list at the top of the script run after the pool, one at a time. Each entry is a module name and a reason. Seven modules are listed today. They fail in the pool and pass alone. Do not empty that list unless a later pair of full runs shows they pass in the pool.

### test_select.py

```bash
python3 scripts/test_select.py --base origin/main
python3 scripts/test_select.py --base origin/main --head HEAD
python3 scripts/test_select.py --paths docs/ops/PREGATE.md
python3 scripts/test_select.py --paths scripts/catalog_check.py
python3 scripts/test_select.py --structural-checks --selection /tmp/pfy-selection.json
python3 scripts/test_select.py --structural-checks --paths docs/ops/PREGATE.md
```

Stdout is JSON: `mode` (`none`, `structural`, `affected`, `full`), `reason`, `modules` (dotted, sorted), `changed`, `source` (`ast`).

`--structural-checks` parses changed JSON, checks links in changed markdown, and runs `catalog_check.py`, `smoke_contract_lint.py`, `check_no_encoded_payloads.py`, and `./pfy help`.

### test_cache.py

```bash
python3 scripts/test_cache.py key
python3 scripts/test_cache.py check --need affected
python3 scripts/test_cache.py check --need full
python3 scripts/test_cache.py record --selection /tmp/pfy-selection.json --receipt /tmp/pfy-tests-receipt.json
```

`check` exits 0 and prints `HIT <key>` when a PASS for this tree is on disk and the stored mode is enough. Otherwise it prints `MISS <key> <reason>` and exits 1.

`record` writes `${PFY_TEST_CACHE:-$HOME/.cache/pfy/test-pass}/<key>.json` by temp file, fsync, and rename. It refuses a non-PASS, a receipt with `rc` other than 0, an `affected` or `full` record with no receipt, and a dirty worktree.

A `full` PASS satisfies a later `structural` or `affected` check for the same key. An `affected` PASS does not satisfy `--need full`.

On this lab the host class is `nimo`. Set `PFY_HOST_CLASS=ubuntu` only in a test. GitHub Actions ignores `PFY_HOST_CLASS` and uses the runner environment.

## Measured numbers

Host: 32 cores, Python 3.14.4, 171 modules. Serial discover baseline, from the ticket and not re-measured: 18 to 22 minutes.

| run | wall | result |
|---|---|---|
| docs-only: select `docs/ops/PREGATE.md` + structural checks | 1.05 s | mode `structural`, 0 modules, checks PASS |
| one file: select `scripts/catalog_check.py` + run the selected module | 1.03 s | mode `affected`, only `tests.test_catalog_entry_numbers`, PASS |
| full suite `-j16` before the serial list | 157.21 s | 3 failed (`tests.test_x_intake_smoke_109_111`, `tests.test_x_intake_smoke_112_115_receipts`, `tests.test_harness2_local_sandbox`), 18 skips. The same three with `-j 1` passed in 165.11 s |
| full suite `-j16` with those three serial modules | 304.17 s | 4 more failures (`tests.test_pfy_build_cloud`, `tests.test_pfy_build_cloud_slice2`, `tests.test_pfy_build_phase_clock`, `tests.test_x_intake_smoke_103_105`). They pass with `-j 1` (cloud pair 151.96 s + 25.69 s on a clean scratch, phase clock 11.69 s, graphjin 1.91 s) |
| full suite `-j16` with all seven serial modules, run 1 | 496.98 s | 171 modules, 0 failed, 18 skips |
| full suite `-j16` with all seven serial modules, run 2 | 495.48 s | 171 modules, 0 failed, 18 skips. No new flakes |

`pfylib/hedge.py` via `--paths` is `affected` with 6 modules. It was not the timed one-file sample.

The two green runs were on this 32-core host while other worktrees also had unittest discovers in progress. Both runs still finished with 0 failures. 496.98 s is about 8.3 minutes, against the 18 to 22 minute serial baseline.

## Risks and recovery

The same table is in [ops/MODULAR-CI.md](ops/MODULAR-CI.md). Short form:

- A missed dynamic import shows up on the nightly full suite. Unknown and unparseable files are already `full`.
- A parallel flake is fixed by a `SERIAL` entry (module, reason), then two more full runs. Seven modules are on that list: the three smoke and harness flakes from the first parallel run, plus `tests.test_pfy_build_cloud`, `tests.test_pfy_build_cloud_slice2`, `tests.test_pfy_build_phase_clock`, and `tests.test_x_intake_smoke_103_105`. Each passed with `-j 1`. If a cloud `setUp` leaves `tmp/cloud-build-tests` behind, delete that directory before the next run.
- A bad cache hit: delete `~/.cache/pfy/test-pass/<key>.json`. Ubuntu CI does not read the cache. `affected` cannot satisfy `--need full`.
- Do not remove a risky glob without Tester+Reviewer. The behavior test locks kalshi, trading, deploy, and secret docs paths to mode `full`.
- `SKIP` on `pfylib_unittests` means the caller runs the suite in the next step. It is printed. It is not a silent skip.

## Next slices

- Light jobs without the global heavy lock.
- Per-tool stage files `data/stages/<tool>.json`.
- Persistent tool cache `~/.cache/pfy/{tools,bin}`. SkillSpector v2.12.0 now lives at `~/.cache/pfy/bin/skillspector`.
- Local-lab off the landing lane.
