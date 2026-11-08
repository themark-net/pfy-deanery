# Sandlock evq1107

## Catalog tools on this job

The job is rootless confinement of one fetched-skill install command: the granted stage directory can be written, and the network stays closed unless a host:port is named. These cards already cover a neighboring part of that job.

| Tool | Stage | What that card covers | How sandlock compares |
|------|-------|----------------------|------------------------|
| SkillSpector | I3 | Static scan before a skill directory is copied. Catch-up trial: 57 directories in 38.44 s, one useful true positive. | Checks content. This probe confines the process that would run the install. |
| agent-cage (PNNL) | I3 | Docker lab for Grok, filesystem MCP, and policy smokes. | The lab boundary. Sandlock wraps one host command, with no docker and no sudo. |
| write-guard-mcp | I3 | Write mediation above the cage mount. | Mediates writes inside the cage. Sandlock is a host wrapper. |
| destructive_command_guard | I1 | Blocks destructive shell commands. Overlaps write-guard. | Matches command text. This probe blocked a plain `printf` and `cat` by effect. |
| Bumblebee | I2 | Advisory lockfile and MCP config scan. ev1107 exact-match supply-chain hit, and the check is not on the pipeline. | Scans files. It does not wrap the installer. |
| asm (agent-skill-manager) | I1 | Cross-agent skill installer, with a skill audit feature. | Installs and audits. It does not confine the install process. |
| harness2 | I1 | Sandboxed OpenCode trial (`#sandbox`). Held-out gain was 0. | One harness trial, not a per-command install wrapper. |
| Skills Manager | I0 | Skill distribution CLI. | Distribution only. |
| Grok CLI bootstrap | I3 | Operator skills install and cage sessions. | Installs trusted skills. It is not a wrapper for an untrusted fetched installer. |

Sandlock does not beat SkillSpector, agent-cage, or write-guard at the jobs those cards already do. It is the one in this set that measured host-command confinement without sudo or docker. That is a probe result, not a replacement.

## Verdict

PROMOTE I2. Enforce mode blocked 4/4 escapes and the stage write landed. Dry-run listed 2 filesystem changes and left the tree unchanged. Startup median was 2.8 ms over 20 runs. The content check stays with SkillSpector. Nothing is wired into a gate.

## Pin

Host kernel `7.0.0-38-generic`. `sandlock check` exit 0, Landlock ABI v8, minimum required ABI v6, status OK. Filesystem, truncate, TCP ports, device ioctl, IPC scoping, and signal scoping are available. No account and no key.

Release `v0.8.9`, published 2026-09-27, tag commit `4a8c09fb537a152710cddfb1a4351d7e8a5af05f` (the tag object is the commit). Asset digest from the GitHub release API matched the file.

```bash
BASE=/home/mark/.cache/pfy/tools/sandlock
mkdir -p "$BASE/home" "$BASE/config" "$BASE/cache" "$BASE/tmp" "$BASE/unpack"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/config" XDG_CACHE_HOME="$BASE/cache" TMPDIR="$BASE/tmp"
curl -fsSL -o "$BASE/sandlock-x86_64-unknown-linux-gnu.tar.gz" \
  https://github.com/multikernel/sandlock/releases/download/v0.8.9/sandlock-x86_64-unknown-linux-gnu.tar.gz
echo "2b6c3c4858177f0603c7c016dd2da854c09cc1dbce13682b8a627465c7842018  $BASE/sandlock-x86_64-unknown-linux-gnu.tar.gz" | sha256sum -c
tar -xzf "$BASE/sandlock-x86_64-unknown-linux-gnu.tar.gz" -C "$BASE/unpack"
"$BASE/unpack/sandlock" --version
"$BASE/unpack/sandlock" check
```

`sha256sum -c` printed OK. `sandlock --version` printed `sandlock 0.8.9`.

| File | Bytes | sha256 |
|------|------:|--------|
| tarball `sandlock-x86_64-unknown-linux-gnu.tar.gz` | 12483723 | `2b6c3c4858177f0603c7c016dd2da854c09cc1dbce13682b8a627465c7842018` |
| `unpack/sandlock` | 13267816 | `79c8d72ddfef2c51fa7c598ef39c8ae746eafed76abd53a61d232ddee7e122b0` |
| `unpack/sandlock-oci` | 13188072 | not run |
| `unpack/libsandlock_ffi.so` | 9459592 | not run |

The three unpacked binaries are 35915480 bytes. Those three plus the tarball are 48399203 bytes. The cache directory is 48414062 bytes once release metadata and trial scratch are included, which is under the 50 MB lightweight bar. The git tree has no binary. `sandlock-oci` is out of scope (no OCI shim). The probe uses `unpack/sandlock` only.

## Probe

`python3 eval/evq1107/sandlock/probe.py` from this worktree. Exit 0. Numbers are `eval/evq1107/sandlock/results.json`. Runtime trees are under `tmp/sandlock-probe/` (gitignored). The canary file is under the cache `probe-secret/` directory. The probe's child environment is `HOME`, `XDG_*`, `TMPDIR`, `PATH`, and `LANG` only. Sandboxed runs also pass `--clean-env`.

The installer writes `SKILL.md` into the stage directory, then tries four escapes: write `SKILL.md` into a skills directory that is granted read and not write, write a sibling that has no grant, `cat` a canary outside every grant, and open TCP to `127.0.0.1` on a port this process is listening on. The unsandboxed control is the same script, so a blocked escape is only counted when the control shows the escape works.

| Run | Wall | Install landed | Escapes blocked | Loopback accepts |
|-----|-----:|----------------|----------------:|-----------------:|
| control, no sandbox | 0.0168 s | yes | 0/4 | 1 |
| enforce, default network | 0.1163 s | yes | 4/4 | 0 |
| enforce plus `--net-allow 127.0.0.1:<port>` | 0.0302 s | yes | 3/4 (connect allowed) | 1 |
| `--dry-run --workdir` | 0.0067 s | discarded | 2 changes listed, 0 left on disk | n/a |

Enforce deny lines were `Permission denied` on the skills create, the sibling create, the canary `cat`, and `PermissionError: [Errno 13]` on `connect`. The shell redirect still created an empty `stolen.txt` in the stage directory. Its size was 0 bytes, and the canary string was absent. The control read 20 bytes, the whole canary.

Dry-run printed:

```text
sandlock: dry-run: filesystem changes:
A  SKILL.md
M  keep.txt
```

`keep.txt` stayed `before\n`. `SKILL.md` was not on disk afterward.

Startup is 21 runs of `sandlock run --clean-env` with read grants on `/usr`, `/lib`, `/lib64`, `/bin`, and `/etc`, then `/bin/true`. The first sample is dropped. The other 20: median 2.8 ms, min 2.7 ms, max 3.9 ms, every exit code 0. Upstream's claim is about 5 ms. This wall measurement is lower. The 0.1163 s enforce figure is one full installer, including Python, and is a single sample.

Real skill directories were not targets. A leak would have landed under `tmp/sandlock-probe/` or the cache canary path.

## Gates

Value gate, all four hold. I3 still waits on pipeline evidence.

1. Gap fill. Met. No cataloged tool wraps one host install command with Landlock and a default-deny network, without sudo.
2. Operator leverage. Met. The wrapper is one `sandlock run` line. This lane does not turn it on.
3. Evidence. Met. The probe exited 0 and `sandlock check` was OK on this kernel.
4. Blast radius. Met. Apache-2.0, no weights, no account, cache path, repo copy is text. The shared-kernel limit is under Risks.

Modularity gate, all four hold.

1. Local binary needed. Met. Default network deny, including loopback, and read versus write are host behavior.
2. Bounded surface. Met. One `sandlock run` binary.
3. Isolatable. Met. Cache path. It is not the product runtime.
4. Reversible. Met. Deleting the cache directory leaves the entry, the card, and this report.

I3 would need this probe plus `self_pipeline` evidence. The probe is repeatable. It has not been applied to this repo's pipeline, and this lane does not wire a gate. Potential stays medium. The catalog ceiling stays I1 until a TOOLS.md row exists. The stage is I2 because the probe answered the isolation question.

## Risks

| Risk | How it fails | How we recover |
|------|----------------|----------------|
| Old kernel | Below 6.12, or Landlock ABI under v6, `sandlock check` is not OK | This host is 7.0 with ABI v8. On an older host, record the check text and leave the card at I0. |
| Shared kernel | A kernel bug escapes the sandbox | Use it to shrink blast radius for our own install commands. Keep agent-cage as the lab boundary. |
| Tight profile | A real installer needs a path this profile does not grant | The command fails with Permission denied. Widen from a known-good run, or run that command without the wrapper. This probe did not run `sandlock learn`. |
| Empty redirect | `cat` of a denied file still creates an empty file in the stage | Score contents. `stolen_bytes` was 0. |
| Allowlist typo | `--net-allow` opens that host:port. The allow run connected to loopback and still blocked the three filesystem escapes | Name the port. Default policy denies loopback too. |
| Early onboard | Treating 4/4 as a product gate | Stay I2 until a grilled ticket applies it and records `self_pipeline`. |

## Next gate

Stay I2. A later ticket can grill one installer wrapper that writes a stage directory and then hands that directory to the SkillSpector advisory scan. No pregate, CI, or other gate wiring in this lane.

## Five questions (this tool in the pipeline)

1. What triggers it? A person, or a later installer command, runs one fetched skill install inside `sandlock run` before any copy into a skills directory. This lane adds no trigger.
2. What does it do, and which services does it read and write? It reads the pinned binary and the granted paths. It writes the stage directory. With `--dry-run` it prints the change list and discards it. No hosted model, no account, no key.
3. What does it trigger next? Nothing in this lane. A later path can pass the stage directory to SkillSpector. That handoff is not built.
4. Where does a human re-enter? Before a copy from the stage directory into `.grok/skills` or `bootstrap/grok-cli/skills`. The dry-run change list is the place to look. This lane does not make that a gate.
5. What stops two runs doing the same work? Each install uses its own stage directory. The run does not edit the cache binary. This lane is one worktree and does not take the model lock.
