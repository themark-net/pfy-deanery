# X intake 2026-11-06: handoff (Entries 165-167)

Window: `2026-11-06T01:44:30Z` .. ~`2026-11-07T01:40Z` (PT calendar day 2026-11-06). Highest existing entry on `origin/main` before this slice was **164** (`164-reasonix.md`); next numbers are **165-167**. Catalog HOLD 70-75 was not touched. No Feature GO.

PR #311 (entries 162-164) confirmed merged to main at `b38db376` (2026-11-06T20:10:49Z) before this run.

nimo had long-running `grok` PIDs (~19h) and active lane worktrees (`br1106`, `headless-1105`, etc.), so keepers were filed from the Grok Bot box via GitHub push (no nimo worktree, Mark's main checkout untouched).

## New entries

All three are I0. No TOOLS.md row, no `data/tools.json` row, no stage card. Smokes are commit-metadata checks that exit 2 on a matching pin (repo not cloned, plugins/skills not installed).

| Entry | Tool | Why | Fits nimo? |
|------|------|-----|------------|
| 165 | [EGM](https://github.com/google/elephant-goldfish-model) (Apache-2.0, plugin `0.1.1`) | Spec-driven design + fresh-eyes review skills for Claude/Codex/Antigravity. Cheap gate before Build burns. | Commit pin only. Install would write agent plugin homes. |
| 166 | [odai](https://github.com/orziz/odai) (MIT, skill `0.7.1`) | Evidence-driven task governance so agents cannot claim "done" without verification. Kin to Entry 154 authorization doctrine. | Commit pin only. No DSH/skill install. |
| 167 | [TeaQL Agent Kit](https://github.com/teaql/teaql-agent-kit) (MIT) | Model-first build workflow + Agent Context Kit for file/context governance and verification evidence. | Commit pin only. Large monorepo; no install. |

Source posts: [EGM](https://x.com/DanKornas/status/2118673751613071452), [odai](https://x.com/DanKornas/status/2118764357551112380), [TeaQL](https://x.com/DanKornas/status/2118651100601438417).

Pins:

- EGM commit `7bd119c1031c58e6a6f4e2031b397a2635872124`
- odai commit `ce7a999843ca42ecd84778561cb0ac7642c5648e` (skillVersion `0.7.1`)
- TeaQL Agent Kit commit `92c79101f725655d5356078938742bd633f341a2`

Files: `sources/entries/165-egm.md`, `166-odai.md`, `167-teaql-agent-kit.md`, `examples/x-intake-local/smoke_165.py`, `smoke_166.py`, `smoke_167.py`, `tests/test_x_intake_smoke_165.py`, `166`, `167` (7 stub tests each), `.gitignore` receipt dirs, README note for 165-167.

## Left open / not keepers this run

- Bookmarks: cartalax/BPC-157 health (SKIP); `/untangle-codebase` by @mazeincoding — no public repo/skill URL found (SKIP incomplete); older Jev/openjev bookmarks already covered by Entry 131 (SKIP).
- Watch SKIP/LATER: pb-mapper, Moli OS, Hindsight, wanderlog-mcp, Awesome AI Agents (list), Kami, Dev Quality Gates (list), Taiwan Health MCP (health), Proximo (Proxmox niche), ChengOS, Lucy (Minecraft), blenderwright, fastbrowse (wants OpenRouter + Browser Use keys; Charlotte 142 already covers browser agents), MoE routing explainer, Qwen4 chatter, history learning, Anthropic 9-step paper thread (technique note only).
- Weekly @tom_doerr Grok automation: no tom_doerr posts in window.
- Live smokes against GitHub and nimo pregate/CI: left for green CI on this PR / owner merge per catalog-only self-review rule.

## Eval-auto note

**EGM** is the strongest design-review candidate this window: could sit in front of Build lanes as a fresh-eyes spec gate (would complement, not replace, harness2/eval-harness). **odai** is the strongest governance-skill candidate vs informal bot authorization (compare with Entry 154 before any trial). Neither is wired.
