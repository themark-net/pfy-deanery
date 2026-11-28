# X intake 2026-11-27: entry 210 and stage card

Public catalog notes for this intake batch. Operator records stay in the private ops repo.

## What landed

- Entry `sources/entries/210-council-of-high-intelligence.md`, I0 awareness, with an I0 stage card `data/stages/council-of-high-intelligence.json`.
- Smoke `examples/x-intake-local/smoke_210.py` with 7 stub tests (`tests/test_x_intake_smoke_210.py`). It checks the pinned
  GitHub commit and exits 2, because nothing is cloned or installed.

## Queue mode

The card has a `trial` gate: a `--duo` run on local models over a few logged Deanery decisions, compared with the
current single-pass decision layer. The open question is whether forced dissent changes any decision enough to justify
the extra model calls; full councils are out of scope for routine gates.

## How to check

```
python3 -m unittest tests.test_x_intake_smoke_210
python3 examples/x-intake-local/smoke_210.py   # exit 2 with "pin matched"
python3 scripts/check_untrusted_text.py
python3 scripts/check_public_paths.py --paths <changed files>
python3 scripts/catalog_eval_queue.py
```

## Next

- Stage card backfill for entries 182-199 is still a separate change.
- Catalog HOLD 70-75 untouched. No Feature GO.
