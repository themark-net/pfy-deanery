# Handoff: build review (2026-11-06)

Per-file cloud review, the short build worktree, and the real `./pfy build` trial on this lane. The lane commits are on main. This note does not change those commands.

Prior headless note: [HANDOFF-headless-1105.md](HANDOFF-headless-1105.md).

## What landed

This lane, both on main. This branch (`bot/build-review-1106`) is based on `72bec83`.

- `d6729c8be19815b11841255160fb868eaba03a60` (`d6729c8`) Review cloud builds one file at a time. Each file is reviewed with the task, the gate tail, and a change-impact map. Any reject, or a review that stops before the last file, rejects the build. A file over the per-file cap (`PFY_REVIEW_FILE_CAP` or `--review-file-cap`, flag wins, default 12000) fails as `review-file-too-large` with `phase` `precheck` before the post-change gate. The map prefers codebase-memory-mcp, then Tree-sitter Analyzer, then git grep. The receipt records `impact.source`. A missing impact tool does not fail the build. After the secret scrub, the gate drops `GIT_CONFIG_COUNT`, `GIT_CONFIG_KEY_*`, and `GIT_CONFIG_VALUE_*` when the names match exactly.
- `72bec83c4f6ab5c4e2495df99d179ed7972325be` (`72bec83`) Put cloud build worktrees on a short path and allow ordinary test edits. The directory is mode 0700, named `pfyb-<stamp>-<pid>`, and it is removed when the run finishes unless `--keep-worktree`. `PFY_BUILD_WORKTREE_ROOT`, when set, is the parent. Otherwise the first candidate that is writable, outside `/tmp` and `/run`, and whose harness2 socket is at most 107 bytes wins: `$XDG_RUNTIME_DIR`, then `/var/tmp`, then `~/.cache`. If none of those pass, the path is still `/var/tmp` with that name. Ordinary files under `tests/` may change. Gate and eval files still fail `tests-tampered` unless `--writable-test` names them. Deleting a base test is still `tests-tampered`.

When this note was written, `origin/main` was `83d204bede34634cb719e4600127e43c52052b52`, two commits after `72bec83`. This branch does not contain them. This note does not merge them.

- `1d8929e4960b00ea72e947173c327bac317d7ea6` (`1d8929e`) Add `./pfy install` PATH launchers for mentat and pfy. Not this lane.
- `83d204bede34634cb719e4600127e43c52052b52` (`83d204b`) Drop inherited git config as a set in the cloud gate, including `GIT_CONFIG_PARAMETERS`, and match the family case-insensitively before the secret scrub. Not this lane.

Operator card: [ops/pfy-build-daily.md](ops/pfy-build-daily.md). Module map: [modules/pfy-build.md](modules/pfy-build.md).

## Trial

Real `./pfy build` on 2026-11-06. Sources, read in this worktree and not committed (`tmp/` is gitignored): `tmp/trial/receipt.json` (schema `pfy-cloud-build/1`) and `tmp/trial/trial.meta`.

| Field | Value |
|-------|--------|
| status | `TIMEOUT` |
| reason | `timeout` |
| exit | receipt `exit_code` 3; trial.meta `exit=3` |
| wall | receipt `wall_seconds` 10802.404; trial.meta `wall_s=10803` |
| commit | null |
| branch | null |
| base | `origin/main` |
| pushed | false |
| worktree_removed | false |
| impact.source | `git-grep` |
| finished_at | `2026-11-06T16:12:12Z` |

Stdout ended `FAIL: timeout` and `TIMEOUT timeout branch=none`. Recovery on the receipt: the gate timed out; rerun with a longer `--timeout`, then rerun the same `./pfy build`.

The task was a docs-only Review section in `docs/ops/pfy-build-daily.md` (per-file review, a change-impact map, `PFY_REVIEW_FILE_CAP`, ordinary tests writable by default). That section was not committed.

Attempts:

1. `FAIL` `commit-recheck-failed`. Review verdict `accept`. The agent added the Review section. The recheck gate on the fresh extract failed, so no branch was kept. The extract is a new repo with one commit message `recheck`. It is not a shallow clone. The attempt row stores the agent text and the review verdict, not the recheck gate tail, so the receipt does not name the unittest that failed. A check that needs older commits has no parents to read in that repo. The receipt does not show which check failed.
2. `PASS-REJECTED` `review-rejected`. Review verdict `reject`. The diff includes the Review section and also edits `tests/test_docs_hygiene.py`, `tests/test_dogfood2_1031_report.py`, and `tests/test_handoff_headless_1105.py` so those checks skip a one-commit `recheck` tree. Review rejected the test edits. They drop checks.
3. `TIMEOUT` `timeout`. The post-change gate aborted (`exit` 124, tail `gate timeout`). The before-gate had passed (`exit` 0, 1565 tests, 18 skipped, 1259.529 s).

Phase seconds on the receipt: agent 3274.824, gate 7526.434, review 145.285. Attempt 3 died in the post-change gate (`gate.after` `aborted` `timeout`, exit 124). The impact map and the review run only after both post-change gates pass. Review then overlaps the recheck gate. Do not add the phase seconds on top of `wall_seconds`.

The command that produced this receipt passed `--timeout 3600` and `--keep-worktree`. The receipt does not store those flags. `--timeout` is the seconds for one grok call (default 1200) and the same cap is passed to the gate. The run budget is `--timeout` times the attempt count (default 3). 3600 times 3 is 10800 seconds. `wall_seconds` is 10802.404, so this run spent that budget and then stopped. The default budget is 1200 times 3 (3600 seconds). Nothing was pushed. `worktree_removed` is false because the trial passed `--keep-worktree`.

## Catalog tools

`change_impact_map` in `scripts/pfy_build_cloud.py` tries three sources. The receipt field is `impact.source`. A missing or empty tool does not fail the build.

| Order | Source id | What it is |
|-------|-----------|------------|
| 1 | `codebase-memory-mcp` | Catalog row in [TOOLS.md](../TOOLS.md) and `data/tools.json` (stage I2). Callers and callees of changed `def` / `class` names, via `list_projects` and `trace_path`. Used only when that worktree is one of the listed projects. |
| 2 | `tree-sitter-analyzer` | Tree-sitter Analyzer, catalog entry 121 ([sources/entries/121-tree-sitter-analyzer.md](../sources/entries/121-tree-sitter-analyzer.md)), `--change-impact`. Not a TOOLS.md row and not a `data/tools.json` row. |
| 3 | `git-grep` | Fallback. `git grep` of the changed symbol names. |

This trial recorded `git-grep`. The runner assigns `impact.source` after that attempt's commit succeeds and before the review calls. Attempts 1 and 2 reached that assignment. Attempt 3 died in the post-change gate before it, so the receipt value is the one attempt 2 stored. Attempt 2's diff adds `def` lines, so the map had symbol names to look up. codebase-memory-mcp is on `PATH` on this host. The CLI contributes only when `list_projects` names that worktree. This session's MCP index (same catalog tool, separate entry point) lists `tmp-cm-smoke` only, not the trial worktree. `tree-sitter-analyzer` is not on `PATH`, and `~/DEVELOP/pfy-mentat/tmp/tree-sitter-analyzer/.venv/bin/tree-sitter-analyzer` is absent. The fallback ran.

## Commands a bot runs

Launch, status, and stop are unchanged from [HANDOFF-headless-1105.md](HANDOFF-headless-1105.md). Set `PFY_STATE_DIR` when the bot must not share the operator state.

```bash
./pfy launch --headless
./pfy launch status
./pfy launch stop
./pfy build "<task>"
```

`./pfy build "<task>"` is the daily cloud build: a short worktree, cloud Grok, the gate, per-file review, and a commit on `cloud/<slug>-<stamp>` when the run PASSes. Nothing is pushed. There is no `--headless` flag on `build`.

Cap. Default 12000 characters of one file's diff. The flag wins when both are set. A file over the cap is `review-file-too-large` with `phase` `precheck`. The post-change gate does not start.

```bash
./pfy build "<task>" --review-file-cap 12000
PFY_REVIEW_FILE_CAP=12000 ./pfy build "<task>"
```

Ordinary files under `tests/` may change with no extra flag. A protected gate or eval path still needs the flag once per path:

```bash
./pfy build "<task>" --writable-test PATH
```

Protected paths are the pregate gate-hash basenames (`conftest.py`, `pytest.ini`, `tox.ini`, `setup.cfg`, `pyproject.toml`, `sitecustomize.py`, `usercustomize.py`, `.gitignore`, `.gitattributes`, anywhere in the tree), plus `examples/eval-harness/`, `.github/workflows/`, `scripts/pregate.sh`, `scripts/pfy`, and `scripts/pfy_build_cloud.py`.

A longer run passes a larger `--timeout` (seconds, must be greater than 0). The default is 1200. Exit 3 when the budget fires. Receipt `status` `TIMEOUT`, `reason` `timeout`, `commit` null, `branch` null.

```bash
./pfy build "<task>" --timeout SEC
```

`./pfy build --help` is the flag list. Its `--timeout` line says "seconds for one grok call". The same number also bounds each gate, and the run budget is that number times the attempt count. The help line does not say that.

## Still open

- The 2026-11-06 trial is `TIMEOUT`: `reason` `timeout`, exit 3, `commit` null, `branch` null, `wall_seconds` 10802.404 (trial.meta `wall_s=10803`). The trial passed `--timeout 3600`. The next run needs a `--timeout` greater than 3600. The Review section was not committed. Rerun `./pfy build`, docs only. Do not edit the history checks so a one-commit `recheck` extract skips them. Review rejected that.
- `worktree_removed` is false because the trial passed `--keep-worktree`. `/var/tmp/pfyb-20261106T131210210179Z-545982` was still on disk when this note was written. This note does not remove it.
- The trial impact source is `git-grep`. codebase-memory-mcp is wired and installed, and it did not supply this map. `tree-sitter-analyzer` is wired and the binary is absent on this host.
- This branch does not contain `1d8929e` or `83d204b`. Those commits are on `origin/main`. This note does not merge them.
- Unchanged from the headless note: `./pfy launch status` and `./pfy launch stop` do not cover a GUI terminal started without `--headless`. Stop can send SIGKILL to a pid number reused after the start-time check. The Tauri operator window is still not built on nimo. Issues #305 and #309 are not blockers for these commands.
