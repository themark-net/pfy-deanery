# Recommend / try local models

Cite **#207**. Ranked recommendations for this host beyond already-pulled. One try/pull against the live FreeToken-first runtime. Honest FAIL if recommend/pull cannot run (no fake best list).

## Operator

On **Engine** (HTML+tk) or CLI:

```bash
./pfy models recommend          # ranked list, or FAIL+next
./pfy models try                # pull top recommendation
./pfy models try <name>         # pull a named recommendation
```

Engine: **Recommend** refreshes the rank; **Try recommended** pulls the top name (or the Pull field if filled). Same `./pfy models pull` FreeToken-first path.

### Rank

Fits this host (VRAM via `nvidia-smi` if present, else RAM budget) and this live runtime. Excludes names already on the live endpoint. Empty fit set or unknown host/engine → **FAIL**, empty list (never a invented “best”).

| Runtime | Try / pull |
|---------|------------|
| FreeToken `:1919` | Records `$PFY_STATE_DIR/ft-model` (same as `models pull`). Load happens at next `ft serve --model` / Launch env. |
| Ollama | `ollama pull` |
| llama-swap / llama-server | **FAIL** - no pull. Next: `set PFY_LLAMA_MODEL` to an existing GGUF |

### Model handoff (what switches)

When picking another local model:

1. **Engine pin** - FreeToken: `$PFY_STATE_DIR/ft-model` (and `pinned-model`). Ollama: pull + `pinned-model`. llama: `PFY_LLAMA_MODEL` path only.
2. **Attach re-probe** - next Attach OpenCode | Hermes | Grok lists models + one smoke on the live detect base. A recorded FreeToken name is **not** attached until serve.
3. **TUI reload** - Engine Refresh / snapshot poll. Paint models from the live endpoint only.

Do not paint `READY` / live for a name that is only recorded. Next is always `Launch env or ./pfy up (engine pin) · Attach re-probe · TUI reload`.

## How to run

```bash
python3 scripts/pfy_recommend_models_207.py --selftest
./pfy models recommend
./pfy models try
python3 scripts/pfy-board.py --recommend
python3 scripts/pfy-board.py --try
```

## Variables

| Name | Where | Purpose |
|------|-------|---------|
| `PFY_STATE_DIR` | `pinned-model`, `ft-model`, `model-handoff.md` | pin + operator next |
| `PFY_FT_MODEL` | env (existing) | FreeToken serve name; try writes `ft-model` |
| `PFY_LLAMA_MODEL` | env (existing) | GGUF path when llama has no pull |
| `LOCAL_CODER_MODEL` | env (existing) | Attach/OpenCode fallback model id |

Registry: [bootstrap/env/REGISTRY.md](../../bootstrap/env/REGISTRY.md).

## Gab open-weight sync (#228)

`./pfy models gab-sync` maps Gab open-weight families to Ollama tags with `fits|tight|won't-fit` for nimo. Surfaces beside FreeToken-first recommend; does not replace it. Chip: **gab auto ≠ local ranking**. Gab does not host GGUF.

## Do not

- Reopen #76 · unpark #198 · catalog 70-75 HOLD
- Invent a best list when engine/host/fit is unknown
- Paint a recorded FreeToken name as live before `./pfy up`
- `LIVE_HARD_OFF`: no cloud catalog writes / no HF API from this path
