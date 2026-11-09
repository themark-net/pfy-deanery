# Catalog pick → implement-on-next-launch or queue org

Cite **#209**. Browse a usable catalog subset from **Tools**. Ask the attached TUI to implement one tool onto itself for the next launch, or queue the work as a GitHub issue with Design→DevBot DoD. Honest SKIP/FAIL. One integration at a time.

## Operator

On **Tools** (HTML+tk) or CLI:

```bash
./pfy catalog                 # usable browse (name/stage/status/notes, not scores)
./pfy catalog ask <name>      # prompt/artifact for attached TUI, operate-or-FAIL
./pfy catalog queue <name>    # GitHub issue Design->DevBot (no operator git/npm/CI)
./pfy catalog status          # queued items
```

`./pfy catalog` keeps the Active Catalog table for documented tools. A stage card with no row in that table is listed after those rows. `catalog_intake_dedupe.py --write-card` does not write TOOLS.md, and browse does not change `integration_stage`. An I0 card is visible and Ask still SKIPs it.

Tools: pick a row, **Ask TUI implement** (copy or auto-handoff `PFY_CATALOG_ASK_PROMPT` on next Attach), **Queue for org**. No Env nav tab.

### Gates

| Condition | Result | Next |
|-----------|--------|------|
| No grok/opencode/hermes/codex/claude attached | **FAIL ask** | Attach grok \| opencode \| hermes \| codex \| claude |
| Entry X 070–075 / catalog PRs 70–75 | **SKIP** | catalog 70-75 HOLD (do not auto-lift) |
| Incomplete (I0, skip install, no smoke, scores-only) | **SKIP** | pick a complete catalog entry |
| Another item already asked/open | **FAIL** | finish or cancel the pending integration first |
| `gh` and `GITHUB_TOKEN` both missing | **FAIL queue** | `gh issue create --repo themark-net/pfy-mentat` (draft in `$PFY_STATE_DIR/catalog-issue-draft.md`) |

Live Queue (real issue + open/closed/PR refresh) is [#214](live-org-queue.md). This file keeps browse/ask. `LIVE_HARD_OFF` still holds for TOOLS.md / tools.json.

## How to run

```bash
python3 scripts/pfy_catalog_ask_queue_209.py --selftest
./pfy catalog
./pfy catalog ask repowise
./pfy catalog queue repowise
python3 scripts/pfy-board.py --catalog
python3 scripts/pfy-board.py --ask repowise
```

## Variables

| Name | Where | Purpose |
|------|-------|---------|
| `PFY_STATE_DIR` | `catalog-queue.json`, `catalog-ask-prompt.md`, `catalog-ask-handoff.md` | queue + next-launch prompt |
| `PFY_CATALOG_ASK_PROMPT` | Attach child env | auto-handoff path for next launch |
| `PFY_CATALOG_ASK_HANDOFF` | Attach child env | handoff notes |
| `GITHUB_TOKEN` / `GH_TOKEN` | env (existing) | Queue-for-org API if `gh` missing |

Registry: [bootstrap/env/REGISTRY.md](../../bootstrap/env/REGISTRY.md).

## Do not

- Reopen #76 · unpark #198 · catalog 70–75 HOLD (do not auto-lift)
- Add an Env nav tab
- Dump S1–S4 scores as the Tools browse
- Auto-implement HOLD/incomplete entries
- `LIVE_HARD_OFF`: no live catalog writes / no TOOLS.md triple-write from this path
