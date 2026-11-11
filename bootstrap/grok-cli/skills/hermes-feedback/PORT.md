# hermes-feedback — first-party pattern port (T-0048)

- **Placement:** first-party (`bootstrap/grok-cli/skills/hermes-feedback/`) — installed to `~/.grok/skills/`
- **Upstream inspiration:** [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) feedback loops (auto-memory, auto-skill, curator)
- **Catalog seed:** X Entry 048 (`sources/x-posts.md`); TOOLS.md row **Hermes Agent (feedback loops)**
- **Related seed:** Entry 055 credential pools — hygiene notes only, not iron-proxy runtime
- **Not a raw snapshot:** no Hermes binary, no skill marketplace dump, no Claude-only harness
- **Taken:** three-loop model; complex-task → skill threshold; curator prune/pin/consolidate; compound knowledge framing
- **Mapped onto Grok + pfy-deanery:**
  - Memory → Grok memory tools + TODO/OQ/worksheets
  - Auto-skill → `/create-skill` discipline + `.grok/skills` / bootstrap first-party layout
  - Curator → explicit inventory of skill dirs + archive/pin (no 7-day daemon)
- **Omitted:** Hermes runtime scheduler, token-cost toggles as product flags, automatic 90-day daemon, credential-pool proxy
- **Policy:** ADR-0009 hybrid (pattern port, not subtree embed); ADR-0002 Grok-first; ADR-0010 no AgenC dependency
