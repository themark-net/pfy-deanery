# Module: pfy build --local flake gate and size caps

**Architecture layer:** Local build runner, opt-in side of `./pfy` ([ARCHITECTURE.md](../ARCHITECTURE.md) layout map, simple launch). Inference stays [ADR-0014](../adr/0014-pluggable-local-inference-spine.md).
**Code:** `pfylib/build_flake.py`, `pfylib/build_size.py`, hook in `scripts/pfy_build_local.py`
**Related ADR / Decisions:** Decision recorded in this file. No new ADR number.

Cloud `./pfy build` is a different runner. See [pfy-build.md](pfy-build.md). This page is only the local flake gate and the size presets. Cost confirmation, packed review quotes, and `--yes` / `--max-cost` live in that cloud module doc, not here. The local receipt still records `estimate.flake_runs` and `estimate.review_prompts` so the $0 banner names those extras.

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

## Configuration / variables

| Name | Where | Purpose |
|------|-------|---------|
| `--flake-runs N` | CLI | Extra clean-clone runs after a green in-wrap gate. `0` skips. |
| `PFY_BUILD_FLAKE_RUNS` | environment | Used when `--flake-runs` is omitted. Default 2 (`DEFAULT_FLAKE_RUNS` in `pfylib/build_flake.py`). A non-integer or a negative value is usage exit 2. |
| `--size small\|product` | CLI | Cap preset. The flag wins over a task line. |
| `size: small` or `size: product` | task text, one whole line | Preset when `--size` is omitted. First match wins. |
| `--max-files`, `--max-lines` | CLI | Override one dimension. They win over the preset. |
| small caps | `pfylib/build_size.py` `SMALL_MAX_FILES` 40, `SMALL_MAX_LINES` 4000 | Default. Same numbers the help text names. |
| product caps | `PRODUCT_MAX_FILES` 120, `PRODUCT_MAX_LINES` 12000 | Opt-in. |
| `flake` | receipt `pfy-local-build/1` | `{runs, skipped, results: [{run, exit, ok, tail, stop}]}`. Omitted when the run stopped before the flake step. |
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

- Caller: `scripts/pfy_build_local.py` only. `scripts/pfy` execs that file when argv contains `--local`.
- Callees: `run_tests` (same bwrap profile as the in-wrap gate) and `judge_tests` against `tests_before`.
- Not a caller: `scripts/pfy_build_cloud.py`. Cloud still re-runs in the same tree and records reason `tests-flaky`. Its phase clock still expects four gate runs.

### Invariants

- `FLAKY` is exit 1, no commit, no branch, no agent retry. Salvage mode does not rewrite it to `TIMEOUT`.
- `--flake-runs 0` does not run the old same-tree second gate. A gate that passes once and would fail on the next read of its own state file can still `PASS`.
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

- Wire these helpers into `scripts/pfy_build_cloud.py` without revisiting the cloud phase clock and the `tests-flaky` contract.
- Treat port 0 as a fixed port, or fail the build on `fixed_ports`.
- Suggest `--size product` when an explicit `--max-files` or `--max-lines` set the cap that was exceeded.
- Commit, push, or retry a `FLAKY` round.
- Raise the small default above 40 files or 4000 lines. Help text and the five-file wrapfix path depend on those numbers.

## Decision

The leasegrid replay saw `./pfy build --local` pass its sandboxed gate while a clean clone of the suite was flaky (a test bound port 15439, and the environment leaked). Evaluators also had to raise wrap caps by hand for a product-sized round. This lane re-runs the local gate from a clean export with a fresh `HOME`, and adds an opt-in product cap.

Rejected: changing the small default. The help text locks "40 changed files" and "4000 added plus removed lines", and a five-file diff must pass with no size flag. The 20-file behavior check is over the line cap (4400 lines), which `--size product` allows.

Rejected: the same `FLAKY` status on the cloud runner in this lane. Cloud keeps a same-tree second gate, reason `tests-flaky`, and a four-run phase clock. Another lane is editing that file.

## Architecture link

This sits on the local runner behind `./pfy build --local`, not on the daily cloud path in [pfy-build.md](pfy-build.md). It does not change the architecture map: no new layer, no new default engine. [ADR-0014](../adr/0014-pluggable-local-inference-spine.md) still chooses inference. [ADR-0012](../adr/0012-simple-harness-agnostic-launch.md) still makes `./pfy` the door.
