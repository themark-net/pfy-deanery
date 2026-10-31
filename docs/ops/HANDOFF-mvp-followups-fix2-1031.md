# Handoff: mvp-followups-fix2-1031

Status: stopped. Exit: lane empty. Branch `bot/mvp-followups-fix2-1031`, worktree `~/DEVELOP/pfy-mentat/tmp/mvp-followups-fix2-1031`. Base `origin/bot/pfy-followups-1030` at `c0d38af`. No PR, no merge, no tag.

Checked 2026-10-31T21:37:19Z: `Runner.Worker` pid 2242260 is alive. MemAvailable about 59 GiB. Load about 4.5 on 32 cores. Not host-pressure. Pregate not run: host busy.

Integration: merge this branch only after `bot/pfy-followups-1030`.

## Done

| Item | Commit | Tests | Gate |
|------|--------|-------|------|
| Hosted CI runs the workflow image-pin lint | `a5805d9` (run log `34f10f7`) | `tests.test_workflow_image_pin`: 16 OK in 6.850s | Tester plus Reviewer |
| One interpreter, missing PyYAML fails closed | `6d3f8de` (run log `c328da2`) | `tests.test_workflow_image_pin`: 17 OK in 12.846s | Tester plus Reviewer |
| Container and service image pins | `e4f03f4` (run log `b88dd81`) | `tests.test_workflow_image_pin`: 21 OK in 13.428s | Tester plus Reviewer |
| Attach mutants A3 A4 A5 A7 A8 A10 | `34ccff0` (run log `7164136`) | `tests.test_attach` and `tests.test_registry`: 39 OK in 1.143s | Tester plus Reviewer |

Exit card: `8b70e73`. Stamp commits only record the item SHA. They do not change behavior.

## Mutation table

Mutants were applied to `pfylib/attach.py`, the named test was run, and the file was restored. None of these diffs were committed. `cmp` against the backup matched after the last restore.

| Mutant | What changed | Result |
|--------|----------------|--------|
| A3 orphan window | `_close_failed_spawn` does not call `_reap_our_child` | RED `test_failed_terminal_reaps_the_spawned_child`. RED `test_failed_terminal_reaps_open_session_child` |
| A4 lost process group | `os.kill(pid, SIGTERM)` instead of `os.killpg` | RED `test_failed_terminal_reaps_the_process_group`. GREEN `test_failed_terminal_reaps_the_spawned_child` |
| A5 lost caller exit code | return dict `exit_code` forced to 0; receipt still gets the real status | RED `test_failed_terminal_exit_code_reaches_the_caller`. GREEN `test_failed_terminal_exit_code_reaches_the_receipt` |
| A7 lost receipt exit code | receipt JSON writes `exit_code` 0; the caller still gets the real status | RED `test_failed_terminal_exit_code_reaches_the_receipt`. GREEN `test_failed_terminal_exit_code_reaches_the_caller` |
| A8 no printed hint | missing `opencode` does not `print` the setup line | RED `test_missing_opencode_prints_install_hint_and_does_not_spawn` |
| A10 no caller hint | `next_step` is the stub `./pfy start opencode` instead of the setup line | RED `test_missing_opencode_prints_install_hint_and_does_not_spawn` |

The six names were not in the 1030 handoff or the tester notes. They were recreated from the drop-in: orphan window, lost exit code, no install hint.

## How each change fails and recovers

Hosted image pin. The G0 job `structural-github` stays on `ubuntu-24.04` and runs `scripts/check_workflow_image_pin.py .github/workflows`. A PR that sets a hosted runner to `ubuntu-latest`, or any other value that is not `ubuntu-24.04`, fails that step. Recovery: set the hosted `runs-on` back to `ubuntu-24.04`. Self-hosted label lists still pass.

Interpreter. Pregate and the hosted lint step both exec `command -v python3` with no `readlink -f`. If that interpreter cannot import PyYAML, the helper exits 1 and the message names that path (`sys.executable`). Recovery: install PyYAML for that same interpreter, or put an interpreter that already has it first on PATH. The hosted job installs PyYAML in a separate step before the lint step. The lint step itself does not install, so a PATH python without PyYAML still fails closed.

Container and service images. `jobs.*.container` (string or `image:`) and `services.*.image` need a tag. `latest` is rejected in any case. A missing tag, an empty tag, an unresolved `${{ }}` image, a digest that is not `@sha256:` plus 64 hex digits, or a malformed shape (not a string or a mapping, service with no image, empty services) exits 1. If any image in that invocation already contains `@sha256:`, every image in the invocation must carry a valid digest. A tag is still required when a digest is present. A registry port is not the tag. Recovery: pin `name:tag`, and if the set uses digests, add `@sha256:` plus 64 hex digits to every image. This repo's real workflows have no container images, so they still pass.

Attach. A spawn that does not stay up SIGTERMs the process group only when `/proc/<pid>/status` shows this process as `PPid`, and never signals this process's own group. `waitpid` then records the real status (exit code, or 128 plus the signal) on the return dict and in `<sid>-attach-receipt.json`. A write error on the receipt does not drop the code from the return value. Recovery: the session file is already cleared; fix the terminal and call again. Missing `opencode` prints the harness setup line (`install opencode; point skills at bootstrap/grok-cli/skills; LOCAL_OPENAI_BASE_URL`), returns FAIL with that string as `next_step`, and does not spawn. Recovery: install opencode with that line and call again. A prove failure (the process is still alive, smoke failed) is not reaped.

## Skipped

| Item | Why |
|------|-----|
| T-0081 OpenCode-in-cage | Named in the 1030 handoff. Needs docker. Not in the owned files. |
| T-0074 model run | Named in the 1030 handoff. Needs a local model. This lane is cloud Grok only. |
| T-0070 next scorer | Named in the 1030 handoff. No next scorer is named. Inventing one would be a new design. |
| `pfy build --local` loose ends | Named in the 1030 handoff. Those files are on the must-not-touch list. |
| Update `docs/ops/PREGATE.md` | The lint row still describes only `runs-on`. It does not mention container or service images, the explicit interpreter, or the hosted G0 step. This lane does not own that file. See the cross-lane request. |

No red-base failures in the owned tests. The first exit-code failures were the new tests dropping the `Popen`, which let `Popen.__del__` consume the zombie. The tests now keep that handle until the call returns. That was not a failure on the base.

## Cross-lane request

`docs/ops/PREGATE.md` lint row: say that the same helper also checks `jobs.*.container` and `services.*.image` (pinned tag, and `@sha256:` when any image in the run already has one), that pregate and G0 both exec `command -v python3`, and that `.github/workflows/eval-structural.yml` job `structural-github` runs the helper on `.github/workflows` after installing PyYAML for that interpreter. Do not edit it from this lane.

## Gate

Tester plus Reviewer. This run changes runtime (`pfylib/attach.py`) and CI (`.github/workflows/eval-structural.yml`). Pregate not run: host busy.

## Next step

Tester plus Reviewer on `bot/mvp-followups-fix2-1031` at `7164136` plus this handoff commit. After both PASS, merge only after `bot/pfy-followups-1030` is on main. Do not merge from this lane.
