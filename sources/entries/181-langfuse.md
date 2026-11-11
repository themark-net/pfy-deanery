### Entry 181: Langfuse: considered alternative, too heavy for nimo

- **URL**: https://github.com/langfuse/langfuse (MIT, TypeScript). Core outside the ee directories is MIT Expat. The upstream LICENSE (read 2026-11-11) puts `ee/`, `web/src/ee/`, `worker/src/ee/`, and `packages/shared/src/server/ee/` under `ee/LICENSE`, a commercial enterprise license. The core runs without those modules.
- **Date**: 2026-11-11
- **Source / Poster**: operator request (chat 2026-11-11), considered next to Phoenix (Entry 180). Not an X post.
- **Summary / Key Claims** (upstream README and LICENSE; their claims): open-core trace UI. Agent Graphs draws loops. LiteLLM has a native Langfuse callback. Self-host of the stack we would need is not a single process.
- **Why it matters here**: it is the obvious other trace UI. Agent Graphs is closer to a lane picture than Phoenix's table of spans. We still pick Phoenix, and Deanery draws the thin lane-graph view itself.
- **Fit on nimo**: no. A self-host that matches the documented stack wants Postgres, ClickHouse, Redis, and S3-compatible object storage (MinIO). That is too heavy for a sink on this machine. No install, no venv, no unit.
- **Findings**:
  - MIT applies to the core. Enterprise modules stay commercial. We did not install either.
  - The LiteLLM callback does not remove the database stack.
- **Extracted Repos / Tools**: https://github.com/langfuse/langfuse
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: none. Not installed.
- **Non-goals**: no self-host on nimo, no Postgres, no ClickHouse, no Redis, no object storage, no unit file.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Treated as the sink | a compose stack is started on nimo | keep the stage at I0; Phoenix (Entry 180) is the sink |
| EE modules used by accident | a license-key feature is switched on | do not install; core vs ee is upstream's split, not ours to host |
| LiteLLM callback pointed here | spans leave the box or wait on a down stack | point traces at the loopback Phoenix OTLP port |

- **Status**: I0 awareness. Not accepted into the catalog table. Revisit only if nimo grows a database host and Phoenix is no longer enough.
