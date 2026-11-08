# taste-skill evq1107

Verdict: PROMOTE I2. App-mode lint on `gui/operator/frontend/index.html` exited 0 with 0 FAIL and 3 WARN in 0.035 s. The same mode on a planted operator page exited 1 with 4 FAIL (gradient, purple, emoji, lorem) in 0.0224 s. Separation is 4. Default mode on that same index exited 1 with 4 FAIL. Inspect in app mode exited 1 on the operator page with 2 FAIL (`palette-terracotta`, `no-title`) in 3.8481 s. Tauri binaries found: 0. The whole probe took 10.4468 s. Nothing is wired into a gate.

`PROMOTE I2 app-mode lint 0 FAIL on the operator page and 4 FAIL on a planted page; inspect 2 FAIL on that page; Tauri binaries 0`

## Catalog tools on this job

The job is gap W: the Tauri operator window is not built on nimo, and the reason to look at this tool is a design-direction draw plus a slop lint for that UI. Searched `data/stages/*.json` `uses`, `features`, `tags`, and `catalog_tags` for slop, lint, design, layout, screenshot, visual, palette, browser, qa, operator, and window. `docs/eval/TOOLSET-RANKING.md` (2026-11-07) holds entry 143 until the window exists and says no entry from 137 to 167 closes gap W. `eval/ev1107/` and `eval/catchup-1107/` have no design-lint number for this page. This lane builds no pipeline, CI, or gate step.

anti-slop and Sloptrim did not match that word list on `uses` (their cards say "generic UI" and "AI-writing"). They are on this table because they are the other slop cards, and anti-slop's non-goals name taste-skill.

| Tool | Stage | What that card covers | How taste-skill compares |
|------|-------|----------------------|--------------------------|
| anti-slop | I0 | A SKILL.md pack that asks an agent to filter generic UI, copy, and comments. The evq probe found programs for 2 of 38 rules and no page scanner. | This probe is a page scanner with an exit code. anti-slop has no equivalent count. |
| Sloptrim | I1 | Offline 0-100 score for AI-writing patterns in a prose file. Planted prose separated by 66 points. | A prose score. This probe scores HTML. Sloptrim was not re-run. |
| assay | I1 | No-LLM web QA. It pressed 12 of 47 operator controls and passed 31 of 31 while `/launch` returned HTTP 501. | A click pass. This probe does not press controls. Assay's number still stands for "was the page used". |
| BugPatrol | I1 | QA patrol through a local model. The probe did not build the operator window. | Needs a model. This probe is offline and finished in 10.4468 s. It does not file product bugs. |
| Open WebUI | I1 | Chat UI for local models. The card says the operator window is the product UI. | A different window. No lint for `gui/operator/frontend`. |
| Camofox Browser | I1 | Stealth browser for agents. The card says browser automation is not core. | A browser, with no design exit code. |
| Charlotte | I0 | Token-bounded browser pages for local models. | Page text for a model. No lint. |
| Hyperframes | I1 | HTML-to-video for agents. | A render to video. No lint. |
| OpenCode Skill Creator | I0 | Frontmatter lint via `skill_validate`. | A different lint. It does not read the operator page. |
| kanbots | I1 | Kanban GUI over worktrees. | A GUI product. No checker for this page. |
| emdash | I0 | Parallel agents GUI, one worktree each. | A GUI product. No checker for this page. |

The in-repo skill `ui-is-the-app-design-in-loop` is the design rule for operator UI. It is not a scanner. This probe does not replace it.

Beats anti-slop on an HTML finding count: yes. Sloptrim scores a prose file and was not run on this HTML, so there is no head-to-head. Beats assay on whether the operator page was used: no. Closes gap W: no. Tauri binaries are still 0.

## Pins

Install root: `~/.cache/pfy/tools/taste-skill/`. Child `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, `TMPDIR`, `TASTE_SKILL_TMP`, and `TASTE_SKILL_HISTORY` were directories under that root. No global install. No account and no key. No model lock. `assets.mjs` was not run.

- Repo `https://github.com/Leonxlnx/taste-skill`
- Commit `6010f91a9935f1c167dfc500fb1a475681892e6b`, tag `v2.1.4`
- Subject `Merge pull request #159 from Leonxlnx/fix/profile-sweep-owner-pid`
- Commit date `2026-10-20 20:38:06 +0200`. The entry's read date is 2026-10-22. The pinned commit is the earlier instant.
- License MIT. `LICENSE` sha256 `4575a543ab88dad12ccea7d97e563d0bce5b448b06072e65d3264497dad326df` (1065 bytes). The entry gives no file checksum.
- `lint.mjs` sha256 `05f2fae2f56fc051b539cdbacb43a6f78fbbfb9644bb74aa11be472ff12dcaf5`
- `draw.mjs` sha256 `6c2047d207d2400d3b099956dfe2ac306203b614246e66bc8760212a7f797dbf`
- `inspect.mjs` sha256 `9482c546288d4d5c738a915905959e99394551ec27bc202ed443af12a02bd1f7`
- Tree without `.git`: 3083290 bytes. Under the 50 MB I2 copy limit. With `.git` the checkout is 5223506 bytes.
- Node `v22.23.0` at `/usr/bin/node`. Chrome `/usr/bin/google-chrome`, `Google Chrome 157.0.8103.38`.

`~/.taste-skill` on the login home was absent before and after (`login_taste_before` and `login_taste_after` are null). Chrome wrote NSS and fontconfig files under the redirected XDG dirs. The skill's `ad-chrome-*` profile list was empty after the run. JPEGs were counted and deleted (operator page 2 shots, 148039 bytes).

## Commands

```bash
LOGIN_HOME=$HOME
BASE=$LOGIN_HOME/.cache/pfy/tools/taste-skill
mkdir -p "$BASE/home" "$BASE/xdg-config" "$BASE/xdg-cache" "$BASE/tmp" "$BASE/src"
export HOME="$BASE/home" XDG_CONFIG_HOME="$BASE/xdg-config" \
  XDG_CACHE_HOME="$BASE/xdg-cache" XDG_DATA_HOME="$BASE/home/.local/share" \
  TMPDIR="$BASE/tmp" GIT_CONFIG_GLOBAL="$BASE/home/.gitconfig" GIT_CONFIG_NOSYSTEM=1
git clone --filter=blob:none --no-checkout https://github.com/Leonxlnx/taste-skill.git "$BASE/src"
git -C "$BASE/src" fetch --depth 1 origin 6010f91a9935f1c167dfc500fb1a475681892e6b
git -C "$BASE/src" checkout --detach FETCH_HEAD
env HOME="$LOGIN_HOME" python3 eval/evq1107/taste-skill/probe.py \
  --node /usr/bin/node \
  --scripts "$BASE/src/skills/taste-skill/scripts" \
  --src "$BASE/src" \
  --expect-pin 6010f91a9935f1c167dfc500fb1a475681892e6b \
  --out eval/evq1107/taste-skill/results.json \
  --home "$BASE/probe-home" \
  --tmp "$BASE/tmp/probe" \
  --chrome /usr/bin/google-chrome \
  --login-home "$LOGIN_HOME"
```

The probe process itself uses the login home only to watch `~/.taste-skill`. Children get the cache home. Exit 0. Exit 1 would mean the planted page was not separated, draw failed, or history landed in the child `HOME/.taste-skill`. Exit 2 would mean the pin or the scripts were missing.

## Probe

Fixtures are `eval/evq1107/taste-skill/fixtures/`. The operator page is `gui/operator/frontend/index.html` (260 lines, 0 lines over the linter's 2000-character skip). App mode is the mode for an operator screen. The draw brief is kind `devtools`, theme `dark`, seed `7`: "native operator window for a local agent harness". Inspect uses `--app --widths 1280`.

| Page | Mode | Exit | FAIL | WARN |
|------|------|------|------|------|
| Operator index | default | 1 | 4 (hairline 2, shadow 1, mono 1) | 8 (outlined-box 6, h-screen 1, em-dash 1) |
| Operator index | app | 0 | 0 | 3 (shadow, mono, em-dash) |
| Operator frontend, 7 files | app | 0 | 0 | 3 (same ids; the em-dash finding says 27) |
| Planted slop | app | 1 | 4 (gradient, purple, emoji, lorem) | 2 (eyebrow, copy) |
| Planted clean | app | 0 | 0 | 0 |
| Eyebrow mutant | default | 1 | 1 (eyebrow) | 0 |
| Eyebrow mutant | app | 0 | 0 | 1 (eyebrow) |
| Smoke slop | default | 1 | 6 (the entry's five ids, plus hairline) | 1 (copy) |
| Smoke clean | default | 0 | 0 | 0 |
| Missing path | default | 2 | n/a | n/a |

The index em-dash WARN says 13. That is a WARN. App-mode exit stays 0.

Draw, seed 7, empty history: both sheets are `true-black-flat` / `ruled-t-frame`, screens `deploy-health-lead`, `table-filter-bar`, `settings-with-usage`. Agreement 2/2. Times 0.0228 s and 0.0255 s. `--options 3` returned 2 styles (`true-black-flat`, `data-terminal`), 1199 bytes, the two runs matched, and the history file was not created. The same seed with one shared history file dealt `true-black-flat` then `data-terminal` / `icon-rail`. History length 2. Memory steered that second draw.

Inspect, app mode, width 1280:

| Page | Exit | FAIL | WARN | Seconds | Shots |
|------|------|------|------|---------|-------|
| Operator index | 1 | palette-terracotta, no-title | unused-canvas, panel-void | 3.8481 | 2 |
| Planted slop | 1 | emoji, gradient, edge-text, placeholder-data | hero-void, unused-canvas | 3.057 | 2 |
| Planted clean | 0 | none | hero-void, unused-canvas | 3.0813 | 2 |

`palette-terracotta` is the status color `#e8875b` on the operator page. `no-title` is the app rule that the screen has no `h1` (the page leads with an `h2`). Both are FAILs on the page we ship. The planted clean page exits 0, so a green inspect is not evidence about the operator page.

`gui/operator/src-tauri/target/{release,debug}/pfy-operator` is absent. `tauri_bins` is `[]`.

## Gates

Value gate, 2 of 4. The I3 bar is 3.

1. Gap fill. Not met for gap W. The Tauri binary count is 0. The 2026-11-07 ranking already holds entry 143 until that window exists. The lint hole versus anti-slop is real, and it is not the open window.
2. Operator leverage. Not met. App-mode lint already passes the HTML we have. A day of glue would still leave the binary absent, and inspect would fail the page on terracotta and a missing `h1`.
3. Evidence. Met. The probe exited 0 on this pin with `results.json` filled in. `tests/test_taste_skill_probe.py` drives the probe with stub node binaries.
4. Blast radius. Met. MIT, no weights, no account, cache only. The checkout without `.git` is 3083290 bytes. It is not the product runtime.

Modularity gate, all four hold.

1. Local code needed. Met. App mode versus default, and the history file steering the next seed, showed up only by running the scripts.
2. Bounded surface. Met. `lint.mjs`, `draw.mjs`, and `inspect.mjs`.
3. Isolatable. Met. The checkout sits under `~/.cache/pfy/tools/taste-skill/`. It is not the product runtime.
4. Reversible. Met. Deleting that cache leaves the pin, the entry, and this report.

I3 also needs the value gate at 3 of 4, a repeatable script, and `self_pipeline` evidence that the tool was applied to this repo's pipeline. The script exists. It was not applied. `self_pipeline` is `not_applicable`. `tier_ceiling` stays I1. Potential is medium: the 4-versus-0 lint split is real, and the gate is not.

## Risks

| Risk | How it fails | How we recover |
|------|----------------|----------------|
| Wrong mode | Default lint exits 1 on the operator page (4 FAIL: hairline, shadow, mono). | Pass `--app` for this screen. The receipt's app row is the floor. |
| Inspect on the shipped page | App inspect exits 1 (`palette-terracotta` on `#e8875b`, `no-title` because there is no `h1`). | Do not block on inspect. An allow list is Design's call. Lint `--app` stays the count. |
| Eyebrow-only edit | App mode stays exit 0 with 1 WARN. Default mode exits 1, and it also fails the real page. | Treat eyebrow as a WARN until Design says otherwise. |
| History leak | A draw with no `TASTE_SKILL_HISTORY` writes `~/.taste-skill/history.json` and the next seed changes style. | Set `TASTE_SKILL_HISTORY` per project. This run's `home_leak` is false. The probe deletes its own history files at the start of a run. |
| Green fixture | Planted clean inspect exits 0 while the operator page exits 1. | Read the operator row. A fixture pass is not the window. |
| Chrome or old Node | Inspect needs Node 22+ and a local Chrome. | Lint and draw still run. This box had Node 22.23.0 and Chrome 157. |
| Early onboard | Reading 0 lint FAIL as the operator window existing. | `tauri_bins` is empty. Stay at I2. |

## Next gate

Stay I2. Do not wire lint or inspect into pregate, CI, or the Tester gate. Reopen only if `gui/operator/src-tauri/target/{release,debug}/pfy-operator` exists and a later ticket grills an allow list for `palette-terracotta` and `no-title`, or decides that lint `--app` alone is the floor. The eyebrow mutant stays a WARN in app mode. No gate wiring from this lane.

## Five questions (this tool in our pipeline)

1. What triggers it? A change under `gui/operator/frontend` would run `lint.mjs --app` on that folder. Nothing in this repo calls it today. This lane adds no hook.
2. What does it do, and which services does it read and write? It reads local HTML, CSS, and JS. Draw writes `direction.json` under `--out` and a history file at `TASTE_SKILL_HISTORY`. Inspect drives local Chrome and writes screenshots under `--out`. No hosted model and no account.
3. What does it trigger next? Nothing in this lane. A human still has to build the Tauri window. The exit code does not start a gate.
4. Where does a human re-enter? When inspect fails the current page, or when a WARN is a choice Design wants to keep (the 13 em dashes, the monospace id line, the inset shadow). Mark decides any allow list.
5. What stops two runs doing the same work? One worktree and branch per eval slug. The tool has no lock. A shared history file steers the next draw, so each project needs its own `TASTE_SKILL_HISTORY`. This lane does not add that run.
