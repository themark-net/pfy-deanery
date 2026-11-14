### Entry 190: Learn Harness Engineering: project-based course and harness-creator skill for coding-agent harnesses

- **URL**: https://github.com/walkinglabs/learn-harness-engineering (MIT, TypeScript and Markdown). Checked at commit `a9342ff471f2c0e60be0c08b9f4a7c502df4e442` (2026-10-22).
- **Date**: 2026-11-13 (daily X intake)
- **Source / Poster**: watch-list post by @tom_doerr, https://x.com/tom_doerr/status/2121290353730883747
- **Summary / Key Claims** (upstream README; their claims, not verified here): a 14-lecture, 8-project course on the environment, state management, verification and control mechanisms that make coding agents reliable, organised around five subsystems (instructions, tools, environment, state, feedback). Recent lectures cover loop engineering (goal, timer and maker-checker loops, generator/evaluator split) and graph engineering (nodes, edges, shared state, routing, rollback and human-approval nodes). Includes breakdowns of four production harnesses, a `skills/harness-creator` skill that scaffolds AGENTS.md, feature lists, init.sh and verification workflows, and `tools/audit-harness.sh`.
- **Why it matters here**: Deanery is a harness plus a catalog loop. This is a widely used (24k+ stars), open rubric for what a harness should have; it can ground the improvement-vector rubric and the Deanery vs vanilla eval tasks (loop, maker-checker, routing) instead of writing that framing from scratch. `audit-harness.sh` may give a cheap structural check of a repo's harness files.
- **Fit on nimo**: documentation and shell; no GPU, no model needed to read or to run the audit script. Clone under `~/DEVELOP` only.
- **Verified on the Grok Bot box** (2026-11-13): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - 24,544 stars, last push 2026-10-22.
  - It is a course, not a runtime tool; the reusable parts are the five-subsystem framework, the harness-creator skill and the audit script.
- **Extracted Repos / Tools**: https://github.com/walkinglabs/learn-harness-engineering
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_190.py`. Commit-metadata only. Pins `$HARNESSENG_COMMIT`. Fetches via `$HARNESSENG_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/harnesseng/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_190` (7 stub tests).
- **Non-goals**: no skill symlinks into the real agent homes, no rewriting Deanery's own AGENTS.md from the scaffold, no install outside `~/DEVELOP`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Scaffold overwrites harness files | harness-creator run in the real repo | Run it only in a scratch worktree and diff |
| Rubric drift | Course framing taken as fact | Use it as a checklist, score against Deanery's own goals |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto running `tools/audit-harness.sh` on a scratch Deanery worktree and mapping its five-subsystem checklist onto the current rubric to see which improvement vectors are missing.
