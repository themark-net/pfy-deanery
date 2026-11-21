# X intake 2026-11-20: entries 206-207 and stage cards

Public catalog notes for this intake batch. Operator records stay in the private ops repo.

## What landed

- Entries `sources/entries/206-qwen3.8-27b-opencode-lora.md` and `207-llamafile.md`, both I0 awareness, each with an I0 stage card in `data/stages/`.
- Smokes `examples/x-intake-local/smoke_206.py` and `smoke_207.py` with 7 stub tests each
  (`tests/test_x_intake_smoke_206.py`, `tests/test_x_intake_smoke_207.py`). 206 checks the pinned Hugging Face
  revision, 207 the pinned GitHub commit; both exit 2, because nothing is downloaded or installed.

## Queue mode

Both cards have `trial` gates. 206 is the stronger candidate: an eval-auto trial in the OpenCode lane against
qwen3.6:35b, Q8_0 base, thinking off. 207 is a runner comparison against Ollama on one pinned GGUF.

## How to check

```
python3 -m unittest tests.test_x_intake_smoke_206 tests.test_x_intake_smoke_207
python3 examples/x-intake-local/smoke_206.py   # exit 2 with "pin matched"
python3 scripts/check_untrusted_text.py
python3 scripts/check_public_paths.py --paths <changed files>
python3 scripts/catalog_eval_queue.py
```

## Next

- Stage card backfill for entries 182-199 is still a separate change.
- Catalog HOLD 70-75 untouched. No Feature GO.
