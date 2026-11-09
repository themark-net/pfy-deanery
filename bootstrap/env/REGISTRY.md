# Environment variable registry

**Purpose:** Single inventory of variables used by this catalog stack.  
**Secrets never go in git.** Only names, purpose, profile affinity, and provisioning rules live here.

When integrating a new tool, **add a row here in the same PR** as the integration.

## Provisioning rules

| Rule | Practice |
|------|----------|
| Init | `make env-init` copies `.env.example` → `.env` (gitignored) if missing |
| Secrets | Operator fills `.env` or exports vars; never commit `.env` |
| Cage | Non-secret vars may be passed into agent-cage via compose env / policy; secrets only via runtime env, not image layers |
| Profiles | `DEPLOY_PROFILE=local-only\|balanced\|max-performance` selects which backends are required vs optional |
| Divergence | Profile-specific overrides in `config/profiles/<name>.env` (no secrets) + optional `.env.local` (gitignored) |

## Registry

| Variable | Secret? | Required profiles | Default / example | Used by | Notes |
|----------|---------|-------------------|-------------------|---------|-------|
| `DEPLOY_PROFILE` | no | all | `balanced` | bootstrap, harness, recipes | Selects local-only / balanced / max-performance |
| `AGENTCAGE_DIR` | no | harness | `$HOME/.agentcage` | harness/agent-cage, agentcage CLI | Runtime cage project after `init` |
| `PATH` (incl. `~/.local/bin`) | no | all | — | grok, agentcage, uv tools | Document in README only |
| `XAI_API_KEY` | **yes** | optional / CI | — | Grok **API key fallback** only | Used if **no** session in `auth.json`. Subscription users usually **do not** need this |
| `GAB_API_KEY` | **yes** | optional | — | Gab cloud lane (`https://gab.ai/v1`) | Plus/max plan; docs gab.ai/docs/api-auth. Not a local GGUF host |
| `PFY_GAB_MODEL` | no | optional | `auto` | Gab cloud model id | `auto` (cloud router) or pin-by-id from GET /v1/models |
| `PFY_GAB_OFFLINE` | no | CI | `1` in CI | Force Gab `/models` fixture | Offline fixture `scripts/fixtures/gab_models_v1.json` |
| `TYPESAFE_API_KEY` | **yes** | optional | — | TypeSafe Jev cloud (`jev-1.13.0`) | Optional. Missing on TypeSafe path → FAIL+next or CUA-S1-FORMS. Never required for #230 smoke |
| `PFY_JEV_MODEL` | no | optional | `jev-1.13.0` | TypeSafe model id | Cloud path only. Under `PFY_JEV_LAYA_SHADOW` unset → `english` for the shadow call |
| `PFY_JEV_CONF_GATE` | no | optional | `0.85` | Decision auto-act margin | Below gate → FAIL / escalate; not percent-correct |
| `PFY_JEV_OFFLINE` | no | CI | `1` in CI | Skip TypeSafe network | operator-free CUA-S1-FORMS selftest |
| `PFY_JEV_LAYA_SHADOW` | no | optional | unset / `0` | Opt-in Laya english second opinion | When `1` and CUA would auto-act, disagree or Laya error → escalate. Default off. Not a lane swap |
| `PFY_JEV_TYPESAFE_URL` | no | optional | TypeSafe cloud | Local `laya-serve` override | Shadow refuses the cloud default; point at `http://127.0.0.1:8765/v1/systemone` |
| `PFY_JEV_TYPESAFE_TIMEOUT` | no | optional | `8` | TypeSafe / laya-serve POST timeout | Trial may raise this for CPU |
| Host `~/.grok/auth.json` | **yes** | Grok Build default | created by `grok login` | Grok CLI OIDC/browser session | **Primary auth** for interactive Grok; mode `oidc` + refresh_token |
| Cage `~/.agentcage/grok-home/auth.json` | **yes** | grok-in-cage | via `make cage-grok-auth-import` | Grok inside agent container | Copy of host session or device-login result; chmod 600 |
| `GROK_HOME` | no | optional | `$HOME/.grok` | Grok CLI state dir | In cage: `/home/agent/.grok` (volume) |
| `POLICY` | no | harness | `default`, `coding-agent-grok`, or `coding-agent-local` | agent-cage compose | `coding-agent-local` allows `host.docker.internal` for host Ollama |
| `OPENAI_API_KEY` | **yes** | optional | — | LiteLLM OpenAI backends | Optional cloud fallback |
| `ANTHROPIC_API_KEY` | **yes** | optional | — | Claude-in-cage experiments | Optional |
| `OPENAI_BASE_URL` | no | local-only, balanced | Host: `http://127.0.0.1:11434/v1` · **Cage:** `http://host.docker.internal:11435/v1` | LiteLLM, agents → Ollama | Inside cage use **gateway port 11435** (user-space forward to host Ollama). Stock Ollama often binds 127.0.0.1 only |
| `OLLAMA_HOST` | no | local-only, balanced | Host: `http://127.0.0.1:11434` · **Cage:** `http://host.docker.internal:11435` | Ollama clients | Same gateway split as `OPENAI_BASE_URL` |
| `OLLAMA_GATEWAY_PORT` | no | local-only, balanced (cage smokes) | `11435` | `examples/litellm-ollama/host-ollama-gateway.sh` | Publishes `0.0.0.0:11435` → `127.0.0.1:11434` without sudo |
| `LITELLM_SMOKE_MODEL` | no | smoke | `deepseek-coder:latest` | `make smoke-litellm-ollama` | Prefer smallest local coding model already pulled |
| `LOCAL_CODER_MODEL` | no | local-only, balanced | `deepseek-coder:6.7b` | OpenCode/worker agents, eval defaults | Bulk implement / completion; set via `eval-select-models`. `#207` try pins `$PFY_STATE_DIR/pinned-model` (FreeToken also `ft-model`) |
| `LOCAL_TOOLS_MODEL` | no | optional | *(empty if split)* | OpenCode agent / voice auto-agent | Tools-capable Ollama tag from `make eval-select-tools-model` (T-0093) |
| `TOOLS_MODE` | no | optional | `split` \| `local_tools` | worker-stage / tools-model.env | Explicit tool-split vs local tools |
| `OPENCODE_AGENT_MODEL` | no | optional | tools model or coder | OpenCode agent runs | Prefer `LOCAL_TOOLS_MODEL` when set |
| `EVAL_MODEL` / `EVAL_GATE_MODEL` | no | eval | from select or profile | `make eval-suite` | Gate for scored tasks |
| `EVAL_GATE_CANDIDATES` | no | eval-auto | set by select script | `make eval-auto` | Fallback list if gate fails chat tasks |
| `LITELLM_MASTER_KEY` | **yes** | optional | — | LiteLLM proxy auth | If running shared LiteLLM |
| `LITELLM_CONFIG` | no | all (when using LiteLLM) | `config/litellm/<profile>.yaml` | LiteLLM | `local-only.yaml` · `balanced.yaml` · `max-performance.yaml` — see `config/litellm/README.md` |
| `OLLAMA_API_BASE` | no | local-only, balanced, max (fallback) | `http://127.0.0.1:11434` | LiteLLM `ollama/*` | No `/v1` suffix; cage: `http://host.docker.internal:11435` |
| `LITELLM_CLOUD_MODEL` | no | balanced, max-performance | `xai/grok-3` | LiteLLM cloud aliases | Override if provider model ID differs |
| `GROK_HOME` | no | all | `$HOME/.grok` | Grok CLI | Skills, config, sessions |
| `CODEBASE_MEMORY_MCP` | no | optional | `codebase-memory-mcp` | Grok MCP | Command on PATH |
| `WRITE_GUARD_MODE` | no | all (when MCP enabled) | `audit` | write-guard MCP (planned) | `off` \| `audit` \| `enforce` |
| `WRITE_GUARD_ROOTS` | no | cage | `/workspace` | write-guard MCP | Allowed write roots |
| `HF_TOKEN` | **yes** | optional | — | colibri/HF weights | Only if OQ-0008 allows downloads |
| `GITHUB_TOKEN` | **yes** | optional | — | gh, private clones | Prefer fine-scoped PAT |
| `VOICE_STT_WHISPER_MODEL` | no | optional | `base.en` | `examples/voice-stt-edge` local Whisper | Prefer `tiny.en`/`base.en`/`small.en` for English commands |
| `VOICE_STT_LANGUAGE` | no | optional | `en` | local STT | ISO language code for Whisper |
| `VOICE_ARECORD_DEVICE` | no | optional | system default | `arecord -D` | e.g. `default`, `pulse`, or `plughw:0,0` from `arecord -l` |
| `VOICE_STT_TRY_OLLAMA` | no | optional | unset | auto backend | Set `1` to try Ollama audio API (usually 404 without a whisper model) |
| `VOICE_STT_OLLAMA_MODEL` | no | optional | `whisper` | voice-stt-edge ollama backend | Experimental; only if Ollama exposes audio transcription |
| `VOICE_STT_OUT` | no | smoke | `examples/voice-stt-edge/.generated` | `make smoke-voice-stt` | Override artifact dir |
| `VOICE_LISTEN_SECONDS` | no | optional | `5` | `make voice-listen` | Mic duration |
| `VOICE_TARGET` | no | optional | `monitor` | `make voice-listen` | `monitor` \| `worker` \| `raw` |
| `VOICE_HANDOFF` | no | optional | `0` | `make voice-listen` | `1` = exec handoff after STT |
| `VOICE_STT_PYTHON` | no | optional | `examples/voice-stt-edge/.venv/bin/python` | `python.sh` / listen | Override interpreter; default prefers project venv |
| `VOICE_REMOTE_HOST` | no | optional | `127.0.0.1` | `make voice-remote` | Use `0.0.0.0` for Android on Tailscale/LAN |
| `VOICE_REMOTE_PORT` | no | optional | `8787` | voice-remote | HTTP port |
| `VOICE_REMOTE_TOKEN` | **yes** (shared secret) | remote | auto `.generated/remote.token` | voice-remote auth | Never commit; phone UI Bearer token |
| `VOICE_AUTO_AGENT` | no | optional | `0` (off) | voice auto-runner | `0` · **`1`/`orchestrate`=dual-tier** · `opencode`=local · `grok`=high-only · `mock` |
| `VOICE_ROUTE` | no | optional | `high-first` | T-0096 orchestrator | `high-first` \| `local-first` \| `local-only` \| `high-only` |
| `VOICE_ORCH_MOCK` | no | optional | `0` | orchestrator smoke | `1` = mock high+low tiers (no cloud) |
| `VOICE_ORCH_REVIEW` | no | optional | `0` | high-first | `1` = Grok reviews after local implement |
| `VOICE_ORCH_FALLBACK_LOCAL` | no | optional | `1` | high-first | If high fails, try local |
| `VOICE_AGENT_MAX_TURNS` | no | optional | `8` | agent_runner / grok | `--max-turns` |
| `VOICE_AGENT_TIMEOUT` | no | optional | `600` | agent_runner | Seconds |
| `VOICE_AGENT_ALWAYS_APPROVE` | no | optional | `1` | agent_runner | Passes grok `--always-approve` when set |
| `VOICE_AGENT_REPO` | no | optional | repo root | remote_server / runner | Grok `--cwd` |
| `OPENCONTEXT_BIN` | no | optional | `oc` on PATH | `./pfy context`, Attach grok/opencode/hermes/codex/claude | Set when `oc` exists; skip if missing (#205) |
| `OPENCONTEXT_CONTEXTS_ROOT` | no | optional | `$HOME/.opencontext/contexts` | `oc` CLI / Attach child env | Global context library |
| `OPENCONTEXT_DB_PATH` | no | optional | `$HOME/.opencontext/opencontext.db` | `oc` CLI / Attach child env | OpenContext SQLite store |
| `PFY_ATTACH_MODE` | no | optional | `bare` | Attach OpenCode/Hermes/Grok/Codex/Claude (#208) | `bare` \| `orchestration` \| `code-graph`; one mode at a time |
| `PFY_ATTACH_HANDOFF` | no | optional | `$PFY_STATE_DIR/attach-mode-handoff.md` | Attach child env | Mode AGENTS/prompt artifact |
| `PFY_ATTACH_PROMPT` | no | optional | `$PFY_STATE_DIR/attach-mode-prompt.md` | Attach child env | Short mode prompt |
| `PFY_LOOP_CARD` | no | optional | `$PFY_STATE_DIR/loop-card.md` | Attach child env / Loop (#213) | 8-exit card after orchestration start |
| `PFY_LOOP_EVIDENCE` | no | optional | `$PFY_STATE_DIR/loop-evidence.json` | Attach child env / Loop (#213) | Last loop/monitor evidence (not slogan-only) |
| `PFY_LOOP_PROMPT` | no | optional | `$PFY_STATE_DIR/loop-prompt.md` | Attach child env (#213) | Continue-from-card prompt |
| `PFY_GRAPH_PATH` | no | optional | (unset) | `./pfy code-graph`, Attach grok/opencode/hermes/codex/claude (#215) | `axon` \| `codebase-memory`; never invent axon |
| `AXON_BIN` | no | optional | `axon` on PATH | `./pfy code-graph`, Attach child env (#215) | Set only when path=axon |
| `PFY_GRAPH_EVIDENCE` | no | optional | `$PFY_STATE_DIR/graph-evidence.json` | Attach child env / Loop (#215) | Last code-graph path evidence |
| `PFY_CATALOG_ASK_PROMPT` | no | optional | `$PFY_STATE_DIR/catalog-ask-prompt.md` | Attach child env / Tools (#209) | Next-launch implement prompt |
| `PFY_CATALOG_ASK_HANDOFF` | no | optional | `$PFY_STATE_DIR/catalog-ask-handoff.md` | Attach child env / Tools (#209) | Catalog ask handoff notes |
| `GITHUB_TOKEN` / `GH_TOKEN` | no | optional | (unset) | Tools Queue for org (#214) | API create/refresh when `gh` missing |
| `PFY_STATE_DIR` launch-wizard.json | no | optional | `$PFY_STATE_DIR/launch-wizard.json` | Loop launch wizard (#225) | composed runtime · lane · toolsets · harness |
| `PFY_SESSION_BRIEF` | no | optional | `$PFY_STATE_DIR/session-compose.md` | Launch session child env (#224) | Honest lane + enabled tools + how-to |
| `PFY_SESSION_PROMPT` | no | optional | `$PFY_STATE_DIR/session-compose-prompt.md` | Launch session child env (#224) | One-line prompt card |

## Profile affinity

| Profile | Must have | Optional | Must not require |
|---------|-----------|----------|------------------|
| `local-only` | Ollama (or other local OpenAI-compatible) | write-guard, codebase-memory | Cloud API keys for core path |
| `balanced` | Local backend + at least one cloud key (e.g. XAI) | LiteLLM, cage MCP | — |
| `max-performance` | Cloud keys (XAI and/or others) | Local as fallback | Blocking on local GPU |

See [config/profiles/](../../config/profiles/) and [docs/ops/deployment-profiles.md](../../docs/ops/deployment-profiles.md).
