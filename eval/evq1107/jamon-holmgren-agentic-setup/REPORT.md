# Jamon Holmgren agentic setup evq1107

STAY I1 reference: public checklist, no repo, and AGENTS.md plus the process kit already hold the patterns.

## What it is

X post `2076001786700394610` by Jamon Holmgren (@jamonholmgren), 2026-07-11 17:52:50 GMT. Catalog title: Jamon Holmgren agentic setup (Entry 007 in `sources/x-posts.md`). The post body is the source. It is a checklist numbered 0 through 18: an AGENTS.md router, one workflow skill (he names Matt Pocock and tags `@/AGENT_WORKFLOW.md`), self-healing docs with a short grep header, agents that run the app and fix as they go, end-to-end checks plus a maintenance note, linters that fix or a cheaper model that fixes, cross-model personas, committed worksheets and git tags, end-of-session feedback, a scripts folder, commit sweeps, a conventions note, a night-shift loop, a task queue, false-confidence audits, screenshot diffs, performance benches, profiling, and an end-of-shift full pass. Replies add no repository. One pitches Infinite Red consulting. No SPDX license. This report cites and summarizes. No second copy of the checklist is committed.

No GitHub repository. Entry 007 already says that. Nothing was cloned. No upstream script ran. No package was downloaded. No cache directory was created. No model lock. There is no `sources/entries` file for this slug. The Status line is Entry 007 in `sources/x-posts.md`.

## Ideas, and the pfy file each would touch

| Idea | pfy file | Already covered by |
| --- | --- | --- |
| AGENTS.md is a router. The first lines of a doc stay greppable. | `AGENTS.md` | The router section and the seven-line header rule are already written there. |
| One workflow skill, tagged into a session. | `bootstrap/grok-cli/skills-external/mattpocock` | The post names that repo. It is already on the skill path. No `AGENT_WORKFLOW.md`. |
| Self-healing docs, worksheets, and end-of-session notes. | `bootstrap/grok-cli/skills/hermes-feedback/SKILL.md` | Loop 1 stores short bullets. Step 5 allows a worksheet when the repo already keeps one. |
| Night-shift loop and a task queue. | `bootstrap/grok-cli/skills/agent-loops/SKILL.md`, `docs/TODO.md` | Exits are written first. `docs/ops/loop-engineering.md` is the loop map. |
| Personas at plan, build, and wrap-up. | `docs/ops/gstack-role-recipes.md` | Role recipes are docs. ADR-0009 keeps gstack as docs, not a clone. |
| Conventions and false-confidence audits. | `bootstrap/grok-cli/skills/karpathy-guidelines/SKILL.md`, `bootstrap/grok-cli/skills/prefer-behavior-and-fail-recover-tests/SKILL.md` | Both skills are first-party. |
| Scaffold the same docs into another repo. | `bootstrap/project-process/init.sh` | The process kit is I3. This post has no init script. |
| Run the app, then an end-of-shift full pass. | `docs/ops/MODULAR-CI.md` | The full suite is the nightly backstop. Gap B (the 3 hour `./pfy build` timeout) is unchanged. |

Leave these out: a cheaper-model precommit fixer, a screenshot-diff product, and a second checklist. `docs/ops/plan-mobile-seed-integration.md` records the Entry 007 synthesis as committed. `integration/agenc/skills/loop-engineering/14-step-roadmap.md` already restates the later items. This lane does not revive AgenC.

## Catalog comparison

Same job: setup patterns (router, workflow skill, session notes, loops). A whole-token scan of uses, features, and catalog_tags for workflow, agents-md, agents.md, persona, worksheet, or night hit 6 cards besides this one: gstack, Multica, Auto-Company, repository-harness, Ruben Hassid, and runx. Ruben Hassid is prompt notes. runx seals a skill-run receipt. Broader harness or process tokens hit 11 more cards, including project-process (I3), agent-cage (I3), Harness Score (I0), and harness2 (I1). The table is the close set, plus the skill-path covers the scan misses. `docs/eval/TOOLSET-RANKING.md` (2026-11-07) says no entry from 137 to 167 closes gap B. Entry 007 is older than that list. This lane builds no pipeline, CI, or gate.

| Tool | Stage | How this post compares |
| --- | --- | --- |
| project-process bootstrap | I3 | Scaffolds DESIGN, ADR, TODO, open questions, and AGENTS.md. |
| mattpocock/skills | I1 | The workflow skill the post tells you to grab. Already on the path. |
| gstack | I1 | Role patterns in docs. The clone stays out. |
| karpathy-guidelines | I1 | Coding conventions skill. |
| Hermes Agent (feedback loops) | I1 | Session feedback. The skill is the port. |
| Finn Loop / eval-loop / 8-exits patterns | I1 | Stop card for the night-shift loop. |
| claude-code-unified-agents | I1 | Persona pack. Recipes: `docs/ops/unified-agents-recipes.md`. The card has no uses line. |
| repository-harness | I0 | Would install a map beside AGENTS.md. This post installs nothing. |
| Multica | I1 | Multi-agent board. Not our orchestrator. Patterns only. |
| Auto-Company | I1 | Persona extract already in operator docs. |

Nothing on this list loses its job to the post.

## Gates

Value, 3 of 4 for I3: gap fill no (the patterns are already in tree; gap B stays open). Operator leverage no (no command). Evidence no (the post is the artifact, and there is no runnable quickstart). Blast radius yes (no weights, no runtime, citation only). Score 1 of 4.

Modularity, all 4 for a local copy: the post was enough, there is no package entrypoint, there is no tree to isolate, and the post id on the card survives without a checkout. 1 of 4. Potential stays low. The I2 shelf stays closed. No `self_pipeline`. Uses and features name no CI, test, or review role. The TOOLS.md row already exists (A, overall 81, X Entry 007). No new `data/tools.json` row. No gate wiring.

## Pins and commands

| Item | Value |
| --- | --- |
| Post | `https://x.com/i/status/2076001786700394610` |
| Id | `2076001786700394610` |
| When | 2026-07-11 17:52:50 GMT |
| Repo | none |
| Commands | none. No clone, no install, no timing. |

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| The checklist is copied again | A second workflow file drifts from AGENTS.md | Cite only. `AGENT_WORKFLOW.md` stays absent. |
| A paid model is wired into precommit | Composer or Sonnet becomes a hook | That fixer stays a non-goal. Local checks stay the ones we already run. |
| Gap B is marked closed | The build timeout is treated as a docs problem | The timeout stays a pfy bug. This card stays I1. |
| The consulting reply is treated as a dependency | Infinite Red becomes a vendor | No account, no contract, no package. |

## Next gate

Stay I1 reference. Re-open only if a later ticket names a gap this post fills that AGENTS.md, the process kit, mattpocock, gstack recipes, hermes-feedback, and agent-loops do not, and that ticket still adds no gate. Not a Feature GO.

## Pipeline questions

This lane writes the card, the Entry 007 Status line in `sources/x-posts.md`, and this directory. 1. A later read starts when a person opens the post. The evq scheduler only started this pass. 2. The checklist reads docs the operator already has. It writes no service here. No account and no model on this lane. 3. Next is the driver sanity check, then a fast-forward land. `./pfy` does not call this post. 4. A person re-enters before any second checklist is added, before any I2 copy, and before any gate ticket. `tmp/STOP` in this worktree stops the lane. 5. One worktree and branch (`bot/evq-jamon-holmgren-agentic-setup-1107`) owns this card. A second read must leave the card alone.
