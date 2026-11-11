# gstack role-pattern recipes (docs-first)

**Status:** Active (T-0014) · **Policy:** [ADR-0009](../adr/0009-skill-port-hybrid-strategy.md) (docs-only for gstack; no full tree embed)  
**Upstream:** https://github.com/garrytan/gstack · pin observed at docs write: `7c9df1c568a9` (MIT)  
**X seed:** Entry 010 in [sources/x-posts.md](../../sources/x-posts.md)

## What we take from gstack

**Idea:** one builder + AI as a **virtual team** with explicit roles and a fixed pipeline:

```text
Think → Plan → Build → Review → Test → Ship → Reflect
```

gstack implements that as many Claude Code slash skills (`/plan-ceo-review`, `/review`, `/qa`, `/ship`, `/cso`, …). **We do not vendor those skills.** We map the **roles and stage gates** onto **pfy-deanery** skills and process so Grok agents get the same discipline without a 20+ skill monorepo.

## Role → pfy-deanery mapping

| Role (gstack spirit) | Upstream examples (do not install) | Use in this stack |
|----------------------|------------------------------------|-------------------|
| **CEO / product rethink** | `/plan-ceo-review`, `/office-hours` | Challenge scope in chat; record pivots with **`/adr`**; park product TBDs with **`/open-questions`** |
| **Eng manager / architecture** | `/plan-eng-review`, `/autoplan` | **`/adr`** + DESIGN; plan via **mattpocock `to-spec`** (paths); one-shot DoD for scoped builds |
| **Designer / UX smell** | `/plan-design-review`, `/design-consultation` | Human taste + checklist in PR; optional later paths skill if needed |
| **Implementer** | implement after plan | Grok coding loop + **karpathy-guidelines** + **ponytail**; **`/agent-loops`** for exit card / type; **`/one-shot`** when DoD is clear |
| **Debugger / RCA** | `/investigate` | **`/investigate`** first-party (T-0017) — Iron Law, phases, DEBUG REPORT |
| **Reviewer** | `/review` | **mattpocock `code-review`** (paths); cross-persona review notes in AGENTS |
| **QA** | `/qa`, `/qa-only`, `/browse` | **`make cage-test`**, **`make smoke-*`**, host tests; cage shell for repro |
| **Security / CSO** | `/cso`, `/guard` | Policy: write-guard (`make smoke-write-guard`), cage network whitelist; threat notes in ADR if needed |
| **Release engineer** | `/ship`, `/land-and-deploy` | Feature branch → review → merge; DEPLOY checklist; no force-push to main |
| **Tech writer** | `/document-release` | **`/docs`**, **`/catalog-docs`**, module docs under `docs/modules/` |
| **Memory / retro** | `/learn`, `/retro`, `/context-save` | **`/hermes-feedback`** (T-0048); session worksheets; TODO/OQ updates |
| **Marketing multi-view** | (adjacent packs) | **`/marketing-council`** (first-party, T-0011) |

## Stage recipes (copy into a session prompt)

### 1. Think (product)

```text
Role: CEO/product. Rethink the problem before solutioning.
- Restate user goal and non-goals.
- Offer Expansion / Hold scope / Reduction options.
- If architecture changes: draft ADR (rejected alternatives required).
- If undecided: open OQ, do not invent silently.
```

### 2. Plan (engineering)

```text
Role: eng manager. Produce an executable plan.
- Use to-spec (mattpocock paths skill) or write a short plan with DoD checklist.
- Prefer agent-cage smokes for integration work (docs/ops/one-shot-example-dods.md).
- List files to touch; pin deps (ADR-0003).
```

### 3. Build

```text
Role: implementer.
- Surgical diffs; karpathy-guidelines / ponytail when tempted to overbuild.
- /one-shot only with written DoD + lab (cage) when integration is in scope.
- No secrets in git; workspace/write-guard awareness.
```

### 4. Review

```text
Role: reviewer (standards + spec).
- Run code-review skill (mattpocock paths) against merge-base…HEAD.
- Axes: standards (repo conventions) vs spec (DoD / issue).
- Optional second persona: security or performance (see AGENTS.md).
```

### 5. Test / QA

```text
Role: QA.
- make catalog-json / unit selftests (tier 0).
- make cage-test and relevant make smoke-* (tier 2).
- Report exit codes and residual risk; no "works on host only" for cage-required DoDs.
```

### 6. Ship

```text
Role: release.
- Feature branch; no force-push main.
- Merge when green; update TOOLS/TODO if catalog impact.
- DEPLOY.md checklist for operator-facing changes.
```

### 7. Reflect

```text
Role: retro.
- What failed / what to pin; update TODO or OQ.
- Self-healing docs if modules changed (/docs or /catalog-docs).
```

## Explicit non-goals (this repo)

| Do not | Why |
|--------|-----|
| `git clone gstack` into this catalog | ADR-0003 / ADR-0009 — huge Claude-oriented tree |
| Copy all 20+ slash skills into `bootstrap/grok-cli/skills/` | Not core; maintenance and surface area |
| Require Bun/Claude Code for pfy-deanery bootstrap | Grok-first (ADR-0002) |
| Treat Multica as gstack | Multica = board/teammates platform; gstack = role skill factory |

## Deeper port investigation (single skill)

**Completed:** attribute-based comparison of high-value gstack skills vs this stack.  
**Detail + scoring table:** [gstack-skill-port-comparison.md](gstack-skill-port-comparison.md).

### Headline results

| Finding | Implication |
|---------|-------------|
| Upstream skills are **Claude-harness-heavy** (generated preamble, hooks, `gstack/bin`) | **Raw `skills.paths` snapshot is not viable** for almost any gstack skill |
| Largest **method** gaps | **`investigate`** (RCA / Iron Law) and **`cso`** (OWASP/STRIDE audit ≠ write-guard) |
| Overlap already covered | `review`≈mattpocock code-review; `spec`≈to-spec; ship/QA stages via recipes + cage smokes |
| **Recommended single deeper port** | **`/investigate` shipped** (T-0017 first-party method rewrite) |
| Second candidate (later) | First-party **cso checklist** rewrite — larger; optional if still needed |

Default for other gstack roles remains **docs + AGENTS router**.

## Related

- [gstack-skill-port-comparison.md](gstack-skill-port-comparison.md) — attributes + scored shortlist  
- [AGENTS.md](../../AGENTS.md) — role router section  
- [ADR-0009](../adr/0009-skill-port-hybrid-strategy.md)  
- T-0011 mattpocock / marketing-council · T-0014 docs recipes · **T-0017** `/investigate` shipped  

- [one-shot-example-dods.md](one-shot-example-dods.md)  

