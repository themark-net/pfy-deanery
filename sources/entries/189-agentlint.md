### Entry 189: AgentLint: local pre-tool guardrails that block secret writes and risky commands and return a correction

- **URL**: https://github.com/mauhpr/agentlint (MIT, Python 3.11+, PyPI `agentlint` 2.12.0). Checked at commit `1fff2d5990ede5895e3e0a4fe2d6ffd4e9883e1c` (2026-11-07).
- **Date**: 2026-11-13 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2121347940073742519
- **Summary / Key Claims** (upstream README; their claims, not verified here): checks proposed file changes and shell commands locally through agent pre-tool hooks. Blocks detected secret writes, `.env` writes, plain force-pushes to `main`/`master`, CI pipeline edits and package publishing; warns on many destructive commands, direct pushes to `main`, test weakening and removed error handling. Returns a reason the agent can act on, then re-checks the revised proposal. Setup commands for Claude Code, Codex, Cursor, Gemini CLI, Continue, Kimi and Grok; `agentlint status` / `doctor` confirm hooks are actually observed. `agentlint ci --diff origin/main...HEAD` checks a PR's file changes.
- **Why it matters here**: Deanery already catalogs destructive-command-guard and QWED (185) and has its own public-path and destructive-command checks. AgentLint is deny-only, local, rule-based and covers the hard stops (secrets, force-push, publishing) in one tool with a CI mode, so it is a direct candidate to replace or back up the in-house checks. As a read-only, deny-only advisory tool it fits the predefined auto-promotion rules if it runs clean in the sandbox.
- **Fit on nimo**: no GPU, no model, no network for checks. `uv tool install` or pip into a venv under `~/DEVELOP`; run `agentlint ci` on a scratch worktree first, before any hook goes into a real agent home.
- **Verified on the Grok Bot box** (2026-11-13): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - 162 stars, PyPI 2.12.0, last push 2026-11-07.
  - `agentlint setup <agent>` edits agent settings files; that is the step to keep off the real homes until it passes.
- **Extracted Repos / Tools**: https://github.com/mauhpr/agentlint, https://github.com/mauhpr/agentlint-plugin
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_189.py`. Commit-metadata only. Pins `$AGENTLINT_COMMIT`. Fetches via `$AGENTLINT_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/agentlint/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_189` (7 stub tests).
- **Non-goals**: no hook installs into the real agent homes, no settings edits, no blocking CI gate on main, no install outside `~/DEVELOP`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Hooks land in a real home | `setup` writes agent settings | Only run `agentlint ci` on a scratch worktree until promoted |
| False blocks stall lanes | A block rule fires on legitimate work | Start in warn-only, compare with the in-house checks |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto running `agentlint ci --diff` over the last 30 Deanery commits plus a seeded set of bad diffs (secret literal, `.env`, force-push, CI edit), scored against `scripts/check_public_paths.py` and destructive-command-guard on catches, false positives and wall time.
