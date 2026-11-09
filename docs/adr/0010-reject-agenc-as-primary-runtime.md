# ADR-0010: Reject AgenC as primary runtime; Grok CLI + agent-cage remain defaults

- **Date:** 2026-07-12
- **Status:** Accepted
- **Supersedes:** informal claims that AgenC is “primary host runtime” (bootstrap/integration READMEs, T-0044 narrative)
- **Related:** [ADR-0002](0002-grok-cli-primary-interface.md) (Grok CLI primary — **affirmed**), OQ-0005

## Context

AgenC ([tetsuo-ai/agenc-core](https://github.com/tetsuo-ai/agenc-core), `get.agenc.ag`) was evaluated as a host agent runtime: install wrapper (`bootstrap/agenc/`), smoke, `/grok-login` for xAI subscription, TUI permission model, optional web console / marketplace-shaped job surfaces.

Operator trial (2026-07-12) found:

- **TUI/UX unfit as daily driver** — approval prompts obscure (Enter/2/3 without clear session semantics), repeated prompts for reads and even `python` JSON tooling, options not always shown; friction vs Grok Build CLI, Claude Code, and OpenCode.
- **Auth product surface confusing** — default remote/`agenc login` (often Google / managed keys) is not “use Grok Build subscription”; parallel OAuth stores; not aligned with Grok-first operator habit.
- **Philosophy mismatch** — project goals require **easy to use**, **easy to deploy**, and alignment with **best-practice toolsets**. A jump-off point whose primary UI fails those tests is the wrong primary, regardless of interesting secondary features.

Interesting capabilities **worth remembering** (not adopting as primary): web console, marketplace-style job intake, daemon/gateway patterns, ACP bridge to Grok Build composer models.

## Decision

1. **Do not** use AgenC as the primary operator interface or default host runtime.
2. **Affirm ADR-0002:** **Grok CLI (Grok Build)** remains the primary operator interface.
3. **Affirm agent-cage** as the primary **container isolation lab** (including Grok-in-image overlay when needed).
4. **Keep AgenC in the catalog** as a **reference / watch** entry (not recommended default). Track gaps (console, marketplace jobs, daemon UX) for possible **re-creation** with our stack when valuable.
5. **Uninstall** AgenC from operator hosts for this project’s default path; bootstrap scripts may remain for optional re-eval only.
6. **Revisit** this ADR when AgenC (or a successor) meets explicit UX gates below — requires a **new superseding ADR**, not silent flip.

## UX / fitness gates to revisit

AgenC (or alternative) may be reconsidered as **primary** only if empirical use shows:

| Gate | Pass looks like |
|------|-----------------|
| **Daily UX** | Clear approval affordances; workspace reads not a tax; session grants work as labeled |
| **Deploy** | One-command install that matches our Node/profile story without dual-identity confusion |
| **Auth** | Clean path to **existing Grok Build / xAI subscription** without forcing third-party account login for basic coding |
| **Parity** | Not worse than Grok Build / Claude Code / OpenCode for core edit-run loops |
| **Lab fit** | Composes with agent-cage + Makefile smokes without replacing them |

Until then: **catalog only**.

## Success path for *this* stack (post-decision)

Definition of success for ongoing operator work (not AgenC):

1. **Launchable Grok Build CLI inside agent-cage** (`make cage-grok-*` / overlay).
2. **Presets** so stock **filesystem MCP** (and related MCP) can operate on the **local/catalog workspace**.
3. **Makefile pipeline** for smoke, test, and **versioned** image/overlay changes.

## Rejected alternatives

1. **AgenC as primary despite TUI pain** — Violates easy-to-use; training tax permanently.
2. **Dual-primary (Grok + AgenC)** — Two auth surfaces, two TUIs, two update stories; operator confusion without scored win.
3. **Delete all AgenC mention** — Loses useful reference (console/marketplace patterns) and re-eval trail.
4. **Immediate full port of AgenC features into this repo** — YAGNI; re-create only after gap is scored against Grok+cage.

## Consequences

- Update `bootstrap/agenc/`, `integration/agenc/`, DESIGN/TODO/TOOLS to **demote** AgenC; T-0044 = install experiment only, not primary.
- Catalog row: reference tier/notes cite this ADR; watch web console + marketplace job intake.
- Host uninstall is the default operator hygiene after trial.
- Next build energy: **Grok-in-cage launch + MCP workspace presets + Makefile versioning** (TODO).

## References

- ADR-0002, OQ-0005, `harness/agent-cage/overlays/grok/`
- Upstream: https://github.com/tetsuo-ai/agenc-core · https://get.agenc.ag/install.sh
- Trial notes: obscure permission TUI; Google remote login vs `/grok-login`; comparison to Grok/Claude/OpenCode
