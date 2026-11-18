# adr-tools companion (optional)

**Status:** Done T-0007 / issue #15  
**Related:** [ADR-0001](../adr/0001-process-docs-and-adr-layout.md) · catalog row `adr-tools` · first-party `/adr` skill

## Default (this repo)

Use **first-party process**, not shell ADR tooling:

| Piece | Path |
|-------|------|
| ADR skill | `bootstrap/grok-cli/skills/adr/` |
| Project scaffold | `bootstrap/project-process/` → multi-file `docs/adr/` |
| Index | `docs/adr/README.md` |

Agents create/supersede ADRs via skill + markdown templates. **No hard dependency** on `adr-tools` in bootstrap or Makefile.

## When to pin `adr-tools`

Optional for teams that want **shell automation** outside Grok/OpenCode sessions:

```bash
# example only - not installed by this repo
git clone https://github.com/npryce/adr-tools.git
# or package manager; then:
adr new "Title of decision"
```

Use when:

1. Humans author ADRs from terminals without agent skills.  
2. CI wants a numbered file without LLM.  
3. An existing org standard already mandates `adr-tools`.

Do **not** use when:

- Agents already write `docs/adr/NNNN-*.md` via `/adr`  
- You would create dual numbering systems (skill vs CLI) without an ADR

## Pin policy

If adopted: record `pinned_commit` / tag in `data/tools.json` (row already B-tier). Keep layout compatible with ADR-0001 (Context / Decision / Consequences + rejected alternatives).

## Integration stage

**I1** catalog / optional pin - not I3 onboard for this monorepo.
