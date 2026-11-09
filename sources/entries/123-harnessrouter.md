### Entry 123: HarnessRouter Community Edition - one self-hosted API in front of many agent harnesses (Unified Harness Protocol)

- **URL**: https://github.com/HarnessRouter/harnessrouter (Apache-2.0, Python, about 3,050 stars at this read; release v0.34.2, image `harnessrouter/harnessrouter` 0.34.2, digest `sha256:db412234…9ad5`)
- **Date**: 2026-10-16 (daily X intake)
- **Source / Poster**: @_avichawla, https://x.com/_avichawla/status/2110993106594316306
- **Summary / Key Claims** (upstream README at v0.34.2): one Docker container (Console, Gateway, Runner) that runs harnesses such as Codex, Claude Code, Hermes and Pi behind one OpenAI Responses-compatible API, implementing the Unified Harness Protocol (UHP, https://unifiedharnessprotocol.org): persistent sessions, streaming progress, files, artifacts, cancellation and structured failures. Switching harness becomes a routing choice instead of a rewrite. Secrets passed through `env`/`vault:` references are redacted from responses, traces and stored records. No HarnessRouter account needed for Community Edition; a managed cloud exists but is optional.
- **Why it matters here**: the org runs several harnesses (Grok Build, Cursor, OpenCode, Grok CLI forks) and compares them by hand. UHP is a candidate common contract for running the same pfy-mentat task through different harnesses and comparing results, and for a future "harness choice as a routing decision" step next to Entry 122. Reference design only for now.
- **Fit on nimo**: The pinned image boots. Docker 29.6.0 is on this host. Image size is 805671098 bytes. A full backend set still downloads third-party CLIs onto the volume (the README says about 4 GB). `.env.example` at v0.34.2 documents an `openai-api` connection with a `base_url` for a local OpenAI-compatible endpoint. This lane did not send a task and did not add a provider key.
- **Verified on the Grok Bot box**: nothing ran; there is no Docker on the box. Read the README at v0.34.2 and the Docker Hub tag list only. The smoke's no-docker path exits 2 as intended. A task has not run on that box.
- **Verified on nimo (2026-11-07 evq)**: tag `v0.34.2` is commit `0c43dc333abb1db1954bb36e8dc712724af7550b`. Docker Hub tag digest `sha256:db412234ea41162e70ecf92f0140402f7cf1fc2a7e00db9180906c7447eb9ad5` matches the smoke pin. With `HR_BACKENDS=none` the console answered `GET /` 200 on `127.0.0.1:39217` and a keyless `POST /api/harness/v1/responses` got 401. Ready in 1.186 s. No harness CLI installed. No task. Report: `ops:eval/evq1107/harnessrouter/REPORT.md`.
- **Finding**: the Console starts with a default password that the README says to change before exposing it; keep the port on loopback. CE issues its own API key, shown once; it must go straight into a secret store. The named volume keeps the database, installed harness CLIs and workspaces, so `docker rm` alone does not clear state (the smoke also removes its volume). Image tags move daily; the smoke pins the digest.
- **Extracted Repos / Tools**: https://github.com/HarnessRouter/harnessrouter · https://hub.docker.com/r/harnessrouter/harnessrouter · https://unifiedharnessprotocol.org · https://github.com/aenawi/uhp-go (third-party Go UHP server, 4 stars, not evaluated)
- **TOOLS.md Link**: None yet. I0 awareness, catalog only. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_122_124.py --entry harnessrouter`. Needs docker; runs the digest-pinned image on `127.0.0.1:$HR_SMOKE_PORT` (default 3917), waits for the Console, checks that a keyless `POST /api/harness/v1/responses` is refused (401/403), then removes the container and volume. No provider key, no CE key, no task. Receipt: `pipelines/smoke/harnessrouter/latest.json`.
- **Non-goals**: No provider key added, no harness run, no cloud upload, nothing exposed beyond loopback.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| No Docker on the host | Smoke exits 2 | This host has Docker 29.6.0. A host without it stays catalog-only |
| Local task never measured | Wiring says a custom `base_url` is accepted; no completion was sent | Stay I0 until a later ticket records a stub hit |
| Paid or hosted provider | A hosted model still needs a key | This lane stored none. A local base URL was not called |
| Default Console password exposed | Anyone on the network can sign in | Loopback bind only; change the password on first start |
| Smoke happy path untested | First Docker run fails on a smoke bug (endpoint path, status code) | This lane's keyless POST got 401, which is the smoke's expected refusal. A task is still unrun |

- **Status**: STAY I0 (evq1107, 2026-11-07). 0 weight files and 0 engines. 15 of 26 default backends map a custom connection to `openai-api`. 8 map to `tokenrouter`. gemini, systemone, and qoder have no custom row. Keyless POST 401. Ready 1.186 s. No task. Not a gate. No Feature GO.
