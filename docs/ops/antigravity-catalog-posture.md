# Antigravity-Manager - catalog posture

**Status:** T-0015 / issue #23 - OQ-0007 answered **skip for now**  
**Upstream:** https://github.com/lbjlaq/Antigravity-Manager  
**Integration stage:** **I1** · opportunity priority **low**  
**Default multi-backend path:** LiteLLM + API keys (not multi-account Tauri relay)

## Policy

| Action | Allowed? |
|--------|----------|
| Catalog / Entry 005 notes | Yes |
| Install Tauri app in lab by default | **No** |
| `make smoke-*` requiring Antigravity | **No** |
| Re-open eval if multi-account pain appears | Yes (raise priority; do not invent OQ if safe default remains) |

## Why not a blocking OQ

Safe reversible default exists (skip install). See [human-decision-inventory.md](human-decision-inventory.md) § When to open an OQ.

## Uses / features / potential

| Field | Content |
|-------|---------|
| **Uses** | Multi-account browser-login → local OpenAI-shim relay |
| **Features** | Account pool, Tauri desktop, OpenAI-compatible local API |
| **Potential** | Low for this stack until quota juggling is a real operator pain |
| **Non-goals** | Primary proxy (LiteLLM wins); default cage dependency |
