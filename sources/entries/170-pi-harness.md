### Entry 170: Pi-Harness: runs, trace, replay, evaluation and recovery around Pi Coding Agent

- **URL**: https://github.com/wangmiaozero/pi-harness (AGPL-3.0, TypeScript). Checked at commit `5b6ec2318d6741e444bfe8a640432be052e509fc` (2026-11-08 UTC), latest release `v2.3.20`. Wraps [Pi Coding Agent](https://github.com/earendil-works/pi).
- **Date**: 2026-11-07 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2118968179145748718 (GitHub reply https://x.com/DanKornas/status/2118968350550474833)
- **Summary / Key Claims** (upstream README; not verified here): desktop workspace and control plane for Pi. Pi runs the agent loop; Pi-Harness adds Runs, Trace, Replay, Run Compare and Evaluation for investigating failures from recorded evidence; Policy, Budget, Checkpoints and Recovery to resume, fork or retry work; and Agent Teams with a task DAG, review gates and isolated worktrees. Installers bundle Pi and Node.js for macOS, Windows and Linux.
- **Why it matters here**: Pi can drive local models, so this is one of the few harness control planes that could run against nimo's Ollama without paid keys. The run/trace/replay/compare model is what pfy-mentat's lane receipts and eval verdict files approximate. Worth comparing against our lane drivers before building more run inspection in-house.
- **Fit on nimo**: Electron-style desktop app; nimo is mostly headless, so a trial would need a display or the box desktop. AGPL means reference-only unless we keep any use internal and unmodified. Catalog-only.
- **Verified on the Grok Bot box** (2026-11-07): commit pin matched; smoke exits 2. 7 stub tests pass.
- **Findings**:
  - Repo is very active (pushes within the hour of this intake); pin matters.
  - Pi itself is not yet a catalog entry; check before any trial.
- **Extracted Repos / Tools**: https://github.com/wangmiaozero/pi-harness · https://github.com/earendil-works/pi
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_170.py`. Commit-metadata only. Pins `$PIHARNESS_COMMIT`. Fetches via `$PIHARNESS_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/pi-harness/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_170` (7 stub tests).
- **Non-goals**: no desktop install, no Pi install, no paid key. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while not installed |
| AGPL obligations | code copied into pfy-mentat | Reference only; no code reuse |
| Desktop app on headless nimo | no display | Trial on a desktop host or skip |
| Pin drift | `main` moves fast | Smoke checks this SHA |

- **Status**: STAY I0 reference (read 2026-11-08). Pin `5b6ec2318d6741e444bfe8a640432be052e509fc` is tag v2.3.23, AGPL-3.0-only. No install and no code copy. H1 stays with skill-up. Receipt: `ops:eval/evq1107/pi-harness/REPORT.md`. No Feature GO.
