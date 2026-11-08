# adr-tools evq1107

STAY I1 reference: the adr skill and project-process already number docs/adr, and ADR-0005 rejected this CLI as the process kit. This lane did not install or run the scripts.

## What it is

adr-tools (https://github.com/npryce/adr-tools) is Nat Pryce's shell CLI for a markdown architecture-decision log. LICENSE.txt is GPL-3.0-or-later on the scripts (Copyright 2016 Nat Pryce). Text the tool writes into a project is CC BY 4.0. No catalog pin. `data/tools.json` is a slim subset (8 rows) and has no adr-tools object. Read pin is master HEAD `b3279baf9be2207d1a4f4bbd608fd0b591c72aee` (2020-03-30 10:39:50 +0100, merge of PR 88). Annotated tag 3.0.0 is `1beff1ad582e1ea3e4eb4c9f665ca3443cbc65c7` and peels to `b47d3837d452ca6d2509d2524c7a08c701e84367` (2018-07-25 19:27:20 +0100). That commit is an ancestor of HEAD. HEAD is 5 commits later. README names `adr init`, `adr new`, `adr new -s N`, and `adr help`. The tree also has `adr-list`, `adr-link`, `adr-generate` (toc and graph), `adr-config`, and `adr-upgrade-repository`. Default directory is `doc/adr`. `templates/template.md` in that directory overrides the Nygard sections (Context, Decision, Consequences). Those sections do not include rejected alternatives. 92 tracked files. Work tree 83347 bytes. `.git` is 163054 bytes after the fetches below. Cache `~/.cache/pfy/tools/adr-tools/src`, not committed.

```bash
CACHE=~/.cache/pfy/tools/adr-tools
mkdir -p "$CACHE"/{home,xdg/config,xdg/cache,tmp}
export HOME="$CACHE/home" XDG_CONFIG_HOME="$CACHE/xdg/config" XDG_CACHE_HOME="$CACHE/xdg/cache" TMPDIR="$CACHE/tmp" GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
git clone --depth 1 --filter=blob:none https://github.com/npryce/adr-tools.git "$CACHE/src"
git -C "$CACHE/src" fetch --depth 1 origin tag 3.0.0
git -C "$CACHE/src" fetch --depth 400 origin master
```

Clone wall clock about 1 second (2026-11-08T06:02:25Z to 2026-11-08T06:02:26Z). The later fetches only related the tag to HEAD. No repo script ran. No model lock.

## Ideas, and the pfy file each would touch

1. Markdown ADRs with a two-way supersede link. Already `bootstrap/grok-cli/skills/adr/SKILL.md` and `bootstrap/grok-cli/skills/adr/references/template.md`. Ours requires rejected alternatives (ADR-0001). Theirs does not.
2. ISO dates (`yyyy-mm-dd`). Already that template. Their ADR 0008 chose this over `dd/mm/yyyy`.
3. Next id is one past the highest number. Already the skill numbering step. A second CLI on the same tree can take the same number.
4. `adr generate toc` prints a markdown contents list to stdout. It would touch `docs/adr/README.md`, which the skill updates with Status and Date. Do not add a generator.
5. Named links such as Amends (`adr link`, or `adr new -l`). Would touch the skill supersede step. The References section already points at related ADRs. Do not add a link type.
6. Configured directory, default `doc/adr`. Tag 3.0.0's message is a parent-directory search for that dir. Our tree is `docs/adr` (ADR-0001). The skill already finds `docs/DECISIONS.md`, `docs/ADR.md`, and `docs/adr/`. A `doc/adr` tree would be the second log ADR-0001 forbids.

## What we already have

Grok CLI bootstrap (I3) ships the adr skill. project-process bootstrap (I3) scaffolds DESIGN, multi-file ADR, TODO, open questions, and AGENTS. `docs/ops/adr-tools-companion.md` (T-0007) already says optional CLI and no Makefile dependency. ADR-0005 rejected replacing the kit with adr-tools. X Entry 002 is the 2026-07-11 source note.

## Catalog comparison

Same job: keep an in-repo architecture-decision log. `docs/eval/TOOLSET-RANKING.md` (2026-11-07) ranks entries 137 to 167 and says none of them closes gap B (the `./pfy build` timeout). adr-tools is Entry 002, older than that table. This lane builds no pipeline, CI, or gate. Searched `data/stages/*.json` uses, features, and tags. `#pipeline` alone is not this job.

| Tool | Stage | How adr-tools compares |
| --- | --- | --- |
| project-process bootstrap | I3 | Full process kit. adr-tools only numbers ADR files and has no DESIGN, TODO, or open questions. |
| Grok CLI bootstrap | I3 | Ships the adr skill (number, supersede, rejected alternatives). The card uses line is the operator env, not a second ADR CLI. |
| RoBrain | I0 | Stage card only, not a TOOLS.md row. Retrieves a rejected-alternative row on an ADR re-proposal. It does not write `docs/adr`. |

## Gates

Value, 3 of 4 for I3: gap fill no (ADR-0005), operator leverage no (does not move gap B), evidence no (the README quickstart was not run), blast radius no (GPL-3.0 scripts stay out of the tree; `adr init` would open a second log). Score 0 of 4.

Modularity, all 4: the README, nine `doc/adr` files, the template, and the usage comments were enough, so a local copy was not required to decide. The surface is `src/adr` plus subcommands (92 files, 83347 bytes). The cache clone is isolatable, and deleting it leaves the TOOLS.md row and the companion doc. 3 of 4. Potential is low, so I2 stays closed. Size is under 50 MB. No `self_pipeline` field. Uses, features, and tags are not a CI, test, or review role. No gate wiring. No new TOOLS.md row.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Second log | `adr init` creates `doc/adr` beside `docs/adr` | This lane ran nothing. ADR-0001 stays. |
| Dual numbers | Skill and CLI pick the same next id | Do not put the CLI on PATH for this repo. |
| GPL copy | Scripts land in git | Cache only. Not committed. |
| Gap B false close | A numbering CLI is treated as the build timeout fix | The timeout stays in pfy. |
| Quiet upstream | HEAD is 2020-03-30, five commits after tag 3.0.0 | Reference only. Nothing on PATH to go stale. |

## Next gate and pipeline

Stay I1 reference. Re-open only if a later ticket shows agents stopped writing `docs/adr` and that ticket still leaves the scripts out of the repo. No Feature GO.

If a later ticket adopted the CLI: (1) a person runs `adr init` or `adr new`. The evq scheduler is not that trigger. (2) It reads the ADR directory and an optional template, writes the next markdown file, rewrites a superseded Status, and opens VISUAL or EDITOR. No model and no account. (3) Next is the editor, then git. pfy does not start a build from that. (4) A human fills Context, Decision, and Consequences in the editor. Our re-entry stays `/adr`, `/open-questions`, and `tmp/STOP`. (5) Two `adr new` runs can take the same number. One worktree per slug keeps this card private. We do not run the CLI, so that race stays closed.

## Verdict

STAY I1 reference: the adr skill and project-process already number docs/adr, and ADR-0005 rejected this CLI as the process kit
