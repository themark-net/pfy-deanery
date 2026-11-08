# OpenClaude-Portable evq1107

STAY I0 reference: USB wrapper that downloads official Claude Code plus Node 24.21.0. Gap B stays the pfy build timeout. No pfy file should change.

## What it is

techjarves/OpenClaude-Portable (package `claudecode-portable` 2.0.0) is a folder launcher for the official Claude Code CLI and Agent SDK. `start.sh` downloads Node.js 24.21.0 from nodejs.org when `engine/` lacks that version, then runs `tools/launcher.mjs`. The runtime manifest pins `@anthropic-ai/claude-code` 2.1.247, `@anthropic-ai/claude-agent-sdk` 0.3.247, and `claude-adapter` 2.2.1. Nine profiles: Anthropic, OpenRouter, DeepSeek, NVIDIA NIM, Gemini, OpenAI, Ollama (`http://127.0.0.1:11434`), LM Studio (`http://127.0.0.1:1234`), and a custom OpenAI base (default `http://127.0.0.1:8080/v1`). A browser dashboard and the terminal share Claude session ids. App files stay under `data/` (`PORTABLE_AI_DATA_DIR` or `<root>/data`). API keys sit in plaintext `data/settings.json` (mode 0600). Dashboard and adapters bind `127.0.0.1` with a fresh token. LICENSE is MIT (Copyright 2026 Tech Jarves). Claude Code and the SDK keep their own terms. The README says this is an independent interface.

## Pin and command

| Item | Value |
| --- | --- |
| Pin | `b3660fda34333d759b7e76ccb62b0a2aa076bb66` |
| Commit | 2026-09-12 19:13:55 +0530. Resume interrupted Windows runtime installs. `dev` is `cac7fa07a37bc97bc7c205c80248ae4303443a70`. This lane pinned `main`. |
| Fetch | 0.73 s. `git fetch --depth 1 --filter=blob:none origin b3660fda34333d759b7e76ccb62b0a2aa076bb66`, then checkout. No upstream script. |
| Size | worktree 1455638 bytes, `.git` 1202027, cache 2657665. 54 files, 27 `.mjs`. Host Node v22.23.0. Their pin is Node 24.21.0. `engine/` stayed absent. |
| Cache | `~/.cache/pfy/tools/openclaude-portable/src`. Not committed. |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` sat under `~/.cache/pfy/tools/openclaude-portable`. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`.

No `sources/entries` file (the ticket entry was `-`). Status is this card. `sources/x-posts.md` Entry 054 is the shared log and was left as it was.

## Ideas, and the pfy file each would touch

1. Folder-local `CLAUDE_CONFIG_DIR` under `data/claude/<provider>-<auth>`, telemetry off. Already `data/harnesses.json` (`claude-code` `config_dir`, default `~/.claude`) and ADR-0012. Leave that slot on the official installer.
2. One launcher and a local-model profile. Already `./pfy` (ADR-0012) and OpenCode plus Ollama (ADR-0011, `bootstrap/opencode/`).
3. Localhost bind and a launch token. Already agent-cage and write-guard-mcp. The plaintext settings file is not a pattern to copy.
4. Checksum-pinned Node and npm packages inside the folder. Already ADR-0003 (pin, do not embed). Upstream gitignores `engine/`. Leave it in the cache.

## Catalog comparison

Gap B in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is the `./pfy build` timeout. This folder never runs that command. Same job: a portable coding client. Searched `#coding-agent` plus portable or folder wording.

| Tool | Stage | How this compares |
| --- | --- | --- |
| Grok CLI bootstrap | I3 | Operator path. ADR-0002. |
| claude-code slot | partial, `data/harnesses.json` | Official `claude.ai/install.sh`. Linked card is claude-code-unified-agents I1, a skill pack. |
| claude-codex-settings | I1 | Hooks for other CLIs. No Node bundle. |
| Continue.dev | I1 | IDE client of a local base. |
| Aider | I1 | Terminal editor. Overlaps `./pfy build --local`. |
| AgenC | I0 | ADR-0010 keeps it off the operator seat. |
| Emdash | I0 | Desktop that launches CLIs. |
| Pi-Harness | I0 | Desktop control plane. |
| Ollama | I2 | Engine the Ollama profile would call. |
| llama.cpp server mode | I1 | Already in the pfy up order. |
| LiteLLM | I2 | The proxy. This repo is a client. |
| Open WebUI | I1 | Chat UI. The product window is pfy's. |

`#coding-agent` also sits on karpathy-guidelines I1, ponytail I1, destructive-command-guard I2, opencode-mem I2, and repowise I2 (a skill, a guard, memory, context packing). Overtime I0 and Kanzo I0 are folder tools for a different job.

## Gates

Value (3 of 4 for I3): gap fill no, operator leverage no (first launch downloads Node 24 and Claude packages; host Node is v22.23.0), evidence no (`start.sh` was not run), blast radius no (MIT wrapper, plaintext API keys, second runtime). Score 0 of 4.

Modularity (all 4): README, `start.sh`, `lib/paths.mjs`, `lib/providers.mjs`, and `tools/runtime-manifest.json` were enough, so local code was not required. The launcher plus dashboard is bounded. The cache copy is isolatable and reversible. 3 of 4. 1455638 bytes is under 50 MB. Potential is low, so I2 stays closed. No `self_pipeline`. Uses and features name no CI, test, or review role. No gate wiring. No new TOOLS.md or `data/tools.json` row.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| First launch | `start.sh` writes `engine/` and fetches nodejs.org | This lane did not run it. |
| Plaintext keys | `data/settings.json` lands in git | Cache only. Never commit that file. |
| Second Claude home | A launch writes real `~/.claude` | Their code sets `CLAUDE_CONFIG_DIR` under `data/claude/`. Still do not launch. |
| Gap B false pass | A USB folder is counted as a build-lane fix | B stays the pfy build timeout. |
| Pin drift | `dev` moves while the pin is `main` | Pin the SHA. |

## Next gate

Stay I0 reference. Re-open only if a later ticket asks to replace the official installer in `data/harnesses.json`. This read does not. Not a Feature GO.

## Pipeline questions

This lane writes the card and this directory. It does not put the tool on a pipeline.

1. Trigger, if adopted later: a person runs `start.sh`. The evq scheduler is only the trigger for this read.
2. It would download Node and Claude Code into `engine/`, read `data/settings.json`, and send prompts to the selected provider. This lane called no model and used no account.
3. Next would be the dashboard or the Claude terminal. pfy does not start from this folder.
4. A human re-enters before any run of `start.sh`, any copy of `engine/`, or any change to the Claude harness slot.
5. One worktree per slug keeps this card private. Two launches on one folder would share `data/` and `engine/`.
