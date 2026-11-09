### Entry 166: odai: evidence-driven agent task governance

- **URL**: https://github.com/orziz/odai (MIT, JavaScript). Checked at commit `ce7a999843ca42ecd84778561cb0ac7642c5648e` (2026-10-29). Odai skill `skillVersion` `0.7.1` (`skills/odai/manifest.json`); CLI package `odai-cli` `0.0.2`. Topics include agent-skills, agentic-workflow, claude-code, codex, dsh-plugin.
- **Date**: 2026-11-06 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2118764357551112380 (GitHub reply https://x.com/DanKornas/status/2118764528292749665)
- **Summary / Key Claims** (upstream README; their claims except where marked verified): governance framework so agents plan and deliver against evidence instead of declaring "done". Aligns goal with facts, schedules capability, holds authorization and risk boundaries, and requires verified acceptance before completion. Ships skills (`odai`, `odai-orchestration`), DSH plugin/agent paths, and a local CLI. Doctrine: ask only when the missing answer changes goal/scope/authorization/acceptance/risk/stop line; verify from files/commands/logs/tests before asking; do not claim tests/reviews that did not happen.
- **Why it matters here**: maps onto pfy-mentat's autonomy loop and the bots' "only ask about material decisions" rule (same family as Entry 154 dsh-superagent authorization docs). Candidate governance skill for Build/Hermes lanes so "done" means verified delivery, not a model claim.
- **Fit on nimo**: CPU/JS only; no NVIDIA. Installing skills or the DSH plugin into a real home is out of this smoke. Catalog-only; smoke exits 2 after a matching commit pin.
- **Verified on the Grok Bot box** (2026-11-06): stub tests cover the commit-metadata path. Live GitHub match expected to exit 2.
- **Findings**:
  - Pin is the git commit; skillVersion `0.7.1` is the useful product pin alongside it.
  - DSH integration exists (`dsh/` tree) — relevant next to Entry 154, but this intake does not install DSH.
  - Upstream includes mood/self-harm response guidance in the README; treat as their product claim, not something we exercise.
- **Extracted Repos / Tools**: https://github.com/orziz/odai
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_166.py`. Commit-metadata only. Pins `$ODAI_COMMIT`. Fetches via `$ODAI_FETCH_BIN` or stdlib GitHub commits API. Does not install skills/plugins. Receipt: `pipelines/smoke/odai/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_166` (7 stub tests).
- **Non-goals**: No skill/plugin install into real agent homes, no DSH global install, no paid key, no TOOLS.md row. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while skills were not installed |
| DSH/plugin sprawl | `build:dsh` / plugin install mutates runtime | Stay at I0; no DSH install from smoke |
| Overlap with 154 | Both speak authorization/verification | Compared in `ops:eval/evq1107/odai/REPORT.md`. Stay I0. Do not double-wire |
| Pin drift | commit moves | Smoke checks this SHA |

- **Status**: STAY I0 reference (read 2026-11-07). Pin `ce7a999843ca42ecd84778561cb0ac7642c5648e`, skillVersion `0.7.1`, MIT. Not a drop-in next to Entry 154: the doctrine overlaps the 8 exits, one-shot, and the testing standing rule. Skills stay uninstalled (smoke still exits 2). No DSH, no hooks. Gap B stays the pfy build timeout. Receipt: `ops:eval/evq1107/odai/REPORT.md`. No Feature GO.
