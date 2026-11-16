### Entry 194: multi-agents: run coding-agent teams vs a solo agent on the same task, with cost and a paired benchmark

- **URL**: https://github.com/BichengWang/multi-agents (MIT, Python, PyPI `multi-agent`). Checked at commit `878a2f9a66829b4a48598bf57e82d6d61b4b1ed3` (2026-11-16 UTC; 2026-11-15 PT).
- **Date**: 2026-11-15 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2122003188773441907
- **Summary / Key Claims** (upstream README; their claims, not verified here): runs a task in your repository as a single agent, a coder/reviewer loop, best-of-N with a judge, or a plan topology. Workers are Claude Code, Codex, a `check` command, or a built-in SDK agent addressed as `sdk@litellm/<provider>/<model>`. Each run returns a patch plus a run record with tokens in/cached/out, cost and seconds; the working tree is untouched unless `--apply`. `--max-cost USD` stops new agent runs once spent and refuses runs it cannot price. A benchmark grades teams against solo agents on the same tasks (local Docker or Modal backend) with paired comparisons and cost per resolved task.
- **Why it matters here**: its north-star question ("did the team beat a single agent, and what did the extra agents cost?") is the same shape as the Deanery vs vanilla Grok Build eval and the cost-before-spend rule. Its run record and `--max-cost` refusal of unpriced runs are patterns for the prompted local-vs-cloud compare.
- **Fit on nimo**: pure Python via uv into a prefix under `~/DEVELOP`; the SDK worker through LiteLLM can point at the local Ollama (qwen3.6 35B default); benchmark on the local Docker backend only (no Modal account). No GPU needed beyond the model server.
- **Verified on the Grok Bot box** (2026-11-15): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - 170 stars; last push 2026-11-08 UTC.
  - Harnesses listed are Claude Code, Codex, SDK and check; no Grok Build or OpenCode harness, so a Deanery trial uses the SDK worker or a `check` wrapper.
- **Extracted Repos / Tools**: https://github.com/BichengWang/multi-agents
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_194.py`. Commit-metadata only. Pins `$MULTIAGENTS_COMMIT`. Fetches via `$MULTIAGENTS_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/multiagents/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_194` (7 stub tests).
- **Eval trial** (still I0, not a TOOLS.md row): `python3 examples/multiagents-trial/trial.py --max-cost 0`. Deanery check wrapper. It does not install upstream `multi-agents`. Default worker `sdk@litellm/ollama/qwen3.6:35b` against local Ollama, priced at $0. One past lane task (`examples/eval-harness/tasks/001-is-palindrome`) runs solo and as coder/reviewer. Record: `tmp/multiagents-trial/latest.json` with pass/fail, tokens, cost, and seconds, plus `latest.txt` beside it (pass/fail per arm, tokens, cost_usd, seconds, refused). `--max-cost` refuses a paid provider and any worker it cannot price. A missing local tag exits 2 and does not pull. `--apply` writes `solution.py` only when `--repo` is under this worktree's `tmp/`. Tests: `python3 -m unittest tests.test_multiagents_trial`.
- **Non-goals**: no Modal backend, no paid API keys, no `--apply` on a real checkout, no Claude plugin install. Catalog HOLD 70-75 untouched. No Feature GO. No `catalog_loop.sh` retarget.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Cloud spend | A worker defaults to a paid model | Local LiteLLM->Ollama only; set `--max-cost 0` for local runs |
| Writes a real tree | `--apply` on the operator checkout | `--apply` is refused unless `--repo` is under this repo's `tmp/`. Without `--apply` the checkout is not modified. |
| Missing local tag | A run pulls the model | Exit 2 after `/api/tags`. No pull. |
| Unpriced worker | Spend that cannot be counted | `--max-cost` refuses before any model call |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. The local trial command above is the eval path. No TOOLS.md row. Live pass/fail numbers are not in this entry.
