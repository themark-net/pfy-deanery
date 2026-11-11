# Local / cloud split (pluggable local runtime + Grok monitor)

**Status:** Active (ADR-0011, **ADR-0014**)  
**Profiles:** [deployment-profiles.md](deployment-profiles.md) · ADR-0006  
**Smokes:** `make smoke-litellm-ollama` · `make eval-structural` · `make eval-suite` (needs a local OpenAI-compat server)  
**Detect:** `./scripts/detect-local-runtime.sh` · `./pfy status`

## Intent

Local inference is a **pluggable OpenAI-compatible endpoint**, not “Ollama forever.” Grok stays the **monitor**. Workers talk to `LOCAL_OPENAI_BASE_URL`.

| Work class | Prefer | Why |
|------------|--------|-----|
| Hard planning, ambiguous design, high-stakes review | **Grok Build** (subscription) | Quality |
| Bulk edit, simple codegen, format, local eval tasks | **Local runtime** via OpenCode or LiteLLM | Cost / latency |
| Structural gates (skills, scorers, JSON) | **No LLM** | `make eval-structural` |
| Flexible multi-provider coding CLI | **OpenCode** | Local + cloud in one client |

Grok remains **primary** for bootstrap and cage lab. OpenCode is **first-class secondary** for cost-aware routing.

## Pick a local runtime (ADR-0014)

Detect order (first healthy wins). Override: `PFY_LOCAL_RUNTIME`, `LOCAL_OPENAI_BASE_URL`.

| Order | Engine | Typical URL | Notes |
|-------|--------|-------------|-------|
| 1 | **llama-swap** (or live `llama-server`) | `http://127.0.0.1:8080/v1` | tok/s + hot-swap; 2026 community path off Ollama |
| 2 | **Shimmy** | `http://127.0.0.1:11435/v1` | tiny Rust drop-in (“FREE forever”); candidate, honest stub if missing |
| 3 | **Ollama** | `http://127.0.0.1:11434/v1` | first-class adapter (T-0101), not deleted |

Missing runtimes are **stub/missing**, never fake-healthy. Do not vendor engines (ADR-0003). Product surface stays `./pfy setup|status|start|stage|ship`.

```bash
./scripts/detect-local-runtime.sh   # {"engine","base_url","status"}
./pfy status
./pfy start                         # uses detected LOCAL_OPENAI_BASE_URL
```

## Topology

```text
                    ┌─────────────────────┐
   hard tasks       │  Grok Build CLI     │ ← subscription / xAI  (monitor)
                    │  (+ agent-cage)     │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
   process skills   │  SKILL.md packs     │  bootstrap/grok-cli/skills
   (portable)       │  same procedures    │  → also OpenCode adapter
                    └──────────┬──────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
   OpenCode CLI          LiteLLM router         Host tools
   (local/cloud)         config/litellm/*       make smoke-*
         │                     │
         └──────────► LOCAL_OPENAI_BASE_URL
                      llama-swap / llama-server :8080
                      Shimmy :11435
                      Ollama  :11434  (+ cage gateway :11435)
```

## Host quick start (local-only)

Any OpenAI-compat local server counts. Ollama remains the documented adapter path:

```bash
# 1. Local runtime on host (pick one)
#    llama-swap + llama-server   → often :8080
#    shimmy                      → often :11435
#    ollama serve                → :11434
ollama serve   # if using the Ollama adapter
ollama pull deepseek-coder:latest   # or qwen2.5:14b for eval gate

# 2. Gateway so cage can reach localhost Ollama (adapter-specific)
cd /path/to/pfy-mentat
./examples/litellm-ollama/host-ollama-gateway.sh start
curl -sS http://127.0.0.1:11434/api/tags | head

# 3. Profile
export DEPLOY_PROFILE=local-only
make env-check   # or env-init first

# 4. Prove path
make local-ollama-overlay-install
make local-ollama-up
make smoke-litellm-ollama     # in-cage completion

# 5. Structural always
make eval-structural

# 6. Model eval when gate model present
export EVAL_MODEL=qwen2.5:14b   # or smaller for smoke
make eval-suite                 # or SKIP if model missing
```

## OpenCode (secondary surface)

See [bootstrap/opencode/README.md](../../bootstrap/opencode/README.md).

Typical pattern:

- Point OpenCode at `LOCAL_OPENAI_BASE_URL` (detected OpenAI compat) for local models.
- Ollama default remains `http://127.0.0.1:11434/v1` if that adapter is selected.
- Optionally add cloud providers for hard tasks (operator keys in env — never git).
- Load the **same** skill directories via OpenCode’s skill/config paths (adapter docs).

## Grok (primary surface / monitor)

```bash
# subscription OIDC
grok login
make cage-grok          # skills + auth import + workspace
# or host: grok
```

Use Grok when the exit card’s **goal** needs high reasoning quality or cage integration debugging.

## How offload works **today** (read this)

Passing `eval-suite` with `deepseek-coder:6.7b` proves the **lab can drive that model**. It does **not** switch Grok Build’s brain to local inference.

| Mechanism | Offloads agent turns to local? |
|-----------|--------------------------------|
| Eval harness / LiteLLM smoke | Yes (test traffic only) |
| OpenCode (or any client) with `OPENAI_BASE_URL` / `LOCAL_OPENAI_BASE_URL` | **Yes — this is the worker** |
| Grok CLI session | No (subscription/cloud) — use as **monitor** |
| Dual session: OpenCode implements, Grok reviews DoD | **`make worker-stage`** + two terminals — [worker-monitor.md](worker-monitor.md) (T-0085) |

**Offload recipe (T-0085):**

```bash
make worker-stage    # smoke + worker.env + monitor-brief.md

# Terminal A — worker
set -a; . examples/opencode-ollama/.generated/worker.env; set +a
# worker.env may still say Ollama; override if detect-local-runtime picked another engine
export LOCAL_OPENAI_BASE_URL="${LOCAL_OPENAI_BASE_URL:-http://127.0.0.1:11434/v1}"
opencode

# Terminal B — monitor
grok   # open monitor-brief.md · /worker-monitor · /agent-loops plan
```

Persist worker model: `LOCAL_CODER_MODEL=deepseek-coder:6.7b` in `.env` (or from `make eval-select-models`).

## Routing heuristic (agents)

Before a multi-step loop, set exit card **budget** and **model tier**:

| Signal | Route |
|--------|--------|
| `make eval-structural` / json / skill text | No LLM |
| Single-file fix, known pattern, eval implement task | **Local worker** (`LOCAL_CODER_MODEL` / OpenCode→local OpenAI-compat) |
| Multi-module design, ADR, unclear product, review | **Grok monitor** |
| Worker failed 3× / no-progress | Escalate to Grok |
| `DEPLOY_PROFILE=local-only` | Never auto-call cloud |
| `balanced` | Local worker first; Grok monitor |
| `max-performance` | Grok first; local fallback |

## Hermes / plugins

- **`/hermes-feedback`** = first-party **pattern** skill (memory / auto-skill / curator).  
- Ollama or OpenCode **Hermes plugins** = optional host experiments; **not** required runtime; do not vendor Hermes Agent (same posture as ADR-0010 for extra primaries).

## Related

- ADR-0014 (pluggable local spine) · ADR-0011 · ADR-0002 · ADR-0006 · ADR-0003 (no vendoring)  
- [human-decision-inventory.md](human-decision-inventory.md)  
- [loop-engineering.md](loop-engineering.md)  
- Issue [#76](https://github.com/themark-net/pfy-deanery/issues/76)
