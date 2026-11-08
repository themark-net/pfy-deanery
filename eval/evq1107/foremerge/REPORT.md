# Foremerge evq1107

STAY I1. Same-path modify, the pattern that parks a rebase, was blocking on 0/6 and a MEDIUM shared_contract on 6/6. Median check was 6.2 ms. A same-line git merge of `pfylib/stage_registry.py` conflicted. A different-region merge of that file was clean. The file=modify check did not tell those two apart. Nothing was wired.

## Catalog tools on this job

Searched `data/stages/*.json` uses, features, and tags, plus the 2026-11-07 section of `docs/eval/TOOLSET-RANKING.md`. Batch-1 notes are under `eval/ev1107/` and `eval/catchup-1107/`. No card already does a pre-edit semantic scope ledger.

| Tool | Stage | What it covers | How foremerge compares |
| --- | --- | --- | --- |
| gitai | I0 | CAS lands for many agents on one branch. The card names our fast-forward races. | Closest land-time tool. Not installed, not run here. It acts when a change lands. Foremerge acts on a declared scope before a write, and it does not land anything. |
| kanbots | I1 | Kanban that fans out to many coding CLIs in worktrees. Tags include worktree and parallel. | Isolation by worktree. No scope check. |
| Emdash | I0 | Parallel agents GUI, one worktree each. | Same shape, no detector. |
| Multica | I1 | Multi-agent board. Not our orchestrator. | No scope ledger. |
| Auto-Company | I1 | Company-daemon patterns, a consensus baton, a pre-mortem gate. | Not a git scope check. |
| atomic-task-graph | I2 | Compile, parallel tool waves, freeze, localized repair. | A freeze is a scheduler lock. It does not compare two declared scopes. |
| write-guard-mcp | I3 | First-party write mediation above the cage mount. | Allows or denies one write. It does not compare two agents. |
| agent-cage | I3 | Isolated lab for Grok. | Sandbox. Not a cross-lane ledger. |
| codebase-memory-mcp | I2 | Primary code graph. | Impact after the code exists. |
| Chiasmus | I1 | Call-graph impact for per-file review. Its probe agrees with test_select on 3/10 commits. | After a diff. Not a pre-edit intent. |
| Elephant-Goldfish Model | I1 | Fresh-eyes spec review before Build. Its probe missed the lock-wait and the fast-forward parks. | Adjacent to gap B. Not an intent ledger. |

The 2026-11-07 ranking says no entry in 137 to 167 closes gap B. Foremerge is entry 097. It does not close that gap either.

What we already do: one worktree and one stage card per lane, and a static list of shared files lanes must not co-edit (`Makefile`, `AGENTS.md`, `docs/eval/TOOLSET-RANKING.md`, `data/stages/_registry.json`, `scripts/pregate.sh`, `scripts/test_select.py`, `run_tests.py`, `scripts/test_cache.py`, `.github`). Two stage-card paths (`data/stages/foremerge.json` and `data/stages/hiroute.json`) were quiet. Git sees a content conflict only after both sides have written.

Foremerge does not beat that. It is the only cataloged tool that compares declared scopes before a write. On the edit our lanes actually make (`modify`), that comparison does not block, and it fires the same warning when git can merge the two regions cleanly.

## Pins

Entry records release v0.5.1 (2026-10-03). The annotated tag object is `10ed5474b83e3c8261fc42afca5bfa5612472910`. The commit is `0fdeb6629379a5f644590bdbcb923f84e215a1c4`. Unpacked under `~/.cache/pfy/tools/foremerge/`. No `install.sh`. No `foremerge setup`. No npm install.

| File | sha256 | bytes |
| --- | --- | --- |
| `foremerge-v0.5.1-x86_64-unknown-linux-gnu.tar.gz` | `9263599abd66a5a97b2222f3010b995f780ead892f26d02a3a2b61d44d5526e3` | 10528077 |
| sidecar `.sha256` | same digest | |
| unpacked `foremerge` | `51455569f46f87e11ba33a2c5ca88c8248cdaea1ff15a67d496263a56fa3f988` | 12736504 |

`sha256sum -c` on the sidecar matched. `foremerge --version` printed `foremerge 0.5.1`. The archive is 10.5 MB and the binary is 12.7 MB, under the 50 MB copy limit. Nothing from the install is committed. `~/.local/bin/foremerge` and `~/.local/bin/fmg` were absent after the run. The real git common dir (`/home/mark/DEVELOP/pfy-mentat/.git`) has no `foremerge` directory. The probe refuses to use that directory.

Trial `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `npm_config_cache`, and `TMPDIR` point under `~/.cache/pfy/tools/foremerge/`. No model, no key, no account.

## Commands

```bash
BASE=/home/mark/.cache/pfy/tools/foremerge
mkdir -p "$BASE"/{home,config,cache,tmp,dl,unpack}
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/config" XDG_CACHE_HOME="$BASE/cache"
export npm_config_cache="$BASE/cache/npm" TMPDIR="$BASE/tmp"
curl -fsSL -o "$BASE/dl/foremerge-v0.5.1-x86_64-unknown-linux-gnu.tar.gz" \
  https://github.com/naw103/foremerge/releases/download/v0.5.1/foremerge-v0.5.1-x86_64-unknown-linux-gnu.tar.gz
curl -fsSL -o "$BASE/dl/foremerge-v0.5.1-x86_64-unknown-linux-gnu.tar.gz.sha256" \
  https://github.com/naw103/foremerge/releases/download/v0.5.1/foremerge-v0.5.1-x86_64-unknown-linux-gnu.tar.gz.sha256
sha256sum -c "$BASE/dl/foremerge-v0.5.1-x86_64-unknown-linux-gnu.tar.gz.sha256"
tar -xzf "$BASE/dl/foremerge-v0.5.1-x86_64-unknown-linux-gnu.tar.gz" -C "$BASE/unpack"
export PFY_FOREMERGE_CACHE="$BASE" FOREMERGE_BIN="$BASE/unpack/foremerge"
python3 eval/evq1107/foremerge/probe.py
```

The probe builds throwaway git repos under the cache tmp. It does not run `setup`, `mcp`, or `daemon`. Ledger overrides for the matrix stay inside each throwaway. The worktree pair uses the default ledger in that pair's git common dir. A token file is created there. This report does not read it and does not record the value.

## Numbers

Recorded run of `probe.py`: 1.26 s wall, 20 cases. Check time min 5.47 ms, median 6.2 ms, max 7.85 ms. Per-case rows are in `results.json`.

| Group | Result |
| --- | --- |
| Destructive or dual replace (`load_stages`, `write_tool`, `Makefile`, `pipeline_role_hits`) | blocking HIGH 4/4. Rules FM-C001 or FM-C002. |
| Same path, both `modify` (Makefile, AGENTS.md, TOOLSET-RANKING.md, `_registry.json`, pregate.sh, symbol `load_stages`) | blocking 0/6. MEDIUM `shared_contract` (FM-C003) 6/6. |
| Disjoint long paths and distinct symbols, including the two stage cards | quiet 6/6. |
| Short tokens `a.py`/`b.py` and `docs/a.md`/`docs/b.md` | MEDIUM `shared_contract` 2/2, not blocking. The explanation says the paths overlap on semantic scope tokens. |

An omitted operation on `Makefile` against `file:Makefile=replace` was MEDIUM, not HIGH. The tool inferred `add` and capped the finding below HIGH. `symbol:Makefile=replace` against `file:Makefile=extend` was MEDIUM across scope kinds, not blocking.

Worktree pair, no database override: init 18.73 ms, check 11.69 ms, one HIGH `destructive_vs_additive`, `blocking` true, `shared_across_worktrees` true. Database and runtime dir stayed under the throwaway.

Git baseline on a copy of `pfylib/stage_registry.py`:

| Edit | git merge | foremerge `file:pfylib/stage_registry.py=modify` both sides |
| --- | --- | --- |
| Both sides change the `load_stages` line | conflict, return code 1, 3.52 ms | not run on the git repo; the declaration check is below |
| One side changes that line, the other appends a tail note | clean, return code 0, 5.3 ms | |
| Declaration only, before either edit | | blocking false, MEDIUM FM-C003, 7.04 ms |

The merge command is already a few milliseconds. The park cost is the lane that already edited, not the merge. Foremerge is early, and on `modify` it does not say whether the later merge will conflict.

History context, not a park count: last 80 commits on `origin/main` (`db42453b822e` at 2026-11-07T17:44:20-08:00 back to `c1f94554468c` at 2026-11-03T18:06:53-08:00). 24 of 79 adjacent pairs share a path. 22 of those 24 are the same author, so they are follow-up commits, already ordered. The other two are also sequential commits on main (`341877173d52`/`e5c9d688eec8` share three Strata files, `7db8c4f73377`/`340344cca129` share `scripts/pfy_build_cloud.py`). Hot shared files touched in that window: `.github` 7, `Makefile` 4, `scripts/pregate.sh` 3, `AGENTS.md` 2, `TOOLS.md` 2, and one each for the ranking doc, `_registry.json`, `scripts/test_select.py`, and `scripts/test_cache.py`. `run_tests.py` and `data/tools.json` were 0.

## Gates

Value gate (3 of 4 needed for I3, not claimed):

1. Gap fill: no. Gap B is a lane that parks when a rebase hits a content conflict. Same-path `modify` blocked 0/6. The warning also fires when two regions of one file merge clean. gitai is the land-time catalog row and was not part of this probe. The per-card split we already use stayed quiet.
2. Operator leverage: no. Every participant has to declare a scope, and the operation our lanes would declare does not gate acceptance. That is not a product lever within a day of glue.
3. Evidence: yes. This probe, with the pins and the command above.
4. Blast radius: yes. Apache-2.0, a 12.7 MB binary in the cache, no client setup, no key. Deleting the cache dir removes the install. The catalog pin stays in the entry.

Score 2 of 4.

Modularity gate (recorded, not used to promote):

1. Local binary needed: yes. The entry says unresolved HIGH conflicts gate acceptance. Only the run showed that same-path `modify` stays MEDIUM.
2. Bounded surface: yes. One CLI. The probe used `init`, `agent register`, `intent publish`, and `conflicts check`.
3. Isolatable: yes. Cache home and throwaway repos. Not the product runtime.
4. Reversible: yes. Delete `~/.cache/pfy/tools/foremerge`. The entry and this report remain.

`uses` and `features` do not name a CI, testing, or review role, so `self_pipeline` is not set. No `TOOLS.md` row and no `data/tools.json` row. I3 would need both a repeatable product script and `self_pipeline` evidence. This lane builds neither.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Someone skips publish | The ledger never sees that lane | Keep the static shared-file list |
| `modify` is not HIGH | Two lanes edit Makefile, blocking stays false, the rebase still parks | Do not treat Foremerge as the park gate |
| Same warning when git is clean | Two regions of one file merge, and FM-C003 still fires | Do not stop a lane on `shared_contract` alone |
| Short tokens | `a.py` against `b.py` is a false MEDIUM | Declare longer keys, or ignore that overlap |
| Omitted operation | Inferred as `add` and capped below HIGH | Require an explicit operation |
| Shared git dir | `init` writes `.git/foremerge` in the common dir, including a token file | Throwaway repos only. Never init a checkout that shares Mark's git dir |
| Pre-1.0 schema | A later release changes the ledger | Pin v0.5.1. Delete the throwaway ledger and re-init |
| One machine | Agents off this host do not share the ledger | A trial stays on nimo |
| `setup` and `install.sh` | They write client MCP config and `~/.local/bin` | Not run. The real-home binaries above were absent |

## Next gate

Stay I1. Do not wire Foremerge into `./pfy`, pregate, or CI. A later probe has to show a signal that separates a same-line content conflict from a clean merge of two regions in the same file. I3 also needs a repeatable script and `self_pipeline` evidence. Gate wiring is a separate ticket.

## Pipeline questions

How Foremerge would run if a later ticket put it in the pipeline. This lane did not add that path.

1. What triggers it? A lane publishes intent before editing. The next lane runs `conflicts check` on its scope. Not a CI job.
2. What does it do, and which services does it read and write? It reads declared scopes from a SQLite ledger in the git common dir and writes that ledger. It does not read file contents, so it cannot see a hunk conflict. No hosted model and no account.
3. What does it trigger next? A HIGH finding is meant to stop acceptance. A MEDIUM finding stops nothing. It does not start a land step.
4. Where does a human re-enter? Before `setup` into a client config, before `init` on a shared checkout, and before any gate wiring. MEDIUM stays a human decision.
5. What stops two runs doing the same work? One ledger per git common dir. Two lanes that both skip publish stay invisible to each other. This probe gave each matrix case its own throwaway ledger. The worktree pair shared one ledger, and the second worktree saw the first publish.
