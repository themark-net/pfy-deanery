# OpenLore evq1107 (2026-11-07)

## Catalog tools on the same job

The job is deterministic code memory plus a breaking-change label for pfy build review (gap B). Gap B is that `./pfy build` is not proven bot-usable: the 2026-11-06 trial hit the 3 hour timeout. The 2026-11-07 ranking says no entry from 137 to 167 closes that gap. OpenLore is entry 129. This lane builds no pipeline, CI, or gate step.

| Tool | Stage | What it already covers | How OpenLore compares |
|------|-------|------------------------|------------------------|
| codebase-memory-mcp | I2 | Primary code-graph. On the chiasmus 10 commits its impact agreed with test_select on 5/10. | This probe did not rescore those 10 commits as a test selector. On one planted file, blast-radius named the same 3 tests as test_select. It does not replace the primary graph. |
| Tree-sitter Analyzer | I1 | Change-impact agreed on 5/10. Venv 173 MB. | Same review slot. OpenLore adds an export label. Tree-sitter Analyzer does not emit one. The prefix here is 708 MB. |
| Chiasmus | I1 | Call-graph impact agreed on 3/10. Install 86 MB. | Same slot. OpenLore does not beat the 5/10 graph. |
| Graphify | I0 | Reference tree-sitter graph. Not the code memory we run. | Same slot, not measured here. |
| repowise | I2 | Context packing. The card says it overlaps codebase-memory. | Not a breaking-change CLI. |
| LEANN | I1 | Compressed RAG. Not our code memory. | Different job. |
| Chroma (or LanceDB) | I0 | Vector store. The card is tagged code-memory. | OpenLore vendors LanceDB for optional embeddings. This probe stayed on the keyword index. |
| opencode-mem | I1 | Memory plugin for the OpenCode worker. | Session memory, not a diff classifier. |
| MemPalace | I0 | Verbatim local memory. | Different job. |
| `scripts/test_select.py` | in this repo | Import graph plus path mentions. | On `pfylib/stage_registry.py` both named the same 3 tests. The selector stays the suite source. |

Batch-1 results under `eval/ev1107/` and `eval/catchup-1107/` do not add another breaking-change measurement. Chiasmus is the call-graph score on this window. catchup-1107 holds strata, skill-up, and skillspector.

OpenLore does not beat what we have. The new piece is the module-level export label. The code-memory half did not beat codebase-memory, and the one measured test list tied test_select.

## Verdict

STAY I1. Planted module-level checks passed 4/4 and named 7/7 in-repo consumers of `load_stages`. The same 10 commits as `eval/ev1107/chiasmus/results.json` had 0 module-level signature breaks and 0 false breaking verdicts. A required parameter on the indented method `PhaseClock.phase` produced 0 changes and overall `non-breaking`. The prefix allocates 708 MB, over the 50 MB I2 copy limit. Gap B is unchanged.

## Pins

Install root: `/home/mark/.cache/pfy/tools/openlore/`. Every tool command used `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, and `TMPDIR` under that root. `OPENLORE_NO_UPDATE_NOTIFIER=1`, `OPENLORE_TELEMETRY=0`, `OPENLORE_NO_AUTO_HEAP=1`. No global install. Login paths `/home/mark/.openlore` and `/home/mark/.pi/agent/extensions` were absent before and after. The redirected home directory was empty at the end.

- npm `openlore@3.3.1`. Lock integrity `sha512-iDg86/Vt+hxSUgBek1Dh2sG0D+DGSyXqD9OGjerko2nf2mHCcyccCC2hiWsEDg1lnP6cScJ4P6Yya/Ef6nrd7g==`. Resolved `https://registry.npmjs.org/openlore/-/openlore-3.3.1.tgz`. That integrity matches `npm view openlore@3.3.1 dist.integrity` on this run.
- Annotated tag `v3.3.1` peels to commit `f33d3b2fbcd34380dfcb5925d966eccd080c2383` (2026-10-10, `chore(release): 3.3.1`). The npm metadata view did not include `gitHead`.
- `engines.node` is `^22.19.0 || >=23.5.0`. This host's `/usr/bin/node` is v22.23.0. `openlore --version` printed `3.3.1`.
- License on the package metadata: MIT.
- `npm install --prefix <cache>/prefix --ignore-scripts --no-audit --no-fund openlore@3.3.1` added 324 packages. The lockfile `packages` object has 396 entries. Peer warnings for optional tree-sitter grammars did not stop the Python index.
- The first install expanded `~` after `HOME` had moved, so the tree landed under the redirected home. It was moved to `/home/mark/.cache/pfy/tools/openlore/prefix`. Nothing was left in the redirected home.
- Prefix `du -sh` is 708M. `du -sb` is 1673767825 bytes. npm cache `du -sh` is 487M (`du -sb` 614205073). Both are over 50 MB.
- Flags that stayed off: `install`, `connect`, `setup`, `--embed`, `--accept`, `--install-hook`.

## Commands

`$BASE` is `/home/mark/.cache/pfy/tools/openlore`. The probe repo is a `git clone --shared` of this worktree at HEAD `e7d45466c3cdf8b7ed92ead08f0b2fe985285cd7` into `$BASE/probe/repo`. That clone has its own HEAD. `init` ran only there.

```bash
npm install --prefix "$BASE/prefix" --ignore-scripts --no-audit --no-fund openlore@3.3.1
python3 eval/evq1107/openlore/probe.py
```

The probe runs, with the env above:

```bash
node dist/cli/index.js -q init
node dist/cli/index.js analyze --no-embed --force
node dist/cli/index.js orient --json --limit 5 --task <phrase>
node dist/cli/index.js certify-public-surface --base HEAD --json
node dist/cli/index.js blast-radius --base HEAD --json
```

Historical rows checkout the commit, then `git reset --mixed` to its parent, so the commit is an unstaged diff. `certify-public-surface` reads that worktree. The clone is reset back to HEAD between rows. `scripts/test_select.py --paths pfylib/stage_registry.py` runs on this worktree, which is the same file at the same HEAD.

## Numbers

Analyze wall time 12.195s, exit 0. The tool's own total was 11.8s. `init` 0.257s. Clone 0.137s.

Index line: keyword plus vocabulary, 2915 call-graph functions, 2429 test functions, 1683 signature-only symbols, 7027 indexed repo symbols. Vocabulary partial, 53666 candidate inputs omitted. Text line index 257831 lines across 2483 files. `.openlore` after the run is 13M allocated (`du -sh`) and 93545740 bytes apparent (`du -sb`).

### Orient

Phrases reuse words from the function's docstring and do not contain the symbol name. Top 5 is the recorded hit. First place is listed beside it.

| Symbol | Name query, first | Name in top 5 | Name seconds | Phrase, first | Phrase in top 5 | Phrase seconds |
|--------|-------------------|---------------|-------------:|---------------|-----------------|----------------|
| load_stages | load_integration_stages | yes (2nd) | 0.765 | test_validate_rejects_monolith_and_bad_cards | yes (2nd) | 0.769 |
| write_tool | write_tool | yes (1st) | 0.766 | test_write_tool_touches_exactly_one_file | yes (2nd) | 0.763 |
| pipeline_role_hits | pipeline_role_hits | yes (1st) | 0.774 | pipeline_role_hits | yes (1st) | 0.813 |

Name queries 3/3 in the top 5, 2/3 in first place. Phrase queries 3/3 in the top 5, 1/3 in first place. A docstring phrase is a weak stand-in for a task, and first place still missed twice.

### Planted contract on this repo

Edits are unstaged on the shared clone of HEAD. Ground truth is an ast of column-0 public `def` and `class` names, tests excluded, matching the tool's export rule (a name that does not start with `_`).

| Case | Expectation | Overall | Seconds | Result |
|------|-------------|---------|--------:|--------|
| `load_stages` gains required `lane` | breaking | breaking | 0.672 | reason `required parameter "lane" was added`, bump major |
| `load_stages` gains `lane: str = ""` | non-breaking | non-breaking | 0.618 | optional trailing parameter, bump patch |
| docstring sentence extended | non-breaking | non-breaking | 0.902 | 0 changes |
| `load_stages` renamed to `_load_stages` | breaking | breaking | 0.614 | rule `export-removed`, bump major |
| `PhaseClock.phase` gains required `lane` | recorded, not a contract pass | non-breaking | 0.627 | 0 changes |

Contract score 4/4. The required-parameter row and the removal row each listed 7 consumers, `consumersTruncated` 0:

- `main` in `pfylib/stage_registry.py`
- `main` in `scripts/catalog_check.py`
- `load` in `scripts/catalog_stage_eval.py`
- `scripts/pfy_catalog_ask_queue_209.py`
- `tests/test_catalog_stage_eval.py`
- `tests/test_stage_registry.py`
- `tests/test_voice_stage0_ref.py`

That is the full caller set found by search in this worktree. The method row is the miss: an indented public method is outside the column-0 export scan, so a required parameter there is invisible.

A clean worktree certify was overall `non-breaking` with all three counts at 0, and `suggestedBump` still `patch`. The docstring row did the same.

### Blast radius versus test_select

On the required-parameter edit of `pfylib/stage_registry.py`:

| Source | Seconds | Tests |
|--------|--------:|-------|
| `blast-radius --base HEAD --json` | 0.982 | `tests/test_catalog_stage_eval.py`, `tests/test_stage_registry.py`, `tests/test_voice_stage0_ref.py` |
| `scripts/test_select.py --paths pfylib/stage_registry.py` | 1.092 | the same three modules, mode `affected`, reason `import graph selected 3 module(s)` |

Set equality holds on this one file. It is not a 10-commit score, and it does not move the 5/10 codebase-memory number.

### Historical window

Same 10 first-parent commits as the chiasmus trial. Ast ground truth found 0 module-level signature breaks (no removed public name, no new required parameter, no parameter removed). A pass over the 60 most recent first-parent commits, skipping these 10, found no further ast break, so the real-history catch count is 0/0. Strict means exit 0 and overall `breaking` or `non-breaking`, with `breaking` exactly when ast says so. `potentially-breaking` does not count as strict. Every row here is strict.

| sha | py files (tests omitted) | ast break | overall | non-breaking count | seconds |
|-----|--------------------------|-----------|---------|-------------------:|--------:|
| 56f6df154eee | 1 | no | non-breaking | 17 | 0.672 |
| 9d3688718e96 | 0 | no | non-breaking | 0 | 0.480 |
| 1868e5d1b2c5 | 0 | no | non-breaking | 0 | 0.520 |
| 914b11c8a2c2 | 1 | no | non-breaking | 25 | 0.655 |
| 9bfc82fcf66c | 7 | no | non-breaking | 4 | 2.593 |
| 25e488764894 | 0 | no | non-breaking | 0 | 0.533 |
| ba18f7cc7947 | 0 | no | non-breaking | 0 | 0.488 |
| 31c373ba1c77 | 1 | no | non-breaking | 0 | 0.870 |
| dd861e01cc8b | 1 | no | non-breaking | 22 | 0.721 |
| 79c083e9e53a | 1 | no | non-breaking | 2 | 0.642 |

False breaking verdicts: 0/10. The large non-breaking counts sit on commits that add a Python file (`scripts/grill_ticket.py`, `scripts/cbm_shadow.py`, `scripts/pipeline_retro.py`). A new export is non-breaking under the tool's rule. `9bfc82fcf66c` and `79c083e9e53a` edit existing modules and stayed non-breaking, which matches the ast.

## Gates

Value gate for I3 needs 3 of 4. This probe has 2.

1. Gap fill: no. Code memory is already codebase-memory at 5/10 on this window. The one blast-radius list tied test_select. The export label is new and passed 4/4 on column-0 defs, and it missed the method break. Gap B, the 3 hour build timeout, did not move.
2. Operator leverage: no. Certify is under a second after a 12 second index, and a 708 MB install for a label that misses methods does not improve the build lane.
3. Evidence: yes. Offline prefix, this report, `results.json`. No API key and no embed download.
4. Blast radius: yes on the written gate. MIT, no account, no model weights downloaded, no primary runtime. The I2 size gate is separate and fails.

Modularity, all four, for a cache probe only:

1. Local code was required. The method miss and the first-place orient misses are not in the entry's TypeScript fixture.
2. The CLI entry point is one package. The unit of eval stayed that CLI. The install is 324 packages.
3. It sat under `~/.cache/pfy/tools/openlore/` and did not become the product runtime.
4. Deleting that directory leaves the pin, this report, and the entry.

Lightweight I2 size gate: fail. The prefix allocates 708 MB. The limit is 50 MB. I2 is not open. The label's 4/4 does not clear that limit.

## Risks

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Indented methods | `PhaseClock.phase` gained a required parameter. Overall stayed `non-breaking` with 0 changes. | Keep the label off class APIs until a pin flags that edit. Module-level defs can use it as a report. |
| Default embed | `analyze` defaults `--embed` on. The local model downloads into `HOME/.openlore/models`. | Pass `--no-embed`. Keep `HOME` under the cache. |
| Heap re-exec | Without `OPENLORE_NO_AUTO_HEAP`, analyze sizes the heap to 75 percent of host RAM. A help-path print on this box named 82500 MB. | Set `OPENLORE_NO_AUTO_HEAP=1`. This repo indexed in 12s at the default heap. |
| `init` writes the tree | It edits `.gitignore` and creates `openspec/`. | Run it only in the cache clone. Do not run `install`, `connect`, or `setup`. |
| `analyze` exit code | The entry records exit 0 when the index is unusable and orient then says no analysis was found. | Read orient and the index line. This run's orient returned functions. |
| Empty diff bump | A clean tree and a docstring-only edit still set `suggestedBump` to `patch` with every count at 0. | Read the three counts. A bump with all zeros is not a change. |
| Update check | The package checks the registry unless `OPENLORE_NO_UPDATE_NOTIFIER=1`. | Set that flag. Telemetry stays off unless `OPENLORE_TELEMETRY=1`. |
| Size | 708 MB allocated, 1.56 GB apparent, plus a 487 MB npm cache. | Leave it in the cache. Do not copy it into the repo. |
| Shared clone | The probe clone borrows objects from this worktree. | Delete `$BASE/probe`. Do not commit `.openlore/`. |

## Next gate

Stay I1. Do not copy the prefix into the repo. A later pin has to allocate under 50 MB, flag the required parameter on `PhaseClock.phase`, and still name the seven `load_stages` consumers. Gate wiring is a separate ticket. No Feature GO.

## Five questions (if this tool were in the pipeline)

1. What triggers it? A person asking whether a working-tree diff breaks a module-level export. Nothing in pregate or CI calls it after this trial.
2. What does it do, and which services does it read and write? It reads a git checkout and answers `certify-public-surface`, `orient`, or `blast-radius`. `init` writes `.openlore/` and edits `.gitignore` in that checkout. With `HOME` under the cache it did not touch the login home. No hosted model and no gate file.
3. What does it trigger next? Nothing. The comparison does not queue a wiring ticket.
4. Where does a human re-enter? A gate that trusted the label would be a separate ticket with a grill step. This lane does not ask for a GO.
5. What stops two runs doing the same work? One cache prefix and one clone per machine. Upstream analyze is single-flight per repository. This lane does not start a second copy.
