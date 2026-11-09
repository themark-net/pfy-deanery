### Entry 096: Sandlock — rootless Linux process sandbox (Landlock + seccomp) for agent commands

- **URL**: https://github.com/multikernel/sandlock (Apache-2.0, Rust, about 550 stars at this read, release v0.8.9 on 2026-09-27)
- **Date**: 2026-10-06 (daily X intake)
- **Source / Poster**: @DanKornas, https://x.com/DanKornas/status/2107323458866630758
- **Summary / Key Claims** (upstream README): Confines a command with Landlock (filesystem, TCP ports, IPC), seccomp-bpf and seccomp user notification (memory/process limits, IP enforcement, /proc virtualization). No root, no cgroups, no containers, no image build; ~5 ms startup. Copy-on-write workdir with `--dry-run` that lists changed files and discards them, outbound host allowlist (`--net-allow host:port`), HTTP method+host+path ACLs through a transparent proxy, saved profiles, and `sandlock learn` to generate a profile from an observed run. Python and Go SDKs over a C FFI.
- **Fit on nimo**: Needs Linux 6.12+ (Landlock ABI v6). Prebuilt `sandlock-x86_64-unknown-linux-gnu.tar.gz` unpacks to a single binary, so it can live in `~/DEVELOP/pfy-mentat/tmp/sandlock/` with no install outside DEVELOP. nimo's kernel version is not checked here; the smoke checks it.
- **Verified on the Grok Bot box** (kernel 6.12, release binary, sha256 checked): `sandlock run -r /usr -r /lib -r /lib64 -r /bin -r /etc -w <ok> -- /bin/sh -c '...'` let the write into `<ok>` land and refused a write into a sibling dir with "Permission denied". The smoke below PASSed there.
- **Why it matters here**: pfy-mentat already tracks agent containment ideas (agent-cage in TOOLS.md, Bumblebee Entry 069, destructive_command_guard in the toolset drop-in) and trailofbits/coop is on the later list. Sandlock is the lightest option that fits nimo's locks: a rootless wrapper around `./pfy build` or local-model CUA tool calls that can pin writes to one worktree under `~/DEVELOP/pfy-mentat/tmp` and block network except named hosts. The `--dry-run` COW mode is a cheap "how does it fail" probe for risky commands.
- **Extracted Repos / Tools**: https://github.com/multikernel/sandlock · https://github.com/multikernel/sandlock/releases/tag/v0.8.9
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke.py --entry sandlock`. Looks for `$SANDLOCK_BIN`, then `~/DEVELOP/pfy-mentat/tmp/sandlock/sandlock`, then PATH. Exits 2 if missing or the kernel is older than 6.12. Otherwise runs a confined shell and expects the allowed write to land and the denied one to be refused (FAIL if the denied write leaks). Receipt: `pipelines/smoke/sandlock/latest.json`.
- **Non-goals**: No `cargo install` into `~/.cargo`, no OCI shim, no HTTPS MITM or credential injection in a first trial.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Old kernel | nimo below 6.12, Landlock ABI too low | Smoke exits 2 with the kernel string; kernel change needs the operator's approval, so it stays a catalog entry |
| False sense of safety | Shared kernel; a kernel bug escapes the sandbox | Treat it as blast-radius reduction for our own agents, not a boundary for hostile code |
| Breaks tools | Too-tight profile makes Build or ROCm calls fail (GPU device nodes, /proc) | Use `sandlock learn` on a known-good run to draft the profile; keep an unsandboxed fallback |

- **Status**: I2 probe on nimo, 2026-11-07. Pinned v0.8.9 commit 4a8c09fb537a152710cddfb1a4351d7e8a5af05f, cache install only. Enforce mode blocked 4/4 install escapes and the stage write landed. See ops:eval/evq1107/sandlock/REPORT.md.
