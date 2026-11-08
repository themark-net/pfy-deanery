# teaql-agent-kit evq1107

STAY I0 reference. Root MIT, child package Apache-2.0. Context lifetimes and a default-deny file policy for other hosts. This lane did not install it or run its scripts. It does not move gap B.

## What it is

TeaQL Agent Kit (teaql/teaql-agent-kit) is a model-first TeaQL app skill plus `@teaql/agent-context-kit` 0.5.0. The skill path is model, evaluate, generate, implement, verify, with progressive Assist for seven language families. The context kit keeps named Markdown blocks until a trusted discard, consumes ephemeral text once, and checks write roots, read-only paths, and marker-aware reads. The activation matrix says Codex, Claude Code, and Cursor get protocol text only. Grok is not listed. The workspace package is private `0.0.0`.

## Pin and license

| Item | Value |
| --- | --- |
| Pin | `92c79101f725655d5356078938742bd633f341a2` |
| Commit | 2026-11-06 08:37:10 +0800, `docs: add Octop icon to README grids`. `ls-remote HEAD` on 2026-11-07 was this SHA. |
| Root license | MIT (`LICENSE`, root `package.json`) |
| Child license | Apache-2.0 (`packages/agent-context-kit/LICENSE` and its `package.json`) |
| Engines | Node `>=22.19.0` on the child package. Not executed. |
| Fetch | `git init`, `git fetch --depth 1 --filter=blob:none origin <pin>`, detach checkout. `date +%s` delta 0. |
| Bytes | worktree 983366, `.git` 432354, cache src 1415720. The entry's ~40 MB note is a full git estimate. This row is the filtered pin checkout. |
| Cache | `~/.cache/pfy/tools/teaql-agent-kit/src`. Not committed. No upstream script ran. HOME, XDG_CONFIG_HOME, XDG_CACHE_HOME, and TMPDIR were under that cache. Git config files were `/dev/null`. |

## Ideas, and the pfy file each would touch

| Idea | pfy file | Already covered by |
| --- | --- | --- |
| On native Pi, a successful edit drops the last green check. The rerun stops at 3 rounds. OpenCode does not get that hook. | `docs/ops/loop-engineering.md` | Eight exits, written before the run. Review quality is `docs/build-dropins/mvp-review-quality-1031.md`. |
| Empty write roots deny every write. Generated paths stay read-only. | `harness/write-guard-mcp/src/write_guard/server.py` | Write mediation above the cage, with a content hash of the body. |
| Missing numbers stay unreported. Do not invent savings. | `docs/ops/skill-verification.md` | Lane reports already require pins, commands, and numbers. |
| A phase ends only on an explicit trusted discard. | `bootstrap/grok-cli/skills/agent-loops/SKILL.md` | Exit cards. The kit does not infer "phase complete". |
| Real HOME writes are a separate watch from path policy. | `examples/x-intake-local/smoke_122_124.py` | Content-hash tree signature. Their file policy is not that watch. |

## Catalog comparison

Same job: what context stays loaded, which files an agent may change, and what counts as verified. Searched `data/stages/*.json` uses, features, and tags, plus `docs/eval/TOOLSET-RANKING.md` (2026-11-07). Entry 167 is on the hold-or-comparison list. That section says no entry from 137 to 167 closes gap B. This lane builds no pipeline, CI, or gate.

| Tool | Stage | What it covers | How this kit compares |
| --- | --- | --- | --- |
| write-guard-mcp | I3 | Write mediation above the cage. | Their policy is an in-process path check. Their file-policy doc says it is not an OS sandbox. |
| agent-cage (PNNL) | I3 | Isolated lab and filesystem MCP. | The cage is the boundary. A Markdown adapter does not replace it. |
| destructive-command-guard | I2 | Denies destructive shell commands. | Protected Pi and OpenCode modes turn shell off. The guard already classifies the command. |
| Sponsio | I2 | Pre-call check and an ordering rule. | Different check. Their policy is path roots. Sponsio blocked 0 of 2 in-repo skill writes. |
| HAR | I0 | Verify receipt keyed by the worktree tree. | Closest to "the tree changed, so the old green is stale". That probe was 0.837s against a 0.222s git worktree baseline. |
| odai | I0 | Evidence-before-done skill. The 2026-11-07 read stayed I0. | Same honesty rule. Their work-complete sheet is TeaQL-specific. |
| Open Steps | I0 | Stop nag on a git fingerprint change. | A stop hook. The second stop exits 0. |
| project-process bootstrap | I3 | DESIGN, ADR, TODO, AGENTS.md. | "Point the agent at instructions" is already the router. |
| Finn loop / 8 exits | I1 | Exit cards before a long run. | A bounded rerun belongs in those exits. This kit does not add one. |

Same conclusion, shorter: Festival I1 (checklist, timeout unchanged), Squadra I1 (refuses an always-passing check), repository-harness I0 (map beside AGENTS.md), Tracekit I0 (0 of 6 skill loads blocked), harness-score I0 (grades files, does not enforce lifetimes). Beats what we have: no.

## Gates

Value (3 of 4 for I3): gap fill no (gap B is the pfy build timeout and two pregate FAILs). Operator leverage no (no Grok adapter; install into agent homes is out of scope). Evidence no (docs read only; the entry records a commit-metadata smoke that exits 2). Blast radius yes for a cache pin (MIT plus Apache-2.0, 983366 byte worktree, no weights). Score 1 of 4.

Modularity (all 4 for I2): local code was not required. One package is publishable, and the repo also ships the TeaQL skill plus many host adapters, so the surface is not one CLI. Isolatable and reversible pass. 2 of 4. The worktree is under 50 MB. Potential is low, not ambiguous, so the I2 shelf does not apply. No `self_pipeline` field. Uses and features name no CI, test, or review role. No TOOLS.md row. No `data/tools.json` row. No gate wiring.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Skill install writes an agent home | `npx skills add` or `pi install` touches a real agent home | Do not install. Cache only. |
| Logos read as enforcement | A Cursor or Grok session is treated as marker-aware | The matrix lists Cursor as guidance only. Grok is absent. |
| App generation scope | `build-teaql-app` starts a TeaQL app here | Reference only. No generation. |
| License mix | Child Apache-2.0 text is copied under the root MIT line | Cite both. Copy no source. |
| Pin drift | `main` moves past this SHA | Keep `92c79101f725655d5356078938742bd633f341a2`. |

## Next gate

Stay I0 reference. Re-open only if a later ticket copies one rule into write-guard or the loop exits, and that ticket grills the copy first. Not a Feature GO.

## Pipeline questions

This lane does not put the kit on a pipeline. The scheduler started the read. It writes this directory, the card, and the entry Status line. No model and no account.

1. Trigger, if adopted later: a person installs one host adapter. Not this scheduler.
2. It would read Markdown markers and allow or deny file tools inside that host. This lane only read the checkout.
3. Next: nothing in `./pfy`.
4. A human re-enters before any install, any TeaQL generation, or any I1 row in TOOLS.md.
5. One worktree per slug keeps this card private. A second read must not edit the same card.
