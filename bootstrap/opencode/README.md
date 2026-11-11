# OpenCode adapter (secondary operator surface)

**Primary remains:** Grok (`bootstrap/grok-cli/`)
**Inference:** `LOCAL_OPENAI_BASE_URL` from the ADR-0014 detector (FreeToken first, then llama-swap, llama-server, Ollama adapter). Not Ollama-only.
**Skills SoT:** `bootstrap/grok-cli/skills/` via `OPENCODE_SKILLS`. Do not fork a second skill tree here.

## Command path (T-0102)

```bash
./pfy harness use opencode
./pfy start opencode
```

That:

1. Sets the active harness to `opencode`.
2. Brings up local inference (detect order unchanged) and product env-stage.
3. Detects `opencode` or `opencode-cli`.
4. Exports `OPENCODE_SKILLS` → `bootstrap/grok-cli/skills`.
5. When the local runtime is ready, points the model provider at `LOCAL_OPENAI_BASE_URL` (`OPENAI_BASE_URL` defaults to that).

Missing binary: honest STUB + https://github.com/themark-net/pfy-deanery/issues/55, exit 2. No fake ready.

## Suggested host layout

```bash
export OPENCODE_SKILLS="$PWD/bootstrap/grok-cli/skills"
# model provider is set by ./pfy start opencode from the live detector
```

| Use | Endpoint |
|-----|----------|
| Local worker | `$LOCAL_OPENAI_BASE_URL` (FreeToken :1919 / llama-swap :9292 / llama-server :8080 / Ollama :11434) |
| Hard tasks | Keep on Grok CLI |

## Non-goals

- Replacing Grok as the default harness
- Vendoring OpenCode into git
- Rewriting the inference detect order

## Related

- [ADR-0012 simple launch](../../docs/adr/0012-simple-harness-agnostic-launch.md)
- [ADR-0014 local inference](../../docs/adr/0014-pluggable-local-inference-spine.md)
- [ADR-0011 hybrid surfaces](../../docs/adr/0011-hybrid-operator-surfaces-grok-opencode-ollama.md)
