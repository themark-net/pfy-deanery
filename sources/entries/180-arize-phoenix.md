### Entry 180: Arize Phoenix: loopback trace sink for lane spans

- **URL**: https://github.com/Arize-ai/phoenix (Elastic-2.0, Python). PyPI `arize-phoenix==21.0.0`. Pin file `config/phoenix/version.txt`.
- **Date**: 2026-11-11
- **Source / Poster**: operator request (chat 2026-11-11). Not an X post.
- **Summary / Key Claims** (upstream docs plus the installed 21.0.0 tree; their product, our bind choices): one process serves a trace UI, OTLP/HTTP at `/v1/traces`, GraphQL at `/graphql`, and OTLP gRPC. Default store is SQLite under `PHOENIX_WORKING_DIR`. gRPC binds to `PHOENIX_HOST` (`phoenix/server/cli/commands/serve.py` passes `grpc_host=host`, and `host` is `get_env_host()`). `PHOENIX_ENABLE_MCP_SERVER=false` is accepted (`_bool_val` allows `true`/`false`; the default is true, so the unit sets false).
- **Why it matters here**: local and cloud lanes need a trace store and a UI. Deanery builds only a thin lane-graph view on top of that store. Phoenix already is the store. Langfuse (Entry 181) draws agent graphs and has a LiteLLM callback, and its self-host is too heavy for nimo.
- **Fit on nimo**: one process. SQLite under the pfy state dir (`PFY_STATE_DIR` or `~/.pfy-mentat`, same rule as `pfylib/registry.state_dir`). The operator's venv is about 446 MB under the tool cache (`python 3.13`, uv). Loopback only.
- **Findings**:
  - The upstream telemetry pixel defaults on. The unit sets `PHOENIX_TELEMETRY_ENABLED=false`.
  - The built-in agent assistant, its bash tool, web access, and GitHub tools default on. The unit turns them off.
  - gRPC binds to `PHOENIX_HOST`, not to a separate address. Keeping that host on loopback keeps gRPC on loopback.
  - Authentication stays off because the host is loopback and the unit does not set authentication variables.
  - HS-runtime-takeover means privilege or host control (`docs/ops/promotion-rules.md`). This is a loopback user service with `NoNewPrivileges=yes`. It does not ask for privilege and it does not control the host. `PrivateTmp` and `IPAddressAllow`/`IPAddressDeny` are omitted because they need a user namespace or BPF. That is not runtime takeover. The stage card therefore does not use those words, and `risk_class` stays `none`.
- **Extracted Repos / Tools**: https://github.com/Arize-ai/phoenix
- **TOOLS.md Link**: Arize Phoenix. Stage I1. `data/tools.json` row included. Service script `scripts/phoenix_service.sh`. Operator note `docs/ops/phoenix.md`.
- **Smoke**: no live server in CI. `python3 -m unittest tests.test_phoenix_service` checks the unit text, the host refusal, and `status` against a local stub. It does not call systemctl.
- **Non-goals**: no cloud Arize, no authentication or exposure beyond loopback, no Postgres.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Bind is not loopback | `PFY_PHOENIX_HOST` is `0.0.0.0` or a LAN address | `unit` and `enable` exit 2 and print no unit |
| Telemetry pixel | upstream default is on | unit sets `PHOENIX_TELEMETRY_ENABLED=false` |
| Assistant runs bash | upstream default is on | unit sets `PHOENIX_DISABLE_AGENT_ASSISTANT` and `PHOENIX_AGENTS_DISABLE_BASH` |
| Disk fills with spans | retention left unlimited | default 30 days via `PFY_PHOENIX_RETENTION_DAYS` |
| Writes land in the operator home | process home is `~` | unit sets `HOME` under the tool cache; data dir is the state dir |
| UI needed from another machine | loopback is not routed | SSH tunnel in `docs/ops/phoenix.md`; do not change the bind |
| Removal | traces deleted by mistake | `disable` removes the unit file only; delete the state dir in a separate step |

- **Status**: I1 staged evaluation. The venv is installed, the service script and operator doc are in-repo, and the promotion rules allow I1 (any evidence artifact, ceiling I1) and do not allow I3 (no verdict, no main-run receipt). ELv2 allows this internal self-host. It is not a managed service, and it is not copyleft, so Stage 0's license leg passes for our use. Not I3. Not a Feature GO.
