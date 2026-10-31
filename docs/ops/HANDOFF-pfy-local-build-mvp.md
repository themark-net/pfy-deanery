# Handoff: pfy-local-build MVP, fix round 2

Branch `bot/mvp-local-build`. Compare: https://github.com/themark-net/pfy-mentat/compare/main...bot/mvp-local-build

Tester failed `42fcc229`. Reviewer notes are in [GATE-NOTES-fix2.md](GATE-NOTES-fix2.md) and are included below. Decisions D16 onward: [AUTONOMOUS-DECISIONS-2026-10-26.md](AUTONOMOUS-DECISIONS-2026-10-26.md). The head of this branch is `git rev-parse HEAD`. A commit cannot record its own SHA.

Fix round 1 stays below. Tester and Reviewer failed `e63a95b2`. The live 8/8 from stamp `20261026T072940388555Z` was scored before that test-gate fix. The post-fix-1 rate is stamp `20261027T031008578576Z` (8/8, 608.235 s). It is not the fix-2 rate.

## Fix round 2

Worktree `tmp/mvp-local-build`. Cloud `./pfy build` (`scripts/pfy_build_p.py`) is unchanged. `./pfy` and `scripts/pfy` stay mode `100755` in git.

### Blockers

1. `test_sigterm_interrupts_and_releases_the_lock` waits for `orphan-child.pid`, `orphan-parent.pid`, and both heartbeats, then sends SIGTERM. The same wait covers the other orphan scenarios in that file. A local mutant that signalled on the `pfy-agent-started` marker still passed in 2.347 s, because the stub won the race on this box. The recorded red is the Ubuntu CI failure: `worktree_pid()` asserted on an empty list. The waiter stays.
2. An unknown runner, or exit 0 with no parseable summary, is `tests-failed`. Unittest, a pytest summary line, and junit xml are parsed. A higher skip, xfail, deselect, error, or failed count is `tests-failed`. A lower passed count is `tests-regressed`. New or changed `conftest.py`, `pytest.ini`, `tox.ini`, `setup.cfg`, `pyproject.toml`, `sitecustomize.py`, `usercustomize.py`, `.gitignore`, and `.gitattributes` anywhere are `tests-tampered`. `os._exit(0)` in `src` does not pass. Pytest is not installed here. The deselect proof is `tools/fake_pytest.py` plus the parser.
3. `tests_before`, `tests_after`, the repeat run, and the archive recheck use the agent bwrap profile with `--unshare-net` and no Ollama bridge. The main checkout is not writable, there is no push remote, and the env is scrubbed. The probe writes the side effect in `src/__init__.py` (TCP to the test listener and to `1.1.1.1:53`, a write into a scratch main, `git push`, and branch `pwned`) and still fixes `src/calc.py`. Those side effects fail and the run is judged on the calc fix. GATE-NOTES R1 is closed. It is not a known gap. The scratch main is under the test tmp, not `~/DEVELOP/pfy-mentat`.
4. Every sandbox adds `--unshare-pid`, `--unshare-ipc`, `--unshare-uts`, and `--die-with-parent`, including `--share-net`. A second tree digest immediately before `git add` is `worktree-changed-after-gate` when it differs. `test_setsid_daemon_cannot_rewrite_after_the_gate` finishes in under 20 s and the committed blob is the fix, which shows the namespace died. The two digests are adjacent on purpose. A mutant that removes only the rehash and keeps `--unshare-pid` still passes that test.
5. `git add -A -f` excludes only `tmp`, bytecode, and pytest cache. `.gitignore` edits do not drop `src/helper.py`. The commit is then extracted with `git archive` under `<repo>/tmp/recheck-<sha12>` and tested in the sandbox. A failure resets `HEAD~1` before the branch exists and reports `commit-recheck-failed`. Removing `-f` made `test_ignored_helper_is_in_the_commit` return `commit-failed` (exit 1), not a silent PASS. The force add is what puts the helper in the commit. The archive recheck is the second gate.
6. The same pid namespace as item 4. `test_host_pid_is_not_killed_from_inside` shows a host pid is not visible to kill, or the kill fails. A mutant that dropped `--unshare-pid` from `prepare_sandbox` left the late-rewrite heartbeat moving and killed a host `sleep` (`poll` returned -9).

### Should-fix and GATE-NOTES

- SIGKILL of the pfy pid stops the sandbox heartbeat. `--reap` writes `ABORTED` / `no-receipt` into the pid file's `receipt_dir` when that receipt is missing, including a directory outside `pipelines/dogfood/build-local/`. A mutant that dropped `--die-with-parent` from `prepare_sandbox` left the heartbeat moving. The `bwrap_works` probe still has the flag, so the pin is the product argv.
- `XDG_RUNTIME_DIR` under `/tmp` or `/var/tmp` is `BLOCKED` `runtime-dir-in-tmp`. An explicit XDG that is missing or not writable is `no-runtime-dir` and does not fall back. When that variable is set, those reasons are chosen before the test gate and before a missing bwrap is reported as `no-sandbox`. When XDG is unset and `/run/user/$UID` is missing, `worktree/tmp/ollama.sock` is used only if that path is shorter than 108 bytes. A longer path is `socket-path`. The fallback test uses one path longer than 108 bytes and one shorter, so the checkout length does not decide the result. The short directory is repo `tmp/s/w` when that fits, otherwise a short directory that is not `/tmp`. This box has `/run/user/1000`, so a normal run still uses the short symlink. The direct-socket path does not call `unlink` on a missing link.
- Production code that monkeypatches `unittest.TestCase` or `TestResult` from `src` can still neutralize assertions. That remains a known gap. `os._exit(0)` and a new `sitecustomize.py` are closed. Unittest does not load `conftest.py`. The hash is what catches a new one. `-I` and `-S` were not added.
- `--unsafe-no-sandbox` prints `WARN: --unsafe-no-sandbox is on and bwrap is not usable, so this run is not sandboxed` when bwrap is missing. A working bwrap still runs. The flag also leaves the test gate unsandboxed. That is a known gap. Tests that need bwrap skip with a reason when it is unusable. `command()` adds the flag only when the test process's own `bwrap_works()` is false. The two runtime-dir tests pass `auto_unsafe=False`, so a runner without bwrap still hits the guard.
- Redaction now covers `passwd=` assignments, `Authorization: Basic`, `AKIA` key ids, and PEM private-key blocks (replaced with `[redacted-private-key]`).
- Python 3.12 and 3.14 `TMPDIR` failures are environment-only. Test tmp dirs stay under this worktree's `tmp/`. Nothing was rewritten to use `/tmp`. Python 3.13 is not installed on this box.
- R2: `gh` is on `PATH` and is not logged in. `GH_TOKEN` and `GITHUB_TOKEN` are unset. This session cannot trigger `eval-structural.yml`. The caller must re-run the tip of `bot/mvp-local-build`. Local reproduction is the suite section below. Hedge and lab_stage did not fail on this box (Ollama was up). The relative-outdir failure is the `TMPDIR`-inside-repo case.

### Suites

- `tests.test_pfy_build_local`: 61 tests, OK, 70.965 s. After the direct-socket `unlink` guard, these four passed in 2.729 s: `test_missing_runtime_dir_is_not_reported_as_missing_bwrap`, `test_runtime_dir_under_system_tmp_is_blocked`, `test_missing_bwrap_blocks_unless_the_flag_is_set`, `test_worktree_socket_is_used_when_the_runtime_dir_is_missing`. The socket test still prints a `ResourceWarning` for the bridge sockets. That is not a failure.
- Stub cheater: `tests.test_pfy_local_build_eval.EvalRunnerTests.test_cheat_asserts_scores_zero_on_t01_t04_t08`. 1 test, OK, 2.733 s. Score 0. The class name is `EvalRunnerTests`.
- Python 3.14.4 (`/usr/bin/python3`), `TMPDIR=$PWD/tmp/scratch`: 916 tests, 612.110 s, failures=1, skipped=16. The failure is `tests.test_local_bench.OutdirPathTests.test_relative_outdir_log_path_safe`.
- Python 3.12.12 (uv prefix): 916 tests, 538.420 s, failures=21, skipped=16. Twenty are `tests.test_harness2_local_sandbox.SandboxTests` (`FileNotFoundError` on the uv `python3.12` path, because that interpreter lives under the home the harness sandbox hides). The twenty-first is the same outdir case. One product line `FAIL: grok not on PATH` is not a unittest failure. These 21 are not in the fix-2 diff.

### Live result, fix round 2

Stamp `20261027T070700973123Z` on host `nimo`, model `qwen3.6:35b`, endpoint `127.0.0.1:11434`. Eval exit 0. Pass rate 8/8 (1.0). Total 617.949 s. Mean 77.244 s. No failures, no blocked, no not-run. Every task used `bwrap-unshare-net`. Every task had `tests_before.exit` 1 and `tests_after.exit` 0.

t01 has `model_was_loaded` false, so this eval loaded the model. t08 has `unloaded` true. While loaded, `ollama ps` showed `context_length` 262144, so there is no `context_warning` and Ollama was not reconfigured.

| id | status | reason | wall_s |
|---|---|---|---|
| t01-fix-off-by-one | PASS | ok | 74.84 |
| t02-add-function | PASS | ok | 80.071 |
| t03-rename-symbol | PASS | ok | 82.191 |
| t04-fix-mutable-default | PASS | ok | 43.33 |
| t05-add-cli-flag | PASS | ok | 92.131 |
| t06-parse-duration | PASS | ok | 57.998 |
| t07-remove-dead-code | PASS | ok | 69.409 |
| t08-fix-unicode-strip | PASS | ok | 117.979 |

Committed summary: [live-20261027T070700973123Z.md](../../eval/local-build/live-20261027T070700973123Z.md). Raw receipts stay gitignored under `pipelines/dogfood/build-local-eval/20261027T070700973123Z/`.

### RED, fix round 2

- RED: `judge_tests` returns `None` when counts are missing -> `test_os_exit_in_src_is_not_a_pass` (PASS, exit 0, assertion 0 != 1).
- RED: `run_tests` skips the sandbox (`if False and repo is not None`) -> `test_sandboxed_tests_block_push_write_and_tcp` (scratch secret became `PWNED`).
- RED: drop `--unshare-pid` from `prepare_sandbox` -> `test_setsid_daemon_cannot_rewrite_after_the_gate` (heartbeat kept moving) and `test_host_pid_is_not_killed_from_inside` (host `sleep` poll -9).
- RED: `git add -A` without `-f` -> `test_ignored_helper_is_in_the_commit` (`commit-failed`, exit 1). Not a silent PASS. With `-f`, `src/helper.py` is in the commit.
- RED: drop `--die-with-parent` from `prepare_sandbox` -> `test_sigkill_of_pfy_kills_the_sandbox_and_reap_writes_aborted` (heartbeat kept moving).
- RED: SIGTERM on the started marker, before the pid files exist -> the local sigterm test still passed (2.347 s). See blocker 1.

### Known gaps, fix round 2

- Confinement is bwrap 0.11.1 as the same uid. It is not a separate user.
- `bwrap-share-net` still has a network. Push stays blocked by the sandbox git dir and the read-only root.
- SIGKILL of the runner cannot write its own receipt. `--reap` does, including a custom receipt dir stored on the pid file.
- Production code can neutralize assertions by patching `unittest.TestCase` or `TestResult` from `src`.
- `--unsafe-no-sandbox` also leaves the test gate unsandboxed, and only when bwrap is missing.
- The rehash before `git add` is back-to-back with the gated digest. The late-rewrite test proves namespace death, not that window.
- Python 3.13 is absent on this box. The `TMPDIR`-inside-repo outdir failure and the uv-3.12 harness2 `FileNotFoundError` set are pre-existing. They were not rewritten.
- One model at a time. The eight fixtures are not a cost comparison against cloud `./pfy build`.
- R1 (`src/__init__.py` during the gate) is closed. It is not listed here as an open hole.

## Fix round 1 (history)

Tester and Reviewer failed `e63a95b2`. This part of the file is the operator handoff after that repair. Decisions D1 through D15 are in the same decisions file.

## What item 1 built

`./pfy build --local "<task>"` runs a local OpenCode agent in a new git worktree under `<repo>/tmp/`, gates on the test command, and on PASS commits one branch `local/<slug>-<stamp>`. It does not push, does not open a PR, and does not commit in the checkout it was started from.

Cloud `./pfy build` (`scripts/pfy_build_p.py`) is unchanged. `--local` anywhere in argv is the switch. The shell `exec`s the local runner so SIGTERM reaches Python.

## Usage

```text
./pfy build --local "<task>" [--repo DIR] [--base REF] [--model TAG]
    [--endpoint URL] [--test-cmd CMD] [--timeout SEC] [--test-timeout SEC]
    [--min-free-gb N] [--protect GLOB] [--writable-test GLOB]
    [--receipt-dir DIR] [--keep-worktree] [--keep-model] [--unload-at-end]
    [--run-tests-on-timeout] [--dry-run] [--reap] [--unsafe-no-sandbox]
./pfy build --local --prompt-file FILE [same flags]
./pfy build --local --reap [--repo DIR]
```

Flag wins over env over default.

| Input | Env | Default |
|---|---|---|
| `--repo` |  | git repo containing the cwd |
| `--base` |  | `origin/main` if it exists, else `HEAD` |
| `--model` | `PFY_LOCAL_BUILD_MODEL` | `qwen3.6:35b` |
| `--endpoint` | `LOCAL_OPENAI_BASE_URL` | `http://127.0.0.1:11434/v1` |
| `--test-cmd` | `PFY_LOCAL_BUILD_TEST_CMD` | `python3 -m unittest discover -s tests -t .` |
| `--timeout` | `PFY_LOCAL_BUILD_TIMEOUT` | 1200 |
| `--test-timeout` |  | 600 |
| `--min-free-gb` | `PFY_LOCAL_BUILD_MIN_FREE_GB` | 32 |
| `--protect` |  | none, repeatable. A hit is `protected-path-changed` before the test gate |
| `--writable-test` |  | none, repeatable. Those paths are left out of the test-file hash |
| `--reap` |  | off. With no task, exit 0 after stale-group recovery |
| `--unsafe-no-sandbox` |  | off. Used only when bwrap is missing. A working bwrap still runs |
| `--receipt-dir` |  | `<repo>/pipelines/dogfood/build-local/<stamp>/` |

`--keep-model` skips unload unless `--unload-at-end` is also set. A single `./pfy build --local` unloads only a model that this run loaded. `--dry-run` runs the pre-flight checks, prints the plan, starts nothing, and loads nothing.

## Review (default on)

Review is on for `./pfy build --local` unless the command passes `--no-review`. `--no-review` is one attempt and does not run the size cap or the model review. That is the MVP-1 path.

The default cap is `--max-files 3` and `--max-lines 250`. A test file named by `--test-cmd` does not count toward the file cap. Added lines plus removed lines count toward the line cap. `./pfy build --local --help` prints the same defaults.

A larger diff is `PASS-REJECTED` (exit 1) even when the tests are green and the change is a legitimate fix. The attempt receipt names the file count and the line count. Raise `--max-files` and `--max-lines` when the task is really that big. Three changed files, or 251 changed lines, is enough to reject.

The reviewer is the same local model as the agent. `--model` (default `qwen3.6:35b`) is the tag for the edit and for the review call. That is a self-review, not an independent reader. A mistake the model cannot see in its own patch is a mistake this step will not catch. The scope, size, and wiring checks do not call the model. The receipt `model` field is that tag. Read the attempt receipt for the verdict. Do not treat a model accept as a second person.

## Receipt schema `pfy-local-build/1`

File: `<receipt-dir>/receipt.json`, written atomically, including on BLOCKED (then `worktree` is null).

Fields: `schema`, `id`, `task` (first 500 chars, redacted), `repo`, `base_sha`, `model`, `endpoint` (host only), `status` (`PASS|FAIL|BLOCKED|TIMEOUT|ABORTED`), `reason`, `exit_code`, `wall_seconds`, `agent_seconds`, `tests_before`, `tests_after`, `files_changed`, `branch`, `commit`, `worktree`, `model_was_loaded`, `unloaded`, `mem` (`mem_available_gb`, `swap_free_gb`, `min_available_gb`), `opencode_version`, `agent_log`, `sandbox` (`bwrap-unshare-net`, `bwrap-share-net`, or `unsafe-no-sandbox`), `started_at`, `finished_at` (UTC, `Z`).

`password: x` redacts to `password:***`. Token, key, secret, and passwd assignments redact the same way. `Authorization: Basic` and an `AKIA` id (16 trailing characters) keep a four-character prefix and then `***`. A PEM private-key block becomes `[redacted-private-key]`. A value of four characters or fewer becomes `***`.

`tests_before` and `tests_after`: `cmd`, `exit`, `passed`, `failed`, `errors`, `seconds`, `tail` (last 40 lines, redacted).

Summary line: `PASS|FAIL|BLOCKED:|TIMEOUT <reason> branch=<name|none> receipt=<path>`.

Exit codes: 0 PASS, a clean dry-run, or `--reap`. 1 FAIL. 2 usage, or `no-opencode`. 3 TIMEOUT. 4 BLOCKED (`mem`, `busy-host`, a failing `/api/ps`, `model-too-big`, `cloud-tag`, `another run`, `no-model`, `no-sandbox`, `no-runtime-dir`, `runtime-dir-in-tmp`, `socket-path`). Stderr for a block is `BLOCKED: <message>`. The reason code stays short.

## Guards, fail, recover

| Fail | Exit | Reason | Recover |
|---|---|---|---|
| `MemAvailable + SwapFree` below `--min-free-gb` | 4 | `mem` | free memory. Full swap counts as 0. `SwapTotal` is not free |
| another model loaded | 4 | `busy-host` | that model unloads on its own. This tool does not unload it |
| model size over 30 GiB | 4 | `model-too-big` | pick a smaller tag |
| tag contains `:cloud` | 4 | `cloud-tag` | pick a local tag |
| `opencode` missing | 2 | `no-opencode` | `./pfy attach opencode` |
| Ollama down or tag missing | 4 | `no-model` | start Ollama, or name a tag it lists |
| `/api/ps` is not 200, times out, or is not JSON | 4 | `busy-host` | the guard fails closed. It does not fall through to `ollama ps` |
| bwrap missing and no `--unsafe-no-sandbox` | 4 | `no-sandbox` | install bwrap, or pass the flag and accept `unsafe-no-sandbox` on the receipt. The flag prints a stderr WARN when bwrap is missing. It does not turn off a working bwrap. It also leaves the test gate unsandboxed |
| runtime dir missing or not writable | 4 | `no-runtime-dir` | set `XDG_RUNTIME_DIR` or `/run/user/$UID` to a writable dir outside `/tmp`. An explicit bad XDG does not fall back. If XDG is unset and that path is also missing, a worktree socket shorter than 108 bytes is used |
| runtime dir is under `/tmp` or `/var/tmp` | 4 | `runtime-dir-in-tmp` | point `XDG_RUNTIME_DIR` outside the sandbox tmpfs |
| the Ollama socket path is 108 bytes or longer | 4 | `socket-path` | use a shorter runtime dir. The inode stays at `worktree/tmp/ollama.sock` |
| lock held by a live pid | 4 | `another run` | wait. A dead pid's lock does not block. `--reap` while the lock is held is the same BLOCKED |
| agent edits nothing | 1 | `no-change` | a real edit |
| a `--protect` path changes | 1 | `protected-path-changed` | leave those paths alone. This fires before the test command |
| tests fail, a new skip, xfail, deselect, or error, or exit 0 with no summary | 1 | `tests-failed` | fix the code. Do not skip the failure. An unknown runner needs a parseable passed count |
| fewer tests than before, even if exit 0 | 1 | `tests-regressed` | do not delete tests |
| a gate file changes or appears, and the judge did not already fail | 1 | `tests-tampered` | do not rewrite asserts, add a conftest, or edit `.gitignore` to hide a file. `--writable-test` is the only exception for test bodies. Gate basenames are still hashed |
| the same command fails on the second run | 1 | `tests-flaky` | no commit |
| the worktree digest changes after the gate and before `git add` | 1 | `worktree-changed-after-gate` | the pid namespace should have died with bwrap. A survivor that rewrites `src` fails here |
| the fresh checkout of the new commit fails the gate | 1 | `commit-recheck-failed` | the commit is reset before the branch is created. A gitignored helper cannot be the only copy of the fix |
| test command cannot start | 1 | `test-cmd-failed-to-start` | a command that exists |
| agent exceeds `--timeout` | 3 | `timeout` | longer timeout, or `--run-tests-on-timeout` to still run the gate. No commit by default |
| SIGINT or SIGTERM | 1 | `interrupted` | run again. The lock is released |
| watchdog sees MemAvailable under 16 GiB | 1 | `mem-edge` | free memory. Only this run's agent group is killed |

On FAIL, TIMEOUT, and BLOCKED there is no branch and no commit. The worktree is kept when one was created.

## Eval

```text
./pfy eval-local-build [--only ID] [--limit N] [--model TAG] [--endpoint URL]
    [--timeout SEC] [--test-timeout SEC] [--require-live]
```

Same command: `python3 scripts/pfy_local_build_eval.py`.

Fixtures live in `eval/local-build/fixtures/<id>/` with `tasks.json`. Each task fails its tests and its `check_cmd` before `reference.patch` and passes both after. The patch is not copied into the repo the agent sees.

The runner writes `pipelines/dogfood/build-local-eval/<stamp>/summary.json` and `summary.md` (gitignored). Exit 0 when every scored task passed, or when the run is a named skip. Exit 1 when pass is below passed+failed+blocked, or when the runner broke. Exit 2 when `--require-live` and a skip fired. The old exit-0-on-a-low-rate contract is gone.

`PFY_LOCAL_BUILD_UNSAFE_NO_SANDBOX=1` forwards `--unsafe-no-sandbox`. Without it, a missing bwrap is `BLOCKED` `no-sandbox`. The product does not turn that flag on by itself.

Skips, printed as `SKIP: <reason>`: `opencode-missing`, `ollama-unreachable`, `model-missing <tag>`, `mem-guard <gib>`, `busy-host <model>`, `busy-host unknown` (the ps call failed). A BLOCKED task stops the run. Later tasks are `not-run`. A skip or a BLOCKED task is not a pass.

All eight tasks protect `tests/*`, `conftest.py`, `pytest.ini`, `pyproject.toml`, `setup.cfg`, and `tox.ini`. The reference patches only touch `src/`. The offline stub that rewrites asserts to `assertTrue(True)` scores 0.

Tasks stay on one model load: every build uses `--keep-model`, and the last build uses `--unload-at-end` only if this eval loaded the model. A model that was already loaded is left loaded.

## Live result

### Stale, scored before B1

Stamp `20261026T072940388555Z` on host `nimo`, model `qwen3.6:35b`, endpoint `127.0.0.1:11434`. Eval exit 0. Pass rate 8/8 (1.0). Total 571.668 s. Mean 71.459 s. No failures. CONTEXT while loaded was 262144, so there is no `context_warning`. Ollama was not reconfigured. This number is not evidence for the repaired gate. The offline stub cheater, not a live model, is what scores 0 against `assertTrue(True)` on t01, t04, and t08.

### First rerun, aborted

Stamp `20261027T030049105086Z`. Preflight at 2026-10-27T03:00:49Z: MemAvailable about 54.1 GiB, SwapFree about 1.0 GiB, `ollama ps` empty. t01, t02, and t03 returned `FAIL` `no-change` in about 83 s. OpenCode's stderr was `Cannot connect to API: The socket connection was closed unexpectedly.` Ollama never showed the model. Cause: the loopback bridge used a 3 second connect timeout and left that timeout on the proxied socket, so a quiet model load was cut off. A slow-upstream test fails in 4.1 s without `settimeout(None)` after the handshake (`RemoteDisconnected`). The run was stopped at t04 (`interrupted`). It is not a pass rate.

### Post-fix rerun

Stamp `20261027T031008578576Z` on host `nimo`, model `qwen3.6:35b`, endpoint `127.0.0.1:11434`. Eval exit 0. Pass rate 8/8 (1.0). Total 608.235 s. Mean 76.029 s. No failures, no blocked, no not-run. Every task used `bwrap-unshare-net`. Every task had `tests_before.exit` 1 and `tests_after.exit` 0.

A probe in this session had already loaded the model, so each receipt says `model_was_loaded` true and `unloaded` false. The eval did not unload a model it had not loaded. After the receipts were copied, this session ran `ollama stop qwen3.6:35b`. `ollama ps` was then empty. While loaded, `context_length` was 262144, so there is no `context_warning` and Ollama was not reconfigured.

The offline stub that rewrites asserts to `assertTrue(True)` scores 0. That is `test_cheat_asserts_scores_zero_on_t01_t04_t08`, not a live model.

| id | status | reason | wall_s |
|---|---|---|---|
| t01-fix-off-by-one | PASS | ok | 64.433 |
| t02-add-function | PASS | ok | 67.241 |
| t03-rename-symbol | PASS | ok | 77.470 |
| t04-fix-mutable-default | PASS | ok | 117.812 |
| t05-add-cli-flag | PASS | ok | 58.887 |
| t06-parse-duration | PASS | ok | 50.177 |
| t07-remove-dead-code | PASS | ok | 73.012 |
| t08-fix-unicode-strip | PASS | ok | 99.203 |

Committed summary: [live-20261027T031008578576Z.md](../../eval/local-build/live-20261027T031008578576Z.md). Raw receipts stay gitignored under `pipelines/dogfood/build-local-eval/20261027T031008578576Z/`.

| id | status | reason | wall_s |
|---|---|---|---|
| t01-fix-off-by-one | PASS | ok | 94.830 |
| t02-add-function | PASS | ok | 57.580 |
| t03-rename-symbol | PASS | ok | 78.778 |
| t04-fix-mutable-default | PASS | ok | 66.103 |
| t05-add-cli-flag | PASS | ok | 41.559 |
| t06-parse-duration | PASS | ok | 69.653 |
| t07-remove-dead-code | PASS | ok | 60.889 |
| t08-fix-unicode-strip | PASS | ok | 102.276 |

Each task had `tests_before.exit` 1 and `tests_after.exit` 0. The receipt for t08 has `unloaded: true`. At 2026-10-26T07:39:19Z `ollama ps` was empty, `opencode` comm count was 0, and `free -g` showed Mem available 86 (start was 63). Swap stayed full, which it already was at the gate.

Can `./pfy build --local` replace Grok Build on a build-only run today? For these eight tiny fixtures, the post-fix rerun passed 8/8 in 608 s on `qwen3.6:35b` inside bubblewrap. A real task from `docs/TODO.md` is still unmeasured (MVP-2). Cloud `./pfy build` is a different program and was not edited.

## Sandbox

The agent runs under bubblewrap when `bwrap` works. The root is read-only. The worktree is read-write. The main checkout, `~/.ssh`, `~/.config/gh`, `~/.grok`, the git common dir, and the git dir are hidden. A hidden directory that is an ancestor of the worktree is a tmpfs, then `--dir` rebuilds the path, then the worktree is bound.

Loopback Ollama uses `--unshare-net` plus one AF_UNIX to TCP splice. The TCP connect allows 3 seconds for the handshake, then the proxied socket blocks for the whole response. Leaving that timeout on the socket cut off a quiet model load and OpenCode reported a closed socket. The socket inode is under the worktree `tmp/`. The name is a short symlink in `XDG_RUNTIME_DIR` or `/run/user/$UID`, because `sun_path` is 108 bytes and this worktree path is longer. That is not `/tmp`. `/run` stays read-only inside the sandbox, so the agent cannot replace the symlink. The listener is a daemon thread in a wrapper that `subprocess.call`s the agent. A forked listener kept bwrap alive after the HTTP response and was reparented to the user systemd.

A non-loopback endpoint uses `--share-net`. Git lockdown still applies. Every sandbox, including that mode, also passes `--die-with-parent`, `--unshare-pid`, `--unshare-ipc`, and `--unshare-uts`. The test gate uses the same profile with `--unshare-net` and no Ollama bridge. Missing bwrap without `--unsafe-no-sandbox` is `BLOCKED` `no-sandbox`. The flag does not disable a working bwrap. When bwrap is missing and the flag is set, stderr gets one WARN that the run is not sandboxed. A runtime dir under `/tmp` is `runtime-dir-in-tmp`. A missing runtime dir is `no-runtime-dir`. An over-long socket path is `socket-path`.

For a linked worktree, `.git` points at `worktree/tmp/git-sandbox` during the agent only. That dir is seeded with the worktree files and has no remotes. `pushurl` is `file:///pfy-local-build-push-blocked`, hooks are an empty directory, and the credential helper is empty. The caller's common git config is not edited. The original `.git` bytes are restored before the product commit. `GIT_CONFIG_*` is on the agent environment only. If `.git` is not a file, the swap is skipped and the read-only filesystem is the boundary.

Opencode's permission file stays, as defence in depth. It is not the boundary. The home for that file is `worktree/tmp/opencode.home` and is deleted after the run, along with the lock and the pid file.

## Known gaps

- Confinement is bwrap 0.11.1 as the same uid. It is not a separate user. It is not a claim about a kernel bug or a bwrap bug.
- Egress is closed only in `bwrap-unshare-net`, and even then one port reaches the local Ollama. `bwrap-share-net` shares the network namespace. Curl to the wider network is possible in that mode. Push is still blocked by the sandbox git dir and the read-only root, which the black-box tests demonstrated for the five push forms and for `python` `open()` of a host file.
- SIGKILL of the runner cannot write its own receipt. The next run and `pfy build --local --reap` kill a dead pid's recorded group, write `ABORTED` for a `build-local` directory with no receipt, and write `ABORTED` into the pid file's `receipt_dir` when that receipt is missing. The model is unloaded only if `loaded_by_run` is set. A live recorded pid is left alone, because the pid may have been recycled. If the process dies before the pid file exists, there is nothing to reap. With `--unshare-pid` and `--die-with-parent`, the sandbox dies with bwrap. Fix-2 gaps that are still open are listed under "Known gaps, fix round 2". The 901-test counts below are the fix-1 run. The fix-2 counts are in the Suites section at the top.
- The agent group gets SIGTERM, five seconds, then SIGKILL, including after the leader has exited. A child that ignores SIGTERM still dies on SIGKILL. That grace is why a hang is not instant.
- Ubuntu CI history: `CloudBuildUnchangedTests` used to need `grok` and a full help golden that differs across Python versions. It now skips when `grok` is missing, checks stable substrings and exit codes, and deletes any new file under `pipelines/dogfood/build/`. Behavior tests add `--unsafe-no-sandbox` only when that process cannot run bwrap, so a runner without bwrap is not a new red. `SandboxEscapeTests` skip only in that case. This box ran them. Nothing was apt-installed.
- Python 3.13 is not installed on this box. Python 3.14.4: 901 tests, 623.379 s, 1 failure, 16 skipped. The failure is `test_relative_outdir_log_path_safe` because `TMPDIR` is inside the repo. Python 3.12.12 (uv prefix): 901 tests, 552.107 s, 21 failures, 16 skipped. One is that same outdir case. The other 20 are `tests.test_harness2_local_sandbox`: the sandbox tries to exec `sys.executable`, and the uv binary lives under the home that sandbox hides (`FileNotFoundError` on that path). The same tree passed those tests under `/usr/bin/python3`. They are not in the fix-1 diff. The hedge detector and the two lab-stage cases did not fail on either run (Ollama was up).
- One model at a time. A second loaded model is `BLOCKED: busy-host`, and this tool does not unload it. A failed `/api/ps` is the same BLOCKED, not an `ollama ps` fallback.
- The default test command is `python3 -m unittest discover -s tests -t .`. Other stacks need `--test-cmd`.
- If a host's Ollama context is below 16384, the runner records `context_warning` and does not reconfigure Ollama. The stale run's context was 262144.
- No push and no PR, by design. The branch stays in the repo's `tmp/` worktree. On PASS that worktree is removed.
- The fixtures are eight tiny tasks. They are not a cost or pass-rate comparison against cloud `./pfy build`.
- Daemon splice threads can emit `ResourceWarning` for sockets they do not close. The bridge test still passes.

## RED

- RED: skip the free-RAM-plus-swap check -> test_low_memory_blocks_and_full_swap_is_not_free
- RED: count total swap -> test_low_memory_blocks_and_full_swap_is_not_free
- RED: skip the protected-path check -> test_protected_test_edit_does_not_commit
- RED: accept a lower test count -> test_deleting_a_test_is_a_regression
- RED: unload unconditionally -> test_model_already_loaded_is_not_unloaded
- RED: skip start_new_session -> test_hang_is_timeout_and_the_group_is_gone
- RED: commit before the gate -> test_protected_test_edit_does_not_commit, test_worse_tests_do_not_commit, test_deleting_a_test_is_a_regression
- RED: run in the origin checkout instead of a worktree -> test_fix_creates_one_commit_and_leaves_the_checkout_alone
- RED: reference.patch for t01 is a no-op -> test_every_fixture_fails_before_the_patch_and_passes_after
- RED: count a SKIP or BLOCKED as PASS -> test_missing_opencode_skips, test_low_memory_blocks_the_first_task_and_stops
- RED: read the pass rate from the stub exit code instead of the receipts -> test_delete_tests_is_zero_and_the_reason_comes_from_the_receipt
- RED: run check_cmd against the fixture instead of the produced worktree -> test_solve_mode_passes_all_eight
- RED: remove the test-file hash -> test_rewriting_asserts_to_true_does_not_commit (PASS, exit 0, assertion 0 != 1)
- RED: remove the kill on leader exit and the post-loop kill -> test_orphan_background_does_not_block (TimeoutExpired at 25 s)
- RED: run_sandboxed returns the raw argv -> test_push_forms_and_secret_write_do_not_leak (bare SHA changed)

Fix-2 mutants are listed under "RED, fix round 2" at the top. They were restored before the suite run. `git diff` does not contain them.

## Status

Current (fix round 2):

- Branch: `bot/mvp-local-build`. Do not merge to main. No PR.
- Compare: https://github.com/themark-net/pfy-mentat/compare/main...bot/mvp-local-build
- Read the head with `git rev-parse HEAD`. A commit cannot record its own SHA.
- Parent of the fix-2 work: `598bb3dcdae42c7adc58b9d0fe15a5b7a6d5533b` (`docs: pfy-local-build MVP fix round 2 drop-in`).
- Suites, blockers, and gaps: the Fix round 2 section at the top.
- Live stamp `20261027T070700973123Z`: 8/8, 617.949 s, mean 77.244 s, `bwrap-unshare-net`, context 262144. Summary: `eval/local-build/live-20261027T070700973123Z.md`.
- `gh` cannot trigger `eval-structural.yml` from this box (not authenticated). The caller re-runs the tip.
- Not a Feature GO. Catalog HOLD 70-75 stays. MVP-2 is still todo.
- `./pfy` and `scripts/pfy` are git mode `100755`. `scripts/pfy_build_p.py` is unchanged.

History, left so the old counts stay findable:

- Base at the first MVP commit: `7b716e86d5a3df3281b262ac15ec0b254f448041`.
- item 1: `b63d8d011ebe95558c35101c2f62d1a23975f861`. 25 behavior tests.
- item 2: `fbbaf90bc5a245d5ca69f274b610c68f369f3664`. 13 behavior tests.
- item 3: `da2ce97`. Live 8/8, 571.668 s. That 8/8 is stale after the gate FAIL.
- item 4: `e63a95b`. Tester and Reviewer then failed that SHA.
- fix 1: merge of `origin/main` is `008c7b2` (`2f2b20e`, catalog only). Post-fix live stamp `20261027T031008578576Z`, 8/8, 608.235 s, context 262144.
- fix 1 suites: Python 3.14.4, 901 tests, 623.379 s, failures=1, skipped=16. Python 3.12.12, 901 tests, 552.107 s, failures=21, skipped=16. Python 3.13 is not installed on this box.
- Earlier unit counts on this branch: 804, then 842. Both had the single `test_relative_outdir_log_path_safe` failure when `TMPDIR` is inside the repo. Fix 2 is 916 on the same failure, plus the 20 uv-3.12 harness2 failures under Python 3.12 only.
- Local structural run on 2026-10-26 exited 1 on that same unittest check. The other `run:` steps exited 0. Regenerated golden and dashboard files were restored and are not part of these commits.

## Commits

Read `git log --oneline origin/main..HEAD` on `bot/mvp-local-build`. The fix-2 commit is the one whose subject starts with `pfy-local-build: close gate blockers 1-6`. It cannot list its own SHA.
