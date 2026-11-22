# X intake 2026-11-21: entry 208 and stage card

Public catalog notes for this intake batch. Operator records stay in the private ops repo.

## What landed

- Entry `sources/entries/208-inkling-2-mini.md`, I0 awareness, with an I0 stage card `data/stages/inkling-2-mini.json`.
- Smoke `examples/x-intake-local/smoke_208.py` with 7 stub tests (`tests/test_x_intake_smoke_208.py`). It checks the pinned
  Hugging Face revision of the ggml-org GGUF repo and exits 2, because nothing is downloaded or installed.

## Queue mode

The card has a `trial` gate: an eval-auto trial in the OpenCode lane against qwen3.6:35b and the entry 206 adapter,
Q8_0 GGUF. The open question is whether llama.cpp on the AMD backend runs the looped layers at a useful speed.

## How to check

```
python3 -m unittest tests.test_x_intake_smoke_208
python3 examples/x-intake-local/smoke_208.py   # exit 2 with "pin matched"
python3 scripts/check_untrusted_text.py
python3 scripts/check_public_paths.py --paths <changed files>
python3 scripts/catalog_eval_queue.py
```

## Next

- Stage card backfill for entries 182-199 is still a separate change.
- Catalog HOLD 70-75 untouched. No Feature GO.
