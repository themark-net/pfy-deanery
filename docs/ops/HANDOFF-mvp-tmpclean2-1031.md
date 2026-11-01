# Handoff mvp-tmpclean2-1031

Status: stopped. Exit: lane empty. Branch `bot/mvp-tmpclean2-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-tmpclean2-1031`. Base `origin/main` `c0d38af` plus `fb759e9`. Fast-forward, behind 0. No merge, no PR, no tags.

Pregate not run by this lane. The drop-in says the operator runs `scripts/pregate.sh`. At 2026-10-31T23:50:03Z `Runner.Worker` was alive (pid 3751002). At 2026-11-01T00:03:02Z the runner was idle, and a pregate of `0afea54` (`bot/backlog-catalog-1030`) already held `~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock`. At 2026-11-01T00:11:04Z that same pregate still holds the lock (flock pid 3755278).

## Done

| Item | SHA | Tests | Gate |
|------|-----|-------|------|
| FU16 separate-process `/tmp/pfy-*` immunity | `c875e7e` | `tests.test_pfylib_tmp_cleanup` 3 OK in 61.781s | pregate plus Reviewer |
| FU1 ripgrep install must be a real run step | `8203c43` | `tests.test_workflow_image_pin` 20 OK in 13.612s | pregate plus Reviewer |
| FU3 `version_of` without bwrap | `5b32274` | `tests.test_x_intake_smoke_149` 29 OK in 2.792s | pregate plus Reviewer |
| FU4 yaml skip uses PATH `python3` | `2abd8c9` | `tests.test_workflow_image_pin` 21 OK in 6.800s | pregate plus Reviewer |
| FU5 image-pin unittest does not exec pregate | `d5422c9` | `tests.test_workflow_image_pin` 21 OK in 0.561s | pregate plus Reviewer |
| FU6 OpenCode reuse, drift, env | `1be6160` | `tests.test_attach` 28 OK in 0.065s | pregate plus Reviewer |
| FU7 opencontext how names `pfylib/attach.py` | `6fe37a2` | `tests.test_registry` and `tests.test_toolsets` 36 OK in 0.072s | pregate plus Reviewer |
| FU8 duplicate YAML keys fail the image-pin lint | `617ec78` | `tests.test_workflow_image_pin` 22 OK in 0.583s | pregate plus Reviewer |
| FU9 T-0124 leaves the active TODO table | `894382e` | docs only | pregate plus Reviewer |
| FU11 `run()` re-checks and `dir_usable` | `4980d94` | `tests.test_x_intake_smoke_149` 32 OK in 2.917s | pregate plus Reviewer |
| FU13 proc-mount probe does not start MemPalace | `7061d3c` | that one test, 1 OK in 0.033s | pregate plus Reviewer |
| FU14 harness2 dry-run off the live home hash | `731f0bb` | `DryRunTests` 1 OK in 0.026s, five repeats OK | pregate plus Reviewer |
| FU15 c0d38af pregate rerun note | `9afffa0` | docs only | pregate plus Reviewer |

Stamp commits sit on top of those SHAs in the run log. They do not change the behavior.

## Skipped

- Follow-up 2 (ubuntu rg path). `eval-structural.yml` already installs ripgrep when `command -v rg` misses, then runs `rg --version`. Hardcoding an ubuntu path would be a guess. This lane does not run the ubuntu-24.04 runner.
- Follow-up 10 (MemPalace staging). Staging writes a shared tree and warms an embedding model. This lane must not write outside the worktree and must not run a local model.
- fix2 already landed these, so they were not redone: F1 probe flags `b5754cb`, F2 tmpfs-only twin `f6a74ea`, P2 failing lint `cd4c116`, G1 root-length guard `a2a9317`.

## How it fails and how it recovers

- FU16. A glob of `/tmp/pfy-*` fails when another process creates `/tmp/pfy-hr-*` during the run. A private TMPDIR leak and a host `/tmp` mkdir leak still fail, and the marker is removed. Recovery: keep the private child TMPDIR and the sitecustomize hook. Scratch stays under this repo's `tmp/`.
- FU1. A comment, an echo, or a commented apt line does not pass. An install without `rg --version` or `command -v rg` fails with "does not run rg". Recovery: put `apt-get` or `apt install` of ripgrep and an rg probe in a run step of `eval-structural.yml`.
- FU3. A banner that is not a dotted triple, or a version other than 3.12.0, exits 2 before init. `run()` is stubbed, so bwrap is not required. Recovery: the banner must parse as the pin. The real bwrap cases still cover the sandboxed path.
- FU4. A PATH `python3` that exits 1 on `import yaml` makes the probe false even when `sys.executable` can import yaml. Recovery: put a yaml-capable `python3` first on PATH.
- FU5. Commenting out the helper call in `check_lint` fails the live-shell assert. A new `pregate-runs` directory fails the snapshot. Recovery: keep the helper invocation uncommented. Do not exec `scripts/pregate.sh` from this unittest.
- FU6. Dead terminal: if the session file or `opencode-attach-base` is left in place, the pre-created files remain. Reuse: a spawn, or a return that skips prove, fails. Reuse prove failure: a spawn or a leftover file fails. No engine: a spawn, a leftover session file, a different error, or `usable` True fails. Drift: if the old session or old base still exists at spawn, the test fails. Mode: if `PFY_ATTACH_MODE` is not `orchestration`, the test fails. OpenContext: if `OPENCONTEXT_BIN` is absent while `oc` is on PATH, the test fails. Recovery: clear both files on the failing returns, call prove on a matching live pid and do not spawn, clear before a drifted spawn and pin the child base to the probed URL, read `attach-mode`, and call OpenContext `apply_child_env` before spawn.
- FU7. A how string that names `_apply_opencontext_env` must resolve to a file that defines it. The old opencode cell named `pfy_enterable_162_b`, which is a shim. Recovery: name `pfylib/attach.py`. The grok cell was the same lie (`attach_usable_202`) and now names the same file.
- FU8. A job whose first `runs-on` is `ubuntu-latest` and whose last is `ubuntu-24.04` fails. PyYAML's default loader would keep the last value and the file would look pinned. Recovery: delete the repeated key.
- FU9. Docs only. The done T-0124 row now sits in the Done table next to T-0121.
- FU11. `run()` with a missing proc path must raise the mount reason before `subprocess.run`. A `which("bwrap")` miss must raise the bwrap reason before `subprocess.run`. `dir_usable` on a mode 644 file must be false. Recovery: keep both raises, and return false unless the path is a directory.
- FU13. If MemPalace starts after the proc-mount probe fails, `checks` is not empty or the escape file exists. Recovery: return at the failed probe, before `run()`.
- FU14. Hashing the live `~/.cache/uv` (about 21 GiB) and `~/.npm` fails on nimo when those trees change during the walk, even though `--dry-run` writes nothing. A parent `BASH_ENV` that prints `huggingface` fails the forbidden-word assert if it is not dropped. Recovery: use the stub private HOME, drop `BASH_ENV`, `ENV`, and `CDPATH`, and put stdout and stderr in every assertion.
- FU15. Docs only. The old sentence promised a pregate re-run. The note now records the c0d38af failure and the successful rerun.

## Cross-lane

No file was skipped because another lane owned it. `docs/ops/HANDOFF-pfy-followups-1030.md` had no unique commit past `origin/main` on another `bot/mvp-*` branch. T-0127 is still a done row in the active TODO table. This lane moved only T-0124, which is the row the review named. Other lanes also commit `docs/TODO.md`.

## Gate

Pregate plus Reviewer. The behavior changes are the image-pin loader, the catalog how strings, and tests. `pfylib/attach.py`, `examples/x-intake-local/smoke_149.py`, and `examples/harness2-local/stage.sh` were not edited.

Pregate not run: host busy.

## Recheck 2026-10-31T23:50:03Z

origin/main is still `c0d38af`. This branch is a fast-forward, behind 0, tip `89f0564` before this note. MemAvailable was about 35.8 GiB. Load was 7.5 on 32 cores. The project map default is to wait and not start another lane's files. Active TODO rows still need a local model, docker, hardware, a catalog lane, or a named scorer. T-0127 stays in the active table.

## Recheck 2026-11-01T00:03:02Z

origin/main is still `c0d38af`. This branch is a fast-forward, behind 0, tip `53f6d7d` before this note. MemAvailable was about 72.4 GiB. Load was about 3.1 on 32 cores. `Runner.Worker` is not running. Tests were not re-run: the tree is the same as `53f6d7d`, and the heavy lock is already held.

This lane does not run `scripts/pregate.sh`. The drop-in assigns that to the operator. A pregate of `0afea54` (`bot/backlog-catalog-1030`) already holds the heavy lock, and pregate writes its run folder under the main repo `tmp/`. Starting another one from this worktree would contend with that run.

No new gap fits this lane. Active TODO rows still need a local model, docker, hardware, a catalog lane, or a named scorer, or they are shelved. T-0127 stays in the active table. Many other `bot/mvp-*` branches also commit `docs/TODO.md`.

## Recheck 2026-11-01T00:11:04Z

origin/main is still `c0d38af`. This branch matches `origin/bot/mvp-tmpclean2-1031` at `2cdd792`, ahead 31, behind 0. MemAvailable was about 71.5 GiB. Load was 3.09 on 32 cores. `Runner.Worker` is not running. Tests were not re-run: the tree is the same as `2cdd792`.

The pregate of `0afea54` is still inside `flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock` (pid 3755278, elapsed about 48 minutes). A `unittest discover` also waits on that lock. This lane does not run `scripts/pregate.sh`.

No new gap fits this lane. The active rows are unchanged: voice is shelved, local-model and hardware rows stay out, catalog and cage rows belong to other lanes, and T-0127 stays in the active table.

## Next step

Operator runs pregate, then Reviewer, on this branch. Do not merge from this lane.
