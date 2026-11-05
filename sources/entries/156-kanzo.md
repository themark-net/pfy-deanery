
### Entry 156: Kanzo: a local kanban board and MCP server in one small Rust binary

- **URL**: https://github.com/emanuele-em/kanzo (AGPL-3.0-only, Rust). Checked at `HEAD` `005424d4d0b4c2971278a14de6fbca6189605e6c` (2026-10-28); latest release `v0.2.1` (2026-10-27), `kanzo --version` = `kanzo 0.2.1`.
- **Date**: 2026-10-31 (daily X intake, window 2026-10-31T00:41Z to 2026-11-01T00:35Z)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2116646648952783046 (repo link in the reply thread)
- **Summary / Key Claims** (upstream README; their claims except where marked verified): a kanban board in the browser (`kanzo`, http://localhost:4242) and an MCP server (`kanzo mcp` on stdio, or `/mcp` over HTTP on the running board) in one program, so a person and coding agents work the same tasks. Agents take the next task, move it to `doing`, comment as they work and move it to `review`; a Backlog column agents leave alone; images attached to tasks are passed to agents as file paths. The whole board is one data folder (`~/kanzo`, or `--home` / `KANZO_HOME`), optionally synced across machines through a private git repo (`kanzo sync`). `kanzo export` prints Markdown or JSON. Claims ~900 tokens for the agent tool list, 10-60 token replies, 2 ms start, 4.5 MB idle memory (measured on an Apple M4; unverified here).
- **Why it matters here**: a shared, local task board that both Mark and the bots can read and write through MCP is a lighter alternative to GitHub issues for pfy-mentat's own run queue, and `next_task` is the same "take the top item and own it" step our orchestrator loop does. The JSON export gives a plain-file view for handoffs.
- **Fit on nimo**: Yes, expected: static x86_64 musl binary, SQLite bundled, no GPU or NVIDIA dependency, nothing to install beyond one file under DEVELOP. Not staged on nimo; the smoke exits 2 there until it is.
- **Verified on the Grok Bot box** (release tarball `kanzo-x86_64-unknown-linux-musl.tar.xz` to `/tmp`, sha256 `4fad8cb2052258ff47dd3c0f23572e22e36482eb11698d75068ef781e2d6884f` matched the published `.sha256`): `init --home` on a temp folder, then over MCP stdio `create_project`, `create_task` and `list_tasks`, then `export -f json` and `export` (Markdown) all show the task in `todo`. Under bwrap with no network and a temp HOME, nothing is written outside `--home`. Smoke PASS.
- **Findings**:
  - AGPL-3.0-only: fine to run locally as an external binary, but do not vendor or copy its code into pfy-mentat, and a modified version offered over a network must publish its source.
  - "The board is a folder" means a folder holding `kanzo.db` (SQLite), `config.toml`, a lock file and a `.gitignore`, not Markdown files; use `export` for readable files.
  - The MCP server answers requests concurrently, so replies can come back out of order; clients must match by id (the smoke sends one request at a time).
  - Avoid `kanzo update` (downloads the latest release from GitHub and replaces the binary), `service install` (adds a login service) and `sync` (pushes the board to a git remote) in any trial. `listen = "0.0.0.0"` has no login. The released binary is 4.7 MB, slightly more than the README's 4.1 MB.
  - Agents find "their" project from the git remote of the repo they work in, so a trial should create projects explicitly by slug.
- **Extracted Repos / Tools**: https://github.com/emanuele-em/kanzo · releases https://github.com/emanuele-em/kanzo/releases/tag/v0.2.1 · crates.io `kanzo`
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_156.py`. Reads `$KANZO_BIN`, else `tmp/kanzo/bin/kanzo`, else PATH; version pinned (`$KANZO_VERSION`, default 0.2.1), else exit 2; never downloads. Temp `--home`, temp HOME, no `KANZO_HOME`; runs `init`, an MCP stdio session (initialize, tools/list, create_project, create_task, list_tasks) and both exports. FAILs if a step fails, a core task tool is missing, the task is not stored or exported, the server stops replying within the timeout, anything is written outside `--home`, or the real `~/kanzo` changes. Receipt: `pipelines/smoke/kanzo/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_156` (12 stub tests).
- **Non-goals**: No web board left running, no `service`, no `sync`, no `update`, no MCP registration in Grok Build, Hermes or any editor, no network listen.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Board lost or corrupted | SQLite file damaged or overwritten | `kanzo export -f json` snapshots; data folder lives under DEVELOP and is rebuildable from export |
| Writes outside scratch | Default data folder is `~/kanzo`; `service install` adds a login unit | Always pass `--home`; smoke checks temp HOME stays empty and real `~/kanzo` is unchanged |
| Silent self-update | `update` or the board's update offer replaces the binary from GitHub | Pin the binary by sha256; never run `update` |
| License creep | AGPL code copied into pfy-mentat | Use only as an external binary over MCP |

- **Status**: Cataloged I0. Smoke PASS on the Grok Bot box with the release binary in `/tmp`; exit 2 by default (not staged). Possible later trial: one pfy-mentat project board driven by `next_task` from a Build run, compared with the current GitHub-issue queue.
