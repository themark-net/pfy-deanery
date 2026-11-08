# Catalog eval queue

Generated work list for catalog evals. `scripts/catalog_eval_queue.py` reads stage cards and `exclusions.tsv`, then writes `queue.tsv`. Do not hand-edit `queue.tsv`. To drop a slug, add a row here with a reason and run the script again.

This replaces the hand-built `tmp/evq/queue.tsv` process. That file is not an input.

## Regenerate

```bash
python3 scripts/catalog_eval_queue.py
```

Defaults are `--stages data/stages`, `--exclusions eval/catalog-queue/exclusions.tsv`, and `--out eval/catalog-queue/queue.tsv`. Same cards and the same exclusions produce the same bytes. When the bytes already match, the run leaves the file in place.

## Columns

| column | source |
|--------|--------|
| n | 1-based position after the sort |
| slug | card filename without `.json` |
| mode | `trial`, `model`, or `ref` |
| gap | `next_gate`, or `-` when that field is missing or blank |
| entry | `entry`, or `-` |
| card | `{slug}.json` |
| why | `uses`, or `-`. A list is joined with `; ` |

Tabs and newlines inside a cell become spaces.

## Sort

`(mode rank, slug)`. Rank is trial 0, model 1, ref 2. Slug order is Unicode code point order. Row 4 is the fourth card in that order after exclusions. The full rules are in the script docstring.

## Mode

First match:

1. `ref` when intent is `reference`, `design_reference`, `ref_only`, or `pattern_only`, or a tag is `design-reference`, or `next_gate` is `read`, or `next_gate` contains the word `reference`.
2. `model` when a tag is `local-model`, or `next_gate` is `model-probe`.
3. `trial` otherwise.

Tags come from `tags` and `catalog_tags`. A leading `#` is ignored. Comparison is case-insensitive. `ref` wins when a card also matches `model`.

`trial` is an install-and-probe candidate. `model` is a probe that needs the local-model lock. `ref` is a design read with no install.

## Filters

Every `*.json` in the stages directory is a row, except names that start with `_` and slugs listed in `exclusions.tsv`. `integration_stage` must be a non-empty string. The stage value does not drop or reorder a row. `tier_ceiling`, `handoff_by`, `potential`, and `features` do not change the queue.

## Exclusions

The header is `slug`, then `reason`, separated by a tab. Each later row needs a non-empty reason. A slug with no card stays in this file so the reason is not lost. An empty reason, a bad header, or a duplicate slug fails the run and does not create or replace `queue.tsv`.

The seed reasons come from the Nov 7 exclusion list (needs Mark's GO, blocked on Hermes, paid gateway, account manager, Vulkan approval, upstream smoke that exits 2, Apple Silicon only, GGUF over the pull cap, methodology notes with no tool, and first-party or already-in-use cards).

## Failure

A malformed card or a missing `integration_stage` prints the filename and the problem on stderr, exits non-zero, and does not create or replace the queue file.
