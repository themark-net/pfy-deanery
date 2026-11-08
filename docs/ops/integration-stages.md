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

I2 to I3 runs, tickets, and main-run receipts: [INTEGRATE.md](INTEGRATE.md).

## Stage files

Each tool has its own card at `data/stages/<slug>.json`. Shared fields (`version`, `policy`, `default_stage`, `probe_path`, `coverage`, `handoff`) live in `data/stages/_registry.json`. Do not recreate `data/tool_integration_stages.json`. That single file made every parallel lane conflict on the same lines. `scripts/catalog_check.py` fails if the monolith is added back, and it checks every card: the file parses, `name` is set, the filename is the slug, and `integration_stage` is I0, I1, I2, I3, or I4.

`last_updated` is not stored. `pfylib.stage_registry.load_stages` fills it with the latest per-tool `last_updated` or date field. When no card has one, it uses the git commit date of `data/stages` (`git log -1 --format=%cs -- data/stages`).

Slug: lowercase the tool name, turn each run of non-alphanumeric characters into one `-`, and strip the ends. `name` in the file is the exact tool name. Two names that slug the same are an error; the message names both tools.

Add a tool by writing only its file. Leave every other card alone:

```json
{
  "name": "Example Tool",
  "integration_stage": "I1"
}
```

`write_tool(root, name, card)` in `pfylib.stage_registry` writes that file atomically (indent 2, original key order, trailing newline). Then run `python3 scripts/catalog_check.py`. `make stages-json` (or `python3 -m pfylib.stage_registry --dump`) prints the assembled document in the old shape. `--apply` rewrites only the cards whose facts changed.

## Self-pipeline rule (CI, testing, review)

I0 to I4 measure how far a tool is built into the product. They do not ask whether we use the tool on ourselves. A tool whose uses, features, or tags cover CI, testing, or review cannot reach I3 until it has been applied to pfy-mentat's own pipeline, or a recorded reason says why not.

The field lives on the per-tool card `data/stages/<slug>.json`. `scripts/catalog_check.py` reads it through `pfylib.stage_registry.load_stages`. Do not put the field back into `data/tool_integration_stages.json`.

```json
"self_pipeline": {
  "status": "applied",
  "evidence": "docs/ops/skill-up-eval.md"
}
```

| status | extra | meaning |
|--------|-------|---------|
| `applied` | `evidence`: a commit or a doc path | Used on this repo's own pipeline |
| `not_applicable` | `reason`: why not | The tool covers the job, and a real reason says not to apply it here |
| `pending` | `grace`: `true` to stay at I3 or I4 | Not applied yet. Without grace, `catalog_check.py` fails. Grace is a listed exception, not a promotion. Do not drop the card to I2 unless a person decides to |

Classification order in `scripts/catalog_check.py` (`pipeline_role_hits`):

1. Explicit role tag on `tags` or `catalog_tags`. The token, with a leading `#` removed, is one of: `ci`, `testing`, `test`, `tests`, `review`, `reviews`, `reviewer`, `qa`, `tdd`, `junit`, `pytest`, `lint`, `linter`, `eval`. A tag hit wins. The prose scan is not required.
2. A feature whose whole text is one of those tokens (for example the feature `eval`).
3. Otherwise, whole words in `uses` and `features`: `ci`, `testing`, `test`, `tests`, `review`, `reviews`, `reviewer`, `qa`, `tdd`, `junit`, `pytest`, `lint`, `linter`. The word `eval` inside a sentence is not in this list.

`#pipeline` and `#evaluation` are not role tags. The check fails when a classified tool is at I3 or I4 and `self_pipeline` is missing, `applied` has no evidence, `not_applicable` has no reason, `pending` has no grace, or the status is something else. A classified tool below I3 does not fail for a missing field.

## Agent rules

1. New X/catalog entries start at **I1** (or I0 if Stage 0 fails).
2. Never ask for a subtree “just to have one.”
3. Ambiguous potential + <50 MB → may open I2 probe; record exit criteria.
4. I3 requires value + modularity gates; open ADR only for primary-runtime or architecture shifts.
5. I4 requires explicit checklist in PR (SUBTREES.md).
6. Do not mark a CI, testing, or review tool I3 or I4 without `self_pipeline` (applied with evidence, not_applicable with a reason, or pending with grace).

## Resolution source

OQ-0003 (2026-07-30): Wait for first embed; define value + modularity thresholds; separate integration-stage rubric; staged evaluation default; lightweight intermediary probe (<50 MB) when potential ambiguous; full integration is a later state.
