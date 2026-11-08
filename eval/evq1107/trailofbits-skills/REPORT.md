# trailofbits-skills evq1107

STAY I0. The install check blocked 4 of 7 skills the entry would copy (exit 1, 30.088s). `--allow-caution` still exited 1 because sharp-edges is DO_NOT_INSTALL. differential-review on one risky diff in this repo found 0 new defects. The pack does not beat SkillSpector at the install gate, and it does not beat the review skill or the existing behavior test on that diff.

`STAY I0 4 of 7 candidate skills blocked by the install check, 0 new defects on the risky diff`

## Catalog overlap

The job is two parts: an install check before a fetched skill is copied (gap H2), and a security pass over a risky diff. Searched `data/stages/*.json` uses, features, and tags, plus `docs/eval/TOOLSET-RANKING.md` (2026-11-07 section and the 2026-10-06 table) and the batch-1 verdicts under `eval/ev1107/` and `eval/catchup-1107/`. This lane builds no pipeline, CI, or gate step.

| Tool | Stage | Why it covers this job | How trailofbits-skills compares |
| --- | --- | --- | --- |
| SkillSpector | I3 | Static scan of a skill directory before copy. Catch-up: 57 directories in 38.44s, advisory, not in pregate. | This probe is that scan, pointed at the pack. The pack does not scan itself. 4 of 7 candidates fail the copy rule. |
| Sandlock | I2 | Rootless confinement of one fetched-skill install command. | Confines a process. These files are markdown. No install command was wrapped. |
| cedr | I1 | Pin skill directories and fail when those files change. | A hash pin. It does not judge skill content. |
| asm (agent-skill-manager) | I1 | Cross-agent skill installer with a skill audit feature. | An installer. This pack is the payload, and the audit here was SkillSpector. |
| Skills Manager | I0 | Skill distribution CLI. | Distribution only. Not run. |
| OpenCode Skill Creator | I0 | Frontmatter lint. Not a security scan. | All 7 names match their folders. That lint would not see the DO_NOT_INSTALL result. |
| Grok CLI bootstrap | I3 | Operator install of trusted skills. | Installs skills we already trust. It is not a check for this fetched pack. |
| Bumblebee | I2 | Advisory read of package lockfiles and MCP configs. | Different files. |
| write-guard-mcp | I3 | Write mediation above the cage mount. | A runtime guard. It does not read a skill pack or a diff. |
| destructive_command_guard | I1 | Blocks destructive shell commands. Overlaps write-guard. | A shell guard, not a skill scan and not a diff checklist. |
| mattpocock/skills | I1 | Planning and review skills already on the path. Tag `#review`. | The review skill is already the reviewer. differential-review added 0 defects on the diff below. |
| agentgg | I0 | Local SAST on a deploy, release, or secrets diff. Needs a local model. | This diff has no planted shell or secret line. agentgg was not re-run. The checklist needed no model. |
| OpenQodex | I1 | Scanner candidates on changed lines. STAY I1, 2 of 3 planted lines. | Those scanners were not needed. The changed lines are cleanup and a test. |

Gap H2 in the 2026-11-07 ranking is the missing install check. SkillSpector is already that check. This pack is fetched content the check refuses as a bundle.

Beats what we have: no.

## Pins

| Piece | Value |
| --- | --- |
| Repo | https://github.com/trailofbits/skills |
| Commit | `5c99c03fb8a9ea568432ecbcba5d86e9f4ac2bf0` (entry short sha `5c99c03fb8a9`) |
| Tree | `0d0c608ca7c7fe1c174c72f200c95c454fd24f83` |
| Date | 2026-10-15T18:16:40Z |
| Subject | fix(devcontainer-setup): pin fnm instead of installing its latest release (#346) |
| License | CC-BY-SA-4.0 (`LICENSE` at the repo root) |
| Plugins | 44, from `.claude-plugin/marketplace.json` |
| SKILL.md | 85 |
| Working tree | 8882282 bytes (`du -sb --exclude=.git`). Under the 50 MB bar. No weights. |
| Seven skill dirs | 341841 bytes |
| SkillSpector | v2.12.0, pin `e7172462caf367736645f66c1aa154ca5f9c64dc`, already at `~/.cache/pfy/tools/skillspector/`. Not reinstalled. |
| Account | none |

A fetch of the short sha failed (`couldn't find remote ref`). The full sha from the GitHub commits API matched the entry date and fetched cleanly. No checksum was in the entry. The pin checked here is the full commit and the tree.

Frontmatter `name` equals the folder for all 7. Description lengths are 179 to 845 characters, which matches the entry. Body bytes are 3291 to 14310. The entry's 3.9 to 11.8 KB body range does not match this pin: variant-analysis is 3291 bytes and atheris is 14310.

The snapshot stays in the cache. It is not committed. CC-BY-SA-4.0 would apply to a snapshot committed in this repo.

## Commands

Install and both scans used `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` under `~/.cache/pfy/tools/trailofbits-skills/`. Git config files were pointed at `/dev/null`. The scans ran inside `bwrap --unshare-net`. No model lock. `ollama` was not called.

```bash
BASE=/home/mark/.cache/pfy/tools/trailofbits-skills
mkdir -p "$BASE/home" "$BASE/xdg-config" "$BASE/xdg-cache" "$BASE/tmp"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/xdg-config" \
  XDG_CACHE_HOME="$BASE/xdg-cache" TMPDIR="$BASE/tmp" \
  GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
git clone --filter=blob:none --no-checkout https://github.com/trailofbits/skills.git "$BASE/src"
git -C "$BASE/src" fetch --depth 1 origin 5c99c03fb8a9ea568432ecbcba5d86e9f4ac2bf0
git -C "$BASE/src" checkout --detach FETCH_HEAD
```

`git rev-parse HEAD` printed `5c99c03fb8a9ea568432ecbcba5d86e9f4ac2bf0`.

The gate command is `scripts/pfy_skill_scan.py` (static mode, `--no-llm` inside the wrapper) on the seven directories named in the entry, with `PFY_SKILLSPECTOR_BIN` set to the cached SkillSpector. Provider env vars are dropped by the wrapper. The receipt is not committed: it holds short scanner titles that quote the skill text. Counts are in `results.json`.

Default run: exit 1, verdict FLAGGED, wall 30.088s, wrapper `llm` false, scratch directory removed. The wrapper deletes the raw reports. One raw report, for differential-review, had `llm_requested` false. All seven ran with the network namespace closed.

| Skill | Recommendation | Score | Findings |
| --- | --- | ---: | ---: |
| property-based-testing | SAFE | 0 | 0 |
| semgrep-rule-creator | CAUTION | 38 | 2 |
| variant-analysis | SAFE | 0 | 0 |
| sharp-edges | DO_NOT_INSTALL | 100 | 46 |
| differential-review | SAFE | 7 | 1 |
| fp-check | CAUTION | 13 | 4 |
| atheris | CAUTION | 28 | 8 |

3 SAFE, 3 CAUTION, 1 DO_NOT_INSTALL. The H2 copy rule is exit 0, so 4 of 7 are blocked and the bundle cannot be copied.

Same command with `--allow-caution`: exit 1, wall 29.508s. CAUTION rows became ok. sharp-edges stayed DO_NOT_INSTALL, so the override does not recover that skill.

Triage of the blocked rows, from the lines the receipt named. These are examples and instructional phrases, the same class as the catch-up false positives, not a separate malware payload:

- semgrep-rule-creator: a fenced rule fixture that shows a dangerous eval, and a pitfall line about patterns without constraints.
- sharp-edges: 34 HIGH, 10 MEDIUM, 1 CRITICAL, 1 LOW. The critical hit is a fenced PHP example of a removed language feature, with a fix line under it. Other hits are detection phrases ("disable security") and partial links to language notes.
- fp-check: a when-not-to-use line and a list of false-positive mistakes.
- atheris: a Dockerfile how-to (sanitizer preload, apt list cleanup, docker run).
- differential-review stayed SAFE. Its one MEDIUM hit is a pattern heading about unchecked calls.

The other 78 skills in the pack were not scanned. The entry says not to port them.

## Probe

Skill tried: `plugins/differential-review/skills/differential-review`. The deep path names a Claude subagent. That agent was not dispatched. The countable phases were run as git commands on commit `a81ffba49a85d6c42b431106007a9668f55d7766` (delete raw scanner JSON when the receipt write fails). That commit is the failure path of the install-gate script. 434 Python files at that commit, so the skill's size table says LARGE and the strategy is SURGICAL. Mechanical checks took 0.371s.

| File | Risk | Why |
| --- | --- | --- |
| scripts/pfy_skill_scan.py | HIGH | Failure path of the install check |
| tests/test_pfy_skill_scan.py | LOW | Test. Read for coverage only |
| docs/ops/skill-scan.md | LOW | Docs |
| eval/catchup-1107/skillspector/REPORT.md | LOW | Docs |

Red flags from the skill, 0 of 5 fired:

| Check | Result |
| --- | --- |
| Removed code comes from a security, CVE, or fix commit | No. `git log -S` on the removed cleanup names only `3ba4dec` ("advisory static scan and I3 card"). Blame on the parent is that commit. The cleanup moved into `finally`. |
| Access-control modifier removed | 0 lines |
| Validation removed (`require`, `assert`, `revert`) | 0 lines. The `is_safe` call moved with the function. It was not dropped. |
| New external call | 0 subprocess, socket, or Solidity call lines |
| 50 or more callers on a HIGH change | `_clear_scratch` and `_scan_paths` each have 1 call site. Band LOW (1 to 5). |

The skill's arithmetic grep (`+`, `-`, `*`, `/`) matched 20 changed lines. Each match is a hyphen or a slash in a name or a path. None is an arithmetic update.

Phase 2: one new test, `test_unwritable_receipt_still_drops_raw_report`. A grep for the private name `_clear_scratch` in tests is 0. The test drives the script and checks that the scratch directory is gone. The skill's name grep would call the new function untested. That elevation would be wrong.

Attack scenario the skill asks for: point `--out` at a directory so the receipt write fails, and leave the raw scanner JSON on disk. After this commit the `finally` path deletes it. The new test locks that. The scenario does not succeed. New defects: 0.

The existing test already said the same thing. The checklist did not add a finding.

## Gates

Value (need 3 of 4 for I3):

| Check | Result |
| --- | --- |
| Gap fill | No. H2 is SkillSpector. The review skill is already on the path. This pack is content the gate blocks as a bundle. |
| Operator leverage | No. A 30s refusal, and 0 new defects on the diff. No glue in this lane changes the install rule or the review. |
| Evidence | Yes. The commands above ran. |
| Blast radius | Yes for a cache pin. 8.88 MB, no weights, no account, not the product runtime. A committed copy would be CC-BY-SA redistribution, so the files stay in the cache. |

2 of 4. Not I3.

Modularity (all 4 for I2 local code and for I3):

| Check | Result |
| --- | --- |
| Local code needed | Yes. The DO_NOT_INSTALL score is not in the README. |
| Bounded surface | No. The published unit is 44 plugins and 85 skills. The entry already skips most of them. There is no single CLI. |
| Isolatable | Yes. The cache copy is not the product runtime. |
| Reversible | Yes. Deleting the cache leaves the pin and this entry. |

3 of 4. I2 is not met. Potential is low, not ambiguous, so the I2 shelf does not apply anyway. Nothing was wired into a gate. `self_pipeline` is `not_applicable`.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Copy the bundle because 3 skills are SAFE | The wrapper on all 7 exits 1. sharp-edges is DO_NOT_INSTALL. | Copy nothing from this pack. `--allow-caution` was measured and still exits 1. |
| Treat scanner titles as proof of malware | The blocked lines read here are examples and detection phrases. A real payload would look the same to the scanner. | Keep the receipt off the tree. A person reads the named file and line before any one-skill copy. This lane did not copy one. |
| Share-alike on a committed snapshot | Edited or unmarked Trail of Bits text lands in a pfy skill. | Cache only. Any later copy stays byte-identical, with the license, credit, URL, and pin. pfy notes go in a separate PORT.md. |
| Claude-only steps | The skill tells the agent to dispatch a namespaced subagent. That dispatch did not run. | The git checks above are the part that ran. Do not treat this as a full Phase 5 audit. |
| Name-grep coverage | The checklist would mark `_clear_scratch` untested. The behavior test covers it. | Trust the behavior test. Do not add a unit that only calls the private name. |
| Upstream move | The short sha is not a fetchable ref. Skills get renamed. | Pin the full commit. The tree hash is in the card. |

## Next gate

Stay I0. I3 needs 3 of 4 value checks, all 4 modularity checks, a repeatable script, and `self_pipeline` evidence. None of that is this lane. A later slice can copy one SAFE skill only after the install check exits 0 on that directory, under the license rules above, and only if that skill finds a defect on a pfy diff that the review skill and the existing tests miss. No gate wiring and no Feature GO.

## Five questions, if this tool were on the pipeline

It is not on the pipeline. This is how it would run if someone picked it up later.

1. What triggers it? A person runs `scripts/pfy_skill_scan.py` on one skill directory before any copy. The checklist itself has no hook.
2. What does it do, and which services does it read and write? The scan reads the skill files and writes a receipt. The checklist reads `git diff` and git history. Both stay on the machine. No hosted model and no account. The cache holds the pin.
3. What does it trigger next? Nothing in `./pfy` starts from the receipt or from a differential-review note.
4. Where does a human re-enter? On a non-zero scan. Exit 1 means do not copy. `--allow-caution` does not clear DO_NOT_INSTALL. A checklist with 0 defects does not merge code.
5. What stops two runs doing the same work? One cache directory and one worktree per slug. The tool has no lock, because it is not wired in. Two readers can share the pin. Two copies into a skills directory would race, so the copy stays a manual step.
