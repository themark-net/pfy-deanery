### Entry 080: OpenContext — personal context store + `oc` CLI (knowledge handoff)

- **URL**: https://github.com/0xranx/OpenContext
- **Date**: 2026-09-08 (owner seed #204; implement #205)
- **Poster / source**: Owner queue from [#204](https://github.com/themark-net/pfy-mentat/issues/204) · upstream [0xranx/OpenContext](https://github.com/0xranx/OpenContext)
- **Summary / Key Claims**: Personal context / knowledge store so coding agents reuse background across repos and sessions. CLI `oc` (`@aicontextlab/cli`) manages a global `contexts/` library (folders/docs, keyword search, LLM manifests) plus MCP (`oc mcp`) and optional desktop/web GUI. Reuses the operator’s existing coding-agent CLI (Codex/Claude/OpenCode) instead of shipping a second agent.
- **Extracted Repos / Tools**: https://github.com/0xranx/OpenContext (GitHub SPDX **MIT**; npm `@aicontextlab/cli` 0.2.2 `package.json` claims Apache-2.0 — both permissive). Pin note: `main` @ `0649e7134346f6f5038a9b29cc5c824ae6a54f3f` (2026-06-16). Node ≥18. Default store: `~/.opencontext/contexts` + `~/.opencontext/opencontext.db`.
- **TOOLS.md Link**: **Catalog HOLD this round** — Stage-0 receipt + score note only. No TOOLS.md / `data/tools.json` triple-write. Do not touch catalog PRs 70–75.
- **Notes (Stage-0 gate):**
  - **License:** PASS — repo LICENSE is MIT (commercial/research OK; no copyleft embed issue). npm metadata Apache-2.0 is also permissive; treat GitHub LICENSE as SoT.
  - **Self-host / quickstart:** PASS — `npm install -g @aicontextlab/cli` (<5 min when Node ≥18 is present). CLI-only path does not require the desktop app.
  - **Hello-world:** PASS — documented CLI: `oc folder create` / `oc doc create` (capture) → `oc folder ls` / `oc doc ls` + store keyword scan (search) → `oc context manifest` (reuse). `oc search --mode keyword` still demands an embedding API key in `@aicontextlab/cli` 0.2.2 (native searcher); prove records that as SKIP under LIVE_HARD_OFF and does not call paid embeddings.
  - **Fail closed:** Stage-0 PASSES on those three. Nimo install/run is DoD 2 (`./pfy context`); missing node/oc is honest FAIL + `npm install -g @aicontextlab/cli`, not a silent skip.
  - **Non-goals (#205):** do not clone OpenContext GUI into pfy chrome; do not run `oc ui` from the operator window; do not `oc init` in this repo (would rewrite `AGENTS.md`); Ix (#198) stays parked; do not reopen #76.
- **Score note (initial, not cataloged):** Memory & RAG / agent knowledge-handoff. S1 ~75 (MCP + CLI into existing agents; not a native OpenAI tool-caller itself). S2 N/A (no inference). S3 ~80 (npm CLI, MCP stdio, env `OPENCONTEXT_CONTEXTS_ROOT` / `OPENCONTEXT_DB_PATH`). S4 ~70 (MIT, ~777★, last push 2026-06-16). Overall ~B pending catalog un-HOLD. I3-shaped operator path via `./pfy context` + Attach env; catalog row deferred.
- **Status**: evq1107 2026-11-07 STAY I1. Manifest recall 8/8 on copied notes, 0/8 facts already in this repo, 0 graded with/without cases. Keyword search skipped (no API key). Catalog HOLD remains. No TOOLS.md row. Report: ops:eval/evq1107/opencontext/REPORT.md.
