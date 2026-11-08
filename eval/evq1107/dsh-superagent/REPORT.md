# dsh-superagent evq1107

STAY I0 reference: research prototype; runtime needs DSH, a dedicated GitHub account, and danger-full-access. This lane did not install, run, or copy upstream code.

## What it is

dsh-superagent (https://github.com/deepseek-ai/dsh-superagent-prototype, MIT, copyright 2026 DeepSeek Harness Team) is a research prototype, not an official DeepSeek product. Package `dsh-superagent` 0.1.0. `engines.node` is `^22.19.0 || >=24.0.0`. `engines.dsh` is `^0.2.1-alpha.2`. It is a DeepSeek Harness bundle for one GitHub repository. It listens to that account's notifications, and optionally Feishu. When an allowed person addresses it, the agent opens a Ticket with its own DSH Session and directory, and the reply goes back on the original thread. The panel listens on 127.0.0.1 port 3082 (`examples/profile.cordis.patch.yml`). Accept mode defaults to `observe`: a positive inferred assessment is stored as ignore marked "would accept", and nothing is accepted. Explicit requests are admitted in every mode. Presets `dsh-superagent-worker` and `dsh-superagent-router` use `danger-full-access` as the operator's OS user. Upstream says a worker can execute a program by path and read the operator's home. A GitHub App cannot be the agent, because the host reads the account's notifications. Install is `npm install -g @deepseek-ai/dsh@0.2.1-rc.3` plus a separate `superagent` profile that changes process-wide PATH. The README says this tree differs from the internal version and from the article *Exploring Super-agent Design*.

## Pin and commands
Cache `~/.cache/pfy/tools/dsh-superagent/src`, not committed. Pin `6337fc823ce20251c8de8085948165c81aaa701e` (2026-10-31 20:05:39 +0800). Work tree 216 files, 2601300 bytes. `.git` is 871550 bytes. No `node_modules`. No script ran. No model lock. Clone duration was not recorded.

```bash
CACHE=~/.cache/pfy/tools/dsh-superagent
mkdir -p "$CACHE"/{home,xdg/config,xdg/cache,tmp}
export HOME="$CACHE/home" XDG_CONFIG_HOME="$CACHE/xdg/config" XDG_CACHE_HOME="$CACHE/xdg/cache" TMPDIR="$CACHE/tmp" GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
git clone --filter=blob:none --no-checkout https://github.com/deepseek-ai/dsh-superagent-prototype.git "$CACHE/src"
git -C "$CACHE/src" fetch --depth 1 origin 6337fc823ce20251c8de8085948165c81aaa701e && git -C "$CACHE/src" checkout --detach FETCH_HEAD
```
## Ideas, and the pfy file each would touch

1. Unasked work starts in `observe` and needs a team-written rule. Touch `docs/ops/loop-engineering.md`. The proactive loop type there is already "Later; not default". Eight exits and `docs/adr/0008-one-shot-workflow.md` already stop unattended work without a DoD.
2. A Subscription delivers context and grants no Mandate. A bot cannot make an explicit request. Touch `data/stages/sponsio.json` (pre-call check, I2) and `data/stages/write-guard-mcp.json`. Cage isolation is `data/stages/agent-cage-pnnl.json`.
3. The panel lists only what needs a person. Touch `docs/ops/product-operator-surface.md` (onboard, stage, ship) and `bootstrap/grok-cli/skills/ui-is-the-app-design-in-loop/SKILL.md`.
4. One Ticket, one Session, one directory. The Mandate records the Policy version. Touch `data/stages/har.json` and `data/stages/brigade.json`. Neither closes the 3 h `./pfy build` timeout.
5. SETUP.md asks one question per message. Do not import that interview. `docs/ops/human-decision-inventory.md` batches operator input and escalates only material decisions.

## Catalog comparison

The job is authorization and attention for a proactive one-repo agent. `docs/eval/TOOLSET-RANKING.md` (2026-11-07) puts entry 154 on the hold list and says no entry 137 to 167 closes gap B. Searched `data/stages/*.json` uses, features, and tags.

| Tool | Stage | How dsh-superagent compares |
| --- | --- | --- |
| odai | I0 | Same family (entry 166). Ask only on a material boundary. No GitHub listener. |
| Finn Loop / 8-exits | I1 | Stop conditions already in the orchestration toolset. |
| Auto-Company | I1 | Company-daemon patterns. Not a one-repo Ticket host. |
| AgenC | I0 | Watch a daemon coding agent. Do not run it as the operator. |
| kanbots | I1 | Kanban into worktrees. 2026-11-07 left the 3 h timeout unchanged. |
| Squadra | I1 | Acknowledge before start. The timeout stays put. |
| Festival | I1 | Plan and next-task. Timeout unchanged. Advisory. |
| Overtime | I0 | Wake and budget for a folder that outlives a process. Timeout unchanged. |
| Reasonix | I0 | DeepSeek-native coding agent. Comparison only. Not this bundle. |
| HAR | I0 | Per-slot worktree and a tree-hash receipt. Gap B is still the timeout. |
| Brigade | I0 | Exclusive claim on a file ledger. Not an allow-list. |
| Chiasmus | I1 | Call-graph impact for a per-file review. Not a Ticket host. |
| Elephant-Goldfish | I1 | Fresh-eyes spec review before Build. Gap B is indirect. |
| Sponsio | I2 | Pre-call ordering. No GitHub account. |
| agent-cage (PNNL) | I3 | Isolated lab. `danger-full-access` as the operator user is the other direction. |
| write-guard-mcp | I3 | Write mediation above the cage mount. |

Gap B stays `./pfy build` (3 h timeout, recheck parked after two pregate FAILs). This bundle does not move it.

## Gates
Value, 3 of 4 for I3: gap fill no, operator leverage no (global DSH, a model provider, a new GitHub account), evidence no (entry smoke `examples/x-intake-local/smoke_154.py` exits 2 until a staged clone with dependencies; this lane did not re-run it), blast radius no (`danger-full-access`, home reads, process-wide PATH). Score 0 of 4. The MIT license is fine to read.

Modularity, all 4 for a local copy: local code was not needed (the numbered docs were enough), the surface is one package plus docs 000-008, the read-only cache is isolatable, and deleting it leaves the pin. 3 of 4. 2601300 bytes is under the 50 MB I2 limit. Potential is low, not ambiguous, so I2 does not apply. No `self_pipeline`. No TOOLS.md row. No `data/tools.json` row. No gate wiring.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Run as Mark | Presets are `danger-full-access` and can read the home directory | Do not install DSH and do not select those presets. This lane ran nothing. |
| Account sprawl | Setup wants a new GitHub user and a model provider | Out of scope. Design reference only. |
| Profile clobber | `dsh superagent --from-default-profile` replaces `~/.dsh/profiles/superagent` | No `dsh` command. The cache stays under `~/.cache/pfy/tools/dsh-superagent/`. |
| Prototype drift | The README says this tree differs from the internal version | The card pins `6337fc823ce20251c8de8085948165c81aaa701e`. Re-read before any later note. |
| False gap-B pass | A Ticket model is counted as the build-timeout fix | Gap B stays the pfy build lane. This verdict stays I0. |

## Next gate

Stay I0 reference. The file mapping is this report. Re-open only if Mark asks for an ADR that cites upstream `docs/000-philosophy.md` and `docs/002-authorization.md` at this pin. No DSH install, no agent GitHub account, no Feishu bot, no runtime trial. Not a Feature GO.

## Pipeline questions

This lane writes the card, the entry Status line, and this directory. It does not add a pipeline step.

1. Trigger, if a later ticket adopted it: a GitHub notification or Feishu message that addresses the agent account. The evq scheduler is not that trigger.
2. It would read that account's notifications and write Tickets, Sessions, directories, comments, and pull requests. This lane called no model and used no account.
3. Next would be a person on the panel for a person stage, or a person merging. Auto-merge defaults off.
4. A human re-enters before any install, any GitHub account, any move from `observe` to `auto`, and any `danger-full-access` preset.
5. One worktree per slug already stops two lanes editing this card. Two bundles on one `superagent` profile would collide. This lane started none.
