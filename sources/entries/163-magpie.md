### Entry 163: magpie: one local gateway for every coding agent's model

- **URL**: https://github.com/yetone/magpie (MIT, Go). Source tag `v0.1.3081` at commit `4e7661adcee3ff019a729edcbae987b536ef4b53` (2026-11-06). Binary release repo https://github.com/yetone/magpie-releases tag `v0.1.3081`. Linux CLI asset `magpie-cli-linux-amd64`, size `71479458`, digest `sha256:6aaf6d22a43fcb01f3aee865ce721aa99fcc509ce9f4938bcff77fc134996adb`. Upstream pitch: pick any model for Claude Code, Codex, Gemini CLI, OpenCode, and peers from one local gateway; fail over when a quota runs out.
- **Date**: 2026-11-05 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2118266061862604931 (GitHub reply https://x.com/DanKornas/status/2118266240259310028)
- **Summary / Key Claims** (upstream README; their claims except where marked verified): a local model gateway and configuration app. It edits each agent's own config so one list of providers (API keys, local models, or signed-in Claude/ChatGPT/Copilot/Gemini/Grok plans) feeds every agent. Optional prompt masking keeps secrets on the machine. Runs as menu-bar app, TUI, web UI, CLI, Docker, or Termux. Install script: `curl -fsSL https://usemagpie.ai/install.sh | sh` (not run here).
- **Why it matters here**: pfy-mentat and the bot org already juggle Grok, Cursor, Hermes, and local Ollama endpoints. magpie is a routing layer candidate so harnesses share one provider list and fail over without rewriting each agent config. Catalog awareness; wiring it would touch agent configs and needs Mark's GO.
- **Fit on nimo**: Metadata check fits. Running the CLI or desktop installer is out of this smoke (downloads, may rewrite agent configs under the real home). Smoke exits 2 after a matching pin and does not run the binary.
- **Verified on the Grok Bot box** (2026-11-05): stub tests cover the metadata path. Live GitHub match expected to exit 2 with `FAIL_CANNOT_RUN_HERE`.
- **Findings**:
  - Pin is the CLI asset from `magpie-releases`, not the larger `magpie-linux-amd64` desktop binary.
  - Source of truth for the commit pin is the `yetone/magpie` tag `v0.1.3081`; release JSON `target_commitish` may be a branch name.
  - A matching release is still exit 2. Exit 0 would mean the binary ran. It did not.
- **Extracted Repos / Tools**: https://github.com/yetone/magpie · https://github.com/yetone/magpie-releases · https://usemagpie.ai
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row, no stage card.
- **Smoke**: `python3 examples/x-intake-local/smoke_163.py`. Uses `run_isolated`, `find_bin`, `pinned`, and `timeout_reason`, with `kill_on_exit=True`. Reads release JSON through `$MAGPIE_FETCH_BIN` or stdlib fetch of `https://api.github.com/repos/yetone/magpie-releases/releases/tags/<tag>`. Pins `$MAGPIE_TAG`, `$MAGPIE_ASSET`, `$MAGPIE_SHA256`, `$MAGPIE_SIZE`, `$MAGPIE_COMMIT`. Does not download or run the binary. Receipt: `pipelines/smoke/magpie/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_163` (7 stub tests).
- **Non-goals**: No install script, no agent-config rewrite, no provider sign-in, no paid key, no TOOLS.md row. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Metadata match becomes exit 0 | Keep exit 2 while the reason says the binary was not run |
| Installer rewrites agent configs | `install.sh` edits Claude/Codex/OpenCode homes | Do not run the installer from this smoke |
| Subscription sprawl | Providers want ChatGPT/Claude/Gemini logins | Stay at I0; local-only providers only if Mark GOs a trial |
| Pin drift | `v0.1.3081` is replaced | Smoke checks this tag's asset digest |

- **Status**: Cataloged I0. Metadata pin recorded. Binary not run (smoke designed for exit 2). Next step, if any: compare with HiRoute (147) and existing Ollama base URL wiring before any trial. No Feature GO.
