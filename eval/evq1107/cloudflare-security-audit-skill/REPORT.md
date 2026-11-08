# Cloudflare security-audit skill evq1107

## Catalog tools on this job

The job is gap H2 from the 2026-11-07 ranking: skill and tool discovery has no install gate. The discovery drop-in keeps fetched skills as data because nothing checks them before they load. Entry 127 is a six-phase source-audit skill whose offline piece is schema-checked `findings.json`. It is outside the 137-167 re-rank table. The H2 row in that table is SkillSpector. Searched `data/stages/*.json` uses, features, and tags, plus `docs/eval/TOOLSET-RANKING.md` (2026-11-07 and the 2026-10-06 table). Batch-1 notes under `eval/ev1107/` and `eval/catchup-1107/` matter where they already measured this job. This lane builds no pipeline, CI, or gate step.

| Tool | Stage | What that card covers | How this skill compares |
|------|-------|----------------------|-------------------------|
| SkillSpector | I3 | Static scan before a skill directory is copied. Catch-up: 57 directories in 38.44 s, one real `shell=True` hit. `scripts/pfy_skill_scan.py` is the advisory wrapper. | Reads the skill text. This probe fed the same token. Both skill files failed as invalid JSON, and two findings receipts still passed. |
| Sandlock | I2 | Rootless confinement of one fetched-skill install command. Probe: 4/4 escapes blocked, stage write landed. | Confines the process. This validator never wraps an installer. |
| cedr | I1 | Pin skill directories, then fail when those files change. Trial: 43 skills, one-line edit caught. The report says that lint is not the H2 gate. | Hashes skill bytes. Passed a `SKILL.md`, this validator stops at invalid JSON and does not hash the skill text. |
| runx | I0 | Seals a receipt for one skill run. Install-gate refuses were 0/4. | A receipt can seal a bad skill. An empty `findings.json` here also passes. |
| asm (agent-skill-manager) | I1 | Cross-agent skill installer, with a skill audit feature. | The feature is named. This probe's validator is a findings schema, not that audit. |
| OpenCode Skill Creator | I0 | Frontmatter lint. The card says it is not a security scan. | Checks skill frontmatter. This probe's clean and planted files get the same JSON error. |
| OpenQodex | I1 | Scanner hits on a diff, then a check that a finding cites a scanner token. Default finalize exits 0 on major findings. | Looks at changed lines. This validator accepted a confirmed record whose file is absent. |
| agentgg | I0 | Local SAST on a diff. Caught planted `shell=True` in code, missed a secret in a log. Needs a local model. | A model scan of a diff. This lane used no model. The schema gate did not name `shell=True`. |
| CodeGuard | I0 | Secure-coding rule text for a host agent. Prefix pass caught 1 of 3 planted defects, 0 of 2 agentgg plants, and 0 hits on a fetched-skill fixture. The card says it is not an install gate. | No findings schema and no install-gate command. This probe also left `shell=True` in place. |
| write-guard-mcp | I3 | Write mediation above the cage mount. | A runtime guard. It does not read a skill or a findings file. |
| destructive_command_guard | I1 | Blocks destructive shell commands. Overlaps write-guard. | Matches command text. The planted line is a string in a fixture. |
| Bumblebee | I2 | Advisory lockfile and MCP config scan. | Other files. |
| agent-cage (PNNL) | I3 | Isolated lab for Grok. | The lab boundary. The validators are one Node process. |
| Grok CLI bootstrap | I3 | Operator skills install for the skills we already keep. | Installs a trusted tree. |
| repository-harness | I0 | Installs a repository map and four skills beside an existing AGENTS.md. Probe: the new map named 0 of 6 authority paths. | Installs a known pack. It does not scan a fetched skill. |
| Skills Manager | I0 | Skill distribution CLI. | Distribution only. |
| mattpocock/skills | I1 | Planning and review skills already on the path. | The review skill is the reviewer. Full audit mode was not run. |
| gstack | I1 | Role patterns already ported in docs. The card says not to clone the repo. | Docs only. |

skill-up is I3 on gap H1 (with-skill versus baseline). It does not scan an install.

Beats what we have: no.

## Verdict

STAY I0. The schema gate blocked 0 of 1 planted `shell=True` lines. Two passing receipts leave that line in the fixture. Upstream validator tests were 65/65 in 0.5072 s. Full audit mode is SKIPPED. Nothing is wired into a gate.

`STAY I0 0/1 planted shell=True lines blocked, 2 passing receipts leave the line, upstream validators 65/65`

## Pin

Host is linux x86_64. Node v22.23.0. No account, no key, no hosted call. License MIT. The entry names commit `c1c8a8c14710` (2026-09-14). The full hash is `c1c8a8c1471069fb0e188eeaff69b8e8db6564a8`, subject "Clarify guidance and full audit modes", commit time 2026-09-14 20:28:54 +0100. Tree `8cd03bb3941496e441d6248aaae2429a35b93cc3`. A `git fetch --depth 1 origin c1c8a8c14710` failed (`couldn't find remote ref`). Depth 50 from `origin` includes that commit, and it is the tip of that fetch. The GitHub API `pushed_at` for the repo was `2026-09-14T19:29:02Z`. The entry's star count from 2026-10-17 was about 30641. The same API read reported `stargazers_count` 65868. The verdict does not use the star count.

Checked-out files, `.git` excluded: 322698 bytes. Cache directory, `.git` included: 477651 bytes. Both are under the 50 MB I2 copy bar. No upstream tree is committed.

```bash
BASE=/home/mark/.cache/pfy/tools/cloudflare-security-audit-skill
mkdir -p "$BASE/home" "$BASE/config" "$BASE/cache" "$BASE/tmp" "$BASE/npm"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/config" XDG_CACHE_HOME="$BASE/cache" TMPDIR="$BASE/tmp" npm_config_cache="$BASE/npm"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
git clone --filter=blob:none --no-checkout https://github.com/cloudflare/security-audit-skill.git "$BASE/src"
git -C "$BASE/src" fetch --depth 50 origin
git -C "$BASE/src" checkout --detach c1c8a8c1471069fb0e188eeaff69b8e8db6564a8
```

| File | sha256 |
|------|--------|
| `skills/security-audit/validate-findings.cjs` | `e85f232e36bfac0f866f244da50376692d6b45c690beadcb00608b0e6c8b5283` |
| `skills/security-audit/validate-coverage-ledger.cjs` | `2eb280bd2e33c002916f86db9b29f9edfedb6454e5db973c766290465b868ac8` |
| `skills/security-audit/report-schema.json` | `6575c9de4a62255699ea052ebf9a49ebfb373a32891bcd89af6f55cc84b35519` |

The probe refuses to score if `HEAD`, the tree, or any of those three hashes move.

## Probe

`python3 eval/evq1107/cloudflare-security-audit-skill/probe.py` from this worktree. Exit 0. Numbers are `eval/evq1107/cloudflare-security-audit-skill/results.json`. The Node child sees only `PATH`, `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `TMPDIR`, `npm_config_cache`, `LANG`, and `GIT_CONFIG_GLOBAL` / `GIT_CONFIG_SYSTEM` set to `/dev/null`. Those homes are under the cache directory. Findings fixtures are written in a temp directory there and removed. The two skill fixtures stay in this eval directory.

Upstream command, cwd `skills/security-audit`, same child env:

```bash
node --test --test-reporter=tap validate-findings.test.cjs validate-coverage-ledger.test.cjs
```

Exit 0. TAP summary: tests 65, pass 65, fail 0, skipped 0. Wall 0.5072 s. Node `duration_ms` 487.257084. The entry's Grok Bot box run was also 65/65, on Node 20.19.2. This run is Node 22.23.0.

Full audit mode is SKIPPED. The skill's own text says that mode needs a parent agent and isolated sub-agents, and an OS sandbox before any target execution. This lane does not call a model and does not start those agents. Guidance mode is prompt text, so the runnable offline check is the two validators.

H2 cases use `validate-findings.cjs` only. Group wall 0.1679 s. The planted line is fixture line 10: `subprocess.run("echo h2-probe", shell=True)`. The clean fixture has zero copies of that token. The probe does not run either fixture.

A case counts as blocking the hazard only when its output names `shell=True` and the exit is non-zero. Invalid JSON is a different failure, and both skill files hit it.

| Case | Exit | What the validator said |
|------|-----:|-------------------------|
| planted `SKILL.md` | 1 | `invalid JSON syntax` |
| clean `SKILL.md` | 1 | `invalid JSON syntax` |
| planted skill directory | 1 | `input must be a regular file` |
| `[]` | 0 | `PASS: 0 findings valid` |
| rejected record whose reason says line 10 is a comment | 0 | `PASS: 1 findings valid` |
| `[{}]` | 1 | `must match exactly one schema` |
| file `../outside.py` | 1 | `must be a safe repository-relative source path` |
| confirmed record citing `fixtures/missing-source.py` | 0 | `PASS: 1 findings valid` |
| confirmed record citing line 10, claiming the process ran | 0 | `PASS: 1 findings valid` |

`fixtures/missing-source.py` is not on disk. Line 10 is still the `shell=True` call after the passing receipts. Skill files separated by exit code: 0 of 2. Hazards blocked: 0 of 1. Malformed receipts rejected: 2 of 2. The path check is real. It does not read the skill.

## Gates

Value gate, 2 of 4. I3 needs 3. I2 needs a probe that helps.

1. Gap fill. Not met. SkillSpector already flags `shell=True` before a copy. cedr hashes skill bytes. Sandlock confines the installer. This schema accepts an empty findings file and a rejected record that denies the planted line.
2. Operator leverage. Not met for H2. One `node` command checks findings shape. It does not decide whether a fetched skill may load. Full audit mode was not run.
3. Evidence. Met. The probe exited 0 and the pinned tests were 65/65.
4. Blast radius. Met. MIT, no weights, no account, cache path, repo copy is text, 477651 bytes of files under the cache.

Modularity gate, all four hold, and that still does not promote.

1. Local code needed. Met. The README describes a source trace on `confirmed` records. The validator accepts a `confirmed` record whose file is absent.
2. Bounded surface. Met. Two Node validators plus `report-schema.json`.
3. Isolatable. Met. Cache path. It is not the product runtime.
4. Reversible. Met. Deleting the cache directory leaves the entry, the card, and this report.

Potential is low. The H2 result is measured, so I2's ambiguity case does not apply. The copy is under 50 MB, and the size bar is not the reason for STAY.

## Risks

| Risk | How it fails | How we recover |
|------|----------------|----------------|
| PASS treated as a skill clear | `[]` exits 0, and a rejected record exits 0 while line 10 still contains `shell=True` | Keep `scripts/pfy_skill_scan.py` as the H2 check. A findings PASS is not a copy decision. |
| False confirmed record | A `confirmed` record for a missing path exits 0, and so does a record that claims the fixture process ran | Open the cited path in a later checker. This lane does not treat `confirmed` as a gate. |
| Same error for clean and planted skills | Both `SKILL.md` files exit 1 with `invalid JSON syntax` | Score content with SkillSpector. This exit only means the file is not `findings.json`. |
| Full audit cost | The skill text calls for many isolated agents | Leave full mode SKIPPED until a later ticket has a parent agent and a sandbox. Guidance text can be read without installing the skill into a live skills directory. |
| `npx skills add` | The upstream install command writes host skill directories | Do not run it. The cache checkout is the only copy. |
| Pin drift | A newer commit changes the schema | The probe checks the commit, the tree, and the three file hashes. Re-run the two test files on the new pin. |
| Unsafe path accepted by mistake | `../outside.py` was rejected here | Keep that case in the probe. A pass on it means the path check regressed. |

## Next gate

Stay I0. A later probe has to reject a findings file that denies a planted skill hazard, or open the cited path and fail when the file is missing. Full audit mode still needs isolated sub-agents, and it is not the install gate. No pregate, CI, or other gate wiring in this lane.

## Five questions (this tool in the pipeline)

1. What triggers it? A person asks for a source audit, or a later command runs `node validate-findings.cjs` on a `findings.json`. This lane adds no trigger.
2. What does it do, and which services does it read and write? It reads `findings.json` and `report-schema.json`. It writes a pass or fail line to the terminal. Full audit mode would also write run files outside the target repo. This lane did not do that. No hosted model, no account, no key.
3. What does it trigger next? Nothing in this lane. A copy into a skills directory still waits on the SkillSpector advisory scan. That handoff is not built here.
4. Where does a human re-enter? Before any copy of a fetched skill, and before a `confirmed` record is treated as a defect. The validator output is not that decision.
5. What stops two runs doing the same work? The validator does not write the cache checkout. Full audit outputs go to a per-run directory. This lane is one worktree and does not take the model lock.
