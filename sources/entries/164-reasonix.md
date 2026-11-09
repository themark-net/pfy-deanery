### Entry 164: Reasonix: DeepSeek-native coding agent (studio release pin)

- **URL**: https://github.com/esengine/DeepSeek-Reasonix (MIT). Release tag `studio-v2.57.0` at commit `737a181c49367a7a153c71889c168638fcfc0ba3` (2026-11-02). Linux CLI asset `reasonix-linux-amd64.tar.gz`, size `40362566`, digest `sha256:c227bbc08c65af27dbcc49aae84e115a912123a3e2b7902a6668acda75fb948f`. Upstream describes a DeepSeek-native AI coding agent for the terminal, engineered around prefix-cache stability. Active Go line lives on `main-v2` / studio releases; the older TypeScript `main` line is marked maintenance-only in the README.
- **Date**: 2026-11-05 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2118515218531704876 (GitHub reply https://x.com/DanKornas/status/2118515389940342826)
- **Summary / Key Claims** (upstream README; their claims except where marked verified): a coding agent that reads code, edits files, and runs tests inside a chosen project folder, with SEARCH/REPLACE apply flow so nothing lands on disk until `/apply`. Marketed as DeepSeek-native with low token cost across long sessions. Also ships ReasonixStudio desktop and mobile APK assets on the same release (not this smoke's pin).
- **Why it matters here**: another sandboxed coding-agent harness to compare with Hermes, Grok Build, Cursor, and dsh-superagent (154). Useful as a DeepSeek-oriented reference for long sessions; not a replacement for the current Build self-review path.
- **Fit on nimo**: Metadata check fits. Running the agent wants a model provider (hosted DeepSeek or other keys; local support not verified here) and write access to a project folder. Smoke exits 2 after a matching pin and does not unpack or run the CLI.
- **Verified on the Grok Bot box** (2026-11-05): stub tests cover the metadata path. Live GitHub match expected to exit 2 with `FAIL_CANNOT_RUN_HERE`.
- **Findings**:
  - Pin is the CLI tarball, not ReasonixStudio AppImage (~179 MB) or the APK.
  - DanKornas titles the tool "Reasonix"; the GitHub org path is still `DeepSeek-Reasonix`.
  - A matching release is still exit 2. Exit 0 would mean the CLI ran. It did not.
- **Extracted Repos / Tools**: https://github.com/esengine/DeepSeek-Reasonix · release `studio-v2.57.0` · compare with Hermes (134) and dsh-superagent (154)
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row, no stage card.
- **Smoke**: `python3 examples/x-intake-local/smoke_164.py`. Uses `run_isolated`, `find_bin`, `pinned`, and `timeout_reason`, with `kill_on_exit=True`. Reads release JSON through `$REASONIX_FETCH_BIN` or stdlib fetch of `https://api.github.com/repos/esengine/DeepSeek-Reasonix/releases/tags/<tag>`. Pins `$REASONIX_TAG`, `$REASONIX_ASSET`, `$REASONIX_SHA256`, `$REASONIX_SIZE`, `$REASONIX_COMMIT`. Does not download or run the archive. Receipt: `pipelines/smoke/reasonix/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_164` (7 stub tests).
- **Non-goals**: No CLI unpack, no model key, no edits to any project, no Studio GUI, no TOOLS.md row. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Metadata match becomes exit 0 | Keep exit 2 while the reason says the archive was not run |
| Agent edits a real repo | A trial points at the operator's tree | Stay at I0; any trial uses an isolated worktree under `tmp/` |
| Paid DeepSeek keys | Default provider path wants a hosted key | Local-only trial only with the operator's GO |
| Pin drift | `studio-v2.57.0` is replaced | Smoke checks this tag's asset digest |

- **Status**: STAY I0 reference (nimo read 2026-11-07). Pin `737a181c49367a7a153c71889c168638fcfc0ba3` (`studio-v2.57.0`). MIT. Docs only, no install, no script run. Default provider is the DeepSeek API. Gap L stays with Ollama, llama-server, LiteLLM, and Strata. Report: `ops:eval/evq1107/reasonix/REPORT.md`. Not a Feature GO.
