# ADR-0014: Pluggable local inference spine

**Status:** Accepted  
**Date:** 2026-08-24  
**Deciders:** CEO (org) · owner named the X engine  
**Issue:** [#76](https://github.com/themark-net/pfy-deanery/issues/76) · PR [#77](https://github.com/themark-net/pfy-deanery/pull/77)

## Context

ADR-0011 made **Ollama** the local worker spine with Grok as monitor. G8 / ADR-0012 still wants `./pfy setup|status|start`: inference up once, harnesses attach.

Ollama-only is stale. The engine people have been discussing on X as the Ollama replacement is **[FreeToken](https://github.com/FlashML-org/FreeToken)** (FlashML / Berkeley+MIT, `ft serve`, OpenAI + Anthropic on **:1919**). It is an edge-native MoE serving engine (bandwidth-adaptive CPU–GPU, FTW weights) claiming ~1.5–2.3× vs llama.cpp / Ollama / KTransformers on agentic decode, plus frontier MoE on a workstation GPU.

llama.cpp `llama-server` + [llama-swap](https://github.com/mostlygeek/llama-swap) remains the GGUF / hot-swap path. Ollama stays an adapter (T-0101).

An earlier draft of this ADR named **Shimmy** (“FREE forever”) as that X engine. Owner correction 2026-08-23: the name is **FreeToken**. Shimmy is optional catalog, not the spine.

## Decision

Local inference is a **pluggable OpenAI-compatible (and, for FreeToken, Anthropic-compatible) endpoint**, not a vendor.

**Detect order** (first healthy wins; override `PFY_LOCAL_RUNTIME` / `LOCAL_OPENAI_BASE_URL`):

1. **FreeToken** (`ft` / `freetoken`, typically `http://127.0.0.1:1919/v1`) — preferred local spine for MoE / agent workers
2. **llama-swap** or live **llama-server** — GGUF tok/s + hot-swap
3. **Ollama** — first-class adapter, never deleted
4. **Shimmy** — optional detect only, not preferred

Workers talk to one `LOCAL_OPENAI_BASE_URL`. Grok remains monitor (ADR-0002, ADR-0011).

`./pfy status` is `ready | partial | stub | missing`. Missing is honest.

Do not vendor FreeToken / llama.cpp / Shimmy (ADR-0003).

## Rejected alternatives

| Option | Why not |
|--------|--------|
| Ollama-only | Blocks FreeToken and llama.cpp performance path. |
| Shimmy as the X engine | Wrong name; owner identified FreeToken. |
| FreeToken-only | NVIDIA-oriented MoE path; GGUF users still need llama.cpp / Ollama. |
| llama.cpp-direct-only | No hot-swap; llama-swap exists. |
| vLLM as default | Cluster serving, not laptop-first. |
| Vendor any engine | ADR-0003 / DESIGN non-goals. |
