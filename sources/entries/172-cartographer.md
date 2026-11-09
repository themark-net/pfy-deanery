### Entry 172: Cartographer: shared git-backed wiki that every agent reads and grows over MCP

- **URL**: https://github.com/BeppeTemp/cartographer (Apache-2.0, Go). Checked at commit `f96e5d9f7b0ae8506ce5470e35372546a70ea292` (2026-11-08). Pre-1.0; breaking changes bump the minor version.
- **Date**: 2026-11-08 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2119285283015274623
- **Summary / Key Claims** (upstream README; their claims, not verified here): one Go binary serves an MCP knowledge base stored in a git repo you own. Claude Code, Codex, OpenCode and any MCP client read and write the same wiki, so what one agent learns the next session (or another client) already knows. Writes go through the server so agents "can't break" the wiki; a health check reports broken, stale or missing pages; a KB can also ship skills, subagents and hooks to connected clients. `cartographer setup` installs a local service, creates the first KB and connects detected agent clients.
- **Why it matters here**: pfy-mentat's bots and Build sessions each keep their own memory, and doctrine is ported by hand into repo skills (port-bot-doctrine-to-pfy-sot). A git-backed, MCP-served wiki is a candidate shared memory layer across Grok Build, Cursor and opencode lanes, and it overlaps codebase-memory-mcp and opencode-mem (both already I3/proposed I3), so it belongs in the memory comparison rather than as a new lane.
- **Fit on nimo**: Go binary, no GPU, no account; needs a git repo for the KB (a local bare repo under `~/DEVELOP` works). The README's Linux path is "see Install" (no Homebrew assumed). `setup` edits every detected agent client's config, which must not touch Mark's real agent homes.
- **Verified on the Grok Bot box** (2026-11-08): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - Ignore the public demo server; trials stay local.
  - Run `setup` only with HOME pointed at a throwaway worktree so it can't rewrite real client configs or install a user service.
- **Extracted Repos / Tools**: https://github.com/BeppeTemp/cartographer
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_172.py`. Commit-metadata only. Pins `$CARTOGRAPHER_COMMIT`. Fetches via `$CARTOGRAPHER_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/cartographer/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_172` (7 stub tests).
- **Non-goals**: no service install, no edits to real agent client configs, no remote KB host. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while Cartographer is not installed |
| `setup` rewrites agent configs | connects every detected client | Run with a throwaway HOME only |
| Duplicate memory layer | overlaps codebase-memory-mcp / opencode-mem | Compare in one memory eval, keep one |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: include in a memory-layer comparison with codebase-memory-mcp and opencode-mem. No Feature GO.
