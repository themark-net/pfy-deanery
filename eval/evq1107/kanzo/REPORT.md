# Kanzo evq1107

STAY I0 reference: AGPL run queue, and gap B stays the pfy build timeout. This lane installed nothing, downloaded no release, and ran no upstream code.

## What it is

Kanzo (https://github.com/emanuele-em/kanzo) is one Rust program: a browser board and an MCP server on one SQLite folder (`~/kanzo`, or `--home` / `KANZO_HOME`). Crate version at the pin is 0.2.1. License is AGPL-3.0-only (`Cargo.toml` `license`, and the LICENSE header is the Affero GPL). A changed copy served on a network must publish its source. This repo cites and summarizes. The clone stays in the cache.

Columns are an optional backlog, then todo, doing, review, done. `next_task` takes the top todo row with `human = 0` (order by position) and moves it to doing. The tool text says to comment, then move the card to the review column, and to leave done rows and human rows for the person. Stdio picks the project from the git remote of the working folder. HTTP `/mcp` needs the project slug. `export` prints Markdown or JSON. The folder is `kanzo.db` plus `config.toml`. README figures (4.1 MB, 2 ms, 4.5 MB idle, about 900 tokens, 10 to 60 token replies) are upstream numbers from an Apple M4. Ten MCP tools are named in `src/mcp.rs` at the pin.

## Pin and commands

Cache `~/.cache/pfy/tools/kanzo/src`, not committed. Read pin `005424d4d0b4c2971278a14de6fbca6189605e6c` (2026-10-28, merge of mcp-human-flag). Tag `v0.2.1` peels to `f1aaf69582c50645de257f3da859fb6a03ddaa5e`, an earlier commit. Entry 156 smoke used that release tarball on the Grok Bot box. This lane did not re-run `examples/x-intake-local/smoke_156.py`. The entry still records exit 2 when no binary is staged. Work tree 2249263 bytes, 44 files. With `.git`, 4291650 bytes. No model lock. Fetch duration was not timed.

```bash
CACHE=~/.cache/pfy/tools/kanzo
mkdir -p "$CACHE"/{home,xdg/config,xdg/cache,tmp}
export HOME="$CACHE/home" XDG_CONFIG_HOME="$CACHE/xdg/config" XDG_CACHE_HOME="$CACHE/xdg/cache" TMPDIR="$CACHE/tmp" GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
git clone --filter=blob:none --no-checkout https://github.com/emanuele-em/kanzo.git "$CACHE/src"
git -C "$CACHE/src" fetch --depth 1 origin 005424d4d0b4c2971278a14de6fbca6189605e6c && git -C "$CACHE/src" checkout --detach FETCH_HEAD
```

## Ideas, and the pfy file each would touch

1. A backlog column and a human flag that `next_task` skips. Touch `docs/TODO.md` (active rows beside parked rows) and exit 6 in `docs/ops/loop-engineering.md`.
2. Move the top item to doing, comment, and let a person close it. Touch `docs/ops/loop-engineering.md`. Brigade already measured an exclusive file claim.
3. Keep a readable export beside the database. Touch `docs/PENDING-HANDOFF.md`. The queue source stays Markdown.
4. Pass the project slug when the client has no git folder. The lane branch already carries the slug. No new file.

## Catalog comparison

Same job: a person and an agent share one queue and take the next item. `docs/eval/TOOLSET-RANKING.md` (2026-11-07) holds entry 156 for AGPL. No entry from 137 to 167 closes gap B (the `./pfy build` 3 h timeout and the parked pregate FAILs).

| Tool | Stage | How Kanzo compares |
| --- | --- | --- |
| kanbots | I1 | Kanban that fans CLIs into worktrees. Its 2026-11-07 probe left the build timeout in place. Kanzo is the board plus MCP. |
| festival | I1 | Next step is one markdown file. Kanzo's next step is one SQL row. |
| brigade | I0 | Exclusive file claim, 0 duplicate ids of 94. Kanzo's SQL claim was not raced here. |
| project-process bootstrap | I3 | Scaffolds `docs/TODO.md`, the ordered queue for humans and agents. |
| Finn Loop / 8-exits | I1 | Exit cards, already the orchestration toolset. |
| multica | I1 | Multi-agent board, outside our orchestrator. |
| LangGraph | I1 | Graph runtime. Our loops cover the operator path. |
| Atomic Task Graph | I2 | DAG compile, a separate job from a board. |
| Squadra | I1 | Ack before a seat starts. The 3 h timeout stayed. |
| mattpocock skills | I1 | Planning skills already name the next step. |
| gstack | I1 | Role patterns already live in docs. |
| Foremerge | I1 | Pre-edit intent ledger. |
| ai-memory | I1 | Claim-once mailbox for notes. |
| Auto-Company | I1 | Daemon patterns, kept as notes. |
| Overtime, Open Steps, odai, Hermes Teammates | I0 | Wake, stop nag, evidence skill, Hermes roster. |

## Gates

Value, 3 of 4 for I3: gap fill no, operator leverage no, evidence no (smoke not re-run), blast radius no (AGPL in-tree copy, default `~/kanzo`, `update`, `service install`, `sync`, and `listen = 0.0.0.0` with no login). Score 0 of 4.

Modularity, all 4 for a local copy: the README was enough to stay, the surface is one crate, the cache clone is isolatable, and deleting it leaves the pin. 3 of 4. 2249263 bytes is under the 50 MB I2 cap. Potential is low, so I2 stays closed. No `self_pipeline`. No TOOLS.md row. No `data/tools.json` row. Advisory only.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| AGPL copy | Upstream Rust lands in this repo | Cache stays under `~/.cache/pfy/tools/kanzo/`. This report quotes no source. |
| Default data dir | A run writes `~/kanzo` | A later trial passes `--home` on a temp dir. This lane ran no binary. |
| Self-update or login unit | `update` or `service install` | Leave both unused. The card pins the commit. |
| Open listen | `0.0.0.0` has no login | A trial keeps `127.0.0.1`. |
| Wrong project | Stdio follows the git remote | Create the project by slug. |
| Gap B misread | A board is treated as a build-timeout fix | The verdict stays I0. |

## Next gate

Stay I0 reference. Re-open only as an external binary at this pin, with `--home` on a temp dir, an explicit slug, and no `update`, `service`, or `sync`. Compare one `next_task` with `docs/TODO.md`. Not a Feature GO.

## Pipeline questions

This lane writes the card, the entry Status line, and this directory. 1. A later adopt starts when a person or an MCP client runs `kanzo mcp`. The evq scheduler only started this read. 2. The board would read and write `kanzo.db` under `--home`. `sync` would push a private git repo. This lane used no account and no model. 3. The agent would comment and move the card. A person closes done rows and human rows. Next here is the driver sanity check, then a fast-forward land. 4. A person re-enters for backlog rows, human rows, sync conflicts, any install, and any gate ticket. `tmp/STOP` in this worktree stops the lane. 5. One worktree per slug (`bot/evq-kanzo-1107`) keeps other lanes off this card. The pin keeps `kanzo.lock` while a store is open and wraps writes in an immediate transaction. This lane started no caller, so that queue was not measured.
