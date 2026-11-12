### Entry 184: brain.md: file-based project memory for coding agents, written through one CLI

- **URL**: https://github.com/mindmuxai/brain.md (Apache-2.0, JavaScript, npm `@mindmux/brain-md`). Checked at commit `5f7128dfd4c8635fa1f1678690d57d8bd3b1e770` (2026-11-05).
- **Date**: 2026-11-11 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2120598934858956965 (repo link in the reply https://x.com/DanKornas/status/2120599105017979215)
- **Summary / Key Claims** (upstream README; their claims, not verified here): an agent-agnostic convention for durable project knowledge (decisions, requirements, constraints) as plain Markdown in a `brain/` directory with a `BRAIN.md` protocol file. Every write goes through the zero-dependency `brain` CLI so the structure stays valid. Any agent that reads files can use it; skills are copied into detected agents.
- **Why it matters here**: the repo already keeps ADRs, skills and handoffs as Markdown, and several memory tools in the catalog (for example MemPalace) add a store or a service. brain.md is the file-only end of that range. Per the no-reinvention rule, compare it with the ADR skill and the lane handoff files before adding more in-house memory structure.
- **Fit on nimo**: no GPU, Node only. `brain setup -y` writes skills into `~/.claude/skills` and other agent homes, and `brain init` writes agent config files into the target repo, so a trial must use `npx` with a throwaway HOME on a scratch repo under `~/DEVELOP`.
- **Verified on the Grok Bot box** (2026-11-11): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - 603 stars, v0.4.1, last push 2026-11-05.
  - Writes into agent homes and repo config on setup: never run in the operator's main checkout.
- **Extracted Repos / Tools**: https://github.com/mindmuxai/brain.md
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_184.py`. Commit-metadata only. Pins `$BRAINMD_COMMIT`. Fetches via `$BRAINMD_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/brainmd/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_184` (7 stub tests).
- **Non-goals**: no global npm install, no `brain setup` against the real HOME, no `brain init` in this repo, no install outside `~/DEVELOP`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Setup writes to real agent homes | `brain setup -y` with the default HOME | `npx` with a throwaway HOME only |
| Repo config overwritten | `brain init` in a real checkout | Scratch repo only |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto comparison on one scratch repo: a local-model lane resumes a task from `brain/` versus from the current handoff file, scoring how many recorded decisions it honours.
