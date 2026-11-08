### Entry 157: SysKnife: typed, approval-gated Linux admin for agents

- **URL**: https://github.com/lacs-project/sysknife (MIT, Copyright (c) 2026 Vladimir Rotariu, Rust). Checked at commit `1b3aab98b878128a267368cd47b51c921cd31219` (committer 2026-11-03T01:25:27Z, `chore(release): 0.30.0`). CLI crate `sysknife-cli` version `0.30.0`, binary `sysknife`. GitHub API description: "An AI that administers Linux through typed, approval-gated, Ed25519-audited actions. The model selects the action; the daemon builds the command."
- **Date**: 2026-11-02 (X intake)
- **Source / Poster**: https://x.com/DanKornas/status/2117178905559715995
- **Summary / Key Claims** (upstream README and crate description; their claims except where marked verified): a Linux sysadmin MCP server and CLI. The model picks a typed action. A daemon builds the command. Actions are approval-gated and Ed25519-audited. The README line is "Plan. Approve. Audit." `--dry-run` is a planner preview, not a direct "run this shell string" switch. Upstream also ships `npx sysknife-setup`.
- **Why it matters here**: agents that do host work on nimo need a guardrail that does not hand the model a shell. Entry 041 `destructive_command_guard` (TOOLS.md, pattern list next to write-guard) blocks known-bad commands. SysKnife is a different shape: the model names an action, and the daemon is what builds the command, with an approval step and an audit signature. Comparison only. Not a replacement, and not a TOOLS.md row.
- **Fit on nimo**: AMD Strix Halo, Radeon 8060S, no NVIDIA. The tool is a Rust CLI and does not need a GPU. This machine has no `cargo` and no `rustc`, and no staged binary. The smoke exits 2. A later run can build only from a clone already at the pin.
- **Verified on nimo** (2026-11-02, this worktree, no sudo): `python3 examples/x-intake-local/smoke_157.py` exited 2. Receipt verdict `FAIL_CANNOT_RUN_HERE`. Reason: `sysknife is not staged and cargo is not available; not downloading a release binary and not building`. No release binary was downloaded. The planner dry-run was not started. Real-HOME paths `.sysknife`, `.config/sysknife`, `.local/share/sysknife`, and `.local/bin/sysknife` were unchanged.
- **Findings**:
  - `--dry-run --non-interactive --json check disk usage` still calls the planner. The smoke runs that only when a binary exists and `bwrap` can start, and it never passes `--yes` or `--dangerously-skip-approval`.
  - Without bubblewrap the smoke stops after `--help` and exits 2, so the planner is not called on the open network. This nimo run never got that far: there was no binary.
  - `npx sysknife-setup`, a daemon install, and unattended root are out of scope. Do not set an accept-unattended-root variable.
- **Extracted Repos / Tools**: https://github.com/lacs-project/sysknife · CLI crate `apps/sysknife-cli` · compare with Entry 041 `destructive_command_guard` (https://github.com/Dicklesworthstone/destructive_command_guard)
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row, no stage card.
- **Smoke**: `python3 examples/x-intake-local/smoke_157.py`. Uses `run_isolated`, `find_bin`, `pinned`, and `timeout_reason`, with `kill_on_exit=True`. Reads `$SYSKNIFE_BIN`, else `tmp/sysknife/sysknife`, else PATH. A set `SYSKNIFE_BIN` or `CARGO_BIN` that is not executable exits 2 and does not fall through. With no binary it builds only when cargo exists and `$SYSKNIFE_DIR` (else `~/DEVELOP/pfy-mentat/tmp/sysknife`) is a git repo at the pin (`$SYSKNIFE_COMMIT`). `CARGO_HOME` and the target dir stay under this worktree's `tmp/xintake-157/`. Then `--version` must contain `0.30.0` (`$SYSKNIFE_VERSION`), `--help` must show `--dry-run`, and the dry-run must return a plan (`action`, `dry_run`, or `dry-run` in the output) with exit 0. A planner or daemon failure exits 2. No root, no `--yes`. Receipt: `pipelines/smoke/sysknife/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_157` (8 stub tests: missing binary, hang killed, no surviving grandchild, plan without execution flags, planner failure, real-HOME write, bad timeout, gitignored receipt).
- **Non-goals**: No root, no daemon install, no `npx sysknife-setup`, no release-binary download, no `--yes`, no system change, no TOOLS.md row. Catalog HOLD 70-75 untouched.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Planner runs a real change | `--yes` or a skip-approval flag executes the built command | The smoke refuses those flags. A trial stays on `--dry-run` until a person approves one action |
| Build writes outside DEVELOP | cargo uses the real `~/.cargo` | `CARGO_HOME` and `CARGO_TARGET_DIR` are under the worktree `tmp/`. This run did not build |
| Unattended root | An env opt-in lets the daemon act as root | Do not set it. No sudo in this slice |
| Pin drift | `main` moves past 0.30.0 | The smoke checks the commit and the version string |

- **Status**: STAY I0 reference (read 2026-11-07). Pin `1b3aab98b878128a267368cd47b51c921cd31219` is CLI 0.30.0, MIT. No cargo, no install, no code copy. Smoke stayed exit 2. H2 stays with SkillSpector. Receipt: `eval/evq1107/sysknife/REPORT.md`. No Feature GO.
