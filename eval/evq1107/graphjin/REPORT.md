# GraphJin evq1107 (2026-11-07)

## Catalog tools on the same job

The job is a governed GraphQL and MCP view over files and code, with a read-only boundary, for pfy build review (gap B). Gap B is that `./pfy build` is not proven bot-usable: the 2026-11-06 trial hit the 3 hour timeout, and the recheck fix is parked after two pregate failures. The 2026-11-07 ranking says no entry from 137 to 167 closes that gap. GraphJin is Entry 104. This lane builds no pipeline, CI, or gate step.

| Tool | Stage | What it already covers | How GraphJin compares |
|------|-------|------------------------|------------------------|
| codebase-memory-mcp | I2 | Primary code-graph MCP. On the shared 10-commit window its impact agreed with test_select on 5/10 (`eval/ev1107/chiasmus/results.json`). | The pinned binary skipped the code source at startup. No symbol query ran. It does not beat the primary graph. |
| write-guard-mcp | I3 | First-party write mediation above the cage mount. | Sqlite `read_only` blocked 3/3 mutations here. That is a query-compiler veto on one throwaway database, not the cage mount. |
| Graphify | I0 | Tree-sitter graph. Agreed with test_select on 5/10. Venv 102 MB (`eval/evq1107/graphify/REPORT.md`). | No impact count. The code source did not start. |
| Tree-sitter Analyzer | I1 | Change-impact on the same window, 5/10. Venv 173 MB. | No impact count. |
| Chiasmus | I1 | Call-graph MCP. Agreed on 3/10. | No impact count. MCP stdio did answer a file list (6/6) and a blocked mutation. |
| Axon | I1 | Call-graph impact, 4/10. Venv 218 MB. | No impact count. |
| repowise | I2 | Context packing. The card says it overlaps codebase-memory. | Not a code index on this pin. |
| Sandlock | I2 | Rootless confinement of one install command. | Different boundary. |
| Sponsio | I2 | Pre-call ordering and shell text blocks. | Different boundary. |
| Bumblebee | I2 | Read-only scan of lockfiles and MCP host configs. | Different job. |
| destructive-command-guard | I2 | Denies destructive shell commands. write-guard does not see the command. | Different job. |
| `scripts/test_select.py` | in this repo | Import graph plus path strings for the suite a change runs. | GraphJin did not name a test. The code source never started. |

Batch-1 results under `eval/ev1107/` and `eval/catchup-1107/` do not contain a GraphJin measurement. The older sqlite smoke is `examples/x-intake-local/smoke_103_105.py`. This probe repeated that read-only check on nimo and added the file table, CodeSQL, production allow-list, and MCP stdio, which the entry had not run.

## Verdict

STAY I0. CodeSQL did not start: the log skipped `repo_code` before any symbol query. The file table listed 6/6 copied paths and the bytes of `data/stages/write-guard-mcp.json` matched (788/788) only when a default sqlite source was also configured. With no default database the same file query returned 0 rows and `database not found: default`. `read_only: true` blocked insert, update, and delete (3/3) with `mutations blocked: table app.notes is read-only`, and the sqlite file stayed at the two seeded rows. The control with `read_only: false` landed all 3 writes. A saved production query returned the 6 files. An ad-hoc named query was refused. MCP stdio `execute_graphql` returned the same 6 files and the same read-only mutation error. `update_current_config` was not in the tool list. The binary is 162586808 bytes, over the 50 MB I2 copy limit. Gap B is unchanged.

## Pins

Entry 104 records release v3.21.6 and the linux amd64 binary sha256. This lane re-checked both hashes.

Install root: `~/.cache/pfy/tools/graphjin/`. `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, and `TMPDIR` for every tool command were directories under that root. No global install, no sudo, no account, no model key. `agent.enabled` was false. The child environment did not receive API key variables.

- Release tag `v3.21.6`, commit `b8c6bbbafcd95c8ae99bb71eee88508b95a97414`. `graphjin version` printed that commit and GraphJin 3.21.6.
- Tarball `graphjin_3.21.6_linux_amd64.tar.gz`, 46452480 bytes. sha256 `48c9bebb2b6f6496ac5a749d293f78a40279dcc2e2675dfab4b641c79e417ebc`, the line in upstream `checksums.txt`, checked with `sha256sum`. `results.json` records that value. `probe.py` does not hash the tarball.
- Binary `graphjin`, 162586808 bytes. sha256 `e6f0fd88f99b07e8036ba7db76f24f0fceab697935559d154e823b5951f46805`, the pin in `examples/x-intake-local/smoke_103_105.py`. `probe.py` hashes this binary on each run.
- License in the tarball `LICENSE` and in `graphjin version`: Apache-2.0.
- Server-side agent, OAuth, Docker, and the `.deb` were not used.

## Commands

`$BASE` is `~/.cache/pfy/tools/graphjin`. The probe copies six files from this worktree into `$BASE/probe/score/<world>/slice/` and serves that copy. It does not write the worktree.

```bash
python3 eval/evq1107/graphjin/probe.py
```

Worlds, each a fresh sqlite file and a fresh slice copy:

- `code`: default sqlite plus `kind: code` on the slice. Stopped when the log said CodeSQL needs a cgo build.
- `files-no-db`: file source only.
- `files-ro`: default sqlite and file source, `read_only: true`, dev mode.
- `control`: same with `read_only: false`.
- `prod`: same as `files-ro` with `production: true` and `mode: prod`.
- MCP stdio on the `files-ro` config: newline JSON-RPC, `tools/list`, then `execute_graphql`.

## Numbers

Slice: `scripts/catalog_check.py`, `pfylib/stage_registry.py`, `examples/x-intake-local/smoke_103_105.py`, `data/stages/write-guard-mcp.json`, `data/stages/codebase-memory-mcp.json`, `sources/entries/104-graphjin.md`.

| Check | Result |
|---|---|
| CodeSQL | Source skipped at startup. No symbol query was sent. Log: `Database 'repo_code' connection failed: codesql requires a cgo-enabled build with bundled tree-sitter grammars. Skipping.` |
| File list, no default database | 0 rows. Error: `database not found: default` |
| File list, beside default sqlite | 6/6 keys, 6/6 sizes |
| `text` of `data/stages/write-guard-mcp.json` | 788 bytes, equal to the file on disk |
| Slice bytes after read_only serve | unchanged |
| GraphQL `repo_files` insert, read_only true | 0 new files, empty data, no read-only error |
| GraphQL `repo_files` insert, read_only false | 0 new files. The insert is not a write path |
| Sqlite read, read_only true | rows `(1, alpha)`, `(2, beta)` |
| Sqlite insert, update, delete, read_only true | 3/3 errors, `mutations blocked: table app.notes is read-only`. DB unchanged |
| Same 3 mutations, read_only false | 3/3 landed. DB ended `(1, x)`, `(3, evil)` |
| Production saved `getNotes` | 2/2 rows |
| Production saved `repoFiles` | 6 files, no error |
| Production query `adhoc` | refused, `unknown graphql query: adhoc`, 0 rows |
| Production unnamed file query | refused, `invalid query or fragment name` |
| MCP `execute_graphql` file list | 6 keys |
| MCP insert | `mutations blocked: table app.notes is read-only` |
| MCP tool `update_current_config` | absent (7 tools, no update tool) |
| Startup, each world | 0.201 to 0.202 s |
| Scored probe wall clock | 1.362 s |
| Binary size | 162586808 bytes |

The 3/3 control is what makes the read-only count mean something. Both worlds used the same mutations. Only the flag changed.

## Gates

Value gate for I3 needs 3 of 4. This probe has 2.

1. Gap fill: no. CodeSQL was skipped at startup, so it does not sit beside codebase-memory. The file list ties a directory walk and drops to 0 without a default database. The sqlite veto matches the existing smoke. Gap B, the 3 hour build timeout, did not move. No review test was named.
2. Operator leverage: no. Startup is about 0.2 s, and the code answer is a skip. A reviewer already has these six paths from the tree.
3. Evidence: yes. Offline binary, this report, `results.json`, `probe.py`.
4. Blast radius: yes on the written gate. Apache-2.0, no model weights, no account, no primary runtime. The install is a cache binary. It is over the 50 MB I2 copy limit and under multi-GB.

Modularity, all four, for a cache probe only:

1. Local code was required. The cgo skip and the `database not found: default` result are not the README's code-index example.
2. The entry point is one static binary. The unit of eval stayed `serve` and `mcp`.
3. It sat under `~/.cache/pfy/tools/graphjin/` and did not become the product runtime.
4. Deleting that directory leaves the pin, this report, and the entry.

Lightweight I2 size gate: fail. The binary is 162586808 bytes. The limit is 50 MB, and a large binary stays out of I2. The skipped code source also fails the "measurably helps" bar.

## Risks

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Release binary has no CodeSQL | Log says a cgo grammar build is required. `gj_code` is never queried. The server can still print that it started. | Do not send review questions at `gj_code` on this pin. A later ticket needs a cgo build under 50 MB before any promote. |
| File table without a default database | `repo_files` returns `database not found: default` and 0 rows. The log says no databases are configured. | Keep one default database source, or do not use the file table. |
| Sqlite path is relative to cwd | A path relative to the config dir opens an empty database and the read returns no rows. | This probe used an absolute path. Keep doing that. |
| File insert looks like a mutation | `repo_files(insert:)` returned empty data and wrote 0 files with `read_only` true and with it false. | Do not score that call as the veto. Score the sqlite error string, which the control showed is the flag. |
| Dev mode allows raw GraphQL | The same insert, update, and delete land when `read_only` is false (3/3). | Any trial sets `read_only: true` and checks the control still lands. |
| Production allow-list | An unnamed query and a named `adhoc` query were refused. The saved `getNotes` and `repoFiles` queries ran. | Ship the saved query files with the config. Do not send ad-hoc text in prod. |
| MCP config edit | `update_current_config` was not listed, so this probe did not try to flip `read_only` at runtime. | Leave `allow_config_updates` false. Do not claim the tamper test passed. |
| `/health` while the engine is down | A process can log `GraphJin started` before queries work. The code world was stopped on the cgo line. | Ready means a GraphQL response, which is what `probe.py` waits for. |
| Big binary | 162586808 bytes, plus the 46452480 byte tarball in the cache. | Keep one pinned copy under the cache. Do not commit it. |
| Server-side agent | It needs a provider key and was not part of this probe. | `agent.enabled: false`. No key in the child environment. |

## Next gate

Stay I0. Do not copy the binary into the repo. A later pin has to be a cgo grammar build under 50 MB, return the functions in this six-file slice, and beat codebase-memory on a review count. Gate wiring is a separate ticket. No Feature GO.

## Five questions (if this tool were in the pipeline)

1. What triggers it? Nothing after this trial. A person would have to ask for a read-only query over a sqlite file or a file tree. Pregate and CI do not call it. `scripts/pfy_build_cloud.py` still prefers codebase-memory, then Tree-sitter Analyzer, then git grep.
2. What does it do, and which services does it read and write? `graphjin serve` reads `dev.yml`, a sqlite file, and a local directory, and serves GraphQL on `127.0.0.1`. `graphjin mcp` speaks stdio JSON-RPC to that same config. With `HOME` under `~/.cache/pfy/tools/graphjin/` it did not use a login config. No hosted model and no gate file. The server-side agent was off.
3. What does it trigger next? Nothing. The comparison does not queue a wiring ticket.
4. Where does a human re-enter? Before any cgo rebuild, before any edit to a review prompt, and before any gate wiring. Mark stops a lane with `tmp/STOP` in the worktree or `tmp/evq/STOP`.
5. What stops two runs doing the same work? One worktree and one branch for this slug. The tool is not on a gate, so it cannot select the same suite twice. The stage card is per tool, so another lane does not edit it.
