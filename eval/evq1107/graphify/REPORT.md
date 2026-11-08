# Graphify evq1107 (2026-11-07)

## Catalog tools on the same job

The job is a local tree-sitter graph for pfy build review (gap B). Gap B is that `./pfy build` is not proven bot-usable: the 2026-11-06 trial hit the 3 hour timeout, and the recheck fix is parked after two pregate failures. The 2026-11-07 ranking says no entry from 137 to 167 closes that gap. Graphify is Entry 017, already on the card as a reference graph. This lane builds no pipeline, CI, or gate step.

| Tool | Stage | What it already covers | How Graphify compares |
|------|-------|------------------------|------------------------|
| codebase-memory-mcp | I2 | Primary code-graph. On this 10-commit window its impact agreed with test_select on 5/10 (`eval/ev1107/chiasmus/results.json`). | This probe also agreed on 5/10. The scored set is the test files in the diff. It did not beat the primary graph. |
| Tree-sitter Analyzer | I1 | Change-impact on the same window, 5/10 (`eval/evq1107/tree-sitter-analyzer/REPORT.md`). Venv 173 MB. | Same 5/10. TSA named the importing test on the affected rows. `graphify affected` on the changed script printed no nodes. |
| Chiasmus | I1 | Tree-sitter call graph. Agreed on 3/10. Bare Python names inflated callers (`main` in 157 files). Install 86 MB. | Agreed on 5/10 and added 0 tests outside test_select. It still does not beat codebase-memory. |
| repowise | I2 | Context packing. The card says it overlaps codebase-memory. | Not a change-impact CLI. |
| LEANN | I1 | Compressed RAG. The card says it is not our code memory. | Different job. |
| Chroma or LanceDB | I0 | Vector store. The card says code memory is already chosen. | Different job. |
| opencode-mem | card uses | Memory plugin for the OpenCode worker. | Different surface. |
| mempalace, memvid | card uses | Local memory stores. | Different job. |
| `scripts/test_select.py` | in this repo | Import graph plus path strings. Mode full on risky, core, or unknown paths. | The selector stays the source of the 10-commit score. |
| `scripts/pfy_build_cloud.py` | in this repo | Review prompt uses codebase-memory, then Tree-sitter Analyzer, then git grep. | Graphify is not in that order. This lane does not add it. |

Batch-1 results under `eval/ev1107/` and `eval/catchup-1107/` do not add another Graphify measurement. Chiasmus and Tree-sitter Analyzer already scored this window.

## Verdict

STAY I0. `graphify affected` plus the test files in the diff agreed with `scripts/test_select.py` on 5/10 commits. codebase-memory agreed on 5/10. Chiasmus agreed on 3/10. On every commit the Graphify set was exactly the changed `tests/test_*.py` files. The walk added 0 tests. `affected` on `scripts/grill_ticket.py`, `scripts/pipeline_retro.py`, and `scripts/catalog_check.py` printed `No affected nodes found.` The venv allocates 102 MB (`du -sh`) and 217390438 bytes (`du -sb`), over the 50 MB I2 copy limit. Gap B is unchanged.

## Pins

Entry 017 in `sources/x-posts.md` records the GitHub repo and no commit, tag, or checksum. This lane pinned the PyPI release that matches GitHub tag `v0.9.104`.

Install root: `~/.cache/pfy/tools/graphify/`. `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, and `TMPDIR` for every tool command were directories under that root. No global install. `graphify install` was not run. Login-home `~/.graphify`, `~/.cache/graphify`, `~/.config/graphify`, and `~/.local/share/graphify` were absent before and after.

- Python 3.11.15 venv. The worktree `python3` is 3.14 and was not the venv.
- PyPI `graphifyy==0.9.104`. The CLI name is `graphify`. Tag `v0.9.104` is commit `433a57a002908e74c9f0abd2ad93af8b302b71c4` (GitHub tags API on this run).
- Wheel `graphifyy-0.9.104-py3-none-any.whl`, 1894506 bytes. sha256 `ecc5f436a44c4e776aa88e96acd0d5f26f9e3f680f1d1a010ca06547a78fbd55` matches the PyPI digest.
- `graphify --version` printed `graphify 0.9.104`.
- `du -sh` on the venv is 102M. `du -sb` is 217390438 bytes. Pip cache `du -sh` is 36M (`du -sb` 32226053). The venv is over 50 MB.
- License on the wheel metadata: Apache-2.0.
- `graphify prs` and `graphify prs --triage` were skipped. The docs require `gh` auth, and triage wants a model backend. No key was passed. `GRAPHIFY_BACKEND=none`.

## Commands

`$BASE` is `~/.cache/pfy/tools/graphify`. The probe repo is a `git clone --shared --no-checkout` of this worktree into `$BASE/probe/repo`. That does not register a worktree on the shared git dir. Graphs were written under `$BASE/probe/graphs/<sha>/graphify-out/`.

```bash
/home/mark/.local/bin/python3.11 -m venv "$BASE/venv"
"$BASE/venv/bin/pip" install "$BASE/src/graphifyy-0.9.104-py3-none-any.whl"
python3 eval/evq1107/graphify/probe.py
```

Extract, per commit, code only, no cluster, no model:

```bash
graphify extract "$BASE/probe/repo" --code-only --no-cluster --force --out "$BASE/probe/graphs/<sha>"
```

The score loads that `graph.json` once and calls the same `format_affected` the `affected` command prints (depth 2, default relations). Three CLI checks are stored in `results.json` under `cli_affected`:

```bash
graphify affected scripts/grill_ticket.py --depth 2 --graph "$BASE/probe/graphs/56f6df154eeebf29be90c6290a0a28a917e5d4bb/graphify-out/graph.json"
graphify affected scripts/pipeline_retro.py --depth 2 --graph "$BASE/probe/graphs/31c373ba1c77588f0bdbb875383d7185ca3be3cb/graphify-out/graph.json"
graphify affected scripts/catalog_check.py --depth 2 --graph "$BASE/probe/graphs/79c083e9e53a4302ed30188d40fc29d445140ab6/graphify-out/graph.json"
```

Each printed `No affected nodes found.` and exited 0.

`scripts/test_select.py --root` was the checked-out commit, so the import graph is that tree. Agreement is set equality of `tests/test_*.py` paths. The Graphify set is the tests `affected` returned, plus any changed test file. That second part is the same inclusion `scripts/cbm_shadow.py` gives `changed_files`.

## Numbers

Window: the same 10 first-parent commits as `eval/ev1107/chiasmus/results.json` (origin/main at `9d3688718e96`). test_select counts below are from this run on each archived tree. They match the chiasmus trial's counts (181, 180, 176 on the full rows). codebase-memory and chiasmus agree flags are copied from that trial.

| sha | mode | test_select | cbm | chiasmus | graphify | added | agree |
|---|---|---:|---:|---:|---:|---:|---|
| 9d3688718e96 | structural | 0 | 0 | 0 | 0 | 0 | yes |
| 1868e5d1b2c5 | full | 181 | 0 | 0 | 0 | 0 | no |
| 914b11c8a2c2 | full | 181 | 2 | 145 | 2 | 0 | no |
| 9bfc82fcf66c | full | 180 | 8 | 173 | 8 | 0 | no |
| 25e488764894 | affected | 1 | 1 | 1 | 1 | 0 | yes |
| 56f6df154eee | affected | 1 | 1 | 139 | 1 | 0 | yes |
| ba18f7cc7947 | structural | 0 | 0 | 0 | 0 | 0 | yes |
| 31c373ba1c77 | affected | 1 | 1 | 19 | 1 | 0 | yes |
| dd861e01cc8b | full | 176 | 1 | 170 | 1 | 0 | no |
| 79c083e9e53a | affected | 3 | 2 | 39 | 2 | 0 | no |

Agreement: Graphify 5/10. codebase-memory 5/10. Chiasmus 3/10. `added` is tests the walk returned that were not already changed test files. It is 0 on all 10.

`56f6df154eee` changes `scripts/grill_ticket.py` and `tests/test_grill_ticket.py`. The test runs the script through a path (`REPO / "scripts" / "grill_ticket.py"`). It does not import the module. The code-only graph has no edge from that test to the script. test_select names the test because the test file changed and because the path string is in the file. Graphify names it because the test file changed.

`31c373ba1c77` is the same shape for `scripts/pipeline_retro.py` and `tests/test_pipeline_retro.py`.

`79c083e9e53a` is the affected miss from the chiasmus report. test_select names 3 tests, including `tests/test_catalog_entry_numbers.py`, because that file references `scripts/catalog_check.py`. codebase-memory omits that file. Graphify omits it too. The two it names are the test files in the diff. Chiasmus named 39.

`1868e5d1b2c5` has no Python hunks. test_select is full (181) because unknown files force the whole suite. Graphify, codebase-memory, and chiasmus return no tests.

On the four full rows, Graphify returns 0, 2, 8, and 1 tests. Those counts match codebase-memory and match the changed test files. `only_graphify` is 0 on all 10 commits.

Newest commit in the window, `9d3688718e96`, code-only graph: 9867 nodes, 24329 edges, 8857341 bytes. Confidence: EXTRACTED 23723, INFERRED 606, AMBIGUOUS 0. INFERRED is 2.5% of edges. Top relations: calls 10557, contains 4732, method 2541, imports 2418, references 1304, rationale_for 1245.

Wall clock for the 10 extracts, checkouts, scores, and the three CLI checks: 92.671 s. Each extract was 7.580 to 8.115 s. Each affected batch was under 0.5 s.

## Gates

Value gate for I3 needs 3 of 4. This probe has 2.

1. Gap fill: no. codebase-memory is already at 5/10 on this window, and test_select stays the selector. Graphify ties the first. The walk did not find `tests/test_catalog_entry_numbers.py` or any test the diff did not already list. Gap B, the 3 hour build timeout, did not move.
2. Operator leverage: no. Extract is about 8 seconds and the CLI returns immediately, and the answer on a changed script is empty. A reviewer already has the changed test paths from `git diff`.
3. Evidence: yes. Offline venv, this report, `results.json`.
4. Blast radius: yes on the written gate. Apache-2.0, no model weights, no account, no primary runtime. The install is a cache venv. It is over the 50 MB I2 copy limit and under multi-GB.

Modularity, all four, for a cache probe only:

1. Local code was required. The empty `affected` result on `scripts/grill_ticket.py` is not in the README's FastAPI example.
2. The CLI entry point is one wheel. The dependency set is the tree-sitter grammars plus networkx and numpy. The unit of eval stayed `extract` and `affected`.
3. It sat under `~/.cache/pfy/tools/graphify/` and did not become the product runtime.
4. Deleting that directory leaves the pin, this report, and the entry.

Lightweight I2 size gate: fail. The venv allocates 102 MB. The limit is 50 MB. I2 is not open on size, and the tie with codebase-memory also fails the "measurably helps" bar.

## Risks

| Risk | How it fails | Recovery |
|------|----------------|----------|
| File seed has no incoming test edge | `graphify affected scripts/grill_ticket.py` prints `No affected nodes found` while the test names that path in a string and runs it as a subprocess. | Keep test_select. Do not replace it with `affected`. |
| Changed-test inclusion | The 5/10 counts the test files in the diff. Removing that inclusion leaves the two empty structural commits, 2/10. | Quote `affected_added_tests` in `results.json`. It is 0. |
| Full or unknown paths | test_select runs 181 tests. The graph returns the handful of test files in the diff, or none. | Do not replace the selector. Core, risky, and unknown rules stay in test_select. |
| `graphify prs` | The review queue needs `gh` auth. `--triage` needs a model backend. | Leave it skipped. No key, no account. |
| `graphify install` | It copies skills and hooks into assistant config dirs. | Do not run it in a lane. The cache HOME stayed empty of those installs. |
| INFERRED tags read as a second resolver | 606 of 24329 edges are INFERRED and 0 are AMBIGUOUS. The missing test link is still missing. | Quote the edge counts. Do not promote on the tag names. |
| Pin drift | PyPI moved through many 0.9.x releases. This wheel will not match a later README. | Stay on 0.9.104 until a new ticket repins and repeats the 10 commits. |
| Graph written into a real checkout | Default extract writes `graphify-out/` in the tree. | This probe used `--out` under the cache. Do not extract in the founder checkout. |

## Next gate

Stay I0. Do not copy the venv into the repo. A later pin has to allocate under 50 MB and either agree with test_select on more than 5 of these 10 commits, or have `graphify affected` name `tests/test_catalog_entry_numbers.py` for `79c083e9e53a`. Gate wiring is a separate ticket. No Feature GO.

## Five questions (if this tool were in the pipeline)

1. What triggers it? A person asking for a per-file blast radius, or a future review prompt. Nothing in pregate or CI calls it after this trial. `scripts/pfy_build_cloud.py` still prefers codebase-memory, then Tree-sitter Analyzer, then git grep.
2. What does it do, and which services does it read and write? `graphify extract --code-only` reads a git checkout and writes `graphify-out/graph.json`. `graphify affected` reads that file and prints nodes. With `HOME` under `~/.cache/pfy/tools/graphify/` it did not touch the login home. No hosted model and no gate file. `graphify prs` would read GitHub through `gh` and was not run.
3. What does it trigger next? Nothing. The comparison does not queue a wiring ticket.
4. Where does a human re-enter? Before any edit to `pfy_build_cloud.py`, and before any gate wiring. Mark stops a lane with `tmp/STOP` in the worktree or `tmp/evq/STOP`.
5. What stops two runs doing the same work? One worktree and one branch for this slug. The tool is not on a gate, so it cannot select the same suite twice. The stage card is per tool, so another lane does not edit it.
