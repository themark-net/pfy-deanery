# imcodes evq1107

`STAY I0 reference: Node daemon with Controlled Nodes; the idle verdict and final-answer memory already sit in pfy docs`

## What it is

IM.codes (npm `imcodes` 0.1.2, MIT, copyright 2026 IM.codes) is a messaging, memory, and review layer around terminal coding agents, plus remote-desktop Controlled Nodes. The README calls it a personal project with no stability or security guarantee. Requirements there are Node >= 22, tmux, and Claude Code, Codex, Gemini CLI, OpenClaw, or Qwen. The architecture is browser, server, daemon. Grok Build is not in that requirements list or the architecture diagram. The tree has `src/agent/providers/grok-sdk.ts` plus `test:grok-acp-smoke` and `test:grok-auth-smoke`. This lane did not open or run them.

## Ideas and the pfy file each would touch

1. Keep only final `assistant.text`, and drop tool noise. Touch `bootstrap/grok-cli/skills/hermes-feedback` (the 2026-10-06 ranking already sends session-memory notes there) and the attempt receipt in `docs/ops/HANDOFF-pfy-local-build-mvp.md`.
2. At idle, classify `complete`, `continue`, or `ask_human`, and fail closed on timeout or bad output. Touch `bootstrap/grok-cli/skills/agent-loops` and that receipt (`PASS|FAIL|BLOCKED|TIMEOUT|ABORTED`).
3. Score `PASS`, `REWORK`, or `BLOCKED`, and never stage, commit, or push. Touch the review step in `docs/ops/HANDOFF-pfy-local-build-mvp.md`. A model accept there is already same-model self-review, and BLOCKED writes no branch.
4. Do not borrow Controlled Nodes, cloud sync, the web app, or the daemon.

## Catalog comparison

Same job: supervised audit/rework and lane memory. Gap B in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is the `./pfy build` 3 hour timeout. Entries 137 to 167 do not close it. This entry does not either.

| Tool | Stage | How imcodes compares |
| --- | --- | --- |
| Finn Loop / 8-exits | I1 | The exit card already decides stop, continue, and human. imcodes is a live daemon around other CLIs. |
| Hermes feedback loops | I1 | The memory pattern is already a skill. The final-answer rule is a note on that skill, not a second store. |
| opencode-mem | I1 | Worker memory for OpenCode. Different surface. |
| MemPalace, RoBrain | I0 | Post-MVP memory. RoBrain's veto is the ask_human shape, and it wants Postgres. |
| Elephant-Goldfish, mattpocock/skills, Chiasmus | I1 | Spec review, review skills, and diff impact. Already the review path. None supervises a live session. |
| neatroots | I2 | Offline loop and repeat rules on traces. A daemon is not required to keep that check. |
| odai | I0 | Evidence-before-done skill. Same fail-closed handoff idea, still a read. |
| codebase-memory-mcp | I2 | Code graph, not session memory. |
| Rulora, HAR, Festival | I1, I0, I1 on origin/main during this lane | Loop counters (2 of 8 exits), worktree receipts, and checklists. None closed gap B. |

## Pins and commands

Pin `b8442c5ca3bd22046568258e84d30781dc6a79d0` at 2026-10-31 22:33:07 -0700 (2026-11-01 UTC). Package imcodes 0.1.2, MIT, Node >= 22. 4480 tracked files, 74973982 bytes without `.git` (over the 50 MB I2 copy limit). Cache `~/.cache/pfy/tools/imcodes/src`, not committed. No upstream script ran, so there is no probe timing. No npm, no daemon, no bind, no model.

```bash
CACHE=~/.cache/pfy/tools/imcodes
mkdir -p "$CACHE"/{home,xdg/config,xdg/cache,tmp}
export HOME="$CACHE/home" XDG_CONFIG_HOME="$CACHE/xdg/config" XDG_CACHE_HOME="$CACHE/xdg/cache" TMPDIR="$CACHE/tmp"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
git clone --filter=blob:none --no-checkout https://github.com/im4codes/imcodes.git "$CACHE/src"
git -C "$CACHE/src" fetch --depth 1 origin b8442c5ca3bd22046568258e84d30781dc6a79d0
git -C "$CACHE/src" checkout --detach FETCH_HEAD
```

## Gates

Value (3 of 4 for I3): gap fill no, operator leverage no, runnable evidence no (docs read only), blast radius not ok (remote command nodes and optional cloud memory). Score 0 of 4.

Modularity (all 4 for a local copy): the README was enough to judge, the tree is not one bounded package, the cache clone is isolatable, and deleting it leaves the pin. Not all 4. Size is over 50 MB, so I2 is closed. Potential is low, not ambiguous.

`uses` contains the word review, so an I3 card would need `self_pipeline`. This lane does not set that field and wires no gate. No TOOLS.md row and no `data/tools.json` row.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Node enrollment | A Controlled Node runs commands on nimo | Do not enroll. This lane did not. |
| Cloud memory | Processed summaries leave the machine | Do not enable sync. |
| README treated as a smoke | Claims become an install | Stay I0. The entry already records that metadata smoke as exit 2. This lane did not re-run it. |
| Pin drift | Default branch moves | The card pins `b8442c5ca3bd22046568258e84d30781dc6a79d0`. |

## Next gate

Stay I0. Re-open only to copy the final-answer rule or the idle verdict into the local-build receipt, still with no daemon. Not a Feature GO.

## Pipeline questions

How imcodes would run if a later ticket adopted it. This lane did not add that path.

1. What triggers it? A person starts the daemon and enables supervised or supervised_audit on a session. Not a pfy scheduler.
2. What does it do, and which services does it read and write? It reads agent turns and writes local memory, optional cloud summaries, and commands on enrolled nodes. It does not commit or push.
3. What does it trigger next? A continue prompt, an audit/rework loop, or ask_human. A human still owns the commit.
4. Where does a human re-enter? Timeout, invalid output, BLOCKED, or any node enrollment.
5. What stops two runs doing the same work? Upstream locks a Team lane per OpenSpec change. Here, one worktree per slug and the driver lock already do that. Do not add a second lock from this tool.
