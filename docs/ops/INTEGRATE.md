# I2 to I3 integration

**Status:** Lane process for tools that already reached I2.  
**Related:** [integration-stages.md](integration-stages.md) · [integrate/TEMPLATE.md](integrate/TEMPLATE.md) · [MODULAR-CI.md](MODULAR-CI.md)

A tool is I3 only after it ran in a real pipeline or gate on `origin/main` and left a receipt. A merged wiring diff, a doc, a plan, or a run on a feature branch is not that receipt.

`make:` and `path:` evidence record an operator path. They support I2. They do not support I3 or I4.

This process does not raise `tier_ceiling` and does not demote `integration_stage`. If apply refuses, record the refusal and stop.

## Intake

List every I2 card with no integration yet. A `receipt:` evidence string, or a non-empty `integration_ticket`, excludes the card. Ceilings are read only.

```bash
python3 scripts/integrate_intake.py
python3 scripts/integrate_intake.py --json
```

Same cards, same bytes. A ceiling of I0, I1, I2, blank, or any value other than I3 or I4 is flagged `tier_ceiling below I3: needs Mark`. Do not change the ceiling in the lane. Ask Mark before a ticket for a flagged card.

## Ticket template

Copy [integrate/TEMPLATE.md](integrate/TEMPLATE.md) to `tmp/TICKET-<slug>.md` in the checkout that starts the lane. Fill every section. The driver reads that file, or `docs/ops/integrate/tickets/<slug>.md` when the tmp file is absent.

The ticket names where the tool sits in the pipeline, what it replaces or adds, how it fails safe, what stops two runs, which real run on main writes the receipt, and what the receipt contains.

## Lane run

One slug, one driver. No pull request.

```bash
scripts/integrate_lane.sh --slug <slug> [--date MMDD] [--ticket FILE]
```

Default `--date` is UTC `MMDD`. The branch is `bot/integrate-<slug>-<date>`. The worktree is `tmp/integrate/wt/<slug>`, cut from `origin/main`.

Order:

1. If `tmp/integrate/<slug>.dispatched` already exists, exit 2. No fetch, no worktree, no grok, no push.
2. Create that marker with `noclobber` before any git or grok call.
3. If `tmp/STOP` exists, write `<slug>.parked` with reason `STOP file` and exit 0.
4. `git fetch origin`, then `git worktree add -b bot/integrate-<slug>-<date>`.
5. `python3 scripts/catalog_check.py` in the worktree.
6. `python3 scripts/grill_ticket.py` on the ticket.
7. Headless Grok Build implement, then a self-review. Each is `grok --always-approve --output-format plain --prompt-file <prompt>`, up to 3 attempts.
8. Sanity on files changed versus `origin/main`: `python3 -m py_compile` for Python, `bash -n` for shell, JSON parse, YAML parse. Then `catalog_check.py` and `check_no_encoded_payloads.py` again.
9. `python3 scripts/test_select.py --base origin/main`. Run the printed modules with `python3 scripts/run_tests.py`. An empty module list skips the runner. No full suite, no shared lock.
10. Land. See below.

A failed step appends `tmp/integrate/progress.md`, writes `tmp/integrate/<slug>.parked` with the reason, and does not push. The dispatched marker stays, so a second start exits 2 until a person removes it.

Log tails use `tail -n 40`. Do not use `tail -40`.

What triggers it: a person, or a later scheduler, runs the driver with a slug from intake.

What it does: it reads the ticket, the stage card, and `origin/main`. It writes a worktree, lane markers under `tmp/integrate/`, and, only on a fast-forward, `refs/heads/main`. The child lane writes the wiring and the receipt. This driver does not edit stage cards by itself.

What it triggers next: the child lane's real pipeline or gate run on main, which writes `eval/integrate/<slug>/receipt.json`. Stage apply is a separate command after that receipt exists.

Where a human re-enters: see the last section.

What stops two runs: the dispatched marker for that slug. Two different slugs are two lanes. The land push is a fast-forward. A rejected push rebases and retries up to 3 times, then parks.

## Landing

From the worktree SHA:

```bash
git fetch origin && git merge-base --is-ancestor origin/main <sha> && git push origin <sha>:refs/heads/main
```

When `origin/main` is not an ancestor of `<sha>`, rebase the worktree onto `origin/main` and retry. Up to 3 attempts. A rejected push takes the same retry. There is no force push and no pull request.

On success the driver writes:

| Marker | Meaning |
| --- | --- |
| `tmp/integrate/LANDED_<slug>` | The SHA that was pushed to `origin/main` |
| `tmp/integrate/<slug>.done` | The same SHA |
| `tmp/integrate/progress.md` | One UTC line per step |

`tmp/integrate/<slug>.parked` is the failure file. Its body is the reason.

## Receipt

Path: `eval/integrate/<slug>/receipt.json`. A receipt whose `main_sha` is not an ancestor of `origin/main` is invalid. Commit the file on main in the same run that produced it, or in a follow-up whose `main_sha` is already on main. Do not point the card at a branch SHA.

```json
{
  "slug": "<slug>",
  "run_kind": "pipeline",
  "main_sha": "<40 hex chars, ancestor of origin/main>",
  "run_id": "<id or omit when log is set>",
  "log": "<path or omit when run_id is set>",
  "started": "2026-11-08T00:00:00Z",
  "finished": "2026-11-08T00:01:00Z",
  "outcome": "ok",
  "tool_version": "<version string>",
  "did": "<what the tool did in that run>"
}
```

`run_kind` is `pipeline` or `gate`. `log_path` is accepted in place of `log`. One of `run_id`, `log`, or `log_path` is required. `slug` matches the card slug. `did` is what the tool did in that run.

The card evidence item is `receipt:eval/integrate/<slug>/receipt.json`.

## Stage apply

`scripts/catalog_apply_verdict.py` refuses I3 and I4 without a valid main-run receipt. The card bytes stay unchanged on every refusal.

| Return | When |
| --- | --- |
| `missing-main-receipt` | No `receipt:` file, or the path is missing. `make:` and `path:` alone hit this. |
| `receipt-malformed` | The receipt is not the object above, `run_kind` is not `pipeline` or `gate`, or the card file is not JSON. |
| `receipt-sha-not-on-main` | `main_sha` is not an ancestor of `origin/main`. |
| `git-unavailable` | `origin/main` cannot be resolved, or git is missing. |
| `tier_ceiling` | The card ceiling is below the target. A valid receipt does not lift it. |
| `self_pipeline` | A CI, testing, or review tool still fails the `catalog_check.py` rule at I3. |
| `missing-embed` | The target is I4 and no evidence item starts with `submodule:` or `subtree:`. |
| none | The write is allowed. I4 needs the receipt and an embed item. |

`apply_stage(card_path, target, repo_root)` is the function the tests call. The CLI verdict path uses the same receipt rule inside the ceiling. Value and modularity gates on a verdict are unchanged. The `self_pipeline` cap is unchanged.

```bash
python3 scripts/catalog_apply_verdict.py --scan
```

Exit 0 means the scan finished. Mismatches are flags, not demotions. Cards already at I3 or I4 without a valid receipt show one of the reason codes above. Cards below I3 do not get those codes. `git diff --stat data/stages` stays empty.

## Human re-entry

Mark raises a `tier_ceiling`. This process does not.

Mark decides whether a flagged I3 or I4 card should be demoted. The scan does not write the card.

A person removes `tmp/integrate/<slug>.dispatched` after reading `<slug>.parked` when a retry is wanted.

`tmp/STOP` in the driver checkout parks the lane before fetch. `tmp/STOP` in the worktree parks before the self-review or the push.

Fail safe: a missing grok, a grok error, a failed check, a dirty tree, or a land that cannot fast-forward parks and leaves main alone. Wiring added by a child lane must default to today's behavior when the tool binary is missing, errors, or times out. A guard that is meant to deny destructive commands fails closed and says so in the ticket.

Trading, release, and secret changes still take the full gate. This driver does not.
