# Axon evq1107 (2026-11-07)

## Catalog tools on the same job

The job is a local call graph and blast radius for pfy build review (gap B). Gap B is that `./pfy build` is not proven bot-usable: the 2026-11-06 trial hit the 3 hour timeout, and the recheck fix is parked after two pregate failures. The 2026-11-07 ranking says no entry from 137 to 167 closes that gap. Axon is entry 082, outside that range. The 2026-10-06 skip line lists Axon with Graphify and Ix because codebase-memory is the primary graph. This lane builds no pipeline, CI, or gate step.

| Tool | Stage | What it already covers | How Axon compares |
|------|-------|------------------------|-------------------|
| codebase-memory-mcp | I2 | Primary code-graph. On the same 10 commits its impact agreed with test_select on 5/10. | Bare impact and file-qualified callers each agreed on 4/10. It does not beat the primary graph. |
| Tree-sitter Analyzer | I1 | Change-impact on this window. `eval/evq1107/tree-sitter-analyzer/REPORT.md` agreed on 5/10. Allocated venv 173 MB. | Agreed on 4/10. On `56f6df154eee` it named 11 tests where Tree-sitter Analyzer and codebase-memory named 1. |
| Chiasmus | I1 | Tree-sitter call graph. `eval/ev1107/chiasmus/REPORT.md` agreed on 3/10. Bare Python names inflated callers (`main` in many files). Install 86 MB. | Agreed on 4/10, ahead of chiasmus and behind the other two. Same bare-name class: `axon context main` hit one non-test `main`, not the changed file. |
| Graphify | I0 | `eval/evq1107/graphify/REPORT.md` scored `graphify affected` plus the test files in the diff. That set agreed on 5/10 because it was exactly those changed test files. The affected walk added 0 tests. Venv 102 MB. Stay I0. | Axon at 4/10 is a caller walk. It does not beat codebase-memory. Graphify's 5/10 does not show a wider blast radius than the diff's own test files. |
| repowise | I2 | Context packing. The card says it overlaps codebase-memory. | Not a change-impact CLI. |
| LEANN | I1 | Compressed RAG. Stay until a measured gap versus codebase-memory. | Different job. |
| chroma or lancedb | I0 | Vector store. Code memory is already chosen. | Different job. |
| opencode-mem | I1 | Worker memory. | Not a call graph. |
| MemPalace | I0 | Verbatim memory. | Not a call graph. |
| `scripts/test_select.py` | in this repo | Import graph plus path mentions. Mode full on risky, core, or unknown paths. | The selector stays the source of the 10-commit score. A call graph does not see the full-mode rule. |
| git grep fallback | in `pfy_build_cloud.py` | Symbol name search when catalog tools miss. | Still the last resort. This lane does not change that order. `./pfy code-graph` is unchanged: it may prefer axon when the binary exists, and it must not paint codebase-memory as Axon. |

Batch-1 results under `eval/ev1107/` and `eval/catchup-1107/` do not add another call-graph measurement. Chiasmus scored this window first. Graphify's later probe on the same commits scored the changed test files, not callers.

## Verdict

STAY I1. Bare `axon impact` and file-qualified callers each agreed with `scripts/test_select.py` on 4/10 commits. codebase-memory agreed on 5/10. Tree-sitter Analyzer agreed on 5/10. Chiasmus agreed on 3/10. Graphify's same-day card stays I0: its 5/10 is the test files already in the diff, and the affected walk added none. Qualifying the callee by file did not move Axon's count. The venv allocates 218 MB and each index is about 125 MB, both over the 50 MB I2 copy limit. Gap B is unchanged. Axon does not beat what we have.

## Pins

Install root: `~/.cache/pfy/tools/axon/`. `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, and `TMPDIR` for every tool command were directories under that root. No global install. Login-home `/home/mark/.axon`, `/home/mark/.cache/axon`, and `/home/mark/.config/axon` were absent before and after (`results.json` `home_before` and `home_after`).

- Python 3.11.15 venv. The worktree `python3` is 3.14.4 and ran the probe and `scripts/test_select.py`. It was not the venv.
- Entry pin: git `main` @ `2b386fb38a468201ab2ec825ddea5ebf4c33f513` (2026-08-03) and PyPI `axoniq` 1.0.1. `axon --version` printed `Axon v1.0.1`.
- Wheel `axoniq-1.0.1-py3-none-any.whl`, 2255992 bytes. sha256 `4632b2f6d11a7c365ade3a307d3d49b7f4e0010ef338ee2531a12caf57260a60` matches the file downloaded for this lane. The runtime is the git checkout, not that wheel. `diff -rq` of the unpacked wheel against the pin shows these Python files differ: `cli/main.py`, `core/embeddings/embedder.py`, `core/embeddings/text.py`, `core/ingestion/pipeline.py`, `core/ingestion/processes.py`, `core/ingestion/watcher.py`, `core/storage/base.py`, `core/storage/kuzu_backend.py`. The frontend tree also differs (built `dist` in the wheel, sources in git). `axon ui` was not built or started.
- Unconstrained `mcp>=1.0.0` resolved mcp 2.3.0. The CLI then failed at import: `streamablehttp_client` was renamed to `streamable_http_client`. The import sits at module level in `cli/main.py`, so `analyze`, `impact`, and `context` die with it. This probe installed `mcp>=1.0,<2`, which resolved mcp 1.30.0 (`importlib.metadata`). `axoniq` metadata stayed 1.0.1. Upstream was not patched into this repo.
- `du -sh` on the venv is 218M. `du -sb` is 361274506 bytes (the number in `results.json`). Pip cache `du -sh` is 113M. fastembed, onnxruntime, numpy, and kuzu are installed. Every commit recorded `embeddings` 0. No model weights were downloaded. `--no-embeddings` was passed on every analyze.
- License: MIT.
- The CLI GETs `https://pypi.org/pypi/axoniq/json` about once a day unless `~/.axon/update-check.json` is fresh (fail-closed, no key). This probe seeded `~/.cache/pfy/tools/axon/home/.axon/update-check.json` with `latest_version` 1.0.1 before the 10 commits, so the timings below are index time, not the 1.5s timeout. `axon serve --watch` and `axon ui` were not started.

## Commands

`$BASE` is `~/.cache/pfy/tools/axon`. The probe repo is a shared clone of this worktree at `$BASE/probe/repo`. That does not register a worktree on the shared git dir. Each commit is checked out with `git checkout --force --detach`, then `.axon` is deleted before analyze.

```bash
python3.11 -m venv "$BASE/venv"
# First install of the git pin pulled mcp 2.3.0 and the CLI did not import.
"$BASE/venv/bin/pip" install 'mcp>=1.0,<2'
"$BASE/venv/bin/pip" install "$BASE/src/axon"
python3 eval/evq1107/axon/probe.py
```

The scored commands, with `HOME` under `$BASE/home` and `NO_COLOR=1`, `TERM=dumb`, `COLUMNS=400`:

```bash
axon analyze . --no-embeddings
axon impact <symbol> --depth 1
axon context <symbol>
```

Depth is 1 because test_select scores direct dependents. The CLI default depth is 3. The operator path takes a bare name. The probe also reads call edges with a read-only cypher query (`rel_type = 'calls'`) and keeps a caller only when the callee id is a symbol whose line range overlaps a `-U0` hunk. Qualified and bare sets both include test files the diff itself changed. Agreement is set equality of `tests/test_*.py` paths, and the selector mode must not be `error`. The cypher printer wraps rows near 80 columns even when `COLUMNS=400`. The probe joins a continuation line before it splits on `|`. Impact text is scored after newlines are removed, with `-- <path>:<line>`. Context uses `File: <path>:<line>`. Call edges are the tool default: confidence is not filtered, so a 0.5 fuzzy edge counts.

## Numbers

Window: the same 10 first-parent commits as `eval/ev1107/chiasmus/results.json` (origin/main at `9d3688718e964dd9e26df465f22ce61cf31e8a0b`). This probe re-ran `scripts/test_select.py` on those shas. Full mode came out 181, 181, 180, and 176, matching the chiasmus trial. Counts and agree flags for codebase-memory, chiasmus, and Tree-sitter Analyzer are copied from that trial and from `eval/evq1107/tree-sitter-analyzer/results.json`. This run's full-mode counts match that trial, and the copied flags are still 5/10, 3/10, and 5/10.

`impact_s` is the sum of `axon impact` and `axon context` for that commit. Wall clock for the probe is 394.982s. Every analyze exited 0.

| sha | mode | test_select | bare | qual | agree B/Q | targets | names | mis | analyze s | graph s | impact s | cbm | chiasmus | tsa | index bytes |
|---|---|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 9d3688718e96 | structural | 0 | 0 | 0 | yes/yes | 0 | 0 | 0 | 9.504 | 5.071 | 0 | 0 | 0 | 0 | 125764018 |
| 1868e5d1b2c5 | full | 181 | 0 | 0 | no/no | 0 | 0 | 0 | 9.446 | 5.26 | 0 | 0 | 0 | 0 | 125739442 |
| 914b11c8a2c2 | full | 181 | 14 | 19 | no/no | 48 | 48 | 8 | 9.604 | 5.071 | 53.039 | 2 | 145 | 4 | 125841842 |
| 9bfc82fcf66c | full | 180 | 10 | 8 | no/no | 41 | 33 | 8 | 9.55 | 5.242 | 42.003 | 8 | 173 | 19 | 125596082 |
| 25e488764894 | affected | 1 | 1 | 1 | yes/yes | 2 | 2 | 0 | 9.939 | 5.227 | 2.46 | 1 | 1 | 1 | 125264306 |
| 56f6df154eee | affected | 1 | 11 | 11 | no/no | 55 | 55 | 8 | 10.507 | 5.616 | 61.276 | 1 | 139 | 1 | 125317554 |
| ba18f7cc7947 | structural | 0 | 0 | 0 | yes/yes | 0 | 0 | 0 | 9.093 | 4.979 | 0 | 0 | 0 | 0 | 125133234 |
| 31c373ba1c77 | affected | 1 | 1 | 1 | yes/yes | 4 | 4 | 0 | 9.187 | 5.051 | 4.467 | 1 | 19 | 1 | 125178290 |
| dd861e01cc8b | full | 176 | 16 | 16 | no/no | 46 | 46 | 7 | 9.305 | 5.147 | 51.811 | 1 | 170 | 2 | 125039026 |
| 79c083e9e53a | affected | 3 | 2 | 2 | no/no | 20 | 20 | 2 | 9.378 | 5.181 | 22.278 | 2 | 39 | 2 | 124871090 |

Bare agreement 4/10. Qualified agreement 4/10. File qualification changed the set on some full rows (`914b11c8a2c2` 14 vs 19, `9bfc82fcf66c` 10 vs 8) and did not change any agree flag.

`25e488764894` and `31c373ba1c77` agree because the changed test file is the one test_select names (`tests/test_grill_ticket.py`, `tests/test_pipeline_retro.py`). The two structural commits have an empty set on every tool. `1868e5d1b2c5` has no overlapping symbols. test_select is full (181). Axon, codebase-memory, chiasmus, and Tree-sitter Analyzer all return no tests.

`56f6df154eee` is the unique loss against codebase-memory. test_select names `tests/test_grill_ticket.py`. Both axon sets name that file plus `tests/test_attach.py`, `tests/test_hermes_bakeoff.py`, `tests/test_hr_sigterm_exact.py`, `tests/test_pfy_build_cloud.py`, `tests/test_pregate_orphans.py`, and five `tests/test_x_intake_smoke_*.py` files (11 total). The two sets are equal, so the extras are stored call edges, not only the bare first hit. Eight of the 55 names resolved to a file that does not define that name in the diff. codebase-memory and Tree-sitter Analyzer named the 1 test. Chiasmus named 139.

`79c083e9e53a` matches the codebase-memory and Tree-sitter Analyzer miss. test_select names 3 tests. Both axon sets name `tests/test_catalog_self_pipeline.py` and `tests/test_stage_registry.py`, and omit `tests/test_catalog_entry_numbers.py` (a path string, not an import). `axon context` resolved `main` to `.github/scripts/restore-operator-launcher.py` and `_load` to `eval/mvp2/gates/test_mvp2_t6_tree_sig_three.py`. Catalog-check helpers on the changed file resolved to `scripts/catalog_check.py`. Chiasmus named 39.

On the four full rows, axon returns 0, 14 or 19, 10 or 8, and 16 tests against 181, 181, 180, and 176. A short list inside a full-mode set still disagrees.

First-commit stats (`9d3688718e96`): files 456, symbols 6422, relationships 29541, clusters 127, flows 381, dead code 243, coupled pairs 53, embeddings 0. Later commits stay in that band (symbols 6247 to 6422, embeddings 0 on all 10).

## Gates

Value gate for I3 needs 3 of 4. This probe has 2.

1. Gap fill: no. The hole in review blast radius is already filled by codebase-memory at 5/10 and by test_select for the suite. Axon is at 4/10 on both the bare CLI and the file-qualified edges. Gap B, the 3 hour build timeout, did not move.
2. Operator leverage: no. Analyze is about 10 seconds and the graph read is about 5 seconds, then 55 names on `56f6df154eee` took 61.276 seconds of impact plus context and still returned 11 tests. The bare CLI mis-resolves common names. A plain `pip install axoniq` on this date does not yield a working CLI, because mcp 2.3.0 breaks the import.
3. Evidence: yes. Offline venv, this report, `results.json`.
4. Blast radius: yes on the written gate. MIT, no model weights downloaded, no account, no primary runtime. The venv is 218 MB and each index is about 125 MB. That is under multi-GB and over the separate I2 copy limit.

Modularity, all four, for a cache probe only:

1. Local code was required. The first-hit name search and the mcp 2 import break are not in the README's install line (`pip install axoniq`).
2. The unit of eval is the `axon` CLI. The dependency set is large (kuzu, igraph, leidenalg, fastembed, onnxruntime, mcp). It stayed one package plus the mcp pin.
3. It sat under `~/.cache/pfy/tools/axon/` and did not become the product runtime.
4. Deleting that directory leaves the pin, this report, and the entry.

Lightweight I2 size gate: fail. The venv allocates 218 MB and the index is about 125 MB. The limit is 50 MB. I2 is not open on size, and 4/10 against codebase-memory at 5/10 also fails the "measurably helps" bar.

## Risks

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Bare name collision | `exact_name_search` scores a path 2.0 when it does not contain `/tests/`, else 1.0, then keeps the first node id (`limit=1`). A top-level `tests/` path is not downranked. `axon context main` still hit one `main`. On `79c083e9e53a` that file was `.github/scripts/restore-operator-launcher.py`. | Query the changed file's node id. On this repo that still left 4/10, because `56f6df154eee` stored edges to 10 extra tests. |
| mcp 2 import | `mcp>=1.0.0` installs 2.3.0. `cli/main.py` imports `streamablehttp_client` at module level. Every subcommand dies. | Pin `mcp>=1.0,<2` (1.30.0 here) until upstream imports `streamable_http_client`. Do not patch the checkout into the repo. |
| Wheel is not the git pin | PyPI 1.0.1 differs in the eight Python files listed above. A later `pip install axoniq` will not match this probe. | Install commit `2b386fb38a468201ab2ec825ddea5ebf4c33f513` and record both the git pin and the wheel sha256. |
| Daily PyPI GET | Without a fresh update cache the CLI calls pypi.org (1.5s, fail-closed). Timings mix in that wait. | Seed `update-check.json` under the redirected HOME, as this probe did, or accept the timeout. No key. |
| Fuzzy call edges | Default impact and the cypher `calls` edges include confidence 0.5. The 10 extra tests on `56f6df154eee` may include those. | A later probe can drop edges under a stated confidence. This one did not, so the 4/10 is the default tool. |
| Wrapped cypher rows | Rich wraps a row near column 80 when stdout is not a tty. A split on the pipe character then drops or shifts the caller path. | Join continuation lines first. `tests/test_axon_probe.py` drives a wrapped row through the probe. |
| Full or unknown paths | test_select runs 176 to 181 tests. The call graph returns a handful, or none. | Do not replace the selector. Core, risky, and unknown rules stay in test_select. |
| String-only test refs | `79c083e9e53a` omits `tests/test_catalog_entry_numbers.py`, the same miss as codebase-memory and Tree-sitter Analyzer. | Keep path mentions in test_select. |
| Size | Venv 218 MB, index about 125 MB per checkout, pip cache 113 MB. Copying that into the repo fails the I2 limit and dirties status if `.axon` is left behind. | Cache and shared clone only. Do not commit `.axon`, the venv, or the wheel. |
| Embeddings and the UI | fastembed is installed. `axon ui` and `axon serve --watch` are out of this lane. A later command can download weights or listen. | Keep `--no-embeddings`. Do not start `axon ui` or `axon serve --watch`. |
| Host writes | The registry uses `Path.home()` (`~/.axon/repos/`). A run without the redirected HOME writes the login home. | The probe builds a clean env with `HOME` under the cache. The login paths stayed absent. |

## Next gate

Stay I1. Do not copy the venv or the index into the repo. A later pin has to qualify Python names by file, stay under 50 MB, and beat codebase-memory's 5/10 on these commits, or name `tests/test_catalog_entry_numbers.py` for `79c083e9e53a` without adding the 10 extra tests on `56f6df154eee`. mcp must stay below 2 until upstream imports `streamable_http_client`. Gate wiring is a separate ticket. No Feature GO.

## Five questions (if this tool were in the pipeline)

1. What triggers it? A person asking for a per-file review blast radius. Nothing in pregate or CI calls axon after this trial. This lane does not change `./pfy code-graph`.
2. What does it do, and which services does it read and write? It reads a git checkout and answers `analyze`, `impact`, `context`, and a read-only cypher query. It writes `<repo>/.axon/` (about 125 MB here) and a repo registry under `HOME/.axon/`. With `HOME` under `~/.cache/pfy/tools/axon/` it did not touch the login home. Once a day it GETs the PyPI JSON for `axoniq` unless the update cache is fresh. No hosted model, no API key, and no gate file.
3. What does it trigger next? Nothing. The comparison does not queue a wiring ticket.
4. Where does a human re-enter? Before any gate wiring, before treating axon as the live code-graph, and before a Feature GO. Mark stops this lane with `tmp/STOP` in the worktree or `tmp/evq/STOP`.
5. What stops two runs doing the same work? One worktree and one branch for this slug (`bot/evq-axon-1107`). The tool is not on a gate, so it cannot select the same suite twice. The stage card is per tool, so another lane does not edit it.
