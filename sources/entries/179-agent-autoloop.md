### Entry 179: Agent Autoloop: local event hub that keeps CLI agents working and asks only on real decisions

- **URL**: https://github.com/KKKKhazix/agent-autoloop (MIT, TypeScript, Node 24). Checked at commit `3539184a2c088f85e5623ebc47e7759849be0f72` (2026-11-10).
- **Date**: 2026-11-10 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2120236559806967885 (repo link in the reply https://x.com/DanKornas/status/2120236735187587227)
- **Summary / Key Claims** (upstream README, Chinese with an English README; their claims, not verified here): a zero-dependency scheduling kernel with pluggable event sources, agents, notification channels and a deploy pipeline. Any CLI that takes a prompt and prints its last reply can be an agent with one config line. When the agent needs a decision it ends its turn (no process, no tokens) and posts a decision card; `agent-autoloop answer` resumes it. Runs on one machine with no cloud server or open port.
- **Why it matters here**: the catalog loop and lane runners already do "run headless, park on a real decision, resume". This is an outside implementation of the same pattern; per the no-reinvention rule it should be compared with the nimo catalog-loop timer and orchestrator lanes before more of that is built in-house.
- **Fit on nimo**: no GPU. Needs Node 24 and Git. The upstream installer is `curl | sh` into the default home; a trial must unpack a release under `~/DEVELOP` with a throwaway HOME and point it at a local-model CLI agent. Notification plugins for Feishu, DingTalk, WeCom, Slack and Discord are not used.
- **Verified on the Grok Bot box** (2026-11-10): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - 4.4k stars and active, but the main docs are Chinese; the English README covers setup.
  - The deploy-pipeline plugin is out of scope (deploys are a hard stop).
- **Extracted Repos / Tools**: https://github.com/KKKKhazix/agent-autoloop
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_179.py`. Commit-metadata only. Pins `$AUTOLOOP_COMMIT`. Fetches via `$AUTOLOOP_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/autoloop/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_179` (7 stub tests).
- **Non-goals**: no `curl | sh` install, no deploy plugin, no chat-app notifications, no install outside `~/DEVELOP`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Installer writes to the real home | `curl \| sh` default path | Unpack a release under DEVELOP with a throwaway HOME |
| Deploy plugin fires | Pipeline plugin enabled | Leave it disabled; deploys stay a hard stop |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto comparison of one park-and-resume task under Agent Autoloop and under the current catalog-loop lane runner, measuring idle cost, resume correctness and setup effort.
