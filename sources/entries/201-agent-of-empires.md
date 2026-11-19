### Entry 201: Agent of Empires (aoe): tmux-backed session manager for parallel coding agents

- **URL**: https://github.com/agent-of-empires/agent-of-empires (MIT, Rust). Checked at commit `d24c1274d1458bfbd161412ade8488957e763b82` (2026-11-18 UTC; 2026-11-17 PT).
- **Date**: 2026-11-17 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2122660013948666004
- **Summary / Key Claims** (upstream README; their claims, not verified here): runs each coding agent (Claude Code, OpenCode, Codex CLI, Gemini CLI, Pi, and others) in its own persistent tmux session with optional git worktree and Docker/Podman isolation; TUI, web dashboard, CLI and HTTP API; status detection, notifications, diff review, repo hooks.
- **Why it matters here**: Deanery runs parallel lanes in worktrees and tracks their status by hand-rolled scripts. aoe is a mature (about 4.6k stars) off-the-shelf lane/session layer with an HTTP API, so it is a candidate to replace or front the lane runner's session bookkeeping and give a phone view of lanes.
- **Fit on nimo**: single Rust binary plus tmux; install under `$PFY_TMP` (avoid the piped-shell installer, which writes to HOME); Podman sandboxing works without NVIDIA.
- **Verified on the Grok Bot box** (2026-11-17): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - Web dashboard (`aoe serve`) must stay bound to localhost or behind the tailnet.
  - Overlaps 186 Agent Cockpit and 195 Mycelium; compare before adopting more than one.
- **Extracted Repos / Tools**: https://github.com/agent-of-empires/agent-of-empires
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_201.py`. Commit-metadata only. Pins `$AGENT_OF_EMPIRES_COMMIT`. Fetches via `$AGENT_OF_EMPIRES_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/agentofempires/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_201` (7 stub tests).
- **Non-goals**: no dashboard exposed off-host, no install outside `$PFY_TMP`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Exposed dashboard | `aoe serve` binds publicly | Bind to localhost; reach via tailnet |
| Session sprawl | tmux sessions outlive lanes | Delete sessions in lane teardown |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: run two scratch lanes under aoe with OpenCode on the local model and compare status visibility against the current lane scripts.
