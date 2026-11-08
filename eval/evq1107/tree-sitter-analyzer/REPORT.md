# Tree-sitter Analyzer evq1107 (2026-11-07)

## Catalog tools on the same job

The job is a local call graph and blast radius for pfy build review (gap B). Gap B is that `./pfy build` is not proven bot-usable: the 2026-11-06 trial hit the 3 hour timeout, and the recheck fix is parked after two pregate failures. The 2026-11-07 ranking says no entry from 137 to 167 closes that gap. Tree-sitter Analyzer is entry 121. `scripts/pfy_build_cloud.py` already falls back to it when codebase-memory-mcp returns nothing.

| Tool | Stage | What it already covers | How Tree-sitter Analyzer compares |
|------|-------|------------------------|-----------------------------------|
| codebase-memory-mcp | I2 | Primary code-graph. On the same 10 commits its impact agreed with test_select on 5/10. | This probe also agreed on 5/10. It did not beat the primary graph. |
| Chiasmus | I1 | Tree-sitter call graph. `eval/ev1107/chiasmus/REPORT.md` agreed on 3/10. Bare Python names inflated callers (`main` in 157 files). Install 86 MB. | Agreed on 5/10. On `56f6df154eee` it named 1 test where chiasmus named 139. It still does not beat codebase-memory. |
| Graphify | I0 | Reference tree-sitter graph. Not the code memory we run. | Same slot, not measured here. No reason to start a third primary graph. |
| repowise | card uses | Context packing. The card says it overlaps codebase-memory. | Not a change-impact CLI. |
| LEANN | card uses | Compressed RAG. Not our code memory. | Different job. |
| chroma or lancedb | card uses | Vector store. Code memory is already chosen. | Different job. |
| `scripts/test_select.py` | in this repo | Import graph plus path mentions. Mode full on risky, core, or unknown paths. | The selector stays the source of the 10-commit score. A call graph does not see the full-mode rule. |
| git grep fallback | in `pfy_build_cloud.py` | Symbol name search when both catalog tools miss. | Still the last resort. This lane does not change that order. |

Batch-1 results under `eval/ev1107/` and `eval/catchup-1107/` do not add another call-graph measurement. Chiasmus is the one that already scored this window.

## Verdict

STAY I1. Change-impact agreed with `scripts/test_select.py` on 5/10 commits. codebase-memory agreed on 5/10 in `eval/ev1107/chiasmus/results.json`. Chiasmus agreed on 3/10. The family gate is real and small: 52 genuine cross-language mis-wires out of 62559 call edges, and 0 for Tree-sitter Analyzer. That did not move the 5/10. The allocated venv is 173 MB, over the 50 MB I2 copy limit. Gap B is unchanged.

## Pins

Install root: `~/.cache/pfy/tools/tree-sitter-analyzer/`. `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, and `TMPDIR` for every tool command were directories under that root. No global install. Login-home `~/.tsa`, `~/.cache/tree-sitter-analyzer`, and `~/.config/tree-sitter-analyzer` were absent before and after.

- Python 3.11.15 venv. The worktree `python3` is 3.14 and was not the venv.
- PyPI `tree-sitter-analyzer==2.2.0` (the entry pin). Tag `v2.2.0` is commit `a1656acde0d1065f7670c4d041f81a0e344ef6d7` (GitHub tags API on this run). Upstream also has `v3.1.1`. This lane did not install it.
- Wheel `tree_sitter_analyzer-2.2.0-py3-none-any.whl`, 2667339 bytes. sha256 `678ac7708e238c578ca11fb3433b200a007d14ba954f3eb79d8913c552ba1203` matches the PyPI digest. Base wheel only. The `[all]` extra is formatters and an HTTP client. The grammars are already required by the base package.
- `tree-sitter-analyzer --version` printed `tree-sitter-analyzer 2.2.0`. `miswire-audit` is the console script beside it.
- `du -sh` on the venv is 173M. `du -sb` is 241754718 bytes (the number in `results.json`). Pip cache `du -sh` is 56M. Both are over 50 MB.
- License on the PyPI metadata: MIT.
- The dependency set includes `anthropic` and `mcp`. No API key was passed. The CLI finished offline.

## Commands

`$BASE` is `~/.cache/pfy/tools/tree-sitter-analyzer`. The probe repo is a `git clone --shared --no-checkout` of this worktree into `$BASE/probe/repo`. That does not register a worktree on the shared git dir. `.ast-cache/` stayed in the clone.

```bash
python3.11 -m venv "$BASE/venv"
"$BASE/venv/bin/pip" install "$BASE/src/tree_sitter_analyzer-2.2.0-py3-none-any.whl"
python3 eval/evq1107/tree-sitter-analyzer/probe.py
```

The probe checks out each commit, then `git reset --mixed` to its parent, so the commit is an unstaged diff. Comparison calls use one `--change-impact-scope` with every changed path. `--change-impact-scope` is `nargs="+"`, so repeating the flag keeps only the last path. `scripts/pfy_build_cloud.py` repeats the flag. The cold row records both shapes.

The build-shaped call, 20 second cap, matches the fallback argv except the scope flag is passed once:

```bash
tree-sitter-analyzer --change-impact --format json --change-impact-no-tests \
  --change-impact-scope <every changed path, capped at 20>
```

The agreement call drops `--change-impact-no-tests` and adds `--change-impact-full`. `miswire-audit` runs on a clean checkout of this worktree HEAD `f53a7b14ca3dfa02de8521a7d92bbd69329f73d2`.

## Numbers

Window: the same 10 first-parent commits as `eval/ev1107/chiasmus/results.json` (origin/main at `9d3688718e96`). This probe re-ran `scripts/test_select.py` on those shas. Full mode is now 189 tests. The chiasmus trial recorded 181, 180, and 176 on those three full rows. The agree/disagree flags for codebase-memory and chiasmus are copied from that trial. Counts below for Tree-sitter Analyzer and test_select are from this run.

The cold commit is listed first. The other rows follow the chiasmus window order.

| sha | mode | test_select | cbm | chiasmus | tsa | agree | cbm agree | chiasmus agree | full s |
|---|---|---:|---:|---:|---:|---|---|---|---:|
| 56f6df154eee | affected | 1 | 1 | 139 | 1 | yes | yes | no | 13.464 |
| 9d3688718e96 | structural | 0 | 0 | 0 | 0 | yes | yes | yes | 6.043 |
| 1868e5d1b2c5 | full | 189 | 0 | 0 | 0 | no | no | no | 1.797 |
| 914b11c8a2c2 | full | 189 | 2 | 145 | 4 | no | no | no | 1.777 |
| 9bfc82fcf66c | full | 189 | 8 | 173 | 19 | no | no | no | 3.578 |
| 25e488764894 | affected | 1 | 1 | 1 | 1 | yes | yes | yes | 0.203 |
| ba18f7cc7947 | structural | 0 | 0 | 0 | 0 | yes | yes | yes | 5.125 |
| 31c373ba1c77 | affected | 1 | 1 | 19 | 1 | yes | yes | no | 1.841 |
| dd861e01cc8b | full | 189 | 1 | 170 | 2 | no | no | no | 3.796 |
| 79c083e9e53a | affected | 3 | 2 | 39 | 2 | no | no | no | 1.782 |

Agreement is set equality of `tests/test_*.py` paths. Tree-sitter Analyzer 5/10. codebase-memory 5/10. Chiasmus 3/10.

`56f6df154eee` changes `scripts/grill_ticket.py` and `tests/test_grill_ticket.py` plus docs. test_select, codebase-memory, and Tree-sitter Analyzer all name `tests/test_grill_ticket.py`. Chiasmus named 139 tests.

`31c373ba1c77` is the same shape. Tree-sitter Analyzer names `tests/test_pipeline_retro.py`. Chiasmus named 19.

`79c083e9e53a` is the affected miss from the chiasmus report. test_select names 3 tests. Tree-sitter Analyzer names `tests/test_catalog_self_pipeline.py` and `tests/test_stage_registry.py`, and omits `tests/test_catalog_entry_numbers.py`. That is the file the chiasmus report says codebase-memory also omits, because the link is a path string rather than an import. Chiasmus named 39.

`1868e5d1b2c5` has no Python hunks that select a single test. test_select is full (189). Tree-sitter Analyzer, codebase-memory, and chiasmus all return no tests.

On the four full rows, Tree-sitter Analyzer returns 0, 4, 19, and 2 tests. codebase-memory returned 0, 2, 8, and 1. Chiasmus returned 0, 145, 173, and 170. `only_tsa` is 0 on all 10 commits: every test Tree-sitter Analyzer named is inside the test_select set. On a full row that set is the whole suite, so a short list still disagrees. On the affected rows, chiasmus added tests the diff does not import (139, 19, and 39). Tree-sitter Analyzer added none.

The build keeps `paths[:20]`. `9bfc82fcf66c` changed 32 files and `dd861e01cc8b` changed 26. The agreement calls passed every path. The wired fallback would drop the rest, and the repeated scope flag would then keep only the last of those 20.

`affected_count` in the JSON was 0 on all 10 commits. The scored set is `tests_to_run`.

Build budget, commit `56f6df154eee`, cache deleted first:

| Call | Seconds | Result |
|------|--------:|--------|
| One `--change-impact-scope`, `--change-impact-no-tests`, cold | 1.303 | exit 0, usable, `changed=10`, `tests_to_run_count=0` |
| Repeated `--change-impact-scope` (the build loop) | 0.223 | exit 0, `changed_count=1` |
| `--change-impact-full`, tests included | 13.464 | exit 0, usable, 1 test, the agreement row |

A later warm build-shaped call on `9d3688718e96`, after that commit's full index, was 1.753s, exit 0, usable, `changed=2`. Every scored call finished inside the 20 second cap `change_impact_map` uses. The wired fallback still skips test discovery (`--change-impact-no-tests`) and, because the flag is repeated, only the last scoped path is analyzed.

Mis-wire audit on HEAD, 5.402s, exit 0. Indexed bash:58, javascript:8, python:484, rust:2.

| Resolver | Cross-language mis-wires | Rate |
|----------|-------------------------:|------|
| Name-only | 53 (52 genuine) | 0.08% of 62559 edges |
| Tree-sitter Analyzer | 0 | 0.00% |

Genuine here means the callee name is not in the tool's builtin exclusion list. Eight offenders are common names (`args`, `run`, `cls`, `toggle`, `select`, `remove`, `build`, `cleanup`) with the caller in one language and a same-name def in another. `.ast-cache` after the run is 83103744 bytes apparent (`du -sb`) and 17M allocated (`du -sh`).

## Gates

Value gate for I3 needs 3 of 4. This probe has 2.

1. Gap fill: no. The hole in review blast radius is already filled by codebase-memory at 5/10 and by test_select for the suite. Tree-sitter Analyzer ties the first and loses to the second on every full-mode commit. The 52 mis-wires are 0.08% of edges and did not change the 5/10. Gap B, the 3 hour build timeout, did not move.
2. Operator leverage: no. A corrected call returns inside 20 seconds, and the map does not beat codebase-memory. The argv in `pfy_build_cloud.py` repeats `--change-impact-scope` and passes `--change-impact-no-tests`, so the prompt does not get the test list, and a multi-file scope keeps one path.
3. Evidence: yes. Offline venv, this report, `results.json`.
4. Blast radius: yes on the written gate. MIT, no model weights, no account, no primary runtime. The anthropic package is installed and was not called.

Modularity, all four, for a cache probe only:

1. Local code was required. The repeated scope flag and the 52 vs 0 mis-wire count are not in the README's fixture (that fixture scored 0 for both resolvers).
2. The CLI entry point is one wheel. The dependency set is large (numpy, mcp, anthropic). The unit of eval stayed the CLI.
3. It sat under `~/.cache/pfy/tools/tree-sitter-analyzer/` and did not become the product runtime.
4. Deleting that directory leaves the pin, this report, and the entry.

Lightweight I2 size gate: fail. The venv allocates 173 MB. The limit is 50 MB. I2 is not open on size, and the tie with codebase-memory also fails the "measurably helps" bar.

## Risks

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Repeated scope flag | `pfy_build_cloud.py` appends `--change-impact-scope` once per path. argparse stores the last list. On `56f6df154eee` that map saw 1 file, not 10. | Pass every path to one flag. This lane does not edit the build. |
| `--change-impact-no-tests` | The fallback map has `tests_to_run_count` 0. The reviewer does not see the test the full call found. | Drop the flag only in a later ticket that diffs the prompt. Keep test_select as the runner. |
| `.ast-cache/` in the tree | 17 MB allocated inside the audited checkout. A real worktree would show it in status. | Shared clone or throwaway dir only. Do not commit the cache. |
| Full or unknown paths | test_select runs 189 tests. The call graph returns a handful, or none. | Do not replace the selector. Core, risky, and unknown rules stay in test_select. |
| Multiplier wording | The tool prints "53x cleaner" for 53 vs 0. The rate is 0.08% of edges. | Quote the edge counts. Do not promote on the multiplier. |
| Hosted client library | `anthropic` is installed. A future command could try the network if a key is in the environment. | Keep the empty env used here. Do not start `tree-sitter-analyzer-mcp`. |
| Pin drift | Tags exist through v3.1.1. This wheel will not match a later README. | Stay on 2.2.0 until a new ticket repins and repeats the 10 commits. |
| Cold index over 20 seconds | This repo's cold full call was 13.464s. A larger tree can exceed the build cap and fall through to git grep. | The build already treats a timeout as an empty map. Do not raise the cap here. |

## Next gate

Stay I1. Do not copy the venv into the repo. A later pin has to allocate under 50 MB and either agree with test_select on more than 5 of these 10 commits, or name `tests/test_catalog_entry_numbers.py` for `79c083e9e53a`. Fixing the repeated scope flag is a separate build ticket. Gate wiring is a separate ticket. No Feature GO.

## Five questions (if this tool were in the pipeline)

1. What triggers it? A person asking for a per-file review blast radius, or the existing fallback in `change_impact_map` when codebase-memory-mcp returns nothing. Nothing in pregate or CI calls it after this trial.
2. What does it do, and which services does it read and write? It reads a git checkout and answers `--change-impact` or `miswire-audit`. It writes `.ast-cache/` in that tree. With `HOME` under `~/.cache/pfy/tools/tree-sitter-analyzer/` it did not touch the login home. No hosted model and no gate file.
3. What does it trigger next? Nothing. The comparison does not queue a wiring ticket.
4. Where does a human re-enter? Before any edit to `pfy_build_cloud.py`, and before any gate wiring. Mark stops a lane with `tmp/STOP` in the worktree or `tmp/evq/STOP`.
5. What stops two runs doing the same work? One worktree and one branch for this slug. The tool is not on a gate, so it cannot select the same suite twice. The stage card is per tool, so another lane does not edit it.
