### Entry 169: IM.codes: shared agent memory, supervised execution and audit layer around terminal coding agents

- **URL**: https://github.com/im4codes/imcodes (MIT, TypeScript). Checked at commit `b8442c5ca3bd22046568258e84d30781dc6a79d0` (2026-11-01), package `imcodes` `0.1.2`. Upstream calls it a personal project with no stability or security guarantees.
- **Date**: 2026-11-07 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2119149373552549945 (GitHub reply https://x.com/DanKornas/status/2119149543472201859)
- **Summary / Key Claims** (upstream README; not verified here): messaging, memory and review layer for terminal coding agents. Turns final assistant outputs (not tool noise) into problem-to-solution memory with local semantic recall and per-message injection. Managed stdio MCP server gives agents memory search/write, agent-to-agent messaging and cron follow-ups bound to runtime identity. **Supervised execution** classifies each finished turn as complete/continue/ask_human and can loop audit-then-rework, failing closed on timeouts or bad output. **OpenSpec Auto Deliver** runs spec audit, implementation, scored audit (`PASS`/`REWORK`/`BLOCKED`) and rework gates, and never commits or pushes itself. Controlled Nodes let an agent operate enrolled computers.
- **Why it matters here**: the idle-boundary supervisor and scored audit/rework loop are close to what pfy-mentat's Build self-review lanes do by hand; the "memory from final answers only" rule is a cheap pattern for our lane memory. Design reference, not an install candidate.
- **Fit on nimo**: Node daemon plus web/mobile app; optional cloud sync and a hosted web app exist. Provider support centers on Claude Code, Codex and Gemini CLI; Grok Build is not listed. Controlled Nodes grant remote command execution, which is out of scope for nimo. Catalog-only.
- **Verified on the Grok Bot box** (2026-11-07): commit pin matched; smoke exits 2. 7 stub tests pass.
- **Findings**:
  - Fail-closed supervision with structured verdicts is the reusable idea.
  - Remote desktop / Controlled Nodes is a security surface we should not enable.
- **Extracted Repos / Tools**: https://github.com/im4codes/imcodes · https://im.codes
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_169.py`. Commit-metadata only. Pins `$IMCODES_COMMIT`. Fetches via `$IMCODES_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/imcodes/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_169` (7 stub tests).
- **Non-goals**: no daemon install, no account or cloud sync, no node enrollment. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while not installed |
| Remote execution exposure | Controlled Node enrolled on nimo | Do not enroll; design reference only |
| Memory leaks to cloud | optional sync enabled | Keep local-only if ever trialed |
| Pin drift | default branch moves | Smoke checks this SHA |

- **Status**: STAY I0 reference. Read-only notes in ops:eval/evq1107/imcodes/REPORT.md. No install, no Controlled Nodes, no Feature GO.
