# Multica evq1107

STAY I1 reference: the cloud board plus Postgres is a second product, and gap B is still the pfy build timeout.

## What it is

Multica is a workspace of issues where the assignee is a person or an agent. Pin `2a48ffa2aa734a4a362c2c52a786cd98a20bcef6` (2026-07-12 15:51:34 +0800, `fix(runtimes): simplify local machine list row (#5298)`). `package.json` version is 0.2.0. The README stack is Next.js 16, a Go server (Chi, sqlc, websocket; `server/go.mod` says `go 1.26.1`), PostgreSQL 17 with pgvector, and a local daemon. The tree also has Electron and an iOS app. `multica setup` logs in to Multica Cloud and starts the daemon. Self-host is Docker (`pgvector/pgvector:pg17`, GHCR `multica-backend` and `multica-web` at tag `latest`, frontend port 3000, backend port 8080). The dev compose file publishes Postgres on 127.0.0.1:5432. The daemon detects Claude Code, Codex, CodeBuddy, GitHub Copilot CLI, OpenCode, OpenClaw, Hermes, Pi, Cursor Agent, Kimi, Kiro CLI, Antigravity, Qoder CLI, and Trae CLI. Grok is not in that list. A squad assigns work to a leader agent. An autopilot opens an issue on a cron, a webhook, or a manual run. A skill is files dropped into the work directory. `docs/product-overview.md` is dated 2026-04-21 and still names Gemini, which this README list does not. This lane ran no install script, brew, make, Docker, or daemon.

## License

`LICENSE` is Apache-2.0 plus extra conditions (copyright 2025 Multica, Inc.). Hosting it, or embedding it in a product sold to others, needs a written commercial license. Internal use is allowed. The frontend logo and copyright must stay. A contributor clause lets the producer tighten the terms. The entry line "MIT/modified Apache" is wrong. Cite and summarize. Copy no source.

## Pin and command

| Item | Value |
| --- | --- |
| Pin | `2a48ffa2aa734a4a362c2c52a786cd98a20bcef6` (entry short pin `2a48ffa2aa73`) |
| Other tip | `main` `57fa7580469a9b3dae5ebe99629107b7dd6438e7`, 2026-11-08 10:02:30 +0800, subject only. Not read. |
| Fetch | `git clone --filter=blob:none` 3.43 s, then checkout 2.46 s. Not `--depth 1`. No upstream script. |
| Tree | 3254 files. Worktree 40033438 bytes. `.git` 50485153 bytes. Combined 90518591 bytes. |
| Cache | `~/.cache/pfy/tools/multica/src`. Not committed. |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` sat under `~/.cache/pfy/tools/multica`. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`. Entry 012 says `data/tools.json` has a Multica object. It does not. This lane does not edit `TOOLS.md` or `data/tools.json`.

## Ideas, and the pfy file each would touch

1. One issue, assignee a person or an agent. `docs/TODO.md` and `docs/ops/loop-engineering.md` already assign work. A board does not move `./pfy build`.
2. Skill files in the work directory for one run. `bootstrap/grok-cli/skills/` plus the install check in `docs/ops/skill-scan.md`. No skill database.
3. A daemon that detects CLIs and claims work. `docs/ops/worker-monitor.md` and `docs/ops/local-cloud-split.md`. Grok stays the monitor (`docs/adr/0002-grok-cli-primary-interface.md`).
4. Resume the last work directory for the same agent and issue. Traces in `AGENTS.md` and `bootstrap/grok-cli/skills/hermes-feedback/SKILL.md`.
5. A squad leader routes members. `docs/ops/gstack-role-recipes.md`. The product surface stays onboard, stage, and ship (`docs/ops/product-operator-surface.md`).

## Catalog comparison

Gap B in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is the unproven `./pfy build` path. No entry from 137 to 167 closes it. Entry 012 does not close it either. This lane builds no pipeline step. Same job: a board or roster that hands work to coding agents. Searched `data/stages/*.json` uses, features, and tags.

| Tool | Stage | How Multica compares |
| --- | --- | --- |
| kanbots | I1 | Kanban for coding CLIs in worktrees. The probe left the build timeout. |
| Kanzo | I0 | Local SQLite kanban. AGPL. Reference only. |
| Squadra | I1 | Manual seats and an ack before start. Timeout unchanged. |
| Auto-Company | I1 | Persona patterns. The company daemon stays off. |
| gstack | I1 | Role recipes in docs. Do not clone the repo. |
| Hermes Teammates | I0 | Fixed roster inside Hermes. Blocked on Hermes wiring. |
| Festival | I1 | Filesystem next-task. Timeout unchanged. |
| Brigade | I0 | Exclusive claim on a file ledger. Not a product board. |
| Emdash | I0 | Desktop, one worktree per task. |
| agent-cage (PNNL) | I3 | Isolation lab. Multica does not replace it. |

## Gates

Value, 3 of 4 for I3: gap fill no, operator leverage no (cloud login or Docker, Postgres, Go 1.26, pnpm 10.28.2, and Grok is not a detected CLI), evidence no (nothing started, and GHCR `latest` is not this pin), blast radius no (modified Apache, a host daemon, default compose credentials). Score 0 of 4.

Modularity, all 4: the README, LICENSE, product overview, and compose file were enough. The unit is a monorepo (web, desktop, mobile, Go server, CLI, daemon). The cache clone is isolatable, and deleting it leaves the pin. 2 of 4. The worktree is under 50 MB. With `.git` it is over 50 MB. Potential is low, so I2 stays closed. No `self_pipeline`. No gate wiring.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Cloud setup | `multica setup` opens a browser login and starts a daemon | Do not run setup. This lane ran nothing. |
| Install script | The curl target is `main`, not this pin | Keep the card pin. Do not run the script. |
| License | Hosting or embedding the app for others needs a commercial license, and terms can tighten | Cite only. Copy no source. |
| Unpinned images | GHCR tags default to `latest`, not commit `2a48ffa2` | Do not pull. Do not run compose. |
| Stale pin | `main` is at `#10097`. This report is `#5298` only | A later read names a new pin. |
| Second product | A board replaces onboard, stage, and ship | Stay on `docs/ops/product-operator-surface.md`. |

## Next gate

Stay I1 reference. Re-open only for a pattern note on person-or-agent issues, and that ticket still leaves the cloud login, the daemon, Postgres, and Docker out. No install. No Feature GO. Gap B stays the pfy build timeout.

## Pipeline questions

This lane writes the card, the Entry 012 Status line in `sources/x-posts.md`, and this directory. No model and no account.

1. Trigger, if a later ticket adopted it: a person runs `multica setup` or `multica setup self-host`. The evq scheduler is not that trigger.
2. It would read Multica Cloud or local Postgres and write issues, comments, a daemon token, and a work directory. This lane called no model and used no account.
3. Next the daemon would exec a detected CLI. Grok is not in that list. Nothing here starts that.
4. A human re-enters before any login, image pull, install script, or gate ticket. `tmp/STOP` in this worktree stops the lane.
5. One worktree and branch (`bot/evq-multica-1107`) owns this card. Two servers on ports 8080 and 3000 would collide. This lane started none.
