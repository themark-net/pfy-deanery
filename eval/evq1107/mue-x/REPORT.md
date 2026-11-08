# MUE-X evq1107

`STAY I1 reference: mutation-safety note recorded; evolve stays off`

## What it is

MUE-X (https://github.com/KorroAi/mue-x, MIT, copyright 2026 Korrocorp) is a Python 3.11 agent that rewrites its own `.py` files. Pin `c7038448abb340b23d03af0fd095cefbfbbcadd9` (2026-10-11 00:13:06 +0200). `LICENSE` begins "MIT License". 61 Python files sit under `mue/evo/`, 75 under `mue/`. Work tree without `.git` is 4715221 bytes. Core deps are the stdlib. FastAPI is optional. No Ollama string is in the tree. README backends are Claude Code, Gemini CLI, and Copilot CLI. This lane did not run upstream code.

`MUTATION_STRATEGIES` in `mue/evo/dna/mutator.py` is explore, exploit, repair, optimize, innovate, prune. Those strategies and `SelfModificationPipeline` write `genes/<name>.py`, not `mue/evo/`. `KERNEL_FILES` names mutator, genome, inspector, and solidify. `seal_kernel` hashes `genes/<name>.py` only when that file exists. This pin's `mue/genes/` has communication, persistence, planning, reasoning, and web_scout, so the seal records none of the four names. `mutate_gene` allows `force=True`. `PROTECTED_PATHS` is `evo/security/guard.py` and `evo/security/__init__.py`. The README says the seal covers the security guard. `mue/evo/llm_dna/mutator.py` still asks an LLM for new gene source, and the pipeline replaces that gene file after parse and import checks. `_backup_gene` keeps 5 copies and `_maintenance` keeps 3. TECHNICAL.md section 6 (repair 94% of 450, zero self-destruction in 500+ cycles) is only in that file. This lane did not reproduce it.

## Mutation-safety note

Self-mod of product code stays on the normal PR loop. A rewrite of the agent harness requires an ADR. Do not run `evolve`, `mine`, or the LLM rewrite path on this repo. The immune layer already in pfy is write-guard plus cage policy: the sealed-kernel idea, with the agent outside the kernel. Blast radius of a live process is its own source tree plus any repo `mine` clones. This pin is a read pin. The kernel seal covers no shipped file. Bounded pattern extract only. Never unattended self-modify.

## Ideas and the pfy file each would touch

1. Parse, backup, import-test, roll back. Already in `docs/ops/mue-x-patterns.md`. The check is `examples/eval-harness/tasks/010-mutation-safety-note/score.py`.
2. Hash-seal files an agent must not rewrite. Touch `docs/ops/exo-self-mod-patterns.md` and `harness/write-guard-mcp/`.
3. Treat drive and mood as a budget. Touch `bootstrap/grok-cli/skills/agent-loops/SKILL.md` (the eight-exit card).
4. Crystallize repeated notes. Touch `bootstrap/grok-cli/skills/hermes-feedback/SKILL.md`. Code structure stays on codebase-memory-mcp.
5. Leave GitHub absorption, the PAD daemon, the MCP plugin creator, and domain auto-switch unused.

## Catalog comparison

Same job: a self-rewriting agent, and gap H1 (a repeatable with/without score) in `docs/eval/TOOLSET-RANKING.md` (2026-11-07). The 2026-10-06 section holds MUE-X as an unsafe runtime. H1 is skill-up. Cards that matched memory: codebase-memory-mcp I2 (code graph), opencode-mem I2, MemPalace I1, OpenContext I1, LEANN I1, Memvid I1, imcodes I0, cass-memory I0, RoBrain I0, Graphify I0, Agent Beacon I0, Chroma (or LanceDB) I0. Axon I1, OpenLore I1, and repowise I2 name codebase-memory as overlap or a non-goal. Auto-Company I1 is a daemon pattern. Aider I1 edits the user repo through git. Grok CLI bootstrap I3 is the operator surface. Substring hits on ast (agentgg, anti-slop, ATG, JevAgentHarness) are not mutators. runx I0 seals a receipt.

| Card | Stage | How MUE-X compares |
| --- | --- | --- |
| skill-up | I3 | With-skill vs no-skill grade. Catch-up: 5/5 both arms, delta 0. MUE-X emitted no such score. |
| harness2 | I1 | The H1 trial. MUE-X does not re-measure it. |
| Exo (exoharness) | I1 | Paired self-mod note. ADR plus PR. No kernel rewrite. |
| Hermes Agent (feedback loops) | I1 | Feedback skill already in tree. |
| write-guard-mcp | I3 | Write mediation above the cage. The MUE-X guard is an in-process denylist. |
| destructive_command_guard | I2 | Denies destructive shell commands. Probe denied 12/12. |
| agent-cage (PNNL) | I3 | Outer sandbox named in the pattern doc. |

## Gates

Value (3 of 4 for I3): gap fill no, operator leverage no, evidence no (read only), blast radius no (live evolve rewrites source and `mine` clones foreign repos). Score 0 of 4.

Modularity: reading `KERNEL_FILES` changed this note, so the README was not enough. The CLI entry is bounded. The cache clone is isolatable and reversible. Size is 4715221 bytes, under 50 MB. Potential is low, so I2 does not apply. No in-repo copy. No `self_pipeline`. No gate wiring.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Unattended evolve | A process rewrites `mue/evo/`. The guard is outside `KERNEL_FILES`. | Do not run it. Delete the cache clone. The pin stays. |
| `mine` | Clones foreign repos beside the agent. | Do not run it. This lane made no install. |
| README treated as a smoke | The 94% table becomes evidence. | Keep it an upstream claim. A later smoke needs an operator GO and must not rewrite this repo. |
| Handoff drift | `data/catalog_stage_handoff.json` still says the note is missing. | This lane edits only the card. If `--apply` restores the old `next_gate`, put this note back on the card. |

## Next gate

Stay I1. This file is the mutation-safety note. Do not run evolve. Not a Feature GO.

## Commands

```bash
CACHE=~/.cache/pfy/tools/mue-x
mkdir -p "$CACHE"/{home,xdg/config,xdg/cache,tmp}
export HOME="$CACHE/home" XDG_CONFIG_HOME="$CACHE/xdg/config" XDG_CACHE_HOME="$CACHE/xdg/cache" TMPDIR="$CACHE/tmp"
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
git clone --filter=blob:none --no-checkout https://github.com/KorroAi/mue-x.git "$CACHE/src"
git -C "$CACHE/src" fetch --depth 1 origin HEAD
git -C "$CACHE/src" checkout --detach FETCH_HEAD
```

Resolved HEAD is the pin above. No upstream script ran. No timing. The model lock was not taken.

## Pipeline questions

1. What triggers it? A person runs `python -m mue evolve`, or the loop's own drives. Not the pfy scheduler.
2. What does it do, and which services does it read and write? It reads its own Python tree and writes genes, backups, a SQLite lattice, and an audit log. `mine` reads the GitHub API and writes cloned patterns. This lane set no API key.
3. What does it trigger next? Another evolve cycle, or a human reading `status`. A human still owns any pfy commit.
4. Where does a human re-enter? Any request to run evolve or mine, a kernel-hash mismatch, or `tmp/STOP`.
5. What stops two runs doing the same work? One worktree per slug. Two evolve loops on one gene tree can clobber backups. Stop both and restore a timestamped backup. This lane created none.
