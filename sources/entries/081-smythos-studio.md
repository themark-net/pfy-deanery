### Entry 081: SmythOS Studio — Open-source visual drag-and-drop AI agent builder + deployable runtime

- **URL**: https://x.com/i/status/2086743218041872393
- **Date**: 2026-08-10
- **Poster**: Tom Dörr (@tom_doerr)
- **Summary / Key Claims**: Builds sophisticated AI agent workflows with an intuitive drag-and-drop visual workspace. Open-source visual agent builder + runtime stack; no-code workflows with optional custom code; deploy local / cloud / edge with governance.
- **Extracted Repos / Tools**:
  - https://github.com/SmythOS/smythos-studio (MIT, ~186★, TypeScript/JS visual UI + Docker Compose self-host; `docker compose up -d` → localhost:6060)
  - Related runtime: https://github.com/SmythOS/sre (MIT, ~1.3k★, SRE Runtime/SDK/CLI for code-first agents; `npm i -g @smythos/cli`)
- **TOOLS.md Link**: Proposed under Agent Frameworks & Orchestration / Visual Workflow Builders (initial scores: S1=82 S2=72 S3=85 S4=80 overall ~80 tier B). Tracking: proposed pin to latest main / Docker image.
- **Notes**: Stage 0 gate **PASS** (MIT; Docker Compose one-command path documented; local dev via pnpm also available). High relevance as a visual/no-code agent orchestration surface with self-host option. Complements CLI-first tools (MCO, OpenCode, etc.) and multi-agent generators. Commercial SaaS/enterprise layer exists (smythos.com) but core Studio + SRE are MIT and runnable fully local. Mentions MCP client paths; LLM connectors are provider-agnostic (OpenAI/Anthropic/Groq etc.) — local Ollama path not prominently documented but should be feasible via standard OpenAI-compatible endpoints. Runtime is the stronger production piece (~1.3k★); Studio is the visual front-end. Recommend: (1) catalog as B-tier visual builder + note SRE runtime; (2) optional smoke of Docker Compose + simple agent graph; (3) no deeper eval queued unless local-LLM friction appears. Fits catalog as another self-hostable visual agent workspace alongside holaOS-style multi-harness tools.
- **Status**: STAY I1 reference (read 2026-11-07). Pin `3e1ea87e6718fdfdb24365b2184fbd1daa9f94f8` is main, 2026-03-31. Root LICENSE is MIT. package.json license fields say ISC. No install, no Docker, no code copy. Compose image `smythos/smythos-studio:alpha` is not this pin. Gap B is unchanged. Receipt: `eval/evq1107/smythos-studio/REPORT.md`. No Feature GO.
