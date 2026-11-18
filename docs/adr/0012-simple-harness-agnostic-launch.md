# ADR-0012: Simple harness-agnostic launch surface (`./pfy`)

- **Status:** Accepted
- **Date:** 2026-07-31
- **Deciders:** operator (product simplicity push)
- **Related:** ADR-0002 (Grok primary), ADR-0011 (hybrid surfaces), G8 in DESIGN.md, T-0090

## Context

Out-of-box README setup is a **menu of Make targets** (env, Grok install, cage, LiteLLM, smokes). Competitors feel simpler:

| Product | Feel |
|---------|------|
| **Ollama** | Install once → `ollama run` / serve; tools attach to it |
| **Hermes / OpenCode on Ollama** | Integrated installer binds agent to models already running |
| **Exo** | `setup.sh` → `./exo.sh` |
| **Claude Code / Codex / Gemini** | One CLI, auth, go |
| **Grok Build** | One CLI + login |

Users want: **one command setup**, **one command start**, **any harness**, unfinished pieces **stubbed with issues** - not “call tooling separately.”

## Decision

1. **Overarching product goal G8:** *Simple deploy path* - `./pfy setup` then `./pfy start` is the default story; eval pipeline remains first-class but not the UX front door.
2. **Single launcher:** repo-root `./pfy` → `scripts/pfy` (also `make pfy ARGS='…'`).
3. **Harness registry:** `data/harnesses.json` lists inference + harnesses with `ready|partial|stub` and setup notes.
4. **Inference-first:** prefer Ollama up before launching a coding harness (Ollama→agent pattern).
5. **Grok remains default harness** (ADR-0002) but is **not exclusive** - OpenCode, Hermes, Claude Code, Codex, Gemini, Exo, Continue are first-class *slots*, stubbed until adapters ship.
6. **Stubs are honest:** `pfy start hermes` exits 2 with setup text + issue pointer; no fake “ready.”
7. **Track gaps as GitHub issues** labeled `harness-adapter` under epic “Simple launch surface.”

## Consequences

- README lead path becomes `./pfy setup` / `status` / `start` (Make still exists for platform builders).
- Product surface (T-0090) maps: setup≈onboard, stage, ship, plus start/harness.
- Full Exo/Hermes/Codex installers stay out of monorepo until adapters graduate stub→partial→ready.

## Rejected alternatives

| Option | Why not |
|--------|---------|
| Only document “use make help” | Failed simplicity test |
| Subtree-embed every harness | ADR-0003 bloat |
| Force single harness forever | Contradicts multi-tool catalog mission |
| Silent no-op stubs | Hides work; issues preferred |
