# Overlays for pfy-deanery

Place docker-compose overrides, MCP server snippets, and Grok/LiteLLM wiring here as they stabilize.

| Overlay | Purpose |
|---------|---------|
| [`grok/`](grok/) | Versioned Grok CLI image + OIDC auth mount |
| [`local-ollama/`](local-ollama/) | Policy `coding-agent-local` + compose fragment for **host Ollama** |
| (future) `mcp-servers.catalog.yaml` | codebase-memory + filesystem tuned for catalog workspace |

**Local Ollama smoke** (from catalog root):

```bash
make local-ollama-overlay-install
make local-ollama-up
make smoke-litellm-ollama
```

Recipe docs: [examples/litellm-ollama/](../../../examples/litellm-ollama/).

Note: `agentcage up` forces its own compose `-f` list and may ignore extra fragments — `local-ollama-up` / `grok-up` call `docker compose` explicitly.
