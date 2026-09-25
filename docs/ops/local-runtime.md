# Local inference runtime (pluggable)

**ADR:** [0014](../adr/0014-pluggable-local-inference-spine.md)

Owner bar: `./pfy start` / `./pfy up` = inference + env-stage + active harness. `./pfy models` is inspect-only. `./pfy models pull` routes to the live engine (FreeToken records the name for next `ft serve --model`; Ollama pulls; llama-* honest skip). `./pfy models recommend` / `try` rank and pull a host-fit model not yet pulled (#207); llama with no pull is FAIL, not a fake best list.

## Preferred: FreeToken

[FreeToken](https://github.com/FlashML-org/FreeToken) (`uv pip install "freetoken[accel]"`, then `ft serve --model <hf-or-path>`; `./pfy up` uses **`PFY_FT_MODEL`**).
OpenAI + Anthropic APIs on **:1919**. Desktop: [flashml.ai](https://www.flashml.ai/).

## Fallback order

`scripts/detect-local-runtime.sh` (first live wins):

1. **freetoken** (`ft` / `freetoken`) — :1919
2. **llama-swap** — :9292
3. **llama-server** — :8080
4. **Ollama** — :11434 adapter (not the spine). `./pfy start ollama` checks health and the default model (`PFY_OLLAMA_MODEL`, then `LOCAL_CODER_MODEL`, then `OLLAMA_MODEL`) even if another engine is already up.
5. **Shimmy** — optional last, not preferred

```bash
export PFY_LOCAL_RUNTIME=freetoken
export LOCAL_OPENAI_BASE_URL=http://127.0.0.1:1919/v1
```

Workers (OpenCode, LiteLLM, eval) use `LOCAL_OPENAI_BASE_URL`. Grok stays the monitor.

Missing binaries are `missing` / `partial`, never fake-healthy. Do not vendor engines.
