---
name: catalog-apply-and-ceiling
description: Apply a verdict to a stage card and raise tier_ceiling by the machine-checked rules in data/promotion-rules.json. Nobody signs off; only a hard-stop rule writes a needs-mark row. The scripts decide. Do not hand-edit the card.
---

# Catalog apply and ceiling

Use this when a verdict should move `integration_stage`, or when a passing eval should raise `tier_ceiling`. The checkers are `scripts/catalog_apply_verdict.py` and `scripts/catalog_auto_raise.py`, and both read `data/promotion-rules.json` through `scripts/promotion_rules.py`. Do not reimplement them. The rules are explained in `docs/ops/promotion-rules.md`.

## Rule-based promotion (operator decision 2026-11-10, 7:04am PT)

Every move from I0 to I4, and every ceiling raise, is decided by the rules file. Nobody signs off and nothing waits for a person, except a hard stop.

- Stage steps (default track): I1 needs `R-not-excluded`, `R-evidence`, `R-tier-ceiling`. I2 adds the hard stops, `R-modularity-gate`, and `R-catalog-fit` (a confident skip_install, redundant, or awareness caps the stage at I1). I3 adds `R-value-gate`, `R-main-receipt`, `R-self-pipeline`. I4 adds `R-embed`.
- Security track (a scanner or guard): I2 also needs `S-sandlock-verdict` (the verdict records `"sandbox": "sandlock"`). I3 also needs `S-sandlock-trial-clean`, `S-profile-readonly`, `S-wiring`, and `S-ci-green`. There is no GATE.json and no Tester or Reviewer sign-off.
- Ceiling (auto-raise): default track I3 when not excluded, no hard stop, `R-classifiable`, the latest verdict passes both gates, and `R-catalog-fit` does not cap the card at I1. Security track I2 when not excluded, no hard stop, and classifiable, with the same catalog-fit cap; I3 when the trial is clean, the profile is read-only, the wiring passes, and both gates pass.
- Print the rules for one card: `python3 scripts/promotion_rules.py --slug <slug> --mode apply --target I3`.

## Hard stops

Only these stop and write a needs-mark row (kind `hard-stop`, reason starts with the rule ID):

- `HS-live-money`, `HS-release-deploy`, `HS-secrets`, `HS-runtime-takeover`, `HS-gpu-unapproved`, `HS-pull-over-25gb-unapproved`.

GPU and over-25 GB blocks clear per slug through `eval/catalog-queue/approvals.tsv` in the private ops checkout (`slug`, `block`, `decided`, `note`; block is `gpu` or `pull-over-25gb`). `--launch-check` prints `skip <slug> gpu-driver` for an approved card: the loop never starts it, and `scripts/gpu_lane_driver.sh` runs approved lanes one at a time after GPU, RAM, and disk checks. A release, deploy, money, secrets, or takeover hit cannot be approved there.

Everything else that used to wait (ceiling flags, demotion flags, parked lanes, unknown risk, exclusions that name the operator) is a failed rule in the card's `promotion_history`, not a row.

## Inputs

- A stage card `data/stages/<slug>.json`.
- The latest `eval/<dir>/<slug>/VERDICT.json`. Latest means the last path in sorted order.
- Schema: `docs/ops/VERDICT.schema.json`.
- For a security tool: `eval/integrate/<slug>/sandbox-trial.json` from `scripts/integrations/sandlock/trial.py`, and a `wiring` object on the card.
- Optional `--date YYYY-MM-DD` for history. Default is the America/Los_Angeles date, or `PFY_LOOP_TODAY` when that is set.

## Outputs

- Apply writes `integration_stage` only when every rule for `proposed_stage` passes. A refusal starts stderr with `refused:` and writes only one `promotion_history` entry: the stage, ceiling, and evidence stay as they were.
- Ledger entry: `{"kind": "stage"|"ceiling", "from", "to", "result": "promote"|"demote"|"raise"|"refuse", "passed": [rule IDs], "failed": [{"rule", "detail"}], "rules": "data/promotion-rules.json@v1", "by": "rules", "date", "verdict"}`. An entry equal to the last one apart from the date is not appended again. A stay writes nothing.
- `--retry-refused` re-applies the recorded verdict of each refused card with no hard stop and no failed verdict gate once eval-structural is green on origin/main. The loop runs it every tick.
- `--scan` writes `eval/catalog-verdicts/CEILING-MISMATCHES.md` (each row names the failed rules) and does not write cards.
- Auto-raise writes `tier_ceiling`, appends `ceiling_history` (with `rules`), and writes the ceiling ledger entry. A refusal with no verdict yet and no hard stop is not written.
- `--dry-run` prints the plan and writes nothing.

## Never

Never demote by hand. Never lower a ceiling. Never touch a card whose ceiling is already above I3.

A slug listed in `eval/catalog-queue/exclusions.tsv` fails `R-not-excluded` in apply and auto-raise. `atomic-task-graph-atg` stays on that list.

## Risk track and word lists

`risk_class` on the card wins when it is one of `security`, `live-money`, `runtime-takeover`, `secrets`, or `none`. An invalid value fails `R-classifiable`. With no field, the tokens decide. A card with no tokens fails `R-classifiable`.

`risk_class: none` or `security` wins over the money, takeover, and secrets words. It does not override a GPU hit, a pull over 25 GB, or a release or deploy hit.

The lists live in `scripts/catalog_auto_raise.py`. These tokens must match that script.

Tokenizer: `[a-z0-9]+(?:-[a-z0-9]+)*` on the lowercased text of `uses`, `features`, `tags`, `catalog_tags`, and `next_gate`.

Whole tokens:

- security track: security, secret, secrets, credential, credentials, password, pentest, penetration, exploit, vulnerability, sast
- secrets handling (HS-secrets): keyring, vault, password-manager, secrets-manager, secret-store, secrets-store, credential-store, credential-helper, secrets-handling
- live-money (HS-live-money): trading, broker, payment, payments, wallet, invoice, bank, funds, stripe, live-money
- runtime-takeover (HS-runtime-takeover): runtime-takeover, takeover, privilege, sudo, rootkit, host-control

GPU: `weights` matches only as a whole token. `gpu`, `vulkan`, `rocm`, `hip`, and `cuda` also match as a hyphen part, so `cpu-gpu` matches and `open-weights` does not.

Release: `release`, `deploy`, and `deployment`, as a whole token or a hyphen part.

Size: a number strictly greater than 25 followed by `gb` or `gib`. An exclusion reason that says `25 gb` or `25gb` is `pull-over-25gb`.

## Security tools

- `--launch-check` prints `launch <slug> security-sandbox` for a security card below I2 with ceiling I2 or above. The loop starts that eval lane with `PFY_LANE_SANDBOX=sandlock`. Run the trial with `scripts/integrations/sandlock/trial.py` so the record carries the profile `confine.py` built (reads, writes, network deny, clean env, no sudo).
- Wiring on the card: `{"mode": "advisory"|"non-blocking", "where": ".github/workflows/<file>.yml"}` with a step that has the comment `# pfy-advisory: <slug>` and `continue-on-error: true`, or `{"mode": "deny-only", "where": "<hook path>", "fail_open_test": "tests/<file>.py"}`.

## Card guard

`scripts/catalog_card_guard.py --worktree DIR` reads `git diff origin/main...HEAD` after the rebase. It restores `integration_stage`, `tier_ceiling`, and `ceiling_history` from current `origin/main` unless `--allow-stage` or `--allow-ceiling` names that slug. A new card stays I0 unless `--allow-stage` is set, and it drops a ceiling unless `--allow-ceiling` is set. It does not open a card the lane did not change. `promotion_history` is the rules ledger and is kept.

## Markers

Apply and raise do not create lane markers. A refusal file is written by the lane driver, not by these commands. The eval lane commits a refusal that changed only `promotion_history`.

## Duplicate-run guard

The commands are pure over the cards, verdicts, and rules. A second run with the same inputs appends no second history or ledger entry. Do not launch a second writer.

## Stop rules

- Do not hand-edit a card to force a stage, a ceiling, or a ledger entry.
- Do not edit data/promotion-rules.json to pass one card. A rule change is a pipeline change with its own commit and tests.
- Stop on stderr that starts with `refused:`. The ledger entry names the failed rule; the loop re-checks it.

## Commands

```bash
python3 scripts/catalog_apply_verdict.py --card data/stages/<slug>.json --verdict <VERDICT.json>
python3 scripts/catalog_apply_verdict.py --retry-refused
python3 scripts/catalog_apply_verdict.py --scan
python3 scripts/catalog_auto_raise.py --dry-run
python3 scripts/catalog_auto_raise.py --slug <slug>
python3 scripts/promotion_rules.py --slug <slug> --mode apply --target I3
python3 scripts/catalog_card_guard.py --worktree <dir>
```
