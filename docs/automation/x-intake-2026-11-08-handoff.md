# X intake 2026-11-08: handoff (Entries 171-173)

Window: `2026-11-08T01:40Z` .. `2026-11-09T01:41Z` (PT calendar day 2026-11-08). Highest entry on `main` (`9cd54cb`) before this slice was **170**. PR #313 (168-170) confirmed merged at `db42453` (2026-11-08T01:45Z). Catalog HOLD 70-75 not touched. No Feature GO.

Filed from the Grok Bot box via GitHub (no nimo worktree; Mark's main checkout untouched). Catalog-only, so under the 2026-11-07 standing rule it lands on Build-style self-review plus a quick check (21/21 stub tests pass; live smokes exit 2 on matching pins).

## New entries (all I0; no TOOLS.md or data/tools.json rows)

| Entry | Tool | Why | Fits nimo? |
|------|------|-----|------------|
| 171 | [LocalHarness](https://github.com/ahwurm/localharness) (MIT, v0.27.7) | Agent harness built for local LLMs: llama.cpp launch sizing from GGUF, one permission gate on every tool call, YAML agents, Agent Skills, SQLite memory, local experiment loop. | Python/uv, no keys. AMD/Strix Halo unverified; install only under DEVELOP; no model fetches. |
| 172 | [Cartographer](https://github.com/BeppeTemp/cartographer) (Apache-2.0) | Git-backed wiki served over MCP that every agent client reads and grows; health checks; ships skills to clients. | Go binary, local bare repo. Run `setup` with a throwaway HOME only. |
| 173 | [agent-manager](https://github.com/wainmann/agent-manager) (Apache-2.0) | tmux manager for many agent CLIs with live status (Grok Build supported), forks, saved prompts, diff review, spawn/send CLI. | Go + tmux, no GPU, no keys. Headless spawn/send unverified. |

Pins: LocalHarness `5af7511ce8f8f799f74de877698e4c4aec0dec45`, Cartographer `f96e5d9f7b0ae8506ce5470e35372546a70ea292`, agent-manager `cbe5fb9bd248636ebeb5ac6f97ab83940d04fb2d`.

Files: `sources/entries/171-localharness.md`, `172-cartographer.md`, `173-agent-manager.md`; `examples/x-intake-local/smoke_171.py`..`173`; `tests/test_x_intake_smoke_171.py`..`173` (7 stub tests each); `.gitignore` receipt dirs; README note.

## Not keepers this run

- Bookmarks: none new in the latest 100.
- LATER: Agent Canary 3.0 (MCP/SDK guarded tool gateway; compare with destructive-command-guard), Varin (AGPL agent harness with lead/helper agents), agent-desktop by vercel-labs (desktop control via accessibility tree; not pfy scope yet), strands-env (agentic RL environments), Shipfox (agents-as-CI platform), deja-vu (session-history memory; repo link not resolved), Agent Skill Index (directory).
- SKIP: Observer AI (screen/camera monitoring), WilmAI (Finnish school system), Omni (chat-app messaging), OpenDesigner (design system add-on), My Office (3D session view), EmbeddingGemma 2 video chat thread, ch3nweiii Karpathy-loop thread (no repo), alex_verem/FurqanR/aisearchio/yume_arasaki posts (no tool).
- No @tom_doerr posts in the window (weekly Grok automation covers him).

## Eval-auto note

**LocalHarness** is the strongest trial candidate: it targets the same local-model harness job as our current Grok Build + Ollama/llama.cpp lanes, with launch sizing, a fail-closed tool gate and skills support built in. Trial: one catalog-lane task, same model, compare tool-call success and wall time. Any GPU run needs Mark's go.
