# agent-substrate evq1107

Verdict: STAY I0. Rootless `runsc` checkpoint ran and restore was refused (`Rootless mode not supported with "restore"`). Inside `unshare -Urm`, the same 32 MiB Python counter was checkpointed, the sentry pid was gone 0.0592 s later, and restore continued at tick 2 with the same acc byte (0.1011 s). MemAvailable rose 44364 kB while that image still existed. Gap B stayed 0: host Build sessions shelved were 0, and the 3 hour `./pfy build` timeout was not changed. The Kubernetes product was SKIPPED. Nothing was wired into a gate.

## Catalog comparison

The assigned job is gap B from the 2026-11-07 ranking: `./pfy build` is not proven bot-usable. This lane's scope is gVisor checkpoint/restore of an idle process with rootless runsc, not the Substrate Kubernetes stack. Searched `data/stages/*.json` uses, features, and tags, plus `docs/eval/TOOLSET-RANKING.md` (2026-11-07). `eval/ev1107/` and `eval/catchup-1107/` do not measure this shelf. The closer probes are under `eval/evq1107/`.

| Card | Stage | What it already does | How agent-substrate compares |
| --- | --- | --- | --- |
| agent-cage (PNNL) | I3 | Docker lab for Grok, filesystem MCP, and policy smokes | The lab boundary. This probe did not start Docker. |
| Sandlock | I2 | Rootless confinement of one install command | Confines a process. It does not checkpoint it. |
| write-guard-mcp | I3 | Write mediation above the cage mount | A write gate. Not a memory image. |
| destructive_command_guard | I2 | Denies destructive shell commands | Matches command text. Not a shelf. |
| skill-up | I3 | Grades a with-skill run against a baseline | Scores a run. It does not park the process. |
| harness2 | I1 | Sandboxed OpenCode trial on the decision set | One harness trial. Not runsc checkpoint. |
| kanbots | I1 | Kanban fan-out into worktrees. Probe did not move the timeout | Does not shelf RAM. |
| Festival | I1 | Plan and checklist files. Probe did not move the timeout | Files survive without a snapshot. |
| Overtime | I0 | ACP session id survives a daemon stop. Gap B stayed 0 | A session id, not an in-memory image. |
| HAR | I0 | Worktree receipt. Gap B stayed 0 | A tree hash, not a process image. |
| Pi-Harness | I0 | Budget checkpoint in a desktop control plane. Not installed | The word checkpoint there is a policy mark. |
| runx | I0 | Seal a receipt for one skill workflow | A receipt, not a shelf. |

It does not beat what we have for gap B. It is the only card in this set that measured a gVisor memory image. That image did not make `./pfy build` finish, and it cannot attach to a process that was not started under runsc.

## Pins

| Item | Value |
| --- | --- |
| Entry read | `769fd32630aa47bd6d7050b39e1aa0804a8622dc` (2026-10-08T21:02:39Z) |
| Tag `v0.4.0` | commit `756c2a53741121e728f4cc3066c8a19e575b4919` (2026-10-07T22:53:25Z). Not the read commit. The gVisor sha256 in `manifests/ate-install/sandboxconfig-gvisor.yaml` is the same at both commits |
| Tarball | `https://storage.googleapis.com/gvisor/releases/nightly/2026-09-02/x86_64/gvisor.tar.zstd` |
| Tarball sha256 | `d547d81401461fd1c679c5c4fa0a6c2b8ef7dc3c22ce23c9e25dcc4c69cfd06f` (`sha256sum -c` OK) |
| Tarball bytes | 128870217 |
| runsc | `release-20260824.0-120-g727c8c389c36-dirty`, 109183527 bytes |
| runsc sha256 | `1a3982cb91714f9c0c7148668d2c40143ee97e238f8a8e7452e410770d34fbe3` |
| Unpack apparent | 326118412 bytes (runsc, containerd-shim, checkpointgofer, gvisor_sentry, runsc-metric-server, prewarmer) |
| License | Apache-2.0 |
| Host | kernel `7.0.0-38-generic`, cgroup `cgroup2fs`, `kernel.apparmor_restrict_unprivileged_userns=1`, `unshare -Urm` exit 0 |
| Full stack | SKIPPED. kind, kubectl, and go are not on PATH. minikube is not on PATH. docker and podman are on PATH and were not started |

The unpack is over the 50 MB lightweight bar. Nothing from the install is in git.

## Commands

```bash
BASE=$HOME/.cache/pfy/tools/agent-substrate
mkdir -p "$BASE/home" "$BASE/config" "$BASE/cache" "$BASE/tmp" "$BASE/dl" "$BASE/unpack"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/config" XDG_CACHE_HOME="$BASE/cache" \
  XDG_RUNTIME_DIR="$BASE/tmp" TMPDIR="$BASE/tmp"
curl -fL -o "$BASE/dl/gvisor.tar.zstd" \
  https://storage.googleapis.com/gvisor/releases/nightly/2026-09-02/x86_64/gvisor.tar.zstd
echo "d547d81401461fd1c679c5c4fa0a6c2b8ef7dc3c22ce23c9e25dcc4c69cfd06f  $BASE/dl/gvisor.tar.zstd" | sha256sum -c
zstd -dc "$BASE/dl/gvisor.tar.zstd" | tar -x -C "$BASE/unpack"
python3 eval/evq1107/agent-substrate/probe.py \
  --runsc "$BASE/unpack/runsc" \
  --work "$PWD/tmp/agent-substrate-probe" \
  --results eval/evq1107/agent-substrate/results.json \
  --bytes 33554432
python3 -m unittest tests.test_agent_substrate_probe
```

The probe sets `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_RUNTIME_DIR`, and `TMPDIR` under the work directory for every runsc child. It does not pass the parent environment through. The guest is a Python loop that holds 33554432 random bytes, prints one digest, then prints `tick` and one acc byte. Network is `none`. The image is deleted after the byte counts are recorded. Wall for this receipt was 9.43 s, most of it the ZFS account wait below.

## Numbers

Script exit 0. Numbers are `eval/evq1107/agent-substrate/results.json`.

| Check | Rootless `--rootless` | `unshare -Urm` |
| --- | --- | --- |
| `do echo` | 1 | not run |
| run until tick 1 | 1 | 1 |
| checkpoint exit | 0 in 0.0173 s | 0 in 0.0151 s |
| sentry RSS while running | 83428 kB | 79768 kB |
| sentry after checkpoint | gone at 0.0595 s, list status stopped | gone at 0.0592 s, list status stopped |
| image apparent / allocated / nonzero | 39059856 / 35859456 / 36086165 | 37884167 / 35064832 / 35145666 |
| fsync of the image | 0.0261 s | 0.0225 s |
| wait until `st_blocks` covered the file | 3.6335 s | 4.5298 s |
| restore | refused in 0.0065 s | 0 in 0.1011 s |
| state continued | 0 | 1 (tick 1 then tick 2, same acc) |
| restore stdout NUL bytes | 0 | 115, then `tick=2` and `tick=3` |
| MemAvailable change while the image still existed | -2516 kB | +44364 kB |

`runsc list` after the wait showed pid `-1` and status `stopped` for both. The 0.015 s checkpoint return is the syscall. The sentry was still alive for a few tens of milliseconds after that. Allocated size on this ZFS home stayed near 0 until the txg commit, so the probe polls `st_blocks` for up to 6 s. The 4.5298 s figure is that wait, not the checkpoint.

On the userns row, RSS was 79768 kB and the image allocated 35064832 bytes (34243 kB). MemAvailable rose 44364 kB. 44364 + 34243 = 78607 kB, 1161 kB under the RSS. The image was still on disk when MemAvailable was read. Rootless MemAvailable moved -2516 kB on this sample, so that row is not evidence that free RAM rose. The pid was gone on both rows.

Gap B: `gap_b_timeout_changed=0`, `host_build_sessions_shelved=0`. This probe does not start `./pfy build`. A process that is already running on the host cannot be checkpointed. Only the process runsc started can be shelved.

Payload was 32 MiB, not the 1 GiB or 8 GiB sizes in the entry plan. Those were not run.

## Gates

Value gate, one of four. Not enough for I3.

1. Gap fill. Not met for gap B. The timeout is unchanged. No other card here writes a runsc image, and that does not close the assigned gap.
2. Operator leverage. Not met. `--rootless` cannot restore. A Build session is not started under runsc, so a day of glue does not park it.
3. Evidence. Met for this runsc pin. The product quickstart was not run.
4. Blast radius. Met as a cache pin. Apache-2.0, no account, no weights, not wired. The unpack is 326118412 bytes, so the I2 size bar fails on its own.

Modularity gate, the probed unit passes and the product does not.

1. Local binary needed. Met. The rootless refusal and the reap delay are host behavior.
2. Bounded surface. Met for one `runsc` binary. The Substrate repo is a Kubernetes monorepo and was not the unit.
3. Isolatable. Met. Cache path. It is not the product runtime.
4. Reversible. Met. Deleting the cache leaves the entry, the card, and this report.

I2 also needs a lightweight copy under 50 MB. This pin is not that. I3 would need the value gate and `self_pipeline`. This lane does not wire a gate. Potential stays low.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Rootless restore | Checkpoint stops the container, then restore exits 128 and the counter is gone | Do not checkpoint with `--rootless` if the process must come back. The userns path restored this sample. Do not sudo. |
| Userns blocked | `apparmor_restrict_unprivileged_userns` is 1. On this boot `unshare -Urm` still exited 0. A later boot can fail it | Record SKIPPED. Do not change the sysctl. |
| Reap delay | `runsc checkpoint` returns while the sentry is still in `S` and still has RSS | The probe polls up to 3 s. This receipt saw the pid gone at 0.0592 s. |
| ZFS account delay | `st_blocks` reads as a few KB until the txg commits, while a read already sees the bytes | Poll up to 6 s. Trust `image_nonzero_bytes` if the poll times out. |
| Image size | A 33554432 byte payload allocated 35064832 bytes. A large shelf writes about that much | Keep the probe at 32 MiB. Delete the image after the count, which this probe does. |
| Already running Build | `host_build_sessions_shelved` is 0 | Start the process under runsc, or do not claim it was shelved. |
| Noisy MemAvailable | The rootless delta was -2516 kB | Cite sentry RSS and pid gone. Cite MemAvailable only next to the image size, as on the userns row. |
| Restore stdout | 115 leading NUL bytes, then the ticks | Score `tick` and `acc`, not a raw byte compare. |
| GPU | Not shelved. nvproxy is NVIDIA. This host is AMD | Leave GPU work on the host. |
| Early onboard | Treating one counter as a build lane | Stay I0 until a later ticket starts its own runsc process and still shows a reason to carry the 326 MB pin. |

## Next gate

Stay I0. A later ticket can re-open this only if it starts the idle process under runsc, accepts `unshare -Urm` because `--rootless` cannot restore, and accepts a cache pin over 50 MB. No pregate, CI, or other gate wiring in this lane.

## Five questions (this tool in the pipeline)

1. What triggers it? Nothing in this lane. A later shelf would run only for a process this runtime itself started.
2. What does it do, and which services does it read and write? It reads the pinned runsc and one OCI bundle. It writes a checkpoint directory under the work dir, then this probe deletes that directory. No hosted model, no account, no key. Docker and Podman were not started.
3. What does it trigger next? Nothing. It does not call `./pfy build`, pregate, or CI.
4. Where does a human re-enter? If someone wants the Substrate router, that is a different ticket. kind, kubectl, and go are absent here. minikube was not installed. This lane does not ask for them.
5. What stops two runs doing the same work? One worktree and branch per slug. Each probe uses its own `--work` and `--root`. This lane does not take the model lock.
