# awesome-hermes-skills evq1107

ZeroPointRepo/awesome-hermes-skills is a curated index for the Hermes Agent ecosystem. The product is one README. It has no CLI and ships no skill body. This lane did not run its scripts or any install line.

## License and pin

Root `LICENSE` is MIT, Copyright (c) 2026 Zero Point Studio. README, CONTRIBUTING.md, and llms.txt say the list text is CC BY 4.0 and each linked project keeps its own license. This lane cites counts and design only.

Pin `9fb166c3548ca7befb579c525991255bb6daac83`, committer 2026-11-02T07:17:29Z, subject `chore: re-resolve canonical entry names [skip ci]`. No catalog pin existed before this read. `git fetch --depth 1 origin HEAD` took the default-branch tip. Cache `~/.cache/pfy/tools/awesome-hermes-skills/src` (not committed). Init through checkout: 0.402 s (2026-11-08T06:00:25Z to 2026-11-08T06:00:26Z). Worktree 17 files, 192586 bytes, 0 files named `SKILL.md`. `.git` 46 files, 119390 bytes. README 909 lines, 81434 bytes. `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `npm_config_cache`, and `TMPDIR` sat under that cache. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`.

```bash
CACHE=~/.cache/pfy/tools/awesome-hermes-skills
mkdir -p "$CACHE"/{home,xdg/config,xdg/cache,npm,tmp,src}
export HOME="$CACHE/home" XDG_CONFIG_HOME="$CACHE/xdg/config" XDG_CACHE_HOME="$CACHE/xdg/cache"
export npm_config_cache="$CACHE/npm" TMPDIR="$CACHE/tmp"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
git -C "$CACHE/src" init -q
git -C "$CACHE/src" remote add origin https://github.com/ZeroPointRepo/awesome-hermes-skills.git
git -C "$CACHE/src" fetch --depth 1 origin HEAD
git -C "$CACHE/src" checkout --detach FETCH_HEAD
```

## What the pin contains

Badge and intro: 368 = 82 built-in + 117 optional + 169 community and related, Hermes v0.20.6. Counted lines: 82 built-in bullets, 117 optional bullets, 116 community skill links, 176 tagged entries. One extra name-and-author line is the format sample in Contributing. The 169 figure is their sum, not that raw link count. Tag marks: production 53, beta 106, experimental 17. Install text: 3 `hermes skills install`, 2 `npx skills`, 4 bash fences. Entry 053 (2026-07-16) said 271 (85 + 101 + 85). `entry-health-report.md` says 152 linked repos checked and none renamed, archived, or deleted. A github.com/owner/repo regex finds 157 unique paths in the README. `.github/data/repo-ids.json` holds 162 numeric ids. Weekly jobs are advisory and do not fail a PR. The security notice says the list is curated, not audited.

## Ideas, and the pfy file each would touch

1. Store the immutable GitHub repo id next to the slug. A rename still returns HTTP 200, and a vacated slug can be claimed. Would touch `catalog_github` on `data/stages/<slug>.json`. Not this lane.
2. Keep link health advisory and off the contributor path. Would be a catalog hygiene note. Do not add it to `scripts/catalog_check.py` or pregate.
3. Stamp the as-of version on a bundled count (Hermes v0.20.6; star counts stamped 2026-08-24 09:23 UTC). `docs/scoring-summary.md` still says 271 and S-tier, with no pin. This lane does not edit that file.

## What we already have

H2 is SkillSpector at I3: `scripts/pfy_skill_scan.py` must exit 0 before a fetched skill is copied (`docs/ops/skill-scan.md`). `docs/build-dropins/skill-discovery.md` keeps fetched skills as data. Skills land through `bootstrap/grok-cli/install.sh` and ADR-0009 (first-party core, paths snapshots, or docs-only). `bootstrap/grok-cli/skills/hermes-feedback/SKILL.md` is the Hermes pattern and forbids a bulk import of this list. mattpocock/skills, ponytail, karpathy-guidelines, and marketing-council are already in the tree. TOOLS.md already has the A-tier row (overall 89). No new row.

## Catalog comparison

Same job: a skill list, and the H2 check before a fetched skill is copied. Gap H2 in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is assigned to SkillSpector (entry 148). Entry 053 is older than that ranking. This lane builds no pipeline, CI, or gate. Searched `data/stages/*.json` uses, features, and tags.

| Tool | Stage | How this list compares |
| --- | --- | --- |
| SkillSpector | I3 | The H2 scan. This README says curated, not audited. |
| Grok CLI bootstrap | I3 | `install.sh` plus `skills.paths` is the source. These lines target Hermes. |
| skill-up | I3 | Grades a with-skill run. Not an index. |
| Sandlock | I2 | Confines one install command. This list does not. |
| asm | I1 | Copies a skill. Its probe blocked 0 of 1 planted skills. |
| Skills Manager | I0 | A home hub. This is an index, not a hub. |
| Hermes Agent (feedback loops) | I1 | The ported pattern. It forbids this bulk import. |
| mattpocock/skills | I1 | Already on the path. This list features that pack. |

Also the same shape, already decided: cedr I1, ponytail I1, gstack I1, karpathy-guidelines I1, marketing-council I1, OpenCode Skill Creator I0, repository-harness I0, trailofbits-skills I0, claude-codex-settings I1, runx I0.

## Gates

Value, 3 of 4 for I3: gap fill no (H2 is the scan, and the README points at a 600+ Hermes hub), operator leverage no (install target is the Hermes CLI), evidence no (no pfy smoke; install was not run), blast radius no (hundreds of unaudited instruction packs, mixed upstream licenses). Score 0 of 4. Reading the list is fine under MIT and CC BY 4.0.

Modularity, all 4: README, CONTRIBUTING, llms.txt, LICENSE, and the three workflows were enough, so a copy was not required to decide. The unit is one README plus three workflows (192586 byte worktree). The cache clone is isolatable, and deleting it leaves the pin. 3 of 4. Potential is low, so I2 stays closed. No `self_pipeline` field. No gate wiring.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Bulk import | An agent runs an install line from the README | This lane ran nothing. hermes-feedback and skill-discovery already forbid that load. |
| Slug squat | `catalog_github` follows a rename to a new owner | Do not install from the list. A later note can store the numeric id. |
| False H2 close | A curated list is treated as the install gate | H2 stays `scripts/pfy_skill_scan.py`. |
| Mixed license | The README or a linked skill is copied into the tree | Cite only. Linked projects keep their own license. The featured youtube-full block is their own product and is not a pfy pick. |

## Next gate and pipeline

Stay I1 reference. Re-open only to record immutable GitHub repo ids beside `catalog_github`, with no install and no copy of the README. No Feature GO.

This lane writes the card, the Entry 053 Status line in `sources/x-posts.md`, and this directory. If a later ticket adopted the list: (1) a person or an agent copies `hermes skills install` or `npx skills add`. The evq scheduler is not that trigger. (2) It reads this README and writes a Hermes skill home or another agent home. This lane called no model and used no account. (3) Next is the installed skill running. Nothing in pregate or CI. (4) A human re-enters before any install. Our re-entry stays the skill scan, `/open-questions`, and `tmp/STOP`. (5) One worktree per slug keeps this card private. Two installs would both write the same Hermes skill directory. Their weekly walks share a `catalog-walk` group. We do not add that group.

## Verdict

STAY I1 reference: Hermes README index only; H2 stays scripts/pfy_skill_scan.py
