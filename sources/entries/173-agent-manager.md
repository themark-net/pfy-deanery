### Entry 173: agent-manager: tmux-based terminal manager for many coding-agent CLIs side by side (Grok Build included)

- **URL**: https://github.com/wainmann/agent-manager (Apache-2.0, Go). Checked at commit `cbe5fb9bd248636ebeb5ac6f97ab83940d04fb2d` (2026-11-08).
- **Date**: 2026-11-08 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2119534423184150662
- **Summary / Key Claims** (upstream README; their claims, not verified here): a thin layer over agent CLIs you already have. Each session is your own installed tool in its own persistent tmux session, using your own login and config. One list shows live status (done, stuck, working) grouped in a project tree; sessions can be forked, given a shell, sent saved prompts, and agents can spawn or message other sessions (`spawn`, `send`, `create_session`). Built-in diff review. Status detection covers Claude Code, OpenCode, Codex, **Grok Build**, Gemini CLI, Pi, Hermes Agent, Cursor CLI and others. No cost tracking yet.
- **Why it matters here**: pfy-mentat runs parallel Grok Build lanes on nimo (catalog loop, integrate batches, up to 4 concurrent) tracked by PID checks and log greps. A manager that knows Grok Build's status and keeps each lane in a named tmux session could replace part of that ad-hoc watching, and its `spawn`/`send` CLI could be driven by the loop scheduler.
- **Fit on nimo**: Go binary plus tmux, Linux supported, no GPU, no account or key (uses the CLIs' existing logins). Install from a release binary or source into `~/DEVELOP`; Homebrew is not needed.
- **Verified on the Grok Bot box** (2026-11-08): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - It's interactive-first; headless use by the loop depends on the `spawn`/`send` CLI working without a TUI, which is unverified.
  - Agents spawning agents bypasses the loop's 20-a-day / 4-concurrent caps unless the scheduler stays the only spawner.
- **Extracted Repos / Tools**: https://github.com/wainmann/agent-manager
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_173.py`. Commit-metadata only. Pins `$AGENTMANAGER_COMMIT`. Fetches via `$AGENTMANAGER_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/agent-manager/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_173` (7 stub tests).
- **Non-goals**: no install outside `~/DEVELOP`, no attaching to running Build lanes, no agent-to-agent spawning. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while agent-manager is not installed |
| Lane caps bypassed | agents spawn more agents | Keep the loop scheduler as the only spawner |
| tmux session clash with live lanes | shared tmux server | Use a dedicated `-L` socket in a trial |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: a read-only trial watching existing nimo lanes' status. No Feature GO.
