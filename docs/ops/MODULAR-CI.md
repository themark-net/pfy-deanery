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

Done on `bot/fastpipe-1107` (slice 1):

- `scripts/run_tests.py` runs one unittest module per subprocess.
- `scripts/test_select.py` maps a diff to `none`, `structural`, `affected`, or `full`. The source recorded in the JSON is `ast`. The codebase-memory binary is not consulted, so ubuntu and nimo select the same modules.
- `scripts/test_cache.py` stores a PASS keyed by tree, `config/test_select.json`, Python version, and host class.
- Pregate runs the selected suite once. G0 ubuntu and G0 nimo each run it once. Nimo reuses the pregate cache when the key matches.
- `.github/workflows/full-suite-nightly.yml` runs the full list on `ubuntu-24.04` at 09:17 UTC, and on `workflow_dispatch`.

Done on `bot/fastpipe-par-1107` (slices 3, 5, and 6):

- Slice 3. Several pregates may run on one host. Each worktree, scratch, and owner file is `<short>-<HHMMSS>-<pid>` with the pid zero-padded to 7 digits. The persist folder stays `<short>-<UTC stamp>-<raw pid>`. `PREGATE_STATE_ROOT` moves that state (default `<git-common-parent>/tmp`). Retention never deletes a folder whose trailing pid is still a pregate, and there is no shared `pregate-latest-summary.md`. Verified: `tests/test_pregate_concurrent.py` started two `--only lint,gate-hash` runs. Both printed `OVERALL=PASS`, with different pids and different summary paths, in the same unittest run (4 tests, 23.6 s, including the path-length guard). A second case kept a live run folder and deleted a dead one past `PREGATE_KEEP_RUNS`.
- Slice 6. `scripts/model_lock.sh` flocks `${PFY_MODEL_LOCK:-$HOME/.cache/pfy/locks/local-model.lock}` for commands that load a local model (Ollama Make targets, harness eval tiers, `make local-bench`, the local-lab eval-auto step, the nightly-models suite). Landings do not call it. Pregate, `scripts/ci_selected_tests.sh`, `scripts/run_tests.py`, and `make eval-structural` do not take this lock and do not wait on `Runner.Worker`. The old `~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock` convention is retired for light jobs. Historical drop-ins that name that file are left as they were.
- `local-lab.yml` cron is `15 10 * * *`: 02:15 America/Los_Angeles. DST has ended, so that zone is UTC-8, which is 10:15 UTC. The 120 minute job wall ends at 12:15 UTC. `nightly-models.yml` cron is `30 12 * * *`: 04:30 PT, 12:30 UTC. Its 120 minute wall ends at 14:30 UTC (06:30 PT). `eval-structural.yml` adds a schedule at `0 15 * * *`: 07:00 PT, 15:00 UTC, after that model window. Step caps stay G0 30, G1 30, Product levers 30, smoke-integration 40, eval-auto 20. Both model workflows use concurrency group `pfy-local-model` with `cancel-in-progress: false`. A GitHub concurrency group does not by itself lock a different workflow. `scripts/model_lock.sh` is the host lock that serializes the model command across workflows, Make, and a shell. Branch landings do not use the nimo runner, so local-lab cannot block them.
- The ubuntu G0 job is a 4-way matrix. `scripts/run_tests.py --shard i/4` keeps the module when `sha256(name)[:8]` as an integer, mod 4, equals `i`. The slice 1 full suite was about 496 s, over 5 minutes, so the landing job is sharded. Every non-test check still runs on every shard. The upload name includes the shard because `actions/upload-artifact` v4 rejects a repeated name. The nimo job runs only on schedule, or on push when the ref is `main` or `master`. Pull requests and `workflow_dispatch` do not start it. On push to main, nimo runs `scripts/test_cache.py check` before the suite and prints `cache hit` on a hit. A sharded run does not record the cache. The nightly workflow is still one `python3 scripts/run_tests.py` with no module arguments and no `--shard`.
- Slice 5. `scripts/tool_cache.sh check` creates `${PFY_TOOL_CACHE:-$HOME/.cache/pfy}/{bin,tools,uv-cache}` and exits 1 when one of those paths exists and is not a directory. `make skill-scan` resolves SkillSpector from `PFY_SKILLSPECTOR_BIN`, then PATH, then `~/.cache/pfy/bin/skillspector`. A set `PFY_SKILLSPECTOR_BIN` does not fall through. `codebase-memory-mcp` uses the same cache bin after PATH misses (and after `PFY_CODEBASE_MEMORY` where that variable already wins). `ci/test-image/Containerfile` pins `python:3.12-slim@sha256:05a994d2344eb364cc186910f4fc8786a38215f39f00d0acc25bff33a08f4177` plus git, ripgrep, and bubblewrap. No secrets and no repo copy. `make test-image` and `make test-in-container` use rootless `/usr/bin/podman`, mount the repo read-only, and put scratch on a tmpfs. Verified on nimo: the image built, and `make test-in-container` ran `tests.test_run_tests`. Result: `PASS tests.test_run_tests 2.10s skips=0`, `modules=1 failed=0`.

Still in place, on purpose:

- `make eval-structural` still calls `run_structural.py` without `--skip-unittests`, so that Make target still runs a full discover.
- `pfy build` still defaults to `python3 -m unittest discover -s tests -t .`.
- Per-tool stage files `data/stages/<tool>.json` are a different slice.
- No Make target starts Strata. Wrap a manual strata run in `scripts/model_lock.sh`. `make local-bench` already wraps `examples/local-bench/bench.py`.

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
- Ubuntu sets `PFY_CI_USE_CACHE=0` and always runs the selection. The workflow passes `--shard i/4`. An empty shard of a non-empty list exits 0 and writes a PASS receipt with `modules` empty. That receipt is not recorded as a tree PASS.
- Nimo sets `PFY_CI_USE_CACHE=1` and does not set a shard. A hit prints `cache hit <key> from pregate` and skips the suite. A miss runs the selection and records on PASS. The nimo job does not start for a pull request or for `workflow_dispatch`.
- `structural` and `none` run the structural checks on shard 0 (and when no shard is set) and no unittest modules. Other shards print a line and exit 0. The workflow's other steps still run those non-test checks on every shard.
- An empty module list for `affected` or `full` exits 1. An empty argument list would otherwise make `run_tests.py` run every module. A bad `--shard` (not `i/n` with `0 <= i < n`) exits 2.

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
| Shard recorded as a full PASS | nimo skips the suite after one quarter of the modules passed | a run with `PFY_CI_SHARD` set does not call `test_cache.py record`. Nimo does not set the shard. Ubuntu does not read the cache |
| Nimo job absent on a branch landing | a pull request looks green while no tests ran | the nimo `if` is explicit. The ubuntu job is the landing gate and still runs the selection, in four shards, including every non-test check. Trading, release, and secret paths stay `full` |
| Retention deletes a live pregate | a second run removes the first run's folder while it is still working | the folder name ends with the pid. Retention skips it while `/proc/<pid>/cmdline` still contains `pregate.sh`. The concurrent test keeps that folder and deletes a dead one |

## Shadow selection

`scripts/cbm_shadow.py` is not a selector. Pregate still decides the suite with `test_select.py` (`source: ast`) and does not read the codebase-memory binary, so ubuntu and nimo still select the same modules. After the verdict, cleanup detaches one shadow process. That process compares the same base and head with `codebase-memory-mcp cli detect_changes --scope tests` and appends one JSONL line to `${PFY_CBM_SHADOW_LOG:-$HOME/.cache/pfy/cbm-shadow/selections.jsonl}`. A tool failure, a timeout, or a missing binary is a line in that log. The gate exit code does not change. `PFY_CBM_SHADOW=0` skips the launch. Numbers and the keep-or-drop recommendation are in [CBM-SHADOW-1107.md](CBM-SHADOW-1107.md).

## Next slices

- Per-tool stage files `data/stages/<tool>.json`.

## Scripts

Usage for the three scripts is in [HANDOFF-fast-pipeline-1107.md](../HANDOFF-fast-pipeline-1107.md). Pregate flags are in [PREGATE.md](PREGATE.md).
