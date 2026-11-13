### Entry 186: Agent Cockpit: evidence-chain board and MCP server that ties agent claims to the runs and code behind them

- **URL**: https://github.com/chutingyean/Agent-Cockpit (AGPL-3.0, JavaScript, npm `@tingyen/agent-cockpit`). Checked at commit `a968c6bc2568a5036981f896939234aaac29c1cd` (2026-11-06).
- **Date**: 2026-11-12 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2121006618976342287 (repo link in the reply https://x.com/DanKornas/status/2121006797318455300)
- **Summary / Key Claims** (upstream README; their claims, not verified here): a local whiteboard plus MCP server for research done with coding agents (Claude Code, Codex, Cursor, Gemini CLI). Every claim is linked to the recorded experiment run and the code that produced it; when the code changes, affected claims are flagged for recheck. One write gate validates every write from MCP, CLI or board; unreported file changes block `git commit` and a Stop hook. Append-only `.cockpit/events.jsonl` allows replay. Built-in call graph and rule-based reviewer. Binds to 127.0.0.1; every check is a plain rule with no LLM calls.
- **Why it matters here**: the Deanery vs vanilla Grok Build evals and the catalog fit checks produce scored claims from runs. Nothing currently records which run and which commit each score came from, or flags a score once the code under it changes. This is an existing tool for that provenance problem, so it is worth checking before building one.
- **Fit on nimo**: no GPU, no model, Node 22.13+ only. `cockpit init` writes MCP configs, `AGENTS.md`, a Stop hook and a pre-commit hook into the target repo, so a trial must use `npx` on a scratch repo under `~/DEVELOP` with a throwaway HOME.
- **Verified on the Grok Bot box** (2026-11-12): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - 487 stars, last push 2026-11-06. AGPL-3.0: fine for local use; do not vendor it into this repo.
  - Writes hooks and agent config on init: never run in the operator's main checkout.
- **Extracted Repos / Tools**: https://github.com/chutingyean/Agent-Cockpit
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_186.py`. Commit-metadata only. Pins `$AGENTCOCKPIT_COMMIT`. Fetches via `$AGENTCOCKPIT_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/agentcockpit/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_186` (7 stub tests).
- **Non-goals**: no global npm install, no `cockpit init` or Claude plugin install in this repo or the real HOME, no vendoring of AGPL code, no install outside `~/DEVELOP`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Hooks land in a real checkout | `cockpit init` in the main repo | Scratch repo only |
| Stop hook blocks agents | Unreported changes stop a lane's turn | Trial without the Stop hook first, board and MCP only |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto on a scratch copy of one past eval: record the arm runs and rubric scores as claims, change one scored file, and check whether the board flags exactly the affected scores.
