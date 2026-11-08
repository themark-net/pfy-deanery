# Muxin evq1107

STAY I0 reference: Apache-2.0 fleet app is off the pfy build path, and a live run would use host ssh keys and the gh login

## What it is

Muxin (Lumary Labs LLC) is a GPUI desktop app, a headless CLI, and an MCP server for Linux, Mac, and Windows machines. It uses the host `ssh` client, then its own agent. The same jobs cover health, agent sessions, files, GitHub runners, services, processes, VMs, and DigitalOcean hosts. `--demo` serves simulated machines. `MUXIN_HOME` relocates `config.toml` (default `~/.config/muxin`). `Cargo.toml` is version 0.6.0, edition 2024, license Apache-2.0. `LICENSE` is the Apache-2.0 grant. `NOTICE` names Lumary Labs LLC, 2026.

## Pin

| Item | Value |
| --- | --- |
| Pin | `d45f3e480e6523febe81ed51061261b92714b3c9` |
| Tag | `v0.6.0` (annotated `af3037aff3ffadf2f45c43c50c5d51db6cec02c6`) |
| Commit | 2026-10-20 14:47:48 -0500, `Muxin 0.6.0` |
| Fetch | 1 s. `git init`, `git fetch --depth 1 origin d45f3e480e6523febe81ed51061261b92714b3c9`, detach checkout. No script, no binary, no `install.sh`. |
| Bytes | total 19702186, worktree 12328970, `.git` 7373216 |
| Tools | `src/mcp.rs` `tools()`: 89 names. All set both hints. 40 have `readOnlyHint` true. 17 have `destructiveHint` true. |

Cache: `~/.cache/pfy/tools/muxin/src`, not committed. `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `TMPDIR`, and `npm_config_cache` were under `~/.cache/pfy/tools/muxin`. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`.

Entry 145 records a demo smoke PASS (9 simulated machines, binary sha256 `b51e6fda3911d181f6bd188bd375d846eeaface64a060888dcfe14201fd3264d`). That file was not opened here.

## Ideas, and the pfy file each would touch

1. Every MCP tool sets `readOnlyHint` and `destructiveHint` before a call. Touch `harness/write-guard-mcp/README.md`. destructive_command_guard (I2) classifies a shell string after the model writes it.
2. `MUXIN_HOME` and `--demo` keep practice state off the real home and off real hosts. Touch `examples/x-intake-local/smoke_143_145.py`.
3. `status` returns an `attention` list (unreachable, stopped runner, low disk). Touch `docs/automation/x-intake-2026-10-22-handoff.md`, which already parks the Sysadmin trial.
4. Failures use `not_found`, `invalid`, and `unreachable`. Touch `docs/ops/loop-engineering.md`. The eight exits already name the stop.

## Catalog comparison

`docs/eval/TOOLSET-RANKING.md` (2026-11-07) holds entry 145 for comparison. Gap B is the 3 hour `./pfy build` timeout. No other card's uses, features, or tags say fleet. Emdash (I0) is the ssh hit: a coding-agent desktop with remote worktrees. This lane builds no pipeline step.

| Tool | Stage | How Muxin compares |
| --- | --- | --- |
| SysKnife | I0 | Typed approval-gated admin on one Linux host (pin `1b3aab98`, no cargo on nimo). Muxin is many hosts over ssh. |
| destructive_command_guard | I2 | Denies one destructive shell command. Muxin marks 17 fleet tools `destructiveHint` and can still run them. |
| write-guard-mcp | I3 | Write mediation above the cage mount. |
| agent-cage (PNNL) | I3 | One isolated lab. |
| Sandlock | I2 | Confines one install command. |
| smolvm | I1 | One microVM. Sandlock is the lighter confine. |
| Bumblebee | I2 | Lockfile and MCP config scan. |
| Brigade | I0 | Task ledger. `fleet_hub` is a non-goal. |
| AgenC | I0 | Watch one daemon coding agent. |
| Foremerge, Emdash, HAR | I1, I0, I0 | Worktrees. Emdash also runs a provider CLI on an SSH host. |

A live Muxin reads host ssh keys. `token` (`src/github/mod.rs:351`) takes `env_token` (`:952`) first (`MUXEN_GITHUB_TOKEN`, `GITHUB_TOKEN`, `GH_TOKEN` on api.github.com). With no env token and an empty account machine it runs `gh auth token` via `gh_program` (`:966`, `:980`). A named account machine uses the fetcher. The 17 destructive tools include `run_on_machines`, `vm_destroy`, `cloud_destroy`, `process_signal`, and `remove_machine`. The build timeout stays where it is.

## Gates

Value (3 of 4 for I3): gap fill 0 (L, B, H1, H2, and W stay open). Operator leverage 0 (design, cage, eval, and the local bulk path stay as they are). Evidence 1 (entry 145 demo smoke PASS; this lane did not re-run it, and no real host was checked). Blast radius 0 (Apache-2.0 and 12328970 worktree bytes are small; an agent install takes host ssh, the gh login, and destructive fleet tools). Score 1 of 4.

Modularity (all 4 for a local copy): a different-host trial needs the binary (local code needed). The cache copy deletes cleanly and the pin remains (isolatable, reversible). Bounded surface fails: app, CLI, MCP, remote agent, and `share-server`. 3 of 4. 12328970 bytes is under the 50 MB I2 cap. Potential is low, so I2 stays closed.

`uses` and `features` are fleet words. The role-token check sees none of them. No `self_pipeline` field. No TOOLS.md row. No `data/tools.json` row.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Destructive tool | An agent calls `run_on_machines`, `vm_destroy`, or `cloud_destroy` on a real host | Stay I0. Expose no tool. |
| Host ssh keys | `config.toml` points at Mark's keys | No `add-machine` in this lane. |
| gh login | `gh auth token` reads the host login, even off `PATH` | No live `muxin`. A later trial needs a user with no gh login. |
| Real-home state | Default dir is `~/.config/muxin` | This clone used a cache `HOME`. Leave the binary unstarted. |
| Pin drift | `main` moves past 0.6.0 | Keep SHA `d45f3e480e6523febe81ed51061261b92714b3c9`. |

## Next gate

Stay I0 reference. Re-open only for a demo-only `status` read, as a user with no gh login, with no destructive tool exposed. No `install.sh`, no real host, no SSH key, no cloud account, no gate. Gap B stays the pfy build timeout. Not a Feature GO.

## Pipeline questions

1. Trigger, if a later ticket adopts it: a person asks for fleet status. This read started from the scheduler.
2. A live copy would read ssh hosts and GitHub and write under `MUXIN_HOME`. This lane called no model and used no account.
3. Next: the lane driver sanity check, then the next slug. pfy build stays on its own path.
4. A human re-enters before any binary run, any real host, or any I1 row (`tmp/evq/muxin.parked`, or a PROMOTE that needs gate wiring).
5. One worktree (`bot/evq-muxin-1107`) owns `data/stages/muxin.json`. A second run stops when `muxin.dispatched` exists.
