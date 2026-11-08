# gstack evq1107

gstack (Garry Tan) is a Claude Code skill factory: specialist slash commands plus a Bun browser daemon. The sprint is Think, Plan, Build, Review, Test, Ship, Reflect. License is MIT, Copyright 2026 Garry Tan, at the pin and at HEAD. HEAD `NOTICE.md` records Apache-2.0 for rewritten impeccable text. The repo license stays MIT.

Pin `7c9df1c568a9ea745508f679a329332b2c338063` is v1.60.1.0, committed 2026-07-09 23:49:09 -0700 (`chore(release): v1.60.1.0`). Checkout `~/.cache/pfy/tools/gstack/src`: 1170 git paths (1169 files plus the `connect-chrome` symlink), 59 files named `SKILL.md`, 74 `bin/` paths, 55,582,637 bytes in those files (over 50 MB; `browse/test/fixtures/security-bench-haiku-responses.json` is 28,825,632 bytes). HEAD `d479c5bf1efed979297dc4498c60aef7b67aa639` is v1.98.0.0, committer 2026-11-08 03:23:53Z, 5013 paths, 72 files named `SKILL.md`, 199 `bin/` paths, read with `git show` and not checked out. Commands: `git init`, `remote add origin https://github.com/garrytan/gstack.git`, `git fetch --depth 1 origin` for each SHA, `git checkout --detach` the pin. Pin API 0.307 s. Pin fetch 1 s (21:48:35 to 21:48:36). HEAD fetch 3 s (21:48:36 to 21:48:39). `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` sat under `~/.cache/pfy/tools/gstack`. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`. This lane did not run `./setup`, `bin/`, Bun, or a browser. HEAD has no `--host grok`. `hosts/index.ts` registers claude, codex, factory, kiro, opencode, slate, cursor, openclaw, hermes, gbrain, copilot, agy, and gemini. `hosts/qm.ts` says it is not a HostConfig. The README names Grok only as an other agent in a docs link.

## Ideas, and the pfy file each would touch

1. Sprint order. Already `AGENTS.md` and `docs/ops/gstack-role-recipes.md`.
2. CEO scope modes (expansion, hold, reduction). Already that Think recipe, plus `/adr` and `/open-questions`.
3. Iron Law debugging and a 3-strike stop. Already `bootstrap/grok-cli/skills/investigate/SKILL.md` (T-0017).
4. Destructive-command warning. Already write-guard-mcp (I3). `/freeze` is a prompt lock, not that gate.
5. Docs after ship (Diataxis). Already the `/docs` skill.
6. Do not borrow ETHOS "Boil the Ocean" (still at HEAD). It fights ponytail and karpathy-guidelines.

## Catalog comparison

Same job: a specialist role workflow for one builder. Gap B in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is the unproven `./pfy build` path. That section says no entry from 137 to 167 closes it. Entry 010 is older and is patterns only. This lane builds no pipeline step. Searched `data/stages/*.json` uses, features, and tags.

| Tool | Stage | How gstack compares |
| --- | --- | --- |
| mattpocock/skills | I1 | to-spec, tdd, and code review are already on the path. `/spec` and `/review` overlap. |
| marketing-skills (marketing-council) | I1 | First-party council. Office hours is one voice. |
| Auto-Company | I1 | Persona files and a consensus baton. The daemon stays off. |
| Multica | I1 | Teammate board, not a slash-skill factory. |
| project-process bootstrap | I3 | DESIGN, ADR, TODO, AGENTS. The sprint router already lives there. |
| Finn Loop / eval-loop / 8-exits patterns | I1 | Exit cards. The gstack sprint has no exit card. |
| Hermes Agent (feedback loops) | I1 | Reflect and memory, already a skill. `/learn` and `/retro` overlap. |
| kanbots | I1 | Worktree fan-out. This lane did not spawn `claude -p`. |
| Squadra | I1 | Manual seats and a non-author close. |
| Elephant-Goldfish Model | I1 | Fresh-eyes spec pass. Closer to gap B than another skill tree. |

Also the same shape, already decided: festival I1, Kander I1, Jamon Holmgren agentic setup I1, claude-code-unified-agents I1, odai I0, Hermes Teammates I0. Nearby, not the same job: SkillSpector I3 (gap H2 install gate), write-guard-mcp I3, ponytail (skills pack) I1, karpathy-guidelines I1.

## Gates

Value, 3 of 4 for I3: gap fill no, operator leverage no (Bun plus Claude Code, no Grok host), evidence no (setup was not run), blast radius no (team mode commits a required section and auto-updates; browser daemon and cookie import; ADR-0002 keeps Grok CLI). Score 0 of 4. MIT is fine and the product still wants to be the factory.

Modularity, all 4: the README, ARCHITECTURE, ETHOS, and LICENSE were enough, so a copy was not required to decide. The unit is a monorepo over 50 MB. The cache clone is isolatable, and deleting it leaves the pin. 2 of 4. Potential is low, so I2 stays closed. No self_pipeline field. No gate wiring. No new TOOLS.md row.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Team install | A session clones into `~/.claude/skills/gstack` and commits team mode | This lane ran nothing. ADR-0009 stays. |
| Browser cookies | Cookie import reads the operator browser | Do not run `bin/`. The cache tree stays read-only. |
| Boil the ocean | An agent treats ETHOS as pfy policy and expands the diff | Keep ponytail and karpathy-guidelines. |
| Paid second model | `/codex` calls another hosted CLI | No account. Review stays the mattpocock skill. |
| Gap B false close | A role pack is treated as the build timeout fix | The 3 hour `./pfy build` timeout stays in pfy. |

## Next gate and pipeline

Stay I1 reference. Re-open only if a later ticket shows this pin or HEAD contradicts `docs/ops/gstack-role-recipes.md`, and that ticket still leaves the clone out. No Feature GO.

This lane writes the card, the Entry 010 Status line in `sources/x-posts.md`, and this directory. If a later ticket adopted the tool: (1) a person pastes the Claude install prompt, and the evq scheduler is not that trigger. (2) It would read the repo and a Claude session, and for QA a browser, and write `~/.claude/skills/gstack`, sometimes `CLAUDE.md`, WIP commits, and a PR. This lane called no model and used no account. (3) Next would be the next slash skill. pfy does not start from those commands. (4) A human re-enters at taste questions and at PR approval. Our re-entry stays `/adr`, `/open-questions`, and `tmp/STOP`. (5) One worktree per slug keeps this card private. Two installs would both write `~/.claude/skills/gstack`.

## Verdict

STAY I1 reference: role patterns already live in docs/ops/gstack-role-recipes.md and ADR-0009 blocks the clone
