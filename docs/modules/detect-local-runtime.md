# Module: `scripts/detect-local-runtime.sh`

**Purpose:** ADR-0014 probe. Prints JSON `{"engine","base_url","status"}`. Ready HTTP beats PATH-only partial. Engines are not vendored.

## Entry

```bash
bash scripts/detect-local-runtime.sh
# overrides:
export PFY_LOCAL_RUNTIME=freetoken   # or llama-swap | llama-server | ollama
export LOCAL_OPENAI_BASE_URL=http://127.0.0.1:1919/v1
```

Order: FreeToken :1919 → llama-swap :9292 → llama-server :8080 → Ollama :11434 → Shimmy :11435.

Probe: `GET /v1/models`, `/health`, or `/api/tags`.

## Not yet

- Auto-install of any engine
- Ollama pin: API up → ready, binary only → partial, no binary → missing. `./pfy start ollama` is the adapter (health + default model), not the detector alone.
- `./pfy up` starts shimmy only after FreeToken, llama-swap, llama-server, and Ollama are not healthy (`shimmy serve --bind 127.0.0.1:11435`)
