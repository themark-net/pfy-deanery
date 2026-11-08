# Ruben Hassid context/token hacks evq1107

STAY I0 reference: public prompt notes, no repo, and the same habits already live in pfy docs.

## What it is

X post `2075807299638014212` by Ruben Hassid (@rubenhassid), 2026-07-11 05:00:01 GMT. Catalog title: 21 Claude $20 plan hacks (Entry 009 in `sources/x-posts.md`). The post body is the source. It is a list of chat habits that keep a Claude subscription on the cheaper plan: turn bulky files into markdown, plan before the coding surface, keep prompts short and reusable, edit one part, batch related asks, edit the original message, pick a cheaper model for a short task, keep the standing brief short and end with a session note, summarize and start a fresh chat, reuse a project for files that recur, attach only the files this task needs, one topic per chat, leave extra features off, schedule a weekly briefing, name the repo task, keep preferences minimal, speak the prompt, split the rolling usage window, and use another product when Claude is the wrong tool. The exact `.md` files sit behind a free newsletter and a Notion link. This lane did not open that gate. Entry 074 is a later Ruben skills post and is a different row.

No GitHub repository. Entry 009 already says that. Nothing was cloned. No upstream script ran. No package was downloaded. No cache directory was created. No model lock.

## License

No SPDX license. The post is public. The prompt files are a newsletter download, so their license is unclear. This report cites and summarizes. No prompt text is copied into the repo.

## Ideas, and the pfy file each would touch

| Idea | pfy file | Already covered by |
| --- | --- | --- |
| Keep the standing brief short. End with a few reusable notes, then a fresh session. | `AGENTS.md`, `bootstrap/grok-cli/skills/hermes-feedback/SKILL.md` | AGENTS.md is the router. Hermes Loop 1 stores short bullets before compaction. |
| Plan, then one scoped build. Write the stop rules first. | `docs/ops/gstack-role-recipes.md`, `bootstrap/grok-cli/skills/agent-loops/SKILL.md` | The role router starts with Think, then Plan, then Build. Exits are written before the run. |
| A reusable prompt is a file with a variable, already in the tree. | `bootstrap/grok-cli/skills/` | karpathy-guidelines is a first-party skill. ponytail is on `skills.paths`. |
| Cheap model for bulk work. Strong model for hard work. | `docs/ops/local-cloud-split.md` | Grok is the monitor. The local worker does bulk. |
| Stop rereading the whole tree. | `docs/evaluation/codebase-memory-vs-graphify.md` | codebase-memory-mcp is primary for that. headson caps a JSON preview. repowise packs tokens. |

Leave these out: turning memory off, Wispr, Claude `/schedule`, a Gemini dependency, Cowork, and the newsletter files. A reply on the thread already says turning memory off reloads context. That fights Hermes Loop 1.

## Catalog comparison

Same job: cut reloaded context, and keep a reusable prompt. A search of `data/stages/*.json` uses, features, and tags for token, context, prompt, memory, and summar hit 35 cards. The table is the subset that does this job. `docs/eval/TOOLSET-RANKING.md` (2026-11-07) ranks entries 137 to 167 and assigns gap H1 to skill-up. Entry 009 is older than that list. This lane builds no pipeline, CI, or gate.

| Tool | Stage | How this post compares |
| --- | --- | --- |
| skill-up | I3 | With/without grade (5/5 both arms, delta 0). This post has no score. |
| harness2 | I1 | Local trial on the 48-case set. Gain 0. Tips leave that measurement where it is. |
| repowise | I2 | Context packing probe. This post is a list. |
| codebase-memory-mcp | I2 | Primary code graph. A named query replaces reading the whole repo. |
| headson | I2 | Byte budget for JSON and YAML in a prompt. |
| karpathy-guidelines, ponytail | I1, I1 | Short surgical prompts and a YAGNI pack, already installed. |
| Hermes feedback loops | I1 | Session memory. The "turn memory off" hack fights this skill. |
| HiRoute, llm-router | I2, I0 | Cheap turns go to the local model. The post splits Sonnet and Opus on a Claude bill. |
| LEANN, OpenContext, ai-memory, opencode-mem, MemPalace | I1, I1, I1, I2, I1 | Stores with recall numbers. This post stores nothing. |
| Jamon Holmgren agentic setup | I1 | One public workflow post. The process kit already covers it. |
| Grok CLI bootstrap | I3 | Skills install is the prompt library. |

Nothing on this list loses its job to the post.

## Gates

Value, 3 of 4 for I3: gap fill no (H1 is the skill-up score). Operator leverage no (no command). Evidence no (the post is the artifact). Blast radius yes (no weights, no runtime, citation only). Score 1 of 4.

Modularity, all 4 for a local copy: docs were enough, there is no package entrypoint, there is no tree to isolate, and the post id on the card survives without a checkout. 1 of 4. Potential is low, so the I2 shelf stays closed. No `self_pipeline`. Uses and features name no CI, test, or review role. The TOOLS.md row already exists (B, overall 77, X Entry 009). No `data/tools.json` row. This lane adds none. No gate wiring.

## Pins and commands

| Item | Value |
| --- | --- |
| Post | `https://x.com/i/status/2075807299638014212` |
| Id | `2075807299638014212` |
| When | 2026-07-11 05:00:01 GMT |
| Quoted article | `2042998030832668675` (not opened) |
| Repo | none |
| Commands | none. No clone, no install, no timing. |

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Newsletter prompts land in-tree | A later lane copies the Notion files | Cite only. Those files stay out of git. |
| Memory is switched off | Every session reloads the standing brief | Keep Hermes Loop 1. The card lists `turn_memory_off` as a non-goal. |
| The list is treated as an H1 score | Gap H1 is marked closed | skill-up stays the scorer. This card stays I0. |
| A Claude surface becomes a dependency | Cowork, `/schedule`, Wispr, or Gemini is added | Those names stay on the non-goals list. |

## Next gate

Stay I0 reference. Re-open only if a later ticket copies one habit into an existing pfy doc (a short standing brief, or a session note before compaction) and grills that copy. Not a Feature GO.

## Pipeline questions

This lane writes the card, the Entry 009 Status line in `sources/x-posts.md`, and this directory. 1. A later read starts when a person opens the post. The evq scheduler only started this pass. 2. The list would read a chat and the files a person attached. It writes no service here. No account and no model on this lane. 3. Next is the driver sanity check, then a fast-forward land. `./pfy` does not call this post. 4. A person re-enters before any prompt file is copied, before any I1 pin, and before any gate ticket. `tmp/STOP` in this worktree stops the lane. 5. One worktree and branch (`bot/evq-ruben-hassid-context-token-hacks-1107`) owns this card. A second read must leave the card alone.
