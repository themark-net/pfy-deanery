# Run log: mvp-dogfood3-1031

Lane: six real cloud `./pfy build` fixes on the integration tip, then the next fitting MVP gap until an exit.
Branch: `bot/mvp-dogfood3-1031`. Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-dogfood3-1031`.
Base: `origin/bot/mvp-integrate-1031` at `1dee0b91bda11ba1fcda87819423437a3f10f289`. Drop-in commit: `ab250dd`.
Launch clock: 2026-11-01T00:37:28Z (survey start of this lane). Exit card written: 2026-11-01T00:55:00Z.
Wall cap: 2026-11-01T08:37:28Z (8 hours), or 2026-11-02T02:00Z, whichever is first.
Stop new items by 2026-11-01T08:17:28Z so the handoff has 20 minutes.
Needs a local model: no. Cloud Grok only. Never `--local`. Do not run `scripts/pregate.sh` during the loop.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     6 human-accepted cloud ./pfy build fixes, each with a receipt under eval/mvp-1031/dogfood3/, a behavior or fail/recover test, a commit, and a push. Handoff table has 6 rows and the pass rate.
1 Goal met:                  lane compares each diff to the task, reruns the affected unittest, and records accept or reject. A failed build is a row, not a silent retry.
2 Turn cap:                  8 cloud builds. Stop even if a spare gap remains.
3 Budget cap:                cloud Grok only. --retries 1 (2 attempts) and --timeout 900 per grok call. No --local. No second model. No project-map Grok while another lane is inside ./pfy build.
4 Wall clock:                2026-11-01T08:37:28Z or 2026-11-02T02:00Z. Leave 20 minutes for the handoff.
5 No-progress:               the same failure twice with no new information, or 3 items in a row skipped. Survey skips before item 01 do not count.
6 Human interrupt:           user stop. Do not ask. A conservative choice goes in the decisions file.
7 Error threshold:           3 consecutive cloud failures with the same reason, then stop.
8 External event:            if origin/main or another bot branch already has the fix, skip that item. If a live lane is editing the file, skip it.
Loop type:                   goal
Human gate:                  no merge, no PR, no tag. This lane accepts or rejects each cherry-pick.
```

Named skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. This card, the drop-in exits, and `docs/ops/HANDOFF-mvp-dogfood3-1031.md` are the binding. Decision logged.

## Drop-in exits (check before every item)

1. Wall cap: 8 hours from 2026-11-01T00:37:28Z, or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z). Leave 20 minutes for the handoff.
2. Lane empty: no item left that fits this lane and these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped.
4. Host pressure: MemAvailable under 16 GiB, or load over 64 (2 x 32 cores) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: record tests that fail on the base and skip that area. Do not stop the lane.

Host at the exit card: MemAvailable about 68 GiB. Load about 3.4 on 32 cores. Not under pressure.

## Phases

Overview: Land six small smoke fixes with the integration tip's cloud `./pfy build`. One build per item, sequential, on this branch. Receipts stay in `eval/mvp-1031/dogfood3/`. Product edits land only by an accepted cherry-pick.

- prep | docs/ops/RUN-LOG-mvp-dogfood3-1031.md, docs/ops/AUTONOMOUS-DECISIONS-mvp-dogfood3-1031.md | exit card committed and pushed before a cloud build | none | general
- select | this log, task queue below | each task names the file and why it is still open | prep | general
- build | eval/mvp-1031/dogfood3/<n>-<slug>/, tmp/target-<n> | receipt, diff, command, wall, exit, attempts, review, human verdict | select | general, lead only (one branch)
- handoff | docs/ops/HANDOFF-mvp-dogfood3-1031.md | 6-row table, pass rate, final state line, pushed, not merged | build | general

These six builds share one branch, so they are one workstream. The lead runs them. No parallel implementer.

Risks:
- Review diff cap is 12000 characters. These tasks are one function. Mitigation: reject a diff that wanders into a second product file.
- A model that edits the planted test trips `tests-tampered` because the test is in the base snapshot and `--writable-test` is not passed.
- Full `unittest discover` would take the shared heavy lock. Mitigation: `--test-cmd` is one module.
- The throwaway clone is `tmp/target-<n>` inside this worktree, never Mark's checkout and never another lane's worktree.
- Secrets in receipts. Mitigation: class-only scan before commit. Never print a matched value.
- selfhost2 is inside a cloud build of `smoke_140_142.py` `tree_hash`. This lane does not edit that file.

## Task queue

Open on this tip. Not committed on another `origin/bot/mvp-*-1031` branch. Not in a live cloud build.

| n | slug | source | file | why it fits |
| --- | --- | --- | --- | --- |
| 01 | smoke128-timeout | smoke_140 already fail-closes a bad PFY_XINTAKE_TIMEOUT; smoke_128 `tmo()` still swallows it and `main` calls the entry | examples/x-intake-local/smoke_128_130.py | one file, behavior is red today |
| 02 | smoke131-timeout | same swallow; `main` has no check | examples/x-intake-local/smoke_131_133.py | one file, after 01 so it can call `timeout_problem` |
| 03 | smoke137-timeout | same swallow | examples/x-intake-local/smoke_137_139.py | one file |
| 04 | smoke137-tree-hash | copy of `tree_hash` follows symlinks and raises on an unreadable file | examples/x-intake-local/smoke_137_139.py | after 03, so the clone includes the timeout fix. Not smoke_140, which selfhost2 is building now |
| 05 | smoke103-timeout | `xintake_timeout` returns the default on a bad value and `main` does not check | examples/x-intake-local/smoke_103_105.py | one file |
| 06 | smoke106-timeout | same helper and the same `main` shape | examples/x-intake-local/smoke_106_108.py | one file |

Each build: throwaway clone under `tmp/target-<n>`, `./pfy build` with `--repo` that clone, `--base HEAD`, `--retries 1`, `--timeout 900`, a focused `--test-cmd`, and `--receipt-dir` at `eval/mvp-1031/dogfood3/<n>-<slug>/`. No `--local`. No `--writable-test`.

## Items

item | commit | tests | result
