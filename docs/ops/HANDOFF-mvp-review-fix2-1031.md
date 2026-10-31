# Handoff: reviewer follow-ups (mvp-review-fix2-1031)

Branch `bot/mvp-review-fix2-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-review-fix2-1031`. Base `origin/bot/mvp-review-fix-1031`, plus merge `fbb2835` of `origin/bot/mvp3-review-retry` (`d624535`). No PR. No force push. Mark merges after Tester plus Reviewer. This run does not merge.

Integrate after `bot/mvp-review-fix-1031`. `./pfy build --local` stays opt-in. Review stays on unless `--no-review`. `--retries` default stays 2. Exit codes are unchanged (0 PASS, 1 FAIL including REVIEW-ERROR and PASS-REJECTED, 2 usage, 3 TIMEOUT, 4 BLOCKED). No Ollama process was started. No model was loaded.

## Items done

| Item | SHA | Tests |
|------|-----|-------|
| Exit card | `9fee546` | docs only |
| Merge MVP-3 tip | `fbb2835` | merge, no rebase |
| 1 Reviewer outage | `e685f70` | both modules, Ran 74 in 109.054s OK |
| 2 Mutant M4 | `d5f4812` | outage tests; mutant failed, then restored |
| 3 Mutant M7 | `5079532` | review module, Ran 14 in 29.210s OK |
| 5 Review defaults | `34a6eaf` | review module, Ran 15 in 29.461s OK |
| 6 No allow list warning | `cef308c` | both modules, Ran 77 in 113.162s OK |
| 7 Stub seam | `8dd5baf` | review Ran 17 in 32.132s OK; local Ran 61 in 81.253s OK |
| 8 Same-model note | `db3dfcb` | docs only. Trial numbers were not re-run |
| 9 Scratch path | `23ea0cd` | eval module, Ran 19 in 47.288s OK |
| 10 Ubuntu review parity | `187efde` | parity test Ran 1 in 31.601s OK; inner review ran=17 skipped=0 |
| 11 Sandbox gate | `b483166` | local plus review, Ran 79 in 115.311s OK |

## What changed

Reviewer HTTP error or timeout is status `REVIEW-ERROR`, reason `review-unavailable`, exit 1. It is not retried and not a reject. The receipt carries a recovery line. Unparseable JSON stays `review-unparseable` and is still retried.

The retry prompt includes the previous diff. M4 (outage reported as `review-unparseable`) and M7 (empty previous diff) fail the new tests.

A task with no `files:` line and no `--allow-path` adds a `warnings` entry. The run can still PASS. `PFY_STUB_PLAN`, `PFY_STUB_COUNT`, and `PFY_STUB_PROMPTS` are read only when `PFY_LOCAL_BUILD_TEST_SEAM=1`. The receipt lists `sandbox_extra_rw`.

Help text and `docs/ops/HANDOFF-mvp3-review-retry.md` say review is on by default and the cap is 3 files and 250 added plus removed lines. `eval/mvp3/REPORT.md` says the reviewer is the same model as the agent (`qwen3.6:35b` on the same endpoint), so a shared blind spot is not an independent review. The human column is the independent read.

Eval copies and `TMPDIR` stay under the script repo's `tmp/` (or `--repo` under that tree). `--repo` elsewhere in the main checkout exits 2 before any write. `eval/mvp3/run_trial.py` already used its own file path. A hostile cwd and `TMPDIR` still create `tmp/mvp3-trial-tmp` here.

The review module has no bwrap skip and no model skip. A PATH with every executable except `bwrap` runs all 17 review tests, skipped 0.

`--unsafe-no-sandbox` sandboxes the test gate whenever bwrap works. The receipt field `gate_unsandboxed` is true only when a gate run took `unsafe-no-sandbox` because bwrap was missing and the flag was set. Without the flag, a missing bwrap is still `BLOCKED` `no-sandbox` and the field stays false. A stub bwrap that logs argv and execs the command after `--` proves the gate line contains `--unshare-net` and `unittest` while the flag is set.

## How this fails and how we recover

| Risk | How it fails | Recovery |
|------|--------------|----------|
| Reviewer HTTP 500 or timeout | Status `REVIEW-ERROR`, one attempt, no branch | Recovery line: run again when the reviewer answers, or pass `--no-review` |
| Outage counted as a reject | M4 tests expect `REVIEW-ERROR`, not `PASS-REJECTED` | Restore the unavailable return. Do not retry |
| Retry prompt drops the last diff | M7 test looks for the removed calc line under `Previous diff:` | The agent sees the prior patch and the reject reason |
| No allow list | PASS receipt carries `warnings` that scope was not checked | Add `files:` or `--allow-path`. The warning goes away. Exit code stays a normal PASS |
| Stub env in production | Seam unset. `sandbox_extra_rw` is empty | Set `PFY_LOCAL_BUILD_TEST_SEAM=1` only in the review harness |
| Same model reviews itself | Report states the human column is the independent read | Do not treat the model accept as a second opinion |
| Scratch follows cwd or `TMPDIR` into the main checkout | Eval refuses that `--repo` (exit 2) and pins `TMPDIR` to the script repo `tmp/` | Run the script from its worktree, or pass `--repo` under that tree |
| Review tests skip on ubuntu | Parity test hides bwrap and requires OK with no `skipped=` | Keep the stub HTTP reviewer. Do not add a bwrap skip |
| Flag unsandboxes a working gate | Stub log must show `--unshare-net` and `unittest` on one line, and `gate_unsandboxed` false | Install bwrap, or pass the flag only when it is missing and accept `gate_unsandboxed` true plus the stderr WARN |

## Skipped

- Item 4 (scope vs commit, gitignored extra file). Already on the base at `7bdede7`, which is an ancestor of this branch. Not on `origin/main`. Not rewritten.
- Further plan rows. G1, G2, G3, G6, G7, G8, and G9 belong to other lanes and other files. G10 is excluded. `mvp-local-t5-1031` needs a local model and `eval/mvp-1031/`. Lane empty.
- Official `./scripts/pregate.sh`. pregate not run: host busy. At 2026-10-31T21:26:33Z `Runner.Worker` pid 2242260 was live and the heavy lock was held by unittest discover pids 2291979 and 2294586. The script would also add a worktree under the main checkout `tmp/pg/`.

## Cross-lane

- `scripts/pregate.sh` still sets scratch from `git rev-parse --git-common-dir`, so a linked worktree writes `tmp/pgs` under the main checkout. That file is not owned. Do not move it into a long worktree path: `docs/ops/PREGATE.md` keeps run roots at or under 60 characters so harness2 unix sockets fit `sun_path`. OQ draft: if pregate scratch must stay inside the invoking worktree, the short-path rule needs a new design. This lane did not write that ADR.
- Cloud runner: if it copies `--unsafe-no-sandbox`, copy the gate rule too. `gate_unsandboxed` is true only when bwrap is missing and the flag is set. Do not copy a path that unsandboxes the gate while bwrap works.
- Integrate: merge `bot/mvp-review-fix2-1031` after `bot/mvp-review-fix-1031`.

## Gate

Runtime changes in `scripts/pfy_build_local.py` and `scripts/pfy_local_build_eval.py`. Needs Tester plus Reviewer at the handoff SHA. Official pregate was not run (host busy). Owned modules exercised here are green. No Feature GO.

## Next

Gate this branch. Then merge it after `bot/mvp-review-fix-1031`. No further local-runner row from the parallel plan fits these files.
