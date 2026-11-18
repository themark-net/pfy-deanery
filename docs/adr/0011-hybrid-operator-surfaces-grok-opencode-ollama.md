# ADR-0011: Hybrid operator surfaces (Grok + OpenCode + Ollama)

- **Date:** 2026-07-25
- **Status:** Accepted (operator surfaces). Inference fabric **superseded by [ADR-0014](0014-pluggable-local-inference-spine.md)**.
- **Deciders:** operator (direction); agent (write-up)

## Context

We need a **flexible** operator environment:

- **Grok Build CLI** remains excellent with a **subscription** for hard reasoning, planning, and interactive coding.
- **Local Ollama** (and LiteLLM routing) can absorb **simple, high-volume** tasks so tokenized cloud cost stays off the critical path.
- **OpenCode** is a flexible multi-model coding CLI; community/Ollama plugins also mention Hermes-class tooling. Catalog already lists OpenCode as a future parity target (T-0040) and rejects AgenC as primary (ADR-0010).

ADR-0002 made Grok the *primary* interface. That remains true for bootstrap depth (skills, cage image, auth import). It must **not** mean “only Grok forever” or “all tokens burn cloud.”

ADR-0006 already defines **local-only / balanced / max-performance** profiles. This ADR names the **CLI surfaces** that sit on those profiles.

## Decision

1. **Primary surface (subscription / hard tasks):** Grok Build CLI + agent-cage (unchanged default path: `make cage-grok`, first-party skills under `bootstrap/grok-cli/`).
2. **Secondary surface (local + flexible cloud split):** **OpenCode**, configured to talk to a **local OpenAI-compatible endpoint** (and optionally cloud providers) via LiteLLM. Default local spine is **ADR-0014** (FreeToken → llama-swap/llama-server → Ollama adapter).
3. **Inference fabric (superseded):** Ollama-on-host as *the* fabric is replaced by ADR-0014. LiteLLM recipes under `config/litellm/` keyed by `DEPLOY_PROFILE` (T-0012) still apply. In-cage local smoke remains `make smoke-litellm-ollama` (+ host gateway) when Ollama is the adapter.
4. **Portability rule:** First-party **process skills** (ADR, OQ, docs, one-shot, investigate, agent-loops, hermes-feedback, …) are authored as **SKILL.md packs** with **portable procedure bodies**. Grok-specific paths (`~/.grok/`, install.sh) stay in `bootstrap/grok-cli/`; OpenCode (and others) load the **same skill content** via a thin adapter package (`bootstrap/opencode/`) that does **not** fork process meaning.
5. **Task routing heuristic (balanced profile):**
   - **Local worker (OpenAI-compat):** structural checks, small edits, format/lint, simple generate/fix, eval-harness implement tasks when model fits, cheap loops.
   - **Grok (or strong cloud):** architecture, ambiguous product forks, hard multi-file design, cage-net debugging, high-stakes review.
6. **Hermes:** Keep **`/hermes-feedback` as pattern skill** (T-0048). Do **not** require Hermes Agent runtime or Ollama “Hermes plugin” for the stack. Optional host experiments are catalog/watch only.

## Rationale

- Matches cost reality: local for bulk, cloud for quality.
- OpenCode’s multi-provider model fits “local cloud split” better than forcing Grok to be the only local client.
- Skills-as-markdown already is the portable unit (ADR-0009 hybrid).
- Affirms ADR-0002 (primary bootstrap) without locking out OpenCode (ADR-0010 comparison set).

Rejected alternatives:

1. **OpenCode becomes sole primary** - Throws away Grok cage/auth/skills depth; subscription path is a first-class product goal.
2. **Grok-only forever** - Ignores local cost/latency and OpenCode flexibility.
3. **Hermes Agent as third primary runtime** - Pattern already ported; full runtime is another TUI/daemon surface (same class of risk as AgenC).
4. **Duplicate skill trees per CLI** - Drift hell; adapter + single SoT under bootstrap skills wins.

## Consequences

- Document operator paths: Grok daily, OpenCode + local OpenAI-compat for local-heavy work, LiteLLM for routing.
- `bootstrap/opencode/` holds install/config notes and skill-path mapping - not a second process doctrine.
- Eval: structural stays CLI-agnostic; implement-lane uses the ADR-0014 spine when present (`make eval-suite`).
- Cage remains Grok-image primary; OpenCode-in-cage is a later smoke (T-0040/T-0080), not a blocker for host OpenCode + local worker.
- **Inference spine superseded by ADR-0014.** Surfaces (Grok monitor / OpenCode worker) still stand.

## References

- ADR-0002, ADR-0006, ADR-0009, ADR-0010, **ADR-0014**
- `config/litellm/`, `examples/litellm-ollama/`
- `docs/ops/local-cloud-split.md`
- `bootstrap/opencode/README.md`
- TODO T-0040, T-0074, T-0080, #76
