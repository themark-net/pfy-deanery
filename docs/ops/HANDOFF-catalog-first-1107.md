# Handoff: catalog-first pipeline rule (2026-11-07)

Branch `bot/catalog-first-1107`. Not pushed. No tool was demoted. No card is `pending`.

## What landed

| path | role |
|------|------|
| `AGENTS.md` | Section "Pipeline changes check the catalog first", next to Modular CI. Five software-factory questions, with attribution. |
| `bootstrap/project-process/templates/AGENTS.md` | One-line copy of the same rule, under Process rules. |
| `docs/ops/integration-stages.md` | Self-pipeline rule and the `self_pipeline` card field. |
| `scripts/catalog_check.py` | Fails an I3 or I4 CI, testing, or review tool that lacks the field. |
| `data/stages/skill-up.json` | `self_pipeline` applied. No other card was edited. |
| `tests/test_catalog_self_pipeline.py` | Behavior of the check. |
| `tests/test_stage_registry.py` | The split-snapshot compare ignores `self_pipeline` only. Every other card field still has to match the old monolith. |

`docs/ops/GRILL-STEP.md` and `scripts/pipeline_retro.py` are not on main, so AGENTS.md does not point at them. The software-factory skill is not vendored. The five questions are copied from mattpocock/skills commit `4ae2317`, `skills/in-progress/software-factory/SKILL.md`.

`data/stages/codebase-memory-mcp.json` was not edited. It is I2. Its uses, features, and tags do not classify it as CI, testing, or review, so the field is not required. Another lane owns its smart-CI evidence.

## Catalog check for this gate

This lane extends `scripts/catalog_check.py`. It does not add a CI job, a runner, or a second checker.

Tools considered (`docs/eval/TOOLSET-RANKING.md` and `data/stages/`):

- software-factory: not in the tree. Questions copied, no factory built.
- mattpocock/skills: already on `skills.paths` (review and tdd). Stage I1. Not wired as a new gate.
- skill-up: already the eval path (`make eval-skillup`, `docs/ops/skill-up-eval.md`, promoted in `dc66de2`). Recorded as applied. No second runner.
- codebase-memory-mcp: ranking lists it as the code graph at I2, not as a CI product on this card. Not wired here.
- eval-harness (pfy): already `make eval-structural`. Stage I1, so the new check does not require a field yet.

Five questions for the check itself:

1. Trigger: someone runs `python3 scripts/catalog_check.py` (the existing catalog check). No new clock.
2. It reads stage cards, `TOOLS.md`, and toolsets. It writes nothing. Exit 1 when the rule fails.
3. It triggers no further run. A failure stops until the card is fixed.
4. A human sets applied plus evidence, not_applicable plus a reason, or pending plus grace. The check does not demote.
5. The check is read-only and has no queue. Two runs do not duplicate work.

## Classified tools

Hits are from `pipeline_role_hits` on the current cards. Below I3 the field is not required, and it was not added.

| tool | stage | hit | self_pipeline |
|------|-------|-----|----------------|
| skill-up | I3 | tag `eval` | applied, evidence `docs/ops/skill-up-eval.md` |
| eval-harness (pfy) | I1 | feature `eval` | not required. Already the structural ladder (`make eval-structural`, `examples/eval-harness`). A later I3 needs applied evidence. |
| mattpocock/skills | I1 | tags `tdd`, `review` | not required. On `bootstrap/grok-cli/skills-external/mattpocock`. Not a CI gate. A later I3 needs applied evidence or a not_applicable reason. |
| Chiasmus | I0 | word `review` | not required |
| Elephant-Goldfish Model | I0 | word `review` | not required |
| Hermes Teammates | I0 | word `reviewer` | not required |
| OpenCode Skill Creator | I0 | word `lint` | not required |
| taste-skill | I0 | word `lint` | not required |

I3 tools the check does not classify: Grok CLI bootstrap, SkillSpector, agent-cage (PNNL), project-process bootstrap, write-guard-mcp. No I4 cards.

SkillSpector stays out on purpose. Its uses and features do not hit the word list, and its non-goals already say it is not a pregate or CI gate. `#pipeline` and `#evaluation` are not role tags, so agent-cage, the Grok CLI bootstrap, project-process, and Finn Loop stay out.

## Verify

`python3 scripts/catalog_check.py` exits 0. Behavior tests: an I3 review tool with no field fails; the same card with applied evidence passes; blank evidence fails; a non-CI I3 tool is unchanged; an explicit `#review` tag classifies a card whose uses do not say review; pending without grace fails; pending with grace stays green and does not demote; not_applicable without a reason fails; an I2 review tool does not need the field.
