---
name: catalog-apply-and-ceiling
description: Apply a verdict to a stage card and auto-raise tier_ceiling to I3 only when both gates pass and the risk class is none. The scripts decide. Do not hand-edit the card.
---

# Catalog apply and ceiling

Use this when a verdict should move `integration_stage`, or when a passing eval should raise `tier_ceiling` to I3. The checkers are `scripts/catalog_apply_verdict.py` and `scripts/catalog_auto_raise.py`. Do not reimplement them.

## Inputs

- A stage card `data/stages/<slug>.json`.
- The latest `eval/<dir>/<slug>/VERDICT.json`. Latest means the last path in sorted order.
- Schema: `docs/ops/VERDICT.schema.json`.
- Optional `--date YYYY-MM-DD` for history. Default is the America/Los_Angeles date, or `PFY_LOOP_TODAY` when that is set.

## Outputs

- Apply writes `integration_stage` only when `proposed_stage` is within the allowed ceiling. A refusal leaves the card bytes unchanged and starts stderr with `refused:`.
- `--scan` writes `eval/catalog-verdicts/CEILING-MISMATCHES.md` and does not write cards.
- Auto-raise writes only `tier_ceiling` and appends `ceiling_history`.
- History object: `{"from","to","by":"catalog_loop","date","reason","evidence":[paths]}`.
- `--dry-run` prints the plan and writes nothing.

## Raise rule

Raise `tier_ceiling` to I3 only when `value_gate` and `modularity_gate` are pass and the risk class is `none`.

Never demote. Never lower a ceiling. Never touch a card whose ceiling is already above I3. A ceiling that is already I3 is unchanged.

Skip when the gates fail or the verdict is missing. Refuse when the risk class is `security`, `live-money`, `runtime-takeover`, or `unknown`. Those rows belong in needs-mark.

A slug listed in `eval/catalog-queue/exclusions.tsv` is refused by apply and by auto-raise, before the gate check. The card bytes stay as they were. Passing gates do not raise it. `atomic-task-graph-atg` stays on that list. Do not promote it and do not raise its ceiling.

`risk_class` on the card wins when it is one of `security`, `live-money`, `runtime-takeover`, or `none`. An invalid or non-string value is `unknown`. With no field, classify tokens. No tokens is `unknown`. Two classes is `unknown`. One class is that class. Otherwise `none`.

`risk_class: none` wins over keyword classes. It does not override a GPU hit, a pull over 25 GB, or a release or deploy hit. Those still need the operator and are not launched.

## Word lists

The lists live in `scripts/catalog_auto_raise.py`. These tokens must match that script.

Tokenizer: `[a-z0-9]+(?:-[a-z0-9]+)*` on the lowercased text of `uses`, `features`, `tags`, `catalog_tags`, and `next_gate`.

Whole tokens:

- security: security, secret, secrets, credential, credentials, password, pentest, penetration, exploit, vulnerability, sast, keyring
- live-money: trading, broker, payment, payments, wallet, invoice, bank, funds, stripe, live-money
- runtime-takeover: runtime-takeover, takeover, privilege, sudo, rootkit, host-control

GPU: `weights` matches only as a whole token. `gpu`, `vulkan`, `rocm`, `hip`, and `cuda` also match as a hyphen part, so `cpu-gpu` matches and `open-weights` does not.

Release: `release`, `deploy`, and `deployment`, as a whole token or a hyphen part.

Size: a number strictly greater than 25 followed by `gb` or `gib`. An exclusion reason that says `25 gb` or `25gb` is `pull-over-25gb`.

## Card guard

`scripts/catalog_card_guard.py --worktree DIR` reads `git diff origin/main...HEAD` after the rebase. It restores `integration_stage`, `tier_ceiling`, and `ceiling_history` from current `origin/main` unless `--allow-stage` or `--allow-ceiling` names that slug. A new card stays I0 unless `--allow-stage` is set, and it drops a ceiling unless `--allow-ceiling` is set. It does not open a card the lane did not change.

## Markers

Apply and raise do not create lane markers. A refusal file is written by the lane driver, not by these commands.

## Duplicate-run guard

The commands are pure over the cards and verdicts. A second run with the same inputs appends no second history row when the last history entry is already the same raise. Do not launch a second writer.

## Stop rules

- Do not hand-edit a card to force a stage or a ceiling.
- Do not raise a security, live-money, runtime-takeover, or unknown card.
- Do not raise a GPU card, a pull over 25 GB, or a release or deploy card.
- Stop on stderr that starts with `refused:`. Leave the card bytes as they were.

## Commands

```bash
python3 scripts/catalog_apply_verdict.py --card data/stages/<slug>.json --verdict <VERDICT.json>
python3 scripts/catalog_apply_verdict.py --scan
python3 scripts/catalog_auto_raise.py --dry-run
python3 scripts/catalog_auto_raise.py --slug <slug>
python3 scripts/catalog_card_guard.py --worktree <dir>
```
