# Integration stages (tool lifecycle)

**Status:** Accepted 2026-07-30 (OQ-0003)  
**Related:** [ADR-0003](../adr/0003-default-pinned-commit-tracking.md) · [SUBTREES.md](../../SUBTREES.md) · [CATEGORIZATION.md](../../CATEGORIZATION.md) · [evaluation-framework.md](../evaluation-framework.md)

## Intent

Catalog scoring (S1–S4, S/A/B/C) answers **“is this tool interesting?”**  
This rubric answers **“how deep may we pull it into *this* repo / lab?”**

No tool is forced to a symbolic first subtree. **Wait** until a stage gate is met. Until full onboard, tools live in staged evaluation that names uses, features, and potential — not assumed integration.

---

## Stages (lifecycle)

| Stage | Name | What lives in-repo | When to use |
|------:|------|--------------------|-------------|
| **I0** | **Awareness** | Catalog row optional / C-tier watch | Failed Stage 0 or pure hype; track only |
| **I1** | **Staged evaluation** | Entry + TOOLS.md + `data/tools.json` pin · pattern/docs notes | Default for every accepted catalog tool |
| **I2** | **Ad-hoc probe** | Optional **lightweight local copy** (not “integrated”) | Potential still ambiguous *and* size gate met |
| **I3** | **Onboard / integrated** | Skill, smoke, eval task, env registry, cage path | Clear value + modularity gates; operator path green |
| **I4** | **Embedded** | Submodule or rare subtree under `tools/` | I3 plus SUBTREES.md embed criteria |

**Rule:** I1 → I3 is the normal happy path. I2 is a **temporary** fork of ambiguity, not a shortcut to I3/I4. I4 remains rare (ADR-0003).

```text
Catalog Phase 0–2  →  I1 staged evaluation
         │
         ├─ potential clear + value+modularity → plan I3 (skill/smoke)
         │
         └─ potential ambiguous + lightweight  → I2 ad-hoc probe copy
                    │
                    ├─ disambiguated positive → I3
                    └─ low value / heavy      → back to I1 or demote

I3 + need in-tree edit / offline embed → I4 (submodule preferred; subtree rare)
```

---

## I1 — Staged evaluation (default)

Must identify and record:

| Field | Content |
|-------|---------|
| **Uses** | Concrete operator jobs (e.g. “local skill install”, “STT edge”) |
| **Features** | Capabilities that matter to Grok + cage + LiteLLM stack |
| **Potential** | High / medium / low / **ambiguous** for *this* stack |
| **Non-goals** | What we will *not* adopt (runtime, weights, daemon, etc.) |
| **Next gate** | What evidence would promote to I2 or I3 |

If **potential is ambiguous**, do **not** pretend full onboard. Either stay I1 or, if lightweight, promote to **I2** only.

---

## Thresholds

### Value gate (required for I3+)

Promote toward onboard only if **≥ 3 of 4**:

1. **Gap fill** — closes a hole vs existing S/A tools or first-party skills (not pure overlap).
2. **Operator leverage** — improves design/coding assist, cage safety, eval, or local bulk path within a day of glue.
3. **Evidence** — runnable quickstart or in-lab smoke path exists (or is trivial to write).
4. **Blast radius OK** — no forced multi-GB weights, no primary-runtime takeover without ADR, license OK for our use.

### Modularity gate (required for I2+ local code, and for I3/I4)

Promote only if **all** true:

1. **Local code needed** — cannot fully evaluate “use under different circumstances” from docs/API alone (e.g. hooks, CLI flags, MCP surface, patch surface).
2. **Bounded surface** — clear package/CLI entrypoints; not a sprawling monorepo as the unit of eval.
3. **Isolatable** — can sit under `tools/` or a cache path without becoming the product runtime by default.
4. **Reversible** — deleting the copy/submodule does not strand catalog truth (pin + entry remain).

### Lightweight size gate (I2 only)

| Metric | Limit (initial arbitrary — tune later) |
|--------|----------------------------------------|
| Working tree to copy / shallow clone | **< 50 MB** |
| No model weights / large binaries | Required |
| Prefer shallow clone or sparse checkout | Required |

If > 50 MB or weight-bearing → **stay I1** (pin + shallow clone on demand in a throwaway dir, never call it “integrated”).

### Embed gate (I4 — submodule/subtree)

All of SUBTREES.md **plus** already at **I3**, **plus**:

- Active customization *in this monorepo*, or offline/CI repro requires a committed pointer.
- Prefer **submodule** over subtree; subtree only if small history + heavy local edits.

**First subtree candidate:** *none*. Wait until a tool clears I3 and the embed gate. Do not pick a symbolic first embed.

---

## Integration level rubric (I-level vs catalog tier)

| Catalog tier | Typical max I-stage without extra proof |
|--------------|------------------------------------------|
| S | I3 planned quickly; I4 still rare |
| A | I1 default; I3 if value+modularity; I2 if ambiguous + light |
| B | I1; I2 only if cheap probe; rarely I3 |
| C / Watch | I0–I1 only |

**Do not** treat “S-tier catalog score” as automatic I4 embed.

---

## What “not integrated” means (I1–I2)

- No claim of production operator path.
- No default Make target that assumes the tool is always installed.
- No env registry “required” vars.
- I2 copy may live under `tools/_probe/<name>/` or gitignored cache — document path; **not** a product surface lever.

## What “integrated” means (I3)

At least two of:

- first-party skill or ops pattern with verification
- `make smoke-*` (prefer in-cage)
- eval task / structural scorer touchpoint
- env registry entry + profile note

---

## How to move a card

Facts are recomputed. Judgments are not.

```bash
python3 scripts/catalog_stage_eval.py          # one line per tool: stage, ceiling, potential, evidence
python3 scripts/catalog_stage_eval.py --apply  # write facts + data/catalog_stage_handoff.json onto the cards
python3 scripts/catalog_check.py               # every TOOLS.md row still has a card
```

`potential`, `uses`, `features`, `non_goals`, and `next_gate` come from the handoff file. Tier, scores, posture phrases, Makefile/path evidence, and the tier ceiling are computed from `TOOLS.md` and the repo. The ceiling is a cap, not a promotion. Edit the handoff and apply again to change a judgment. Do not flip `integration_stage` just because the ceiling allows it.

## Agent rules

1. New X/catalog entries start at **I1** (or I0 if Stage 0 fails).
2. Never ask for a subtree “just to have one.”
3. Ambiguous potential + <50 MB → may open I2 probe; record exit criteria.
4. I3 requires value + modularity gates; open ADR only for primary-runtime or architecture shifts.
5. I4 requires explicit checklist in PR (SUBTREES.md).

## Resolution source

OQ-0003 (2026-07-30): Wait for first embed; define value + modularity thresholds; separate integration-stage rubric; staged evaluation default; lightweight intermediary probe (<50 MB) when potential ambiguous; full integration is a later state.
