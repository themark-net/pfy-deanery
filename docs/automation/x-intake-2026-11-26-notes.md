# X intake 2026-11-26: entry 209 and stage card

Public catalog notes for this intake batch. Operator records stay in the private ops repo.

## What landed

- Entry `sources/entries/209-ternary-bonsai-2.5-27b.md`, I0 awareness, with an I0 stage card `data/stages/ternary-bonsai-2-5-27b.json`.
- Smoke `examples/x-intake-local/smoke_209.py` with 7 stub tests (`tests/test_x_intake_smoke_209.py`). It checks the pinned
  Hugging Face revision of the prism-ml GGUF repo and exits 2, because nothing is downloaded or installed.

## Queue mode

The card has a `trial` gate: an eval-auto trial on nimo with stock llama.cpp and the Q2_0 GGUF against qwen3.6:35b and
the entry 206 adapter. The open question is whether Q2_0 runs at a useful speed on the AMD Vulkan or ROCm backend; the
PrismML fork formats (PTQ1_0, PQ2_0) need CUDA or Metal kernels and are out of scope on nimo.

## How to check

```
python3 -m unittest tests.test_x_intake_smoke_209
python3 examples/x-intake-local/smoke_209.py   # exit 2 with "pin matched"
python3 scripts/check_untrusted_text.py
python3 scripts/check_public_paths.py --paths <changed files>
python3 scripts/catalog_eval_queue.py
```

## Next

- Stage card backfill for entries 182-199 is still a separate change.
- Catalog HOLD 70-75 untouched. No Feature GO.
