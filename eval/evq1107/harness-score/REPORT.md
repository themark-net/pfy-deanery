# Harness Score evq1107

Verdict: STAY I0. harness-score 1.8.2 gives a repeatable filesystem grade. On this repo the grade is L1 Documented, 48/105 (46%). Deleting AGENTS.md and 65 SKILL.md files moves it to 41/105 and the level stays L1. The skills dimension stays 0/17. That number does not measure the harness this repo runs, and it does not fill gap H1.

## Pins

| Item | Value |
| --- | --- |
| Package | `harness-score@1.8.2` |
| Tag | `v1.8.2` at `70a0ecc1aa907faf1f7a99a919eb88122f9a328d` (`git ls-remote` and the registry `gitHead`) |
| Tarball | `https://registry.npmjs.org/harness-score/-/harness-score-1.8.2.tgz` |
| Tarball sha256 | `816c6362704e73111801cfce3861a189c2494868d0a95b4aa7883ca29a0b94c2` (matches entry 128) |
| Tarball size | 37355 bytes. Unpacked package is 117153 bytes. |
| Registry sha512 | matched `dist.integrity` on the 1.8.2 registry document. The digest is not copied here. |
| Runtime deps | none (`package.json` `dependencies` is empty) |
| Node | v22.23.0 at `/usr/bin/node` |
| Install | `~/.cache/pfy/tools/harness-score/src/package` (unpacked tarball). No `npm install -g`. |
| CLI | `dist/cli.js`, `package.json` version 1.8.2, `--version` prints `1.8.2` |
| License | MIT |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, and `TMPDIR` pointed at that cache path. The scan did not get `--scope user` or `--scope system`. After the scans, the cache home and XDG dirs had no files. `~/.harness-score` and `~/.config/harness-score` were absent before and after.

## Commands

```bash
CACHE="$HOME/.cache/pfy/tools/harness-score"
mkdir -p "$CACHE"/{home,xdg/config,xdg/cache,xdg/data,tmp,src}
export HOME="$CACHE/home" XDG_CONFIG_HOME="$CACHE/xdg/config"
export XDG_CACHE_HOME="$CACHE/xdg/cache" XDG_DATA_HOME="$CACHE/xdg/data"
export TMPDIR="$CACHE/tmp" NO_COLOR=1
unset FORCE_COLOR
curl -fsSL -o "$CACHE/src/harness-score-1.8.2.tgz" \
  https://registry.npmjs.org/harness-score/-/harness-score-1.8.2.tgz
sha256sum "$CACHE/src/harness-score-1.8.2.tgz"
mkdir -p "$CACHE/src/package"
tar -xzf "$CACHE/src/harness-score-1.8.2.tgz" -C "$CACHE/src/package" --strip-components=1
NODE=/usr/bin/node
CLI="$CACHE/src/package/dist/cli.js"
"$NODE" "$CLI" --json "$WT"
"$NODE" "$CLI" --json "$WT"
"$NODE" "$CLI" --min-level 2 --quiet "$WT"
```

The with/without pair used a `git archive HEAD` of this worktree (tracked files only, no `.git`). The stripped copy deleted `AGENTS.md`, `.grok`, `bootstrap/grok-cli/skills`, `bootstrap/grok-cli/skills-external`, and `bootstrap/opencode`. `.claude`, `.cursor`, `.cursorrules`, `CLAUDE.md`, and `GEMINI.md` were already absent. Tests, `Makefile`, and `.github` stayed.

The live worktree was clean (`git status`). Its pass map matched the archive. Ignored paths were `pfylib/__pycache__/` and `tmp/`. Counts below are the live worktree for "with" and the stripped archive for "without". Per-check rows are in `summary.json`.

## Numbers

| Tree | Exit | Seconds | Level | Score | Checks | SKILL.md files |
| --- | --- | --- | --- | --- | --- | --- |
| This worktree | 0 | 0.0556 | L1 Documented | 48/105 (46%) | 17 pass, 19 fail | 68 |
| Same tree, rerun | 0 | 0.0528 | L1 Documented | 48/105 (46%) | same JSON | 68 |
| Stripped archive | 0 | 0.0511 | L1 Documented | 41/105 (39%) | 15 pass, 21 fail | 3 |

The rerun stdout sha256 is `d391c13398273b44f955f321d15e1fd0abe7cb78ffc7a380c93ac00badc4ebf2` on both live runs. `byte_identical` is true. Both snapshots are `complete` (`truncated` false). `--min-level 2` on the worktree exited 1 in 0.0536s. Stderr said maturity L1 is below required L2 because skills or hooks are under 30%.

| Dimension | With | Without |
| --- | --- | --- |
| context | 20/20 (100%) | 13/20 (65%) |
| skills | 0/17 (0%) | 0/17 (0%) |
| hooks | 0/14 (0%) | 0/14 (0%) |
| sensors | 2/20 (10%) | 2/20 (10%) |
| ci | 8/14 (57%) | 8/14 (57%) |
| hygiene | 18/20 (90%) | 18/20 (90%) |

Only CTX-01 and CTX-02 flip. CTX-01 is 4 points and CTX-02 is 3 points. That is the whole 7 point drop (48 to 41). The level stays L1 because L2 still wants skills at least 30% or hooks at least 30%. Both stay at 0%.

What the worktree scan actually saw:

- CTX-01 and CTX-02 pass. `AGENTS.md` is at the root, 136 non-empty lines, 32 headings. The bar is 20 lines and 2 headings.
- CTX-03 passes on one codex rule: `bootstrap/project-process/templates/AGENTS.md`. That hit remains after the real `AGENTS.md` is deleted. `detectedHarnesses` is `["codex"]` on both trees.
- SKL-01 fails. Evidence lists `.cursor/skills/`, `.claude/skills/`, `.devin/skills/`, `.agents/skills/`, and a plugin `skills/` directory. Of the 68 `SKILL.md` files, 20 are under `.grok/skills`, 15 under `bootstrap/grok-cli/skills`, and 30 under `bootstrap/grok-cli/skills-external`. None of those paths are in the check.
- HKS-01 fails. No `.cursor/hooks.json`, `.claude/settings.json` hooks key, or Devin hooks file.
- SNS-01 fails. It found 258 test files and no test runner. SNS-05 passes on those same files (2 points). That is the whole sensors score.
- CI-01 and CI-02 pass. CI-02 evidence is that CI invokes tests (`pytest`). CI-03 fails (no lint or type check seen). CI-04 fails (no pre-commit).
- HYG-01, HYG-02, HYG-03, HYG-04, HYG-06, HYG-07 pass. HYG-03 found no real `.env`. HYG-06 scanned 3 harness files on the worktree and 2 on the stripped tree, and found no credential signatures. HYG-05 fails (no root `LICENSE`). HYG-08 is not applicable (no MCP config) and is outside the 105 point max.

The three `SKILL.md` files that remained in the stripped tree are `examples/agentdescent-trial/skill/SKILL.md`, `bootstrap/project-process/skills/project-process/SKILL.md`, and `eval/catchup-1107/skill-up/cases/SKILL.md`. Skills stayed 0/17 with those files present too.

## Catalog comparison

Gap H1 in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is a repeatable with/without score, because harness2 showed no gain. The ranking assigns that gap to entry 136 (harness2) and entry 146 (skill-up). This lane asked whether harness-score's L0-L4 grade is that score.

| Card | Stage | Same job? | What this probe showed |
| --- | --- | --- | --- |
| skill-up | I3 | Yes. Grades a with-skill run against a no-skill baseline. | Already the H1 score. Its catch-up trial was 5/5 on both arms, delta 0. harness-score never runs a case. Removing 65 skills changed its skills score by 0. |
| harness2 | I1 | Yes. A harness edit trial on the 48-case set. Gain was 0. | This grade does not re-measure those cases. |
| eval-harness (pfy) | I1 | Partial. First-party structural ladder (`make eval-structural`). | Sensors here are 2/20 on a repo whose own ladder is the structural check. |
| neatroots | I2 | Partial. Offline rules on saved traces. | Different input. A trace check can see a repeated tool call. This scanner cannot. |
| SkillSpector | I3 | Partial. Static scan of a skill directory before copy. | It reads the skill tree this scanner missed. |
| OpenCode Skill Creator | I0 | Partial. Frontmatter lint of `SKILL.md`. | Stayed I0 on these same 68 skills. Trigger evals stay with skill-up. |
| bumblebee | I2 | Partial. Lockfile and MCP config advisory. | Hygiene overlap. This scan found no MCP config (HYG-04 pass, HYG-08 not applicable). |
| write-guard-mcp | I3 | Partial. Write mediation for the cage. | A runtime guard. This scanner looks for Cursor or Claude hooks JSON and did not find any. |
| project-process bootstrap | I3 | Partial. Writes `AGENTS.md` into another repo. | CTX-01 and CTX-02 pass on the file that scaffold already requires. |
| Jamon Holmgren agentic setup | I1 | Partial. Public workflow notes. The card already says the process kit covers `AGENTS.md`. | Same overlap. |
| agent-cage | I3 | The harness we run. Tag `#harness`. | The cage is the lab. harness-score did not detect `.grok`. |

harness-score does not beat skill-up, harness2, or eval-harness on H1. Its extra output is one L0-L4 number. On this repo that number stays L1 when the skill tree is removed.

## Gates

Value gate (3 of 4 needed for I3):

1. Gap fill: no. H1 is a with/without behavioral score. skill-up is already I3 for that. Here the only movement is CTX-01 and CTX-02 (7 points). Skills stay 0/17 with 68 `SKILL.md` files on disk.
2. Operator leverage: no. The 0.06s grade stays L1 either way, so it does not change an operator decision. The misses a person can already see (no root `LICENSE`, no pre-commit config, test runner named in CI as pytest) are not a new hole in the harness.
3. Evidence: yes. Pin re-checked, two byte-identical scans, one stripped scan, `--min-level 2` exit 1. Receipt: `summary.json`.
4. Blast radius: yes. MIT, 37355 byte tarball, no runtime dependencies, offline scan, cache home, no account, no key.

Score 2 of 4.

Modularity gate (all 4, recorded because the CLI had to be run):

1. Local code needed: yes. The `.grok` miss and the stuck L1 showed up only by running `dist/cli.js`.
2. Bounded surface: yes. One package, one CLI, no runtime dependencies.
3. Isolatable: yes. The copy is under `~/.cache/pfy/tools/harness-score/`. It is not the product runtime.
4. Reversible: yes. Delete that cache directory. The entry pin remains.

Unpacked size is 117153 bytes, under the 50 MB lightweight limit. Size is not the reason for I0. The grade does not help the gap, so this lane does not keep an I2 claim.

`uses` names CI, so a later I3 would need `self_pipeline` with evidence. This lane did not put the tool on the pipeline and does not set that field. No `TOOLS.md` row and no `data/tools.json` row.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Score chasing | A repo adds Cursor-shaped files so the total rises | Do not gate on the total. This lane wires no gate. |
| Path bias | `.grok/skills` and `bootstrap/grok-cli/skills` score 0. Level stays L1 after they are deleted | Stay I0 until a pinned version scores those paths and the level moves when they are removed |
| Level hides the harness | L1 with `AGENTS.md` and L1 without it | Read CTX and SKL rows. The entry already said a short `AGENTS.md` stays L0 and the level is the wrong threshold |
| Template counted as a rule | CTX-03 passes on `bootstrap/project-process/templates/AGENTS.md`, and `detectedHarnesses` is `codex` | Treat that path as a scaffold template. It is not the live Grok skill tree |
| Sensor miss | 258 test files and SNS-01 still fails, while CI-02 passes because a workflow says pytest | Keep `make eval-structural` as the structural check |
| Dirty `.env` | HYG-03 fails when a local `.env` is in the tree | Scan a clean worktree or a `git archive`. This worktree had no `.env` and HYG-03 passed |
| Version churn | A later npm version adds checks and the score moves | Pin 1.8.2. `--diff` can flag `maturityModelChanged` |
| Credential evidence | A hit on HYG-06 can echo a secret into JSON | This scan's evidence had no key-shaped string. A future hit stays in the cache report and out of git |

## Next gate

Stay I0. Re-open only if a pinned version scores `.grok/skills` and the level changes when that tree is removed. No `--min-level` in CI, no Cursor plugin, no GitHub Action, no badge. Not a Feature GO.

## Pipeline questions

How harness-score would run if a later ticket put it in the pipeline. This lane did not add that path.

1. What triggers it? A person runs the pinned CLI on a clean worktree. A CI job would be a separate ticket.
2. What does it do, and which services does it read and write? It reads the repo filesystem (tracked, untracked, and ignored files, skipping dependency dirs, bodies over 512 KiB). It writes a JSON report. It does not call a model, a host, or an account.
3. What does it trigger next? Nothing in this lane. `--min-level` would exit 1 and could stop a job. On this repo that exit is 1 for level 2, because skills and hooks are 0%.
4. Where does a human re-enter? Before any gate, any plugin install, or any commit that adds files only to raise the score.
5. What stops two runs doing the same work? The scan is read-only and byte-identical, so two runs do not corrupt each other. They also do not dedupe. One worktree per slug is what keeps lanes apart. There is no tool lock.
