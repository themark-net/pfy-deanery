### Entry 178: StarSling Skills: agent skills that audit GitHub Actions for speed, config and security

- **URL**: https://github.com/starslingdev/skills (MIT, Python). Checked at commit `14571ad98289d8afd8de1a5b87ddc51909984f30` (2026-11-11).
- **Date**: 2026-11-10 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2120010062630408599 (repo link in the reply https://x.com/DanKornas/status/2120010238791442934)
- **Summary / Key Claims** (upstream README; their claims, not verified here): three repo-audit skills plus one account skill. `ci-speedup` (90+ optimization patterns, reads local workflows and GitHub run history through an authenticated `gh`), `ci-score` (10+ configuration checks, fully offline), `ci-secure` (10+ critical GitHub Actions attack paths, local with optional `gh` checks). Each writes a report and offers fixes in the working tree only; no commit, push or PR unless asked. The fourth skill, `sling`, needs a StarSling account and is out of scope.
- **Why it matters here**: the standing CI rule asks for modular, cached, non-duplicated CI and a check of cataloged tools before any pipeline change. `ci-score` and `ci-speedup` are a direct, read-only second opinion on the pfy-mentat workflows; `ci-secure` is an advisory, deny-only security read.
- **Fit on nimo**: Python 3.9+ and PyYAML only; no GPU, no account for the three audit skills. `ci-speedup` uses the existing `gh` login read-only. Install by copying the skill folders into a worktree, never `npx skills add -g` into agent homes.
- **Verified on the Grok Bot box** (2026-11-10): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - Pattern counts are upstream's own.
  - Skip `sling` (account and billing view).
  - Under the CI rule, a cataloged CI tool cannot reach I3 until it is used on pfy-mentat's own pipeline or a reason is recorded.
- **Extracted Repos / Tools**: https://github.com/starslingdev/skills
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_178.py`. Commit-metadata only. Pins `$STARSLING_COMMIT`. Fetches via `$STARSLING_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/starsling/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_178` (7 stub tests).
- **Non-goals**: no StarSling account, no global skill install, no auto-applied fixes. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while the skills are not installed |
| Skill applies fixes unasked | Workflow files edited | Run in a worktree copy; review diff before landing |
| `gh` token scope too wide | Skill reads more than run history | Use `ci-score` offline first; `ci-speedup` read-only |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: run `ci-score` offline and `ci-speedup` read-only on pfy-mentat's workflows in a worktree and compare findings with the current CI plan.
