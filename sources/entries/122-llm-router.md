### Entry 122: llm-router — local, free-first prompt router for AI coding tools (Ollama first, secrets stay local)

- **URL**: https://github.com/ypollak2/llm-router (MIT, Python, 115 stars at this read; PyPI `llm-routing` 15.4.0)
- **Date**: 2026-10-16 (daily X intake)
- **Source / Poster**: @DanKornas, https://x.com/DanKornas/status/2111049257603961259
- **Summary / Key Claims** (upstream README at 15.4.0): an MCP server plus host hooks for Claude Code, Codex CLI, OpenCode, Pi, Gemini CLI, Copilot and others. Each prompt gets a task type and complexity from a deterministic heuristic (`classify_signals`, no model call); only ambiguous prompts escalate to an LLM or embedding classifier. Simple prompts are drafted on a free or local model first (Ollama, then free hosted tiers), then the chain walks up toward paid models. A grounding check drops drafts that cite files or functions not in context. Prompts that contain a key, token or private key route to local models only (fail-closed). Runs entirely on the machine, no account; provider keys are optional. Ships budget caps, savings reports, a replay log and a soak corpus.
- **Why it matters here**: our routing between nimo's local models, Grok Build and Cursor is hand-written (`org-spinny-decide`, `./pfy decision`, the bot-budget skill). llm-router is an open, testable version of "try local first, escalate only when needed" with a deterministic classifier we can score offline, and its secrets-stay-local rule matches the standing no-secrets rule. **Possible eval-auto trial**: score its offline classifier against `org-spinny-decide` on the same labeled set of real org prompts (local vs escalate), with nimo's `qwen3.6:35b` as the local tier.
- **Fit on nimo**: Yes for the classifier and MCP server: a venv under `~/DEVELOP/pfy-mentat/tmp/llm-router` (Python 3.11+, pulls `litellm`, `fastapi`, `mcp`). Ollama is already on nimo. Hooks are written for Claude Code and similar hosts; Grok Build is not a listed host, so wiring it into Build would be our own adapter.
- **Verified on the Grok Bot box**: smoke PASS in `/tmp` with a temp HOME, under bubblewrap with no network: the classifier called "what does os.path.join do?" a confident simple query and the rate-limiter prompt confident code; `llm-router demo` exited 0 and printed its routing table; HOME stayed empty. Negative paths: no binary gives exit 2; a wrong `$LLMROUTER_VERSION` gives 2.
- **Finding**: `LLM_ROUTER_DIRECT_EXECUTION` is **on by default**, giving the local model `write_file`, `edit_file` and `run_command` under an allowlisted path; upstream says that does not stop targeted deletes, force pushes or exfiltration. Any trial sets `LLM_ROUTER_DIRECT_EXECUTION=false`. `llm-router install` writes hooks and MCP config into host config dirs under HOME and keeps state in `~/.llm-router/` (outside DEVELOP on nimo), so trials use a temp HOME and never run `install` against Mark's real config. `demo` prints static example prices, not measured ones.
- **Extracted Repos / Tools**: https://github.com/ypollak2/llm-router · https://pypi.org/project/llm-routing/ · https://github.com/ypollak2/llm-router/blob/main/SECURITY.md
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_122_124.py --entry llmrouter`. Looks up `$LLMROUTER_BIN`, then `tmp/llm-router/.venv/bin/llm-router`, then PATH; package pinned to 15.4.0. Offline classifier plus `demo` only; no model call, no `install`. Receipt: `pipelines/smoke/llmrouter/latest.json`.
- **Non-goals**: No hooks installed into any host, no provider keys, no routing of real org traffic.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Direct execution left on | Local model edits files or runs commands during a trial | Always set `LLM_ROUTER_DIRECT_EXECUTION=false`; run in a throwaway worktree |
| `install` touches real host config | Hooks appear in Mark's real agent config | Never run `install` outside a temp HOME; `llm-router uninstall --purge` removes them |
| Heuristic misroutes hard prompts to a small model | Bad drafts on real work | Score it offline on a labeled set before any wiring; keep the grounding check on |
| Upstream churn (15.x moves fast) | Smoke pin goes stale | Bump the pin deliberately in a follow-up after re-running the smoke |

- **Status**: STAY I0 (evq1107). Offline complexity matched the HiRoute labels on 14 of 20. The hook chain named Ollama first on 20 of 20. Evidence: `ops:eval/evq1107/llm-router/REPORT.md`. Not wired into `./pfy`.
