# Handoff: reviewer follow-ups (mvp-review-fix2-1031)

Branch `bot/mvp-review-fix2-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-review-fix2-1031`. No PR. No force push. DevBot fast-forwards main after Tester plus Reviewer. This run does not merge.

Integrate after `bot/mvp-review-fix-1031`. `./pfy build --local` stays opt-in. Review stays on unless `--no-review`. `--retries` default stays 2. Exit codes stay 0 PASS, 1 FAIL (including reviewer-unavailable, crash, PASS-REJECTED, and stale-worktree), 2 usage, 3 TIMEOUT, 4 BLOCKED. No Ollama process was started. No model was loaded.

Wave 4 supersedes the earlier lane-empty handoff. The merge of `origin/bot/mvp3-review-retry` at `582414b` is `ae4ad38`. Product tip for the runtime changes is `08ca29b`.

## Wave 4 items

| Item | SHA | Tests |
|------|-----|-------|
| Wave 4 exit card | `c527aa9` | docs only |
| Merge 582414b | `ae4ad38` | local plus review, Ran 85 in 148.861s OK |
| S1 reviewer outage | `5cdc5c2` | review module, Ran 23 in 67.088s OK |
| S2 overall timeout | `55ca386` | review Ran 24 in 122.108s OK; local Ran 62 in 112.159s OK |
| S3 crash, not no-change | `c114c7f` | local module, Ran 64 in 84.626s OK |
| S4 one label list | `2bd11ce` | local module, Ran 65 in 85.031s OK |
| S5 stale worktrees | `08ca29b` | local module, Ran 68 in 87.750s OK |

## Earlier items still on the branch

| Item | SHA | Note |
|------|-----|------|
| 1 First outage token | `e685f70` | Superseded by S1. Current token is `reviewer-unavailable`, not `REVIEW-ERROR`. |
| 2 Mutant M4 | `d5f4812` | Outage is not a reject. Mutant failed, then the file was restored. |
| 3 Mutant M7 | `5079532` | Previous diff reaches the retry prompt. |
| 4 Scope vs commit | `7bdede7` | Already on the base. Reconfirmed by `582414b`. Not rewritten. |
| 5 Review defaults | `34a6eaf` | Help text and the MVP-3 handoff: review on, cap 3 files / 250 lines. |
| 6 No allow list | `cef308c` | Receipt `warnings` entry. The run can still PASS. |
| 7 Stub seam | `8dd5baf` | `PFY_STUB_*` only when `PFY_LOCAL_BUILD_TEST_SEAM=1`. |
| 8 Same-model note | `db3dfcb` | `eval/mvp3/REPORT.md`. Trial numbers were not re-run. |
| 9 Scratch path | `23ea0cd` | Eval scratch under the script repo `tmp/`. |
| 10 Ubuntu review parity | `187efde` | Review module ran 17, skipped 0, with bwrap hidden. |
| 11 Sandbox gate | `b483166` | This lane's copy of round-2 `mvp-sandbox-gate-1031`. |

## What changed in wave 4

An unreachable reviewer (HTTP error or a review-call timeout) sets receipt and attempt status `reviewer-unavailable`, exit 1. It is not `FAIL`, not `TIMEOUT`, and not `PASS-REJECTED`. Nothing is committed and the attempt is not retried. Empty diff stays `review-empty-diff`. An agent timeout stays reason `timeout`.

`--overall-timeout` (default 7200, env `PFY_LOCAL_BUILD_OVERALL_TIMEOUT`) caps the whole build and review loop from the start stamp. Hitting it sets status `TIMEOUT`, reason `overall-timeout`, exit 3. A shorter overall cap wins over the review-call timeout, so that case is `overall-timeout` rather than `reviewer-unavailable`.

A nonzero agent exit with an empty diff is status and reason `crash`, exit 1. It is not retried. Exit 0 with an empty diff stays `no-change`. A nonzero exit that wrote a diff still reaches the gate and can PASS.

Receipt status and the stdout summary token are the same word from `LABELS`: PASS, FAIL, PASS-REJECTED, reviewer-unavailable, crash, TIMEOUT, BLOCKED, ABORTED. `BLOCKED` no longer prints as `BLOCKED:`. `_lab` raises `LabelError` for any other word and that error is not rewritten to FAIL.

After the lock, leftover `tmp/local-build-*` directories are listed on `stale_worktrees` and removed before `git worktree add`. A path that is still there stops the run with status FAIL, reason `stale-worktree`, exit 1, worktree null. The agent does not start. Dry-run lists the leftovers and does not delete them.

## How this fails and how we recover

| Risk | How it fails | Recovery |
|------|--------------|----------|
| Reviewer HTTP 500 or review-call timeout | Status `reviewer-unavailable`, one attempt, no branch | Run again when the reviewer answers, or pass `--no-review` |
| Whole loop exceeds the wall cap | Status `TIMEOUT`, reason `overall-timeout`, exit 3, no branch | Run again with a larger `--overall-timeout` |
| Agent exits nonzero and writes nothing | Status `crash`, exit 1, not retried | Run the build again. An exit 0 empty diff can still retry as `no-change` |
| Summary token drifts from the receipt | Stdout first token must equal the receipt status, including `BLOCKED` with no colon | The eight words live in `LABELS` and in the module docstring |
| Unknown status rewritten to FAIL | `_lab("NOT-A-STATUS")` raises `LabelError` | Fix the word. Do not store it as FAIL |
| Leftover worktree cannot be removed | Reason `stale-worktree`, worktree null, agent does not start, directory remains | Delete that directory and run again. A removable leftover is deleted and named on the receipt |
| Dry-run deletes a leftover | Dry-run leaves the directory and still lists it | Dry-run starts nothing |
| Flag unsandboxes a working gate | Stub log must show `--unshare-net` and `unittest`, and `gate_unsandboxed` false | Install bwrap, or pass the flag only when it is missing |
| No allow list | PASS receipt carries a `warnings` entry | Add `files:` or `--allow-path` |
| Stub env in production | Seam unset. `sandbox_extra_rw` stays empty | Set `PFY_LOCAL_BUILD_TEST_SEAM=1` only in the harness |
| Review tests skip on ubuntu | Parity test hides bwrap and requires OK with no skips | Keep the stub HTTP reviewer |

## Skipped

- Further plan rows after S5. G1, G2, G3, G6, G7, G8, and G9 belong to other lanes and other files. G4 and G5 are already on the base. G10 is excluded. Round 2 `mvp-sandbox-gate-1031` is item 11.
- `mvp-local-t5-1031`. It needs a local model and it writes `eval/mvp-1031/`, which this lane must not touch. This drop-in says never load a model.
- Official `./scripts/pregate.sh`. pregate not run: host busy. At 2026-10-31T23:18:15Z `Runner.Worker` pid 3510235 was live. MemAvailable was about 79 GiB and load was about 3.71 on 32 cores, so this was the runner, not host pressure.

## Cross-lane

- `scripts/pregate.sh` still sets scratch from `git rev-parse --git-common-dir`, so a linked worktree writes `tmp/pgs` under the main checkout. That file is not owned. Do not move it into a long worktree path: `docs/ops/PREGATE.md` keeps run roots at or under 60 characters so harness2 unix sockets fit `sun_path`. OQ draft: if pregate scratch must stay inside the invoking worktree, the short-path rule needs a new design. This lane did not write that ADR.
- Cloud runner: if it copies `--unsafe-no-sandbox`, copy the gate rule too. `gate_unsandboxed` is true only when bwrap is missing and the flag is set.
- Cloud runner: if it copies the review loop, copy `reviewer-unavailable` (not retried, not a reject), the overall cap, crash versus no-change, the label list, and stale-worktree. Do not import this lane's file. Those files are not owned here.
- Integrate: merge `bot/mvp-review-fix2-1031` after `bot/mvp-review-fix-1031`.

## Gate

Runtime changes in `scripts/pfy_build_local.py`. Needs Tester plus Reviewer at the branch tip. Official pregate was not run (host busy). The local module at S5 was Ran 68 in 87.750s OK. The review module was last run green at S2 (Ran 24 in 122.108s OK) and was not re-run for S3 through S5, which did not change the review verdict path. No Feature GO.

## Next

Gate this branch. Then merge it after `bot/mvp-review-fix-1031`. No further local-runner row from the parallel plan fits these files.
