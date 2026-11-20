### Entry 205: vibecosystem: profile-based agents, skills and hooks runtime for Claude Code and Codex

- **URL**: https://github.com/vibeeval/vibecosystem (MIT; GitHub lists C#, the installer and hooks are Bash and Node). Checked at commit `9ef6d7266b2d4e9ee1d3460a3e2f3bda8a9c187a` (2026-11-11 UTC; 2026-11-11 PT).
- **Date**: 2026-11-19 (daily X intake; post seen 2026-11-17 PT, queued 2026-11-18)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2122886516808503565
- **Summary / Key Claims** (upstream README; their claims, not verified here): packages agents, skills and hooks for software work as profiles. The default `core` profile installs a selected set for investigation, implementation, review and verification; `quality`, `context`, `memory`, `orchestration` and `dashboard` are opt-ins, and `full` is 138 agents, 296 skills and 20 rules. Context-producing hooks are capped at 4,000 characters per event and 12,000 per session on lean profiles. Has a dry-run install and `vibeco effective-config`, `doctor` and `stats` diagnostics; a separate Codex adapter.
- **Why it matters here**: Deanery ships its own skill packs and keeps them pinned. The profile split (small default, explicit opt-ins, per-event context caps, a doctor command) is a pattern source for keeping lane prompts small. It is a design reference, not an install: it targets Claude Code and Codex, not Grok Build or OpenCode.
- **Fit on nimo**: Node 18+ and Bash; the source installer writes into the agent's home config and `~/.local/bin`, so any look must use a throwaway HOME under `$PFY_TMP` and the `--dry-run` flag. The remote installer script is out of scope.
- **Verified** (2026-11-19): commit pin matched via `git ls-remote` and the GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - About 550 stars, created 2026-03-14 UTC, last push 2026-11-11 UTC; npm release 3.5.x.
  - Skills from this pack must never be loaded into a lane; per Deanery's injection rules they are data to read, not instructions.
- **Extracted Repos / Tools**: https://github.com/vibeeval/vibecosystem
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row. Stage card `data/stages/vibecosystem.json`.
- **Smoke**: `python3 examples/x-intake-local/smoke_205.py`. Commit-metadata only. Pins `$VIBECOSYSTEM_COMMIT`. Fetches via `$VIBECOSYSTEM_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/vibecosystem/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_205` (7 stub tests).
- **Non-goals**: no hook registration in any real agent home, no remote installer, no skills loaded into lanes, no install outside `$PFY_TMP`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Writes into a real agent home | Installer edits hook registrations | Dry run only, throwaway HOME under `$PFY_TMP` |
| Skills read as instructions | Pack text reaches a lane prompt | Read as data only; never load into a lane |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0 reference. Next step, if any: read the profile manifest and context caps against Deanery's skill packs; no install.
