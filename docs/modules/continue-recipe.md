# Module: Continue config recipe

**Purpose:** Point Continue at `LOCAL_OPENAI_BASE_URL` from the ADR-0014 detector. Recipe only - not a CLI harness. Do not exec the IDE. Do not vendor Continue sources.

## Entry

Copy [`bootstrap/continue/config.json`](../../bootstrap/continue/config.json) into Continue. Replace dummy `apiBase` with `$LOCAL_OPENAI_BASE_URL` (append `/v1` if missing). Recipe: [`bootstrap/continue/README.md`](../../bootstrap/continue/README.md).

Detect order: FreeToken `:1919` first, llama-swap `:9292`, llama-server `:8080`, Ollama `:11434` last. Not Ollama-only.

```bash
./pfy harness show continue   # json dump of the registry recipe entry
./pfy start continue          # always STUB exit 2 + issue #61
```

Registry `status` is **partial** (docs recipe). Live start stays stub. `detect` is `[]`.

Upstream: [continuedev/continue](https://github.com/continuedev/continue)

## Not yet

- Exec Continue from `./pfy start continue`
- Vendoring Continue into git
- Marking the registry **ready**
- Other harness adapters
