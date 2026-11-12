### Entry 183: Commit Check: commit, branch, author and file policy as code for teams and agents

- **URL**: https://github.com/commit-check/commit-check (MIT, Python 3.11+). Checked at commit `0659e65a4cd9d848b0f377aefb0382ad01666973` (v2.20.5 docs, 2026-11-11).
- **Date**: 2026-11-11 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2120395094507356442 (repo link in the reply https://x.com/DanKornas/status/2120395270655709580)
- **Summary / Key Claims** (upstream README; their claims, not verified here): one `cchk.toml` drives checks in a pre-commit hook, CI, a GitHub Action, an agent skill, a Python API and an MCP server. Rules cover Conventional Commits, subject length and mood, WIP/fixup commits, sign-off, AI attribution (forbid it or require an `Assisted-by:` line), author name and email, branch names, force push, committed file size and forbidden paths, and tag names. `--format json` gives stable rule IDs; `--fix` corrects mechanical slips.
- **Why it matters here**: lanes push many commits headless. The public-repo rules (no operator name, no home paths, no ops files) are enforced today by `scripts/check_public_paths.py`; Commit Check covers the commit-metadata side (author fields, forbidden paths, AI attribution, message shape) with machine-readable output that fits the predefined-rules pipeline. It is a deny-only, read-only check, which is the class the auto-promotion rules allow.
- **Fit on nimo**: no GPU. `pip install commit-check` into a venv under `~/DEVELOP`. Offline by default. The GitHub App path is not used (account install).
- **Verified on the Grok Bot box** (2026-11-11): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - Active since 2022, 95 stars, OpenSSF Scorecard badge and coverage on CI.
  - `check-files` forbidden paths overlaps `check_public_paths.py`; the trial should decide whether it replaces or sits beside it.
- **Extracted Repos / Tools**: https://github.com/commit-check/commit-check
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_183.py`. Commit-metadata only. Pins `$COMMITCHECK_COMMIT`. Fetches via `$COMMITCHECK_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/commitcheck/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_183` (7 stub tests).
- **Non-goals**: no GitHub App install, no hooks in the operator's main checkout, no `--fix` rewriting commits that are already pushed, no install outside `~/DEVELOP`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Hook blocks lane commits | Strict Conventional Commits on existing history | Start report-only (`--format json`, no hook) |
| Overlap with path guard | Two guards disagree | Trial compares both on the same commit range |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto run of `commit-check --message --author-name --author-email --files --format json` over the last 50 main commits next to `check_public_paths.py`, counting real catches and false positives.
