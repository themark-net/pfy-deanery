### Entry 168: cedr: plan-aware agent routing, multi-vendor review council, skill/MCP pinning, rules sync

- **URL**: https://github.com/Sheernox/cedr (Apache-2.0, Rust). Checked at commit `9cf2683e54a60e2f36f6f11fe715a7906e711597` (2026-11-06), latest release `v0.10.0` (Linux x86_64/arm64 archives with `SHA256SUMS`). Public beta; formats may change before 1.0.
- **Date**: 2026-11-07 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2119217328697040957 (GitHub reply https://x.com/DanKornas/status/2119217500286230915)
- **Summary / Key Claims** (upstream README; their claims, not verified here): one CLI with six parts. **Route** picks agent, model and effort per kind of work from `routes.toml`, sends equal work to the plan with the most room left and skips plans near their limits. **Council** runs one reviewer per vendor, merges findings, blocks on any P0/P1, and never silently passes on too few reports. **Guard** lints the agent setup, pins every skill and MCP server in `.cedr/guard.lock`, and fails CI when a server's tools, descriptions or network hosts change. **Sync** writes rules, skills, MCP servers, permissions and hooks once in `.cedr/` and generates each agent's native files, failing CI on drift. **Monitor** reads local agent logs for tokens and plan headroom. **Bench** runs baseline vs candidate on real tasks with tests deciding each trial.
- **Why it matters here**: nearly every part maps onto an open pfy-mentat concern: usage-aware routing between Grok Build and Cursor (bot-budget doctrine), a fail-closed review gate, pinning skills/MCP against silent drift, one source of truth for rules ported into each agent's files (port-bot-doctrine-to-pfy-sot), and baseline-vs-candidate trials (eval-auto). Stronger fit than most harness entries; worth reading before building any of these in-house.
- **Fit on nimo**: single static-ish Rust binary, glibc 2.34+, no GPU. Harness profiles target Claude/Codex/T3 Code; Grok Build and Cursor CLI support is unverified, so Route/Monitor may need custom harness entries. Self-update runs daily by default; any trial must pin the version and disable updates. `cedr doctor` mentions an account; whether Route/Guard/Sync work fully offline without cedr.dev is unverified.
- **Verified on the Grok Bot box** (2026-11-07): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - Guard and Sync are the parts most likely to work with our agents unchanged (file-based).
  - Council needs multiple vendor reviewers; we only have Grok and Cursor.
  - Do not let the binary self-update or write `~/.config/cedr` from a smoke.
- **Extracted Repos / Tools**: https://github.com/Sheernox/cedr · https://cedr.dev/docs
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_168.py`. Commit-metadata only. Pins `$CEDR_COMMIT`. Fetches via `$CEDR_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/cedr/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_168` (7 stub tests).
- **Non-goals**: no install into agent homes, no cedr.dev account, no paid key, no Route against live plans. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while cedr is not installed |
| Self-update changes behavior mid-trial | daily background update | Pin release, disable update, verify `SHA256SUMS` |
| Sync overwrites hand-edited agent files | `--force` used | Never pass `--force`; run in a worktree first |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto trial of Guard + Sync in a throwaway worktree against our current skill/MCP pinning and AGENTS.md porting. No Feature GO.
