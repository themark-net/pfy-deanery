# Quality hooks extract - claude-codex-settings (Entry 076)

**Source:** https://github.com/fcakyon/claude-codex-settings  
**Status:** Pattern extract 2026-07-30 · **No** forced Claude Code runtime  
**Related:** #27 · asm (#26) · karpathy-guidelines skill

## High-value patterns to port (first-party / AGENTS)

| Pattern | Intent | Grok / pfy home |
|---------|--------|-----------------|
| Force-push / unsafe git blocks | Prevent destructive git | write-guard + AGENTS “no force-push main” |
| Simplification-before-commit | Fight overcomplication | `/one-shot` + ponytail-audit + karpathy-guidelines |
| AI-buzzword / filler filters | Reject slop copy | docs skill / review checklist |
| Shared AGENTS.md / CLAUDE.md shape | Consistent operator guidance | `AGENTS.md` + project-process templates |
| Clarify-before-large-change | Ask when ambiguous | open-questions skill + human-decision-inventory |

## Optional skill checklist (operator)

When reviewing agent output before commit:

1. Diff only what the DoD required?  
2. Any force-push, hard reset, or secrets?  
3. Names/abstractions justified or YAGNI?  
4. Tests or structural eval path mentioned?  

## Non-goals

- Do not vendor Claude Code plugins wholesale.  
- Do not require Codex/Cursor install.  
