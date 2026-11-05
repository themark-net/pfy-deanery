# Handoff: MVP parallel plan 2026-10-31

Status: done. Planning only. Branch `bot/mvp-plan-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-plan-1031`. Base `origin/main` `85c53dc`. No product code. No lanes started. No PR. No merge. No tag.

## Commits

| Commit | What |
|--------|------|
| `39fc87c` | This session's drop-in (already on the branch before the plan) |
| `b4e5323` | `docs/plans/MVP-PARALLEL-1031.md` and `docs/plans/MVP-PARALLEL-1031-lanes.tsv` |
| `875b3f8` | Ten lane drop-ins, plus the `.gitignore` ownership line in the plan |

## What Mark runs next

Launch one cloud Build per row of `docs/plans/MVP-PARALLEL-1031-lanes.tsv`. Five rows. Every `needs_local` value is `no`. Do not launch `mvp-integrate-1031` until those five have pushed. Do not launch round 2 until `origin/bot/mvp-integrate-1031` has a handoff.

Round 1:

| name | branch | base |
|------|--------|------|
| mvp-cloud-1031 | `bot/mvp-cloud-1031` | `origin/main` |
| mvp-review-fix-1031 | `bot/mvp-review-fix-1031` | `origin/bot/mvp3-review-retry` |
| mvp-preflight-1031 | `bot/mvp-preflight-1031` | `origin/main` |
| mvp-surface-1031 | `bot/mvp-surface-1031` | `origin/main` |
| mvp-eval-1031 | `bot/mvp-eval-1031` | `origin/main` |

Integration: `bot/mvp-integrate-1031` from `origin/main`, drop-in `docs/build-dropins/mvp-integrate-1031.md`. Merge order is in the plan.

Round 2 drop-ins, not in the TSV: `mvp-dedupe-1031`, `mvp-sandbox-gate-1031`, `mvp-local-t5-1031` (the only local-model lane), `mvp-daily-card-1031`.

## Daily command the lanes are building

`./pfy build "<task>"` is cloud Grok: worktree, gate, review, commit on a `cloud/` branch, receipt schema `pfy-cloud-build/1`, no push. `./pfy build -p` stays the jev dogfood wrap. `./pfy build --local` stays opt-in. Local stays NO-GO as the default.

## Tests

None. This session was plan-only. Pregate not run: plan-only session.

## How this fails and how we recover

| Risk | What you see | Recovery |
|------|----------------|----------|
| Two lanes edit one file | Merge conflict in integration | The plan matrix names the owner. Keep the owner's side. `docs/TODO.md` keeps both facts. |
| Cloud lane and preflight lane each classify errors | Two copies of the regexes until integrate | Demo may ship with the inline copy. `mvp-dedupe-1031` deletes it after integrate. |
| A round-1 branch never appears | Integrate cannot demo | Record the skip. Demo only if both `scripts/pfy_build_cloud.py` and `eval/mvp-1031/check_receipt.py` exist. |
| Demo hits rate limit or auth | Receipt is not PASS | Commit that receipt. Do not fall through to `--local`. |

## Gate

Docs only. Pregate plus Reviewer when the host is idle. No Tester gate. No Feature GO.

## Next step

Operator launches the five TSV rows. This session stops here.
