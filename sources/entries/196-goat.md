### Entry 196: GOAT: run and steer your coding agents across your own machines (Grok Build and OpenCode providers)

- **URL**: https://github.com/goat-si/goat (MIT, TypeScript; T3 Code derived). Checked at commit `56874cfafb49fe3f305a90ab0403daf36f7c132a` (2026-11-16 UTC; 2026-11-15 PT).
- **Date**: 2026-11-15 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2121844641783820544
- **Summary / Key Claims** (upstream README; their claims, not verified here): each machine runs a GOAT server that owns projects, threads, provider sign-ins and memory (an environment); one desktop/web/phone client connects to many environments. Agents can browse an SSH host, start a thread or worktree there, move a thread with its uncommitted changes, and wait for the result; **Fleet** shows what is running and what needs you. Providers include Claude Code, Codex, Cursor, Grok Build, OpenCode, Pi, ACP agents and cloud agents. Linux desktop app and a `goat` CLI; `goat service install` keeps the server running.
- **Why it matters here**: names Grok Build and OpenCode as providers, and the multi-host model maps onto the operator's hosts (nimo primary plus others). A possible operator view of parallel lanes across hosts in place of per-host tmux and log checks.
- **Fit on nimo**: Linux build from source (Vite+) or release binary in a prefix under `$PFY_ROOT`; server bound to localhost or a private network. No GPU needed. Does not itself serve models; uses whatever provider CLIs are on each host.
- **Verified on the Grok Bot box** (2026-11-15): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - 116 stars, pushed minutes before this run.
  - Releases come from a separate repo (goat-si/goat-releases) and the install script pipes to `sh`; trial from the pinned source build instead.
  - Hosts download their own GOAT releases when an agent crosses machines, which would install outside `$PFY_ROOT` on other hosts unless configured.
- **Extracted Repos / Tools**: https://github.com/goat-si/goat
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_196.py`. Commit-metadata only. Pins `$GOAT_COMMIT`. Fetches via `$GOAT_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/goat/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_196` (7 stub tests).
- **Non-goals**: no `goat service install`, no cross-host auto-download, no cloud providers, no computer-use add-on, no install outside `$PFY_ROOT`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Writes on other hosts | Crossing machines downloads GOAT releases there | Single-host trial on nimo only |
| Server exposed | Web app reachable off-host | Bind localhost; no tunnel |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto a single-host trial driving one Grok Build and one OpenCode lane from GOAT vs the current per-lane tmux/log checks.
