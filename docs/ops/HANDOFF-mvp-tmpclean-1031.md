# Handoff mvp-tmpclean-1031

Branch `bot/mvp-tmpclean-1031`. Base `origin/bot/mvp-integrate-1031` (`19c2710` plus drop-in `db1ca11`). Worktree `/home/mark/DEVELOP/pfy-mentat/tmp/mvp-tmpclean-1031`. No rebase, no force push, no PR, no merge to main, no tag. Not a Feature GO. No local model. No `--local`.

Exit: lane empty (exit 2), after the four drop-in items. Wall cap was 2026-11-01T05:15:31Z. This handoff is earlier. Host at the suite end: MemAvailable about 58 GiB, load about 4.4, 32 cores.

## Done

| Item | Commit | Result |
|------|--------|--------|
| Exit card | `adb4168` | Pushed before any test edit |
| Red repro | `f344d87` | Old checker failed in 50.955s. Only new path was `/tmp/pfy-hr-x`, created and removed by this lane |
| Hermetic checker | `a7ae331` | 3 tests OK in 50.098s while a sibling `/tmp/pfy-hr-x` existed. Planted leaks failed the checker |
| Honor TMPDIR | `0284030` (run-log sha `01f06a1`) | 5 tests OK in 0.031s. `bash -n` on the nine scripts |
| Full suite | no code change | Ran 1054 in 670.592s. Failures 2, skipped 16. Both failures are the recorded red base |

## What changed

The cleanup checker no longer snapshots every `/tmp/pfy-*` name. The child gets a fresh directory from `tempfile.mkdtemp` (so the runner `TMPDIR` is honored) and a `sitecustomize` hook that records `os.mkdir` and `os.makedirs` on host `/tmp` outside that directory. Pass means the private directory is empty and every logged path is gone. `tests/support_tmpclean_leaker.py` is not collected by unittest. Its `private` mode leaves a `mkdtemp` directory. Its `host` mode does `os.mkdir("/tmp/" + marker)`. Both must fail the checker. The permanent sibling dir is `/tmp/pfy-hr-<pid>`, removed only when this test created it.

Host scratch that ignored `TMPDIR` now uses `mktemp` or `tempfile` defaults:

- `examples/hermes-bakeoff/opencode_arm.py` sets the child `TMPDIR` from `run.child_tmpdir()` (repo `tmp/`, never a hardcoded `/tmp`).
- `tests/test_x_intake_smoke_149.py` keeps the caller `TMPDIR` in `run_smoke` and in `_call_main`, and clears the cached `tempfile.tempdir` for the duration of `main()`.
- `scripts/smoke-product-levers.sh`, `scripts/eval-auto.sh`, `examples/eval-harness/smoke_tools_model.sh`, `examples/opencode-ollama/smoke.sh`, and the four `examples/voice-stt-edge/smoke*.sh` scripts. Each has a probe flag that prints the path and exits before any server.
- `examples/litellm-ollama/host-ollama-gateway.sh` pid and log follow `XDG_RUNTIME_DIR`, then `TMPDIR`, then `/tmp`. Explicit `OLLAMA_GATEWAY_PID_FILE` and `OLLAMA_GATEWAY_LOG` still win. `--paths` prints both and exits. The gateway was not started.

## Suite

```text
TMPDIR=$PWD/tmp nice -n 19 flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock python3 -m unittest discover -s tests -t .
```

Queued 2026-10-31T21:42:32Z behind another lane. Lock acquired 2026-10-31T21:49:29Z. Ended 2026-10-31T22:00:40Z. Discover itself: Ran 1054 tests in 670.592s. FAILED (failures=2, skipped=16). Wrapper exit 1 because of those two failures.

Integrate on this base reported 1048 tests. The extra 6 are this lane: the cleanup module grew by 2, plus `tests.test_tmpdir_scripts` (1), two `Smoke149` cases, and one hermes case.

### Failure 1, recorded, not fixed

`tests.test_pfy_build_local.CloudBuildUnchangedTests.test_help_and_dry_run_stay_the_same`

Bare `./pfy build --help` is the cloud card. The test still expects `--prompt-file`. Same failure the integrate handoff recorded. `tests/test_pfy_build_local.py` is not owned here.

### Failure 2, recorded, not fixed

`tests.test_local_bench.OutdirPathTests.test_relative_outdir_log_path_safe`

`log_path_for_receipt` returned `tmp/mvp-eval-1031/local-bench-out-87ltk9c3/demo_model.log` and the test wanted that path absolute. `TMPDIR` is this worktree `tmp/`, so `TemporaryDirectory` sits inside the repo. The test file matches the base. Not rewritten.

## How it fails and how we recover

- Sibling `/tmp/pfy-*` during the cleanup run: the old checker failed the whole module. The new checker ignores directories it did not create. The test removes only `/tmp/pfy-hr-<pid>` when it created that path.
- Real leak inside the private `TMPDIR`: the checker raises `leaked: private TMPDIR not empty`. The checker's `finally` deletes that private base.
- Real leak via `os.mkdir` on host `/tmp`: the hook logs it, the checker raises `leaked: host /tmp paths still present`, and the host-leak test asserts the marker path is gone. The checker's `finally` removes that marker.
- Hook not loaded (`python -S`, or `PYTHONPATH` dropped): the ready file is missing and the checker raises `hook did not load`. The leak tests do not treat that as a pass.
- Limit: a nested interpreter started with `-S` or `-I`, or a scrubbed env that drops the hook, can still `mkdir` on host `/tmp` unseen. An empty private `TMPDIR` still catches `tempfile` users that keep `TMPDIR`. Children inside `bwrap --tmpfs /tmp` do not leak onto the host. An outer bwrap was rejected because `examples/harness2-local/sandbox.py` already mounts its own `/tmp`.
- Opencode child with `TMPDIR=/tmp`: `test_opencode_run_tmpdir_stays_under_repo_tmp` fails. The test mocks `subprocess.run` and does not launch opencode. It deletes its temp base.
- `smoke_149` dropping `TMPDIR`, or a cached `tempfile.tempdir` from an earlier `gettempdir()`: `mkdtemp` lands outside the private dir and `test_inprocess_main_keeps_caller_tmpdir` fails. `_call_main` sets `tempfile.tempdir = None` around `main()` and restores the previous cache in `finally`. The test deletes the private dir.
- A script that still names a fixed `/tmp/...` file: `tests.test_tmpdir_scripts` fails the banned-literal check or the printed probe path is not under the private `TMPDIR`. Probe flags exit before servers, models, or the gateway. The test deletes the private dir and any printed path that survived outside it.

## Left alone

Cage and sandbox paths that are supposed to use `/tmp` inside the cage:

- `examples/litellm-ollama/run-in-cage.sh` writes `/tmp/ollama-tags-cage.json`.
- `examples/eval-harness/run-in-cage.sh` writes `/tmp/ollama-tags-eval.json` and defaults `EVAL_RESULT_JSON` and `EVAL_MATRIX_MD` under `/tmp`.
- `examples/harness2-local/sandbox.py` uses `--tmpfs /tmp` and refuses checkout, runs, state, and harness paths under `/tmp`.
- `tests/test_pfy_local_build_eval.py` bwrap probe `--tmpfs /tmp`.
- `scripts/pfy_build_local.py` (`_under_system_tmp` and bwrap `--tmpfs /tmp`). Not owned.

Not creators of `/tmp/pfy-*` directories: PATH stubs (`/tmp/pfy-215-no-graph`, `/tmp/pfy-205-no-oc`, `/tmp/pfy-208-no-mcp`, `/tmp/fake-*`), `pfylib/attach.py` fake binary string, the voice orchestrator prompt line, `scripts/eval_unified_agents_pack.py` read-only default, `scripts/pfy_opencontext_205.py` `cwd="/tmp"` (working directory only). `examples/x-intake-local/smoke.py` `_child_env` still does not forward `TMPDIR` unless the caller puts it in `extra`. A bwrap child would not have an arbitrary parent `TMPDIR` bound.

## Cross-lane requests

- `tests.test_pfy_build_local.CloudBuildUnchangedTests.test_help_and_dry_run_stay_the_same`: expect dogfood flags on `./pfy build -p --help`, and the cloud card on bare `./pfy build --help`. Do not edit that test from this lane. Same request as the integrate handoff.
- `tests.test_local_bench.OutdirPathTests.test_relative_outdir_log_path_safe`: with `TMPDIR` inside the repo the helper returns a relative log path. The file matches `origin/main`. A later edit can point that case's temp dir outside the repo. This lane must not use `/tmp` for scratch.
- `pipelines/dogfood/local-bench-5/run_runtime_matrix.sh` still writes `/tmp/rt-${LABEL}-${BACKEND}.log` and a matching `.stop` file. Outside the drop-in search roots (`tests/`, `pfylib/`, `examples/`, `scripts/`). Not edited.
- `bootstrap/agenc/smoke.sh` still tees `/tmp/agenc-smoke-llm.txt`. Outside the search roots. Not edited.
- `bootstrap/agenc/install.sh` still downloads the Node tarball to `/tmp/${platform}.tar.xz` and removes it after extract. Outside the search roots. Not edited.

## Gate

Runtime change: host scripts and `examples/hermes-bakeoff/opencode_arm.py`. Gate: Tester plus Reviewer.

Pregate not run: host busy. `pgrep -f 'Runner[.]Worker'` matched a live worker, and other lanes were already running `scripts/pregate.sh` under the heavy lock. Do not treat this handoff as a Feature GO.

## Next

Lane empty for this worktree. Next work that is not this lane: the help-test contract, then the three out-of-root `/tmp` names above if a lane owns those files. Do not merge this branch.
