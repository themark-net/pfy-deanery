# Entry 101 — atg-compile live probe (nimo)

- **Date**: 2026-10-06 (PT)
- **Cite**: Zhang et al. (2026), arXiv:2607.01942. Independent reimplementation in themark-net/atg-framework. Not official ATG code.
- **Summary**: Offline `llamacpp-nommap` lane plus a 10-case atg-compile bench. Live Ollama `qwen3.6:35b` exited 0 with 2/10 valid DAGs and 2/10 sink-correct (repairs 0, wall 478s). The I2 score (2/10 valid, 2/10 sink-correct) was taken at 86d1b890 on build/atg-finish and has not been re-run at the main pin 543e778. Catalog stage moved from I1 to I2 on that pass and stops there. `qwen3-coder-next` was not loaded: the 48.19 GiB blob plus 25 GiB exceeded MemAvailable.
- **Status**: I2 probe. Not Feature GO. Catalog HOLD 70–75. eval-harness untouched.
- **Artifacts**: a private ops note, `pipelines/dogfood/atg-compile/receipt-live-qwen36-35b.json`. Scored SHA `86d1b8905116fb7ec954ee5c4fe0d18f763b7e16` on `build/atg-finish`. Bench pin: `543e778ed24fbf3fc903eb961feb627039019832` on `main`. The I2 score (2/10 valid, 2/10 sink-correct) was taken at 86d1b890 on build/atg-finish and has not been re-run at the main pin 543e778. Point `ATG_REPO` at a clean checkout or worktree of atg `main` at that SHA.
