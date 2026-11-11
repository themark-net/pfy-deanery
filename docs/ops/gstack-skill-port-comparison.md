# gstack skill deeper-port comparison

**Status:** Investigation complete (2026-07-12)  
**Upstream pin:** `7c9df1c568a9` (https://github.com/garrytan/gstack)  
**Policy:** [ADR-0009](../adr/0009-skill-port-hybrid-strategy.md) · Role recipes: [gstack-role-recipes.md](gstack-role-recipes.md)

## Purpose

Decide whether **any single** gstack skill earns a deeper port (paths snapshot or first-party rewrite), using explicit **comparison attributes**. This does **not** change the default: gstack as a whole stays **docs-only**.

## Comparison attributes (schema)

Use these columns for any future external skill-pack promotion review:

| Attribute | Type | Meaning |
|-----------|------|---------|
| **unique_gap** | 0–5 | How much capability we lack vs current pfy-deanery skills/process (5 = large hole) |
| **daily_utility** | 0–5 | How often a Grok operator on this catalog would invoke it |
| **method_quality** | 0–5 | Quality of the portable *method* if stripped of host glue |
| **raw_portability** | 0–5 | Can we paths-snapshot SKILL.md as-is on Grok? (5 = clean MIT skill like mattpocock) |
| **sibling_deps** | enum | `none` \| `soft` \| `hard` — needs other gstack skills/bins |
| **host_coupling** | enum | `none` \| `claude_hooks` \| `gstack_bin` \| `both` |
| **size_loc** | int | Approx. lines in upstream SKILL.md (incl. generated preamble) |
| **size_tree** | string | On-disk size of skill dir |
| **license** | string | Upstream license |
| **core_fit** | 0–5 | Fit to ADR-0009 “core” criteria if rewritten first-party |
| **recommended_placement** | enum | `docs-only` \| `paths-snapshot` \| `first-party-rewrite` \| `do-not-port` |
| **notes** | text | One-line rationale |

**Scoring note:** Prefer **first-party-rewrite** when `method_quality` high and `raw_portability` low. Prefer **paths-snapshot** only when `raw_portability` ≥ 4 and `sibling_deps` is `none`.

## Structural finding (all gstack skills sampled)

Upstream skills under this pin are largely **auto-generated** from `SKILL.md.tmpl` with:

- Large shared **preamble** (update check, telemetry, GBrain, AskUserQuestion protocol, Claude model patches)
- **`allowed-tools`** / **PreToolUse hooks** aimed at Claude Code
- Calls into **`~/.claude/skills/gstack/bin/*`**

Therefore: **`raw_portability` is 0–1 for nearly every gstack skill.** A naive `skills-external/gstack-foo/` snapshot would not run as intended on Grok. Deeper port means **extract the method** into a small first-party skill, not rsync the file.

## Candidate comparison (shortlist)

| Skill | unique_gap | daily_utility | method_quality | raw_portability | sibling_deps | host_coupling | size_loc | size_tree | core_fit | recommended_placement | notes |
|-------|------------|---------------|----------------|-----------------|--------------|---------------|----------|-----------|----------|----------------------|-------|
| **investigate** | 4 | 5 | 5 | 1 | soft (freeze optional) | both | ~1070 | 72K | 4 | **first-party-rewrite** | Iron Law RCA phases; biggest *engineering* method gap; rewrite without gstack bin |
| **cso** | 5 | 3 | 5 | 0 | hard (sections/, reports dir) | gstack_bin | ~1285 | 140K | 3 | **first-party-rewrite** (later) | Largest *security* gap vs write-guard; too heavy as raw port; checklist extract later |
| **review** | 1 | 4 | 3 | 1 | soft | both | ~1850 | 184K | 1 | docs-only | Overlaps mattpocock **code-review** (already paths) |
| **spec** | 1 | 4 | 4 | 1 | soft | both | large | — | 2 | docs-only | Overlaps mattpocock **to-spec** |
| **autoplan** | 2 | 3 | 3 | 0 | **hard** (loads CEO/design/eng skills) | both | ~1850 | 148K | 1 | do-not-port | Cannot port alone |
| **qa** | 3 | 3 | 4 | 0 | hard (browse/browser) | both | ~1680 | 108K | 1 | docs-only | Cage smokes cover integration; browser QA is different product |
| **careful** / **guard** | 2 | 3 | 3 | 0 | hard (bin scripts) | claude_hooks | small | 8–16K | 2 | docs-only | Need host hook runtime Grok does not provide; write-guard is MCP-layer analog for writes |
| **office-hours** | 2 | 2 | 3 | 1 | soft | both | ~1700 | 196K | 2 | docs-only | CEO recipes already in role-recipes; marketing-council for multi-view |
| **ship** | 1 | 3 | 3 | 1 | soft | both | ~1400 | 276K | 1 | docs-only | Our ship recipe + DEPLOY is enough |
| **retro** | 2 | 2 | 3 | 1 | soft (gstack state files) | gstack_bin | ~1810 | 136K | 2 | docs-only | TODO/OQ/session notes cover reflect stage |

## Ranking for a *single* deeper port

| Rank | Candidate | Why |
|------|-----------|-----|
| **1 (recommended)** | **investigate → first-party method rewrite** | Highest daily_utility + method_quality; fills a real gap (no dedicated RCA skill); core of the skill is text process (Phases 1–5 + Iron Law), not Claude-only |
| **2** | **cso → first-party checklist rewrite (later)** | Highest unique_gap vs write-guard (FS policy ≠ OWASP/STRIDE audit); larger rewrite; ship after investigate if still needed |
| **3+** | others | Covered by existing ports or unportable without full gstack runtime |

## Recommendation (operator confirm to implement)

1. **Do not** add `skills-external/gstack/*` raw snapshots.  
2. **Next optional implementation:** first-party skill **`investigate`** (name TBD: `investigate` or `debug-rca`) under `bootstrap/grok-cli/skills/`, containing:
   - Iron Law: no fix without root-cause hypothesis  
   - Phases: investigate → pattern analysis → hypothesis test → minimal fix → verify + DEBUG REPORT  
   - 3-strike / blast-radius stops  
   - Handoffs: `/adr` if architectural; mattpocock `tdd` for regression test; `make smoke-*` for integration  
   - **Omit:** gstack preamble, telemetry, freeze bin, GBrain  
3. **Park cso** as optional second rewrite (security checklist + confidence gate + read-only report), not a paths snapshot.  
4. Keep **role recipes** as the default for all other gstack roles.

**Implemented (T-0017):** first-party skill `bootstrap/grok-cli/skills/investigate/`
(`/investigate`) — method rewrite only; no gstack harness.

## Attribute legend for TOOLS.md / catalog notes

When documenting gstack or similar packs, use:

| Tag / phrase | Meaning |
|--------------|---------|
| `docs-only` | Recipes/router only; no install |
| `paths-snapshot` | Curated skills.paths tree |
| `first-party-rewrite` | Owned skill inspired by upstream method |
| `raw-port-blocked` | Upstream SKILL not usable without host harness |

## Related

- [gstack-role-recipes.md](gstack-role-recipes.md)  
- [ADR-0009](../adr/0009-skill-port-hybrid-strategy.md)  
- T-0011 (marketing-council, mattpocock), T-0014 (docs recipes)  
