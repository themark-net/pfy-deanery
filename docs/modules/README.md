# Module docs (operators + agents)

Short structural maps for first-party packages in this repo. Deep design stays in ADRs; runbooks in `docs/ops/`.

| Module | Path | Doc |
|--------|------|-----|
| Consultant eval pack | `docs/ops/consultant-eval.md` | [consultant-eval.md](../ops/consultant-eval.md) |
| `./pfy` simple surface | `scripts/pfy` | [pfy.md](pfy.md) |
| Toolset × harness handoff + hedge | `pfylib/` + `data/toolsets.json` | [pfylib.md](pfylib.md). ADR-0017 is cited and the file is not in `docs/adr/` yet ([pfy-launcher.md](../design/pfy-launcher.md)) |
| Launch wizard | `scripts/pfy_launch_wizard_225.py` | [launch-wizard.md](launch-wizard.md) · [ops/launch-wizard.md](../ops/launch-wizard.md) |
| Session compose | `scripts/pfy_session_compose_224.py` | [session-compose.md](session-compose.md) · [ops/session-compose.md](../ops/session-compose.md) |
| OpenContext `oc` handoff | `scripts/pfy_opencontext_205.py` | [opencontext.md](opencontext.md) · [ops/opencontext.md](../ops/opencontext.md) |
| Code-graph (Axon) | `scripts/pfy_code_graph_215.py` | [code-graph.md](code-graph.md) · [ops/code-graph.md](../ops/code-graph.md) |
| Attach mode | `scripts/pfy_attach_mode_208.py` | [attach-mode.md](attach-mode.md) · [ops/attach-mode.md](../ops/attach-mode.md) |
| Orchestration loops | `scripts/pfy_orchestration_213.py` | [attach-mode.md](attach-mode.md) · [ops/attach-mode.md](../ops/attach-mode.md) |
| Recommend / try models | `scripts/pfy_recommend_models_207.py` | [recommend-models.md](recommend-models.md) · [ops/recommend-models.md](../ops/recommend-models.md) |
| Catalog ask / queue | `scripts/pfy_catalog_ask_queue_209.py` | [catalog-ask-queue.md](catalog-ask-queue.md) · [ops/catalog-ask-queue.md](../ops/catalog-ask-queue.md) |
| Live org queue | `scripts/pfy_live_org_queue_214.py` | [live-org-queue.md](live-org-queue.md) · [ops/live-org-queue.md](../ops/live-org-queue.md) |
| Local runtime detector | `scripts/detect-local-runtime.sh` | [detect-local-runtime.md](detect-local-runtime.md) |
| Product env-stage | `scripts/env-stage.sh` | [env-stage.md](env-stage.md) |
| Grok CLI bootstrap | `bootstrap/grok-cli/` | [bootstrap-grok-cli.md](bootstrap-grok-cli.md) |
| OpenCode host adapter | `bootstrap/opencode/` | [opencode-adapter.md](opencode-adapter.md) |
| Hermes runtime adapter | `hermes` / `hermes-agent` | [hermes-adapter.md](hermes-adapter.md) |
| Claude Code adapter | `claude` | [claude-code-adapter.md](claude-code-adapter.md) |
| Codex adapter | `codex` | [codex-adapter.md](codex-adapter.md) |
| Gemini adapter | `gemini` / `gemini-cli` | [gemini-adapter.md](gemini-adapter.md) |
| Exo optional lab adapter | `bootstrap/exo/` + `exo.sh` | [exo-adapter.md](exo-adapter.md) |
| Continue config recipe | `bootstrap/continue/` | [continue-recipe.md](continue-recipe.md) |
| project-process scaffold | `bootstrap/project-process/` | [bootstrap-project-process.md](bootstrap-project-process.md) |
| agent-cage lab | `harness/agent-cage/` | [harness-agent-cage.md](harness-agent-cage.md) |
| write-guard MCP | `harness/write-guard-mcp/` | [write-guard-mcp.md](write-guard-mcp.md) |
| In-cage tool smokes | `examples/` + `pipelines/smoke/` | [examples-smokes.md](examples-smokes.md) |

**Related ops (not a package):** [gstack role recipes](../ops/gstack-role-recipes.md) (T-0014) · [gstack skill port comparison](../ops/gstack-skill-port-comparison.md) (attributes + single-skill recommendation).

**Catalog (not modules):** [TOOLS.md](../../TOOLS.md) · [data/tools.json](../../data/tools.json) · [sources/x-posts.md](../../sources/x-posts.md)  
**Deploy map:** [docs/ops/DEPLOY.md](../ops/DEPLOY.md)
- [gab-228.md](gab-228.md) - Gab cloud + local recommend sync (#228)
- [jev-230.md](jev-230.md) - Jev-style decision layer (#230; CUA-S1-FORMS primary local)
