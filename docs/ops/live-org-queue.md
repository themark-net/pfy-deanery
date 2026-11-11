# Live org queue from Tools — real GitHub issues + status

Cite **#214**. Deepens Tools **Queue for org**: create a real GitHub issue on `themark-net/pfy-deanery` with Design→DevBot DoD, then paint **open / closed / PR**. Honest SKIP/FAIL. No mock success.

Catalog browse + Ask TUI remain [#209](catalog-ask-queue.md). This slice is the live queue path nimo smoke found missing.

## Operator

On **Tools** (HTML+tk) or CLI:

```bash
./pfy catalog queue <name>    # REAL gh/api issue — operate-or-FAIL
./pfy catalog status          # refresh open/closed/PR
python3 scripts/pfy_live_org_queue_214.py --selftest
python3 scripts/pfy_live_org_queue_214.py --dry-run   # GET repo only; never creates
```

Queue prefers `gh issue create` (when `gh auth status` is 0), then `GITHUB_TOKEN`/`GH_TOKEN` POST to `api.github.com`. Missing auth is **FAIL** + draft at `$PFY_STATE_DIR/catalog-issue-draft.md` — never a fake PASS.

Status refresh uses `gh issue view` / API GET + linked PR (timeline or `gh pr list`). Tools and Loop paint `open` / `closed` / `pr`.

### Gates

| Condition | Result | Next |
|-----------|--------|------|
| Entry X 070–075 / catalog PRs 70–75 | **SKIP** | catalog 70-75 HOLD (do not auto-lift) |
| Incomplete (I0, skip install, no smoke) | **SKIP** | pick a complete catalog entry |
| Another item already asked/open/pr | **FAIL** | finish or cancel the pending integration first |
| `gh` unauthenticated and no `GITHUB_TOKEN`/`GH_TOKEN` | **FAIL queue** | `gh auth login` then `gh issue create --repo themark-net/pfy-deanery` (draft in `$PFY_STATE_DIR/catalog-issue-draft.md`) |

That is not a live catalog write (`LIVE_HARD_OFF` still holds for TOOLS.md / tools.json).

## How to run

```bash
python3 scripts/pfy_live_org_queue_214.py --selftest
python3 scripts/pfy-gui.py --selftest
python3 scripts/pfy-board.py --help >/dev/null
bash -n scripts/pfy
```

Selftest: FAIL without auth + PASS with stub `create_fn`. Optional live dry-run GET only if a token/`gh` auth is present — **does not create issues**.

## Variables

| Name | Where | Purpose |
|------|-------|---------|
| `PFY_STATE_DIR` | `catalog-queue.json`, `catalog-issue-draft.md` | queue + FAIL draft |
| `GITHUB_TOKEN` / `GH_TOKEN` | env (existing) | Queue-for-org API if `gh` missing/unauthed |

Registry: [bootstrap/env/REGISTRY.md](../../bootstrap/env/REGISTRY.md).

## Do not

- Reopen #76 · unpark #198 · catalog 70–75 HOLD (do not auto-lift / do not merge #75)
- Fake PASS when auth is missing
- Spam issues from `--selftest`
- `LIVE_HARD_OFF`: no live catalog writes / no TOOLS.md triple-write from this path
- No operator git/npm/CI chore
