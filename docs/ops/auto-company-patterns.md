# Auto-Company patterns (extract only — not a runtime)

**Source:** X Entry 066 · TOOLS.md **Auto-Company** (S on company rubric)  
**Posture:** Pattern goldmine for Grok skills / AGENTS — **not** primary company daemon (no ADR to adopt company runtimes).  
**Related:** `/marketing-council`, gstack role recipes, Multica (watch), ADR-0005 light process

## What we take

| Pattern | Use in pfy-deanery |
|---------|-------------------|
| **Named expert personas** with fixed jobs (CEO/critic/eng) | Role router in AGENTS.md; optional persona prompts in skills — not 14 concurrent agents by default |
| **Shared consensus baton** (human-editable shared doc) | `docs/TODO.md` + OQ + short worksheets; avoid pure chat-only “agreement” |
| **Pre-mortem GO/NO-GO gate** | `/adr` rejected alternatives + `/open-questions` before hard-to-reverse work |
| **Forbidden pure discussion** without ship artifact | Prefer DoD (`/one-shot`) or exit card (`/agent-loops`) |
| **Squad formation for scope** | Scope reduction before spawn; ponytail / karpathy against bloat |
| **Honest cost caveat** | Cost ladder in one-shot; `DEPLOY_PROFILE` caps |

## What we do not take

- Daemon that runs a full simulated company overnight as default  
- Mandatory multi-provider agent swarm  
- Replacing DESIGN/ADR/TODO with a third process system  

## Operator recipe (lightweight)

```text
1. Restate goal + non-goals (CEO/product voice)
2. Pre-mortem: list failure modes → ADR or OQ if architecture/TBD
3. Spec with DoD (to-spec or one-shot DoD)
4. Build with exits (agent-loops / one-shot)
5. Critic pass (code-review or second persona)
6. Reflect: hermes-feedback memory + TODO update
```

## Re-eval trigger

Promote toward richer multi-agent org tooling only if:

- Multica / company templates score higher on **local-first + cage** than today, and  
- Operator explicitly wants standing autonomous “company” loops (time/proactive), and  
- A cage smoke exists for the chosen runtime  

Until then: **patterns in docs/skills; Grok + cage remains the runtime.**
