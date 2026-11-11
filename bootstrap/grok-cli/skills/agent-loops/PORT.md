# agent-loops — first-party pattern port (T-0050)

- **Placement:** first-party (`bootstrap/grok-cli/skills/agent-loops/`) — installed to `~/.grok/skills/`
- **Catalog row:** TOOLS.md **Finn Loop / eval-loop / 8-exits patterns** (Entries 024 · 027 · 031 · 032 · 068)
- **Primary seed:** Entry 068 eight exits (`sources/entries/068-eight-exits-agent-loop.md`)
- **Also taken from:**
  - Entry 027 — four loop types (turn / goal / time / proactive)
  - Entry 024 — Finn spec → build → review + human gate
  - Entry 032 — rubric-first eval loop + rigor ladder
  - Entry 031 — generate → test → update context
- **Mapped onto pfy-deanery:**
  - Goal loops → `/one-shot` + DoD + cost ladder (ADR-0008)
  - Exits → turn/error caps already in one-shot; expanded explicit exit card
  - Verification → `make smoke-*`, `make eval-*`, cage lab
  - Review gate → mattpocock `code-review`; ship discipline in AGENTS
- **Not a raw snapshot:** no third-party loop harness binary; no Linear/Slack/Vercel requirement; no AgenC
- **Omitted:** emoji-merge bots, multi-agent company daemons, scheduled cloud products
- **Policy:** ADR-0009 hybrid pattern ports; ADR-0002 Grok-first; ADR-0005 light process
