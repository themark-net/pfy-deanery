# Chiasmus impact trial (ev1107)

Verdict: STAY I1. `chiasmus_graph` analysis `impact` at pin 0.1.40 runs offline on nimo and does not beat codebase-memory. Agreement with `scripts/test_select.py` is 3/10. codebase-memory on the same commits is 5/10. No test that chiasmus added, and test_select skipped, imports the changed module. This lane does not wire chiasmus into test selection, pregate, or CI.

Counts are in `eval/ev1107/chiasmus/results.json`.

## Pins

| Item | Value |
|---|---|
| npm | `chiasmus@0.1.40` |
| tarball sha256 | `0d1e911a8ada5007c5f440d0c87a0f284d367188aeb2d0f8fba790f833500a34` |
| npm shasum | `3b2036b60d9fd5217b9466c3a45a178cf7fcac05` |
| Node | v22.23.0 at `/usr/bin/node` |
| server | `node_modules/chiasmus/dist/mcp-server.js` (stdio) |
| install size | `node_modules` 86 MB, npm cache 70 MB |
| graph cache after the run | `CHIASMUS_CACHE_DIR` 2.8 MB |

The entry's git commit pin is `e3e8aa54d200f97507514d205b3bfb156aa70150`. This run checked the npm version and the tarball hash. It did not re-clone the git tag.

`~/.chiasmus` and `~/.cache/chiasmus` were absent before and after. `CHIASMUS_HOME` and `CHIASMUS_CACHE_DIR` stayed under `~/.cache/pfy/tools/chiasmus/`.

## Commands

Env for install and the server, all under `~/.cache/pfy/tools/chiasmus/`: `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `npm_config_cache`, `TMPDIR`, `CHIASMUS_HOME`, `CHIASMUS_CACHE_DIR`. The server env did not pass provider keys. `tools/list` omitted `chiasmus_search`. `chiasmus_solve` was listed and was not called. No `chiasmus-http`.

```bash
npm install --prefix ~/.cache/pfy/tools/chiasmus --ignore-scripts --omit=optional chiasmus@0.1.40
node ~/.cache/pfy/tools/chiasmus/node_modules/chiasmus/dist/mcp-server.js
```

MCP is newline-delimited JSON-RPC. `initialize` with `protocolVersion` `2024-11-05`, then `notifications/initialized`, then `tools/call` of `chiasmus_graph`. Arguments: `files` (absolute paths), `analysis` (`facts` or `impact`), `target` (impact only), `cache` true.

Two commits were not in the 2026-11-07 shadow report because they landed later. Their rows were appended with:

```bash
python3 scripts/cbm_shadow.py --base 1868e5d1b2c5f8c042ffef24c67153c61b0b2a3c --head 9d3688718e964dd9e26df465f22ce61cf31e8a0b
python3 scripts/cbm_shadow.py --base 914b11c8a2c2fc55407874342ee5789ed223a085 --head 1868e5d1b2c5f8c042ffef24c67153c61b0b2a3c
```

## Method

Window: last 10 first-parent commits of `origin/main` at `9d3688718e964dd9e26df465f22ce61cf31e8a0b`, each against its parent. Each tree was `git archive` into the tool cache. That does not register a worktree on the shared git dir.

Python files are the same scan dirs as `scripts/test_select.py` (`tests`, `scripts`, `pfylib`, `harness`, `examples`, `eval`, `bootstrap`, `gui`, plus root `*.py`). One `facts` call per commit supplies `defines(file, name, kind, line)`. A target is a function, method, or class whose start line overlaps a diff hunk, plus a `def` or `class` name the diff removed. One `impact` call per target. The primary test set is every `tests/test_*.py` that defines a returned caller name, plus changed test files. A second set counts a caller name only when exactly one file defines it. Agreement is set equality with the shadow log's `test_select` list for that sha and base.

A chiasmus-only test is a real miss when `test_select.Graph.test_dependents` or `string_refs`, on the archived tree, says that test imports a changed Python module.

Python names in this pin are bare. `impact` of `main` is one graph node. Mapping a returned name to every file that defines it is what the tool's facts allow. The unique-name column is the same answer with ambiguous names dropped. Both columns agree on 3/10.

## Numbers

Wall clock for the 10 commits is 50.683 s (facts 3.166 s, impact 20.941 s, the rest archive and the import check). Shadow log: test_select 9.574 s, codebase-memory `detect_changes` 0.450 s. A cold `facts` call on 459 files, before this cached run, was 3.614 s.

| sha | mode | test_select | cbm | chiasmus | unique | agree | cbm agree | wall s |
|---|---|---:|---:|---:|---:|---|---|---:|
| 9d3688718e96 | structural | 0 | 0 | 0 | 0 | yes | yes | 3.635 |
| 1868e5d1b2c5 | full | 181 | 0 | 0 | 0 | no | no | 2.932 |
| 914b11c8a2c2 | full | 181 | 2 | 145 | 119 | no | no | 7.578 |
| 9bfc82fcf66c | full | 180 | 8 | 173 | 137 | no | no | 5.917 |
| 25e488764894 | affected | 1 | 1 | 1 | 1 | yes | yes | 3.859 |
| 56f6df154eee | affected | 1 | 1 | 139 | 115 | no | yes | 8.936 |
| ba18f7cc7947 | structural | 0 | 0 | 0 | 0 | yes | yes | 2.086 |
| 31c373ba1c77 | affected | 1 | 1 | 19 | 10 | no | yes | 2.514 |
| dd861e01cc8b | full | 176 | 1 | 170 | 138 | no | no | 7.295 |
| 79c083e9e53a | affected | 3 | 2 | 39 | 17 | no | no | 5.931 |

The three agreements are two empty structural diffs and `25e488764894`, which only changes `tests/test_grill_ticket.py`.

`56f6df154eee` changes `scripts/grill_ticket.py` and its test. test_select and codebase-memory both name that one test. Impact returns caller names such as `main` (defined in 157 files), so the primary set is 139 tests. None of the 138 extras import the change.

`79c083e9e53a` is the shadow report's affected miss. test_select names `tests/test_catalog_entry_numbers.py` because that file references `scripts/catalog_check.py`. codebase-memory omits it. Chiasmus omits it too, and adds 37 tests that do not import the change.

`1868e5d1b2c5` has no Python hunks. test_select is `full` because `eval/ev1107/osc/VERDICT` and `validate.mjs` are unknown files (181 tests). Chiasmus and codebase-memory both return no tests. A call graph does not see that rule.

## Gates

Value gate for I3, 2 of 4:

1. Gap fill: no. codebase-memory agrees more often, and test_select stays the selector.
2. Operator leverage: no for this job. The bare-name graph adds tests the diff does not import.
3. Evidence: yes. Offline stdio run, this report.
4. Blast radius: yes on the value-gate wording. Apache-2.0, no model weights, stdio only, cache confined when the two env vars are set.

Modularity gate, all 4 true: the behavior is not visible from the README alone, the entry point is one npm package, it lives in the tool cache, and deleting that cache leaves the card and the entry.

Lightweight I2 size gate: fail. `node_modules` is 86 MB. The limit is 50 MB. I2 is not open on size, and the ticket's beat-codebase-memory bar also fails.

## Risks

| Risk | How it fails | Recovery |
|---|---|---|
| Bare Python names | `impact` merges every `main`. The test set grows to files that share a caller name and do not import the diff. | Keep test_select. Re-trial only if a later pin qualifies names by file. |
| Unknown or core paths | A non-Python path forces `full` in test_select. Impact returns nothing when no Python symbol changed, and the suite would be skipped. | Do not replace the selector. The core, risky, and unknown rules stay in test_select. |
| Real home writes | Unset `CHIASMUS_HOME` creates `~/.chiasmus`. Unset `CHIASMUS_CACHE_DIR` writes `~/.cache/chiasmus`. | Set both under `~/.cache/pfy/tools/chiasmus/` on every run. This run did. Both real paths stayed absent. |
| Solver or HTTP side path | `chiasmus-http` has no auth. `chiasmus_solve` and `chiasmus_search` want a model. | This lane used stdio `chiasmus_graph` only. Do not start the daemon and do not call those two tools. |

## Next gate

Stay I1. Promote only after a pin that qualifies Python symbols by file, and a repeat of this 10-commit comparison that either agrees with test_select more often than codebase-memory or names a skipped test that really imports the change. The copy is over 50 MB, so that win still does not become an in-tree I2 probe. Gate wiring is a separate ticket.

## Five questions (if this tool were in the pipeline)

1. What triggers it? A person asking for a per-file review blast radius on a diff. Nothing in pregate or CI calls it after this trial.
2. What does it do, and which services does it read and write? It reads a git archive of the repo and answers `chiasmus_graph` over stdio. It writes only `CHIASMUS_HOME` and `CHIASMUS_CACHE_DIR` under `~/.cache/pfy/tools/chiasmus/`. No hosted model and no gate file.
3. What does it trigger next? Nothing. The comparison does not queue a wiring ticket.
4. Where does a human re-enter? Before any gate wiring. A later pin needs a new ticket and the grill step. Mark stops a lane with `tmp/STOP` or `tmp/ev1107/STOP`.
5. What stops two runs doing the same work? This eval had one worktree and one branch. The tool is not on a gate, so it cannot select the same suite twice. The graph cache is content-hashed under the tool cache and is not a lock.
