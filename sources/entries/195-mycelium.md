### Entry 195: Mycelium: shared room (chat, task board, memory) where several coding agents work tasks together

- **URL**: https://github.com/mycelium-io/mycelium (Apache-2.0 per README badge, Python 3.12). Checked at commit `68906f2e23347b23452e9eb4771a699bded1fddb` (2026-11-16 UTC; 2026-11-15 PT).
- **Date**: 2026-11-15 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2122071151958499722
- **Summary / Key Claims** (upstream README; their claims, not verified here): a **room** holds a chat, a task board and a shared memory. You run the coding agents you already use (Claude Code, Codex, Cursor and others) on your own machines and add them to a room; they work tasks together and write what they learn into the room so the next agent can pick it up. Desktop app runs a hub locally with no Docker (Linux AppImage); a CLI install runs the hub in Docker; optional API sign-in in `config.toml`. Marked experimental with breaking changes expected.
- **Why it matters here**: a candidate for the cross-lane memory and hand-off problem (stalled lanes losing context between runs) and for coordinating parallel lanes without a single shared lock. Compare with 186 Agent Cockpit and 173 agent-manager.
- **Fit on nimo**: self-hosted hub, local only; Docker or AppImage under `$PFY_ROOT`. Agent support depends on its adapters; Grok Build and OpenCode are not named in the README, so check adapters before any trial.
- **Verified on the Grok Bot box** (2026-11-15): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - 130 stars, pushed minutes before this run; GitHub API reports license NOASSERTION while the README badge says Apache 2.0.
  - The recommended setup pipes a remote install script to bash, and an agent runbook asks agents to curl and follow `agents.md`; do neither on nimo.
- **Extracted Repos / Tools**: https://github.com/mycelium-io/mycelium
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_195.py`. Commit-metadata only. Pins `$MYCELIUM_COMMIT`. Fetches via `$MYCELIUM_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/mycelium/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_195` (7 stub tests).
- **Non-goals**: no curl-to-bash installer, no agent-followed remote runbook, no hub beyond localhost, no install outside `$PFY_ROOT`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Remote script runs | `install.sh | bash` or `agents.md` runbook | Build from the pinned source in a scratch prefix |
| Hub exposed | API bound beyond localhost with auth off | Bind 127.0.0.1; enable `[auth]` |
| Breaking changes | Experimental main moves fast | Trial from the pinned SHA |

- **Status**: Cataloged I0. Next step, if any: check for Grok Build/OpenCode adapters; if present, eval-auto one two-lane task sharing a room vs today's hand-off notes.
