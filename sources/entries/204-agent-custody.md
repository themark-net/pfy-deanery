### Entry 204: agent-custody: policy gateway and signed receipts for agent tool calls

- **URL**: https://github.com/svayatta/agent-custody (Apache-2.0, TypeScript, Bun and Node 22; Python client). Checked at commit `065a02fcc455f4217cd4d10792caf744c7a7b8e7` (2026-11-19 UTC; 2026-11-19 PT).
- **Date**: 2026-11-19 (daily X intake; post seen 2026-11-18 PT, queued 2026-11-18)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2122999758692196422
- **Summary / Key Claims** (upstream README; their claims, not verified here): a gateway sits between agents and their tools (MCP servers, REST APIs, other agents over A2A) and checks each call against a Cedar or Rego policy before forwarding it. A person signs a time-limited grant for an agent's scopes; each checked call, allowed or denied, gets a signed receipt in a Merkle transparency log that can be verified offline with public keys. A coding-agent hook starts in observe mode to show what a starter deny list would block. The upstream threat model says the gateway only covers calls routed through it and the coding hook is not a sandbox.
- **Why it matters here**: Deanery's prompt-injection work (lane cage, tool allowlist, path guard) blocks actions but leaves no verifiable record of what a lane tried. Observe-mode receipts for lane tool calls would be an audit layer next to the cage, not a replacement for it.
- **Fit on nimo**: Bun and Node under `$PFY_TMP`; the demo uses a stand-in server, and key generation is local. No paid keys or hosted service are needed for the demo path. Its coding hook targets Claude Code; a Grok Build or OpenCode hook would need checking.
- **Verified** (2026-11-19): commit pin matched via `git ls-remote` and the GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - About 110 stars, created 2026-09-04 UTC, pushed 2026-11-19 UTC; young project.
  - The container quick start uses `sudo chown` on a config dir; on nimo use the from-source path in a rootless container instead.
- **Extracted Repos / Tools**: https://github.com/svayatta/agent-custody
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row. Stage card `data/stages/agent-custody.json`.
- **Smoke**: `python3 examples/x-intake-local/smoke_204.py`. Commit-metadata only. Pins `$AGENT_CUSTODY_COMMIT`. Fetches via `$AGENT_CUSTODY_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/agentcustody/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_204` (7 stub tests).
- **Non-goals**: no enforcement on real lanes, no sudo, no global npm or pip install, no install outside `$PFY_TMP`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Mistaken for a sandbox | Hook is trusted to stop a lane | Keep the lane cage; receipts are audit only |
| Hook only for one agent | No Grok Build or OpenCode hook | Route only MCP calls through the gateway, or stop at catalog |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: observe-mode trial on one sandboxed lane's MCP calls, receipts written under `$PFY_TMP`, compared with the lane cage's own logs.
