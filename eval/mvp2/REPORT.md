# MVP-2 trial: local build vs cloud Build

Branch `bot/mvp2-trial`. Base for every arm: `997d89264495861a178713ccf7d4447ea828afc4`. Model for arm L: `qwen3.6:35b` via `./pfy build --local` (opencode, sandbox `bwrap-unshare-net`, protect-by-default). Arm C: `grok -p` with `--cwd`, `--always-approve`, and `--no-alt-screen`, then the same gate in that sandbox. One attempt per local task. Cloud retry was allowed once and was not needed. No task diff was merged onto this branch. Patches are under `eval/mvp2/patches/`.

## Result

No-go for making `./pfy build --local` the default on build-only runs.

| Arm | Gate pass | Review accept | Wall | Attempts | Timeouts | Memory blocks |
|-----|-----------|---------------|------|----------|----------|---------------|
| L | 5/6 | 4/6 | 1694.0 s | 1 each | 0 | 0 |
| C | 6/6 | 6/6 | 583.6 s | 1 each | 0 | 0 |

Cloud was faster on five tasks. `t1` tied (113.9 s local, 113.5 s cloud). Weekly Build percent was not readable. That sentence is an operator observation with no receipt field. Auth file exists and is non-empty. Six cloud sessions were present, each `turnCount` 1. `modelCalls` were 9, 5, 9, 9, 12, and 7 (51 total). Token totals are not in this report.

## Per task

| Task | Level | L gate | L review | L wall | L diff | C gate | C review | C wall | C diff |
|------|-------|--------|----------|--------|--------|--------|----------|--------|--------|
| t1 smolvm stderr first | trivial | PASS | accept | 113.9 s | 2 files, +49/-8 | PASS | accept | 113.5 s | 2 files, +50/-8 |
| t2 tree_sig 119 | trivial | PASS | accept | 196.7 s | 2 files, +60/-3 | PASS | accept | 18.7 s | 2 files, +60/-3 |
| t3 daemon stop fail | medium | PASS | accept | 463.9 s | 2 files, +91/-0 | PASS | accept | 118.6 s | 2 files, +93/-1 |
| t4 timeout substep | medium | PASS | reject | 286.7 s | 3 files, +111/-7 | PASS | accept | 173.1 s | 3 files, +109/-5 |
| t5 receipts outside repo | slightly hard | FAIL | reject | 461.4 s | 2 files, +67/-1 | PASS | accept | 118.3 s | 3 files, +83/-2 |
| t6 tree_sig three | slightly hard | PASS | accept | 171.4 s | 4 files, +107/-9 | PASS | accept | 41.4 s | 4 files, +107/-9 |

Diffs include the planted acceptance test. Gaming: none. Every canonical gate found the planted test unchanged. Scope creep: none. No arm edited a file outside its spec.

### Why a review would reject the local misses

`t4` local is green and still wrong. The overtime handler wraps the whole inner try, so a timeout on `ls`, `set`, or `settings` is labeled `new`. The gate only times out `new`. Cloud catches `new` alone and leaves other timeouts on the old `overtime` label. Both arms changed only the two allowed assertion strings.

`t5` local never sets `PFY_SMOKE_RECEIPT_DIR`. The 117 test reads a temp path, the smoke still writes the repo receipt, and the child dies with `FileNotFoundError`. Errors rose from 0 to 1. The 119 test module was not edited. Cloud sets the env var from `setUp` in both modules, reads receipts from that temp dir, and leaves the smoke scripts and the gitignore tests alone.

### Accepted diffs

`t1` both arms scan stderr for `Pulling image` first and still return a cache-only stdout line. `t2` and `t6` copy the `smoke_122_124.py` content hash, including `:dir` and `:unreadable`. `t3` both arms return 1 when daemon stop times out and the lock is gone, and they keep the step record. Cloud does that after the real-HOME check. Local returns before that check, which matches the existing live-lock return. Both are acceptable. A clean stop still passes.

## What local handles

Local handles a one-function rule change (`t1`), a copy of an in-repo algorithm into one file (`t2`) or three files (`t6`), and a single new fail return on a path the gate names (`t3`).

Local does not yet handle a timeout that must be named at one call inside a larger try (`t4`), or wiring one env var through two existing test modules (`t5`).

## What is still missing

A review step is the gap this trial measured. `t4` shows a green gate is not enough to land the diff.

A retry was not measured. Local had one attempt by decision. `t5` used 460 s of the 1200 s agent budget and stopped on a wrong fix, so a second attempt might help. This run does not show that.

A bigger context was not the limit. No local arm timed out. None reported a truncated prompt. That sentence is an operator observation with no receipt field. The agent budget was not exhausted on the failure.

A stronger local model might close `t4` and `t5`. This trial used only `qwen3.6:35b`.

## Decisions that affect the numbers

Arms were local-first, then cloud. The 21 GiB model was unloaded between local arms so the 32 GiB `MemAvailable+SwapFree` floor still held. The floor was not lowered. No foreign model was loaded. Lowest `min_available_gb` recorded during a local arm was 36.4. The local process wrapper was 60 minutes. The agent timeout stayed 1200 s. Cloud wrapper was 40 minutes. Reload time did not dominate: local wall and `agent_seconds` differ by at most 28 s.

The local tool prefixes the spec with "do not commit" and the test command. Cloud received the spec text, then this runner ran the gate. Cloud still passed more tasks.

Hermes #303 items were not used. Those prerequisites are already fixed on this base. Openqodex sub-step naming was not a task because the existing assertion and the smoke comment would have exceeded three files.

## How to read a patch

`eval/mvp2/patches/<task>-L.patch` and `<task>-C.patch` are `git diff 997d892` of the arm worktree, including the planted test. Prefer the cloud patch when both exist. Do not land the local `t4` or `t5` patches.
