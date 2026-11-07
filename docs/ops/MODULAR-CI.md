# Modular CI

Landing a change runs the tests that change can affect, once, and caches a PASS for that git tree. The full suite still runs nightly. This page is the operator and agent contract for that split.

## Standing rule

- Run only the tests a change can affect.
- Run tests once per commit and cache the result.
- No global lock or single runner for light jobs.
- Run non-GPU checks in parallel on hosted runners or containers.
- Give each tool its own state file.
- Cache tool and image layers.
- Only jobs bound by local-model token speed get a long serialized lane.
- The full suite runs nightly as a backstop.
- Trading, release and secret changes always get the full run.

## This slice

Done on `bot/fastpipe-1107`:

- `scripts/run_tests.py` runs one unittest module per subprocess.
- `scripts/test_select.py` maps a diff to `none`, `structural`, `affected`, or `full`. The source recorded in the JSON is `ast`. The codebase-memory binary is not consulted, so ubuntu and nimo select the same modules.
- `scripts/test_cache.py` stores a PASS keyed by tree, `config/test_select.json`, Python version, and host class.
- Pregate runs the selected suite once. G0 ubuntu and G0 nimo each run it once. Nimo reuses the pregate cache when the key matches.
- `.github/workflows/full-suite-nightly.yml` runs the full list on `ubuntu-24.04` at 09:17 UTC, and on `workflow_dispatch`.

Still in place, on purpose:

- The heavy lock `~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock` and the one-pregate-at-a-time limit. The next slice takes light jobs off that lock.
- `make eval-structural` still calls `run_structural.py` without `--skip-unittests`, so that Make target still runs a full discover.
- `pfy build` still defaults to `python3 -m unittest discover -s tests -t .`.

## How a landing run is chosen

`config/test_select.json` holds `core_globs`, `risky_globs`, and `structural_globs`. The comment in that file is the rule: risky globs must never be removed without Tester+Reviewer.

| mode | when | what runs |
|---|---|---|
| `none` | the diff is empty | no unittest |
| `structural` | only docs, markdown outside `tests/`, or catalog data under `sources/` or `data/` that tests do not reference | JSON parse of changed JSON, markdown links in changed markdown, `catalog_check.py`, `smoke_contract_lint.py`, `check_no_encoded_payloads.py`, `./pfy help` |
| `affected` | a test imports a changed module (transitively), references a changed path by string, or is the changed test file | those modules |
| `full` | `.github/`, the selector or the runner, pregate, shared test helpers, a module imported by more than 40% of test modules, the Makefile, the `pfy` launchers, a risky path, an unknown file, or an unparseable file | every `tests/test_*.py` |

Risky paths match case-insensitively: kalshi, polymarket, trading, paper, LIVE_HARD_OFF, deploy, release, publish, wrangler, secret, token, `.dev.vars`, auth. A docs file whose name contains one of those words is `full`. That is the safe direction.

A changed data file under `sources/` or `data/` that a test mentions by path or by a specific basename is `affected`, and those tests are added.

## One suite in pregate, plus the sandbox re-run

Ubuntu-24.04 has no usable bwrap. Pregate's `ubuntu-parity` check mirrors that: it runs the selected modules once with `bwrap` removed from `PATH`. That is the only full pass of the selection.

`eval-structural` then runs the G0 commands with `run_structural.py --skip-unittests`. The unittest check is printed as `SKIP` with a reason. It is not a silent pass of the suite. After that, modules whose source contains the string `bwrap` run again with the host `PATH`, so the sandbox cases still execute on nimo. On this tree that subset is 22 of 171 modules (`python3 scripts/run_tests.py --print-bwrap`).

`ci-parity` still runs the two runtime-dir tests with bwrap hidden. The standalone `suite` check stays skipped unless `--force-suite` or `--only suite`. `--full` ignores the diff and runs every module.

On a clean PASS, pregate records the cache. `affected` and `full` are recorded only when `receipts/ubuntu-tests.json` exists and its `rc` is 0. A `--only lint` run does not write a suite PASS. A dirty worktree is not recorded.

## CI

`scripts/ci_selected_tests.sh` is the single test step for both G0 jobs.

- Push to `main`: the base is `github.event.before` (a zero SHA falls back to the merge-base with `origin/main`).
- Pull request and `workflow_dispatch`: the base is the merge-base with `origin/main`. The script fetches that history.
- Ubuntu sets `PFY_CI_USE_CACHE=0` and always runs the selection.
- Nimo sets `PFY_CI_USE_CACHE=1`. A hit prints `cache hit <key> from pregate` and skips the suite. A miss runs the selection and records on PASS.
- `structural` and `none` run the structural checks and no unittest modules.
- An empty module list for `affected` or `full` exits 1. An empty argument list would otherwise make `run_tests.py` run every module.

`eval-structural.yml` cancels a superseded run on the same branch. It does not cancel `main` or `master`.

The nightly workflow is not named G0. `tests/test_ci_discover_cover.py` fails if a second job claims the G0 ubuntu or nimo name, if either G0 job drops the selector, the runner, or `--skip-unittests`, or if the nightly command passes module arguments.

## Cache key

`sha256` of `tree SHA`, `sha256` of `config/test_select.json`, `platform.python_version()`, and host class (`nimo` or `ubuntu`), joined by newlines.

Files live in `${PFY_TEST_CACHE:-$HOME/.cache/pfy/test-pass}/<key>.json`.

Inside GitHub Actions the host class comes from `RUNNER_ENVIRONMENT`. `PFY_HOST_CLASS` cannot point a hosted runner at the nimo cache. Outside Actions the default is `nimo`, and `PFY_HOST_CLASS=nimo|ubuntu` is how tests pick a class.

A stored `full` PASS satisfies `check --need structural` and `--need affected`. An `affected` PASS does not satisfy `--need full`. Only `result: PASS` is written. A corrupt file, a dirty tree, or a mismatched tree, config, Python, or host class is a miss.

Ubuntu CI never reads this cache. Nimo and a local pregate share it only when they are the same user, the same Python, and the same tree.

## Measured

Host: 32 cores, Python 3.14.4. Serial baseline from the ticket, not re-measured: one `python3 -m unittest discover -s tests -t .` is 18 to 22 minutes. This tree has 171 `tests/test_*.py` modules.

| run | wall | result |
|---|---|---|
| `test_select.py --paths docs/ops/PREGATE.md` plus `--structural-checks` | 1.05 s | `structural`, 0 modules. Checks passed (JSON not applicable, markdown links, catalog_check, smoke_contract_lint, encoded payloads, `./pfy help`) |
| `test_select.py --paths scripts/catalog_check.py` plus `run_tests.py` on the selected module | 1.03 s | `affected`, `tests.test_catalog_entry_numbers` only, PASS |
| `run_tests.py -j16` full suite, before the serial list | 157.21 s | 171 modules, 3 failed, 18 skips. Those three pass with `-j 1` (165.11 s for the three alone) |
| `run_tests.py -j16` with the first three serial modules | 304.17 s | 171 modules, 4 failed, 18 skips. The new failures pass alone: phase clock 11.69 s, graphjin 1.91 s, and the cloud pair 151.96 s + 25.69 s on a clean scratch |
| `run_tests.py -j16` with all seven serial modules, run 1 | 496.98 s | 171 modules, 0 failed, 18 skips |
| `run_tests.py -j16` with all seven serial modules, run 2 | 495.48 s | 171 modules, 0 failed, 18 skips. No new flakes |

The docs-only and one-file numbers use `--paths` on this branch. A diff of this branch against `origin/main` is `full`, because the branch changes `.github/`, the runner, and pregate.

The two green runs (496.98 s and 495.48 s, about 8.3 minutes) agreed: 171 modules, 0 failed, 18 skips. Other worktrees on this host had unittest discovers running at the same time. Both runs still passed. The serial baseline of 18 to 22 minutes was not re-measured.

## Risks and recovery

| risk | how it fails | recovery |
|---|---|---|
| Dynamic import the graph cannot see | an affected run skips a test that loads the changed module through a constructed string | nightly full suite; a string constant that equals a known module name is already an edge; an unknown or unparseable file is `full` |
| Parallel modules share a tree, a scratch dir, or the bwrap relay deadline | `tests.test_x_intake_smoke_109_111` and `tests.test_x_intake_smoke_112_115_receipts` see `pipelines/smoke` change under them. `tests.test_x_intake_smoke_103_105` reads `pipelines/smoke/graphjin/latest.json` while `tests.test_x_intake_smoke_103_111_receipts` writes it. `tests.test_pfy_build_cloud` and `tests.test_pfy_build_cloud_slice2` share `tmp/cloud-build-tests` and `/var/tmp/pfyb-*`. `tests.test_pfy_build_phase_clock` saw gate count 6 instead of 4. `tests.test_harness2_local_sandbox` exits `relay down` before `call.pgid` exists, because the relay has 5 seconds to answer | those seven are in `SERIAL` in `scripts/run_tests.py` and run after the pool, one at a time. Each passed with `-j 1`. A failed cloud `setUp` leaves the fixture repo; the next `git commit` then exits 1 with an empty stderr. Recovery: delete `tmp/cloud-build-tests` and rerun. A new flake is another `SERIAL` row, then two more full runs |
| Cache hit without a suite | nimo skips tests for a tree whose PASS was recorded from `--only lint` or from a failed receipt | `affected` and `full` require a receipt with `rc` 0; a dirty tree is a miss; delete `~/.cache/pfy/test-pass/<key>.json` to force a run. Ubuntu does not read the cache |
| Risky glob deleted or narrowed | a trading, release, or secret path runs a subset | the globs live in `config/test_select.json`; `tests/test_test_select.py` requires `docs/kalshi-note.md`, `docs/trading-note.md`, `docs/deploy-note.md`, and `docs/secret-note.md` to be `full` with `risky glob` in the reason. Do not remove them without Tester+Reviewer |
| Named skip treated as a green suite | G0 structural prints PASS while no tests ran | `check_pfylib_unittests` prints `SKIP` and the reason; the next step must call `scripts/ci_selected_tests.sh`. The cover test fails if `--skip-unittests` or `scripts/run_tests.py` disappears from the job |
| Leading-dot path stripped | `.github/workflows/ci.yml` misses the core glob and is explained as "no test reference" | `glob_match` and `--paths` strip a literal `./` prefix only. `tests/test_test_select.py` covers `--paths .github/workflows/ci.yml` |
| Sandbox test that never says `bwrap` | the host-PATH re-run skips it, and ubuntu-parity only sees the hidden-PATH result | put the word `bwrap` in the module, or add the module to the re-run. Nightly on ubuntu-24.04 is the hidden-PATH backstop |

## Next slices

- Light jobs without the global heavy lock.
- Per-tool stage files `data/stages/<tool>.json`.
- Persistent tool cache `~/.cache/pfy/{tools,bin}`. SkillSpector v2.12.0 now lives at `~/.cache/pfy/bin/skillspector`.
- Local-lab off the landing lane.

## Scripts

Usage for the three scripts is in [HANDOFF-fast-pipeline-1107.md](../HANDOFF-fast-pipeline-1107.md). Pregate flags are in [PREGATE.md](PREGATE.md).
