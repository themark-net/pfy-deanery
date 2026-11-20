### Entry 203: LoopForge: self-hosted delivery workflows for coding agents with script and human gates

- **URL**: https://github.com/Tencent/LoopForge (MIT per the LICENSE file, with third-party components under their own licenses; GitHub reports NOASSERTION; Go). Checked at commit `6f606cf2a7354f05d1dbf2085f4eb832b7e89ccb` (2026-11-19 UTC; 2026-11-19 PT).
- **Date**: 2026-11-19 (daily X intake; post seen 2026-11-17 PT, queued 2026-11-18)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2122909144793383164
- **Summary / Key Claims** (upstream README; their claims, not verified here): a self-hosted workspace where a chat "Main Bot" or a fixed SOP runs coding-agent CLIs (CodeBuddy, Codex, Claude Code, OpenCode, Cursor CLI, Pi and others) as executors. SOPs chain Agent, Script and Human-gate nodes; roles for planning, implementation, review and testing each get their own prompt, model, skills and MCP tools. Docker sandboxes per conversation, per-node artifacts and logs, retry or rerun from any node, delivery as a PR or a direct merge.
- **Why it matters here**: this is the same job as Deanery's lane pipeline (separate implement, test and review roles, script gates, an operator gate, artifacts per step). It is a no-reinvention comparison target for the lane runner and the operator queue, and OpenCode is a listed executor, so a local-model path may exist.
- **Fit on nimo**: Docker Compose stack (MySQL plus platform services) pulled from GHCR; it listens on `0.0.0.0:8090` by default, so it must be bound to localhost or the tailnet before any trial. Would run under `$PFY_TMP` with rootless containers; no NVIDIA dependency is stated.
- **Verified** (2026-11-19): commit pin matched via `git ls-remote` and the GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - About 4.1k stars, created 2026-07-28 UTC, pushed 2026-11-19 UTC.
  - The installer creates an admin account in the local web app and offers to install missing system packages; neither is acceptable on nimo without a container-only plan.
  - Overlaps 202 CompozyOS and 201 Agent of Empires; compare designs before trying more than one.
- **Extracted Repos / Tools**: https://github.com/Tencent/LoopForge
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row. Stage card `data/stages/loopforge.json`.
- **Smoke**: `python3 examples/x-intake-local/smoke_203.py`. Commit-metadata only. Pins `$LOOPFORGE_COMMIT`. Fetches via `$LOOPFORGE_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/loopforge/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_203` (7 stub tests).
- **Non-goals**: no account sign-up, no service on `0.0.0.0`, no system package installs, no install outside `$PFY_TMP`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Exposed web app | Default bind is all interfaces | Bind to localhost in a rootless container only |
| Executors need paid keys | No local OpenCode or Ollama path works | Stop at catalog; compare design only |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: design comparison of its SOP node model (Agent, Script, Human gate, send-back) against Deanery's lane stages and operator queue.
