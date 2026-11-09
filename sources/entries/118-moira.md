### Entry 118: MCP Moira — self-hosted workflow engine that walks an agent through a node graph with per-step completion conditions over MCP

- **URL**: https://github.com/moira-mcp/moira (Apache-2.0, TypeScript, 122 stars at this read; release v6.0.0, 2026-10-13)
- **Date**: 2026-10-14 (daily X intake)
- **Source / Poster**: @DanKornas, https://x.com/DanKornas/status/2110188594228867463
- **Summary / Key Claims** (upstream README and `docker-compose.yml`): "Agent Workflow Engine for AI agents." A workflow is a node graph; Agent Directive nodes give the agent one step with a directive, a completion condition and a JSON Schema for its inputs; Condition nodes route on ordered cases. The agent drives it through an MCP server at `/mcp`; a web UI and docs are served on the same port. Self-host is Docker Compose: a Traefik ingress plus one Moira container on SQLite, with administrator-approved local accounts. A hosted Moira Cloud also exists (not needed; we don't use it).
- **Why it matters here**: Our standing rule is to write a loop's exits before running it, and the operator wants long runs that stop on real exits. Moira makes each step's done-condition explicit and checks the agent's inputs against a schema, outside the model. It is a comparison point for how the orchestrator lane and the `./pfy decision` layer encode exits today, not a replacement yet.
- **Fit on nimo**: Only with Docker, which we haven't confirmed on nimo and which counts as a system change outside `~/DEVELOP` if it has to be installed (needs the operator first). The compose files and `.env` would live under `~/DEVELOP/pfy-mentat/tmp/moira`. The image is small next to nimo's RAM; no GPU or model needed.
- **Verified**: Not run. The Grok Bot box has no Docker. Only the smoke's exit-2 paths were exercised (no staged dir, no docker, image not pinned by digest), plus a stub `docker` to check that `compose down` runs after a failed `up`.
- **Finding**: upstream's compose and `.env.example` default to `ghcr.io/moira-mcp/moira:latest`, so a trial must pin the image by digest. The `.env` template holds an auth secret and an admin password: generate them on nimo, keep the file under `tmp/` (gitignored), and never paste them anywhere.
- **Extracted Repos / Tools**: https://github.com/moira-mcp/moira · https://github.com/moira-mcp/moira/blob/main/docs/VISION.md
- **TOOLS.md Link**: None yet. I0 awareness, catalog only. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_117_118.py --entry moira`. Needs a staged compose dir (`$MOIRA_DIR` or `tmp/moira`), docker with compose, and a digest-pinned `MOIRA_IMAGE` plus a digest-pinned Traefik `image:` line in the staged compose file (upstream uses the tag `traefik:v2.11.58`); otherwise exit 2. The smoke's clean env drops `DOCKER_HOST` and docker contexts (temp HOME), so only `/var/run/docker.sock` is used; for another socket on nimo set `MOIRA_DOCKER_HOST` (e.g. `unix:///run/user/$(id -u)/docker.sock`). Brings the stack up on port 18080, checks `/docs/` returns 200 and `/mcp` answers, then always runs `compose down -v` (named volumes removed). Receipt: `pipelines/smoke/moira/latest.json`.
- **Non-goals**: No Docker install, no cloud account, no workflow authored in this slice.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| No Docker on nimo | Smoke exits 2 | Stays catalog-only until the operator approves Docker or it's already there |
| Unpinned image | `:latest` changes under us | Smoke refuses anything but `@sha256:` |
| Secrets in `.env` | Leak into logs or git | Smoke never reads or prints them; `.env` stays under gitignored `tmp/` |
| Port clash | 8080 already used | Smoke defaults to 18080 (`$MOIRA_PORT`) |

- **Status**: STAY I1 after the 2026-11-07 nimo probe (`eval/evq1107/moira/`). Pin `b66b537a0465194d8806fa638776237d8cf853c5`, tag v6.0.0, cache checkout `~/.cache/pfy/tools/moira/`. Schema rejected 8/8 bad shapes. The condition stopped 3/3 FAIL reports. 4/4 schema-valid lies still finished. The completion string changed 0/2 routes. MCP server SKIPPED (account). Not a gate. No Feature GO.
