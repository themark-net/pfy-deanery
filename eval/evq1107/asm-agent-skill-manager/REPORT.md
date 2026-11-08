# asm (agent-skill-manager) evq1107

## Catalog tools on this job

The job is gap H2 from the 2026-11-07 ranking: skill and tool discovery has no install gate. The discovery drop-in keeps fetched skills as data until something checks them. This lane also measured the catalog claim that asm distributes one skill across CLIs. Searched `data/stages/*.json` uses, features, and tags, plus `docs/eval/TOOLSET-RANKING.md` (2026-11-07 section and the 2026-10-06 hold list). Batch notes under `eval/ev1107/` and `eval/catchup-1107/` matter where they already measured this job. This lane builds no pipeline, CI, or gate step.

| Tool | Stage | What that card covers | How asm compares |
|------|-------|----------------------|------------------|
| SkillSpector | I3 | Static scan before a skill directory is copied. Catch-up: 57 directories in 38.44 s. `scripts/pfy_skill_scan.py` is the advisory wrapper. H2 says copy only after that command exits 0. | Reads SKILL.md. This probe's audit command read 0 files and returned safe. Install still copied the planted file. |
| skill-up | I3 | Grade a with-skill run against a baseline. Gap H1. | Does not scan an install. |
| Sandlock | I2 | Rootless confinement of one fetched-skill install command. Probe: 4/4 escapes blocked. | Confines the process. This probe does not wrap the copy. |
| Grok CLI bootstrap | I3 | Operator skills install and cage sessions for the tree this repo already keeps. | Installs a trusted tree. asm copied one fixture into a temp `.grok/skills` and a temp `.opencode/skills`. |
| Skills Manager | I0 | Skill distribution CLI. Comparison only. The tree stays the source. | Same job, other CLI. This probe landed 2/2 project copies and blocked 0/1 high-risk skills. |
| OpenCode Skill Creator | I0 | Frontmatter lint. The card says it is not a security scan. | Different check. |
| cedr | I1 | Pin skill directories, then fail when those files change. | Hashes bytes after they exist. |
| runx | I0 | Seal a receipt for one skill workflow run. | A receipt can seal a bad skill. |
| trailofbits-skills | I0 | Security checklists. The card says the pack is not an install gate. Its probe used SkillSpector on the pack. | Content, not the copier. |
| Cloudflare security-audit skill | I0 | Findings schema. Probe blocked 0 of 1 planted skill lines. | Another check that left the planted line in place. |
| CodeGuard | I0 | Secure-coding rule text. The card says it is not an install gate. | No copy command. |
| repository-harness | I0 | Install a repository map and four skills beside an existing AGENTS.md. | Installs a known pack. It does not label a fetched SKILL.md. |
| write-guard-mcp | I3 | Write mediation above the cage mount. | A runtime guard. |
| destructive_command_guard | I1 | Blocks destructive shell commands. | Matches command text. The planted line is a string in a fixture. |
| agent-cage (PNNL) | I3 | Isolated lab for Grok. | The lab boundary. |
| Bumblebee | I2 | Advisory lockfile and MCP config scan. | Other files. |

The 2026-10-06 ranking already lists asm under skip or hold. skill-up stays on H1.

Beats what we have: no.

## Verdict

STAY I1. `asm install --yes` copied 1/1 high-risk skills (0 blocked) in 0.0613 s. The same preview named 3/3 planted categories. `audit security` on the installed copy returned safe, 0 files, 0 lines, exit 0, in 0.042 s. A local-path audit before the copy scanned nothing (exit 1, 0.035 s). One clean skill landed in 2/2 project provider dirs. Nothing is wired into a gate.

`STAY I1 0/1 high-risk skills blocked, audit read 0 files, 2/2 project copies landed`

## Pin

Host is linux x86_64. Node v22.23.0. npm 11.12.1. No account and no key. License MIT. The entry records no commit and no checksum. This lane pinned the npm release that matches annotated tag `v2.24.0`.

| Field | Value |
|-------|--------|
| npm | `agent-skill-manager@2.24.0` |
| tag object | `2a8b36909418ea8d2372d615775c2c1fa67fc33d` |
| tag commit / npm gitHead | `10d9bac8ce34e4b2f4ea55c81166bb2777edb2a9` |
| tarball sha1 | `21d753c2179ac2d5cea2dfcf2f0f65c182a2207e` (registry shasum) |
| tarball sha256 | `78fde253af3e216098a6d471dd90341d4aace1bc839816d1080a6fc1432661dd` |
| tarball sha512 | matches the registry integrity string |
| tarball bytes | 2955401 |
| binary | `asm v2.23.0 (6cb9272)` |

The package version and gitHead say 2.24.0. The bundled CLI prints 2.23.0 and a 7-character id that this lane did not resolve as a git object. The pin is the tarball hash.

```bash
BASE=/home/mark/.cache/pfy/tools/asm-agent-skill-manager
mkdir -p "$BASE/home" "$BASE/config" "$BASE/cache" "$BASE/tmp" "$BASE/npm" "$BASE/prefix"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/config" XDG_CACHE_HOME="$BASE/cache" TMPDIR="$BASE/tmp"
export npm_config_cache="$BASE/npm" npm_config_userconfig="$BASE/npmrc" CI=1 ASM_SKIP_POSTINSTALL=1
curl -fsSL -o "$BASE/agent-skill-manager-2.24.0.tgz" \
  https://registry.npmjs.org/agent-skill-manager/-/agent-skill-manager-2.24.0.tgz
npm install --prefix "$BASE/prefix" --ignore-scripts --no-audit --no-fund \
  "$BASE/agent-skill-manager-2.24.0.tgz"
```

`sha256sum` matched the table. Registry sha512 integrity matched. npm added 50 packages. The probe recomputed the tarball sha256 and recorded `tarball_sha256_ok: true`.

Logical sizes (`du -sb`): cache directory 119,051,418 bytes, prefix 58,625,143 bytes, package directory 40,841,406 bytes (the registry unpacked size), npm cache 56,177,209 bytes. Allocated sizes on this ZFS pool (`du -sh`): cache 71M, prefix 41M, package directory 7.4M, npm cache 25M. The 50 MB I2 bar is a copy size. The runnable prefix is 58,625,143 logical bytes, over that bar. No upstream tree is committed.

During setup, `asm doctor --json` reported the registry reachable. The probe does not run doctor and does not install from the registry.

## Probe

`python3 eval/evq1107/asm-agent-skill-manager/probe.py` from this worktree. Exit 0. Numbers are `eval/evq1107/asm-agent-skill-manager/results.json`. Fixtures are the two `SKILL.md` files under `eval/evq1107/asm-agent-skill-manager/fixtures/`. Runtime trees are under the cache `tmp/asm-probe/` directory. The child env is `HOME`, `XDG_*`, `TMPDIR`, `npm_config_cache`, `npm_config_userconfig`, `PATH` (`/usr/bin:/bin`), `LANG`, `CI`, `NO_COLOR`, and git config pointed at `/dev/null`. Those homes are under the cache directory. Copies use `-s project` so the target is `.grok/skills` or `.opencode/skills` under the temp project, not a global provider dir.

The planted body contains `bash -c`, `child_process`, `API_KEY=` with a fake marker, and `https://example.invalid/skill.md`. The clean body has none of those.

| Step | Exit | Wall | Result |
|------|-----:|-----:|--------|
| `asm --version` | 0 | 0.0355 s | `asm v2.23.0 (6cb9272)` |
| `audit security` on the planted directory, before any copy | 1 | 0.035 s | scanned false. The error says the path was not found as an installed skill. |
| `install` planted, `-p grok -s project -y --json` | 0 | 0.0613 s | success true, risk high, categories Shell commands, Credentials, External URLs (3/3). File landed. All 4 planted tokens still in the copy. blocked false. `resolutionSource` is `github`. |
| `audit security planted --json` from that project | 0 | 0.042 s | verdict safe, totalFiles 0, totalLines 0, reason "No suspicious patterns detected." 0/4 tokens named. |
| `install` clean, `-p grok -s project -y` | 0 | 0.0516 s | risk safe, landed |
| `install` clean, `-p opencode -s project -y` | 0 | 0.052 s | risk safe, landed |

`high_risk_blocked` is 0/1. `providers_landed` is 2/2. `clean_safe` is 2/2. `real_homes_unchanged` is true for `~/.grok/skills`, `~/.claude`, `~/.codex/skills`, and `~/.config/opencode` (mtime and size before and after).

The install preview is what named the three categories. The JSON receipt has `success: true` and no risk field. `--yes` is the agent path from the entry, and it still copied the high-risk file. The published dist skips `SKILL.md` and every `.md` file inside `audit security`, which is why that command scanned 0 files on a skill whose only file is `SKILL.md`.

## Gates

Value gate is 2 of 4. I3 needs 3, plus a repeatable script and `self_pipeline`. This lane does not wire a gate.

1. Gap fill. Not met. SkillSpector already reads a skill before copy. This install copies a high-risk SKILL.md, and `audit security` calls that file safe.
2. Operator leverage. Not met. Two project copies, 0.0516 s and 0.052 s, do not replace the Grok skills install. The safety label does not stop the copy.
3. Evidence. Met. The probe exited 0 offline on the pinned tarball.
4. Blast radius. Met. MIT, no weights, no account, cache path, repo copy is text. The prefix is over the I2 size bar and under a multi-GB weight.

Modularity gate, all four hold, and I2 still does not.

1. Local CLI needed. Met. The skipped markdown and the non-blocking copy are runtime behavior. The README text that shows a local-path audit does not match this binary.
2. Bounded surface. Met. One `asm` binary.
3. Isolatable. Met. Cache path with `HOME` redirected and `-s project`. It is not the product runtime.
4. Reversible. Met. Deleting the cache directory leaves the entry, the card, and this report.

I2 is for ambiguous potential plus a copy under 50 MB. Potential is low after this probe. The prefix is 58,625,143 logical bytes. Stay I1.

## Risks

| Risk | How it fails | How we recover |
|------|----------------|----------------|
| `--yes` copies a high-risk skill | Exit 0, `success: true`, SKILL.md present, 4/4 tokens still in the file | Keep SkillSpector in front of any copy. Do not treat the preview label as a block. |
| `audit security` skips markdown | 0 files, verdict safe, exit 0, on a planted SKILL.md | Treat that verdict as unread. The H2 check stays `scripts/pfy_skill_scan.py`. |
| Local path is a name lookup | `audit security <directory>` exits 1 and scans nothing | The command audits an installed directory name, which means the copy already happened. |
| Receipt says github | `resolutionSource` is `github` for a local folder | Do not use that field as provenance. |
| Version string drift | package 2.24.0, binary prints 2.23.0 (6cb9272) | Pin the tarball sha256. Re-check the printed version when the pin moves. |
| Real home | Global scope expands `~` through the home directory. An unset redirect writes provider dirs in the real home | This probe set `HOME` under the cache and used `-s project`. The four watched paths were unchanged. |
| `asm doctor` calls the registry | Setup doctor reported the registry reachable | Leave doctor out of an offline run. |
| Over the I2 size bar | Prefix logical size 58,625,143 bytes | Keep the install in the cache. Do not copy it into the repo. |
| Early onboard | Treating 3/3 category labels as a product gate | Stay I1 until a later pin refuses the copy and beats SkillSpector. |

## Next gate

Stay I1. A later pin has to make `asm install --yes` leave the high-risk SKILL.md out of the provider directory, and `audit security` has to read that file. It still has to beat SkillSpector on a planted skill from this repo. No pregate, CI, or other gate wiring in this lane. No Feature GO.

## Five questions (this tool in the pipeline)

1. What triggers it? A person, or a later installer, runs `asm install` or `asm audit security` on a fetched skill. This lane adds no trigger.
2. What does it do, and which services does it read and write? It reads the pinned CLI and a local skill directory. With `-s project` it writes `.grok/skills` or `.opencode/skills` under the working directory, plus config under the redirected home. The probe did not call the registry. No hosted model, no account, no key.
3. What does it trigger next? Nothing in this lane. A copy that already landed would still need SkillSpector before it is treated as a skill. That handoff is not built.
4. Where does a human re-enter? When the preview says High Risk. `--yes` still copies, so a person has to refuse the file. Mark's GO would be required before any copy into a real skills directory.
5. What stops two runs doing the same work? This lane is one worktree and one branch. The probe deletes its temp project before it starts. Two concurrent `asm` installs were not measured. The tool's lock file was not part of the score.
