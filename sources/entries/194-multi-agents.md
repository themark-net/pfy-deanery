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
- **Non-goals**: no Modal backend, no paid API keys, no `--apply` on a real checkout, no Claude plugin install. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Cloud spend | A worker defaults to a paid model | Local LiteLLM->Ollama only; set `--max-cost 0` for local runs |
| Writes a real tree | `--apply` on the operator checkout | Scratch worktree under `~/DEVELOP/pfy-deanery/tmp` only |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto running one past Deanery lane task solo vs coder/reviewer on the local default, compared on pass/fail, tokens and wall time against the current hand-run eval scoring.
