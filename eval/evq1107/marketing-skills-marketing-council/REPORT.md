# marketing-skills (marketing-council) evq1107

STAY I1 reference: the council port tracks this pin except a process banner; the other 46 skills do not move the pfy build timeout

## What it is

Marketing Skills (coreyhaines31/marketingskills) is a pack of markdown agent skills, Node helpers, and integration notes for Claude Code, Codex, Cursor, and other Agent Skills hosts. At this pin, plugin.json and marketplace.json say version 2.8.7. The X entry named v2.8.0. That changelog line (2026-07-06) is the one that added marketing-council. This pin is the 2026-07-10 merge, still with marketing-council at metadata.version 1.0.0. License is MIT. Root LICENSE. Copyright (c) 2025 Corey Haines. 47 skill directories, 415 files, worktree 3174365 bytes without `.git` (4482892 with it). `tools/clis` has 64 `.js` files. AGENTS.md says 51 CLI tools. `tools/integrations` has 93 notes. No file under `skills/` is executable. The longest SKILL.md is seo-audit at 497 lines.

The council skill seats 12 named advisors. Modes are one seat, 3 to 5, or all 12. A council session seats a dissenter. Quick take is one named advisor. The output is a disagreement map and a chair summary. Dossiers live under `references/advisors/`.

## Pin and command

| Item | Value |
| --- | --- |
| Pin | `5139746081be40a975316a0a11d8bcf61fae8fe4` (manifest short pin `5139746081be`) |
| Commit | 2026-07-10 16:02:00 -0700. Merge pull request #438 from coreyhaines31/development. |
| Fetch | 0.805 s for fetch plus checkout. `git init`, `git fetch --depth 1 --filter=blob:none origin 5139746081be40a975316a0a11d8bcf61fae8fe4`, `git checkout --detach FETCH_HEAD`. No upstream script. |
| Cache | `~/.cache/pfy/tools/marketing-skills-marketing-council/src`. Not committed. |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `npm_config_cache`, and `TMPDIR` sat under that cache. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`.

## Ideas, and the pfy file each would touch

1. A required dissenter and a disagreement map. Already `bootstrap/grok-cli/skills/marketing-council/SKILL.md`, `AGENTS.md`, and `docs/ops/gstack-role-recipes.md`.
2. Load only the seated dossiers. Already `references/advisors/` beside that skill. 14 of the 15 files at the pin match the port byte for byte. SKILL.md is the exception (pin 12480 bytes, 161 lines; port 12924 bytes, 168 lines): the T-0011 banner and the `/adr` handoff. `PORT.md` is only in the port. `.grok/skills/marketing-council` matches the bootstrap copy on 16 of 16 files.
3. Read one product context file before questions. The skill already checks `.agents/product-marketing.md`. Operators already read `docs/DESIGN.md`. Leave that as the context file.
4. Keep each SKILL.md under 500 lines. Already `docs/adr/0009-skill-port-hybrid-strategy.md`. Leave the other 46 skills out.
5. Leave the GitHub `VERSIONS.md` fetch and the Claude shell-injection syntax. The pin stays `bootstrap/grok-cli/manifest.json`. The port has no shell-injection line.

## Catalog comparison

Same job: a multi-advisor prompt for a marketing decision, and a skill pack. Gap B in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is the `./pfy build` timeout. That section covers entries 137 to 167 and says none of them closes B. Entry 004 is older. This lane builds no pipeline, CI, or gate. Searched `data/stages/*.json` uses, features, and tags.

| Tool | Stage | How this pack compares |
| --- | --- | --- |
| gstack | I1 | Role patterns already in docs. Not this bench. |
| Auto-Company | I1 | Persona files. The daemon stays out. This council is one skill. |
| mattpocock/skills | I1 | Plan skills already on the path. Tag `#review` is a different job. |
| MCO | I1 | Parallel raw answers. Its probe kept 0 comparison decisions. |
| Squadra | I1 | Manual seats on one task. Not a marketing bench. |
| multi-agent-generator | I0 | Emits team source. Its debate text allows agreement. |
| awesome-hermes-skills | I1 | A skill index. Tag `#prompt-pack`. Not this council. |
| Hermes feedback loops | I1 | A feedback skill. Not a bench. |
| SkillSpector | I3 | Scan before a fetched skill is copied. This lane copied nothing. |
| Skills Manager | I0 | A second hub. `install.sh` plus this tree stay the source. |

The first-party skill already covers this pin.

## Gates

Value, 3 of 4 for I3: gap fill no (the council is already the first-party skill; gap B is the build timeout). Operator leverage no (the other 46 skills and the CLI files do not shorten that timeout). Evidence no (docs read only; no `npx`, no script). Blast radius yes for the markdown (MIT, 3174365 bytes, no weights, not a second runtime). Score 1 of 4.

Modularity, all 4: the README, AGENTS.md, and the council skill were enough, so a local copy was not required to decide. The unit is 47 skills plus `tools/`. The cache clone is isolatable, and deleting it leaves the manifest pin. 2 of 4. Under the 50 MB I2 bar. Potential for a further pull-in is low, so I2 stays closed. Uses and features name no pipeline role. No `self_pipeline`. No gate wiring. TOOLS.md already has the row. This lane did not edit it.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Handoff to missing skills | The chair names positioning, offers, copy, and ads. Those skills are not under `bootstrap/grok-cli/skills/`. | The port points at `/adr` and `/open-questions`. Do not run `npx skills add`. |
| Update check | AGENTS.md says fetch `VERSIONS.md` from GitHub, then `git pull`. | Keep the manifest pin. This lane did not pull the pack. |
| CLI or Composio | A helper calls an ads or CRM account. | Do not run `tools/clis`. No account. |
| Pack treated as the build fix | 47 skills look like gap B progress. | Gap B stays the `./pfy build` timeout. Verdict stays I1. |

## Next gate

Stay I1 reference. Re-open only if a later ticket shows this pin's council `SKILL.md` contradicts the first-party port, and that ticket still leaves the other 46 skills out. No Feature GO.

## Pipeline questions

This lane writes the card, the Entry 004 Status line in `sources/x-posts.md`, and this directory.

1. Trigger, if a person uses it later: they invoke `/marketing-council`. The evq scheduler only started this read.
2. The skill reads the seated dossiers and writes a simulated board note in the chat. The CLI helpers would call outside accounts. This lane called no model and used no account.
3. Next is `/adr` or `/open-questions`. `./pfy build` does not start from this skill.
4. A human re-enters before any install, any `git pull` of the pack, or any I2 copy.
5. One worktree per slug (`bot/evq-marketing-skills-marketing-council-1107`) keeps this card private.
