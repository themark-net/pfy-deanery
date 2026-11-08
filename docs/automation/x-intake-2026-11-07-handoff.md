# X intake 2026-11-07: handoff (Entries 168-170)

Window: `2026-11-07T01:40Z` .. `2026-11-08T01:40Z` (PT calendar day 2026-11-07). Highest entry on `main` (`7ec63ee`) before this slice was **167**. PR #312 (165-167) confirmed merged at `7ec63eed` (2026-11-07T02:57Z). Catalog HOLD 70-75 not touched. No Feature GO.

Filed from the Grok Bot box via GitHub (no nimo worktree; Mark's main checkout untouched). Catalog-only, so under the 2026-11-07 standing rule it lands on Build-style self-review plus a quick check (21/21 stub tests pass; live smokes exit 2 on matching pins).

## New entries (all I0; no TOOLS.md or data/tools.json rows)

| Entry | Tool | Why | Fits nimo? |
|------|------|-----|------------|
| 168 | [cedr](https://github.com/Sheernox/cedr) (Apache-2.0, v0.10.0) | Plan-aware agent/model routing, multi-vendor review council, skill/MCP pin lock with CI drift fail, rules written once and synced to each agent's files, baseline-vs-candidate bench. | Rust binary, no GPU. Grok Build/Cursor harness support unverified; pin version and disable self-update. |
| 169 | [IM.codes](https://github.com/im4codes/imcodes) (MIT) | Fail-closed supervised execution with scored audit/rework gates; memory built only from final answers. | Design reference. Don't enable Controlled Nodes. |
| 170 | [Pi-Harness](https://github.com/wangmiaozero/pi-harness) (AGPL-3.0, v2.3.20) | Runs/trace/replay/compare/evaluation and checkpoints around Pi, which can drive local models. | Desktop app; nimo headless. Reference only (AGPL). |

Pins: cedr `9cf2683e54a60e2f36f6f11fe715a7906e711597`, IM.codes `b8442c5ca3bd22046568258e84d30781dc6a79d0`, Pi-Harness `5b6ec2318d6741e444bfe8a640432be052e509fc`.

Files: `sources/entries/168-cedr.md`, `169-imcodes.md`, `170-pi-harness.md`; `examples/x-intake-local/smoke_168.py`..`170`; `tests/test_x_intake_smoke_168.py`..`170` (7 stub tests each); `.gitignore` receipt dirs; README note.

## Not keepers this run

- Bookmarks: none new in the latest 100.
- SKIP: imp (NVIDIA RTX 50-series only), Ririko Discord bot, CaseCite (legal RAG), paseo-agy-acp (second paid Antigravity account), Capri AI (Windows only), Awesome-AGI-Agents (list), Design Studio (prototype sandbox), Strata (already Entry 162), alex_verem/_avichawla/mattpocockuk threads (no tool).
- LATER: Tucano (agent channels; built on Claude Code), Facade Code (VS Code multi-agent orchestrator for Claude/Codex), Revia (agent-authored graph language), Nodecode (self-modifying Lisp agent), Braxis Blueprint (free-tier LLM lane lessons; needs signups), self-host by ajnart (homelab app installer, not pfy scope).
- No @tom_doerr posts in the window (weekly Grok automation covers him).

## Eval-auto note

**cedr Guard + Sync** is the strongest trial candidate: it could replace our hand-maintained skill/MCP pinning and the manual port of bot doctrine into each agent's files with one `.cedr/` source and a CI drift check. Trial in a throwaway worktree first, release pinned, self-update off, never `--force`.
