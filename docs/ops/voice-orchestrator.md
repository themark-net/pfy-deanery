# Dual-tier voice orchestrator (T-0096)

**Status:** Live  
**Default route:** **high-first** (Grok coordinates → may DELEGATE_LOCAL → OpenCode)  
**Related:** ADR-0011 · ADR-0012 · T-0085 worker/monitor · [voice-agent-runner.md](voice-agent-runner.md)

## Why

Voice must reach **tools, MCP, git, and complex planning** - not only local completion.  
Local-first alone is cheap but weak for hard tasks; Grok-only is expensive.  
Orchestrator **coordinates both directions**:

```text
STT transcript
     │
     ▼
 HIGH (Grok)  ──plan / MCP / review──┐
     │ DELEGATE_LOCAL                  │ escalate / re-delegate
     ▼                                 │
 LOW (OpenCode + LOCAL_TOOLS_MODEL) ───┘
     │
     ▼
 last-run.json  { tier_history: [high:coordinate, low:implement, …] }
```

## Enable

```bash
# Default dual-tier (high-first)
VOICE_AUTO_AGENT=1 make voice-remote
# same:
VOICE_AUTO_AGENT=orchestrate VOICE_ROUTE=high-first make voice-remote

# Desk / re-run last prompt
make voice-orchestrate
# or
make voice-agent-run   # defaults to orchestrate
```

## Routes (`VOICE_ROUTE`)

| Route | Flow | Cost |
|-------|------|------|
| **`high-first`** (default) | Grok plans → optional DELEGATE_LOCAL → OpenCode → optional review | Cloud first turn |
| `local-first` | OpenCode first → escalate to Grok on fail/signals | Prefer local $ |
| `local-only` | OpenCode only | Local |
| `high-only` | Grok only | Cloud |

ADR-0012 still applies: use **local-only / opencode** when saving budget; use **high-first** when you need coordination quality.

## DELEGATE_LOCAL protocol

High coordinator emits:

```text
<<<DELEGATE_LOCAL
Implement X in file Y; run make smoke-foo
>>>
```

Orchestrator extracts the body and runs the **low** tier with that prompt.

## Env

| Variable | Default | Meaning |
|----------|---------|---------|
| `VOICE_AUTO_AGENT` | off | `1`/`orchestrate` dual-tier; `opencode` local; `grok` high-only |
| `VOICE_ROUTE` | `high-first` | Routing policy |
| `VOICE_ORCH_MOCK` | off | Mock high+low (smokes) |
| `VOICE_ORCH_REVIEW` | `0` | High reviews after local |
| `VOICE_ORCH_FALLBACK_LOCAL` | `1` | If high fails, try local |
| `VOICE_AGENT_MAX_TURNS` | `8` | Grok turns |
| `VOICE_AGENT_TIMEOUT` | `600` | Per-tier timeout |

## last-run.json

```json
{
  "mode": "orchestrate",
  "route": "high-first",
  "ok": true,
  "tiers": ["high:coordinate", "low:implement"],
  "tier_history": [ { "tier": "high", "role": "coordinate", "ok": true }, … ],
  "reply_preview": "…"
}
```

Phone UI: poll `GET /api/last-run` (same as before).

## Smoke (no cloud)

```bash
make smoke-voice-orchestrate
```

## Live recipes

```bash
# Full coordination (costs Grok + local)
export VOICE_AUTO_AGENT=1
export VOICE_ROUTE=high-first
export LOCAL_TOOLS_MODEL=qwen2.5-coder:7b-instruct   # from eval-select-tools-model
VOICE_REMOTE_HOST=127.0.0.1 make voice-remote

# Cost-saving day
VOICE_AUTO_AGENT=opencode make voice-remote

# After local fail, force high
VOICE_AUTO_AGENT=grok make voice-agent-run
```

## Not yet

- Grok MCP tool that *spawns* OpenCode as a first-class tool inside one Grok session (future)  
- Sticky multi-turn conversation memory across voice turns  
- Full duplex media  

## Related

- [local-tools-split.md](local-tools-split.md)  
- [worker-monitor.md](worker-monitor.md)  
