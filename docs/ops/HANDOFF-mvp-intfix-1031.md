# Handoff mvp-intfix-1031

Branch `bot/mvp-intfix-1031`. Base `origin/bot/mvp-integrate-1031` (`19c27109fc8d273c79fc4d1025551468d1f9e14a`). Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-intfix-1031`. No merge, no PR, no tag, no force-push. No Feature GO. Catalog HOLD unchanged. No local model. No `--local`.

Exit: lane empty. Launch 2026-10-31T21:15:23Z. Finish 2026-10-31T21:52:00Z. Wall cap was 2026-11-01T05:15:23Z.

Merge this branch after `bot/mvp-review-fix2-1031`. That lane owns the rest of `tests/test_pfy_build_local.py`. This lane edited only `CloudBuildUnchangedTests` in that file.

## Done

| Item | SHA | Result |
|---|---|---|
| Exit card | `7209ff2b78ab257d697a1dcf62263e4462fc16b7` | Pushed before either fix |
| Help contract (plan D1) | `bb00fe7bf10480943636a8ade455939e0411d4cb` | `CloudBuildUnchangedTests` 2 OK in 0.965s |
| Log path contract | `92853178e347aa99b6923d6ea9429414aaf57db2` | `tests.test_local_bench` 17 OK in 1.234s |

Bare `./pfy build --help` is the cloud card (`Daily cloud build`, `./pfy build "<task>"`, pointers at `-p` and `--local`). `./pfy build -p --help` still lists `--prompt-file` and `-p, --prompt`. `./pfy build -p x --dry-run` still prints READY and leaves no new names under `pipelines/dogfood/build` or `pipelines/dogfood/build-cloud`.

`log_path_for_receipt` in `examples/local-bench/bench.py` stores a repo-relative path when the resolved log is inside the repo, and the absolute resolved path when it is not. The only consumer is `rec["log"]` in `bench_one`. Entry 090: `relative_to` raising turned a good run into DROP.

## Suite

```text
TMPDIR=$PWD/tmp nice -n 19 flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock python3 -m unittest discover -s tests -t .
```

Lock acquired 2026-10-31T21:38:19Z. Ran 1049 tests in 670.488s. FAILED (failures=1, skipped=16). Log: `tmp/suite-intfix/unittest.log` (gitignored).

The integrate discover was 1048 tests, 2 failures, 16 skipped. Both of those failures are gone. This run has one added test (`test_log_path_receipt_inside_and_outside_repo`) and one different failure.

### Failure recorded, not fixed

`tests.test_pfylib_tmp_cleanup.PfylibTmpCleanupTests.test_module_run_leaves_no_new_tmp_dirs`

During the discover the new `/tmp` names were seven `pfy-xintake-*-receipts-*` directories. A targeted re-run (`TMPDIR=$PWD/tmp`, 51.143s) failed with a different name, `/tmp/pfy-hr-2710251`, which was gone afterward. That prefix is the `tempfile.TemporaryDirectory(prefix="pfy-hr-")` in `examples/x-intake-local/smoke_122_124.py`. The cleanup test scans host `/tmp` while other processes on this host create the same prefixes. The integrate discover did not fail this test. Not an owned file.

## How it fails and how we recover

- Help: if bare `./pfy build --help` lists `--prompt-file` or `-p, --prompt`, the daily cloud card is hidden. If `./pfy build -p --help` contains `Daily cloud build` and drops those flags, dogfood help is gone. Recovery is the split in `CloudBuildUnchangedTests`: cloud card on bare help, dogfood flags on `-p --help`, dry-run still READY, receipt directory names unchanged.
- Log path: an in-repo temp log stored absolute bakes the machine prefix into `rec["log"]`. An outside path that still contains `..`, or a symlink that is not resolved, is not the path a reader can open after `resolve`. The old `relative_to` raise became DROP. Recovery: inside the repo, `root / stored` opens the log bytes. Outside, the stored string equals `Path.resolve()`, has no `..` part, and opens the same file. Both placements are in `test_log_path_receipt_inside_and_outside_repo`. `test_relative_outdir_log_path_safe` classifies `TemporaryDirectory` by resolved location, so `TMPDIR` inside the worktree and `TMPDIR` outside it both pass.
- Tmp cleanup: not recovered here. See the cross-lane request.

## Cross-lane requests

- `tests/test_pfylib_tmp_cleanup.py` and the x-intake smokes that create `pfy-xintake-*` and `pfy-hr-*` under `/tmp`. The locked discover and one targeted re-run both failed that test, with different paths. Do not treat it as a regression from `bb00fe7` or `9285317`. Integrate's discover did not list it.
- Merge `bot/mvp-intfix-1031` after `bot/mvp-review-fix2-1031`. Overlap is only `CloudBuildUnchangedTests` in `tests/test_pfy_build_local.py`.

## Gate

Runtime change: `log_path_for_receipt` in `examples/local-bench/bench.py`. Gate: Tester plus Reviewer.

The help change is test-only. Pregate not run: host busy (`Runner.Worker` was running). Do not treat this handoff as a Feature GO.

## Next

Integrator: merge this branch after `bot/mvp-review-fix2-1031`, then re-run the locked discover. The owned failures from integration pass 1 are fixed. The `/tmp` cleanup failure belongs to the owner of `tests/test_pfylib_tmp_cleanup.py`.

Decisions: 4 lines in `docs/ops/AUTONOMOUS-DECISIONS-mvp-intfix-1031.md`. Run log: `docs/ops/RUN-LOG-mvp-intfix-1031.md`.
