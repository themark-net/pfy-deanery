### Entry 157: Emdash: parallel coding agents, one worktree per task

- **URL**: https://github.com/generalaction/emdash (Apache-2.0, Copyright 2026 General Action, Inc., TypeScript, Electron). Release tag `v1.2.10`, `target_commitish` `ab766e8fbb436584dcf0f299740e79d559b8ed31`. Linux asset `emdash-x86_64.AppImage`, size `233276140`, digest `sha256:274586c70ba70466667fa811c5ead49610493859bed8c51e4f9abc0850c26d7d`. GitHub API description: an open-source agentic development environment that runs multiple coding agents in parallel and can use any provider.
- **Date**: 2026-11-02 (X intake)
- **Source / Poster**: https://x.com/DanKornas/status/2117382748692197498
- **Summary / Key Claims** (upstream repo description and the pinned release; their claims except where marked verified): a desktop app for running several coding agents at once, one git worktree per task, with a choice of model provider. It is an Electron GUI. The pinned Linux build is an AppImage of about 233 MB.
- **Why it matters here**: pfy-mentat already runs parallel agent work in separate git worktrees (this slice is one). Emdash is a primary-dev-environment reference for that shape: many agents, one worktree each, provider chosen per run. Comparison only. It does not replace the catalog harness, the worktree checkout, or `./pfy`.
- **Fit on nimo**: AMD Strix Halo, Radeon 8060S, no NVIDIA. Launching the AppImage is a GUI desktop session and a 233 MB download. This smoke does not do either. The metadata check is CPU and network only, and it fits.
- **Verified on nimo** (2026-11-02, this worktree, no sudo): `python3 examples/x-intake-local/smoke_157.py` exited 2. Receipt verdict `FAIL_CANNOT_RUN_HERE`. The GitHub release JSON matched the pin (name, size, digest, and commit). Reason: `Linux release asset emdash-x86_64.AppImage matches pin v1.2.10 (sha256 274586c70ba70466667fa811c5ead49610493859bed8c51e4f9abc0850c26d7d, 233276140 bytes) at commit ab766e8fbb436584dcf0f299740e79d559b8ed31; Emdash is an Electron GUI desktop app and was not launched`. The AppImage was not downloaded. No local `emdash` binary was launched. Real-HOME paths `.config/emdash`, `.local/share/emdash`, and `.emdash` were unchanged.
- **Findings**:
  - A matching release is still exit 2. Exit 0 would mean the GUI ran. It did not.
  - A digest, size, name, or tag mismatch, or a 40-hex commit that is not the pin, is exit 1. A fetch failure or a timeout is exit 2.
  - "Any provider" means a real trial wants accounts and keys. That is out of scope here.
- **Extracted Repos / Tools**: https://github.com/generalaction/emdash · release tag `v1.2.10`
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row, no stage card.
- **Smoke**: `python3 examples/x-intake-local/smoke_157.py`. Uses `run_isolated`, `find_bin`, `pinned`, and `timeout_reason`, with `kill_on_exit=True`. Reads the release JSON through `$EMDASH_FETCH_BIN` or a stdlib fetch of `https://api.github.com/repos/generalaction/emdash/releases/tags/<tag>`. Pins `$EMDASH_TAG`, `$EMDASH_ASSET`, `$EMDASH_SHA256`, `$EMDASH_SIZE`, and `$EMDASH_COMMIT`. Records `$EMDASH_BIN` if one is staged and does not launch it. Does not download the AppImage. Receipt: `pipelines/smoke/emdash/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_157` (7 stub tests: missing fetcher, hang killed, no surviving grandchild, matching metadata does not launch the GUI, wrong size fails, bad timeout, gitignored receipt).
- **Non-goals**: No AppImage download, no GUI launch, no provider account, no key, no TOOLS.md row. Catalog HOLD 70-75 untouched.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | A later edit turns a metadata match into exit 0 | Keep exit 2 while the reason says the GUI was not launched. The stub test checks that sentence |
| Accidental 233 MB download | A script fetches the AppImage "to be sure" | The smoke reads the release JSON only. Do not add a download |
| Provider keys in a trial | "Any provider" pulls a hosted account into this repo | Stay at I0. A trial needs its own checkout and Mark's GO |
| Pin drift | A newer tag replaces `v1.2.10` on `main` | The smoke checks this tag's asset digest, not floating `main` |

- **Status**: Cataloged I0. Metadata matched on nimo. The GUI was not launched (exit 2). Next step, if any: none until someone wants a desktop trial outside this repo. No Feature GO.
