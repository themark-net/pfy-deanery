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
python3 scripts/catalog_fit_triage.py pending [--limit N] [--mock PATH] [--write]
python3 scripts/catalog_fit_triage.py replay [--mock PATH] [--model NAME] [--out PATH]
```

`PFY_CATFIT_MODEL` overrides the default `qwen3.6:35b`. When that variable is unset, a missing install (`GET /api/tags`) or a generate load error (HTTP error, `model requires more system memory`, `not found`, unreachable model load) retries once with `qwen2.5:14b` (`PFY_CATFIT_FALLBACK_MODEL`). The stderr note is `catalog-fit: fallback <requested> -> <used> (<reason>)`. The written record and the replay file store `model` as the tag that ran and `fallback_from` as the requested tag when a fallback happened. An explicit `PFY_CATFIT_MODEL` or `--model` does not fall back. The host defaults to `http://127.0.0.1:11434` (`PFY_CATFIT_HOST`, else `OLLAMA_HOST`). Temperature is 0. Generate timeout is `PFY_CATFIT_TIMEOUT` seconds (default 120). Do not pull a model. CI sets `PFY_CATFIT_MOCK` or `--mock` and does not call Ollama, and the tags check is skipped under that mock. `--write` stores `eval/catalog-fit/<slug>.json`. Replay writes its result under `./tmp/` unless `--out` names another path.

`pending --limit N --write` selects I0 cards with no fit file, skips names starting with `_` and slugs in `eval/catalog-queue/exclusions.tsv`, and triages them in slug order. N defaults to `PFY_CATFIT_PER_TICK` (4). Exit 0 and exit 3 write the record. Exit 1 writes nothing, logs one line, and continues with the next slug. The command itself exits 0 so a down Ollama does not stop the caller.

## What a stored verdict does

A confident `skip_install`, `redundant`, or `awareness` (confidence at or above the Jev gate) caps promotion at I1 via `R-catalog-fit` and blocks launch. The eval queue omits that slug. A missing file or a low confidence passes: the normal eval lane decides. Hard stops in `data/promotion-rules.json` still run first.

## Factory

1. Trigger: each catalog loop tick, before `catalog_eval_queue.py`, for new I0 cards. Also `triage <slug>` by hand. This is local inference, not a Grok lane, so it does not consume the 20/day lane-start budget. The per-tick cap is `PFY_CATFIT_PER_TICK` (default 4), serial, with `PFY_CATFIT_TIMEOUT` on each generate. When `PFY_MODEL_LOCK` is set the call holds `scripts/model_lock.sh`.
2. Reads the stage card, the exclusions file, and the rubric. Optional Ollama on 127.0.0.1:11434. Writes `eval/catalog-fit/<slug>.json` only with `--write`. Does not edit the card. Does not pull a model.
3. The same tick rebuilds the eval queue. A confident negative omits the slug and blocks launch.
4. A human re-enters on exit 3 (the record is kept; the normal eval lane decides). A hard stop still writes needs-mark. Exit 1 (Ollama down) leaves no file, logs one line, and the tick continues.
5. Slugs run in order, capped per tick. A slug that already has a fit file is not triaged again. `--write` replaces the same path. The script does not launch a lane.
