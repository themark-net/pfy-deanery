# Module: Live org queue (`scripts/pfy_live_org_queue_214.py`)

**Purpose:** Queue for org creates a **real** GitHub issue on `themark-net/pfy-deanery` with Design→DevBot DoD and paints open/closed/PR. Cite #214.

## Human operator

- What: Tools **Queue for org** opens a live issue (gh or `GITHUB_TOKEN`). Tools/Loop list queued items with **open / closed / PR**. Missing auth is FAIL + draft, not a mock PASS.
- How: [docs/ops/live-org-queue.md](../ops/live-org-queue.md)
- Failures: no `gh` auth and no token → FAIL + `gh auth login`. HOLD 70–75 or incomplete → SKIP (not auto-lifted).
- Recovery: authenticate; pick a complete non-HOLD row; finish or cancel the pending item.

### Configuration / variables

| Name | Where | Purpose |
|------|-------|---------|
| `PFY_STATE_DIR` | `catalog-queue.json`, `catalog-issue-draft.md` | queue + FAIL draft |
| `GITHUB_TOKEN` / `GH_TOKEN` | env | API create/refresh if `gh` missing |

Registry: [bootstrap/env/REGISTRY.md](../../bootstrap/env/REGISTRY.md).

## Agent

- Entry: `scripts/pfy_live_org_queue_214.py` (`--selftest` / `--queue NAME` / `--status` / `--dry-run`).
- Callers: `./pfy catalog queue|status` (via `pfy_catalog_ask_queue_209.py` delegate); board `catalog_queue` / `catalog_status` / `catalog_fields`; `POST /catalog/queue`; Tools HTML+tk.
- Invariants: no mock success; HOLD 70–75 not auto-lifted; no operator git/npm/CI; do not reopen #76; selftest never creates live issues.
- Issue **#214** only.

## Architecture link

Operator-stack layer (board/gui + `./pfy` catalog), not a catalog triple-write. Extends #209 browse/gates.
