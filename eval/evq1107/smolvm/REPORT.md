# smolvm evq1107

## Catalog tools on this job

The job is gap H2 from the 2026-11-07 ranking: skill and tool discovery has no install gate. The discovery drop-in keeps fetched skills as data because nothing checks them before they load. smolvm (entry 109) is a KVM microVM that can run one command with its own guest kernel. Searched `data/stages/*.json` uses, features, and tags, plus `docs/eval/TOOLSET-RANKING.md` (2026-11-07). Batch-1 notes under `eval/ev1107/` and `eval/catchup-1107/` matter where they already measured this job.

| Tool | Stage | What that card covers | How smolvm compares |
|------|-------|----------------------|---------------------|
| SkillSpector | I3 | Static scan before a skill directory is copied. Catch-up: 57 directories in 38.44 s, one real `shell=True` hit. | Checks the skill text. This probe does not read the skill. It only runs a shell in a guest. |
| Sandlock | I2 | Rootless confinement of one fetched-skill install command. Probe: 4/4 escapes blocked, stage write landed, startup median 2.8 ms, full installer 0.1163 s, cache under 50 MB. | Same job, on the host kernel. This probe blocked 3/3 filesystem escapes in 3.0446 s and used 203328512 allocated bytes. |
| agent-cage (PNNL) | I3 | Docker lab for Grok, filesystem MCP, and policy smokes. | The lab boundary. smolvm is a local microVM, not that lab. |
| write-guard-mcp | I3 | Write mediation above the cage mount. | Mediates writes inside the cage. This probe never mounted a host path. |
| destructive_command_guard | I2 | Classifies one shell command and denies destructive git, filesystem, and disk commands. Probe denied 12/12 destructive commands. | Matches command text. This probe does not look at the command. A plain `printf` still ran inside the guest. |
| Bumblebee | I2 | Advisory lockfile and MCP config scan. | Scans files. It does not run the install. |
| cedr | I1 | Pin skill directories, then fail when those files change. Trial: 43 skills, one-line edit caught. | Holds a hash of the skill tree. This probe does not hash a skill. |
| asm (agent-skill-manager) | I1 | Copy a local skill into a project provider directory. Probe: 0/1 high-risk copies blocked, and audit read 0 files. | Copies the skill onto the host. This probe did not copy anything onto the host. |
| runx | I0 | Seals a receipt for a skill workflow run. Install-gate refuses were 0/4. Boundary was `trusted_host_process`. | A receipt, not a VM. |
| Tracekit | I0 | Signed records of tool calls. Coding and dev packs blocked 0/6 skill loads. Strict blocked 1/6. | A policy record on the host. This probe is a guest kernel. |
| CodeGuard | I0 | Secure-coding rule text. Not an install gate. | Text only. |
| Skills Manager | I0 | Skill distribution CLI. | Distribution only. |
| harness2 | I1 | Sandboxed OpenCode trial (`#sandbox`). Held-out gain was 0. | One harness trial, not a per-command install wrapper. |

smolvm does not beat SkillSpector or Sandlock on H2. The separate kernel is real (guest `6.12.95`, host `7.0.0-38-generic`). The install check we already have is lighter and already measured. Nothing is wired into a gate.

## Verdict

STAY I1. The guest blocked 3/3 filesystem escapes in 3.0446 s with no volume and no `--net`. The allocated cache is 203328512 bytes, so the I2 size bar fails. Sandlock already blocks install escapes in 2.8 ms. Value gate is 1 of 4. No gate wiring.

## Pin

Host kernel `7.0.0-38-generic`. `/dev/kvm` is read/write for this user (group `kvm`). No account and no key. The `curl | bash` installer was not used. No smol cloud, no pack push, no checkpoint.

Release `v1.26.1`, published 2026-10-10T12:15:50Z. Annotated tag object `39f7c83e983bbc5ff408129a83d772f398d42861` points at commit `093852e8f527ce7db5f96195b909de15fef82251`. The GitHub release API digest for `smolvm-1.26.1-linux-x86_64.tar.gz` is `sha256:bcae519f7dad3cead2deaa0362a42a1ad7bffce73ea7a28161dea6822c559654`, and that matches `checksums.sha256`. `smolvm-bin` matches the tarball `checksums.txt` (`62ed0353d664c2d6d78bd87ecf3213c64464003f51cb58506b87b187b1a6494a`). `smolvm --version` printed `smolvm 1.26.1`.

Image pin `alpine:3.22@sha256:5291449c3df73caf6ed85e649dec1b9e818b39a5d8c871e97afc13e9cd5e8fa8`. The digest in the receipt is that pin. It is not taken from guest output. The evidence line is `Using cached image e3e932cf66304460 (host cache hit; no pull)`.

```bash
BASE=/home/mark/.cache/pfy/tools/smolvm
mkdir -p "$BASE/home" "$BASE/config" "$BASE/cache" "$BASE/tmp" "$BASE/unpack" "$BASE/dl"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/config" XDG_CACHE_HOME="$BASE/cache" TMPDIR="$BASE/tmp"
curl -fsSL -o "$BASE/dl/checksums.sha256" \
  https://github.com/smol-machines/smolvm/releases/download/v1.26.1/checksums.sha256
curl -fL -o "$BASE/dl/smolvm-1.26.1-linux-x86_64.tar.gz" \
  https://github.com/smol-machines/smolvm/releases/download/v1.26.1/smolvm-1.26.1-linux-x86_64.tar.gz
( cd "$BASE/dl" && sha256sum -c checksums.sha256 --ignore-missing )
tar -xzf "$BASE/dl/smolvm-1.26.1-linux-x86_64.tar.gz" -C "$BASE/unpack"
sha256sum "$BASE/unpack/smolvm-1.26.1-linux-x86_64/smolvm-bin"
"$BASE/unpack/smolvm-1.26.1-linux-x86_64/smolvm" --version
```

`sha256sum -c` printed OK for the linux-x86_64 tarball.

| File | Bytes |
|------|------:|
| tarball `smolvm-1.26.1-linux-x86_64.tar.gz` | 46763510 |
| `smolvm-bin` | 40497848 |
| `lib/libkrunfw.so.5.5.0` | 17172152 |
| `lib/libkrun.so` | 9048272 |
| cache allocated (`du -s -B1`) | 203328512 |
| cache apparent (`du -s -B1 --apparent-size`) | 53981834227 |

The apparent size is the sparse `storage-template.ext4` (21474836480) and `overlay-template.ext4` (10737418240) beside the binary. Those three binaries alone are 66718272 bytes, over the 50 MB lightweight bar, before the templates. The git tree has no binary.

## Probe

`python3 eval/evq1107/smolvm/probe.py` from this worktree. Exit 0. Numbers are `eval/evq1107/smolvm/results.json`.

The host control is `/bin/sh` with the same script. It must see the sentinel, rewrite it to `pwn`, and see the cwd marker. `control_escapes_blocked` 0 means that host shell was not confined. The guest is `machine run` with `--oci-cache --cpus 1 --mem 512 --storage 1 --unprivileged`, no `--net`, and no `--volume`. The cwd is the probe work directory. The sentinel is outside that directory and outside the redirected HOME. The guest tries to read the sentinel, overwrite it, and read the cwd marker.

A cold run without `--net` exited 1 in 14.68 s: `networking is disabled`, and the in-guest pull could not resolve `index.docker.io`. One warm run then baked the image:

```text
machine run --net --dns 1.1.1.1 --oci-cache --image <pin> --cpus 1 --mem 512 --storage 1 -- true
```

That warm wall was 9.85 s (`baked in 6s`, `Caching image e3e932cf66304460`). The committed probe did not repeat it (`warm_wall_s` is null). An earlier sentinel-only no-net run took 2.97 s. The same probe, before it required the image line, took 3.2625 s. The receipt below is the committed run.

| Run | Wall | Guest kernel | Filesystem escapes blocked | Sentinel unchanged | Real HOME smolvm dirs |
|-----|-----:|--------------|---------------------------:|--------------------|------------------------|
| host control | n/a | host | 0/3 | control file became `pwn` | unchanged |
| guest, cached, no `--net` | 3.0446 s | 6.12.95 | 3/3 | yes | unchanged |

Guest stdout was the cache line, `pfy-smolvm-install-ok`, `name: probe-skill`, `6.12.95`, `host-hidden`, `host-write-blocked`, `cwd-hidden`. Stderr was `can't create` the sentinel path (`nonexistent directory`). The three escapes are: sentinel not visible, sentinel bytes unchanged, cwd marker not visible. No TCP connect was attempted, so egress deny is not a measured number. `--net` was absent on the measured run.

The install body is `printf 'name: probe-skill'`. It is not a package install. Upstream's boot claim is under 200 ms. This wall is the whole `smolvm` process plus the guest shell, and it is 3.0446 s. Default `--mem` is 8192 MiB and default `--storage` is 20 GiB. This run set 512 and 1.

`python3 -m unittest tests.test_smolvm_probe` passed. Those tests use stub executables. A stub that prints the host kernel and rewrites the sentinel exits 1 with `guest_escapes_blocked` 0. A stub that deletes the sentinel exits 1 with `sentinel_unchanged` false. A stub that prints kernel `6.12.95` and leaves the sentinel exits 0 with 3/3. With `SMOLVM_REQUIRE_IMAGE=1`, a missing cache line exits 1 even when the three escapes are blocked. A wrong `SMOLVM_SHA256` exits 2 and the stub does not run. No network, no `/dev/kvm`, no real binary.

## Gates

Value gate, 1 of 4. I3 needs 3 of 4 plus pipeline evidence.

1. Gap fill. Not met. SkillSpector checks content. Sandlock confines the install on this host. The separate kernel is a real difference and it is not a better install gate.
2. Operator leverage. Not met. One cached run is 3.0446 s, the first pull needs `--net`, and the cache is 203328512 allocated bytes. Sandlock's startup median was 2.8 ms.
3. Evidence. Met. The probe exited 0 on this host with `/dev/kvm` read/write.
4. Blast radius. Not met. Apache-2.0, no account, no weights. The copy is large binaries plus sparse 10 GiB and 20 GiB templates. Default RAM is 8192 MiB. That is not a day-to-day install wrapper.

Modularity gate, all four hold. The I2 size bar does not.

1. Local binary needed. Met. Guest kernel and hidden host files are host behavior.
2. Bounded surface. Met. One `smolvm machine run` entrypoint. The Kubernetes shim was not run.
3. Isolatable. Met. Cache path under `~/.cache/pfy/tools/smolvm/`. It is not the product runtime.
4. Reversible. Met. Deleting the cache directory leaves the entry, the card, and this report.

I2 needs the lightweight bar (under 50 MB, no large binaries). The unpacked binaries are 66718272 bytes before templates. The stage stays I1. I3 would also need `self_pipeline` evidence. This lane does not wire a gate. Potential stays low.

## Risks

| Risk | How it fails | How we recover |
|------|----------------|----------------|
| No KVM | `/dev/kvm` is not read/write | The probe exits 2 and does not exec. This host was read/write. A group change still needs Mark. |
| First pull | Without `--net` the guest cannot resolve the registry (14.68 s, exit 1) | One warm run with `--net --dns 1.1.1.1 --oci-cache`, then measure with `--net` off. If the warm fails, do not claim isolation. |
| Sparse disks | `storage-template.ext4` and `overlay-template.ext4` look like 20 GiB and 10 GiB | Keep them in the tool cache. `du -s -B1` allocated 203328512. Delete the cache directory to drop them. |
| Default RAM | Forgotten `--mem` caps the guest at 8192 MiB | This probe passed `--mem 512`. Do not run the default during a local-model bench. |
| Cwd mount | A later build mounts the process cwd and the guest reads the repo | The cwd marker check fails and `guest_escapes_blocked` drops. This run was `cwd-hidden`. |
| Secret flags | `--secret-env`, `--credential`, or `--volume` copies host material into the guest | This probe passed none of those. Do not add them for an untrusted install. |
| Sha drift | A new tarball is unpacked over the pin | The probe exits 2 on a `smolvm-bin` mismatch and does not exec. |
| Early onboard | Treating 3/3 as a product gate | Stay I1. Sandlock and SkillSpector remain the H2 path. |

## Next gate

Stay I1. Re-open only if a hostile-code boundary is required and a copy without the 10 GiB and 20 GiB templates is under 50 MB. That would still sit beside Sandlock, not replace the SkillSpector scan. No pregate, CI, or other gate wiring in this lane.

## Five questions (this tool in the pipeline)

1. What triggers it? Nothing in this lane. A later command would run one untrusted install inside `smolvm machine run` only if Sandlock's shared kernel is not enough. This lane adds no trigger.
2. What does it do, and which services does it read and write? It reads the pinned binary, `/dev/kvm`, and a cached OCI image. The measured run writes guest stdout only. State stays under the redirected HOME in the tool cache. The real HOME's `~/.cache/smolvm` and `~/.local/share/smolvm` were absent before and after. No hosted model, no account, no key.
3. What does it trigger next? Nothing. A later path could hand a stage directory to SkillSpector. That handoff is not built.
4. Where does a human re-enter? Before any copy from a guest into `.grok/skills` or `bootstrap/grok-cli/skills`, and before any `/dev/kvm` group change. This lane does not make that a gate.
5. What stops two runs doing the same work? Each probe uses the tool cache and does not edit the pinned binary. This lane is one worktree. The run does not take the model lock. Live model work was not used.
