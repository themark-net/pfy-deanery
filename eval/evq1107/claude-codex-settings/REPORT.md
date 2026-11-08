# claude-codex-settings evq1107

STAY I1 reference: hook pack for other CLIs; the patterns already sit in docs/ops/claude-codex-quality-hooks.md and H2 stays with SkillSpector

## What it is

fcakyon/claude-codex-settings is marketplace `claude-settings` 2.10.0: skills, command hooks, and settings for Claude Code, Codex CLI, Cursor, and Antigravity CLI. The README quotes Karpathy on overcomplication and missing clarification. Root LICENSE is Apache-2.0. Of 38 local plugin manifests, 28 say Apache-2.0 and 10 say MIT. The Claude marketplace lists 41 names: those 38, plus anthropic-essentials, anthropic-plugin-dev, and labrat, which point at other git URLs this lane did not clone. Local tree: 114 `SKILL.md` files, 6 agent files, 21 command files, 4 MCP configs, 7 `hooks.json` files, 23 files under `hooks/`, 1347 files, 9264115 bytes without `.git`. All 7 `hooks.json` files use command hooks only. Events include before a tool call, after an edit or write, session start, prompt submit, and before compact. Antigravity drops hooks. Grok is not a target.

## Pin and command

| Item | Value |
| --- | --- |
| Pin | `0574bbbae11bd710f063abe62cf2c1b5b6d157c4` |
| Commit | 2026-11-07 19:06:16 +0300. docs: run simplify on docs-only commits too (#374). |
| Fetch | 0.82 s. `git clone --depth 1 https://github.com/fcakyon/claude-codex-settings.git`. No upstream script. |
| Cache | `~/.cache/pfy/tools/claude-codex-settings/src`. Not committed. |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `npm_config_cache`, and `TMPDIR` sat under `~/.cache/pfy/tools/claude-codex-settings`. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`. This lane did not run claude, codex, cursor-agent, uv, or any script.

## Ideas, and the pfy file each would touch

1. Deny force-push (`--force`, `-f`, `--force-with-lease`, a leading `+` refspec) and `git rebase`, after stripping quoted text. Already `docs/ops/claude-codex-quality-hooks.md` and destructive-command-guard.
2. One-use marker `simplify-guard.ok` in the worktree git dir so a commit waits for `/simplify`, with an explicit skip. Other runtimes stay open. Already ponytail, karpathy-guidelines, and `/one-shot`.
3. Block AI-attribution trailers on `git commit` and `gh`. A later policy would edit the same quality-hooks note. This lane copies no script.
4. Block buzzword marks on writes and on commit or PR text. The en dash stays. Already the house style rule, anti-slop, and Sloptrim. Sloptrim's card refuses Claude hooks.
5. `AGENTS.md` is a symlink to `CLAUDE.md`. Already `AGENTS.md` and project-process bootstrap.

The 2026-07-30 extract still matches these five patterns at this pin. It does not name the attribution trailer hook, the design-PR image hook, or the PreCompact priority script. Those stay in the upstream tree.

## Catalog comparison

Gap H2 in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is the missing skill install gate. The 2026-10-06 section lists this pack under skip or hold. This lane builds no pipeline step. Searched `data/stages/*.json` uses, features, and tags for hooks, skill copy, and shared agent guidance. Gateway, memory, and router hits (magpie, opencode-mem, llm-router) are other jobs.

| Tool | Stage | Same job |
| --- | --- | --- |
| SkillSpector | I3 | Static scan before a skill copy. This pack installs by marketplace name. |
| Sandlock | I2 | Confines one install command. This pack has no confinement. |
| asm | I1 | Copies a skill. The probe still copied a high-risk file. |
| Skills Manager | I0 | Home hub and symlinks. install.sh plus SkillSpector cover that job. |
| write-guard-mcp | I3 | Mediates file writes. The force-push script reads the shell command. |
| destructive-command-guard | I2 | Denies destructive git, filesystem, and disk commands. |
| karpathy-guidelines | I1 | The same Karpathy pitfalls, already a first-party skill. |
| ponytail | I1 | YAGNI pack on skills.paths. It has no fetch refusal. |
| anti-slop | I0 | Prompt rules for generic copy. |
| Sloptrim | I1 | Offline prose score. Card non-goal includes Claude hooks. |
| project-process bootstrap | I3 | Scaffolds DESIGN, ADR, TODO, open questions, and AGENTS.md. |

Also adjacent: Bumblebee (MCP config scan, I2), CodeGuard (rule text, I0), Harness Score (grades hook files, I0), repository-harness (`AGENTS.md` installer, I0), agent-cage (lab isolation, I3).

## Gates

Value, 3 of 4 for I3: gap fill no (H2 stays SkillSpector; unsafe git stays destructive-command-guard), operator leverage no (hooks fire in Claude or Codex), evidence no (install needs those CLIs and writes their homes; this lane ran nothing), blast radius no (root Apache-2.0 and 9264115 bytes with no weights, but four anthropic-office-skills LICENSE.txt files forbid copies outside Anthropic services while that plugin manifest says MIT). Score 0 of 4.

Modularity, all 4: README, `CLAUDE.md`, and the seven `hooks.json` files were enough to decide. The unit is 38 plugins plus a site and sync scripts, so the surface is wide. The cache clone is isolatable. Deleting it leaves the pin. 2 of 4. 9264115 bytes is under the 50 MB I2 bar. Potential is low, so I2 stays closed. No `self_pipeline`. No gate wiring. No new TOOLS.md row.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Marketplace add writes a real home | claude, codex, and cursor-agent install into their config dirs | This lane ran no installer. A later copy uses a temp HOME. |
| Hook script treated as a Grok policy | The seven hooks are commands for those CLIs | Keep the pattern note. Do not vendor scripts. |
| Hosted model recipe looks local | README sets `ANTHROPIC_BASE_URL` to Moonshot, MiniMax, or Z.ai, and the Codex config uses workspace-write with network | Leave Ollama and llama-server on the pfy path. No key. |
| simplify marker looks like a gate | Other runtimes stay open, and a user can mint a one-use skip | Do not wire pregate. |
| Remote marketplace plugins | Three entries clone other git URLs at install time | This lane did not fetch them. |
| Anthropic office skills | Four LICENSE.txt files forbid copies outside Anthropic services; the plugin manifest says MIT | Cite only. Those files stay in the cache clone. |

## Next gate

Stay I1 reference. Re-open only if a later ticket names one policy and copies that rule into write-guard or destructive-command-guard. No install and no Feature GO.

## Pipeline questions

This lane writes the card, the entry Status line, and this directory.

1. Trigger, if a later ticket adopted a hook: a person names one policy. The evq scheduler is not that trigger.
2. It would read a Claude or Codex tool call and run a hook script. It would write a deny or a one-use git marker. This lane called no model and used no account.
3. Next would be the tool call, or a blocked one. pfy does not start from `hooks.json`.
4. A human re-enters on the one-use skip, or by editing the pattern note. Gate wiring needs a separate ticket and Mark's GO.
5. One worktree per slug keeps this card private. Two marketplace installs into one home would both write that home.
