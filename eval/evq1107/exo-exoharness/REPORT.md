# Exo (exoharness) evq1107

STAY I1 reference: patterns already extracted; Docker plus a hosted key, and it does not close the pfy build timeout.

## What it is

Exo (https://github.com/exoharness/exo) is a Rust and TypeScript agent harness. License is MIT. `LICENSE` copyright 2026 Ankur Goyal. `Cargo.toml` and `package.json` both say `license` MIT. Version 0.1.0. Rust edition 2024, `rust-version` 1.95. Crates: cli, cost, executor, exoharness. The README describes a complete harness (tools, tasks, integrations) that can see its own code and logs, clone itself, and change prompts, memory, tools, and harness policy. The quick start asks for git, Docker, mise, and an OpenAI or OpenRouter key. `.env.example` names `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `CURSOR_API_KEY`, and Braintrust variables. Canonical chat is ExoChat at exoharness.ai. This lane did not run `setup.sh`, `exo.sh`, cargo, pnpm, or Docker.

The July pin still matches the pattern note. `docs/RSI.md` keeps an append-only event log outside the sandbox. `examples/exo/docs/SELF-CONTROL.md` section 8 is snapshot, cargo or pnpm checks, `rebuild_and_restart_exo(reason)`, then git revert or `rewind_sandbox`. The canary clone is still an upstream gap (sections 4 and 7: sandbox clone and agent clone are not built). `docs/design/skills-arch.md` stores skills as artifacts (name and description every turn, body on demand). `docs/sandbox-snapshots.md` captures filesystem bytes only. The skill index is read-modify-write with no compare-and-swap.

There is no `sources/entries` file. The Status line in shared `sources/x-posts.md` still says Cataloged 2026-07-31. This lane left that file alone. Status for this pass is the card and `eval/evq1107/exo-exoharness/VERDICT`.

## Pin and command

| Item | Value |
| --- | --- |
| Pin | `372602d1b553af06e9843e19f31fa8a7f749ab6e`. Subject `scheduler: durable state, slot-anchored fires, one-shot @at, and a durable fire->wake handoff (#185)`. The pin stores that arrow as U+2192. Author date 2026-07-30T14:40:17-07:00. |
| Tip | `d7fb6d2ee477dec48d272461b4c534152939ad22` from `git ls-remote origin HEAD`. Subject `fix(mcp): use initialize-compatible protocol (#412)`. Author date 2026-11-02T20:26:25-08:00. Metadata only. Worktree stayed on the pin. |
| Fetch | `~/.cache/pfy/tools/exo-exoharness/src`. `git init`, remote `https://github.com/exoharness/exo.git`, `git fetch --depth 1 --filter=blob:none origin 372602d1b553af06e9843e19f31fa8a7f749ab6e`, `git checkout --detach FETCH_HEAD`. Wall time 1 s (2026-11-07T22:02:55-08:00 to 22:02:56-08:00). `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` were under that cache. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`. |
| Bytes | Worktree 304 files, 8162536 bytes. `.git` 3291254 bytes. Total 11453790. Under 50 MB. No setup.sh, exo.sh, cargo, pnpm, Docker, or model. |

## Ideas, and the pfy file each would touch

| Idea | pfy file | What we already have |
| --- | --- | --- |
| Event log survives rewind. | `docs/ops/exo-self-mod-patterns.md` | That note already maps the log to pipelines, git, and hermes-feedback. |
| Snapshot, then a named rebuild with a reason. | `docs/ops/integration-self-mod-eval.md` | `make eval-integration-change` is the ingest loop. A rebuild of this repo stays off. |
| Skills as artifacts, name and description first. | `bootstrap/grok-cli/skills/` | Progressive disclosure is already the skill layout. |
| Canary clone before adopt. Upstream has not built it. | `docs/ops/integration-self-mod-eval.md` | Adoption stays an ADR plus a PR. `default_harness` stays grok (`docs/modules/exo-adapter.md`). |

## Catalog comparison

Same job: a full agent harness that can change itself, and gap B in `docs/eval/TOOLSET-RANKING.md` (2026-11-07), the unproven `./pfy build` path. That section says no entry from 137 to 167 closes gap B. Exo is the 2026-07-31 x-posts entry, outside that range. The 2026-10-06 section holds Exo as an unsafe runtime. This lane builds no pipeline, CI, or gate. A word scan of uses, features, tags, non_goals, and intent (harness, self-mod, sandbox, rebuild, lane, review, build) matched 49 cards. The table is the harness set. Gap B neighbors in that scan are Elephant-Goldfish, Chiasmus, Aider, kanbots, festival, MCO, Squadra, and rulora. They cover spec passes, impact, or lane stops. Exo does not move the build timeout either.

| Tool | Stage | How Exo compares |
| --- | --- | --- |
| Grok CLI bootstrap | I3 | Operator surface. Exo stays a lab stub in `data/harnesses.json` (issue 60). |
| agent-cage (PNNL) | I3 | Lab sandbox and policy. Exo wants its own Docker sandbox. |
| project-process bootstrap | I3 | DESIGN, ADR, TODO, AGENTS. The upstream AGENTS.md is data for this read. |
| write-guard-mcp | I3 | Named writes above the cage. The Exo guardian is a host CLI beside the agent. |
| destructive_command_guard | I2 | Denies destructive shell commands. Exo `shell` runs inside its sandbox. |
| Hermes Agent (feedback loops) | I1 | Session memory is already a skill. |
| MUE-X | I1 | Paired self-mod note. Same hold. |
| Finn Loop / eval-loop / 8-exits patterns | I1 | Exit cards. Exo section 8 has no eight-exit card. |
| harness2 | I1 | Local harness trial on the decision set. A different runtime. |
| eval-harness (pfy) | I1 | Structural ladder we already run. |

Pi-Harness (I0) and repository-harness (I0) are the same shape. Beats what we have: no.

## Gates

Value (3 of 4 for I3): gap fill no (the pattern note and the ingest target already exist, and gap B stays open). Operator leverage no (Docker, mise, and a hosted key before any day of glue). Evidence no (this lane read docs only). Blast radius no (a live process can edit its own tree and call a hosted model). Score 0 of 4. The MIT license is fine for a read.

Modularity (all 4 for I2): the README, RSI.md, and SELF-CONTROL.md were enough, so a product copy was not required. The unit is a Rust workspace plus TypeScript, a website, and adapters. The cache clone is isolatable, and deleting it leaves the pin. 2 of 4. Potential is low. The worktree is 8162536 bytes, under 50 MB, and that does not open I2. No `self_pipeline`. Uses and features name no CI, test, or review role. No gate wiring. No new TOOLS.md row.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| setup.sh | Installs toolchains and asks for a hosted key. Writes a real home. | Do not run it. This lane set HOME under `~/.cache/pfy/tools/exo-exoharness`. |
| Unattended RSI | The agent edits `/workspace/exo` and rebuilds. | Do not start it. `default_harness` stays grok. Delete the cache clone. The pin stays. |
| Tip drift | A reader treats `d7fb6d2` as the judged tree. This lane read `372602d1`. | Stay on the pin. A newer tree is a new ticket. |
| Shared status | `sources/x-posts.md` still says Cataloged 2026-07-31. | The card, this report, and VERDICT are the 2026-11-07 status. |
| Skill index race | Two conversations drop one install. Upstream documents no compare-and-swap. | Do not run two copies. This lane started none. |
| ExoChat | Canonical template talks to exoharness.ai. | Do not start the canonical template. |

## Next gate

Stay I1 reference. Re-open only if a later ticket grills a lab copy under an operator GO, with Docker and no hosted key, and leaves `default_harness` on grok. Not a Feature GO.

## Pipeline questions

This lane does not put Exo on a pipeline. The scheduler started the read. It writes this directory and `data/stages/exo-exoharness.json`. No model and no account.

1. Trigger, if adopted later: a person runs the upstream setup one-liner, then `./exo.sh`. `./pfy start exo` only execs `exo.sh` when that file is already present. It does not run the installer.
2. It would read its repo mount, a Docker sandbox, and a hosted key, and write `.exo` state plus rebuilds of itself. This lane only read git docs.
3. Next in pfy: nothing. `default_harness` stays grok. The lane driver then runs the quick sanity check.
4. A human re-enters before any install, any API key, any Docker start, or any I2 claim. `tmp/STOP` stops this lane.
5. One worktree per slug keeps this card private. Two live Exo processes on one `.exo` tree can drop a skill-index write. This lane started none.
