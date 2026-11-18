# ADR-0008: One-shot workflow (minimize questions, cheap iteration)

- **Date:** 2026-07-12
- **Status:** Accepted

## Context

Operators sometimes want a single request executed to a **working product** with minimal back-and-forth. Unbounded agent autonomy is unsafe without a test lab and cost controls. We already have agent-cage, deployment profiles, and process docs - one-shot should **require** them, not ignore them.

## Decision

1. Define an official **one-shot workflow** (`docs/ops/one-shot-workflow.md`) and skill `/one-shot`.
2. One-shot **minimizes user questions** but is **not** unlimited: budgets, cost ladder (local/static → cage → cloud), and hard-blocker questions only.
3. **Prerequisites fail closed:** env profile check; isolation lab (prefer agent-cage) when the DoD needs integration tests; explicit Definition of Done before coding.
4. Default max auto cost tier follows `DEPLOY_PROFILE` (local-only forbids cloud in the loop).
5. One-shot does not bypass ADRs, triple-write catalog rules, or secret hygiene.

## Rationale

- Matches “iterate cheaply until green” without burning cloud tokens first.
- Ties autonomy to real guardrails (containers/VMs/lab) the operator already invests in.
- Clear stop conditions prevent infinite loops.

Rejected alternatives:

1. **Always ask until fully specified** - high friction for mechanical delivery.
2. **Unlimited YOLO** - unsafe; no lab requirement.
3. **Cloud-first always** - expensive; contradicts local-first goals.

## Consequences

- Agents must write DoD + assumptions in one-shot runs.
- New integration one-shots should prefer in-cage verification.
- Skill shipped under bootstrap for reinstall.

## References

- `docs/ops/one-shot-workflow.md`
- ADR-0002, ADR-0003, ADR-0006, ADR-0007
- `harness/agent-cage/`
