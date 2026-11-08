### Entry 143: taste-skill: agent skills with a deterministic design-direction draw and a slop linter that runs in a real browser

- **URL**: https://github.com/Leonxlnx/taste-skill (MIT, zero-dependency Node scripts; about 101k stars at this read). Read at commit `6010f91a9935f1c167dfc500fb1a475681892e6b` (main, 2026-10-22), which is tag `v2.1.4` (the repo has 8 tags); the smoke pins the commit.
- **Date**: 2026-10-22 (daily X intake, window 2026-10-22T00:37Z to 2026-10-23T00:36Z)
- **Source / Poster**: @DanKornas, https://x.com/DanKornas/status/2113121663109751227 (repo link in the reply https://x.com/DanKornas/status/2113121833385890253)
- **Summary / Key Claims** (upstream README and script headers; their claims except where marked verified): an agent skill (`design-taste-frontend`) for coding agents that build websites, landing pages, dashboards and app screens. `scripts/draw.mjs` deals a design direction (hero, type, palette, sections, motion) at random within what fits a sector and brief, remembers recent draws so it doesn't repeat, and writes `direction.json` for the other scripts. `scripts/lint.mjs` statically flags common AI-slop patterns (gradients, emoji, eyebrow labels, lorem ipsum, purple palettes, hairlines, generic copy). `scripts/inspect.mjs` renders the page in an installed headless Chrome at several widths, measures it, flags layout problems (focal point, hero void, edge text, first action) and saves screenshots. Exit codes: 0 clean, 1 at least one FAIL, 2 bad input.
- **Why it matters here**: Mark's rule is that UI is the app and Design stays in the loop (skill `ui-is-the-app-design-in-loop`). Today Design Bot and Reviewer judge pfy-mentat, Leasegrid and Gom Jobbar screens by eye. A lint plus a browser check that exits 1 on slop gives the Tester gate a machine-checkable design floor, and the seeded draw gives Design a reproducible starting direction instead of a blank prompt.
- **Fit on nimo**: Yes. About 320 KB of plain `.mjs`; lint and draw need Node 18+, inspect needs Node 22+ and any Chrome/Chromium (Chrome's DevTools port is local). No keys, no network, no GPU. Clone into `~/DEVELOP/pfy-mentat/tmp/taste-skill`.
- **Verified on the Grok Bot box** (Node 24.14.1 from a tarball under /tmp, system Chrome, bubblewrap with no network, temp HOME; `TASTE_SKILL_HISTORY`, `TASTE_SKILL_TMP`, `TMPDIR` and the XDG dirs in the temp dir): smoke PASS. Lint on a slop fixture exited 1 with exactly `emoji, eyebrow, gradient, lorem, purple`; on a clean fixture exited 0 with no findings; on a missing path exited 2. `draw.mjs --options 3 --seed 7` printed the same menu twice and wrote nothing. A full seeded draw wrote `direction.json` into `--out` and its history only to the temp history file. `inspect.mjs` in headless Chrome failed the slop page (FAIL `gradient`, `emoji`, `eyebrow`, `focal-point`, `edge-text`, `off-centre`) and saved JPEG screenshots, leaving no `ad-chrome-*` profile. Hand mutants (slop fixture swapped for the clean one, an extra expected id) each FAILed.
- **Findings**:
  - **A full draw writes `~/.taste-skill/history.json` by default** and `--out` defaults to `.taste-skill/` in the cwd. Set `TASTE_SKILL_HISTORY` and `--out` on nimo, or the draw memory leaks across projects.
  - **Our "clean" fixture still FAILs `inspect`** (`palette-cream`, `measure`). The browser check is opinionated, beyond the lint. Treat its FAILs as Design's call, not an automatic block, until Design Bot agrees which rules we keep (`--allow rule,rule` exists for that).
  - Chrome itself leaves `~/.local/share/{applications,pki}` and `com.google.Chrome.*` Singleton dirs in `TMPDIR`; the skill's own profile is cleaned. Point HOME/XDG/TMPDIR at temp dirs when a gate runs it.
  - `inspect.mjs` needs Node 22+ (built-in WebSocket); lint and draw run on 18+.
- **Extracted Repos / Tools**: https://github.com/Leonxlnx/taste-skill
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_143_145.py --entry taste-skill`. Looks up `$TASTE_SKILL_DIR`, then `tmp/taste-skill` (a git clone); HEAD pinned to `6010f91a...` (`$TASTE_SKILL_COMMIT`). Node from `$TASTE_NODE`, `tmp/taste-skill/node/bin/node` or PATH; Chrome from `$TASTE_CHROME` or the system PATH. Receipt: `pipelines/smoke/taste-skill/latest.json`.
- **Non-goals**: No `npx skills add`, no copying into any agent's skill dir, no wiring into Design Bot or the Tester gate, no image search (`assets` downloads) from the skill.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Opinionated rules | A deliberate design choice FAILs inspect | Design Bot keeps an `--allow` list per product; lint stays the hard floor |
| Upstream churn | Rule ids or JSON shape change between tags | Commit pin; re-read and bump on purpose |
| Draw memory leak | History in `~/.taste-skill` steers another project's draw | Per-project `TASTE_SKILL_HISTORY`; the smoke watches `~/.taste-skill` |
| Chrome missing or old Node | inspect can't run | The smoke exits 2 with the reason; lint and draw still usable |

- **Status**: Probe on nimo 2026-11-07, PROMOTE I2. App-mode lint 0 FAIL on the operator page and 4 FAIL on a planted page. Inspect 2 FAIL on that page. Tauri binaries 0. See eval/evq1107/taste-skill/VERDICT. Not wired into a gate.
