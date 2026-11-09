### Entry 145: Muxin: one app and MCP server for a fleet of Linux, Mac and Windows machines and their agent sessions

- **URL**: https://github.com/LumaryLabsLLC/muxin (Apache-2.0, Rust). Release `v0.6.0` (2026-10-20); `Muxin-0.6.0-linux-x86_64.tar.gz` sha256 `0d12438c5dff60c1688e666fa688579e0ca8fc1a6fdc13fb7f0a25f6ffdce837` (matches the release SHA256SUMS.txt); the `muxin` binary in it sha256 `b51e6fda3911d181f6bd188bd375d846eeaface64a060888dcfe14201fd3264d`.
- **Date**: 2026-10-22 (daily X intake, window 2026-10-22T00:37Z to 2026-10-23T00:36Z)
- **Source / Poster**: @DanKornas, https://x.com/DanKornas/status/2113132994407907731 (repo link in the reply https://x.com/DanKornas/status/2113133171227210060)
- **Summary / Key Claims** (upstream README; their claims except where marked verified): a desktop app and CLI for managing Macs, Linux machines and Windows PCs together with AI agent work: machine health, sessions, files, GitHub runners, services, processes, VMs and cloud hosts in one place, over SSH. It ships an MCP server (`muxin mcp`) so an agent can query and act on the fleet, and a `--demo` mode with simulated machines.
- **Why it matters here**: the operator runs nimo, borg, maximum, plant and beelink (Proxmox), and Sysadmin checks them with ad hoc ssh commands. One MCP server that answers "what's running where, what needs attention" would give Sysadmin, DevBot and pfy-mentat's Hermes interface a single fleet view, and its tools are annotated read-only versus destructive, which maps onto our gate rules.
- **Fit on nimo**: Yes. A 0.6.0 x86_64 release binary, no GPU, no keys; the GUI needs X libraries (`libxkbcommon-x11`, `libxcb-xkb`) that a desktop host like nimo should already have. Config and state go to `~/.config/muxin` unless `MUXIN_HOME` is set. Unpack under `~/DEVELOP/pfy-mentat/tmp/muxin`; never its `install.sh`.
- **Verified on the Grok Bot box** (release tarball checked against SHA256SUMS.txt; the two missing X libraries extracted from .debs into /tmp and passed via `LD_LIBRARY_PATH`, nothing installed; bubblewrap with no network, temp HOME, `MUXIN_HOME` and `XDG_STATE_HOME` in the temp dir): smoke PASS. `muxin --version` is 0.6.0; `muxin paths` resolves under `MUXIN_HOME`; `machines --demo --json` lists exactly 9 simulated machines. `muxin mcp --demo` over stdio reports serverInfo muxin 0.6.0 and 89 tools, 17 marked `destructiveHint` (among them `run_on_machines`, `cloud_destroy`, `vm_destroy`, `process_signal`, `remove_machine`) and `status` read-only. `status` summarised "9 machines, 8 runners: 4 working, 3 idle, 1 offline"; `get_machine forge` returned it; an unknown id returned `not_found` listing the known ids; a wrong argument name returned `invalid`; a demo `run_on_machines` returned `succeeded` with simulated output; the server exited on stdin EOF. Hand mutants (8 expected machines, a run on an unknown id) each FAILed.
- **Findings**:
  - **Muxin uses the host's GitHub CLI login.** An earlier probe without `XDG_STATE_HOME` saw `$HOME/.local/state/gh/device-id` appear, but Muxin has no device-id code; that file is written by `gh` itself. Outside demo mode Muxin uses the host's `gh` login (`src/github/mod.rs:353`, `:862`, `:966-975`) and finds `gh` at hard-coded paths even when it is off PATH (`:978-998`), so any trial on nimo would read the operator's GitHub token unless the trial user has no `gh` login. The smoke points `XDG_STATE_HOME` at a temp dir and watches the real `~/.local/state/gh`.
  - **`--demo` goes after the subcommand** (`muxin machines --demo`, `muxin mcp --demo`).
  - **17 of 89 tools are destructive** across every host it knows. Any trial must expose only the read-only tools to agents (or run with no real hosts configured) until a gate exists.
  - A source build of v0.6.0 failed on the box's rustc 1.85.1 (dependencies need newer); use the checked release binary.
- **Extracted Repos / Tools**: https://github.com/LumaryLabsLLC/muxin · https://github.com/LumaryLabsLLC/muxin/releases/tag/v0.6.0
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_143_145.py --entry muxin`. Looks up `$MUXIN_BIN`, then `tmp/muxin/Muxin/muxin`, then PATH; binary sha256 (`$MUXIN_SHA256`) and version (`$MUXIN_VERSION`) pinned; `$MUXIN_LIB_DIR` becomes `LD_LIBRARY_PATH` when set. Demo data only; nothing reaches a real machine. Receipt: `pipelines/smoke/muxin/latest.json`.
- **Non-goals**: No `install.sh`, no real hosts or SSH keys added, no cloud accounts, no GitHub login, no MCP config change for any agent.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Destructive tools | An agent calls `run_on_machines` or `vm_destroy` on a real host | Read-only tool allowlist in the trial; destructive calls go through Sysadmin and the operator |
| SSH key exposure | Muxin holds keys for every host | Trial with a dedicated read-only user per host, never the operator's keys |
| State outside HOME config | `gh` (run by Muxin) writes `~/.local/state/gh`, or Muxin writes `~/.config/muxin` | `MUXIN_HOME` and `XDG_STATE_HOME` under `tmp/muxin`; the smoke watches both |
| Host GitHub token | Outside demo mode Muxin runs the host `gh` (hard-coded paths, even off PATH) and reads the operator's token | Trial only as a user with no `gh` login |
| Young project | 0.x release; tool names change | Binary sha pin; re-check the tool list on bump |

- **Status**: STAY I0 reference (read 2026-11-07). Pin `d45f3e480e6523febe81ed51061261b92714b3c9` is release v0.6.0, Apache-2.0. Fleet desktop and SSH MCP. Off the pfy build path. No install, no binary run. Prior demo smoke stays the box record. Receipt: `ops:eval/evq1107/muxin/REPORT.md`. No Feature GO.
