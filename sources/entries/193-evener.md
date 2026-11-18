### Entry 193: Evener: self-hosted coding-agent hub with browser, CLI and scripted sessions, Ollama supported

- **URL**: https://github.com/prime-radiant-inc/evener (MIT, Go). Checked at commit `965b90b51a1770afa14e52443bff29e70e8492d1` (2026-11-15 UTC; 2026-11-14 PT).
- **Date**: 2026-11-14 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2121572847239729273
- **Summary / Key Claims** (upstream README and docs; their claims, not verified here): a coding agent that reads files, runs commands, edits code and checks results. `evener hub` connects a browser UI (follow and steer), a CLI for scripted tasks, and an iPhone client to sessions; docs cover sessions, delegates, jobs, memory, sandboxing, and per-project launch files with content-hash trust approval for repo-supplied commands and MCP servers. Provider registry includes `ollama` (no key required) and generic `openai-compatible` endpoints, with an explicit "never the default" rule for Ollama models. Prebuilt installer for Linux x64 puts the binary under `~/.local/share/evener/bin`.
- **Why it matters here**: another harness to compare against OpenCode/jcode (174) lanes and vanilla Grok Build, with features Deanery cares about: scripted CLI runs, delegate jobs, local-model routing through Ollama, and trust-by-content-hash for repo-provided commands (a pattern for the predefined auto-promotion rules). From the Prime Radiant team.
- **Fit on nimo**: Linux x64 prebuilt or Go source build; point the provider at the local Ollama (qwen3.6 35B default). Install into a prefix under `$PFY_ROOT` with an isolated HOME/XDG dirs so it does not write `~/.local` or `~/.config`.
- **Verified on the Grok Bot box** (2026-11-14): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - 197 stars, pushed minutes before this run; docs say tagged releases lag `main`.
  - Live provider auth is listed by upstream as an untested prerequisite of its own walkthrough.
- **Extracted Repos / Tools**: https://github.com/prime-radiant-inc/evener
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_193.py`. Commit-metadata only. Pins `$EVENER_COMMIT`. Fetches via `$EVENER_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/evener/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_193` (7 stub tests).
- **Non-goals**: no hub exposed beyond localhost, no iPhone client, no cloud provider keys, no install outside `$PFY_ROOT`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Writes outside `$PFY_ROOT` | Installer and XDG defaults use `~/.local` and `~/.config` | Set HOME/XDG dirs to a scratch prefix |
| Hub exposed | `--addr` bound beyond localhost | Bind 127.0.0.1 only |
| Fast-moving main | Snapshot behavior changes between runs | Smoke checks this SHA; trial from the pinned build |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto running one stalled-lane task through Evener CLI on the local Ollama default next to the current OpenCode lane, scored on pass/fail, wall time and tokens.
