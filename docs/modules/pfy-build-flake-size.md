# Module: pfy build --local flake gate and size caps

**Architecture layer:** Local build runner, opt-in side of `./pfy` ([ARCHITECTURE.md](../ARCHITECTURE.md) layout map, simple launch). Inference stays [ADR-0014](../adr/0014-pluggable-local-inference-spine.md).
**Code:** `pfylib/build_flake.py`, `pfylib/build_size.py`, hook in `scripts/pfy_build_local.py`, opt-in hook in `scripts/pfy_build_cloud.py`
**Related ADR / Decisions:** Decision recorded in this file. No new ADR number.

Cloud `./pfy build` is a different runner. See [pfy-build.md](pfy-build.md). Cost confirmation, packed review quotes, and `--yes` / `--max-cost` live in that cloud module doc, not here. This page is the local flake gate, the cloud opt-in that reuses the same helper, and the size presets. The local receipt still records `estimate.flake_runs` and `estimate.review_prompts` so the $0 banner names those extras. The cloud dollar quote does not add clean-clone runs.

## Operator

### What it does

After the in-wrap gate passes, `./pfy build --local` copies the result tree, including uncommitted edits and any state file the gate wrote, and runs the gate again. Each extra run gets a new `HOME` and does not see parent tokens. The default is 2 extra runs. Any failure sets status `FLAKY`, writes no commit, and does not retry. `--flake-runs 0` skips the extra runs.

The same pass also scans test files for a literal non-zero `bind` or server address port, and for `listen` of a literal port at least 1024. Hits are a warning on the receipt. They do not fail the build. Port 0 is an ephemeral bind and is not listed. A small `listen` argument is a backlog, not a port.

`--size small` is the default cap: 40 changed files and 4000 added plus removed lines. `--size product` raises that to 120 files and 12000 lines. A task line `size: small` or `size: product` is used when the flag is omitted. An explicit `--max-files` or `--max-lines` wins for that dimension.

### How to run

```bash
./pfy build --local "<task>"
./pfy build --local --flake-runs 0 "<task>"
./pfy build --local --size product "<task>"
PFY_BUILD_FLAKE_RUNS=0 ./pfy build --local "<task>"
```

A task file can carry the preset:

```text
size: product
files: src/part_*.py
```

### Failure modes

| Symptom | Likely cause | Recovery |
|---------|--------------|----------|
| Status `FLAKY`, reason `flaky`, exit 1, no branch | The in-wrap gate passed and a clean-clone run failed | Make the test pass from a clean tree with a fresh `HOME`. The receipt field `flake.results` has each run's exit and tail. `--flake-runs 0` skips the re-runs. |
| Stderr names `--max-lines`, reason `review-diff-over-line-cap` | The diff is over the line cap. Nothing is reviewed or committed. | Pass `--max-lines`, or `--size product` when the message offers it and the diff fits that preset. |
| Status `PASS-REJECTED`, reason text names `--max-files` | The file count is over the file cap. The gate was green. | Pass `--max-files`, or `--size product` when the reason offers it. This stays a review rejection, not `FLAKY`. |
| Receipt `fixed_ports` lists a port | A test binds or listens on a literal port | Bind port 0, or read the port from the environment. The build can still `PASS`. |

### Cloud opt-in

`./pfy build` (no `--local`) does not run this gate unless you pass `--flake-runs`. Omitted, the daily path still overlaps a same-tree second gate with the post-change gate and records reason `tests-flaky`. The phase clock still runs four gates: before, after, that second gate, and the commit recheck. `PFY_BUILD_FLAKE_RUNS` is not read on the cloud route. That variable is the local default of 2. Reading it here would change existing cloud receipts.

```bash
./pfy build --flake-runs 2 "<task>"
./pfy build --flake-runs 0 "<task>"
```

`--flake-runs N` with N greater than 0 replaces the same-tree second gate. After the post-change gate passes, the runner exports the result tree, including a state file the gate wrote, and re-runs the gate N times. Each run gets a new `HOME` and does not see parent tokens. Any failure sets status `FLAKY`, reason `flaky`, exit 1, writes no commit, and does not retry. The receipt field `flake.results` has one row per run (`run`, `exit`, `ok`, `tail`, `stop`).

`--flake-runs 0` skips the clean clones and the same-tree second gate. The receipt is `flake.skipped` true and `results` empty. A gate that passes once and would fail on the next read of its own state file can still `PASS`. The commit recheck still runs. It extracts the commit, so it does not see a state file that was never committed.

The dollar quote stays the same. These re-runs are tests, not extra model calls. The wall line is not increased either. `flake` on the receipt is the record. Cloud does not scan `fixed_ports`. That warning stays on `--local`.

| Symptom | Likely cause | Recovery |
|---------|--------------|----------|
| Status `FLAKY`, reason `flaky`, exit 1, no branch | `--flake-runs` was set, the post-change gate passed, and a clean-clone run failed | Make the test pass from a clean tree with a fresh `HOME`. Read `flake.results`. Pass `--flake-runs 0` to skip the re-runs, then rerun `./pfy build`. Nothing was committed. This is not retried and it is not reason `tests-flaky`. |
| Reason `tests-flaky` | The flag was omitted. The same-tree second gate failed. | Rerun `./pfy build`. Retries still apply. Pass `--flake-runs N` only when you want the clean-clone verdict instead. |

## Configuration / variables

| Name | Where | Purpose |
|------|-------|---------|
| `--flake-runs N` | CLI, local and cloud | Extra clean-clone runs after a green gate. `0` skips. On `--local`, omitted means 2. On cloud, omitted means the flag is off: the same-tree second gate stays, and the receipt has no `flake` field. |
| `PFY_BUILD_FLAKE_RUNS` | environment, local only | Used when `--local` omits `--flake-runs`. Default 2 (`DEFAULT_FLAKE_RUNS` in `pfylib/build_flake.py`). A non-integer or a negative value is usage exit 2. The cloud route does not read this variable. |
| `--size small\|product` | CLI | Cap preset. The flag wins over a task line. |
| `size: small` or `size: product` | task text, one whole line | Preset when `--size` is omitted. First match wins. |
| `--max-files`, `--max-lines` | CLI | Override one dimension. They win over the preset. |
| small caps | `pfylib/build_size.py` `SMALL_MAX_FILES` 40, `SMALL_MAX_LINES` 4000 | Default. Same numbers the help text names. |
| product caps | `PRODUCT_MAX_FILES` 120, `PRODUCT_MAX_LINES` 12000 | Opt-in. |
| `flake` | receipt `pfy-local-build/1`, and `pfy-cloud-build/1` when `--flake-runs` is passed | `{runs, skipped, results: [{run, exit, ok, tail, stop}]}`. Omitted when the run stopped before the flake step. Omitted on cloud when the flag is omitted. |
| `fixed_ports` | receipt | `[{path, line, port, call}]`. Empty when nothing matched. |
| `review.size` | receipt | `small` or `product`. |
| `warnings` | receipt | Includes `fixed listen port <port> in <path>:<line> (<call>)` for each hit. |

The clean-clone environment keeps `PATH`, sets `HOME` and `TMPDIR` under the clone, sets `LANG` (or `C.UTF-8`), `PYTHONDONTWRITEBYTECODE`, and the `XDG_*` dirs under that `HOME`. `LC_ALL` is copied only when the parent set it. Tokens are not copied.

## Agent

### Entry points

- `resolve_flake_runs`, `fresh_env`, `export_result_tree`, `run_clean_clones`, `flake_verdict`, `scan_fixed_ports`, `port_warning_lines` in `pfylib/build_flake.py`
- `resolve_caps`, `task_size`, `file_cap_reason`, `line_cap_message` in `pfylib/build_size.py`
- `build_local` calls `_run_flake_clones` after the in-wrap gate and the tamper check, and before review. `_apply_review_flags` stores the preset and the flake count.

### Data shapes

- Flake row: `run` (int), `exit` (int or null), `ok` (bool), `tail` (last lines, redacted), `stop` (`""`, `timeout`, `interrupted`, or `mem-edge`).
- `flake_verdict`: the first stop in `timeout`, `interrupted`, `mem-edge`, else `flaky` when any row is not ok, else `ok`.
- Port hit: `path` relative to the result tree, `line`, `port`, `call` (`bind`, `listen`, or a server class name).

### Callers / callees

- Caller: `scripts/pfy_build_local.py`. `scripts/pfy` execs that file when argv contains `--local`.
- Caller: `scripts/pfy_build_cloud.py` `_run_clean_flake`, only when `--flake-runs` is passed. It calls `run_clean_clones` and `flake_verdict`. The cloud gate runs in the export with that fresh env. A nested git dir keeps `git` from walking up to the caller.
- Callees: `run_tests` on the local side (same bwrap profile as the in-wrap gate) and `judge_tests` against `tests_before`. Cloud calls its own `gate` method.
- Not a caller unless the flag is set: the daily cloud path. Omitted, it still re-runs in the same tree and records reason `tests-flaky`. Its phase clock still expects four gate runs.

### Invariants

- `FLAKY` is exit 1, no commit, no branch, no agent retry. Salvage mode does not rewrite it to `TIMEOUT`. The cloud route uses the same rule: status `FLAKY`, reason `flaky`, no retry.
- `--flake-runs 0` does not run the old same-tree second gate, on local and on cloud. A gate that passes once and would fail on the next read of its own state file can still `PASS`.
- Cloud with the flag omitted does not write `flake` and does not change the four-gate clock.
- Each extra run is a new export of the original result tree, not a copy of the previous export.
- The export skips `.git`, `tmp`, caches, and `*.pyc`, so the clone does not share the live git dir.
- The state file the gate writes stays out of the commit when it was created after the diff snapshot. The commit recheck extracts the commit, so it does not see that file.
- File overage stays `PASS-REJECTED` / `review-rejected`. Line overage stays `FAIL` / `review-diff-over-line-cap` and is not retried.
- Size and tamper recovery both name the flag, then the rerun line: `--max-files` / `--max-lines` / `--size product` for caps, `--writable-test <path>` for a protected file.
- The line-cap message names `--max-lines`. It also names `--size product` only when the line cap was not explicit and both dimensions fit the product preset.
- The file-cap reason names `--max-files`. It also names `--size product` only when the file cap was not explicit and the file count fits the product preset.
- Port 0 is omitted. `listen` below 1024 is omitted.
- Small caps stay 40 and 4000.

### Extension points

- Add a preset in `PRESETS` inside `pfylib/build_size.py` and allow the name on `--size` and on the task-line regex.
- Add a server class name to `_SERVERS` in `pfylib/build_flake.py` when a new stdlib constructor takes an address tuple.

### Do not

- Make `--flake-runs` the cloud default, or read `PFY_BUILD_FLAKE_RUNS` on the cloud route. Both would change the four-gate clock and the `tests-flaky` contract.
- Treat port 0 as a fixed port, or fail the build on `fixed_ports`.
- Suggest `--size product` when an explicit `--max-files` or `--max-lines` set the cap that was exceeded.
- Commit, push, or retry a `FLAKY` round.
- Raise the small default above 40 files or 4000 lines. Help text and the five-file wrapfix path depend on those numbers.

## Decision

The leasegrid replay saw `./pfy build --local` pass its sandboxed gate while a clean clone of the suite was flaky (a test bound port 15439, and the environment leaked). Evaluators also had to raise wrap caps by hand for a product-sized round. This lane re-runs the local gate from a clean export with a fresh `HOME`, and adds an opt-in product cap.

Rejected: changing the small default. The help text locks "40 changed files" and "4000 added plus removed lines", and a five-file diff must pass with no size flag. The 20-file behavior check is over the line cap (4400 lines), which `--size product` allows.

Rejected for the local lane: making cloud `FLAKY` the default in the same change. Cloud kept a same-tree second gate, reason `tests-flaky`, and a four-run phase clock while other lanes were editing that file.

Later decision, cloud opt-in: the clean-clone gate is available on `./pfy build` only when `--flake-runs` is passed. Default off, not default 2. A default of 2 would add gate runs, replace `tests-flaky` retries with a terminal `FLAKY`, and surprise receipts that the phase clock and `tests.test_pfy_build_cloud` already lock. The shared env var stays local-only for the same reason. `--flake-runs 0` is an explicit skip, distinct from omitting the flag. Cloud still does not warn on `fixed_ports`, and the dollar and wall quotes do not grow when the flag is set. Those two are left off on purpose. The receipt field `flake` is the record of the re-runs.

## Architecture link

The default gate sits on the local runner behind `./pfy build --local`. The same helper is opt-in on the daily cloud path in [pfy-build.md](pfy-build.md), behind `--flake-runs`. Omitting that flag does not change the cloud default. No new layer and no new default engine. [ADR-0014](../adr/0014-pluggable-local-inference-spine.md) still chooses inference. [ADR-0012](../adr/0012-simple-harness-agnostic-launch.md) still makes `./pfy` the door.
