### Entry 177: renderlint: linter for the rendered UI that agents ship

- **URL**: https://github.com/ngocanhnckh/renderlint (MIT, JavaScript, Node >= 18.17). Checked at commit `de107c28084823103fc951fcca1cbac6f61b09b6` (2026-11-10). npm package `@ngocanhnckh/renderlint`.
- **Date**: 2026-11-10 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2120168588371759313 (repo link in the reply https://x.com/DanKornas/status/2120168764243337399)
- **Summary / Key Claims** (upstream README; their claims, not verified here): opens the app in a real browser, renders each page at phone, tablet and desktop widths plus dark mode, sweeps the widths in between, re-checks with longer text and data, and reports visual defects (text overflow, clipped headings, low contrast, overlapping chart labels, `$undefined` values, emoji in place of icons) with element, source file, annotated screenshot and a fix in plain text an agent can act on. Fails the build until errors reach 0.
- **Why it matters here**: operator-facing UI PRs are FAIL unless they are actually launched and looked at. A deterministic rendered-UI check that an agent can read would give Build and the review step a machine-checked signal before a human or bot looks at screenshots. Advisory, read-only on the app under test.
- **Fit on nimo**: no GPU. Needs Node and a headless Chromium (Playwright-style). `init` edits AGENTS.md, adds a build gate and a Claude Code hook; a trial must run `npx renderlint` against a worktree copy with a throwaway HOME and npm cache under `~/DEVELOP`, never `init` in the main checkout.
- **Verified on the Grok Bot box** (2026-11-10): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - Defect classes and the gallery are upstream's own; reproduce on one pfy-mentat UI page before trusting them.
  - `init` writes agent instruction files and hooks; keep it out of homes and the main checkout.
- **Extracted Repos / Tools**: https://github.com/ngocanhnckh/renderlint
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_177.py`. Commit-metadata only. Pins `$RENDERLINT_COMMIT`. Fetches via `$RENDERLINT_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/renderlint/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_177` (7 stub tests).
- **Non-goals**: no `init` in a real checkout, no Claude Code hook, no install outside `~/DEVELOP`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while renderlint is not installed |
| `init` rewrites agent files | AGENTS.md and hooks changed | Run only `npx renderlint` in a worktree copy |
| No headless browser on the host | Chromium download fails | Record exit 2; point at an existing Chrome binary |
| Pin drift | `master` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: run it once against one operator-facing UI page in a worktree and compare its findings with the last human or bot UI review.
