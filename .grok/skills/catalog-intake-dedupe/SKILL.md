---
name: catalog-intake-dedupe
description: Turn one source string into an I0 stage card, or report the existing catalog match. The script decides. Do not reimplement the match.
---

# Catalog intake dedupe

Use this when a source entry should become an I0 card, or when you need to know that the source is already in the catalog.

The checker is `scripts/catalog_intake_dedupe.py`. Read its output. Do not copy its slug or match rules into a prompt.

## Inputs

- One source string: a GitHub URL, `owner/repo`, a name, or a path to a local directory.
- Optional `--root` for a repo root. Default is the repo that contains the script.
- Optional `--write-card`. Without it, the command only prints.

## Outputs

One line:

- `new <slug>` when nothing matches.
- `duplicate <slug> <match>` when a stage card, an entry, or `sources/x-posts.md` already has the source.

`--write-card` writes `data/stages/<slug>.json` for a new source. `integration_stage` stays I0. A duplicate never writes.

The card records evidence the input actually has: the repo URL, a license when a local tree states one, a pin SHA when the source or a local git HEAD has one, and one README claim from a local tree. No network. `tier_ceiling` is I1 when that list is non-empty, so a later apply can move the card to I1. A name with none of those facts stays `evidence: []` and `tier_ceiling: I0`.

## Markers

This step has no lane marker. The card file is the record. A later lane must not create a second card for the same slug.

## Duplicate-run guard

Run the command once. If the line starts with `duplicate`, stop. Do not call `--write-card` again for that source.

## Stop rules

- Empty slug: the script exits 1 and writes `empty slug` on stderr. Do not invent a slug.
- Duplicate: stop. Do not edit the matched card in this step.
- Do not set `integration_stage` above I0 here. Apply does that.
- Do not set `tier_ceiling` above I1. It is I1 only when the evidence list is non-empty, and I0 when the source has no repo URL, license, pin, or README claim.

## Supersede intake hook

When the source may cover track, catalog, evaluate, or integrate, ask the checker. Do not reimplement the part count.

```bash
python3 scripts/supersede_check.py --parts track,catalog
```

The command prints one JSON object with `supersede_candidate`. True means two or more of those parts. Tag the source `#supersede-candidate` and add a row to `data/supersede-watchlist.json`. A false result does not add a row. This command does not run the catalog loop.

## Commands

```bash
python3 scripts/catalog_intake_dedupe.py "<source>"
python3 scripts/catalog_intake_dedupe.py "<source>" --write-card
python3 scripts/supersede_check.py --parts track,catalog
```
