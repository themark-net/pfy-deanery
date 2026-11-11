# Promotion rules

Source of truth: `data/promotion-rules.json`. Engine: `scripts/promotion_rules.py`.

Operator decision, 2026-11-10 7:04am PT: rules move cards through the pipeline, nobody signs off. Every stage move from I0 to I4 and every `tier_ceiling` raise is decided by machine-checked rules. Only a hard stop waits for a person. This replaces the security full gate (GATE.json with a Tester and Reviewer PASS) from 2026-11-10 12:08am PT.

## How a decision is made

1. The card's track is `security` when it is a scanner or guard (`risk_class: security`, or the security words in `scripts/catalog_auto_raise.py`). Otherwise `default`.
2. For a target stage the engine runs every rule listed for each step up to that stage on that track, in the modes the rule names (`apply`, `scan`, `ceiling`, `launch`).
3. The allowed stage is the highest step whose rules all pass. A verdict is applied only when every rule for its `proposed_stage` passes.
4. Each promotion, demotion, raise, and refusal writes one `promotion_history` entry on the card: the passed rule IDs, the failed rule IDs with the exact detail, the rules version, the verdict path, and the date.
5. A refusal with no hard stop and no failed verdict gate is re-applied by `catalog_apply_verdict.py --retry-refused` on the next tick once eval-structural is green on origin/main.

## Stage steps

| Step | Default track | Security track adds |
| --- | --- | --- |
| I1 | R-not-excluded, R-evidence, R-tier-ceiling | |
| I2 | the six hard stops, R-modularity-gate | S-sandlock-verdict |
| I3 | R-value-gate, R-main-receipt, R-self-pipeline | S-sandlock-trial-clean, S-profile-readonly, S-wiring, S-ci-green |
| I4 | R-embed | |

## Ceiling raise (auto-raise)

| Track | Raise to | Rules |
| --- | --- | --- |
| default | I3 | R-not-excluded, hard stops, R-classifiable, R-modularity-gate, R-value-gate (latest verdict) |
| security | I2 | R-not-excluded, hard stops, R-classifiable |
| security | I3 | the I2 rules plus R-modularity-gate, R-value-gate, S-sandlock-trial-clean, S-profile-readonly, S-wiring |

## Rules

- `R-not-excluded`: the slug is not in `eval/catalog-queue/exclusions.tsv`.
- `R-classifiable`: `risk_class` is valid, or the card text has words to classify.
- `R-evidence`: the evidence list supports the target up to I2 (I1 any artifact; I2 a measured probe, `make:`, or `path:`).
- `R-tier-ceiling`: the target is at or below `tier_ceiling`.
- `R-modularity-gate`, `R-value-gate`: the verdict gate is `pass`.
- `R-main-receipt`: a `receipt:` item is a valid main-run receipt (`run_kind` pipeline or gate) whose `main_sha` is on origin/main.
- `R-self-pipeline`: a CI, testing, or review tool passes the `catalog_check.py` self_pipeline check.
- `R-embed`: a `submodule:` or `subtree:` item.
- `S-sandlock-verdict`: the verdict records `"sandbox": "sandlock"`.
- `S-sandlock-trial-clean`: `eval/integrate/<slug>/sandbox-trial.json` has `run_kind` sandbox-trial, `sandbox` sandlock, `outcome` ok, `exit_code` 0, `unsandboxed_lines` 0, and `scan_verdict` CLEAN when present.
- `S-profile-readonly`: that trial's `profile` (written by `scripts/integrations/sandlock/confine.py`) writes only under `./tmp/`, `/tmp/` or `$TMPDIR` (plus `/dev/null`, which reaches no file), has network `deny` or a pinned fetch list, `sudo` false, a clean env, and no read of the home root or a secrets path (`.ssh`, `.gnupg`, `.aws`, `.grok`, `.config`, `.netrc`, `.dev.vars`, `auth.json`, `.docker`, `.kube`).
- `S-wiring`: the card's `wiring` is `advisory` or `non-blocking` (a CI step with the comment `# pfy-advisory: <slug>` and `continue-on-error: true`), or `deny-only` with an existing `fail_open_test`.
- `S-ci-green`: eval-structural concluded success on origin/main (public API, no token; `PFY_MAIN_GREEN=1` or `0` overrides in tests).

## Hard stops

The only rules that stop and write a needs-mark row (kind `hard-stop`, the reason starts with the rule ID):

- `HS-live-money`: live money or trading.
- `HS-release-deploy`: a release or a deploy.
- `HS-secrets`: secrets handling (keyring, vault, password or secrets managers, credential stores).
- `HS-runtime-takeover`: privilege or host control.
- `HS-gpu-unapproved`: a GPU run with no `gpu` row in the ops `approvals.tsv`.
- `HS-pull-over-25gb-unapproved`: a pull over 25 GB with no `pull-over-25gb` row there.

A card can narrow its row with `hard_stop_scope` (for example `real install only`): the scope is added to the reason, so the row names the one action still waiting. A sandboxed eval with a throwaway HOME is not that action. A slug in `eval/catalog-queue/exclusions.tsv` is closed: it never launches and gets no hard-stop row.

## Inspect one card

```bash
python3 scripts/promotion_rules.py --slug bumblebee --mode apply --target I3
python3 scripts/promotion_rules.py --slug bumblebee --mode ceiling --target I3
```

Each line is `pass` or `fail`, the rule ID, and the detail. Exit 3 when a rule fails.

## Changing a rule

Edit `data/promotion-rules.json` and, for a new rule ID, add its check to `CHECKS` in `scripts/promotion_rules.py`. Loading fails closed when the file and the checks disagree. A rule change is a pipeline change: its own commit, a test, and the catalog-first note.
