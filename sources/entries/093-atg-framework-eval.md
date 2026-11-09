# Entry 093 — atg-framework evaluation + toolset ranking + Build drop-ins

- **Date**: 2026-10-06 (PT)
- **Cite**: OQ-0004 · issues #22, #30 · atg-framework `29bca8a` · branch `bot/atg-eval`
- **Summary / Key Claims**: atg-framework (an independent reimplementation of Zhang et al. 2026, arXiv:2607.01942) has the full compile → thought experiment → parallel execute → LCA repair loop in code, with 35 unit tests green and the offline toy passing. It is **not yet a paper PoC**: the live compile went 0/3 on 2026-10-05, there is no baseline or metric suite, and the client is native Ollama only. pfy should **adapt** it (compile bench on the local-bench harness, decision lane as judge, opt-in `atg` loop kind) and **skip** embedding it. Toolset ranking: llama-server no-mmap lane, ATG, DSPy on #230, destructive_command_guard and opencode-mem lead.
- **Method**: Read-only review of the code, Decisions 0011–0020, NEXT and USING. Tests ran on a /tmp copy. Catalog and vendor read-through. No model loaded (host bench running).
- **Status**: **I1 unchanged / no promotion.** The catalog card is stale ("No runnable core"). Refreshing it is in a private ops note. Not a Feature GO.
- **Artifacts**: `docs/eval/ATG-FRAMEWORK-EVAL.md`, `docs/eval/TOOLSET-RANKING.md`, a private ops note, private ops notes*`
