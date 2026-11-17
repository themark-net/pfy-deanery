### Entry 198: Miniforge: spec-to-PR autonomous software factory (OpenCode, Claude Code or Codex backends)

- **URL**: https://github.com/miniforge-ai/miniforge (Apache-2.0, Clojure/Babashka). Checked at commit `fe703740b7e193561284329d7dc540687a989ec2` (2026-11-17 UTC; 2026-11-16 PT).
- **Date**: 2026-11-16 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2122365593097572492
- **Summary / Key Claims** (upstream README; their claims, not verified here): write a spec (plain English or EDN), run `mf run spec.edn`, and Miniforge plans, writes code, runs tests, lints, reviews itself and opens a PR ("full SDLC", "factory, not a chatbot"). LLM backend is the OpenCode, Claude Code or Codex CLI; work runs in an OCI container runtime (Podman).
- **Why it matters here**: it overlaps Deanery's own Think-Plan-Build-Review-Test-Ship pipeline. Under the no-reinvention rule it is a direct comparison target: if it drives a stalled lane to a reviewed PR better than Deanery does, adopt its pieces.
- **Fit on nimo**: OpenCode backend pointed at the local model keeps it local-only; Podman rootless. `bb bootstrap` installs Java, Clojure CLI, clj-kondo, Polylith and markdownlint and puts `mf` in `~/.local/bin`, so a trial needs a prefix under `~/DEVELOP` instead of the default bootstrap.
- **Verified on the Grok Bot box** (2026-11-16): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - 58 stars, pushed 2026-11-16.
  - Bootstrap writes outside `~/DEVELOP` (`~/.local/bin/mf`, toolchains); Babashka install path offers `bash <(curl ...)`.
  - Opens PRs itself; a trial must target a scratch repo, never themark-net mains.
- **Extracted Repos / Tools**: https://github.com/miniforge-ai/miniforge
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_198.py`. Commit-metadata only. Pins `$MINIFORGE_COMMIT`. Fetches via `$MINIFORGE_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/miniforge/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_198` (7 stub tests).
- **Non-goals**: no default `bb bootstrap` into HOME, no curl-to-bash, no PRs to real repos, no Claude/Codex paid backends. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Writes outside DEVELOP | Bootstrap installs toolchains and `mf` in HOME | Containerised or prefixed install under `~/DEVELOP` |
| PRs on real repos | Factory opens a PR against a product repo | Scratch repo and token scoped to it |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto one past Deanery lane spec through Miniforge (OpenCode on the local model) vs the Deanery pipeline, on a scratch repo.
