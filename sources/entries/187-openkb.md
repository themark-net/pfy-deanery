### Entry 187: OpenKB: compile documents into a maintained Markdown wiki with vectorless, reasoning-based retrieval

- **URL**: https://github.com/VectifyAI/OpenKB (Apache-2.0, Python, PyPI `openkb` 0.4.5). Checked at commit `ff54396e575ee6feb0113b631a34caa082b441cc` (2026-07-22).
- **Date**: 2026-11-12 (daily X intake)
- **Source / Poster**: watch-list post by @tom_doerr, https://x.com/tom_doerr/status/2120999145360027817
- **Summary / Key Claims** (upstream README; their claims, not verified here): a CLI (plus a bundled local web workbench) that compiles PDFs, Office files, Markdown, HTML and URLs into an interlinked wiki of summaries, concept pages and entity pages, flags contradictions, and keeps it current as documents are added (the "LLM wiki" idea). Long documents use PageIndex tree indexing, which runs locally by default, with no vector database. Query and chat over the wiki; a Skill Factory distils agent skills from it. Plain `.md` output, Obsidian-compatible. Any LiteLLM provider, including Ollama and LM Studio.
- **Why it matters here**: the catalog is a pile of sources, entries and READMEs that every fit check re-reads from scratch. OpenKB is an existing way to compile that into a maintained knowledge base with cross-links and contradiction flags, using a local model. Compare it with the current flat entries before adding more in-house summarising.
- **Fit on nimo**: no GPU needed by OpenKB itself; compile and query calls go to a model through LiteLLM, so point it at the local default model on nimo via Ollama. pip into a venv under `~/DEVELOP`. The optional PageIndex cloud features need a key and are out of scope.
- **Verified on the Grok Bot box** (2026-11-12): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - 4883 stars, PyPI 0.4.5, last push 2026-07-22.
  - Compile cost scales with corpus size and model speed; a full catalog compile on a local model could take a long time, so start with a slice.
- **Extracted Repos / Tools**: https://github.com/VectifyAI/OpenKB, https://github.com/VectifyAI/PageIndex
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_187.py`. Commit-metadata only. Pins `$OPENKB_COMMIT`. Fetches via `$OPENKB_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/openkb/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_187` (7 stub tests).
- **Non-goals**: no cloud model provider, no `PAGEINDEX_API_KEY`, no skill symlinks into the real agent homes, no exposed workbench (loopback only), no install outside `~/DEVELOP`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Cloud spend | Default model is a cloud model | Set an Ollama model in `.openkb/config.yaml` before `add` |
| Workbench exposed | Auth is off by default | Bind to 127.0.0.1 only |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto on a 30-entry slice of `sources/entries/` with the local default model: answer ten known catalog questions (overlaps, licences, nimo fit) from the compiled wiki versus from a plain grep, scoring accuracy and wall time.
