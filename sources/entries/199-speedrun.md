### Entry 199: Speedrun: black-box YAML end-to-end UI tests for Android, iOS and web

- **URL**: https://github.com/hubastard/speedrun (Apache-2.0, Odin). Checked at commit `19bcdb7d5a073429595fd12bebbe547c82db31a4` (2026-11-17 UTC; 2026-11-16 PT).
- **Date**: 2026-11-16 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2122184370102350274
- **Summary / Key Claims** (upstream README; their claims, not verified here): taps, types, scrolls and asserts from outside the app with nothing added to it; tests are short Maestro-like YAML flows (`launchApp`, `tapOn`, `assertVisible`; `url:` for web). One binary with built-in Android and iOS agents; drives Chrome and Firefox itself with no JVM or WebDriver. Claims a 15-step Android Settings flow in 4.5 s vs 35 s for Maestro, and faster than Playwright and Cypress on web. Ships an MCP mode for agents.
- **Why it matters here**: operator-facing UI is the app, and GUI PRs fail without a launch-and-drive check. A fast black-box runner an agent can write YAML for could back Deanery's GUI launch tests and the Leasegrid Android checks on the emulator.
- **Fit on nimo**: Linux x86_64 release binary or source build into `~/DEVELOP`; no GPU. Android flows need an emulator or device (the Android tester runs one on the operator's computer).
- **Verified on the Grok Bot box** (2026-11-16): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - 111 stars, pushed 2026-11-12. Speed claims come from the author's own bench repo (hubastard/speedrun-bench).
  - Install script is curl-to-bash; use the release binary or a source build in a prefix.
- **Extracted Repos / Tools**: https://github.com/hubastard/speedrun
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_199.py`. Commit-metadata only. Pins `$SPEEDRUN_COMMIT`. Fetches via `$SPEEDRUN_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/speedrun/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_199` (7 stub tests).
- **Non-goals**: no curl-to-bash, no Homebrew, no install outside `~/DEVELOP`, no tests against production accounts. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Flaky emulator runs | Preinstalled emulator apps steal focus on first boot | Warm the emulator first; retry once; record receipts |
| Speed claims don't hold | Author bench not reproducible here | Time our own flow against the current check |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto one Deanery GUI launch flow (web) in Speedrun vs the current launch check.
