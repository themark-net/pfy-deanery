# SysKnife evq1107

STAY I0 reference: no cargo on nimo, and H2 stays with SkillSpector. This lane did not install, build, or run upstream code.

## What it is

SysKnife (https://github.com/lacs-project/sysknife, MIT, copyright 2026 Vladimir Rotariu) is a Linux sysadmin MCP server and CLI. The model names a typed action. A privileged daemon builds the command, requires a one-time approval receipt from a terminal, and appends an Ed25519 audit row. The README line is "Plan. Approve. Audit." Crate `sysknife-cli` is 0.30.0 and the binary is `sysknife`. `--dry-run` prints a plan or an approval preview and does not execute or issue a receipt. An intent dry-run still calls the planner. The README says some actions still run through a shell fragment that SysKnife builds. The docs claim 190 or more actions. This lane did not count them. `npx sysknife-setup` stays out.

## Pin and commands

Cache `~/.cache/pfy/tools/sysknife/src`, not committed. Tag `v0.30.0` peels to `1b3aab98b878128a267368cd47b51c921cd31219`. Clone and checkout took 2 s. Work tree 16736821 bytes, 1415 files. With `.git`, 29777154 bytes. `command -v cargo` and `command -v rustc` printed nothing. No script ran. No model lock.
```bash
CACHE=~/.cache/pfy/tools/sysknife
mkdir -p "$CACHE"/{home,xdg/config,xdg/cache,tmp}
export HOME="$CACHE/home" XDG_CONFIG_HOME="$CACHE/xdg/config" XDG_CACHE_HOME="$CACHE/xdg/cache" TMPDIR="$CACHE/tmp" GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
git clone --filter=blob:none --no-checkout https://github.com/lacs-project/sysknife.git "$CACHE/src"
git -C "$CACHE/src" fetch --depth 1 origin 1b3aab98b878128a267368cd47b51c921cd31219 && git -C "$CACHE/src" checkout --detach FETCH_HEAD
```

## Ideas, and the pfy file each would touch

1. The host builds argv from a fixed action name. A note would sit beside enforce in `harness/write-guard-mcp/README.md`. The live check is destructive_command_guard (Entry 041, I2), which classifies the shell string the model already wrote.
2. A human mints the receipt on a channel the model does not sit on. Touch `docs/ops/human-decision-inventory.md`. The eight exits in `docs/ops/loop-engineering.md` already stop for a person.
3. Sign the authorization decision and leave later status unsigned. runx (I0) and tracekit (I0) already record that shape and stay out.
4. Leave the daemon, the sudoers helpers, the system service, and `npx sysknife-setup` unused.

## Catalog comparison

The job is gap H2 in `docs/eval/TOOLSET-RANKING.md` (2026-11-07): a check before a fetched skill is loaded. Entry 157 is on that page's hold list. The card's job is typed approval-gated Linux admin. Searched `data/stages/*.json` uses, features, and tags.

| Tool | Stage | How SysKnife compares |
| --- | --- | --- |
| SkillSpector | I3 | Static scan before a skill copy (`docs/ops/skill-scan.md`). |
| Sandlock | I2 | Confines one install command. A system daemon acts on the host. |
| destructive_command_guard | I2 | Denies destructive shell commands (probe 12/12). The typed catalogue is the other shape. Unrun here. |
| write-guard-mcp | I3 | Write mediation and an audit above the cage mount. |
| agent-cage (PNNL) | I3 | Isolated lab. A system daemon is the other direction. |
| Sponsio | I2 | Pre-call check. In-repo skill writes were 0/2. |
| Tracekit | I0 | Ed25519 bundle. Skill-load commands blocked 0/6. |
| runx | I0 | Sealed receipt. Install-gate refuses were 0/4. |
| smolvm | I1 | MicroVM confinement. Sandlock is the lighter install confine. |
| Bumblebee | I2 | Lockfile and MCP config scan. |
| Moira | I1 | JSON Schema on one directive. |
| cedr | I1 | Content pin of skill directories. |
| asm (agent-skill-manager) | I1 | Probe copied a planted skill (0/1 blocked). |
| Muxin | I0 | Sysadmin fleet MCP. Also off the MVP path. |
| CodeGuard, trailofbits-skills, Skills Manager | I0 | Rule text, checklists, and a home skill hub. |

H2 stays with SkillSpector and Sandlock. The typed-action split is a design note. This host cannot build it.

## Gates

Value, 3 of 4 for I3: gap fill no, operator leverage no, evidence no (entry smoke `examples/x-intake-local/smoke_157.py` exited 2 on 2026-11-02; this lane did not re-run it), blast radius no (privileged daemon and sudoers). Score 0 of 4.

Modularity, all 4 for a local copy: the README was enough to stay, the tree is a Rust workspace plus `packaging/`, the cache clone is isolatable, and deleting it leaves the pin. 2 of 4. 16736821 bytes is under the 50 MB I2 limit. Potential is low, so I2 does not apply. No `self_pipeline`. No TOOLS.md row. No `data/tools.json` row. No gate wiring.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Planner executes | `--yes` or `--dangerously-skip-approval` with `SYSKNIFE_I_ACCEPT_UNATTENDED_ROOT` | Do not set that variable and do not pass those flags. This lane ran nothing. |
| Setup writes the real home | `npx sysknife-setup` puts binaries in `~/.local/bin` and merges MCP config | No npx. The clone stays under `~/.cache/pfy/tools/sysknife/`. |
| Pin drift | `main` moves past 0.30.0 | The card pins `1b3aab98b878128a267368cd47b51c921cd31219`. |
| H2 false pass | A host admin daemon is counted as the skill install gate | H2 stays SkillSpector. This verdict stays I0. |
| Shell inside the daemon | The README says some actions still use a shell fragment SysKnife builds | Do not record "no shell" as a measured result. A later ticket would read the action specs from this pin. |

## Next gate

Stay I0 reference. Re-open only to build this pin from the cache and dry-run one read-only intent, with no `--yes`, no daemon, and no release download. Not a Feature GO.

## Pipeline questions

This lane writes the card, the entry Status line, and this directory. It does not add a pipeline step.

1. Trigger, if a later ticket adopted it: a person runs the CLI, or an MCP client calls `sysknife_plan`. The evq scheduler is not that trigger.
2. It would read host state and write a SQLite audit log. Mutating actions would change the host. This lane called no model and used no account.
3. Next would be a person running `sysknife approve`. The model does not mint the receipt.
4. A human re-enters before any install, any daemon, any `--yes`, and any high-risk step (the docs require typing the action name).
5. One worktree per slug already stops two lanes editing this card. Two daemons on one socket would collide. This lane started none.
