### Entry 132: ai-memory — self-hosted, git-backed shared memory and claim-once handoffs across 20+ agent harnesses (Grok Build, Hermes)

- **URL**: https://github.com/akitaonrails/ai-memory (MIT, Rust single binary; 11,343 stars at this read; release `v3.1.1`, 2026-10-17, tag at `52020da90131`)
- **Date**: 2026-10-19 (daily X intake, window 2026-10-18T00:36Z to 2026-10-20T00:36Z)
- **Source / Poster**: @alex_verem, https://x.com/alex_verem/status/2112197339066863872 (repo link resolved from the thread's t.co)
- **Summary / Key Claims** (upstream README at v3.1.1): one memory server you run yourself (laptop, homelab box) that more than twenty harnesses feed through MCP and lifecycle hooks. The support matrix lists Claude Code, Codex, Cursor, OpenCode, OpenClaw, **Grok Build CLI** and **Hermes Agent** as supported. Knowledge is a markdown wiki per project (git-backed), with search, a cross-project "how you work" profile and typed **handoffs that have an owner and are claimed exactly once**. `ai-memory run <harness>` can carry a private local projection of the previous agent's session. Embeddings and LLM features are optional. Multi-user auth and an audit log are built in. The one-step install (`install.sh` then `ai-memory setup`) writes `~/.local/bin`, a systemd `--user` service and MCP/hook config into each harness.
- **Why it matters here**: the operator is moving pfy-mentat to Hermes Agent as its local-first bot interface while Grok Build does the heavy work. Both are first-party integrations here, so one loopback server on nimo could hold a shared project memory and hand work between Build sessions, Hermes bots and Cursor agents with a claim-once guarantee, so two bots can't pick up the same handoff. It is zero-LLM by default, so it costs nothing to run. Overlaps Entry 108 (cass-memory: a scored playbook from session history) and the opencode-mem toolset candidate; this one is the shared store and handoff layer, not a rule learner.
- **Fit on nimo**: Yes for the binary: the release tarball unpacked under `~/DEVELOP/pfy-mentat/tmp/ai-memory/` (47.8 MB static x86_64 binary) with `--data-dir` inside `~/DEVELOP`. **Not** `install.sh`, `ai-memory setup` or the marketplace plugins: those write `~/.local/bin`, a user service and every harness's config, which is outside `~/DEVELOP` and needs the operator.
- **Verified on the Grok Bot box** (tarball sha256 `d055aef2989eeceb08da7a2db3533d9389a689058c57b5f8a03d5f4439225a2d`, matches the release's `.sha256`; binary sha256 `be9f539cbaaa8c583dd94a58c3817c35321f3d887e8195df91bf74f9c5eefa4b`; `ai-memory --version` 3.1.1; bubblewrap 0.12.0, no network, temp HOME): smoke PASS. `init` on a temp data dir; `serve --transport http` on a loopback port with `AI_MEMORY_EMBEDDING_PROVIDER=none` came up healthy; a page was written, found by search, not found by a nonsense query, read back, and present on disk as markdown under `wiki/`; a message sent to a second project was claimed by the first `message pop` (with the untrusted-input notice) and the second pop was empty. Temp HOME and the watched real-HOME dirs (`~/.local/share/ai-memory`, `~/.config/ai-memory`) unchanged.
- **Findings**:
  - **The CLI needs the server**: offline `write-page`/`search` fail, so any use on nimo means a running loopback service (a user service is a the operator decision).
  - `message send` to a project the server hasn't seen yet returns 404; the target project has to exist (one page written) first.
  - `init` writes a root bearer token file into the data dir. Keep the data dir out of git and never read or paste that file; the smoke never opens it.
  - `message pop` wraps cross-project bodies with a security notice: popped text is untrusted input to the next agent, which matches our prompt-injection rules.
  - Wiki paths are UUIDs per org/project, not readable names, so browsing the markdown by hand needs the CLI.
- **Extracted Repos / Tools**: https://github.com/akitaonrails/ai-memory · https://github.com/akitaonrails/ai-memory/releases/tag/v3.1.1 · https://github.com/akitaonrails/ai-memory/blob/main/docs/support-matrix.md
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_131_133.py --entry aimemory`. Looks up `$AI_MEMORY_BIN`, then `tmp/ai-memory/ai-memory`, then PATH; version pinned to 3.1.1 (`$AI_MEMORY_VERSION`). A stdlib driver runs `init`, a loopback `serve`, then the CLI against it, all on a temp data dir in one isolated child; it never runs `setup`, `install` or `run`. Receipt: `pipelines/smoke/aimemory/latest.json`.
- **Non-goals**: No `setup`, no user service, no hooks or MCP registration in any harness, no embeddings provider, no team server.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Setup sprawl | `setup` rewrites every harness's MCP/hook config | Don't run it; register MCP by hand per harness only after the operator's OK |
| Token leak | Root token file committed or pasted | Data dir outside git; reference the file by path only |
| Poisoned handoff | One agent's popped message steers another | Treat popped bodies as untrusted (upstream notice), never as instructions |
| Duplicate claim | Two bots take one handoff | The smoke FAILs if a second pop returns the message |
| Server down | CLI calls fail, bots lose memory | Bots must carry on without it; health-check `/healthz` before use |

- **Status**: Staged I1 on 2026-11-07 after the nimo probe (pasted search 8/8, repo facts 0/8, claim-once 8/8, 0 graded cases). Not I2. See eval/evq1107/ai-memory/VERDICT.
