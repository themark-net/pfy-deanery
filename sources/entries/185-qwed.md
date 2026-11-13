### Entry 185: QWED: deterministic, fail-closed verification of LLM and agent output (SymPy, Z3, SQLGlot, AST)

- **URL**: https://github.com/QWED-AI/qwed-verification (Apache-2.0, Python, PyPI `qwed` 9.1.0). Checked at commit `5d43b993d8a02348e4830eade60355e74d604126` (2026-11-12).
- **Date**: 2026-11-12 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2120734823513739438 (repo link in the reply https://x.com/DanKornas/status/2120734994570318191)
- **Summary / Key Claims** (upstream README; their claims, not verified here): a verification layer that checks claims in model output with deterministic engines (SymPy for math, Z3 for logic, SQLGlot for SQL, Python AST for code) and fails closed: a claim it cannot check is `UNVERIFIABLE`, never `VERIFIED`. Results carry `status` (`VERIFIED` / `UNVERIFIABLE` / `BLOCKED`) and an `admission` (`ADMIT` / `BLOCKED`), with a SHA-256 `proof_ref`. Nine policy guards (SystemGuard for shell commands and file paths, ConfigGuard for secrets in config, MCPPoisonGuard for MCP tool definitions, ExfiltrationGuard, and others) return block or hold decisions locally with no server or model. Runs as a library, CLI, self-hosted API or Docker image.
- **Why it matters here**: catalog promotion and lane gating now run on predefined machine-checked rules instead of human sign-off. QWED is a ready-made library of exactly that kind of deny-only, deterministic check (shell commands, file paths, secrets in config, poisoned MCP tool descriptions). Per the no-reinvention rule, compare its guards with the in-house public-path and destructive-command checks before writing more of our own.
- **Fit on nimo**: no GPU for the deterministic engines and guards. Only the natural-language and logic routes call an LLM, and those can point at a local Ollama model. pip into a venv under `~/DEVELOP`; the server and Docker image need several secrets and are out of scope for a trial.
- **Verified on the Grok Bot box** (2026-11-12): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - 73 stars, v9.1.0, last push 2026-11-12. Fast-moving: open issues #320 and #581 list known fail-closed exceptions on the logic and consensus routes.
  - `qwed init` creates a local API key and model config: run it only with a throwaway HOME.
- **Extracted Repos / Tools**: https://github.com/QWED-AI/qwed-verification
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_185.py`. Commit-metadata only. Pins `$QWED_COMMIT`. Fetches via `$QWED_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/qwed/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_185` (7 stub tests).
- **Non-goals**: no server or Docker deploy, no `qwed init` against the real HOME, no cloud model provider, no install outside `~/DEVELOP`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Guard used as an allow-list | `ADMIT` read as "safe" on routes with known exceptions | Use guards deny-only; treat `UNVERIFIABLE` as not verified |
| NL route leaks prompts | Default provider is a cloud model | Local Ollama model only, or skip the NL routes |
| Pin drift | `main` moves daily | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto, report-only: run SystemGuard and ConfigGuard over the last 200 lane shell commands and changed config files next to the current in-house checks, and count real catches against false positives.
