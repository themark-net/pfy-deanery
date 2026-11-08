# anti-slop evq1107

STAY I0. The pinned pack is prompt text. Two of 38 rules show up in a program. The core skill is 57827 bytes (14429 chars/4) against karpathy-guidelines at 2518 bytes (626 chars/4), about 23 times larger. A repeatable phrase pass on this repo is not a with/without score, so gap H1 stays open. Potential is low. I2 does not apply.

`STAY I0 core skill 57827 bytes vs karpathy 2518, programs cover 2 of 38 rules, no with/without score`

## Catalog overlap

Same job: a repeatable score of generic AI output, plus the context cost of a SKILL.md rule pack (gap H1). Searched `data/stages/*.json` uses, features, and tags, plus `docs/eval/TOOLSET-RANKING.md` (2026-11-07 section and the 2026-10-06 table) and the batch results under `eval/ev1107/` and `eval/catchup-1107/`. This lane builds no pipeline, CI, or gate step.

anti-slop is entry 105. The 2026-11-07 ranking covers entries 137 to 167, so this entry is not in that table. That ranking assigns H1 to skill-up (with/without grade) and, for offline trace rules, to neatroots.

The probe's keyword scan (slop, copywriting, buzzword, contrast, baseline, yagni, comment) hit four cards: taste-skill (slop), skill-up (baseline), ponytail (yagni), Open Steps (baseline). Open Steps is a word hit only. The scan missed karpathy-guidelines, harness2, neatroots, and eval-harness (pfy) because their uses lines use other words. Those four were read because they are the H1 tools or the skill packs already loaded.

| Tool | Stage | What that card covers | How anti-slop compares |
| --- | --- | --- | --- |
| skill-up | I3 | Grade a with-skill run against a plain run. Catch-up trial: both arms 5/5, delta 0, flake 0/10. | The H1 instrument already on disk. This pack does not grade a run. It does not beat that probe. |
| taste-skill | I0 | Design slop lint plus a browser layout check. The entry records lint exit 1 on a slop fixture (emoji, eyebrow, gradient, lorem, purple) and exit 0 on a clean fixture. | A page scanner. anti-slop has no page scanner. `check-repo.mjs` audits the pack's own tree. The phrase pass below is this probe, not an upstream CLI. |
| karpathy-guidelines | I1 | One coding-behavior skill already in the skill tree. 2518 bytes. | The core skill is 57827 bytes and still needs a person to apply it. It does not add a score. |
| ponytail (skills pack) | I1 | YAGNI skill pack already under skills-external. Six SKILL.md files sum to 17214 bytes. | Already loaded, and smaller than the anti-slop core file alone. |
| neatroots | I2 | Offline rule checks for loops, repeated tool calls, and error streaks on saved traces. | Different rules. This probe did not score a trace. |
| harness2 | I1 | The local trial whose gain was 0. That result is the H1 gap. | This pack does not re-score that trial. |
| eval-harness (pfy) | I1 | First-party structural ladder (`make eval-structural`). | Already the repeatable structural score. This probe is not that ladder. |
| CodeGuard | I0 | Secure-coding rule text a host agent can read. Not an offline scanner. Stayed I0 after its own phrase probe. | Same shape (markdown rules for a host agent), different subject. |

Beats what we have: no.

## Pins

| Piece | Value |
| --- | --- |
| Repo | https://github.com/miqdadbadjuber/anti-slop |
| Commit | `388cbe3b6c37d5175b9f460015bb092ef9e34894` |
| Subject | docs: trim the usage-mode prose in the README |
| Parent | `91f12ec67e9de6043cfd93b846404986ba73c3f4`, tag v3.2.20, subject `v3.2.20: usage modes become a saved preference` |
| Version | `3.2.20` in `package.json`, `cli/package.json`, and `skills/antislop/VERSION`. The tag commit says the same version. The entry names both the tag and the child commit. This lane pins the child. |
| License | MIT (`LICENSE`) |
| Tree | 1207333 bytes excluding `.git`. Cache dir 2338661 bytes after the clone. Under the 50 MB I2 bar. |
| Digest | The entry gives no file checksum. `antislop.md` sha256 `1b32f1295b2eef2a9f9c9609bf2de6e71408bb41ca424731753c7f66e011c6e7`. `skills/antislop/VERSION` sha256 `ce6ddda39d58fbf68b3810aa75fe22894936f20c1e62c901ae455e0bab5138df`. `contrast-check.py` sha256 `619cdf3da8b27f87d8e4049b4acecfe1a559b234ab2aa9cf09447c28745c3075`. |
| Node | v22.23.0 at `/usr/bin/node`. Used only for `scripts/check-repo.mjs`. |
| Python | 3.14.4. No venv and no extra install. |

No account and no key. The clone used `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `TMPDIR`, `GIT_CONFIG_GLOBAL`, and `GIT_CONFIG_NOSYSTEM` under `~/.cache/pfy/tools/anti-slop/`. A fetch of the short prefix `388cbe3b6c37` failed. The full SHA fetched. The probe's child processes get those same variables under the cache. The probe process itself uses `Path.home()` so it can find the cache. Nothing was written to `~/.config/antislop`. The installer was not run.

## Commands

```bash
BASE=$HOME/.cache/pfy/tools/anti-slop
mkdir -p "$BASE/home" "$BASE/xdg-config" "$BASE/xdg-cache" "$BASE/tmp" "$BASE/src"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/xdg-config" \
  XDG_CACHE_HOME="$BASE/xdg-cache" TMPDIR="$BASE/tmp" \
  GIT_CONFIG_GLOBAL="$BASE/home/.gitconfig" GIT_CONFIG_NOSYSTEM=1
git clone --filter=blob:none --no-checkout https://github.com/miqdadbadjuber/anti-slop.git "$BASE/src"
git -C "$BASE/src" fetch --depth 1 origin 388cbe3b6c37d5175b9f460015bb092ef9e34894
git -C "$BASE/src" checkout --detach FETCH_HEAD
```

The probe then ran with the real home, so `Path.home()` resolves the cache:

```bash
python3 eval/evq1107/anti-slop/probe.py
```

Exit 0. Script clock 1.924 s. No model lock. `ollama` was not called.

`python3 -m unittest tests.test_anti_slop_probe` drives the probe as a subprocess. The node binary is a stub, or a path that does not exist. The pack and the corpus are temp dirs. No network and no real clone.

## What was skipped

| Part | Reason |
| --- | --- |
| `npx antislop-ai`, `npx skills add`, plugin doors | The entry non-goal. Those paths write harness skill folders and `~/.config/antislop/settings.json`. |
| With/without model run | This lane takes no model lock. The pack does not grade a run by itself. |
| Contrast MCP (`contrast-mcp.py`) | A server. Not started. The formula twin is covered by check-repo, which passed. |

## Probe

`python3 eval/evq1107/anti-slop/probe.py` reads the pin. It counts `#### R-NN` headings, quoted phrases on the FORBIDDEN lines of R-15 and R-16, and backtick comment snippets in `antislop-code` before the "Not a Ban" heading. It scores the fixtures, then the operator surface of this repo (AGENTS.md, docs, both skill trees, pfylib, scripts). It runs the score twice. `passes_agree` is true.

The upstream carve-out that ignores an em dash in a `#### R-NN` heading is for the pack's own docs. This probe does not apply it to other text. `tests/test_anti_slop_probe.py` puts that heading in a fixture and requires a count of at least 1.

### Upstream programs

`node scripts/check-repo.mjs` on the pin: exit 0, `all 13 checks passed`, 0.0359 s. The script does not read `process.argv`. It cannot score this repo.

Rule ids that appear in `scripts/`, `cli/`, or `skills/**/*.py` (not in the skill markdown): `R-02` and `R-25`. That is 2 of 38.

`python3 skills/antislop-human/contrast-check.py --selftest`: exit 0, `selftest: 8 reference pairs OK`, 0.0118 s.

| Pair | Ratio | Normal text (4.5:1) | Exit |
| --- | --- | --- | --- |
| `#FFFFFF` on `#777777` | 4.48:1 | FAIL | 1 |
| `#000000` on `#FFFFFF` | 21.00:1 | PASS | 0 |

The grey pair's exit 1 is the checker working. The probe still exits 0, because that pair is a sample, not the selftest. The ratio line is in `results.json`.

### Context

chars/4 is a size estimate, not a tokenizer count.

| File | Bytes | chars/4 |
| --- | ---: | ---: |
| `antislop.md` | 57655 | 14386 |
| `skills/antislop/SKILL.md` | 57827 | 14429 |
| `skills/antislop-code/SKILL.md` | 8944 | 2232 |
| six `skills/*/SKILL.md` together | 146463 | 36571 |
| karpathy-guidelines `SKILL.md` | 2518 | 626 |
| ui-is-the-app-design-in-loop `SKILL.md` | 3248 | 806 |
| ponytail `SKILL.md` | 6707 | 1671 |
| ponytail pack, all `SKILL.md` | 17214 | |

The core skill file is the core document plus frontmatter. Loading it is about 23 times the karpathy skill. Loading all six skills is about 58 times that skill. The entry's "load only the core plus one concern" path (core plus `antislop-code`) is 66771 bytes.

### Lexical score

Phrases extracted from the pin, 14: Get Started, Learn More, Try Now, Explore, Discover, AI Powered, Next Generation, Revolutionary, Seamless, Cutting Edge, Intelligent, Ultimate, Powerful, Effortless. Comment snippets extracted: 37. The em dash ban is on because R-02 names that character. The en dash is counted because `check-repo.mjs` rejects it too. Part 1's sample stats (`10K+ Users`, `99.9% Uptime`) are not quoted FORBIDDEN lines, so they are not in the phrase list.

Fixtures under `eval/evq1107/anti-slop/fixtures/`:

| File | Em dash | Multi-word phrases | Single-word phrases | Comment snippets |
| --- | ---: | ---: | ---: | ---: |
| `slop.md` | 1 | 2 (Get Started, AI Powered) | 1 (Seamless) | 0 |
| `slop.js` | 0 | 0 | 0 | 3 |
| `clean.md` | 0 | 0 | 0 | 0 |
| `clean.js` | 0 | 0 | 0 | 0 |
| `python_comment.py` | 0 | 0 | 0 | 0 |

`slop.md` also contains `10K+ Users` and `99.9% Uptime`. Those scored 0. `python_comment.py` uses the same words as the JS plant (`Main logic`, `Initialize the variable`) behind `#`. The extracted snippets are `//` lines, so the Python file scored 0. `clean.js` is the comment the skill says to keep, and it sits after "Not a Ban", so it is not a snippet. It scored 0.

This repo, 656 files, two passes agree:

| Area | Files | Files with a hit | Em dash | En dash | Single-word | Multi-word |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| docs | 482 | 342 | 1002 | 257 | 364 | 1 |
| bootstrap/grok-cli | 49 | 40 | 385 | 38 | 2 | 0 |
| .grok/skills | 48 | 39 | 376 | 33 | 4 | 0 |
| scripts | 55 | 23 | 81 | 3 | 8 | 0 |
| AGENTS.md | 1 | 1 | 17 | 1 | 2 | 0 |
| pfylib | 21 | 1 | 1 | 0 | 0 | 0 |
| Total | 656 | 446 | 1862 | 332 | 380 | 1 |

Phrase hits on that surface: Discover 369, Powerful 6, Explore 2, Ultimate 2, Next Generation 1, Revolutionary 1. The other eight phrases are 0. Comment snippets: 0.

Discover's top file is `docs/ops/RUN-LOG-mvp-ci-cover-1031.md` (17). The matches checked there are the standalone word, including `unittest discover`, not a button label. `.grok/skills` and `bootstrap/grok-cli/skills` are separate trees, so Ultimate and Powerful on the shared advisor notes are counted in both. Multi-word hits on the whole surface: 1 (`Next Generation` in `docs/scoring-summary.md`).

## Gates

Value gate for I3 needs 3 of 4. This probe has 2.

1. Gap fill: no. H1 is a with/without score. skill-up already grades that and is I3. taste-skill already claims a design-slop lint with an exit code. karpathy and ponytail are already loaded and much smaller.
2. Operator leverage: no. An operator still has no pass or fail for "did this skill change the output". The phrase pass flags Discover 369 times and would fail AGENTS.md on 17 em dashes. It misses the planted Python comments and the planted fake stats.
3. Evidence: yes. The pin, check-repo, the contrast selftest, the two contrast pairs, and the phrase pass ran on this host.
4. Blast radius: yes. MIT markdown and two small programs in the cache, about 2.3 MB, no key, no daemon, no copy in the skill trees. Deleting the cache leaves the pin and this report.

Modularity, all four, for a cache probe only:

1. Local code was required. The docs call the Delivery Gate a PASS/FAIL report. The tree shows that report is a checklist, `check-repo.mjs` takes no path, and only R-02 and R-25 appear in program files.
2. The pack is a bounded surface: six skill folders, one self-check, one contrast CLI. The installer was left out.
3. The tree sits under `~/.cache/pfy/tools/anti-slop/` and is not the product runtime.
4. Deleting that directory does not remove the catalog pin or this report.

The working tree is 1.2 MB, under the 50 MB I2 size bar. I2 is for ambiguous potential. After these numbers the potential is low. Stage stays I0.

## Risks

| Risk | How it fails | Recovery |
| --- | --- | --- |
| A missing node looks like a clean self-check | `check-repo.mjs` never runs and the lane treats that as 13/13 | The result status is `skipped` and `ok` is false. `tests/test_anti_slop_probe.py` covers a node path that does not exist. |
| A failed self-check hides the corpus score | The probe exits before writing counts | Exit 1 still writes `results.json`, and the lexical multi-word count is still there. The same test covers a stub node that exits 1. |
| Upstream version drift | VERSION and package.json disagree and the lane still calls it 3.2.20 | Exit 2. `versions.agree` is false. The same test writes VERSION `9.9.9` against package.json `3.2.20`. |
| The pack carve-out is copied onto our docs | A heading em dash is ignored, so AGENTS.md looks cleaner than it is | External text counts the heading. The test fixture is `#### R-02` plus the dash and requires a count of at least 1. |
| Single-word bans flood prose | Discover alone is 369 hits, mostly ordinary verbs | Do not gate on the phrase list. Multi-word hits on this surface were 1. |
| The em dash ban fights existing docs | 1862 em dashes, including 17 in AGENTS.md | Keep our docs authoritative. Do not fail a tree on R-02. |
| Context on a small local model | Core skill is about 23 times karpathy. All six skills are about 58 times it. | Do not load the pack on the local worker. This lane did not. |
| The mode question stalls an unattended run | The core asks During or After when no settings file exists | Do not append the pointer to AGENTS.md. This lane did not write the settings file. |
| Part 1 samples are not a detector | `10K+ Users` in the plant scored 0 | A zero phrase score is not a clean bill. |
| Comment tells are JavaScript-shaped | The Python plant scored 0 while `slop.js` scored 3 | Do not use the snippets as a Python comment checker. |
| Grey-pair exit is mistaken for a broken pin | `#FFFFFF` on `#777777` exits 1 because 4.48 is under 4.5 | Read the ratio line. The selftest is the pin check, and it passed 8/8. |
| Tag and entry commit diverge | Someone checks out tag v3.2.20 and misses the docs child this entry named | Pin the full SHA above. Both still say version 3.2.20. |

## Next gate

Stay I0. A later probe can argue I2 only if an offline program, with no model, scores one with-skill arm against a plain arm on this repo and the margin is large enough for skill-up to re-grade. That result would still sit beside skill-up and taste-skill, not replace them. Wiring a gate needs Tester and Reviewer. This lane does not wire one.

## How this tool would run in our pipeline

These five are the software-factory questions for the pack as a pipeline step. This lane does not add that step.

1. What triggers it? A Design or comment-editing lane that opted into the pack. Nothing in pregate, CI, or the scheduler triggers it today.
2. What does it do, and which services does it read and write? A host agent would read the pinned skill files from the cache. The only programs that write a result without a model are `check-repo.mjs` (its own tree) and `contrast-check.py` (the colors you pass). No hosted model and no account. This lane did not install the pointer into AGENTS.md.
3. What does it trigger next? Nothing mechanical. The Delivery Gate is a checklist the agent prints. A later job cannot consume an exit code from the 38 rules.
4. Where does a human re-enter? The core asks During or After on every new session when no settings file exists. That question is the human stop. An unattended lane would have to pin the mode in the prompt. We did not.
5. What stops two runs doing the same work? The pack has no lock and no run id. Two agents can both load it. Our scheduler already keeps one worktree per slug. That is the scheduler's rule, not the pack's.
