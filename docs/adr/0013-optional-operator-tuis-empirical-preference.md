# ADR-0013: Treat operator TUIs (including AgenC) as optional scored components; introduce empirical preference dimension

- **Date:** 2026-07-27
- **Status:** Accepted
- **Supersedes:** the absolute “catalog-only / not primary” posture of [ADR-0010](0010-reject-agenc-as-primary-runtime.md) with respect to the full AgenC surface
- **Related:** ADR-0002 (Grok CLI primary), ADR-0011 (hybrid surfaces), ADR-0010 (historical trial data), ADR-0007 (write-guard)

## Context

ADR-0010 correctly recorded an early operator trial (2026-07-12) in which the AgenC TUI showed high friction (obscure approval model, repeated prompts, auth surface mismatch with Grok Build subscription). That trial justified not making AgenC the default primary runtime and remains valid historical data.

Subsequent framing clarified the higher-order goal: standardize measurement of *fit* for every component, including operator interfaces. Interfaces should be treated as optional, independently scoreable parts rather than binary accept/reject gates. Developer preference is real but empirical — it cannot be known until after actual deployment and repeated use.

Making the TUI “just another part” allows the catalog to evaluate the full AgenC surface (protocol + MCP + worker + optional TUI) on the same terms as any other tool while preserving clear defaults for this repository.

## Decision

1. **Defaults remain unchanged.** Grok CLI (ADR-0002) + agent-cage remain the default primary operator path and isolation lab for this repository.
2. **AgenC full surface is first-class and optional.** The protocol, marketplace MCP/worker/SDK, and TUI are scored components. The TUI may be used, hybridized, or completely bypassed via CLI/MCP/worker.
3. **Preference is an empirical, post-deployment dimension.** A new (or expanded) rubric dimension “Operator Interface Fit / Preference” is measured only after real operator hours or real tasks. Initial values may be left “pending real use.” Stage 0 and objective stages are unchanged.
4. **Historical trial data is retained as input.** The friction observations from ADR-0010 become scored attributes under the preference dimension rather than a permanent categorical rejection.
5. **Isolation remains distinct.** agent-cage is the primary general-purpose isolation harness (Docker-based sandbox with network policy, filesystem isolation from host, MCP overlays). AgenC’s sandboxing is marketplace-oriented and does not supersede or fully duplicate agent-cage. Local agent isolation / harness security is treated as its own concern (category or strong Stage factor).

## Rubric impact

Add or formalize in CATEGORIZATION.md:

**Operator Interface Fit / Preference (empirical, 0–100, post-deployment only)**  
Measured only after real operator hours or real tasks. Factors include:
- Cognitive load of the approval / permission model
- Session continuity and resumption friction
- Ability to bypass the TUI entirely in favor of CLI / MCP / skills
- Alignment with existing muscle memory (Grok CLI, Claude Code, OpenCode, pure terminal, etc.)
- Frequency of “I would rather not use this surface” signals in real work
- Whether preference changes after the first day / first week

Explicitly marked as unknown until deployment. Initial catalog entries can leave it blank or “pending real use.” Does not replace Stage 0 or the objective stages.

## Consequences

- Label ADR-0010 as Superseded by this ADR in the index.
- Update TOOLS.md / data/tools.json AgenC entry: remove hard demotion language; note that the TUI is optional; flag preference score as pending empirical data; keep existing objective scores.
- Update CATEGORIZATION.md with the new preference dimension and a note that local agent isolation / harness security is a distinct concern (agent-cage remains the primary scored example).
- Bootstrap and hybrid surface notes may list AgenC as one selectable operator surface without making it the default.
- Eval / one-shot / agent-loops skills should eventually capture preference receipts after real runs.
- No change to default launch paths or agent-cage primacy.

## Rejected alternatives

1. Silent amendment of ADR-0010 — violates the “never silent overwrite” rule and loses decision history.
2. Making AgenC co-primary or default — still lacks empirical preference data and would dilute the Grok CLI + cage baseline.
3. Deleting the original trial observations — loses valuable historical receipts.
4. Treating preference as a pre-deployment Stage 0 gate — preference is unknown until use.
5. Treating AgenC isolation as superseding agent-cage — scopes differ; cage is general local lab, AgenC isolation is marketplace-tied.

## References

- ADR-0010 (superseded posture), ADR-0002, ADR-0011, ADR-0007
- Session discussion 2026-07-27 on optional interfaces and empirical preference
- Upstream AgenC: https://github.com/tetsuo-ai/agenc-core , https://agenc.tech , marketplace kit + MCP
- agent-cage: https://github.com/pnnl/agent-cage (primary isolation lab)
