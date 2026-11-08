# ponytail skills pack evq1107

STAY I1. smoke-grok-skills asserts 0 of 6 skills. The pack has 0 commands that refuse a fetched skill. The vendored snapshot matches the pin on 6 of 6 files. Value gate is 2 of 4. This does not beat SkillSpector on H2.

`STAY I1 smoke-grok-skills asserts 0 of 6 skills, 0 install-gate commands, pin matches 6 of 6`

## Catalog overlap

Same job: H2, a check before a fetched skill is loaded. Also the YAGNI prompt job this pack already fills. Searched `data/stages/*.json` uses, features, and tags, plus `docs/eval/TOOLSET-RANKING.md` (2026-11-07 section and the 2026-10-06 table) and the batch results under `eval/ev1107/` and `eval/catchup-1107/`. This lane builds no pipeline, CI, or gate step.

There is no `sources/entries` file for this slug. The pin is the `pinned_commit` already in `bootstrap/grok-cli/manifest.json`. The 2026-11-07 ranking assigns H2 to SkillSpector (entry 148). This pack is not in entries 137 to 167. The 2026-10-06 section already lists it as on `skills.paths`.

| Tool | Stage | What that card covers | How this pack compares |
| --- | --- | --- | --- |
| SkillSpector | I3 | Static scan of a skill directory before copy. Catch-up trial: 57 directories in 38.44 s. The wrapper exits 0 only for SAFE. | The H2 check already on disk. This pack has 0 gate fences and 0 refusal checks. It does not beat that scan. |
| skill-up | I3 | Grade a with-skill run against a no-skill baseline. Catch-up trial was 5/5 on both arms, delta 0. | Closes H1, not H2. This lane did not run a model bake-off. |
| karpathy-guidelines | I1 | One coding-behavior skill already in the skill tree. | Same kind of prompt, already installed. This pack adds no install check. |
| cedr | I1 | Pin skill directories and fail when those files change. | A hash pin. smoke-grok-skills does not hash these six files. |
| Sandlock | I2 | Rootless confinement of one fetched-skill install command. | Wraps an installer. This pack does not. |
| Bumblebee | I2 | Advisory read-only check for package lockfiles and MCP host configs. | Different files. |
| write-guard-mcp | I3 | First-party write mediation above the cage mount. | A runtime guard. It does not scan a skill tree. |
| destructive_command_guard | I2 | Classifies one shell command and denies destructive git and filesystem commands. That probe does not close H2. | A shell guard, not a skill scan. |
| CodeGuard | I0 | Rule text. The probe found no install-gate command. | Same shape of negative result. |
| Cloudflare security-audit skill | I0 | Schema check. The probe blocked 0 of 1 planted skill lines. | This pack also has no checker to block a planted skill. |
| trailofbits-skills | I0 | Security checklists an agent can read. Not an install gate. | Text for an agent. Not a gate. |
| anti-slop | I0 | Prompt pack. Not a scanner. | Same shape, different words. |
| asm (agent-skill-manager) | I1 | Cross-agent skill installer. The card says we already install Grok skills ourselves. | This pack is already registered via `skills.paths`. |
| Skills Manager | I0 | Skill distribution CLI. The card says our tree stays the source. | Does not replace the snapshot. |

Beats what we have: no.

## Pins

| Piece | Value |
| --- | --- |
| Repo | https://github.com/DietrichGebert/ponytail |
| Commit | `8e69b4a55f735e1319999064f82786b838cb3d7b` |
| Date | 2026-07-09T04:15:43+02:00 |
| Subject | report active level on bare /ponytail instead of resetting to default |
| Catalog prefix | TOOLS.md says `8e69b4a`. `git rev-parse HEAD` matched the full manifest pin. No separate file checksum was given. |
| Package | `@dietrichgebert/ponytail` 4.8.4 at that commit |
| License | MIT (`LICENSE`) |
| Snapshot | `bootstrap/grok-cli/skills-external/ponytail/` is `skills/` only |
| Skills bytes | 17214 |
| Pin tree, no `.git` | 1596339 bytes (under the 50 MB I2 size cap) |
| Cache | `~/.cache/pfy/tools/ponytail-skills-pack/src` |
| Skill sha256 | in `results.json` |

The six `SKILL.md` files are byte-identical to the pin. 0 only on one side. 0 differ.

## Commands

Clone, first attempt, no account and no key. `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `TMPDIR`, `npm_config_cache`, and `GIT_CONFIG_GLOBAL` were under the cache. `GIT_CONFIG_SYSTEM=/dev/null`.

```bash
BASE=/home/mark/.cache/pfy/tools/ponytail-skills-pack
mkdir -p "$BASE/home" "$BASE/xdg-config" "$BASE/xdg-cache" "$BASE/tmp" "$BASE/npm" "$BASE/src"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/xdg-config" \
  XDG_CACHE_HOME="$BASE/xdg-cache" TMPDIR="$BASE/tmp" \
  npm_config_cache="$BASE/npm" GIT_CONFIG_GLOBAL="$BASE/home/.gitconfig" \
  GIT_CONFIG_SYSTEM=/dev/null GIT_TERMINAL_PROMPT=0
git -C "$BASE/src" init
git -C "$BASE/src" remote add origin https://github.com/DietrichGebert/ponytail.git
git -C "$BASE/src" fetch --depth 1 origin 8e69b4a55f735e1319999064f82786b838cb3d7b
git -C "$BASE/src" checkout --detach FETCH_HEAD
```

The probe uses `Path.home()` to find the cache, so it ran with the real `HOME`. It does not write there.

```bash
python3 eval/evq1107/ponytail-skills-pack/probe.py
```

Exit 0. Probe clock 0.0579 s. `verify_skills.py` (the body of `make smoke-grok-skills`, without `--installed`) clock 0.037 s, exit 0. No model lock. `ollama` was not called. The probe read the pin `LICENSE` first line (`MIT License`) instead of assuming the license.

`bootstrap/grok-cli/install.sh` was not run. Its verify step merges the real Grok config. That script prints `OK ponytail snapshot` when `ponytail/SKILL.md` exists. That is one file, and it is not `smoke-grok-skills`.

## What was skipped

| Part | Reason |
| --- | --- |
| Upstream `npm test` | `package.json` runs node tests, then nested npm tests for the Pi extension and the MCP server. That does not scan a fetched skill. No node modules were installed. |
| Hooks and the MCP server | `hooks/ponytail-activate.js` writes a session flag and emits the ruleset. It does not scan a third-party skill. Not started. The hooks are not in the vendored snapshot. |
| Benchmarks | Prompt and model runs. This lane does not call a model. Not started. |

## Probe

`results.json` holds the counts.

| Check | Result |
| --- | --- |
| smoke OK lines that name one of the six skills | 0 of 6 |
| `run_structural.py` paths that name one of the six | 1 of 6 (`ponytail/SKILL.md` exists). Existence only. |
| `gate_paths_pack` on this repo | pass, `claude-unified-agents=16, mattpocock=8, ponytail=6` |
| Same function, temp tree, ponytail directory absent, 10 claude skills | pass, detail contains `missing ponytail` |
| Same function, 9 claude skills | fail, `claude-unified-agents degraded` |
| Shell fences that exit on a skill | 0 |
| Phrase hits (`do not install`, `install gate`, `before it is copied`, and the two close variants) | 0 |
| Frontmatter name matches the directory, description key present | 6 of 6 |
| Executable or shebang skill files | 0 |
| Host-install lines inside the six files | 1, in `ponytail-help`. It names a global npm install and a brew upgrade for Claude Code. It is not a skill scan. |
| Refusal checks in upstream `register()` before `register_skill` | 0. The only `if` in that loop is `is_dir` and `exists`. |

`make smoke-grok-skills` runs `bootstrap/grok-cli/scripts/verify_skills.py`. That script walks `first_party_skills` only. The six names live under `external_skills.ponytail`. A passing smoke does not mean this pack loaded.

`scripts/eval_integration_change.py` `gate_paths_pack` counts `*/SKILL.md` and returns false only when the claude pack is present and under 10 skills. Deleting this pack does not fail that count. The old committed line `ponytail=6` in `pipelines/eval/integration-change.latest.md` is a count, not a load assertion. This run's live detail is `ponytail=6` with `mattpocock=8` (that artifact said `mattpocock=3`).

## Tests

`python3 -m unittest tests.test_ponytail_skills_pack_probe`

The loose-mention test runs the probe against a stub executable. The stub prints `note: ponytail not in this smoke` and `OK source adr`. The count stays 0. The recover stub prints `OK source ponytail` and the count is 1.

The paths-count test runs `--s7-fixture`. A missing ponytail directory still passes. A claude pack of 9 skills fails.

`RED: count any line that contains a pack name (drop the OK-line match in asserted_names) -> tests.test_ponytail_skills_pack_probe.PonytailPackProbeTests.test_loose_mention_is_not_a_load_assertion`

`RED: treat a missing ponytail directory as a paths-pack failure (invert missing_ok in --s7-fixture) -> tests.test_ponytail_skills_pack_probe.PonytailPackProbeTests.test_missing_pack_does_not_fail_the_paths_count`

Both mutants were restored. The tests pass again. The mutants are not committed.

## Verdict against the gates

Value gate for I3 needs 3 of 4.

| Gate | Met | Why |
| --- | --- | --- |
| Gap fill | no | H2 is already SkillSpector's job. This pack does not check a fetched skill. karpathy-guidelines already covers the "write less" prompt. |
| Operator leverage | no | The snapshot is already on `skills.paths`. This probe adds no command that closes H2. |
| Evidence | yes | Pin checkout, 6 of 6 hashes, smoke run, repeatable probe. |
| Blast radius | yes | MIT. `skills/` is 17214 bytes. No weights. Hooks and MCP were not installed. |

2 of 4. Not I3.

Modularity gate for a local copy is all 4: the smoke behavior is not visible from the upstream README alone, the surface is six files, the checkout sits in the cache, and deleting the cache leaves the manifest pin. I2 is for ambiguous potential plus a lightweight copy. Potential as a coding prompt is already high, and the H2 answer is now clear: it does not close the gap. The rubric sends that back to I1. `tier_ceiling` stays I1. Stage stays I1.

No `self_pipeline` field. The card uses and features do not cover CI, testing, or review, so the check does not require one below I3.

## Risks

- A later reader treats `ponytail=6` or `OK ponytail snapshot` as proof the smoke loads the pack. How it fails: delete the directory and `gate_paths_pack` still returns true, and `verify_skills.py` still exits 0. How we recover: stay at I1 until `verify_skills.py` fails when one of the six is missing or its frontmatter breaks. That change is a separate ticket. This lane does not edit the smoke.
- The upstream `register()` loads every `SKILL.md` under `skills/` once the file exists. How it fails: a fetched skill dropped beside the pack would be registered, with 0 refusal checks. How we recover: do not install `__init__.py` or the hooks. Fetched skills stay out of a skills dir until SkillSpector exits 0, which is already the rule in `docs/ops/skill-scan.md`.
- The vendored file drifts from the pin. How it fails: `run_structural.py` only checks that `ponytail/SKILL.md` exists (1 of 6). The other five can change and that check still passes. How we recover: re-run this probe. `byte_differ` must stay empty. Not a gate.
- `ponytail-help` names a global install for Claude Code. How it fails: an agent follows that line and mutates a host toolchain. How we recover: this probe does not run that line. Do not install the upstream hooks. No new wiring.
- The refusal counter ignores an `if` that also contains `exists` or `is_dir`. How it fails: a refusal glued onto that same line would still count as 0. How we recover: the current line is only the directory and file check, read at this pin. A later pin that adds a real refusal should fail a re-read of that loop, not a silent promote.

## Next gate

Stay I1. I3 stays closed until `smoke-grok-skills` fails when one of the six skills is missing or its frontmatter breaks. H2 stays with SkillSpector. No gate wiring and no Feature GO from this lane.

## Five questions (this tool in the pipeline)

1. What triggers it? Grok scans `skills.paths` when a session starts, or a person invokes the pack. No CI job calls it. `smoke-grok-skills` does not.
2. What does it do, and which services does it read and write? The six files are prompt text. They read nothing on their own. They write nothing. The upstream hooks would write a flag under the Claude config dir. Those hooks are not in the snapshot this repo loads.
3. What does it trigger next? The agent prefers a smaller diff. The pack starts no scan, no smoke, and no second tool.
4. Where does a human re-enter? The person reads the diff, or tells the agent to stop. The pack has no approval step.
5. What stops two runs doing the same work? Nothing in the pack. Two sessions can load the same six files. That is harmless: the files take no lock and write no receipt.
