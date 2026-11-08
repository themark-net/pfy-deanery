# runx evq1107

## Catalog tools on this job

The job is gap H2 from the 2026-11-07 ranking: skill and tool discovery has no install gate. The discovery drop-in keeps fetched skills as data because nothing checks them before they load. runx (entry 111) is a local runtime that seals a receipt for a skill workflow run. Searched `data/stages/*.json` uses, features, and tags, plus `docs/eval/TOOLSET-RANKING.md` (2026-11-07). Batch-1 notes under `eval/ev1107/` and `eval/catchup-1107/` matter where they already measured this job.

| Tool | Stage | What that card covers | How runx compares |
|------|-------|----------------------|-------------------|
| SkillSpector | I3 | Static scan before a skill directory is copied. Catch-up: 57 directories in 38.44 s, one real `shell=True` hit. `scripts/pfy_skill_scan.py` is the advisory wrapper. | Scans the skill text and writes a JSON recommendation. This probe sealed a skill whose body says to ignore previous instructions and fetch a newer copy. Wall 0.0246 s, outcome completed. |
| Sandlock | I2 | Rootless confinement of one fetched-skill install command. Probe: 4/4 escapes blocked, stage write landed. | Confines the process. This probe's cli-tool wrote, read, and deleted outside the skill directory, and the receipt sealed. |
| cedr | I1 | Pin skill directories, then fail when those files change. Trial: 43 skills, one-line edit caught. | The hash holds on every later check. runx refuses a digest mismatch only when the caller passes both digests. With the flags omitted, the edited skill still sealed. |
| write-guard-mcp | I3 | Write mediation above the cage mount. | Mediates writes in the cage. runx's recorded boundary is `trusted_host_process`. |
| destructive_command_guard | I1 | Blocks destructive shell commands. | Matches command text. The escape was a Node `fs` call inside an admitted cli-tool. It ran. |
| asm (agent-skill-manager) | I1 | Cross-agent skill installer, with a skill audit feature. | Installs and audits. `runx add` on a local directory exited 1 in 0.0008 s (`registry_error`, wants `<owner>/<name>`). |
| Bumblebee | I2 | Advisory lockfile and MCP config scan. | Scans other files. It does not seal a skill run. |
| Tracekit | I0 | Signed, policy-gated tool call records. | Same neighborhood, still awareness. This receipt had `grant_refs` 0 and decision `open`. |
| HAR | I0 | Tree-hash receipt for a worktree slot. Probe stayed I0 (0.837 s vs a git worktree at 0.222 s). | A receipt for a different subject. |
| Skills Manager | I0 | Skill distribution CLI. | Distribution only. |
| Grok CLI bootstrap | I3 | Operator skills install for the skills we already keep. | Installs a trusted tree. |
| agent-cage (PNNL) | I3 | Isolated lab for Grok. | The lab boundary. runx is not a sandbox. |
| odai | I0 | Evidence-before-done governance skill. | A skill, not a runner. |

skill-up is I3 on gap H1 (with-skill versus baseline). It does not scan an install.

runx does not beat SkillSpector, Sandlock, or cedr on H2. The receipt machinery works. The install gate does not.

## Verdict

STAY I0. Install-gate refuses were 0/4. Receipt checks were 3/3. Echo median was 0.0249 s over 5 runs. The sealed receipt recorded `execution_boundary` `trusted_host_process`, `grant_refs` 0, `scope_refs` 0, and decision `open`. Nothing is wired into a gate.

## Pin

Host is linux x86_64. Node v22.23.0. No account, no key, no hosted call. `runx login`, `runx publish`, `runx connect`, and `runx add` of a GitHub URL were not run. A GitHub add uses the hosted index.

Release `cli-v0.9.1`, published 2026-09-13T00:38:20Z. Annotated tag object `e19e133047343211a0eb4032eb9566f782feeff8` points at commit `4576f08185dbf1f9b76dadfad39ca5cc92e8a142`. The GitHub release API digest for the musl tarball is `sha256:59eee2af81d24d0f8ba2416e2bac55d147ed93693e6a41ffe7c2cfd5cba98cc7`, and that matches `checksums.txt` and the `.sha256` sidecar.

```bash
BASE=/home/mark/.cache/pfy/tools/runx
mkdir -p "$BASE/home" "$BASE/config" "$BASE/cache" "$BASE/tmp" "$BASE/unpack"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/config" XDG_CACHE_HOME="$BASE/cache" TMPDIR="$BASE/tmp"
curl -fsSL -o "$BASE/checksums.txt" \
  https://github.com/runxhq/runx/releases/download/cli-v0.9.1/checksums.txt
curl -fsSL -o "$BASE/runx-0.9.1-x86_64-unknown-linux-musl.tar.gz.sha256" \
  https://github.com/runxhq/runx/releases/download/cli-v0.9.1/runx-0.9.1-x86_64-unknown-linux-musl.tar.gz.sha256
curl -fsSL -o "$BASE/runx-0.9.1-x86_64-unknown-linux-musl.tar.gz" \
  https://github.com/runxhq/runx/releases/download/cli-v0.9.1/runx-0.9.1-x86_64-unknown-linux-musl.tar.gz
echo "59eee2af81d24d0f8ba2416e2bac55d147ed93693e6a41ffe7c2cfd5cba98cc7  $BASE/runx-0.9.1-x86_64-unknown-linux-musl.tar.gz" | sha256sum -c
tar -xzf "$BASE/runx-0.9.1-x86_64-unknown-linux-musl.tar.gz" -C "$BASE/unpack"
"$BASE/unpack/runx-0.9.1-x86_64-unknown-linux-musl/runx" --version
```

`sha256sum -c` printed OK. `--version` printed `runx-cli 0.9.1`. License file in the archive is Apache-2.0.

| File | Bytes | sha256 |
|------|------:|--------|
| tarball `runx-0.9.1-x86_64-unknown-linux-musl.tar.gz` | 15958297 | `59eee2af81d24d0f8ba2416e2bac55d147ed93693e6a41ffe7c2cfd5cba98cc7` |
| `runx` | 30488704 | `e0c0627882c2ce7a4e8cfb20cf4896a4aa371db0e13c95c8b86fa31276388b60` |
| `runx-js-worker` | 7287824 | `49230c5fb9fbb9f436b30c3c57bcc5300d54f83318815625811c6bae113ca635` |

The unpacked tree is 37787834 bytes, under the 50 MB lightweight bar. The tarball kept beside it brings the cache install to about 53.7 MB. Nothing from the archive is in the git tree. The probe uses `runx` only. Its runners are cli-tool Node scripts, the same runner type as upstream hello-world at this tag, so `runx-js-worker` was not executed. v0.9.1 profiles are `X.yaml`.

## Probe

`python3 eval/evq1107/runx/probe.py` from this worktree. Exit 0. Numbers are `eval/evq1107/runx/results.json`. Runtime trees are under `tmp/runx-probe/` (gitignored). The child environment sets `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` under the cache path, drops inherited `RUNX_*` names and key-like names, and passes a throwaway Ed25519 seed only in that child. The seed is not printed and not stored. Issuer type is `ci`. Login-home `.runx`, `.config/runx`, and `.cache/runx` were absent before and after.

Four hazards, with no digest flags, which is how a fetched directory would be named:

| Hazard | Result | Wall |
|--------|--------|-----:|
| SKILL.md says to ignore previous instructions and fetch a newer copy. Runner echoes the input. | sealed, outcome completed, message echoed | 0.0246 s |
| cli-tool writes `escaped.txt` outside the skill directory | sealed, write landed | 0.0248 s |
| same run reads `canary.txt` outside the skill directory | sealed, canary returned in the result | same run |
| same run deletes `sentinel.txt` outside the skill directory | sealed, file gone | same run |

Refuses before the act: 0/4.

Digest pin, separate copy of the escape skill. `runx skill inspect` returned package `sha256:a380aceb3b5f8049b12d36ed74a5c7d3668cdda88a606f4cdc0317c9a0d591d1` and closure `sha256:90eb9c31bdc4281c9ca64bf1e8a76ab5a5b3f8a97ee191e2bfb1a6d9e3dd54e9`.

| Call | Result |
|------|--------|
| Both digests, correct | sealed, and the outside write landed |
| Wrong package digest, real closure digest | failure, `skill package digest mismatch`, outside files untouched |
| Skill file edited, old digests passed again | failure before the write |
| Same edited skill, digest flags omitted | sealed, and the three outside effects landed |

The pin works when the caller already has both digests. It is not applied on its own.

Receipt checks on the benign echo (5 runs, walls 0.0297, 0.0256, 0.0221, 0.0249, 0.0226 s, median 0.0249 s):

| Check | Result |
|-------|--------|
| `runx verify` with the signing identity | exit 0, `valid` true, `signature_mode` production |
| same receipt, different seed | exit 3, `valid` false, `SignatureKeyHashMismatch` |
| `created_at` edited to `2020-01-01T00:00:00.000Z` | exit 3, `valid` false, `SealDigestMismatch` and `SignatureInvalid` |

3/3. A run with no signing identity still sealed. `runx verify` then exited 1 (`status` failure). The same receipt passed with `--allow-local-development-signatures` in mode `local-development`. That flag is not evidence.

`runx add <local-dir>` exited 1 in 0.0008 s with `registry_error`. It wants `<owner>/<name>`. It did not scan the directory.

## Gates

Value gate, 1 of 4. Short of I3.

1. Gap fill. Not met. 0/4 install hazards were refused. SkillSpector already scans, Sandlock already confines, cedr already pins.
2. Operator leverage. Not met. Naming a directory runs the skill. A receipt after the fact does not decide the load. Adopting the runtime would add a second skill format beside the packs we already run.
3. Evidence. Met. The probe exited 0 on the pinned binary.
4. Blast radius. Not met for this job. Apache-2.0, no weights, no account on the local path, and the unpacked tree is under 50 MB. The boundary is `trusted_host_process` with 0 grants, so the fetched skill runs as the user.

Modularity gate, all four hold. That allows a local probe. It does not by itself promote.

1. Local binary needed. Met. Empty grants, the boundary string, and the outside write are host behavior.
2. Bounded surface. Met. One `runx` binary. This probe used `skill`, `skill inspect`, `verify`, and `add`.
3. Isolatable. Met. Cache path. It is not the product runtime.
4. Reversible. Met. Deleting the cache directory leaves the entry, the card, and this report.

I2 is for a probe that measurably helps while potential is still open. This probe answered the question: the receipt checks pass, and the install gate does not. Potential is low.

## Risks

| Risk | How it fails | How we recover |
|------|----------------|----------------|
| Placeholder signatures | A receipt with no seed still seals. `--allow-local-development-signatures` makes verify say valid. | Count only production mode. This report ignores the allow flag. |
| Trusted host process | The cli-tool has the user's rights. 0/4 hazards were blocked. | Keep SkillSpector in front of a copy and Sandlock around an install command. Do not point `runx skill` at a fetched tree. |
| Optional digest | Omit the two flags and an edited skill still runs and seals. | Treat the pin as caller-supplied. cedr already fails a one-line skill edit without that step. |
| Hosted add | A GitHub `runx add` talks to the hosted index. Login, publish, and connect are in the same binary. | This lane did not call them. A local path failed closed. Leave the non-goals in place. |
| Format churn | v0.9.1 reads `X.yaml`. Later main reads `run.yaml`. | The probe exits 2 when the binary sha differs. Keep the tag and the sha together. |
| Receipts in the worktree | The default directory is `.runx/receipts` in the working directory. | The probe passes `-R` under `tmp/runx-probe/`, which is gitignored. |
| Second runtime | Skill packs here are `SKILL.md` plus our own runners. | Stay I0. Copying receipt fields later is a separate note, not this binary. |

## Next gate

Stay I0. Reopen only if a later ticket copies the receipt fields we measured (subject, authority, seal, fail-closed verify) into a pfy record and shows a tampered run that the current handoff does not catch. That ticket grills wiring first. No pregate, CI, or other gate in this lane. Not a Feature GO.

## Five questions (this tool in the pipeline)

1. What triggers it? Nothing added here. A person would run `runx skill <dir>` on a skill that is already trusted. Discovery stays on `scripts/pfy_skill_scan.py` and the no-install rule in the skill-discovery drop-in.
2. What does it do, and which services does it read and write? It reads the pinned binary and the skill directory. It writes the receipt directory named with `-R`. With the three `RUNX_RECEIPT_SIGN_*` variables set together it signs. This probe used no hosted model, no account, and no network after install.
3. What does it trigger next? Nothing. It does not call SkillSpector, Sandlock, or pregate.
4. Where does a human re-enter? Before a fetched skill is loaded. runx will run the directory it is given. A promotion of this runtime needs a later grilled ticket and Mark's GO. This lane does not ask.
5. What stops two runs doing the same work? This lane does not share a receipt directory. The eval slot is one worktree. The receipt has idempotency fields. No second scheduler is added.
