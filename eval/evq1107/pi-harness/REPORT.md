# Pi-Harness evq1107

Verdict: STAY I0 reference. AGPL-3.0-only desktop control plane around Pi Coding Agent. This lane did not install it or copy code. It does not fill gap H1.

## What it is

Pi-Harness (wangmiaozero) is an Electron workspace. Pi (earendil-works/pi) runs the agent loop, sessions, context, and compaction. Pi-Harness adds Runs, Trace, Replay, Run Compare, Evaluation, Policy, Budget, Checkpoints, Recovery, and Agent Teams (task DAG, review gates, worktrees). Linux is an x64 AppImage validated upstream on Ubuntu 24.04. A source build wants Node `>=24.22.1 <25`. This host is Node v22.23.0. Changelog 2.3.15 documents keyless Ollama on the same computer. Pi has no catalog entry and no TOOLS.md row.

## Pin and license

`LICENSE` and `package.json` say `AGPL-3.0-only`. The clone stays in `~/.cache/pfy/tools/pi-harness/src`. None of it is committed.

| Item | Value |
| --- | --- |
| Pin | `5b6ec2318d6741e444bfe8a640432be052e509fc` |
| Tag | `v2.3.23` (`37ae52dfc201253000959c9c8bb36ce645fa56e4`) |
| Commit time | 2026-11-08 09:22:17 +0800 |
| package.json | 2.3.23 |
| Entry 170 | said latest release v2.3.20 (changelog 2026-11-04). That SHA is the later v2.3.23 tag. |
| Fetch | `git init`, `git fetch --depth 1 origin 5b6ec2318d6741e444bfe8a640432be052e509fc`, checkout, and a directory listing. Wall time 35s. |
| Bytes | 1185980761 total, worktree 600309701, `.git` 585671060 |
| Ran | no upstream script, no installer, no package install |

## Ideas, and the pfy file each would touch

| Idea | pfy file | What we already have |
| --- | --- | --- |
| Resume, fork, or retry from a recorded run | `docs/ops/loop-engineering.md` | Eight exits, plus `eval/evq1107/<slug>/VERDICT` |
| Compare two settled runs | `docs/ops/skill-up-eval.md` | skill-up I3, both arms 5/5, delta 0 |
| A score that cannot change policy or the verdict | `docs/ops/loop-engineering.md` | Suite smokes over self-score. Their plugin doc says the same. |
| One worktree per agent | `docs/ops/PREGATE.md` | One evq worktree per slug, and pregate's own worktree |
| Budget and a checkpoint before resume | `docs/ops/loop-engineering.md` | Budget cap. `docs/ops/cage-session-resumption-design.md` |
| Trace export that drops prompts and secrets | `scripts/pfy_build_cloud.py` | Cloud redact. neatroots reads saved traces. No export taken. |

## Catalog comparison

H1 in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is a repeatable with/without score (entries 136 and 146). Their evaluator is a desktop panel on a settled Pi run. Upstream `docs/plugins/architecture.md` says it cannot alter the run, built-in evaluation, policy, or the review verdict.

Same job, already covered: skill-up I3 (tag `#eval`, the H1 score; this app runs no case set), harness2 I1 (gain 0; this read does not re-score the 48 cases), eval-harness (pfy) I1 (`make eval-structural`). Trace and replay: neatroots I2 (no export taken), agentplay I0, tracekit I0. Stops and budgets: Rulora I1, Finn loop / 8 exits I1. Teams and worktrees: kanbots I1 (tags `#worktree` `#multi-agent`; the dispatcher stays the evq scheduler), Emdash I0, Foremerge I1, atomic-task-graph I2, Hermes Teammates I0. Isolation and policy: agent-cage I3, write-guard-mcp I3. Memory: opencode-mem I1 (a Pi context pane does not fill that slot).

## Gates

Value (3 of 4 for I3): gap fill no. Operator leverage no (no install; the AppImage wants a display; source Node is 24 and this host is 22). Evidence no (this lane did not run it; entry 170 records a commit-metadata smoke that exits 2). Blast radius no (AGPL-3.0-only, 600309701 byte worktree, Electron app that bundles Pi and Node). Score 0 of 4.

Modularity for I2, all 4 required: isolatable and reversible pass (the cache copy is not the product runtime, and deleting it leaves the pin). Local code was not required, and the surface is an Electron app rather than one CLI, so 2 of 4. 600309701 bytes also exceeds the 50 MB I2 limit.

`features` includes `review gates`, so an I3 card would need `self_pipeline`. This lane sets no such field and wires no gate. No TOOLS.md row. No `data/tools.json` row.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| AGPL copy | Upstream code lands in this repo | Cache only. Cite, do not copy. |
| Pin drift | Entry said v2.3.20; the SHA is tag v2.3.23 | Pin the SHA. Do not follow `main`. |
| Headless host | AppImage has no display | Do not install. A desktop trial needs a new ticket. |
| H1 false pass | Run Compare is treated as a with/without score | H1 stays skill-up. This verdict stays I0. |
| Plugin trust | Approved plugin Node is not a sandbox (their security doc) | Do not enable plugins here. |

## Next gate

Stay I0 reference. Re-open only if a later ticket asks for an internal unmodified desktop trial after Pi has a catalog entry. Not a Feature GO.

## Pipeline questions

This lane does not put the tool on a pipeline. The scheduler started the lane. It writes the card, the entry Status line, and this directory.

1. Trigger, if adopted later: a person opens the desktop app. Not this scheduler.
2. It would read Pi sessions and write run state inside the app. This lane called no model and used no account.
3. Next: nothing. A supplementary evaluator cannot change policy or a verdict.
4. A human re-enters before any install, any plugin enable, or any AGPL exception.
5. One worktree per slug already keeps lanes off the same card. Do not start two desktop trials on one Pi home.
