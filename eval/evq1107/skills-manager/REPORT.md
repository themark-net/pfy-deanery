# Skills Manager evq1107

`STAY I0 reference: npm hub beside the skill tree; the H2 scan and install.sh already cover the job`

## What it is

skills-manager-cli (Sun Yongshen, npm `skills-manager-cli`) is one home hub (`~/.skills-manager`) that installs skills from git, a URL, an archive, a marketplace, or a well-known index, then symlinks or copies a subset into agent homes. No-arg `npx` bootstraps only a manager skill and, on a non-TTY, mounts it into every detected agent (upstream ADR-0014). The CLI is the engine. A dashboard on `127.0.0.1:4777` is optional. The README's "70+ agents" is their catalog claim.

## License and pin

MIT, Copyright (c) 2026 Sun Yongshen. Pin `fae0bb864a8b96c1d0ca6278a6b7062e62992a36`, commit 2026-10-27T03:20:24Z, package `2026.10.27-1`, Node `>=20`. This host is Node v22.23.0. Cache `~/.cache/pfy/tools/skills-manager/src` (not committed): 330 worktree files, 2478511 bytes without `.git`, 3610963 bytes with it. Fetch and checkout 0.591 s. No pnpm, no npm, no upstream script. `dist/` is absent, so the published bin was not built. The 2026-11-02 smoke PASS (version, help, `list --home`) was not re-run.

```bash
CACHE=~/.cache/pfy/tools/skills-manager
mkdir -p "$CACHE"/{home,xdg/config,xdg/cache,npm,tmp,src}
export HOME="$CACHE/home" XDG_CONFIG_HOME="$CACHE/xdg/config" XDG_CACHE_HOME="$CACHE/xdg/cache"
export npm_config_cache="$CACHE/npm" TMPDIR="$CACHE/tmp"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
git -C "$CACHE/src" init -q
git -C "$CACHE/src" remote add origin https://github.com/shenysun/skills-manager.git
git -C "$CACHE/src" fetch --depth 1 origin fae0bb864a8b96c1d0ca6278a6b7062e62992a36
git -C "$CACHE/src" checkout --detach FETCH_HEAD
```

## Ideas (borrow the note, not the CLI)

| Idea | pfy file |
| --- | --- |
| Update anchor is the skill subdirectory tree SHA, so a README-only commit is not an update | `bootstrap/grok-cli/manifest.json`, `docs/ops/skill-verification.md` |
| Resident cost is a char-approx of `name` plus `description`, report-only, and `--budget` exits 1 with no auto-remove | `docs/ops/skill-verification.md` |
| A category apply is explicit and idempotent; later tag edits show as drift and do not push | `docs/adr/0009-skill-port-hybrid-strategy.md` |

Leave the no-arg mount, the second hub, marketplace fetch, and the dashboard. Those fight `docs/adr/0009-skill-port-hybrid-strategy.md` and `docs/build-dropins/skill-discovery.md` (fetched skills stay data). That is why the lane stays reference-only.

## Catalog comparison

Same job: install and distribute skills, and the H2 check before a fetched skill is copied. Searched `data/stages/*.json` uses, features, and tags, plus `docs/eval/TOOLSET-RANKING.md` (2026-11-07). Entry 159 is in that section's hold-or-comparison list. H2 is assigned to SkillSpector. This lane adds no pipeline, CI, or gate.

| Tool | Stage | Same job | How this CLI compares |
| --- | --- | --- | --- |
| Grok CLI bootstrap | I3 | Skills install into the operator env | `bootstrap/grok-cli/install.sh` plus `skills.paths` is the source. A `~/.skills-manager` hub would be a second authority. |
| asm | I1 | Copy a skill into grok and opencode | Same distribute shape. Its probe copied a high-risk SKILL.md (0/1 blocked). This scanner was not run. |
| SkillSpector | I3 | Static scan before copy | H2 rule is `scripts/pfy_skill_scan.py` exit 0. Their `audit security` stays exit 0 when highs exist unless `--strict` (upstream docs/CLI.md). |
| Sandlock | I2 | Confine one install command | This CLI does not confine the fetch. |
| cedr | I1 | Hash-pin local skill dirs | Tree-SHA is upstream freshness. cedr locks bytes already in the tree. |
| repository-harness | I0 | Install four skills beside AGENTS.md | One repo overlay, not a multi-agent hub. |
| OpenCode Skill Creator | I0 | Frontmatter lint | No distribute step. |
| awesome-hermes-skills | I1 | A list of skills | An index, not a hub. |

## Gates

Value (3 of 4 for I3): gap fill no, operator leverage no, blast radius no (non-TTY bootstrap writes every detected agent home). Evidence is the 2026-11-02 CLI start only. Score 1 of 4. License is MIT and the worktree is 2478511 bytes, which does not offset the home writes.

Modularity (all 4 for I2): docs were enough, so local code is not required. The npm bin is bounded. The cache copy is isolatable and reversible. Score 3 of 4. Under 50 MB, and potential is low, so I2 stays closed.

`uses` and `features` carry no CI, test, or review role token. No `self_pipeline` field. No TOOLS.md row. No `data/tools.json` row.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| No-arg npx | Mounts the manager skill into every detected agent home | Do not run it. The smoke never bootstraps. |
| Second hub | `~/.skills-manager` drifts from `bootstrap/grok-cli/skills/` | Keep the repo tree as the source (ADR-0009). |
| High findings still install | Default `audit security` exits 0 when highs exist | H2 stays `scripts/pfy_skill_scan.py`. |
| Empty scan | `audit security --home` on a missing hub creates it and exits 0 (upstream docs/CLI.md) | Do not point a check at that command. |
| Unread scanner | `builtin-v1` is a README claim | Stay I0. A later ticket must beat SkillSpector on a planted skill. |

## Next gate

Stay I0. Re-open only to copy the tree-SHA note or the resident-cost count into `docs/ops/skill-verification.md`, with no CLI and no second hub. Not a Feature GO.

## Pipeline questions

1. What triggers it? If adopted, a person runs `npx skills-manager-cli`, or an agent follows the manager skill. This lane did not add that path.
2. What does it read and write? It reads git, URLs, archives, and marketplaces, and writes `~/.skills-manager` plus agent skill homes. This lane used no model and no account.
3. What does it trigger next? Distribute, update, or a chat install. Nothing in pregate or CI.
4. Where does a human re-enter? The TTY agent multi-select, any `--strict` finding, and any mount into `~/.grok` or `~/.claude`.
5. What stops two runs doing the same work? Their hub is one directory per machine. Here, one worktree per slug already keeps lanes off this card. Do not add their hub lock.
