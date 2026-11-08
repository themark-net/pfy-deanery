### Entry 121: Tree-sitter Analyzer (TSA) — local code-intelligence MCP and CLI: structure, call graph, blast radius, mis-wire audit

- **URL**: https://github.com/aimasteracc/tree-sitter-analyzer (MIT, Python 3.10+, 55 stars at this read; `tree-sitter-analyzer` 2.2.0 on PyPI)
- **Date**: 2026-10-15 (daily X intake)
- **Source / Poster**: @DanKornas, https://x.com/DanKornas/status/2110822774390309058
- **Summary / Key Claims** (upstream README and `--help`): indexes a codebase with tree-sitter (13 languages) and serves symbol search, structure, call graphs, change impact, file and project health, a refactor queue and a "safe to edit" check to coding agents over MCP (8 facade tools) and a CLI, locally with no telemetry. Its call graph is "family-gated" so a call in one language is not wired to a same-name function in another; `miswire-audit` measures how often a name-only resolver would get that wrong on your repo. Ships `tsa-*` agent skills (`--install-skills`).
- **Why it matters here**: pfy-mentat already catalogs codebase-memory-mcp (`examples/codebase-memory-mcp`, compared with Graphify in `docs/evaluation/codebase-memory-vs-graphify.md`) and Graphify (Entry 017). TSA is a third local option in the same slot, and its `--safe-to-edit`, `--change-impact` and `--trace-from` modes map to what Build and the orchestrator need before editing. Worth adding to that comparison, not replacing anything yet.
- **Fit on nimo**: Yes. Pure Python in a venv under `~/DEVELOP/pfy-mentat/tmp/tree-sitter-analyzer/`. No model, no GPU, no network after install.
- **Verified on the Grok Bot box** (uv venv in `/tmp`, bubblewrap read-only root, no network, temp HOME): `--version` printed 2.2.0; `--structure --output-format json` on a small fixture listed exactly its two functions; `miswire-audit .` indexed python and javascript files, analysed 5 call edges and reported 0 mis-wires for TSA. On this tiny fixture a name-only resolver also scored 0, so the fixture proves the tool runs, not the claimed advantage.
- **Finding**: `miswire-audit` writes `.ast-cache/` into the repo it audits, so run it on a throwaway worktree or gitignore that folder. The README's one-line installer pipes a mutable `uv` installer into bash; use a pinned `pip install` in a venv instead (the smoke expects that).
- **Extracted Repos / Tools**: https://github.com/aimasteracc/tree-sitter-analyzer · https://pypi.org/project/tree-sitter-analyzer/
- **TOOLS.md Link**: None. No TOOLS.md row, no `data/tools.json` row. Stage card `data/stages/tree-sitter-analyzer.json`.
- **Smoke**: `python3 examples/x-intake-local/smoke_119_121.py --entry tsa`. Uses `$TSA_BIN`, then `~/DEVELOP/pfy-mentat/tmp/tree-sitter-analyzer/.venv/bin/tree-sitter-analyzer`, then PATH; `miswire-audit` must be next to it; version pinned 2.2.0 (`$TSA_VERSION` overrides). Receipt: `pipelines/smoke/tsa/latest.json`.
- **Non-goals**: No MCP wiring into any host, no skills installed, no run on pfy-mentat itself in this slice.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| `.ast-cache/` committed by accident | Cache shows up in a diff | Audit only throwaway worktrees; gitignore `.ast-cache/` if it is ever run in a real checkout |
| Claimed advantage doesn't show on our repos | Name-only and TSA score the same | The 2026-11-07 probe on a shared clone scored 52 genuine name-only mis-wires and 0 TSA mis-wires on 62559 edges. Change-impact still agreed with test_select on 5/10 commits, tied with codebase-memory. Report `eval/evq1107/tree-sitter-analyzer/REPORT.md` |
| Unpinned installer | `curl | bash` pulls a moving `uv` | Pinned `pip install` in a venv only |

- **Status**: STAY I1 after the 2026-11-07 nimo probe. Pin PyPI 2.2.0, tag v2.2.0 commit a1656acde0d1065f7670c4d041f81a0e344ef6d7, wheel sha256 678ac7708e238c578ca11fb3433b200a007d14ba954f3eb79d8913c552ba1203. Change-impact agreed with test_select on 5/10 commits, the same count as codebase-memory and ahead of chiasmus at 3/10. The allocated venv is 173 MB, over the 50 MB I2 copy limit. Not a gate. No Feature GO. Report `eval/evq1107/tree-sitter-analyzer/REPORT.md`.
