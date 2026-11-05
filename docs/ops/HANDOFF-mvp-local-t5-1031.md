# Handoff mvp-local-t5-1031

Lane goal met for the owned files. No rebase, no force push, no PR, no merge, no tag. `--local` is not the default. No edits under `scripts/` or `pfylib/`.

Exit: lane empty. t5 and t4 are recorded. The MVP plan gaps that remain belong to other lanes and touch files this lane must not edit. Wall clock still had room at 2026-10-31T23:55Z (reserve 2026-11-01T05:37Z).

Model: this lane loaded `qwen3.6:35b` for both runs (`model_was_loaded` false on both receipts). Both receipts say `unloaded` true. `ollama ps` showed no models after each wrapper, and again when this handoff was written.

## Items done

| Item | Commit | Result |
|------|--------|--------|
| Exit card and base check | `358de84` | `origin/bot/mvp-integrate-1031` is `0c3f133` |
| Review-fix present | `358de84` | `scope-commit-mismatch` is in `scripts/pfy_build_local.py` on that base. Not patched here |
| `eval/mvp-1031/rerun_local.py` | `b8b1003` | Wrapper shells `./pfy build --local` with `--review` and `--retries 2` |
| Diff check for inherited gitignore matches | `771cc1f` | A path counts only when this commit adds or changes it |
| t5 receipt and note | `771cc1f` | Runner PASS. Diff has no new gitignored path |
| t4 receipt and note | this handoff commit | TIMEOUT after 3 attempts. No commit |

## t5

Receipt: `eval/mvp-1031/local-rerun/t5-receipts-outside-repo/receipt.json`

- Runner exit 0, gate `PASS ok`, attempts 1, review on, retries 2, model `qwen3.6:35b`.
- Commit `4aa36fd34d1b9007bbf4887dcd729977aded3ee2` on the throwaway clone, not on this branch.
- Diff vs parent `bc865e84`: `tests/test_x_intake_smoke_117_118.py`, `tests/test_x_intake_smoke_119_121.py`.
- `check-ignore` on that diff is empty. Gitignored path in the commit: no.
- The first wrapper process exited 1 because a full-tree check matched three `pipelines/dogfood/local-bench-4/receipt-*.json` files. Those files are already in the parent. The note records that, and the corrected result is no.

Lock wait: acquired 2026-10-31T22:52:31Z, finished 2026-10-31T23:02:02Z. The holder before that was another lane's pregate. This lane did not signal it.

## t4

Receipt: `eval/mvp-1031/local-rerun/t4-timeout-substep/receipt.json`

- Exit code 3. Gate `TIMEOUT timeout`. Commit: none. Gitignored path in the commit: no.
- Attempts: 1 `tests-failed` (198s), 2 `tests-failed` (432s), 3 `timeout` (1207s). Wall 1838s.
- Review was on. Retries 2. Model `qwen3.6:35b`. Unloaded.
- Lock acquired 2026-10-31T23:23:51Z, finished 2026-10-31T23:54:51Z.

## Tests

`TMPDIR=tmp/scratch nice -n 19 python3 eval/mvp-1031/test_rerun_local.py`

- At `b8b1003`: 11 tests OK, no model.
- After the parent-diff fix: 12 tests OK, no model.

No `unittest discover`. No pregate.

## How it fails and how it recovers

- No task, or an unknown task: exit 2. Ollama is not called. Recovery: pass `t5-receipts-outside-repo` or, after a t5 receipt exists, `t4-timeout-substep`.
- Known task without the inherited flock: exit 2 and the wrapper text. The script does not take the lock. Recovery: the contract command below.
- t4 before a t5 receipt file exists: exit 2. The runner is not started. Recovery: record t5 first.
- Host mem under 32 GiB, ollama already holding a model, or the API down: exit 4. Nothing is spawned and nothing is unloaded. Recovery: rerun when the host is free.
- Runner binary missing: exit 1, a note, no traceback. Recovery: point `PFY_RERUN_PFY` at a real `./pfy` and rerun. The real run leaves that env unset.
- SIGTERM: the child process group this script started is signaled, then the script exits. Recovery: rerun the same command.
- A commit that adds or changes a gitignored path: exit 1 even if `./pfy` exited 0. The note lists the paths. Recovery: do not rewrite that commit. Fix the runner in the review-fix lane and rerun.
- A gitignored path already in the parent does not fail the child commit.

Contract:

```text
flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock \
  nice -n 19 python3 eval/mvp-1031/rerun_local.py t5-receipts-outside-repo
```

## Skipped

- Pregate not run: host busy. `pgrep -f 'Runner[.]Worker'` showed pid 3751002 (`Runner.Worker spawnclient`) at 2026-10-31T23:55Z.
- Plan gaps G1 through G10: other lanes own those files (`scripts/`, `pfylib/`, catalog, TODO, module docs). This lane's owned set does not include them.

## Cross-lane requests

None. t4's timeout is the local agent's result (two red gates, then the agent timeout). It is not a patch for `scripts/` or `pfylib/`. t5 did not add a gitignored path.

## Gate

Eval and test only. Gate: pregate plus Reviewer. Pregate was not run (host busy). Reviewer is the next step. Not a Feature GO. Do not merge.

## Next

Reviewer on `bot/mvp-local-t5-1031`. Leave `./pfy build` on the cloud default.
