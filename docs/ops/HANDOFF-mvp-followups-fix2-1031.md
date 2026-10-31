# Handoff: mvp-followups-fix2-1031

Status: stopped. Exit: lane empty after round 2. Branch `bot/mvp-followups-fix2-1031`, worktree `~/DEVELOP/pfy-mentat/tmp/mvp-followups-fix2-1031`. Base `origin/bot/pfy-followups-1030` at `c0d38af`. No PR, no merge, no tag.

Round 1 stopped at 2026-10-31T21:37:19Z. The parent reopened the lane the same day with F1, F2, P2, and G1. Those four are done. Checked at the round 2 start (2026-10-31T21:47:11Z): MemAvailable about 58 GiB, load about 4.8 on 32 cores, `Runner.Worker` pid 2631906 alive. Pregate not run: the round 2 addendum says not to, and the runner was busy.

Integration: merge this branch only after `bot/pfy-followups-1030`.

## Done

| Item | Commit | Tests | Gate |
|------|--------|-------|------|
| Hosted CI runs the workflow image-pin lint | `a5805d9` (run log `34f10f7`) | `tests.test_workflow_image_pin`: 16 OK in 6.850s | Tester plus Reviewer |
| One interpreter, missing PyYAML fails closed | `6d3f8de` (run log `c328da2`) | `tests.test_workflow_image_pin`: 17 OK in 12.846s | Tester plus Reviewer |
| Container and service image pins | `e4f03f4` (run log `b88dd81`) | `tests.test_workflow_image_pin`: 21 OK in 13.428s | Tester plus Reviewer |
| Attach mutants A3 A4 A5 A7 A8 A10 | `34ccff0` (run log `7164136`) | `tests.test_attach` and `tests.test_registry`: 39 OK in 1.143s | Tester plus Reviewer |
| F1 bwrap probe passes `--bind` and `--die-with-parent` | `b5754cb` (run log `db3d8b5`) | `tests.test_x_intake_smoke_149`: 27 OK in 2.889s | Tester plus Reviewer |
| F2 `--tmpfs` fake-bwrap twin | `f6a74ea` (run log `47e7edc`) | `tests.test_x_intake_smoke_149`: 28 OK in 2.940s | Tester plus Reviewer (test-only; pregate not run) |
| P2 failing image-pin lint fails pregate | `cd4c116` (run log `4d73492`) | `tests.test_workflow_image_pin`: 22 OK in 19.700s | Tester plus Reviewer |
| G1 root-length guard boundary | `a2a9317` | `tests.test_workflow_image_pin`: 24 OK in 25.749s | Tester plus Reviewer (test-only; pregate not run) |

Stamp commits only record the item SHA. They do not change behavior. The handoff commit is the one that adds this file's round 2 text.

## Round 2 mutation checks

Each mutant was applied, the named test was run, and the file was restored. `cmp` against the backup matched. None of these diffs were committed.

| Mutant | Result |
|--------|--------|
| F1 drop `--die-with-parent` from the probe | RED `test_bwrap_rejecting_bind_or_die_with_parent_is_unavailable` (reason becomes `version pin 3.12.0 != --version None`) |
| F1 drop `--bind` from the probe | RED the same test, on the `--bind` case, same version-pin reason |
| F2 drop `--tmpfs` from the probe | RED `test_bwrap_without_tmpfs_mount_fails_closed_with_bwrap_reason`, same version-pin reason |
| P2 ignore `PREGATE_IMAGE_PIN_ROOT` | RED `test_failing_image_pin_lint_fails_pregate` with OVERALL=PASS |
| G1 compare with `-ge` instead of `-gt` | RED `test_root_path_at_the_limit_passes_the_guard` (`path too long (57 > 57 chars)`) |

A real `bwrap` probe with `--bind <tmp> <tmp>` and `--die-with-parent` returned 0 on this host before F1 was committed.

## Mutation table (round 1 attach)

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

F1 bwrap probe. `examples/x-intake-local/smoke_149.py` `bwrap_ok` now runs `bwrap` with `--bind <temp> <temp>` and `--die-with-parent`, plus the `/proc` and tmpfs `/dev/shm` mounts the real run already used. The temp directory is removed before the function returns. If it cannot be created, the probe reports unavailable. A fake `bwrap` that exits 1 when it sees `--bind` or `--die-with-parent` makes the smoke exit 2 with `bwrap is not usable here; MemPalace must run with no network`, and MemPalace does not run. Recovery: fix the host so those flags work, then run the smoke again. There is no unsandboxed path.

F2 tmpfs twin. A fake `bwrap` that exits 1 only when argv contains `--tmpfs` (and exits 0 otherwise) makes the same smoke exit 2 with the bwrap reason. Recovery is the same as F1: the probe already passes `--tmpfs /dev/shm`. A probe that drops that flag looks like a version mismatch later; this test goes red first.

P2 failing lint. `PREGATE_IMAGE_PIN_ROOT`, when non-empty, is the path passed to `scripts/check_workflow_image_pin.py`. Unset or empty, the path stays `.github/workflows`. A scratch copy of `tests/fixtures/workflow_image_pin/latest.yml` (`ubuntu-latest`) makes `scripts/pregate.sh --only lint` exit nonzero and print `OVERALL=FAIL`. The lint log contains `unpinned GitHub-hosted runs-on (ubuntu-latest)`. Recovery: pin the fixture job to `ubuntu-24.04`, or unset the hook so the real workflows are checked. The real workflow files were not edited. A missing hook path fails closed inside the helper.

G1 root length. Pregate refuses `RUN_ROOT` or `SCRATCH` when the character length is greater than `PREGATE_MAX_ROOT_LEN` (default 60). The message is `path too long (N > LIMIT chars): <path>` and names `PREGATE_MAX_ROOT_LEN`. Exit is 2, before any check, so there is no OVERALL line. A limit equal to the longer of the in-place repo path and the scratch path (`<git common parent>/tmp/pgs/<7 sha chars>-<6 clock chars>`) passes the guard, and `--only lint` prints OVERALL=PASS. Recovery: use a shorter checkout, or set `PREGATE_MAX_ROOT_LEN` above that checkout. The B2 lint test still sets it to 200 so a long CI path can run the lint.

## Skipped

| Item | Why |
|------|-----|
| T-0081 OpenCode-in-cage | Named in the 1030 handoff. Needs docker. Not in the owned files. |
| T-0074 model run | Named in the 1030 handoff. Needs a local model. This lane is cloud Grok only. |
| T-0070 next scorer | Named in the 1030 handoff. No next scorer is named. Inventing one would be a new design. |
| `pfy build --local` loose ends | Named in the 1030 handoff. Those files are on the must-not-touch list. |
| Update `docs/ops/PREGATE.md` | Still owned by another lane. See the cross-lane request. |
| Update `sources/entries/149-mempalace.md` | Catalog file. This lane must not edit it. The probe text there still needs the new flags. See the cross-lane request. |
| Full pregate | Round 2 addendum says not to run it. `Runner.Worker` was also alive at the start of the round. |

No red-base failures in the owned tests. The first round-1 exit-code failures were the new tests dropping the `Popen`, which let `Popen.__del__` consume the zombie. The tests now keep that handle until the call returns. That was not a failure on the base.

## Cross-lane requests

`docs/ops/PREGATE.md` lint row: say that the same helper also checks `jobs.*.container` and `services.*.image` (pinned tag, and `@sha256:` when any image in the run already has one), that pregate and G0 both exec `command -v python3`, and that `.github/workflows/eval-structural.yml` job `structural-github` runs the helper on `.github/workflows` after installing PyYAML for that interpreter. Also say that `PREGATE_IMAGE_PIN_ROOT`, when non-empty, replaces that directory for the lint call, and that the root-length guard is a strict greater-than on `RUN_ROOT` and `SCRATCH` (a path of exactly `PREGATE_MAX_ROOT_LEN` is accepted; exit 2 with `path too long` when it is longer). Do not edit that file from this lane.

`sources/entries/149-mempalace.md`: the `bwrap_ok` probe now also passes `--bind` of a real temp directory and `--die-with-parent`, the same flags `run()` uses. A bwrap that rejects either flag exits 2 with the bwrap reason. Do not edit that catalog file from this lane.

## Gate

Tester plus Reviewer. This run changes runtime (`pfylib/attach.py`, `examples/x-intake-local/smoke_149.py`, `scripts/pregate.sh`) and CI (`.github/workflows/eval-structural.yml` from round 1). Pregate not run.

## Next step

Tester plus Reviewer on `bot/mvp-followups-fix2-1031` at the handoff commit. After both PASS, merge only after `bot/pfy-followups-1030` is on main. Do not merge from this lane.
