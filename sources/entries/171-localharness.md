### Entry 171: LocalHarness: self-hosted coding/research agent harness built for local LLMs

- **URL**: https://github.com/ahwurm/localharness (MIT, Python 3.12+). Checked at commit `5af7511ce8f8f799f74de877698e4c4aec0dec45` (2026-11-04), README says v0.27.7, pre-1.0.
- **Date**: 2026-11-08 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2119353223106425058
- **Summary / Key Claims** (upstream README; their claims, not verified here): agents defined in YAML per project or per user; one permission gate in front of every tool call, and agents that read untrusted content (web, MCP results) lose write tools. Talks to vLLM, llama.cpp, Ollama or LM Studio over one OpenAI-compatible client; `localharness start` can size and launch a llama.cpp server from the GGUF tensor table (context, KV cache type, drafting). SQLite memory with background consolidation, an autoresearch experiment loop, post-turn critics ("metaharness"), Agent Skills (`SKILL.md`) support, bench results kept on disk. Companion project LocalShift moves headless Claude Code jobs onto it once a local model is good enough.
- **Why it matters here**: this is the closest thing seen so far to pfy-mentat's "local suite" goal from the harness side: local-model launch sizing, a fail-closed permission gate, harness-neutral skills, and a local experiment loop. Mark asked to be told when another project does part of the suite better, so it should be compared against our current local lanes (Grok Build driving Ollama/llama.cpp, opencode, the ATG work) before we build more of that ourselves.
- **Fit on nimo**: Python + uv, no account or paid key. llama.cpp and Ollama are already on nimo; the README's llama.cpp path is "reference machine" validated, Ollama only CPU round-trip validated, and AMD/ROCm or Vulkan is not mentioned, so Strix Halo support is unverified. Install would have to go under `~/DEVELOP` (uv tool dir redirected), never the default `~/.local`.
- **Verified on the Grok Bot box** (2026-11-08): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - `localharness start` may offer to fetch a model; any trial must point it at an existing served model and refuse downloads over 25 GB without Mark's go.
  - The `mobile` and `dispatch` (Discord) plugins are off by default; keep them off.
  - Pre-1.0: config schema can change without notice.
- **Extracted Repos / Tools**: https://github.com/ahwurm/localharness · https://github.com/ahwurm/localshift
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_171.py`. Commit-metadata only. Pins `$LOCALHARNESS_COMMIT`. Fetches via `$LOCALHARNESS_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/localharness/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_171` (7 stub tests).
- **Non-goals**: no install into `~/.local` or agent homes, no model download, no plugins beyond the defaults, no GPU run without Mark's go. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while LocalHarness is not installed |
| `start` pulls a large model | offers a fetch when none is found | Point it at an existing server; refuse fetches |
| Writes outside DEVELOP | uv tool and `~/.localharness` defaults | Redirect `UV_TOOL_DIR` and HOME to a worktree |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto trial on one catalog-lane task against our current local lane (same model, same task), comparing tool-call success and wall time. Needs Mark's go for any GPU run. No Feature GO.
