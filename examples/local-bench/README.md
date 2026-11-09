# local-bench (Entry 089)

Stdlib harness for nimo local-inference: Ollama GPU tok/s plus the same 48 labeled Choice cases as Entry 086. Cite **#230**. Catalog **HOLD 70–75**. No GUI. **Not a Feature GO.** CUA-S1-FORMS stays the default decision lane.

```bash
python3 examples/local-bench/bench.py --check
python3 examples/local-bench/bench.py
python3 examples/local-bench/bench.py --no-stretch --num-ctx 2048
```

Default models (already in the Ollama store; the harness never pulls):

1. `qwen2.5-coder:1.5b`
2. `glm-4.7-flash:latest`
3. `qwen3-coder:30b`

Stretch (only if 1–3 RAN and `MemAvailable` stays ≥ 8 GiB): `qwen3-coder-next:latest`. `gpt-oss:120b` is skipped (65 GB > 64 GiB BIOS VRAM carve).

Fail closed: Ollama unreachable, or a requested model name missing from `/api/tags`. If a present model fails to load or stalls >30 min, it is dropped and the run continues. Unload is `keep_alive: 0`. Does not change BIOS, kernel cmdline, or sysctl.

Receipt: `pipelines/dogfood/local-bench/receipt.json`. Results: a private ops note.
