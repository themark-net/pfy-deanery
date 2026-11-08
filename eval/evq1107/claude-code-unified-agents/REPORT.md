# claude-code-unified-agents evq1107

STAY I1 reference: the curated 16 paths already sit on skills.paths, and a persona pack does not close the pfy build timeout.

## What it is

stretchcloud/claude-code-unified-agents is a Claude Code sub-agent prompt pack. License is MIT, copyright 2024 StretchCloud (root LICENSE). The README says 54 production-ready agents and that each file has 1000+ lines. The pin has 53 markdown files under `claude-code-unified-agents/.claude/agents/` (35,250 lines by splitlines, 999,833 bytes). None of the 53 ends with a newline, so wc -l is 35,197. 15 files have at least 1000 lines. 38 do not. Shortest is backend-architect at 46 lines, the same count as the 2026-07-31 table. README and AGENTS_LIST name performance-optimizer, ui-designer, content-strategist, and iot-engineer. Those files are absent. Frontmatter on all 53 files sets name, description, category, color, and tools. Counts: development 14, infrastructure 7, quality 6, data-ai 6, business 6, specialized 12, creative 1, core 1 (orchestrator, tools: Task only). `scripts/install.sh` defaults to `$HOME/.claude/agents` (user) or `.claude/agents` (project). `scripts/quick-install.sh` clones, then runs install.sh. This lane ran neither script.

pfy already keeps 16 SKILL.md files under `bootstrap/grok-cli/skills-external/claude-unified-agents/` (manifest pin matches). The 2026-07-31 receipt scored 53 agents, 52 pass, mean 4.06 (`pipelines/eval/unified-agents-eval.latest.md`). Recipes: `docs/ops/unified-agents-recipes.md`. ADR-0009 is the paths-snapshot rule. ADR-0002 keeps Grok CLI primary. No `sources/entries` file (ticket entry was `-`). Status line updated in the 2026-07-31 block of `sources/x-posts.md`. `data/tools.json` has no object with this name (8 tools in the slim file). TOOLS.md has an A-tier heading and field table. `catalog_check.py` still lists the card as stage-only, because that section is not a `| **name** |` row. This lane did not edit TOOLS.md.

## Pin and command

| Item | Value |
| --- | --- |
| Pin | `b026de60c0fc5438f53faffb5cd7f43f84ed3267` |
| Commit | 2025-08-03 17:11:46 +0100. `updated gitignore` |
| ls-remote HEAD | same SHA |
| Time | fetch 0.44 s, checkout 0.01 s |
| Size | 1,078,626 bytes excluding `.git`. `.git` 403,412. 61 git paths. |
| Cache | `~/.cache/pfy/tools/claude-code-unified-agents/src`. Not committed. |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` were under that cache. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`. Command: `git init`, remote `https://github.com/stretchcloud/claude-code-unified-agents.git`, `git fetch --depth 1 origin b026de60c0fc5438f53faffb5cd7f43f84ed3267`, `git checkout --detach FETCH_HEAD`, `git ls-remote origin HEAD`.

## Ideas, and the pfy file each would touch

1. A short roster of specialist postures. Already `docs/ops/unified-agents-recipes.md` and the 16 SKILL.md files. The product router is `AGENTS.md`.
2. When two skills match, name the one to prefer. Already the table in `docs/ops/unified-agents-recipes.md` (orchestrator to `/agent-loops`, error-detective to `/investigate`, the reviewer file to mattpocock `code-review`).
3. Score frontmatter and length before any copy. Already `scripts/eval_unified_agents_pack.py`. The install gate for a fetched skill is SkillSpector (I3), not install.sh.
4. A delegation plan before a long task. Already `docs/ops/loop-engineering.md` and `bootstrap/grok-cli/skills/agent-loops/SKILL.md`. Leave the Claude Task tool out.
5. A per-agent tool allow-list. Cage policy and write-guard already bound tools. Do not copy Claude tool names into the cage.

Leave out curl-to-bash, a copy into `~/.claude`, domain dumps (game, healthcare, fintech), and Claude Code as the operator UI.

## Catalog comparison

Same job: specialist role prompts for one coding agent. Gap B in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is the unproven `./pfy build` path (3 hour timeout). That section says no entry from 137 to 167 closes it. This block is the 2026-07-31 x-posts note, older than that list. This lane builds no pipeline, CI, or gate. Scanned `data/stages/*.json` uses, features, and tags.

| Tool | Stage | How this pack compares |
| --- | --- | --- |
| gstack | I1 | Role recipes in docs. ADR-0009 blocks that clone. The same ADR allows a curated paths snapshot. PORT.md already places this pack there. The ADR table names gstack, not this repo. |
| mattpocock/skills | I1 | Plan and review skills already on the path. Prefer them where the recipes say so. |
| ponytail (skills pack) | I1 | Same skills.paths mechanism. YAGNI pack, already installed. |
| karpathy-guidelines | I1 | Coding-behavior skill already in the tree. |
| Hermes Agent (feedback loops) | I1 | Session feedback skill. The context-manager file was mapped to docs, not copied. |
| Finn Loop / eval-loop / 8-exits patterns | I1 | Exit card. The orchestrator file has no eight exits. |
| Auto-Company | I1 | Persona extract in operator docs. The daemon stays off. |
| Jamon Holmgren agentic setup | I1 | Checklist already in AGENTS.md. |
| project-process bootstrap | I3 | Scaffolds DESIGN, ADR, TODO, and AGENTS.md. |
| SkillSpector | I3 | Scans a skill before copy. install.sh does not. |
| Elephant-Goldfish Model | I1 | Fresh-eyes spec before Build. Closer to gap B than another persona file. |
| kanbots | I1 | Worktree fan-out. Its probe did not move the timeout. |
| agent-cage (PNNL) | I3 | The lab. This pack is not a runtime. |

## Gates

Value, 3 of 4 for I3: gap fill no (B is the build timeout; the 16 postures are already on the path). Operator leverage no (install.sh writes `~/.claude/agents`, not the Grok path, and the glue is already done). Evidence yes for the 2026-07-31 receipt (52/53, mean 4.06). This lane did not re-run it. Blast yes for the curated snapshot (MIT, about 1 MB, no weights) while Claude stays non-primary. Score 2 of 4.

Modularity, all 4: the README, LICENSE, and file list were enough, so a product copy was not required. The unit is one agents directory plus three scripts. The cache tree is isolatable. Deleting it leaves the pin and the 16 skills. 3 of 4. Size is under 50 MB. Potential is low, not ambiguous, so I2 stays closed. Uses and features name no pipeline role. No `self_pipeline`. No gate wiring. No new TOOLS.md row.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| install.sh | A session copies 53 files into `~/.claude/agents` | This lane ran nothing. Stay on the 16 paths. |
| curl pipe | quick-install.sh clones, then runs install.sh | Do not run it. |
| Primary UI | `/agents` replaces Grok | ADR-0002. Stay I1. |
| Domain dumps | A long industry file becomes a first-party skill | No new copy. PORT.md already skipped that. |
| Gap B false close | A persona pack is counted as the timeout fix | Verdict stays I1. |

## Next gate and pipeline

Stay I1 reference. Re-open only if a later ticket shows this pin is no longer upstream HEAD, or the recipes no longer match the 16 files, and that ticket still does not run install.sh and adds no gate. Not a Feature GO.

1. Trigger, if adopted later: a person runs install.sh. The evq scheduler is not that trigger.
2. It would read the markdown and write `~/.claude/agents` or `.claude/agents`. This lane only read docs. No model and no account.
3. Next would be Claude `/agents`. pfy does not start there. The build timeout stays in pfy.
4. A human re-enters before any install, any Claude home write, or any I3 wiring. Stop files: `tmp/STOP` and `tmp/evq/STOP`.
5. One worktree (`bot/evq-claude-code-unified-agents-1107`) keeps this card private. Two installs would both write `~/.claude/agents`.
