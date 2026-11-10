### Entry 174: jcode: Rust coding-agent harness built for many parallel sessions

- **URL**: https://github.com/1jehuang/jcode (MIT, Rust). Checked at commit `9c9003b18da0506739988bec461c1760014effcf` (2026-11-10), latest release v0.99.1 (Linux x86_64 tarball published with SHA256SUMS).
- **Date**: 2026-11-09 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2119670303588487218 (repo link in the reply https://x.com/DanKornas/status/2119670479623782824)
- **Summary / Key Claims** (upstream README; their claims, not verified here): headless sessions cost about 3.3 MB of RAM each after the first (README table: OpenCode ~5.9 MB, pi ~79.6 MB, Claude Code ~169 MB per extra session), about 19 ms to first input, built for "dozens of agents in parallel" on one codebase. Provider layer includes an OpenAI-compatible client (`JCODE_OPENAI_API_BASE`) and an OpenRouter-style client whose source mentions Ollama and LM Studio and has a no-auth switch (`JCODE_OPENROUTER_ALLOW_NO_AUTH`). Has hooks, MCP (remote), memory and multi-agent coordination docs.
- **Why it matters here**: the pipeline priority is many light lanes in parallel with no shared lock. If jcode really runs many sessions this cheaply against a local OpenAI-compatible endpoint, it is a candidate to replace opencode as the per-lane harness for non-GPU and local-model lanes.
- **Fit on nimo**: static Linux x86_64 release binary, no GPU needed for the harness itself. Local models through the existing Ollama/llama.cpp OpenAI-compatible endpoints (unverified). The upstream installer is `curl | bash` into the default home; a trial must unpack the release tarball under `~/DEVELOP` and run with a throwaway HOME instead. Many provider files (Anthropic, Copilot, Cursor, Gemini, Bedrock) are cloud-account paths we will not use.
- **Verified on the Grok Bot box** (2026-11-09): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - The RAM numbers are upstream's own benchmark (`scripts/bench_headless_memory.py`); reproduce before trusting them.
  - YC-backed project with a cloud product (jcode cloud, iOS app); keep cloud and account features off.
  - Local-endpoint support is read from source, not run.
- **Extracted Repos / Tools**: https://github.com/1jehuang/jcode
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_174.py`. Commit-metadata only. Pins `$JCODE_COMMIT`. Fetches via `$JCODE_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/jcode/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_174` (7 stub tests).
- **Non-goals**: no `curl | bash` install, no cloud login, no install outside `~/DEVELOP`, no GPU run without the operator's go. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while jcode is not installed |
| Installer writes to the real home | `curl \| bash` default path | Use the release tarball under DEVELOP with a throwaway HOME |
| Local endpoint does not work | provider expects a cloud key | Record the failure and stay I0; no paid keys |
| Pin drift | `master` moves fast | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto trial running the same N parallel light lanes under opencode and jcode against the same local endpoint, comparing RAM per session, tool-call success and wall time.
