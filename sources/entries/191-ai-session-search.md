### Entry 191: AI Session Search (aise): one local index over coding-agent session history, with an MCP server

- **URL**: https://github.com/ahundt/ai-session-search (Apache-2.0, Rust; PyPI and crates.io `ai-session-search` 1.1.0). Checked at commit `941c2a958ba3760dd07b278963ebcf59b2d7be1b` (2026-11-14).
- **Date**: 2026-11-14 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2121550214611849231
- **Summary / Key Claims** (upstream README; their claims, not verified here): indexes local transcripts from Claude Code, Claude Desktop local agent, Codex, Cursor, Antigravity, Pi coding agent, Prime Agent, Google AI Studio and Gemini CLI into one index. CLI, TUI, MCP server, Python and Rust APIs. Finds sessions and messages, recovers every version of a file an agent wrote (`aise files history` / `extract --restore` into a `.recovered` sibling), lists subagent sessions, separates harness notices (injected instructions, hooks, interrupts) from human input, and reports where a human had to correct the agent (`aise skills corrections`, `aise repeats`). `aise integrations install --dry-run` previews every write.
- **Why it matters here**: Deanery evals and lane post-mortems currently rebuild "what happened in that run" by hand from logs. aise covers memory/recall over past sessions, file recovery after a lane edits something, and correction mining (where the operator had to step in), which feeds the improvement-vector rubric. Grok Build transcripts are **not** on its provider list, so the honest first question is whether a provider adapter is small enough or whether it only helps on OpenCode-style or Cursor sessions.
- **Fit on nimo**: CPU only, no model, no network for search. `uv tool install` or `cargo install --locked` into a prefix under `$PFY_ROOT`; skip `aise integrations install` (it registers MCP and writes guidance into each detected agent home).
- **Verified on the Grok Bot box** (2026-11-14): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - 67 stars, last push 2026-11-14 (1.1.0 release prep). Linux, macOS and Windows.
  - No Grok Build provider listed; adding one is the gating question for Deanery use.
- **Extracted Repos / Tools**: https://github.com/ahundt/ai-session-search
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_191.py`. Commit-metadata only. Pins `$AISE_COMMIT`. Fetches via `$AISE_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/aise/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_191` (7 stub tests).
- **Non-goals**: no `integrations install` into real agent homes, no MCP registration, no install outside `$PFY_ROOT`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Agent homes edited | `integrations install` writes MCP config and guidance | Use `--dry-run` only; point it at a copied session dir |
| Index leaks private text | Index holds prompts, secrets pasted in sessions | Keep the index under `$PFY_ROOT`, never in a repo |
| No Grok Build coverage | Grok sessions not parsed | Trial on OpenCode/Cursor lanes first; file an adapter issue |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto that indexes a copy of the last week's lane sessions and answers five real post-mortem questions (which run edited file X, where the operator corrected the agent), timed against the current grep-the-logs method.
