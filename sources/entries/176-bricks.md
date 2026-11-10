### Entry 176: Bricks: component contracts and governance skills for agents building UI

- **URL**: https://github.com/kostja94/bricks (MIT). Checked at commit `b110aa2808a7be0f74bac1142bb2ad2ef70b2a56` (2026-11-06).
- **Date**: 2026-11-09 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2119919451470446744 (repo link in the reply https://x.com/DanKornas/status/2119919626637156798)
- **Summary / Key Claims** (upstream README; their claims, not verified here): Agent Skills, not a component library. `component-builder` builds a missing component in its real page context after reading routes, tokens and conventions; `component-inventory` maps pages to components into a project-owned `docs/component-system.md`; `component-auditor` finds semantic duplicates and drift; `component-cleanup` removes verified-unused UI. Machine-readable catalog in `catalog/components.json` with stable component ids, including agent-interface concepts (Task Input, Conversation, Chat Panel, Agent Workspace). Installed with `npx skills add kostja94/bricks --skill <name>`.
- **Why it matters here**: the operator GUI (`gui/operator`) is built and changed by agents, and the rule is that UI is the app with Design in the loop. Plain `SKILL.md` files are harness-neutral, so the inventory and auditor skills could run in Grok Build or opencode lanes to keep the GUI from growing duplicate components, and the Agent Workspace contract is a checklist for the operator console.
- **Fit on nimo**: text-only skills, no GPU, no keys. The `npx skills add` installer writes into agent skill folders in the home directory; a trial should copy the `SKILL.md` files into a worktree instead.
- **Verified on the Grok Bot box** (2026-11-09): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - Content is skewed toward marketing-site components (footer, CTA, testimonials); only the agent-interface and governance parts are relevant.
  - Some guidance routes host-specific copy to a sibling project (Pagina); ignore that.
- **Extracted Repos / Tools**: https://github.com/kostja94/bricks
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_176.py`. Commit-metadata only. Pins `$BRICKS_COMMIT`. Fetches via `$BRICKS_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/bricks/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_176` (7 stub tests).
- **Non-goals**: no `npx skills add` into real agent homes, no GUI rewrite. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while the skills are not vendored |
| Installer writes agent homes | `npx skills add` default targets | Copy SKILL.md files into a worktree only |
| Skills push a redesign | auditor proposes broad changes | Run audit-only; Design decides |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: run `component-inventory` in audit-only mode on `gui/operator` in a worktree and have Design review the output.
