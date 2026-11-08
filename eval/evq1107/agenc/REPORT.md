# AgenC evq1107

STAY I0 reference: 0.19.32 is still a daemon coding agent, and no scored gap beats Grok plus cage.

## What it is

AgenC Core (tetsuo-ai/agenc-core) is a terminal coding agent. A local daemon owns sessions, permissions, provider calls, and command execution. The TUI, headless print, background agents, channel gateway, and phone remote are clients of that daemon. License is MIT (root LICENSE, package.json, README footer). One nested file, `runtime/scripts/hermetic-docker-seccomp.LICENSE`, is Apache-2.0. A fixture LICENSE under `runtime/tests` is MIT (DeepSeek, 2023). The README default provider is grok. Sign-in stays split: `agenc login` and `agenc grok-login` (X / xAI subscription, no API key). Node devEngines want `>=26.5.0 <27`. This host is Node v22.23.0. The 2026-07-12 trial in ADR-0010 rejected the TUI and the auth surface. ADR-0013 keeps the surface optional. `docs/ops/agenc-reeval-stance.md` says re-open only if a gap beats Grok plus cage. The README names no web console. Plugin marketplaces remain in `docs/agenc-account-model-access.md` and `docs/INDEX.md`. Account sign-in there is identity, marketplace, remote, and desktop sync. It does not supply models. Remote control and the channel gateway are the README add-ons. No `sources/entries` file (the ticket entry was `-`). Status is the card. The TOOLS.md row already says reference only. This lane left that file alone.

## Pin and command

| Item | Value |
| --- | --- |
| Pin | `126ee5b793a6aaa8edbbd9c0cbdbead5bcb938f1` on `main` |
| Commit | 2026-11-07 15:52:05 +0100, Recapture FND baselines for AgenC Core 0.19.32 |
| Packages | agenc-core 0.19.32, `@tetsuo-ai/agenc` 0.19.32, `@tetsuo-ai/runtime` 0.19.32, `@tetsuo-ai/agenc-sdk` 0.3.0 |
| Fetch | 9 s. In `~/.cache/pfy/tools/agenc/src`: `git init`, `git remote add origin https://github.com/tetsuo-ai/agenc-core.git`, `git fetch --depth 1 --filter=blob:none origin 126ee5b793a6aaa8edbbd9c0cbdbead5bcb938f1`, `git checkout --detach FETCH_HEAD`. HOME, XDG_CONFIG_HOME, XDG_CACHE_HOME, npm_config_cache, and TMPDIR were under that cache. GIT_CONFIG_GLOBAL and GIT_CONFIG_SYSTEM were `/dev/null`. |
| Bytes | src `du -sb` 117436549, `.git` 28222965, worktree `du -sb --exclude=.git` 89213584. 7499 tracked files. |
| Ran | no upstream script, no installer, no npm |

## Ideas, and the pfy file each would touch

| Idea | pfy file | What we already have |
| --- | --- | --- |
| Refuse a run whose safety record the reader cannot parse | `docs/ops/loop-engineering.md` | Eight exits in `bootstrap/grok-cli/skills/agent-loops`. |
| A failed compact warns and the session survives | `docs/ops/cage-session-resumption-design.md` | Resume is per repo. Leave their checkpoint schema in the cache. |
| M5 is one frozen spine: worktree, implement, verify, fresh-context check, evidence. That contract excludes a general DAG engine | `docs/ops/HANDOFF-pfy-local-build-mvp.md` | Gap B is the 3 h `./pfy build` timeout. ATG at I2 is the typed DAG. |
| Admission stays on when budget caps are off (concurrency, cancel, deadline, evidence) | `docs/ops/loop-engineering.md` | The budget cap is already one of the eight exits. |

Leave the daemon, the phone remote, the Ledger path, the channel gateway, and the curl-pipe installer alone.

## Catalog comparison

Same job: a daemon coding agent for build lanes and checks. Gap B in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is the unproven `./pfy build` path. No entry from 137 to 167 closes it. AgenC is older than that range and sits on the 2026-10-06 skip-or-hold list. Auto-Company (I1) already keeps the persona extract in operator docs, and the company daemon stays off the operator path. Continue.dev (I1) is an IDE client held as reference. The local worker is OpenCode through `./pfy build --local`.

| Card | Stage | How AgenC compares |
| --- | --- | --- |
| Grok CLI bootstrap | I3 | The operator. Its non-goal is replace with AgenC. |
| agent-cage (PNNL) | I3 | Isolation lab. ADR-0013: their sandbox does not replace the cage. |
| write-guard-mcp | I3 | The permission gate we run. |
| Aider | I1 | Headless git editor. Its probe left gap B open. |
| kanbots | I1 | Worktree lanes. 0 of 11 CLIs dispatched. Timeout unchanged. |
| Finn Loop / 8 exits | I1 | Stop card. It overlaps the fail-closed reader idea above. |
| MCO, Elephant-Goldfish, Chiasmus | I1 | Spec and diff checks. None is a host runtime. |
| Hermes feedback loops | I1 | Pattern port. That card keeps the skill and leaves the daemon uninstalled. |
| Overtime, imcodes, Emdash, Pi-Harness | I0 | Other daemons or desktops. Each stayed reference. |

## Gates

Value (3 of 4 for I3): gap fill no, operator leverage no, evidence yes only as the demoted `bootstrap/agenc/smoke.sh` path (this lane did not run it; host Node is 22 and upstream wants 26), blast radius no (onboard would take the operator seat; worktree 89213584 bytes). Score 1 of 4.

Modularity (all 4 for a local copy): the README and design index were enough, the unit is a 7499-file monorepo, the cache copy is isolatable, and deleting it leaves the pin. 2 of 4. Over the 50 MB I2 limit. Potential is low.

`uses`, `features`, and tags name no CI, test, or review role. No `self_pipeline` field. No gate wiring.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Daemon autostart | An install owns `AGENC_HOME` and a socket | This lane did not install. Leave it that way. |
| Dual login | `agenc login` is treated as the Grok subscription | Stay on Grok CLI. `agenc grok-login` is a separate command. |
| Node drift | `bootstrap/agenc/install.sh` still says Node >= 25. Upstream wants 26.x. Host is 22. | Leave that script unrun. |
| Pin drift | `main` moved the same day (0.19.32 on 2026-11-07) | Pin the SHA. Leave `main` unfollowed. |
| Size | The monorepo lands in git | Cache only. |

## Next gate

Stay I0 reference. Re-open only if a scored gap beats Grok plus cage. A Feature GO stays out.

## Pipeline questions

This lane does not put AgenC on a pipeline.

1. Trigger, if a later ticket adopted it: a person runs `agenc` and the launcher starts the daemon. The evq scheduler stays off that path.
2. It would read the workspace and write sessions under `AGENC_HOME`, plus provider calls. This lane called no model and used no account.
3. Next: a TUI, a print run, or a background agent. pfy stays on its own scheduler.
4. A human re-enters before any install, any daemon start, or any I3 claim. ADR-0010 already requires a new ADR before a primary revisit.
5. Upstream runs one daemon per `AGENC_HOME`. Here, one worktree per slug keeps this card private. A second trial on the same home stays out.
