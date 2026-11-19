### Entry 202: CompozyOS: local control plane for always-on coding-agent sessions

- **URL**: https://github.com/compozy/compozy (MIT, Go). Checked at commit `29cf4a69b0e207f4ffbf0decd468264cd8f4b611` (2026-11-18 UTC; 2026-11-17 PT).
- **Date**: 2026-11-17 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2122614711363494152
- **Summary / Key Claims** (upstream README; their claims, not verified here): runs the agent CLIs you already have (Claude Code, Codex, Cursor) as sessions that outlive the terminal; always-on agents check in on their own and surface only when they need a human; replaces glued-together loops, cron, webhooks and approvals. Has a downloadable app, docs and a marketplace.
- **Why it matters here**: this is the same job as Deanery's loop and operator queue (scheduled lanes, approvals, "needs the operator" surfacing). It is a no-reinvention comparison target, not a drop-in; check whether its loop and approval model can run on local models only.
- **Fit on nimo**: Go binary under `$PFY_TMP`; whether it works with OpenCode or a local model, and without an account, is unverified.
- **Verified on the Grok Bot box** (2026-11-17): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - About 2.9k stars, pushed 2026-11-18 UTC.
  - Marketplace and download links suggest a hosted component; confirm the local-only path before any trial.
- **Extracted Repos / Tools**: https://github.com/compozy/compozy
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_202.py`. Commit-metadata only. Pins `$COMPOZY_COMMIT`. Fetches via `$COMPOZY_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/compozy/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_202` (7 stub tests).
- **Non-goals**: no account sign-up, no hosted control plane, no install outside `$PFY_TMP`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Needs an account | Local mode requires sign-in | Keep at I0 as a comparison reference |
| Supported agents only | No OpenCode/local model path | Stop at catalog; compare design only |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: design comparison against Deanery's loop and operator queue; trial only if a local-only path exists.
