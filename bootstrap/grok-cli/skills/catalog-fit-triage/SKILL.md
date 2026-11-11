---
name: catalog-fit-triage
description: Ask a small local model whether a Deanery catalog tool fits or should skip install. The script gates confidence with Jev. Deterministic hard stops stay authoritative.
---

# Catalog-fit triage

Use this before a Grok catalog lane when a card may be a poor fit, a duplicate, or a skip-install. The driver is `scripts/catalog_fit_triage.py`. Do not reimplement the rubric, the JSON check, or the confidence gate.

Deanery (pfy-deanery) tracks, catalogs, evaluates, and integrates tools local-first. This triage keeps a small local model off the Grok lane when the tool does not fit.

## Rubric

The rubric and the labeled cases live in `data/decision-gates/catalog-fit.v0.json`. Dimensions:

- fit: the local-first mission and an existing stage gap
- overlap_with: an existing catalog slug, or null
- skip_install: a safe default exists without installing
- blast_radius: low, medium, or high (config rewrite, runtime takeover, secrets or account pools are high)
- unique_gap: Unique value from `docs/evaluation-framework.md` (clear gap, overlap, or redundant)

Verdicts: `fit`, `skip_install`, `redundant`, `awareness`.

## Model output

The local model emits only this JSON object and no other text:

```json
{"slug": "<slug>", "fit": false, "overlap_with": null, "verdict": "awareness", "reason": "<why>", "confidence": 0.9}
```

`fit` is a boolean. `overlap_with` is a string or null. `verdict` is one of `fit`, `skip_install`, `redundant`, `awareness`. `reason` is a string. `confidence` is a margin from 0 to 1, never percent-correct.

`scripts/pfy_jev_230.py` (`decide_choice`, `conf_chip`, `conf_gate`, `decision_exit_code`) is the only decision layer. Exit 0 is a confident verdict. Exit 3 is escalate (confidence under the gate, or JSON that is not a verdict). Exit 1 is broken. Unusable JSON is never `fit`.

## Commands

```bash
python3 scripts/catalog_fit_triage.py triage <slug> [--mock PATH] [--write]
python3 scripts/catalog_fit_triage.py replay [--mock PATH] [--model NAME] [--out PATH]
```

`PFY_CATFIT_MODEL` defaults to `qwen2.5:14b`. The host defaults to `http://127.0.0.1:11434` (`PFY_CATFIT_HOST`, else `OLLAMA_HOST`). Temperature is 0. Do not pull a model. CI sets `PFY_CATFIT_MOCK` or `--mock` and does not call Ollama. `--write` stores `eval/catalog-fit/<slug>.json`. Replay writes its result under `./tmp/` unless `--out` names another path.

## What a stored verdict does

A confident `skip_install`, `redundant`, or `awareness` (confidence at or above the Jev gate) caps promotion at I1 via `R-catalog-fit` and blocks launch. The eval queue omits that slug. A missing file or a low confidence passes: the normal eval lane decides. Hard stops in `data/promotion-rules.json` still run first.

## Factory

1. Trigger: triage one card before a Grok lane. This slice does not start the model from the catalog loop.
2. Reads the stage card and the rubric. Optional Ollama on 127.0.0.1:11434. Writes `eval/catalog-fit/<slug>.json` only with `--write`. Does not edit the card.
3. Nothing launches next. A confident negative omits the slug from the eval queue and blocks launch.
4. A human re-enters on exit 3. A hard stop still writes needs-mark.
5. Queue bytes stay deterministic. `--write` replaces the same path. The script does not launch a lane.
