# Handoff: G0 path and dirty-cache skip (2026-11-08)

Lane `bot/cifix-1108` at the fix on `aa84daad`. Not pushed. No pull request. No stage card edit. No ceiling edit. No secret, trading, deploy, or release change.

## Symptom

Two eval-structural failures on main `aa84daad`:

1. Hosted ubuntu shard 2, `tests.test_asm_agent_skill_manager_probe`, tried to `mkdir /home/mark/.cache/pfy/tools` and failed. The runner has no `/home/mark`.
2. Nimo G0 ran the tests, then caching exited 1 with `not recorded: dirty worktree`.

## Root cause

1. `eval/evq1107/asm-agent-skill-manager/probe.py` set `CACHE` to `/home/mark/.cache/pfy/tools/asm-agent-skill-manager` and called `mkdir` on that tree at the start of `main`, before the stub binary was checked. The unittest runs that `main`. `HOME` and `XDG_CACHE_HOME` were ignored. Repro before the fix: with both variables pointed at a temp dir, the probe still rewrote `/home/mark/.cache/pfy/tools/asm-agent-skill-manager/tmp/asm-probe` (mtime `1794144887596291079` became `1794145113839863291`) and the new test failed on that change.

2. `scripts/test_cache.py` `record` printed `not recorded: dirty worktree` and returned 1. `scripts/ci_selected_tests.sh` is `set -e`, and the nimo job sets `PFY_CI_USE_CACHE=1`, so that return failed the step after the suite had passed. Repro: a temp git repo, clean `record` exit 0, then a dirty README, then `record` exit 1 with that exact line. The same command under `bash -c 'set -euo pipefail; ...'` also exited 1 and did not reach the next line. The nimo workflow writes `pipelines/eval/golden.latest.md` before the test step. That file is tracked and the writer stamps a new UTC timestamp, so the checkout is dirty on every nimo G0 run. `pipelines/eval/structural.latest.md` is gitignored and is not the dirty path.

## What changed

- The asm probe cache is `$XDG_CACHE_HOME/pfy/tools/asm-agent-skill-manager` when `XDG_CACHE_HOME` is set, otherwise `$HOME/.cache/pfy/tools/asm-agent-skill-manager` (`Path.home()`).
- The asm unittest sets `HOME`, `XDG_CONFIG_HOME`, and `XDG_CACHE_HOME` under its temp dir. A second case unsets `XDG_CACHE_HOME` and expects `$HOME/.cache/...`. Both cases assert the login path `/home/mark/.cache/pfy/tools/asm-agent-skill-manager/tmp/asm-probe` is not created or rewritten.
- `record` still writes nothing when the worktree is dirty. It prints `not recorded: dirty worktree` and exits 0. `check` still exits 1 on a dirty tree. A non-PASS, a bad receipt, and an `affected` or `full` record without `rc` 0 still exit 1 and write nothing.
- `docs/ops/MODULAR-CI.md` states that exit code.

## Catalog-first

`python3 scripts/catalog_check.py` printed:

`PASS catalog-check slim-subset ok n_json=8 (not a 1:1 dump of TOOLS.md) · toolsets=8 linked=2 catalog_tool=null:6 · tools_md=55 stage_cards=55 i1_cards_open=0 stage_only=74`

No catalog tool is a portable tool-cache or a test-pass cache for this repo. `scripts/test_cache.py` is the cache. The asm card stays I1 with ceiling I1. Its non-goal still says it is not a pregate or CI gate. This lane does not wire it in. It stops the existing unittest from creating a fixed login directory.

Build used the written grill below. The coordinator subsequently executed the required tools-off grill successfully; see the coordinator evidence below.

1. Should a dirty skip exit 0? Yes. The suite already passed. Recording is optional. Test: `tests.test_test_cache.TestCacheTests.test_dirty_worktree_skips_record_and_the_suite_stays_green`.
2. Should `check` exit 0 on a dirty tree? No. A dirty tree must not skip the suite. The same test expects `check` exit 1 and `dirty worktree`.
3. Should `pipelines/eval/golden.latest.md` be gitignored so nimo can record? No. That would record a PASS for a checkout that rewrites a tracked file. The ticket says skip and keep the cache intact.
4. Should every eval probe lose a hardcoded `/home/mark`? No. Only the failing unittest and cheap defects in CI tests and scripts.
5. Should a FAIL receipt on a dirty tree exit 0? No. The same test expects non-zero and `only PASS`, and the previous cache file unchanged.

## Five questions

1. What triggers it? Ubuntu G0 runs `scripts/ci_selected_tests.sh` with `PFY_CI_USE_CACHE=0` and `PFY_CI_SHARD`. Shard 2 includes `tests.test_asm_agent_skill_manager_probe` when the selection is full (module hash mod 4). Nimo G0 runs the same script with `PFY_CI_USE_CACHE=1` and no shard, on push to main or master and on the schedule.
2. What does it do, and which services does it read and write? The probe reads fixtures and writes `results.json` next to the copy under test, plus cache dirs under `XDG_CACHE_HOME` or `HOME/.cache`. `record` reads git status, the selection JSON, and the receipt. On a clean PASS it writes `${PFY_TEST_CACHE:-$HOME/.cache/pfy/test-pass}/<key>.json`. On a dirty tree it writes nothing. No hosted service, no account, no model.
3. What does it trigger next? A green ubuntu shard lets that G0 job succeed. A dirty nimo skip exits 0 and does not write a hit, so the next `check` is a miss and the suite runs. A clean pregate can still record, and a later nimo `check` can hit.
4. Where does a human re-enter? A real module failure still exits 1 from `scripts/run_tests.py` before `record`. A non-PASS `record` still exits 1. Delete `~/.cache/pfy/test-pass/<key>.json` to force a run after a bad hit. No new prompt.
5. What stops two runs doing the same work? The cache key is the tree SHA, the sha256 of `config/test_select.json`, the Python version, and the host class. A dirty run does not write, so it cannot make another run skip. `check` on a dirty tree is a miss. A shard does not record. Ubuntu does not read the cache.

## Scan of hardcoded `/home/mark` in CI tests and scripts

Left in place. They do not mkdir a login home:

- `tests/test_laya_trial_086.py` falls back to a venv path and skips when that file is not executable.
- `tests/test_fs_nav.py` passes the string as `ROOT` to `print_fs_nav`. It does not create the directory. The test already sets `HOME` to a temp dir.
- `tests/test_local_bench.py` passes a string to `is_ollama_exe`.
- `scripts/pfy_build_cloud.py` lists `/home/mark/.local/bin/codebase-memory-mcp` as one candidate. A missing file returns None.

Other `eval/**/probe.py` files still default to `/home/mark/.cache/pfy/tools/<name>`. They were not the shard failure. This lane did not edit them.

## Evidence

Red, before the fix, `HOME` and `XDG_CACHE_HOME` under `tmp/cifix-tests`:

- `test_dirty_worktree_skips_record_and_the_suite_stays_green` failed: `AssertionError: 1 != 0 : not recorded: dirty worktree`.
- `test_cache_uses_home_when_xdg_cache_home_is_unset` failed: login `asm-probe` mtime changed (`1794144887596291079` vs `1794145113839863291`).

Green, same env, after the fix:

- `python3 -m py_compile` on `scripts/test_cache.py`, the probe, and both test modules.
- PyYAML `safe_load` of all six `.github/workflows/*.yml`.
- `python3 -m unittest tests.test_test_cache tests.test_asm_agent_skill_manager_probe`: 7 tests, OK, 1.516s.
- Login `asm-probe` mtime stayed `1794145113839863291`.

`scripts/test_cache.py` is a `core_globs` entry, so `test_select` on `1794a8ce` is mode `full` (259 modules, same list as `scripts/run_tests.py --list`). Temps for the local runs were under this worktree `tmp/cifix-tests`. The two changed modules were also run with `HOME` and `XDG_CACHE_HOME` under that temp dir before the full list. The full list used the normal `HOME`, which is how G0 runs.

## Limitations

- Nimo G0 stays dirty because `golden.latest.md` is rewritten. The step is green and the cache is not written, so this job does not create a hit. A clean pregate on the same tree, Python, and host class still can.
- `record` treats a failed `git status` as dirty (`worktree_dirty` already did) and now exits 0 without writing. The suite result is unchanged.
- Pregate already skipped `record` when `git status --porcelain` was non-empty, and that path did not fail the summary. It is unchanged.
- The repro of the old probe refreshed the empty scratch dir `~/.cache/pfy/tools/asm-agent-skill-manager/tmp/asm-probe`. The prefix, tarball, and `probe-try` files were not removed. The green run did not touch that path.
- Build did not run the grill script; the coordinator subsequently ran it successfully.
- No push. The coordinator lands after an independent sanity check.

## Post-commit selection run

On `1794a8ce`:

- `python3 scripts/test_select.py --base origin/main --head HEAD` mode `full`, reason `core glob scripts/test_cache.py: scripts/test_cache.py`, 259 modules.
- `python3 scripts/test_select.py --structural-checks --selection tmp/cifix-tests/selection.json` passed markdown links, `catalog_check.py`, `smoke_contract_lint.py`, `check_no_encoded_payloads.py`, and `./pfy help`.
- `TMPDIR=$PWD/tmp/cifix-tests python3 scripts/run_tests.py --receipt tmp/cifix-tests/receipt.json` ran those 259 modules once. `jobs=16`, `seconds=502.239`, `skips=19`, `rc=1`. The only failure is `tests.test_stage_registry` (`test_assembled_document_matches_legacy_monolith`). `tests.test_asm_agent_skill_manager_probe` and `tests.test_test_cache` passed. This commit does not change `data/`, `pfylib/`, or `tests/test_stage_registry.py`. The legacy blob is the last commit of `data/tool_integration_stages.json`, which this commit does not touch. Stage cards were left unchanged. That failure is not one of the two ticket fixes.

## Coordinator verification before landing

- Build exited 0 and self-reviewed. Independent temp-HOME and temp-XDG run: both changed test modules, 7 tests, OK. Python compile and all workflow YAML parsing passed.
- `python3 scripts/grill_ticket.py tmp/TICKET.md --paths scripts/test_cache.py` exited 0: 5 questions, 2 behavioral exit assertions. Full receipt in ignored `tmp/TICKET.md.grill.json`. The generated test examples refer to nonexistent convenience APIs, so they were not installed. Their assertions are covered by the existing subprocess regression tests in the two changed test modules.
- The full selected suite's sole failure was reproduced on a fresh detached worktree of unchanged origin/main aa84daad: `python3 -m unittest tests.test_stage_registry` fails `test_assembled_document_matches_legacy_monolith` (6 tests, 1 failure). This is pre-existing and outside this task; stage cards and ceilings remain untouched. Landing the two approved CI fixes with that baseline failure disclosed.
