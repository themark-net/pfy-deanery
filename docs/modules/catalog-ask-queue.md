# Module: Catalog ask / queue (`scripts/pfy_catalog_ask_queue_209.py`)

**Purpose:** Usable catalog browse from Tools, ask the attached TUI to implement a tool for the next launch, or queue a GitHub issue for Design→DevBot. Cite #209.

## Human operator

- What: Tools lists the Active Catalog table (name, category, github, stage, notes, status) and any stage card that is not already a row. Scores stay off the list. A card from `catalog_intake_dedupe.py --write-card` shows up here. Browse does not write TOOLS.md and does not change `integration_stage`. **Ask TUI implement** writes a paste/auto-handoff prompt. **Queue for org** is the live path in [live-org-queue.md](live-org-queue.md) (#214).
- How: [docs/ops/catalog-ask-queue.md](../ops/catalog-ask-queue.md)
- Failures: no attached harness -> FAIL + Attach grok|opencode|hermes|codex|claude. HOLD 70-75 or incomplete (including a new I0 card) -> SKIP (not auto-lifted). One integration at a time. One stage file that is not valid JSON hides every card stage.
- Recovery: Attach a TUI; pick a complete non-HOLD row; finish or cancel the pending item. Remove or fix the bad stage file and browse again. The Active Catalog names stay listed while it is broken.

## Agent

- Entry: `scripts/pfy_catalog_ask_queue_209.py` (`--selftest` / `--browse` / `--ask NAME` / `--queue NAME` / `--status`).
- Callers: `./pfy catalog …` payload; board `catalog_ask` / `catalog_queue`; `POST /catalog/ask` `/catalog/queue`; Tools HTML+tk.
- Invariants: no Env nav tab; no scores-only dump; HOLD 70-75 not auto-lifted; no operator git/npm/CI; do not reopen #76. Unmatched stage cards are read from `data/stages/<slug>.json` (name, `integration_stage`, github). Browse does not write that file. Documented Active Catalog rows keep their table name, category, and github.
- Issue **#209** only.

## Architecture link

Operator-stack layer (board/gui + `./pfy` catalog), not a catalog triple-write.
