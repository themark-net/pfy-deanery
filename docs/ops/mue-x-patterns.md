# MUE-X patterns (extract only - no evolve runtime)

**Source:** Entry 067 · TOOLS.md **MUE-X**  
**Posture:** Pattern extract for self-modifying agent safety. **Do not** run unattended `evolve` in this lab without pin + safety note + operator batch OK.

## Patterns worth stealing

| Pattern | Use here |
|---------|----------|
| **AST mutation strategies** (bounded transforms) | Prefer surgical diffs; never self-rewrite agent kernel in-repo |
| **Immune / sealed kernel** idea | Process invariants in AGENTS/ADR; write-guard + cage policy as outer immune layer |
| **Memory lattice layers** | Map to: TODO/OQ (durable), Grok memory (session), codebase-memory (code graph) |
| **Drive / mood as control signals** | Map to exit cards (budget, error threshold) not personality daemons |
| **GitHub absorption** | Catalog via scoring + pin, not auto-merge foreign code |

## Defaults (no human)

- Catalog A-tier reference only until `python -m mue status` smoke exists and is green.  
- No subtree embed (ADR-0003).  
- Self-mod of **product code** via normal PR loop; self-mod of **agent harness** requires ADR.

## Structural hook

Structural: `examples/eval-harness/tasks/010-mutation-safety-note/` (in `eval-structural`). Deeper local-backend evolve lab still deferred.

## Deeper lab deferred (issue #28)

Local-backend + mutation-safety eval remains **optional**. Default: pattern/docs only. Promote only with pin + safety note and I2/I3 gates. No evolve-in-lab by default.
