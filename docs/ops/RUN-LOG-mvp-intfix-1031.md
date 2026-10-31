# RUN-LOG mvp-intfix-1031

Branch `bot/mvp-intfix-1031`. Base `origin/bot/mvp-integrate-1031` (`19c2710`). Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-intfix-1031`. No rebase, no force-push, no PR, no merge to main, no tag. No local model. No `--local` on a real run.

Launch: 2026-10-31T21:15:23Z. Wall cap: 2026-11-01T05:15:23Z (8 hours), which is earlier than Sunday 2026-11-01 18:00 PT / 2026-11-02T02:00Z. Stop new items by 2026-11-01T04:55:23Z so the handoff has 20 minutes. Host at launch: 32 cores, MemAvailable about 60 GiB, load about 4.4 (threshold is 64).

Overview: Unblock integration pass 2. Update `CloudBuildUnchangedTests` so bare `./pfy build --help` is the cloud card and `./pfy build -p --help` keeps the dogfood flags (plan D1). Make `log_path_for_receipt` and its test agree for a log inside the repo and outside it, including when `TMPDIR` is the worktree `tmp/`. Run one full unittest discover under the heavy lock with `TMPDIR=$PWD/tmp`. Then stop. Further work is only another failure in these same files.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria): CloudBuildUnchangedTests expects the cloud card on bare ./pfy build --help and the dogfood flags on ./pfy build -p --help. log_path_for_receipt tests pass with the log inside the repo and outside it. One flock discover with TMPDIR=$PWD/tmp records counts. Handoff pushed. No Feature GO.
1 Goal met:                  targeted modules green, then one unittest discover summary line in this log and the handoff
2 Turn cap:                  3 listed items, then only further failures inside the owned files. Stop at the first exit.
3 Budget cap:                no cloud ./pfy build, no --local, no Ollama, no spend
4 Wall clock:                2026-11-01T05:15:23Z, or 2026-11-02T02:00Z, whichever is first. Handoff buffer starts 20 minutes earlier.
5 No-progress:               same failure twice with no new information, or 3 items in a row skipped
6 Human interrupt:           user stop. Do not ask. Conservative default, one decisions line, continue.
7 Error threshold:           3 consecutive same failures, or the drop-in "same failure twice" rule, then stop
8 External event:            if origin/bot/mvp-review-fix2-1031 or a newer integrate tip already fixed an item, do not rewrite it
Loop type:                   goal
Human gate:                  no merge to main, no PR, no tag. Push only bot/mvp-intfix-1031. Merge note: after bot/mvp-review-fix2-1031.
```

Drop-in exits (checked before every item):

1. Wall cap with the 20 minute handoff buffer above.
2. Lane empty: no remaining item fits the owned files and these rules.
3. No progress: same failure twice with no new information, or 3 skipped items in a row.
4. Host pressure: MemAvailable under 16 GiB, or load over 64 for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: a failure that also fails on the pre-change base is recorded and that area is skipped. Do not stop the lane.

Named skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. This card, the drop-in exit list, and `docs/ops/HANDOFF-mvp-intfix-1031.md` are the binding.

## Phases

- exits | `docs/ops/RUN-LOG-mvp-intfix-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp-intfix-1031.md` | exit card committed and pushed before either fix | none | lead
- help-test | `CloudBuildUnchangedTests` in `tests/test_pfy_build_local.py` only | `./pfy build --help` shows the cloud card; `./pfy build -p --help` shows dogfood `--prompt-file` and `-p, --prompt`; dry-run of `-p` still prints READY | exits | lead
- log-path | `tests/test_local_bench.py`, `log_path_for_receipt` in `examples/local-bench/bench.py` | suite passes for a log inside the repo and outside it; fail/recover covers both placements | exits | lead
- suite | no extra feature edits | one `nice -n 19 flock` unittest discover with `TMPDIR=$PWD/tmp`; other failures recorded; fix only when the file is owned here | help-test and log-path | lead
- handoff | `docs/ops/HANDOFF-mvp-intfix-1031.md`, this log | SHAs, skips, evidence, fail/recover, cross-lane, gate, next step, final `state:` line, push | suite | lead

Owned files: the `CloudBuildUnchangedTests` class, `tests/test_local_bench.py`, `log_path_for_receipt` and its module (not the cloud or local runners), and this lane's docs/ops files. `mvp-review-fix2-1031` owns the rest of `tests/test_pfy_build_local.py`.

## Risks

- Shared host and the heavy lock: the full suite waits on `~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock`. Targeted tests do not take the lock. Do not signal processes this lane did not start.
- Shared file `tests/test_pfy_build_local.py`: edit only `CloudBuildUnchangedTests`. A needed edit elsewhere is a cross-lane request.
- `TMPDIR` under the worktree makes `tempfile` look in-repo. The log-path test must classify by the resolved path, not by "this came from TemporaryDirectory".
- One worktree and one branch: the lead implements both items. Spawning editors onto this checkout would race the index and the push. Project-map writes only gitignored `.project-map/`.
- Parallel lanes: stay in this worktree. Do not touch `~/DEVELOP/pfy-mentat` or other worktrees under `tmp/`.

## Item log

Format: `item | commit | tests | result`

exits | 7209ff2 | none | exit card pushed before either fix
help-test | bb00fe7 | TMPDIR=$PWD/tmp python3 -m unittest tests.test_pfy_build_local.CloudBuildUnchangedTests | 2 OK in 0.965s
log-path | this commit | TMPDIR=$PWD/tmp python3 -m unittest tests.test_local_bench | 17 OK in 1.234s; before the helper, outside path was '/proc/self/comm' != resolved '/proc/<pid>/comm'
