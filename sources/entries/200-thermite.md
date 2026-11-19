### Entry 200: Thermite: autoresearch harness where agents propose and a separate judge measures

- **URL**: https://github.com/iammrduncan/thermite (Apache-2.0, TypeScript, Node 22.19+). Checked at commit `3c27889fe017a05560aaa62952b172c9db870fce` (2026-11-18 UTC; 2026-11-17 PT).
- **Date**: 2026-11-17 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2122637360777064591
- **Summary / Key Claims** (upstream README; their claims, not verified here): agents run experiments in parallel lanes on their own machines against a metric. Agents only propose a change and a claim; a judge (a project "kit" the agents never see) builds, times and checks each change against the current champion on the same device, re-confirms surprising wins on fresh runs and held-out cases, and keeps a ledger of losses with reasons. Three modes: hill climb, goal (a checklist), research (quotes checked word for word against sources). Dashboard, under heavy development (v0.2.4 release bundle with a compose file).
- **Why it matters here**: this is close to Deanery's eval-auto and self-improvement loop: lanes, a planner, a judge the agent can't edit, and a champion/promotion rule. It is a no-reinvention check for the catalog loop's evaluate-and-promote step and a pattern source for "agents never grade their own work".
- **Fit on nimo**: Node and containers under `$PFY_TMP`; workers would need a local OpenAI-compatible model endpoint (no paid keys). Judge runs on the same device, which suits nimo's single-GPU timing.
- **Verified on the Grok Bot box** (2026-11-17): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - 107 stars, pushed 2026-11-17; README warns it changes daily, pin a release.
  - Uses a release-bundle compose stack; check which agent CLIs and model providers it supports before any trial.
- **Extracted Repos / Tools**: https://github.com/iammrduncan/thermite
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_200.py`. Commit-metadata only. Pins `$THERMITE_COMMIT`. Fetches via `$THERMITE_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/thermite/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_200` (7 stub tests).
- **Non-goals**: no hosted service, no paid model keys, no install outside `$PFY_TMP`, no GPU run without a go. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Upstream churn | Daily breaking changes | Pin a tagged release bundle |
| Runaway campaign | No default caps on turns or wall time | Set an explicit time and lane cap per campaign |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto on one past Deanery eval task (judge kit = existing test/metric) against the current catalog-loop evaluate step.
