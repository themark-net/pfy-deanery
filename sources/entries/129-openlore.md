### Entry 129: OpenLore - deterministic local code memory plus breaking-change guardrails for coding agents

- **URL**: https://github.com/clay-good/OpenLore (MIT, TypeScript; 341 stars at this read; npm `openlore` 3.3.1, tag `v3.3.1` at `f33d3b2fbcd3`, 2026-10-10)
- **Date**: 2026-10-17 (daily X intake)
- **Source / Poster**: @DanKornas, https://x.com/DanKornas/status/2111321050457747779
- **Summary / Key Claims** (upstream README at 3.3.1): one static-analysis pass (tree-sitter, 21 languages plus IaC) builds a local graph of functions, callers, tests, specs and decisions. `orient(task)` returns the code a task touches in one call; `certify-public-surface --base <ref>` classifies changed exports as breaking / potentially-breaking / non-breaking and names each consumer; `review`, `blast-radius`, `coverage-gaps`, `env-impact` and `enforce` (a commit gate) work the same way. No LLM in the hot path, no API key; keyword (BM25) search by default, optional on-device embeddings. Ships an MCP server and `install`/`connect` commands that wire Claude Code, Cursor, Cline, Continue, Pi and `AGENTS.md`.
- **Why it matters here**: it attacks two things on our list at once: agents re-reading the repo every task (Build drop-ins, local `qwen3.6:35b` with small context) and changes that silently break callers before Tester sees them. The breaking-change verdict is deterministic, so it can run as a cheap pre-PR check in Build or bot runs. It overlaps codebase-memory-mcp (code-graph toolset) and Entry 121 (Tree-sitter Analyzer) on retrieval, but adds the governance half they don't have.
- **Fit on nimo**: Yes, but heavier than it looks: Node **^22.19 or >= 23.5** (nimo's Node version unconfirmed; a Node 22 tarball can be unpacked under `~/DEVELOP/pfy-mentat/tmp/node`) and an npm prefix under `~/DEVELOP/pfy-mentat/tmp/openlore` of about **1.7 GB** (the box install added 322 packages; the lockfile lists 393; mostly onnxruntime and LanceDB for optional embeddings). CPU only; no GPU needed.
- **Verified on the Grok Bot box** (Node 22.20.0, `npm install --prefix /tmp/... --ignore-scripts openlore@3.3.1`; bubblewrap, no network, temp HOME): smoke PASS. `orient` ranked `applyDiscount` first; adding a required parameter gave `breaking` with `checkout` as consumer and suggested a major bump; after restoring the file the verdict was `non-breaking`; only the `.gitignore` that `init` writes appeared in the repo; temp HOME and the watched real-HOME dirs (`~/.openlore`, `~/.pi/agent/extensions`) unchanged. Node 20 gives exit 2.
- **Findings**: (1) **`analyze` exits 0 even when its index build panics** (its LanceDB layer panics on a read-only `/tmp`, and `orient` then says "No analysis found"), so checks must read `orient` output, not exit codes; the smoke sets `TMPDIR` inside its temp dir. (2) It **checks registry.npmjs.org for updates** unless `OPENLORE_NO_UPDATE_NOTIFIER=1`, and caches that in `~/.openlore/`; telemetry is off unless `OPENLORE_TELEMETRY=1`. (3) `install`, `connect` and `setup` write host agent configs, a SessionStart hook and `~/.pi/agent/extensions`; never run them with the real HOME. (4) `init` edits the project's `.gitignore` and creates `openspec/`.
- **Extracted Repos / Tools**: https://github.com/clay-good/OpenLore · https://www.npmjs.com/package/openlore
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_128_130.py --entry openlore`. Looks up `$NODE_BIN`, `tmp/node/bin/node`, then PATH, and `$OPENLORE_DIR` or `tmp/openlore`; package version pinned to 3.3.1. Temp TS fixture repo only. Receipt: `pipelines/smoke/openlore/latest.json`.
- **Non-goals**: No `install`/`connect`/`setup`, no MCP registration in any host, no embeddings model download. The nimo probe did run on this repo; see the status line.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Silent partial index | `analyze` says OK, `orient` has nothing | Check `orient`/`status` output; keep `TMPDIR` writable |
| Host config written | Hooks or MCP entries appear in Mark's real agent config | Never run `install`/`connect`/`setup` outside a temp HOME |
| Disk and Node footprint | 1.7 GB prefix, Node 22 needed | Stage under `tmp/`, delete the prefix after a trial |
| Overlap with code-graph tools | Two indexes doing the same job | Trial against codebase-memory-mcp on the same tasks before keeping both |

- **Status**: STAY I1. nimo probe 2026-11-07: module-level contract 4/4, 0 false breaks on 10 commits, method break missed, prefix 708 MB. See eval/evq1107/openlore/REPORT.md.
