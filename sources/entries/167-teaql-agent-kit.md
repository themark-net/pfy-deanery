### Entry 167: TeaQL Agent Kit: model-first build + agent context governance

- **URL**: https://github.com/teaql/teaql-agent-kit (MIT, TypeScript). Checked at commit `92c79101f725655d5356078938742bd633f341a2` (2026-11-06). Workspace package `@teaql/teaql-agent-kit-workspace` `0.0.0`. Ships `skills/build-teaql-app` and `@teaql/agent-context-kit` (context lifetimes, marker-aware file policy, host adapters). Advertises Claude Code, Codex, Cursor, Copilot, Gemini CLI, OpenCode, DeepSeek Harness, and peers.
- **Date**: 2026-11-06 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2118651100601438417 (GitHub reply https://x.com/DanKornas/status/2118651271028543784)
- **Summary / Key Claims** (upstream README; their claims except where marked verified): model-driven harness for builders who already have a coding agent. Workflow: model → evaluate → generate → implement → verify, with progressive API Assist. Separate **Agent Context Kit** governs context lifetimes, file access policy, and verification evidence so agents cannot treat "wrote files" as "verified". One-prompt start: point the agent at this repo's instructions.
- **Why it matters here**: pfy-mentat needs verification gates after agent edits (Tester lesson: content-hash real HOME; Build self-review on green). The context-kit half is the reusable piece even if we never adopt TeaQL app generation. Catalog awareness for harness-engineering patterns next to Entries 100/102/136.
- **Fit on nimo**: Node/TS skills; no NVIDIA. Full kit is large (~40 MB git); installing into real agent homes is out of scope for this smoke. Catalog-only; smoke exits 2 after a matching commit pin.
- **Verified on the Grok Bot box** (2026-11-06): stub tests cover the commit-metadata path. Live GitHub match expected to exit 2.
- **Findings**:
  - Pin is the git commit on `main`; workspace version stays `0.0.0` (monorepo).
  - Runtime enforcement depends on each host adapter; logos do not imply every governance feature is active (upstream caveat).
  - Do not npm-install or copy skills into the operator's agent homes from the smoke.
- **Extracted Repos / Tools**: https://github.com/teaql/teaql-agent-kit · package `packages/agent-context-kit`
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_167.py`. Commit-metadata only. Pins `$TEAQL_COMMIT`. Fetches via `$TEAQL_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/teaql-agent-kit/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_167` (7 stub tests).
- **Non-goals**: No skill install, no paid key, no TeaQL app generation against any repo, no TOOLS.md row. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while the kit was not installed |
| Skill install writes agent homes | copying skills into `~/.claude/skills` | Do not install from this smoke |
| App-generation scope creep | build-teaql-app wants to generate apps | Use only as design reference for context/verification |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: STAY I0 reference (nimo read 2026-11-07). Pin `92c79101f725655d5356078938742bd633f341a2`. Root MIT. Child `@teaql/agent-context-kit` 0.5.0 is Apache-2.0. Docs only, no install, no script run. Context lifetimes and the file policy overlap write-guard, cage, and the 8 exits. Gap B unchanged. Report: `ops:eval/evq1107/teaql-agent-kit/REPORT.md`. Not a Feature GO.
